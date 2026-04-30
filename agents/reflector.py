import json
from state import ResearchState
from config import get_llm, MAX_SEARCH_LOOPS
from prompts import REFLECT_PROMPT


def reflector(state: ResearchState) -> dict:
    llm = get_llm()
    papers = state.get("extracted_papers", [])
    loop_count = state.get("loop_count", 0)
    prev = state.get("reflection_feedback", "")

    prev_section = f"上一轮反馈：{prev}" if prev else ""

    response = llm.invoke(REFLECT_PROMPT.format(
        topic=state["topic"],
        loop_count=loop_count,
        paper_count=len(papers),
        papers=json.dumps(papers, ensure_ascii=False, indent=2)[:3000],
        prev_feedback=prev_section,
    ))
    content = response.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        feedback = json.loads(content)
    except json.JSONDecodeError:
        feedback = {"score": 0.5, "missing": [], "query_refinement": "", "should_continue": False}

    score = float(feedback.get("score", 0.5))

    has_code = any(
        p.get("code_url") not in (None, "", "unknown")
        and "github.com" in p.get("code_url", "")
        for p in papers
    )
    if not has_code and loop_count < MAX_SEARCH_LOOPS:
        feedback["should_continue"] = True
        if not feedback.get("query_refinement"):
            topic = state["topic"]
            feedback["query_refinement"] = f"site:github.com {topic} implementation code"
        if "代码" not in str(feedback.get("missing", [])):
            feedback.setdefault("missing", []).append("缺少附带真实 GitHub 代码的论文")

    new_queries = []
    if feedback.get("should_continue") and loop_count < MAX_SEARCH_LOOPS:
        refinement = feedback.get("query_refinement", "")
        if refinement:
            new_queries = [refinement]

    result = {
        "reflection_feedback": json.dumps(feedback, ensure_ascii=False),
        "reward_scores": [score],
        "loop_count": loop_count + 1,
    }
    if new_queries:
        result["search_queries"] = new_queries

    return result
