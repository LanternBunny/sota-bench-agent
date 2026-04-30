import json
from config import get_judge_llm
from prompts import REPORT_JUDGE_PROMPT


def compute_metrics(state: dict) -> dict:
    papers = state.get("extracted_papers", [])
    rewards = state.get("reward_scores", [])
    n = len(papers) if papers else 1

    covered = sum(
        1 for p in papers
        if p.get("method") and p["method"] != "unknown"
        and p.get("dataset") and p["dataset"] != "unknown"
        and p.get("contribution") and p["contribution"] != "unknown"
    )

    recent = sum(1 for p in papers if (p.get("year") or 0) >= 2024)

    with_code = sum(
        1 for p in papers
        if p.get("code_url") not in (None, "", "unknown")
    )

    return {
        "paper_count": len(papers),
        "coverage": round(covered / n, 3),
        "recency": round(recent / n, 3),
        "code_availability": round(with_code / n, 3),
        "avg_reward": round(sum(rewards) / len(rewards), 3) if rewards else 0.0,
        "loop_count": state.get("loop_count", 0),
        "reward_curve": list(rewards),
    }


def compute_report_quality(report: str, topic: str) -> dict:
    if not report or not report.strip():
        return {
            "completeness": 0, "accuracy": 0, "structure": 0,
            "insight": 0, "actionability": 0, "overall": 0,
            "comments": "空报告",
        }

    llm = get_judge_llm()
    prompt = REPORT_JUDGE_PROMPT.format(topic=topic, report=report[:4000])
    response = llm.invoke(prompt)
    content = response.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        scores = json.loads(content)
        for k in ("completeness", "accuracy", "structure", "insight", "actionability", "overall"):
            scores[k] = float(scores.get(k, 0))
        return scores
    except (json.JSONDecodeError, TypeError):
        return {
            "completeness": 0, "accuracy": 0, "structure": 0,
            "insight": 0, "actionability": 0, "overall": 0,
            "comments": "LLM 评估解析失败",
        }
