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

    target_repo_url = state.get("target_repo_url", "")
    reproduction_status = state.get("reproduction_status", "")
    if target_repo_url or reproduction_status:
        appendix += "\n## 附录：代码复现\n\n"
        appendix += f"- 目标仓库：{target_repo_url or '无'}\n"
        appendix += f"- 复现状态：{reproduction_status or '未执行'}\n"
        code_rewards = state.get("code_reward_scores", [])
        if code_rewards:
            appendix += f"- 代码复现奖励：{code_rewards}\n"

    return {"final_report": report_content + appendix}
