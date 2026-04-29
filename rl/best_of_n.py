import json
from state import ResearchState
from config import get_fast_llm, BEST_OF_N
from rl.reward import compute_batch_reward
from prompts import EXTRACT_PROMPT


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
