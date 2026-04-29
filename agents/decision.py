import json
from state import ResearchState
from config import MAX_SEARCH_LOOPS


def decision_node(state: ResearchState) -> str:
    feedback_str = state.get("reflection_feedback", "{}")
    loop_count = state.get("loop_count", 0)
    papers = state.get("extracted_papers", [])

    try:
        feedback = json.loads(feedback_str)
    except json.JSONDecodeError:
        feedback = {}

    should_continue = feedback.get("should_continue", False)

    if should_continue and loop_count < MAX_SEARCH_LOOPS:
        return "search"

    papers_with_code = [
        p for p in papers
        if p.get("code_url") not in (None, "", "unknown")
    ]
    if len(papers_with_code) >= 2:
        return "code_agent"

    return "report"
