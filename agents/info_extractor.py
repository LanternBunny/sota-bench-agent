import json
import re
import urllib.request
import urllib.error
from state import ResearchState
from config import get_llm
from prompts import EXTRACT_PROMPT


def _validate_github_url(url: str) -> bool:
    if not url or url == "unknown":
        return False
    if not re.match(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+", url):
        return False
    clean = url.split("/tree/")[0].split("/blob/")[0].rstrip("/")
    try:
        req = urllib.request.Request(clean, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status < 400
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return False


def _extract_urls_from_raw(raw_results: list[dict]) -> set[str]:
    urls = set()
    for r in raw_results:
        text = f"{r.get('url', '')} {r.get('content', '')} {r.get('title', '')}"
        found = re.findall(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+", text)
        urls.update(found)
    return urls


def info_extractor(state: ResearchState) -> dict:
    llm = get_llm()
    topic = state["topic"]
    raw = state.get("raw_results", [])

    if not raw:
        return {"extracted_papers": []}

    raw_github_urls = _extract_urls_from_raw(raw)

    results_text = json.dumps(raw[:15], ensure_ascii=False, indent=2)
    response = llm.invoke(EXTRACT_PROMPT.format(results=results_text, topic=topic))
    content = response.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        papers = json.loads(content)
    except json.JSONDecodeError:
        papers = []

    for p in papers:
        code_url = p.get("code_url", "unknown")
        if code_url and code_url != "unknown":
            if code_url not in raw_github_urls:
                p["code_url"] = "unknown"
            elif not _validate_github_url(code_url):
                p["code_url"] = "unknown"

    valid = [p for p in papers if p.get("relevance_score", 0) >= 2]
    return {"extracted_papers": valid}
