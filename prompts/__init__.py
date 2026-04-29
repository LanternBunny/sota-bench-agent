"""
SOTA-Bench Agent Prompt 集中管理模块

所有 LLM prompt 模板统一维护在此目录下。
各 agent 通过 from prompts import QUERY_PLANNER_PROMPT 方式引用。
修改 prompt 只需编辑对应 .py 文件，无需改动 agent 逻辑。
"""

from prompts.query_planner import QUERY_PLANNER_PROMPT
from prompts.info_extractor import EXTRACT_PROMPT
from prompts.reflector import REFLECT_PROMPT
from prompts.report_writer import REPORT_PROMPT
from prompts.judge import JUDGE_PROMPT
from prompts.execution_planner import EXECUTION_PLANNER_PROMPT
from prompts.error_analyzer import ERROR_ANALYZER_PROMPT

__all__ = [
    "QUERY_PLANNER_PROMPT",
    "EXTRACT_PROMPT",
    "REFLECT_PROMPT",
    "REPORT_PROMPT",
    "JUDGE_PROMPT",
    "EXECUTION_PLANNER_PROMPT",
    "ERROR_ANALYZER_PROMPT",
]
