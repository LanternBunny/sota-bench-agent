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


def _select_paper(state: ResearchState) -> dict:
    papers = state.get("extracted_papers", [])
    papers_with_code = [
        p for p in papers
        if p.get("code_url") not in (None, "", "unknown")
    ]
    if not papers_with_code:
        return {
            "reproduction_status": "no_code_available",
            "execution_logs": "",
        }
    best = max(papers_with_code, key=lambda p: p.get("relevance_score", 0))
    return {"target_repo_url": best["code_url"]}


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
    graph.add_node("select_paper", _select_paper)
    graph.add_node("code_reproduction", build_code_bridge_graph().compile())
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
            "report": "report_writer",
            "code_reproduction": "select_paper",
        },
    )

    graph.add_edge("select_paper", "code_reproduction")
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
