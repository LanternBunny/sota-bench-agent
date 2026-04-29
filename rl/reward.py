import json
from config import get_judge_llm
from prompts import JUDGE_PROMPT

WEIGHTS = {
    "completeness": 0.3,
    "relevance": 0.3,
    "code_availability": 0.2,
    "recency": 0.2,
}


def compute_reward(paper: dict, topic: str) -> float:
    scores = {}

    fields = ["title", "year", "method", "dataset", "contribution"]
    filled = sum(1 for f in fields if paper.get(f) and paper[f] not in (0, "unknown", ""))
    scores["completeness"] = filled / len(fields)

    scores["relevance"] = min(paper.get("relevance_score", 3) / 5.0, 1.0)

    code_url = paper.get("code_url", "unknown")
    scores["code_availability"] = 1.0 if code_url not in ("unknown", "", None) else 0.0

    year = paper.get("year", 0)
    if year >= 2024:
        scores["recency"] = 1.0
    elif year >= 2022:
        scores["recency"] = 0.6
    elif year > 0:
        scores["recency"] = 0.3
    else:
        scores["recency"] = 0.0

    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(total, 3)


def compute_reward_llm(paper: dict, topic: str) -> float:
    llm = get_judge_llm()
    response = llm.invoke(JUDGE_PROMPT.format(
        topic=topic,
        paper=json.dumps(paper, ensure_ascii=False, indent=2),
    ))
    content = response.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        scores = json.loads(content)
        total = sum(float(scores.get(k, 0)) * WEIGHTS[k] for k in WEIGHTS)
        return round(total, 3)
    except (json.JSONDecodeError, TypeError):
        return 0.5


def compute_batch_reward(papers: list[dict], topic: str, use_llm: bool = False) -> list[float]:
    func = compute_reward_llm if use_llm else compute_reward
    return [func(p, topic) for p in papers]
