import json
import os
from code_agent.state import CodeAgentState
from code_agent.executor import TIMEOUT, _get_env_name, _run_in_conda, _terminal_log


def _run_fix_command(cmd: str, repo_dir: str):
    env_name = _get_env_name(repo_dir)
    return _run_in_conda(cmd, env_name, repo_dir, timeout=TIMEOUT)


def patch_generator(state: CodeAgentState) -> dict:
    patch_str = state.get("patch", "{}")
    repo_dir = state.get("repo_dir", "")
    fix_count = state.get("fix_count", 0)
    plan = list(state.get("execution_plan", []))
    step = state.get("current_step", 0)

    try:
        patch = json.loads(patch_str)
    except json.JSONDecodeError:
        return {
            "fix_count": fix_count + 1,
            "status": "running",
            "execution_logs": ["Failed to parse patch, skipping step"],
            "current_step": step + 1,
        }

    logs = []
    fix_type = patch.get("fix_type", "skip_step")

    if fix_type == "skip_step":
        logs.append("Skipping failed step")
        _terminal_log("Skipping failed step")
        return {
            "fix_count": fix_count + 1,
            "current_step": step + 1,
            "status": "running",
            "execution_logs": logs,
        }

    if fix_type == "change_command" and patch.get("fix_commands"):
        new_cmd = patch["fix_commands"][0]
        if step < len(plan):
            logs.append(f"Replacing command: {plan[step]} -> {new_cmd}")
            _terminal_log(f"Replacing command: {plan[step]} -> {new_cmd}")
            plan[step] = new_cmd
        return {
            "fix_count": fix_count + 1,
            "execution_plan": plan,
            "status": "running",
            "execution_logs": logs,
        }

    if fix_type == "install_dep":
        for cmd in patch.get("fix_commands", []):
            try:
                result = _run_fix_command(cmd, repo_dir)
                if result.returncode == 0:
                    logs.append(f"Fix command OK in conda env: {cmd}")
                    _terminal_log(f"Fix command OK in conda env: {cmd}")
                else:
                    logs.append(f"Fix command failed: {cmd} -> {result.stderr[:200]}")
                    _terminal_log(f"Fix command failed: {cmd} -> {result.stderr[:200]}")
            except Exception as e:
                logs.append(f"Fix command error: {cmd} -> {e}")
                _terminal_log(f"Fix command error: {cmd} -> {e}")
        return {
            "fix_count": fix_count + 1,
            "status": "running",
            "execution_logs": logs,
        }

    for cmd in patch.get("fix_commands", []):
        try:
            result = _run_fix_command(cmd, repo_dir)
            if result.returncode == 0:
                logs.append(f"Fix command OK in conda env: {cmd}")
                _terminal_log(f"Fix command OK in conda env: {cmd}")
            else:
                logs.append(f"Fix command failed: {cmd} -> {result.stderr[:200]}")
                _terminal_log(f"Fix command failed: {cmd} -> {result.stderr[:200]}")
        except Exception as e:
            logs.append(f"Fix command error: {cmd} -> {e}")
            _terminal_log(f"Fix command error: {cmd} -> {e}")

    for mod in patch.get("modified_files", []):
        filepath = os.path.join(repo_dir, mod.get("path", ""))
        old = mod.get("old", "")
        new = mod.get("new", "")
        if os.path.exists(filepath) and old:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if old in content:
                    content = content.replace(old, new, 1)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    logs.append(f"Patched: {mod['path']}")
                    _terminal_log(f"Patched: {mod['path']}")
                else:
                    logs.append(f"Pattern not found in {mod['path']}, skipping")
                    _terminal_log(f"Pattern not found in {mod['path']}, skipping")
            except Exception as e:
                logs.append(f"Patch error on {mod['path']}: {e}")
                _terminal_log(f"Patch error on {mod['path']}: {e}")

    return {
        "fix_count": fix_count + 1,
        "status": "running",
        "execution_logs": logs,
    }
