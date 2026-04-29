from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import ResearchState
from agents.query_planner import query_planner
from agents.search_agent import search_agent
from agents.paper_filter import paper_filter
from agents.info_extractor import info_extractor
from agents.reflector import reflector
from agents.decision import decision_node
from agents.report_writer import report_writer
from rl.best_of_n import best_of_n_extract
from rl.experience_buffer import experience_buffer
from rl.reward import compute_batch_reward
from code_agent.graph import compile_code_agent
from config import MAX_CODE_FIX_LOOPS


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


def run_code_agent(state: ResearchState) -> dict:
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
    repo_url = best["code_url"]

    code_app = compile_code_agent()
    result = code_app.invoke({
        "repo_url": repo_url,
        "fix_count": 0,
        "max_fixes": MAX_CODE_FIX_LOOPS,
        "status": "pending",
    })

    logs = result.get("execution_logs", [])
    return {
        "target_repo_url": repo_url,
        "reproduction_status": result.get("status", "unknown"),
        "execution_logs": "\n".join(logs) if isinstance(logs, list) else str(logs),
        "code_reward_scores": [result.get("reward", 0.0)],
    }


def build_research_graph(use_best_of_n: bool = True) -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("query_planner", query_planner)
    graph.add_node("search_agent", search_agent)
    graph.add_node("paper_filter", paper_filter)

    if use_best_of_n:
        graph.add_node("info_extractor", best_of_n_extract)
    else:
        graph.add_node("info_extractor", info_extractor)

    graph.add_node("reflector", reflector)
    graph.add_node("report_writer", report_writer)
    graph.add_node("code_agent", run_code_agent)
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
            "search": "search_agent",
            "report": "report_writer",
            "code_agent": "code_agent",
        },
    )

    graph.add_edge("code_agent", "report_writer")
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
