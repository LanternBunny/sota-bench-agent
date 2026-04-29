import json
from state import ResearchState
from config import get_llm
from prompts import EXTRACT_PROMPT


def info_extractor(state: ResearchState) -> dict:
    llm = get_llm()
    topic = state["topic"]
    raw = state.get("raw_results", [])

    if not raw:
        return {"extracted_papers": []}

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

    valid = [p for p in papers if p.get("relevance_score", 0) >= 2]
    return {"extracted_papers": valid}
