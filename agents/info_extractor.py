import json
import re
import urllib.request
import urllib.error
from state import ResearchState
from config import get_llm
from prompts import EXTRACT_PROMPT


NON_REPO_OWNERS = {
    "collections", "events", "features", "marketplace", "orgs",
    "search", "settings", "sponsors", "topics", "users",
}

NON_CODE_REPO_TERMS = (
    "awesome", "paper-list", "papers-list", "reading-list", "literature",
    "survey", "surveys", "resources", "resource-list", "benchmark-list",
)


def _is_probable_code_repo(url: str) -> bool:
    clean = _normalize_github_url(url)
    if not clean:
        return False
    repo_name = clean.rstrip("/").split("/")[-1].lower()
    return not any(term in repo_name for term in NON_CODE_REPO_TERMS)


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


def _normalize_github_url(url: str) -> str:
    match = re.search(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+", url or "")
    if not match:
        return ""
    clean = match.group(0).split("/tree/")[0].split("/blob/")[0].rstrip("/.,;:)]}>'\"")
    if clean.endswith(".git"):
        clean = clean[:-4]
    owner = clean.split("/")[3].lower()
    if owner in NON_REPO_OWNERS:
        return ""
    return clean


def _extract_github_entries(raw_results: list[dict]) -> list[dict]:
    entries = []
    seen = set()
    for r in raw_results:
        text = f"{r.get('url', '')} {r.get('code_url', '')} {r.get('content', '')} {r.get('title', '')}"
        found = re.findall(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+", text)
        for url in found:
            clean = _normalize_github_url(url)
            if clean and _is_probable_code_repo(clean) and clean not in seen:
                seen.add(clean)
                entries.append({"url": clean, "result": r})
    return entries


def info_extractor(state: ResearchState) -> dict:
    llm = get_llm()
    topic = state["topic"]
    raw = state.get("raw_results", [])

    if not raw:
        return {"extracted_papers": []}

    raw_github_entries = _extract_github_entries(raw)
    raw_github_urls = {entry["url"] for entry in raw_github_entries}

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
            clean = _normalize_github_url(code_url)
            if clean not in raw_github_urls or not _is_probable_code_repo(clean):
                p["code_url"] = "unknown"
            elif not _validate_github_url(clean):
                p["code_url"] = "unknown"
            else:
                p["code_url"] = clean

    valid = [p for p in papers if p.get("relevance_score", 0) >= 2]
    used_code_urls = {p.get("code_url") for p in valid}
    for entry in raw_github_entries:
        url = entry["url"]
        if url in used_code_urls or not _validate_github_url(url):
            continue
        r = entry["result"]
        valid.append({
            "title": r.get("title") or url.rsplit("/", 1)[-1],
            "year": 0,
            "method": "GitHub repository related to the research topic",
            "dataset": "unknown",
            "code_url": url,
            "download_url": r.get("download_url", ""),
            "contribution": r.get("content", "")[:200] or "Open-source implementation found in search results.",
            "relevance_score": max(2, min(5, int(round(float(r.get("score", 0)) * 5)) or 2)),
            "paper_type": "code",
        })
        used_code_urls.add(url)
        if sum(1 for p in valid if p.get("code_url") not in (None, "", "unknown")) >= 2:
            break

    return {"extracted_papers": valid}
