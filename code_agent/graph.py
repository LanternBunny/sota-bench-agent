from langgraph.graph import StateGraph, START, END

from code_agent.state import CodeAgentState
from code_agent.repo_fetcher import repo_fetcher
from code_agent.code_parser import code_parser
from code_agent.execution_planner import execution_planner
from code_agent.executor import executor, cleanup_conda_env
from code_agent.error_analyzer import error_analyzer
from code_agent.patch_generator import patch_generator
from config import MAX_CODE_FIX_LOOPS


def _route_after_fetch(state: CodeAgentState) -> str:
    if state.get("status") == "failed":
        return "give_up"
    return "parse"


def _route_after_exec(state: CodeAgentState) -> str:
    status = state.get("status", "")
    if status == "success":
        return "done"
    if status == "error":
        fix_count = state.get("fix_count", 0)
        if fix_count >= state.get("max_fixes", MAX_CODE_FIX_LOOPS):
            return "give_up"
        return "analyze"
    step = state.get("current_step", 0)
    plan = state.get("execution_plan", [])
    if step < len(plan):
        return "next_step"
    return "done"


def _finalize_success(state: CodeAgentState) -> dict:
    return {
        "status": "success",
        "reward": 1.0,
        "execution_logs": ["Code reproduction completed successfully"],
    }


def _finalize_failure(state: CodeAgentState) -> dict:
    return {
        "status": "failed",
        "reward": -0.5,
        "execution_logs": [f"Gave up after {state.get('fix_count', 0)} fix attempts"],
    }


def build_code_agent_graph() -> StateGraph:
    graph = StateGraph(CodeAgentState)

    graph.add_node("repo_fetcher", repo_fetcher)
    graph.add_node("code_parser", code_parser)
    graph.add_node("execution_planner", execution_planner)
    graph.add_node("executor", executor)
    graph.add_node("error_analyzer", error_analyzer)
    graph.add_node("patch_generator", patch_generator)
    graph.add_node("finalize_success", _finalize_success)
    graph.add_node("finalize_failure", _finalize_failure)

    graph.add_edge(START, "repo_fetcher")

    graph.add_conditional_edges(
        "repo_fetcher",
        _route_after_fetch,
        {
            "parse": "code_parser",
            "give_up": "finalize_failure",
        },
    )

    graph.add_edge("code_parser", "execution_planner")
    graph.add_edge("execution_planner", "executor")

    graph.add_conditional_edges(
        "executor",
        _route_after_exec,
        {
            "done": "finalize_success",
            "analyze": "error_analyzer",
            "give_up": "finalize_failure",
            "next_step": "executor",
        },
    )

    graph.add_edge("error_analyzer", "patch_generator")
    graph.add_edge("patch_generator", "executor")

    graph.add_edge("finalize_success", END)
    graph.add_edge("finalize_failure", END)

    return graph


def compile_code_agent():
    graph = build_code_agent_graph()
    return graph.compile()


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/openai/openai-quickstart-python"
    app = compile_code_agent()

    print(f"Testing Code Agent with: {url}")
    result = app.invoke({
        "repo_url": url,
        "fix_count": 0,
        "max_fixes": MAX_CODE_FIX_LOOPS,
        "status": "pending",
    })

    print(f"\nStatus: {result.get('status')}")
    print(f"Reward: {result.get('reward')}")
    print(f"Fix attempts: {result.get('fix_count')}")
    print("\nExecution logs:")
    for log in result.get("execution_logs", []):
        print(f"  {log}")
