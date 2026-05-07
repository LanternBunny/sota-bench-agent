from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import ResearchState
from agents.decision import decision_node
from agents.paper_filter import paper_filter
from rl.best_of_n import best_of_n_extract
from subgraphs.agents import (
    build_query_planner_graph,
    build_search_agent_graph,
    build_info_extractor_graph,
    build_reflector_graph,
    build_report_writer_graph,
)
from subgraphs.code_bridge import build_code_bridge_graph
from rl.experience_buffer import experience_buffer
from agents.pdf_agent import pdf_agent
from agents.info_extractor import _is_probable_code_repo


def save_experience(state: ResearchState) -> dict:
    papers = state.get("extracted_papers", [])
    rewards = state.get("reward_scores", [])
    avg_reward = sum(rewards) / len(rewards) if rewards else 0.0

    trajectory = {
        "topic": state.get("topic", ""),
        "queries": state.get("search_queries", []),
        "paper_count": len(papers),
    }
    experience_buffer.add(trajectory, avg_reward)
    return {}


def prepare_code_candidates(state: ResearchState) -> dict:
    candidates = []
    seen = set()
    for paper in state.get("extracted_papers", []):
        code_url = paper.get("code_url", "")
        if (
            not code_url
            or code_url == "unknown"
            or "github.com" not in code_url
            or not _is_probable_code_repo(code_url)
            or code_url in seen
        ):
            continue
        seen.add(code_url)
        candidates.append({
            "title": paper.get("title", "Unknown"),
            "code_url": code_url,
            "method": paper.get("method", ""),
            "dataset": paper.get("datasets", paper.get("dataset", "")),
            "relevance_score": paper.get("relevance_score", 0),
        })
    candidates.sort(key=lambda item: item.get("relevance_score", 0), reverse=True)

    target_repo_url = state.get("target_repo_url", "")
    if not target_repo_url and state.get("auto_reproduce_code") and candidates:
        target_repo_url = candidates[0].get("code_url", "")

    result = {"code_candidates": candidates}
    if target_repo_url:
        result["target_repo_url"] = target_repo_url
    return result


def route_after_code_candidates(state: ResearchState) -> str:
    if state.get("target_repo_url"):
        return "reproduce"
    return "report"


def run_code_reproduction(state: ResearchState) -> dict:
    app = build_code_bridge_graph().compile()
    result = app.invoke({
        "topic": state.get("topic", ""),
        "workspace_name": state.get("workspace_name") or state.get("topic", ""),
        "base_env": state.get("base_env", ""),
        "target_repo_url": state.get("target_repo_url", ""),
    })
    return {
        "reproduction_status": result.get("reproduction_status", result.get("status", "unknown")),
        "code_reward_scores": result.get("code_reward_scores", [result.get("reward", 0.0)]),
        "execution_logs": result.get("execution_logs", []),
    }


def build_research_graph(use_best_of_n: bool = True) -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("query_planner", build_query_planner_graph().compile())
    graph.add_node("search_agent", build_search_agent_graph().compile())
    graph.add_node("paper_filter", paper_filter)

    if use_best_of_n:
        graph.add_node("info_extractor", best_of_n_extract)
    else:
        graph.add_node("info_extractor", build_info_extractor_graph().compile())

    graph.add_node("reflector", build_reflector_graph().compile())
    graph.add_node("report_writer", build_report_writer_graph().compile())
    graph.add_node("pdf_agent", pdf_agent)
    graph.add_node("prepare_code_candidates", prepare_code_candidates)
    graph.add_node("code_reproduction", run_code_reproduction)
    graph.add_node("save_experience", save_experience)

    graph.add_edge(START, "query_planner")
    graph.add_edge("query_planner", "search_agent")
    graph.add_edge("search_agent", "paper_filter")
    graph.add_edge("paper_filter", "info_extractor")
    graph.add_edge("info_extractor", "reflector")

    graph.add_conditional_edges(
        "reflector",
        decision_node,
        {
            "search": "query_planner",
            "report": "pdf_agent",
        },
    )

    graph.add_edge("pdf_agent", "prepare_code_candidates")
    graph.add_conditional_edges(
        "prepare_code_candidates",
        route_after_code_candidates,
        {
            "reproduce": "code_reproduction",
            "report": "report_writer",
        },
    )
    graph.add_edge("code_reproduction", "report_writer")
    graph.add_edge("report_writer", "save_experience")
    graph.add_edge("save_experience", END)

    return graph


def compile_graph(use_best_of_n: bool = True):
    graph = build_research_graph(use_best_of_n)
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "multimodal hallucination detection"
    app = compile_graph()

    print(f"研究主题: {topic}")
    print("=" * 60)

    config = {"configurable": {"thread_id": "test-1"}}
    result = app.invoke({"topic": topic, "loop_count": 0}, config)

    print("\n" + "=" * 60)
    print("最终报告：")
    print(result.get("final_report", "无报告生成"))
