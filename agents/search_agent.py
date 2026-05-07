from tavily import TavilyClient
from state import ResearchState
from config import TAVILY_API_KEY
import re
import urllib.request


GITHUB_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
NON_REPO_OWNERS = {
    "collections", "events", "features", "marketplace", "orgs",
    "search", "settings", "sponsors", "topics", "users",
}


def _normalize_github_repo(url: str) -> str:
    match = GITHUB_RE.search(url or "")
    if not match:
        return ""
    owner, repo = match.group(1), match.group(2).rstrip(".git.,;:)]}>'\"")
    if owner.lower() in NON_REPO_OWNERS or not repo:
        return ""
    return f"https://github.com/{owner}/{repo}"


def _extract_github_links(text: str) -> list[str]:
    links = []
    seen = set()
    for match in GITHUB_RE.finditer(text or ""):
        link = _normalize_github_repo(match.group(0))
        if link and link not in seen:
            seen.add(link)
            links.append(link)
    return links


def extract_github_link(url: str, content: str = "") -> str:
    direct = _normalize_github_repo(url)
    if direct:
        return direct

    content_links = _extract_github_links(content)
    if content_links:
        return content_links[0]

    if not url or url.endswith(".pdf"):
        return ""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"},
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            html = response.read(100000).decode("utf-8", errors="ignore")
        links = _extract_github_links(html)
        return links[0] if links else ""
    except Exception:
        return ""


def get_paper_download_link(url: str) -> str:
    if "arxiv.org/abs/" in url:
        return url.replace("/abs/", "/pdf/") + ".pdf"
    if "arxiv.org/html/" in url:
        return url.replace("/html/", "/pdf/") + ".pdf"
    if "openreview.net/forum" in url:
        return url.replace("/forum", "/pdf")
    if url.endswith(".pdf"):
        return url
    return ""


def _append_results(all_results: list[dict], response: dict, query: str) -> None:
    for r in response.get("results", []):
        t_url = r.get("url", "")
        content = r.get("content", "")
        code_url = extract_github_link(t_url, content)
        dl_link = get_paper_download_link(t_url)

        content_augment = content
        if code_url:
            content_augment += f"\nCode link: {code_url}"
        if dl_link:
            content_augment += f"\nDownload link: {dl_link}"

        all_results.append({
            "title": r.get("title", ""),
            "url": t_url,
            "download_url": dl_link,
            "code_url": code_url,
            "content": content_augment,
            "score": r.get("score", 0.0),
            "query": query,
        })


def _github_count(results: list[dict]) -> int:
    links = {
        _normalize_github_repo(r.get("code_url", "") or r.get("url", ""))
        for r in results
    }
    return len({link for link in links if link})


def search_agent(state: ResearchState) -> dict:
    client = TavilyClient(api_key=TAVILY_API_KEY)
    queries = state["search_queries"]
    all_results = []

    for query in queries:
        try:
            response = client.search(
                query=query,
                max_results=5,
                search_depth="advanced",
                include_answer=False,
            )
            _append_results(all_results, response, query)
        except Exception as e:
            print(f"搜索失败 [{query}]: {e}")

    if _github_count(all_results) < 2:
        topic = state.get("topic", "")
        fallback_queries = [
            f"site:github.com {topic} implementation OR code",
            f"{topic} GitHub repository PapersWithCode",
        ]
        for query in fallback_queries:
            try:
                response = client.search(
                    query=query,
                    max_results=5,
                    search_depth="advanced",
                    include_answer=False,
                )
                _append_results(all_results, response, query)
                if _github_count(all_results) >= 2:
                    break
            except Exception as e:
                print(f"补充 GitHub 搜索失败 [{query}]: {e}")

    return {"raw_results": all_results}
