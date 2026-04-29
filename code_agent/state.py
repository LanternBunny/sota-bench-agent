from typing import TypedDict, Annotated
import operator


class CodeAgentState(TypedDict, total=False):
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

    status: str  # "pending" | "running" | "success" | "failed"
    reward: float
