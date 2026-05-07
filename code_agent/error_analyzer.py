import json
import os
import re
from code_agent.state import CodeAgentState
from config import get_llm
from prompts import ERROR_ANALYZER_PROMPT


def error_analyzer(state: CodeAgentState) -> dict:
    llm = get_llm()
    plan = state.get("execution_plan", [])
    step = state.get("current_step", 0)
    cmd = plan[step] if step < len(plan) else "unknown"
    deterministic = _deterministic_analysis(cmd, state.get("error_message", ""))
    if deterministic:
        return {
            "patch": json.dumps(deterministic, ensure_ascii=False),
            "execution_logs": [f"Error analysis: {deterministic['root_cause']}"],
        }

    response = llm.invoke(ERROR_ANALYZER_PROMPT.format(
        command=cmd,
        error_type=state.get("error_type", "unknown"),
        error_message=state.get("error_message", "")[:2000],
        structure=state.get("repo_structure", "")[:1000],
        requirements=state.get("requirements_content", "")[:1000],
        source_context=_extract_source_context(cmd, state.get("repo_dir", "")),
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


def _deterministic_analysis(command: str, error_message: str) -> dict:
    combined = f"{command}\n{error_message}".lower()
    if "pytorch-cuda" in combined and (
        "packagesnotfounderror" in combined
        or "package not found" in combined
        or "could not solve" in combined
        or "not available from current channels" in combined
    ):
        index_url = _pytorch_index_from_text(combined)
        return {
            "root_cause": "当前 conda 镜像/channel 无法提供 pytorch-cuda，改用 PyTorch 官方 wheel index 安装 CUDA wheel。",
            "fix_type": "change_command",
            "fix_commands": [f"pip install torch torchvision torchaudio --index-url {index_url}"],
            "modified_files": [],
        }
    return {}


def _pytorch_index_from_text(text: str) -> str:
    match = re.search(r"pytorch-cuda\s*=\s*([0-9]+)(?:\.([0-9]+))?", text)
    if not match:
        return "https://download.pytorch.org/whl/cu121"
    return f"https://download.pytorch.org/whl/cu{match.group(1)}{match.group(2) or '0'}"


def _extract_source_context(command: str, repo_dir: str) -> str:
    """Return local function signature context for `python -c` import calls."""
    if not repo_dir or not os.path.isdir(repo_dir):
        return ""

    match = re.search(r"from\s+([\w.]+)\s+import\s+([\w_]+)", command)
    if not match:
        return ""

    module, func_name = match.groups()
    module_path = os.path.join(repo_dir, *module.split(".")) + ".py"
    if not os.path.exists(module_path):
        return ""

    try:
        with open(module_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return ""

    def_pattern = re.compile(rf"^def\s+{re.escape(func_name)}\s*\(")
    start = next((i for i, line in enumerate(lines) if def_pattern.match(line)), None)
    if start is None:
        return ""

    snippet = lines[start:start + 80]
    return f"# {os.path.relpath(module_path, repo_dir)}\n" + "".join(snippet)[:4000]
