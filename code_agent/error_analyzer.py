import json
from code_agent.state import CodeAgentState
from config import get_llm
from prompts import ERROR_ANALYZER_PROMPT


def error_analyzer(state: CodeAgentState) -> dict:
    llm = get_llm()
    plan = state.get("execution_plan", [])
    step = state.get("current_step", 0)
    cmd = plan[step] if step < len(plan) else "unknown"

    response = llm.invoke(ERROR_ANALYZER_PROMPT.format(
        command=cmd,
        error_type=state.get("error_type", "unknown"),
        error_message=state.get("error_message", "")[:2000],
        structure=state.get("repo_structure", "")[:1000],
        requirements=state.get("requirements_content", "")[:1000],
    ))
    content = response.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        analysis = json.loads(content)
    except json.JSONDecodeError:
        analysis = {
            "root_cause": "Unable to parse error",
            "fix_type": "skip_step",
            "fix_commands": [],
            "modified_files": [],
        }

    return {
        "patch": json.dumps(analysis, ensure_ascii=False),
        "execution_logs": [f"Error analysis: {analysis.get('root_cause', 'unknown')}"],
    }
