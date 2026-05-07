import json
from state import ResearchState
from config import MAX_SEARCH_LOOPS


def decision_node(state: ResearchState) -> str:
    feedback_str = state.get("reflection_feedback", "{}")
    loop_count = state.get("loop_count", 0)
    try:
        feedback = json.loads(feedback_str)
    except json.JSONDecodeError:
        feedback = {}

    should_continue = feedback.get("should_continue", False)

    if should_continue and loop_count < MAX_SEARCH_LOOPS:
        return "search"

    return "report"
