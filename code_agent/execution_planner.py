import json
from code_agent.state import CodeAgentState
from config import get_llm
from prompts import EXECUTION_PLANNER_PROMPT


def _terminal_log(message: str):
    print(f"[CodeAgent] {message}", flush=True)


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

    structure_lower = structure.lower()

    try:
        commands = json.loads(content)
    except json.JSONDecodeError:
        commands = []
        if "requirements.txt" in structure_lower:
            commands.append("pip install -r requirements.txt")
        elif "environment.yml" in structure_lower:
            commands.append("conda env update -f environment.yml")
        elif "setup.py" in structure_lower or "pyproject.toml" in structure_lower:
            commands.append("pip install -e .")
        if entry_file:
            commands.append(f"python {entry_file}")

    commands = [
        cmd.strip()
        for cmd in commands
        if isinstance(cmd, str) and _is_valid_command(cmd, structure_lower, entry_file)
    ]

    if not commands:
        _terminal_log("No executable reproduction plan could be inferred")
        return {
            "status": "failed",
            "execution_plan": [],
            "current_step": 0,
            "execution_logs": ["No executable reproduction plan could be inferred"],
        }

    _terminal_log(f"Planned {len(commands)} execution steps")
    for i, cmd in enumerate(commands):
        _terminal_log(f"plan[{i}]: {cmd}")

    return {
        "execution_plan": commands,
        "current_step": 0,
        "execution_logs": [f"Planned {len(commands)} execution steps"],
    }


def _is_valid_command(cmd: str, structure_lower: str, entry_file: str) -> bool:
    cmd = cmd.strip()
    cmd_lower = cmd.lower()
    if not cmd or cmd_lower in {"python", "python3"}:
        return False
    if cmd_lower.startswith(("conda create ", "conda activate ", "conda deactivate", "conda init")):
        return False
    if "/path/to/" in cmd_lower:
        return False
    if "requirements.txt" in cmd_lower and "requirements.txt" not in structure_lower:
        return False
    if "pip install -e" in cmd_lower and "setup.py" not in structure_lower and "pyproject.toml" not in structure_lower:
        return False
    if entry_file:
        return True
    if cmd_lower.startswith("python ") or cmd_lower.startswith("python3 "):
        return False
    return True
