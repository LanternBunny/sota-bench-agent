import json
import re
from state import ResearchState
from config import get_llm
from prompts import REPORT_PROMPT


def _strip_markdown_fence(text: str) -> str:
    """去除 LLM 输出中包裹的 ```markdown ... ``` 代码块标记。"""
    stripped = text.strip()
    pattern = r"^```(?:markdown|md)?\s*\n(.*?)```\s*$"
    match = re.match(pattern, stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


def report_writer(state: ResearchState) -> dict:
    llm = get_llm()
    papers = state.get("extracted_papers", [])
    topic = state["topic"]

    response = llm.invoke(REPORT_PROMPT.format(
        topic=topic,
        papers=json.dumps(papers, ensure_ascii=False, indent=2),
    ))

    report_content = _strip_markdown_fence(response.content)

    reward_summary = state.get("reward_scores", [])
    appendix = f"\n\n---\n\n## 附录：Agent 运行统计\n\n"
    appendix += f"- 搜索轮次：{state.get('loop_count', 1)}\n"
    appendix += f"- 提取论文数：{len(papers)}\n"
    appendix += f"- 反思奖励分数：{reward_summary}\n"
    if reward_summary:
        appendix += f"- 平均奖励：{sum(reward_summary) / len(reward_summary):.2f}\n"

    return {"final_report": report_content + appendix}
