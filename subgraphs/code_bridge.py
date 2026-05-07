from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END

from code_agent.graph import build_code_agent_graph
from config import MAX_CODE_FIX_LOOPS


class CodeBridgeState(TypedDict, total=False):
    topic: str
    workspace_name: str
    base_env: str
    auto_reproduce_code: bool
    target_repo_url: str

    repo_url: str
    repo_dir: str
    readme_content: str
    requirements_content: str
    entry_file: str
    repo_structure: str
    execution_plan: list[str]
    current_step: int
    execution_logs: Annotated[list[str], operator.add]
    error_message: str
    error_type: str
    patch: str
    fix_count: int
    max_fixes: int
    status: str
    reward: float

    reproduction_status: str
    code_reward_scores: Annotated[list[float], operator.add]


def _init_code_agent(state: CodeBridgeState) -> dict:
    repo_url = state.get("target_repo_url", "")
    if not repo_url:
        return {
            "status": "failed",
            "reproduction_status": "no_code_available",
        }
    return {
        "repo_url": repo_url,
        "workspace_name": state.get("workspace_name") or state.get("topic", ""),
        "base_env": state.get("base_env", ""),
        "fix_count": 0,
        "max_fixes": state.get("max_fixes", MAX_CODE_FIX_LOOPS),
        "status": "pending",
    }


def _should_run(state: CodeBridgeState) -> str:
    if not state.get("target_repo_url"):
        return "skip"
    return "run"


def _collect_result(state: CodeBridgeState) -> dict:
    return {
        "reproduction_status": state.get("status", "unknown"),
        "code_reward_scores": [state.get("reward", 0.0)],
    }


def _skip(_state: CodeBridgeState) -> dict:
    return {
        "reproduction_status": "no_code_available",
        "code_reward_scores": [0.0],
    }


def build_code_bridge_graph() -> StateGraph:
    graph = StateGraph(CodeBridgeState)

    code_agent_compiled = build_code_agent_graph().compile()

    graph.add_node("init", _init_code_agent)
    graph.add_node("reproduction_agent", code_agent_compiled)
    graph.add_node("collect_result", _collect_result)
    graph.add_node("skip", _skip)

    graph.add_edge(START, "init")
    graph.add_conditional_edges(
        "init",
        _should_run,
        {
            "run": "reproduction_agent",
            "skip": "skip",
        },
    )
    graph.add_edge("reproduction_agent", "collect_result")
    graph.add_edge("collect_result", END)
    graph.add_edge("skip", END)

    return graph


def compile_code_bridge():
    return build_code_bridge_graph().compile()
