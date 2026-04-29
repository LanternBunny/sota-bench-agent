from typing import TypedDict, Annotated
import operator


class PaperInfo(TypedDict, total=False):
    title: str
    year: int
    method: str
    dataset: str
    code_url: str
    contribution: str
    relevance_score: float
    paper_type: str


class ResearchState(TypedDict, total=False):
    topic: str
    search_queries: list[str]
    raw_results: Annotated[list[dict], operator.add]
    extracted_papers: list[PaperInfo]

    reflection_feedback: str
    reward_scores: Annotated[list[float], operator.add]
    loop_count: int

    final_report: str

    target_repo_url: str
    repo_files: dict[str, str]
    execution_logs: str
    reproduction_status: str
    code_reward_scores: Annotated[list[float], operator.add]
