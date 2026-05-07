from typing import TypedDict, Annotated
import operator


class PaperInfo(TypedDict, total=False):
    title: str
    year: int
    method: str
    dataset: str
    code_url: str
    download_url: str
    contribution: str
    relevance_score: float
    paper_type: str


class CodeCandidate(TypedDict, total=False):
    title: str
    code_url: str
    method: str
    dataset: str
    relevance_score: float


class ResearchState(TypedDict, total=False):
    topic: str
    workspace_name: str
    base_env: str
    auto_reproduce_code: bool
    search_queries: list[str]
    raw_results: Annotated[list[dict], operator.add]
    extracted_papers: list[PaperInfo]
    code_candidates: list[CodeCandidate]

    reflection_feedback: str
    reward_scores: Annotated[list[float], operator.add]
    loop_count: int

    final_report: str

    target_repo_url: str
    repo_files: dict[str, str]
    execution_logs: Annotated[list[str], operator.add]
    reproduction_status: str
    code_reward_scores: Annotated[list[float], operator.add]
