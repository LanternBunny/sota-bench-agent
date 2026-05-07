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

    try:
        queries = json.loads(content)
    except json.JSONDecodeError:
        queries = [
            f"{topic} survey review",
            f"{topic} benchmark dataset",
            f"{topic} latest papers 2025 2026",
            f"site:github.com {topic} implementation code",
            f"{topic} PapersWithCode GitHub repository",
        ]

    github_queries = [
        f"site:github.com {topic} implementation code",
        f"{topic} PapersWithCode GitHub repository",
    ]
    for query in github_queries:
        if query not in queries:
            queries.append(query)
    return {"search_queries": queries}
