import json
import re
import tempfile

import requests
from pypdf import PdfReader

from config import get_fast_llm
from state import ResearchState


PDF_PROMPT = """你是一个专门评估和提取 AI 论文核心信息的助手。
我们在论文文本中正则匹配到了以下可能的 GitHub 代码链接：
【正则匹配到的代码链接】：{github_hints}

这里有这篇论文包含摘要、实验或结果部分的节选文本：
{text}

请严格输出 JSON：
{{
  "code_url": "如果正则匹配到相关代码，或正文直接提到 GitHub/代码链接，填写具体 URL；否则填 unknown",
  "datasets": "论文中评估或使用的主要数据集名称",
  "sota_metrics": "具体 SOTA 指标数字；没有读到具体数字则填 unknown"
}}
不要输出 markdown 代码块或额外说明。
"""


def _pdf_url(url: str) -> str:
    if "arxiv.org/abs/" in url:
        return url.replace("/abs/", "/pdf/") + ".pdf"
    if "arxiv.org/html/" in url:
        return url.replace("/html/", "/pdf/") + ".pdf"
    if "openreview.net/forum" in url:
        return url.replace("/forum", "/pdf")
    if url.endswith(".pdf") or "pdf" in url.lower():
        return url
    return ""


def _strip_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return content.strip()


def extract_info_from_pdf(url: str) -> dict | None:
    pdf_url = _pdf_url(url)
    if not pdf_url:
        return None

    try:
        response = requests.get(
            pdf_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        response.raise_for_status()
        pdf_data = response.content[: 15 * 1024 * 1024]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_data)
            tmp_path = tmp.name

        reader = PdfReader(tmp_path)
        all_text = ""
        target_pages = {0, 1}
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            all_text += page_text + "\n"
            lower = page_text.lower()
            if "experiment" in lower or "result" in lower:
                target_pages.add(i)

        github_links = sorted(set(re.findall(
            r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
            all_text,
        )))
        github_links = [link.rstrip(".)],;:>\"'") for link in github_links]
        github_hints = ", ".join(github_links) if github_links else "无"

        text_content = ""
        for i in sorted(target_pages):
            if i < len(reader.pages):
                text_content += (reader.pages[i].extract_text() or "") + "\n"
            if len(text_content) > 20000:
                break
        text_content = text_content.encode("utf-8", "replace").decode("utf-8")[:20000]

        resp = get_fast_llm(temperature=0).invoke(
            PDF_PROMPT.format(text=text_content, github_hints=github_hints)
        )
        result = json.loads(_strip_json(resp.content))
        result["download_url"] = pdf_url
        return result
    except Exception as exc:
        print(f"PDF Agent failed on {pdf_url}: {exc}")
        return None


def pdf_agent(state: ResearchState) -> dict:
    papers = state.get("extracted_papers", [])
    enriched = []

    for paper in papers:
        target_url = paper.get("download_url") or paper.get("url", "")
        pdf_info = extract_info_from_pdf(target_url)
        if pdf_info:
            code_url = pdf_info.get("code_url")
            if code_url and code_url not in ("unknown", "None", ""):
                paper["code_url"] = code_url
            paper["datasets"] = pdf_info.get("datasets", paper.get("dataset", ""))
            paper["sota_metrics"] = pdf_info.get("sota_metrics", "")
            paper["download_url"] = pdf_info.get("download_url", target_url)
        else:
            paper.setdefault("datasets", paper.get("dataset", "unknown"))
            paper.setdefault("sota_metrics", "unknown")

        has_paper = paper.get("download_url") not in (None, "", "unknown", "None")
        has_code = paper.get("code_url") not in (None, "", "unknown", "None")
        if has_paper or has_code:
            enriched.append(paper)

    def paper_score(paper: dict) -> int:
        return sum(
            bool(paper.get(key) and paper.get(key) not in ("unknown", "None"))
            for key in ("download_url", "code_url", "sota_metrics", "datasets")
        )

    enriched.sort(key=paper_score, reverse=True)
    return {"extracted_papers": enriched}
