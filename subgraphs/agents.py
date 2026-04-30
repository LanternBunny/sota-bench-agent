"""
将每个 LLM Agent 函数拆分为 3 步子图：build_prompt → call_llm → parse_output
使其在 LangGraph Studio 中可展开查看内部流程。
"""
from typing import TypedDict, Annotated, Callable
import operator
from langgraph.graph import StateGraph, START, END

from state import ResearchState


# ── query_planner ──────────────────────────────────────────────

class _QPState(TypedDict, total=False):
    topic: str
    search_queries: list[str]
    _prompt: str
    _raw_response: str


def _qp_build_prompt(state: _QPState) -> dict:
    from prompts import QUERY_PLANNER_PROMPT
    return {"_prompt": QUERY_PLANNER_PROMPT.format(topic=state["topic"])}


def _qp_call_llm(state: _QPState) -> dict:
    from config import get_llm
    llm = get_llm()
    resp = llm.invoke(state["_prompt"])
    return {"_raw_response": resp.content.strip()}


def _qp_parse_output(state: _QPState) -> dict:
    import json
    content = state["_raw_response"]
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    queries = json.loads(content)
    return {"search_queries": queries}


def build_query_planner_graph() -> StateGraph:
    g = StateGraph(_QPState)
    g.add_node("build_prompt", _qp_build_prompt)
    g.add_node("call_llm", _qp_call_llm)
    g.add_node("parse_output", _qp_parse_output)
    g.add_edge(START, "build_prompt")
    g.add_edge("build_prompt", "call_llm")
    g.add_edge("call_llm", "parse_output")
    g.add_edge("parse_output", END)
    return g


def compile_query_planner():
    return build_query_planner_graph().compile()


# ── info_extractor ─────────────────────────────────────────────

class _IEState(TypedDict, total=False):
    topic: str
    raw_results: Annotated[list[dict], operator.add]
    extracted_papers: list[dict]
    _prompt: str
    _raw_response: str
    _raw_github_urls: list[str]


