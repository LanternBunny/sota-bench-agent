import json
from state import ResearchState
from config import get_llm
from prompts import QUERY_PLANNER_PROMPT


def query_planner(state: ResearchState) -> dict:
    llm = get_llm()
    topic = state["topic"]
    response = llm.invoke(QUERY_PLANNER_PROMPT.format(topic=topic))
    content = response.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    queries = json.loads(content)
    return {"search_queries": queries}
