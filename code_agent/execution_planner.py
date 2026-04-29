import json
from code_agent.state import CodeAgentState
from config import get_llm
from prompts import EXECUTION_PLANNER_PROMPT


def execution_planner(state: CodeAgentState) -> dict:
    llm = get_llm()

    readme = state.get("readme_content", "")[:2000]
    requirements = state.get("requirements_content", "")[:1500]
    structure = state.get("repo_structure", "")[:1500]
    entry_file = state.get("entry_file", "main.py")

    response = llm.invoke(EXECUTION_PLANNER_PROMPT.format(
        structure=structure,
        readme=readme,
        requirements=requirements,
        entry_file=entry_file,
    ))
    content = response.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        commands = json.loads(content)
    except json.JSONDecodeError:
        commands = [
            "pip install -r requirements.txt",
            f"python {entry_file}",
        ]

    return {
        "execution_plan": commands,
        "current_step": 0,
        "execution_logs": [f"Planned {len(commands)} execution steps"],
    }