def _ie_build_prompt(state: _IEState) -> dict:
    import json, re
    from prompts import EXTRACT_PROMPT
    raw = state.get("raw_results", [])
    urls = set()
    for r in raw:
        text = f"{r.get('url', '')} {r.get('content', '')} {r.get('title', '')}"
        found = re.findall(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+", text)
        urls.update(found)
    results_text = json.dumps(raw[:15], ensure_ascii=False, indent=2)
    prompt = EXTRACT_PROMPT.format(results=results_text, topic=state["topic"])
    return {"_prompt": prompt, "_raw_github_urls": list(urls)}


def _ie_call_llm(state: _IEState) -> dict:
    from config import get_llm
    llm = get_llm()
    resp = llm.invoke(state["_prompt"])
    return {"_raw_response": resp.content.strip()}


def _ie_parse_output(state: _IEState) -> dict:
    import json, re, urllib.request, urllib.error
    content = state["_raw_response"]
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    try:
        papers = json.loads(content)
    except json.JSONDecodeError:
        papers = []

    raw_urls = set(state.get("_raw_github_urls", []))
    for p in papers:
        code_url = p.get("code_url", "unknown")
        if code_url and code_url != "unknown":
            if code_url not in raw_urls:
                p["code_url"] = "unknown"
            else:
                clean = code_url.split("/tree/")[0].split("/blob/")[0].rstrip("/")
                if not re.match(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+", clean):
                    p["code_url"] = "unknown"
                else:
                    try:
                        req = urllib.request.Request(clean, method="HEAD")
                        req.add_header("User-Agent", "Mozilla/5.0")
                        resp = urllib.request.urlopen(req, timeout=10)
                        if resp.status >= 400:
                            p["code_url"] = "unknown"
                    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
                        p["code_url"] = "unknown"

    valid = [p for p in papers if p.get("relevance_score", 0) >= 2]
    return {"extracted_papers": valid}


def build_info_extractor_graph() -> StateGraph:
    g = StateGraph(_IEState)
    g.add_node("build_prompt", _ie_build_prompt)
    g.add_node("call_llm", _ie_call_llm)
    g.add_node("parse_output", _ie_parse_output)
    g.add_edge(START, "build_prompt")
    g.add_edge("build_prompt", "call_llm")
    g.add_edge("call_llm", "parse_output")
    g.add_edge("parse_output", END)
    return g


def compile_info_extractor():
    return build_info_extractor_graph().compile()


# ── reflector ──────────────────────────────────────────────────

class _RFState(TypedDict, total=False):
    topic: str
    extracted_papers: list[dict]
    reflection_feedback: str
    reward_scores: Annotated[list[float], operator.add]
    loop_count: int
    search_queries: list[str]
    _prompt: str
    _raw_response: str


def _rf_build_prompt(state: _RFState) -> dict:
    import json
    from prompts import REFLECT_PROMPT
    papers = state.get("extracted_papers", [])
    loop_count = state.get("loop_count", 0)
    prev = state.get("reflection_feedback", "")
    prev_section = f"上一轮反馈：{prev}" if prev else ""
    prompt = REFLECT_PROMPT.format(
        topic=state["topic"],
        loop_count=loop_count,
        paper_count=len(papers),
        papers=json.dumps(papers, ensure_ascii=False, indent=2)[:3000],
        prev_feedback=prev_section,
    )
    return {"_prompt": prompt}


def _rf_call_llm(state: _RFState) -> dict:
    from config import get_llm
    llm = get_llm()
    resp = llm.invoke(state["_prompt"])
    return {"_raw_response": resp.content.strip()}


def _rf_parse_output(state: _RFState) -> dict:
    import json
    from config import MAX_SEARCH_LOOPS
    content = state["_raw_response"]
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
    papers = state.get("extracted_papers", [])
    loop_count = state.get("loop_count", 0)

    has_code = any(
        p.get("code_url") not in (None, "", "unknown")
        and "github.com" in p.get("code_url", "")
        for p in papers
    )
    if not has_code and loop_count < MAX_SEARCH_LOOPS:
        feedback["should_continue"] = True
        if not feedback.get("query_refinement"):
            feedback["query_refinement"] = f"site:github.com {state['topic']} implementation code"
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


def build_reflector_graph() -> StateGraph:
    g = StateGraph(_RFState)
    g.add_node("build_prompt", _rf_build_prompt)
    g.add_node("call_llm", _rf_call_llm)
    g.add_node("parse_output", _rf_parse_output)
    g.add_edge(START, "build_prompt")
    g.add_edge("build_prompt", "call_llm")
    g.add_edge("call_llm", "parse_output")
    g.add_edge("parse_output", END)
    return g


def compile_reflector():
    return build_reflector_graph().compile()


# ── report_writer ──────────────────────────────────────────────

class _RWState(TypedDict, total=False):
    topic: str
    extracted_papers: list[dict]
    reward_scores: Annotated[list[float], operator.add]
    loop_count: int
    final_report: str
    _prompt: str
    _raw_response: str


def _rw_build_prompt(state: _RWState) -> dict:
    import json
    from prompts import REPORT_PROMPT
    papers = state.get("extracted_papers", [])
    prompt = REPORT_PROMPT.format(
        topic=state["topic"],
        papers=json.dumps(papers, ensure_ascii=False, indent=2),
    )
    return {"_prompt": prompt}


def _rw_call_llm(state: _RWState) -> dict:
    from config import get_llm
    llm = get_llm()
    resp = llm.invoke(state["_prompt"])
    return {"_raw_response": resp.content.strip()}


def _rw_parse_output(state: _RWState) -> dict:
    import re
    content = state["_raw_response"]
    stripped = content.strip()
    pattern = r"^```(?:markdown|md)?\s*\n(.*?)```\s*$"
    match = re.match(pattern, stripped, re.DOTALL)
    if match:
        stripped = match.group(1).strip()

    papers = state.get("extracted_papers", [])
    reward_summary = state.get("reward_scores", [])
    appendix = f"\n\n---\n\n## 附录：Agent 运行统计\n\n"
    appendix += f"- 搜索轮次：{state.get('loop_count', 1)}\n"
    appendix += f"- 提取论文数：{len(papers)}\n"
    appendix += f"- 反思奖励分数：{reward_summary}\n"
    if reward_summary:
        appendix += f"- 平均奖励：{sum(reward_summary) / len(reward_summary):.2f}\n"

    return {"final_report": stripped + appendix}


def build_report_writer_graph() -> StateGraph:
    g = StateGraph(_RWState)
    g.add_node("build_prompt", _rw_build_prompt)
    g.add_node("call_llm", _rw_call_llm)
    g.add_node("parse_output", _rw_parse_output)
    g.add_edge(START, "build_prompt")
    g.add_edge("build_prompt", "call_llm")
    g.add_edge("call_llm", "parse_output")
    g.add_edge("parse_output", END)
    return g


def compile_report_writer():
    return build_report_writer_graph().compile()


# ── search_agent ──────────────────────────────────────────────

class _SAState(TypedDict, total=False):
    search_queries: list[str]
    raw_results: Annotated[list[dict], operator.add]
    _current_queries: list[str]
    _tool_raw: list[dict]


def _sa_build_queries(state: _SAState) -> dict:
    queries = list(state.get("search_queries", []))
    return {"_current_queries": queries}


def _sa_call_tool(state: _SAState) -> dict:
    from tavily import TavilyClient
    from config import TAVILY_API_KEY
    client = TavilyClient(api_key=TAVILY_API_KEY)
    queries = state.get("_current_queries", [])
    all_results = []
    for query in queries:
        try:
            response = client.search(
                query=query,
                max_results=5,
                search_depth="advanced",
                include_answer=False,
            )
            for r in response.get("results", []):
                all_results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                    "query": query,
                })
        except Exception as e:
            print(f"搜索失败 [{query}]: {e}")
    return {"_tool_raw": all_results}


def _sa_collect_results(state: _SAState) -> dict:
    return {"raw_results": state.get("_tool_raw", [])}


def build_search_agent_graph() -> StateGraph:
    g = StateGraph(_SAState)
    g.add_node("build_queries", _sa_build_queries)
    g.add_node("call_tool", _sa_call_tool)
    g.add_node("collect_results", _sa_collect_results)
    g.add_edge(START, "build_queries")
    g.add_edge("build_queries", "call_tool")
    g.add_edge("call_tool", "collect_results")
    g.add_edge("collect_results", END)
    return g


def compile_search_agent():
    return build_search_agent_graph().compile()
