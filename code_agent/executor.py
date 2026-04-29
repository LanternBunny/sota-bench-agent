import subprocess
import os
from code_agent.state import CodeAgentState

TIMEOUT = 180
CONDA_ENV_PREFIX = "sota_repo_"


def _get_env_name(repo_dir: str) -> str:
    repo_name = os.path.basename(repo_dir)
    return f"{CONDA_ENV_PREFIX}{repo_name}"


def _ensure_conda_env(env_name: str, repo_dir: str) -> tuple[bool, str]:
    """为 repo 创建一个独立的 conda 环境，返回 (成功, 日志)。"""
    check = subprocess.run(
        ["conda", "env", "list"], capture_output=True, text=True,
    )
    if env_name in check.stdout:
        return True, f"Conda env '{env_name}' already exists"

    result = subprocess.run(
        ["conda", "create", "-n", env_name, "python=3.10", "-y", "-q"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        return False, f"Failed to create conda env: {result.stderr[:500]}"
    return True, f"Created conda env '{env_name}'"


def _run_in_conda(cmd: str, env_name: str, cwd: str, timeout: int = TIMEOUT) -> subprocess.CompletedProcess:
    """在指定 conda 环境中执行命令。"""
    wrapped = f"conda run --no-capture-output -n {env_name} bash -c {_shell_quote(cmd)}"
    return subprocess.run(
        wrapped,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )


def _shell_quote(s: str) -> str:
    """安全引用 shell 参数。"""
    return "'" + s.replace("'", "'\\''") + "'"


def executor(state: CodeAgentState) -> dict:
    plan = state.get("execution_plan", [])
    step = state.get("current_step", 0)
    repo_dir = state.get("repo_dir", "")

    if step >= len(plan):
        return {
            "status": "success",
            "execution_logs": ["All steps completed successfully"],
            "reward": 1.0,
        }

    if not repo_dir or not os.path.isdir(repo_dir):
        return {
            "status": "failed",
            "execution_logs": [f"repo_dir invalid: '{repo_dir}'"],
            "reward": -1.0,
        }

    env_name = _get_env_name(repo_dir)

    if step == 0:
        ok, log = _ensure_conda_env(env_name, repo_dir)
        if not ok:
            return {
                "status": "failed",
                "execution_logs": [log],
                "reward": -0.5,
            }

    cmd = plan[step]
    logs = []

    try:
        result = _run_in_conda(cmd, env_name, repo_dir)

        stdout = result.stdout[-2000:] if result.stdout else ""
        stderr = result.stderr[-2000:] if result.stderr else ""

        if result.returncode == 0:
            logs.append(f"[Step {step}] SUCCESS: {cmd}")
            if stdout:
                logs.append(f"stdout: {stdout[:500]}")
            return {
                "current_step": step + 1,
                "execution_logs": logs,
                "error_message": "",
                "error_type": "",
                "status": "running",
            }
        else:
            logs.append(f"[Step {step}] FAILED (exit {result.returncode}): {cmd}")
            logs.append(f"stderr: {stderr[:1000]}")
            return {
                "execution_logs": logs,
                "error_message": stderr[:2000],
                "error_type": _classify_error(stderr),
                "status": "error",
            }

    except subprocess.TimeoutExpired:
        logs.append(f"[Step {step}] TIMEOUT ({TIMEOUT}s): {cmd}")
        return {
            "execution_logs": logs,
            "error_message": f"Command timed out after {TIMEOUT}s",
            "error_type": "timeout",
            "status": "error",
        }
    except Exception as e:
        logs.append(f"[Step {step}] EXCEPTION: {e}")
        return {
            "execution_logs": logs,
            "error_message": str(e),
            "error_type": "exception",
            "status": "error",
        }


def cleanup_conda_env(repo_dir: str):
    """清理 repo 对应的 conda 临时环境。"""
    env_name = _get_env_name(repo_dir)
    subprocess.run(
        ["conda", "env", "remove", "-n", env_name, "-y", "-q"],
        capture_output=True, text=True, timeout=60,
    )


def _classify_error(stderr: str) -> str:
    stderr_lower = stderr.lower()
    if "modulenotfounderror" in stderr_lower or "no module named" in stderr_lower:
        return "missing_module"
    if "importerror" in stderr_lower:
        return "import_error"
    if "filenotfounderror" in stderr_lower:
        return "file_not_found"
    if "syntaxerror" in stderr_lower:
        return "syntax_error"
    if "cuda" in stderr_lower or "gpu" in stderr_lower:
        return "gpu_error"
    if "permission" in stderr_lower:
        return "permission_error"
    if "memory" in stderr_lower or "oom" in stderr_lower:
        return "memory_error"
    return "runtime_error"
