import json
from state import ResearchState
from config import get_fast_llm, BEST_OF_N
from rl.reward import compute_batch_reward
from prompts import EXTRACT_PROMPT
from agents.info_extractor import (
    _extract_github_entries,
    _is_probable_code_repo,
    _normalize_github_url,
    _validate_github_url,
)


def _augment_with_verified_github(papers: list[dict], raw: list[dict]) -> list[dict]:
    valid = list(papers)
    raw_github_entries = _extract_github_entries(raw)
    raw_github_urls = {entry["url"] for entry in raw_github_entries}

    for paper in valid:
        code_url = paper.get("code_url", "unknown")
        if code_url and code_url != "unknown":
            clean = _normalize_github_url(code_url)
            if clean in raw_github_urls and _is_probable_code_repo(clean) and _validate_github_url(clean):
                paper["code_url"] = clean
            else:
                paper["code_url"] = "unknown"

    used_code_urls = {paper.get("code_url") for paper in valid}
    for entry in raw_github_entries:
        url = entry["url"]
        if url in used_code_urls or not _validate_github_url(url):
            continue
        result = entry["result"]
        valid.append({
            "title": result.get("title") or url.rsplit("/", 1)[-1],
            "year": 0,
            "method": "GitHub repository related to the research topic",
            "dataset": "unknown",
            "code_url": url,
            "download_url": result.get("download_url", ""),
            "contribution": result.get("content", "")[:200] or "Open-source implementation found in search results.",
            "relevance_score": max(2, min(5, int(round(float(result.get("score", 0)) * 5)) or 2)),
            "paper_type": "code",
        })
        used_code_urls.add(url)
        if sum(1 for paper in valid if paper.get("code_url") not in (None, "", "unknown")) >= 2:
            break

    return valid


def best_of_n_extract(state: ResearchState) -> dict:
    """对 Info Extractor 做 Best-of-N 采样，选择奖励最高的结果。"""
    llm = get_fast_llm(temperature=0.7)
    topic = state["topic"]
    raw = state.get("raw_results", [])

    if not raw:
        return {"extracted_papers": [], "reward_scores": [0.0]}

    results_text = json.dumps(raw[:15], ensure_ascii=False, indent=2)
    prompt = EXTRACT_PROMPT.format(results=results_text, topic=topic)

    candidates = []
    for i in range(BEST_OF_N):
        response = llm.invoke(prompt)
        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            papers = json.loads(content)
            papers = [p for p in papers if p.get("relevance_score", 0) >= 2]
            papers = _augment_with_verified_github(papers, raw)
        except json.JSONDecodeError:
            papers = []

        if papers:
            rewards = compute_batch_reward(papers, topic)
            avg_reward = sum(rewards) / len(rewards)
        else:
            avg_reward = 0.0

        candidates.append((papers, avg_reward))

    best_papers, best_reward = max(candidates, key=lambda x: x[1])

    return {
        "extracted_papers": best_papers,
        "reward_scores": [best_reward],
    }
