import subprocess
import os
import selectors
import time
import re
import signal
from code_agent.state import CodeAgentState

TIMEOUT = int(os.getenv("CODE_AGENT_COMMAND_TIMEOUT", "3600"))
CONDA_ENV_PREFIX = "sota_repo_"
PIP_INDEX_URL = os.getenv("PIP_INDEX_URL", "https://pypi.tuna.tsinghua.edu.cn/simple")
PIP_TRUSTED_HOST = os.getenv("PIP_TRUSTED_HOST", "pypi.tuna.tsinghua.edu.cn")
PIP_DEFAULT_TIMEOUT = os.getenv("PIP_DEFAULT_TIMEOUT", "3000")
PIP_RETRIES = os.getenv("PIP_RETRIES", "10")
CODE_AGENT_BASE_ENV = os.getenv("CODE_AGENT_BASE_ENV", "")
HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
GIT_SSL_BACKEND = os.getenv("CODE_AGENT_GIT_SSL_BACKEND", "gnutls")
PYTORCH_WHEEL_INDEX = os.getenv("CODE_AGENT_PYTORCH_WHEEL_INDEX", "https://download.pytorch.org/whl/cu121")
HF_DOWNLOAD_RETRIES = int(os.getenv("CODE_AGENT_HF_DOWNLOAD_RETRIES", "3"))
HF_DOWNLOAD_RETRY_DELAY = int(os.getenv("CODE_AGENT_HF_DOWNLOAD_RETRY_DELAY", "10"))
HF_HUB_DOWNLOAD_TIMEOUT = os.getenv("HF_HUB_DOWNLOAD_TIMEOUT", "300")
HF_HUB_ETAG_TIMEOUT = os.getenv("HF_HUB_ETAG_TIMEOUT", "60")
HF_HUB_DISABLE_XET = os.getenv("HF_HUB_DISABLE_XET", "1")
CONDA_CHANNELS = [
    channel.strip()
    for channel in os.getenv(
        "CODE_AGENT_CONDA_CHANNELS",
        "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main,"
        "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r,"
        "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge",
    ).split(",")
    if channel.strip()
]
_ACTIVE_PROCESS: subprocess.Popen | None = None
_PREVIOUS_SIGINT_HANDLER = None
_SIGINT_HANDLER_INSTALLED = False


def _terminal_log(message: str):
    print(f"[CodeAgent] {message}", flush=True)


def _install_sigint_handler():
    global _PREVIOUS_SIGINT_HANDLER, _SIGINT_HANDLER_INSTALLED
    if _SIGINT_HANDLER_INSTALLED:
        return
    _PREVIOUS_SIGINT_HANDLER = signal.getsignal(signal.SIGINT)
    try:
        signal.signal(signal.SIGINT, _handle_sigint)
        _SIGINT_HANDLER_INSTALLED = True
    except ValueError:
        _terminal_log("SIGINT handler not installed because executor is not running in the main thread")


def _handle_sigint(signum, frame):
    if _ACTIVE_PROCESS and _ACTIVE_PROCESS.poll() is None:
        _terminal_log("Ctrl+C received: stopping current reproduction command only; Streamlit app stays alive")
        _terminate_process(_ACTIVE_PROCESS)
        return
    if callable(_PREVIOUS_SIGINT_HANDLER):
        _PREVIOUS_SIGINT_HANDLER(signum, frame)
        return
    raise KeyboardInterrupt


def _get_env_name(repo_dir: str) -> str:
    repo_name = os.path.basename(repo_dir)
    return f"{CONDA_ENV_PREFIX}{repo_name}"


def _ensure_conda_env(env_name: str, repo_dir: str, base_env: str = "") -> tuple[bool, str]:
    """为 repo 创建一个独立的 conda 环境，返回 (成功, 日志)。"""
    _terminal_log(f"Checking conda env: {env_name}")
    check = subprocess.run(
        ["conda", "env", "list"], capture_output=True, text=True,
    )
    if env_name in check.stdout:
        return True, f"Conda env '{env_name}' already exists"

    base_env = _select_base_env(check.stdout, env_name, base_env)
    if base_env:
        _terminal_log(f"Creating conda env: {env_name} by cloning base env '{base_env}'")
        cmd = ["conda", "create", "-n", env_name, "--clone", base_env, "-y", "-q"]
    else:
        _terminal_log(f"Creating conda env: {env_name} with python=3.10")
        cmd = ["conda", "create", "-n", env_name, "python=3.10", "-y", "-q", *_conda_channel_args()]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        return False, f"Failed to create conda env: {result.stderr[:500]}"
    if base_env:
        return True, f"Created conda env '{env_name}' from base env '{base_env}'"
    return True, f"Created conda env '{env_name}' with python=3.10"


def _select_base_env(env_list_output: str, target_env: str, requested: str = "") -> str:
    envs = _parse_conda_env_names(env_list_output)
    candidates = [
        requested,
        CODE_AGENT_BASE_ENV,
        os.getenv("CONDA_DEFAULT_ENV", ""),
        "langgraph",
    ]
    for env in candidates:
        if env and env != target_env and env in envs:
            return env
    return ""


def _parse_conda_env_names(output: str) -> set[str]:
    envs = set()
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace("*", " ").split()
        if parts:
            envs.add(parts[0])
    return envs


def _run_in_conda(cmd: str, env_name: str, cwd: str, timeout: int = TIMEOUT) -> subprocess.CompletedProcess:
    """在指定 conda 环境中执行命令。"""
    cmd = _normalize_reproduction_command(cmd)
    attempts = HF_DOWNLOAD_RETRIES if _is_hf_download_command(cmd) else 1
    last_result = None

    for attempt in range(1, attempts + 1):
        if attempts > 1:
            _terminal_log(f"Hugging Face download attempt {attempt}/{attempts}")
        try:
            result = _run_in_conda_once(cmd, env_name, cwd, timeout)
        except subprocess.TimeoutExpired:
            if attempt >= attempts:
                raise
            _terminal_log(f"Hugging Face download command timed out; retrying in {HF_DOWNLOAD_RETRY_DELAY}s")
            time.sleep(HF_DOWNLOAD_RETRY_DELAY)
            continue
        if result.returncode == 0:
            return result
        last_result = result
        if attempt >= attempts or not _is_retryable_hf_download_error(result.stderr):
            return result
        _terminal_log(f"Retryable Hugging Face download error detected; retrying in {HF_DOWNLOAD_RETRY_DELAY}s")
        time.sleep(HF_DOWNLOAD_RETRY_DELAY)

    return last_result or subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")


def _run_in_conda_once(cmd: str, env_name: str, cwd: str, timeout: int = TIMEOUT) -> subprocess.CompletedProcess:
    mirror_env = (
        f"PIP_INDEX_URL={_shell_quote(PIP_INDEX_URL)} "
        f"PIP_TRUSTED_HOST={_shell_quote(PIP_TRUSTED_HOST)} "
        f"PIP_DEFAULT_TIMEOUT={_shell_quote(PIP_DEFAULT_TIMEOUT)} "
        f"PIP_RETRIES={_shell_quote(PIP_RETRIES)} "
        f"HF_ENDPOINT={_shell_quote(HF_ENDPOINT)} "
        f"HUGGINGFACE_HUB_ENDPOINT={_shell_quote(HF_ENDPOINT)} "
        f"HF_HUB_DOWNLOAD_TIMEOUT={_shell_quote(HF_HUB_DOWNLOAD_TIMEOUT)} "
        f"HF_HUB_ETAG_TIMEOUT={_shell_quote(HF_HUB_ETAG_TIMEOUT)} "
        f"HF_HUB_DISABLE_XET={_shell_quote(HF_HUB_DISABLE_XET)} "
    )
    wrapped = f"conda run --no-capture-output -n {env_name} bash -c {_shell_quote(mirror_env + cmd)}"
    _terminal_log(f"Using pip mirror: {PIP_INDEX_URL} (trusted_host={PIP_TRUSTED_HOST}, pip_timeout={PIP_DEFAULT_TIMEOUT}s, retries={PIP_RETRIES})")
    _terminal_log(f"Using Hugging Face mirror: {HF_ENDPOINT}")
    _terminal_log(f"Using conda mirrors: {', '.join(CONDA_CHANNELS)}")
    _terminal_log(f"cwd={cwd}")
    _terminal_log(f"run: {wrapped}")

    process = subprocess.Popen(
        wrapped,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd,
        start_new_session=True,
    )
    global _ACTIVE_PROCESS
    _ACTIVE_PROCESS = process
    output_lines = []
    start = time.monotonic()
    selector = selectors.DefaultSelector()
    assert process.stdout is not None
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while process.poll() is None:
            if time.monotonic() - start > timeout:
                _terminate_process(process)
                raise subprocess.TimeoutExpired(wrapped, timeout)
            for key, _events in selector.select(timeout=0.2):
                line = key.fileobj.readline()
                if line:
                    output_lines.append(line)
                    print(line, end="", flush=True)

        for line in process.stdout:
            output_lines.append(line)
            print(line, end="", flush=True)
        returncode = process.returncode
    finally:
        if _ACTIVE_PROCESS is process:
            _ACTIVE_PROCESS = None
        selector.close()

    output = "".join(output_lines)
    return subprocess.CompletedProcess(
        args=wrapped,
        returncode=returncode,
        stdout=output,
        stderr=output,
    )


def _is_hf_download_command(cmd: str) -> bool:
    cmd_lower = cmd.lower()
    return (
        "huggingface-cli download" in cmd_lower
        or "hf download" in cmd_lower
        or "snapshot_download" in cmd_lower
        or "hf_hub_download" in cmd_lower
        or "from_pretrained" in cmd_lower
        or "huggingface.co/" in cmd_lower
        or HF_ENDPOINT.lower().rstrip("/") in cmd_lower
    )


def _is_retryable_hf_download_error(output: str) -> bool:
    output_lower = output.lower()
    retryable_markers = [
        "read timed out",
        "readtimeout",
        "httpsconnectionpool",
        "connection aborted",
        "connection reset",
        "temporarily unavailable",
        "incomplete read",
        "chunkedencodingerror",
        "cas-bridge.xethub.hf.co",
        "xethub.hf.co",
    ]
    return any(marker in output_lower for marker in retryable_markers)


def _shell_quote(s: str) -> str:
    """安全引用 shell 参数。"""
    return "'" + s.replace("'", "'\\''") + "'"


def _terminate_process(process: subprocess.Popen):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except Exception:
            process.kill()


def _normalize_reproduction_command(cmd: str) -> str:
    cmd = _normalize_huggingface_command(cmd)
    cmd = _normalize_git_command(cmd)
    cmd = _normalize_pytorch_conda_command(cmd)
    cmd = _normalize_conda_command(cmd)
    cmd = _normalize_pip_command(cmd)
    return cmd


def _normalize_huggingface_command(cmd: str) -> str:
    """Force common Hugging Face downloads through the configured mirror."""
    return cmd.replace("https://huggingface.co/", f"{HF_ENDPOINT.rstrip('/')}/")


def _normalize_git_command(cmd: str) -> str:
    """Use this machine's supported Git SSL backend for reproduction clones."""
    if not cmd.strip().lower().startswith("git clone "):
        return cmd
    return re.sub(
        r"^\s*git\s+clone\b",
        f"git -c http.sslBackend={GIT_SSL_BACKEND} clone",
        cmd,
        count=1,
        flags=re.IGNORECASE,
    )


def _normalize_conda_command(cmd: str) -> str:
    """Force conda package operations through repo-configured mirror channels."""
    if not _is_conda_package_command(cmd):
        return cmd

    cleaned = cmd
    patterns = [
        r"\s+--override-channels",
        r"\s+(?:-c|--channel)(?:=|\s+)\S+",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned)

    return f"{cleaned.strip()} {_conda_channel_flags()}"


def _normalize_pytorch_conda_command(cmd: str) -> str:
    """Avoid fragile conda CUDA packages that are often missing from mirrors."""
    cmd_lower = cmd.strip().lower()
    if not cmd_lower.startswith(("conda install ", "conda create ")):
        return cmd
    if "pytorch-cuda" not in cmd_lower:
        return cmd

    packages = _extract_torch_pip_packages(cmd)
    index_url = _pytorch_index_from_command(cmd) or PYTORCH_WHEEL_INDEX
    return f"pip install {' '.join(packages)} --index-url {index_url}"


def _extract_torch_pip_packages(cmd: str) -> list[str]:
    packages = []
    for token in re.findall(r"[^\s]+", cmd):
        normalized = token.strip().strip("'\"")
        lowered = normalized.lower()
        if lowered.startswith("pytorch=") or lowered.startswith("pytorch=="):
            version = re.split(r"={1,2}", normalized, maxsplit=1)[1]
            packages.append(f"torch=={version}")
        elif lowered == "pytorch":
            packages.append("torch")
        elif lowered.startswith(("torch=", "torch==")):
            version = re.split(r"={1,2}", normalized, maxsplit=1)[1]
            packages.append(f"torch=={version}")
        elif lowered in {"torch", "torchvision", "torchaudio"}:
            packages.append(lowered)
        elif lowered.startswith(("torchvision=", "torchvision==", "torchaudio=", "torchaudio==")):
            name, version = re.split(r"={1,2}", normalized, maxsplit=1)
            packages.append(f"{name}=={version}")

    if not any(pkg == "torch" or pkg.startswith("torch==") for pkg in packages):
        packages.insert(0, "torch")
    if not any(pkg.startswith("torchvision") for pkg in packages):
        packages.append("torchvision")
    return _dedupe_preserve_order(packages)


def _pytorch_index_from_command(cmd: str) -> str:
    match = re.search(r"pytorch-cuda\s*=\s*([0-9]+)(?:\.([0-9]+))?", cmd, flags=re.IGNORECASE)
    if not match:
        return ""
    major = match.group(1)
    minor = match.group(2) or "0"
    return f"https://download.pytorch.org/whl/cu{major}{minor}"


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _is_conda_package_command(cmd: str) -> bool:
    cmd_lower = cmd.strip().lower()
    return (
        cmd_lower.startswith("conda install ")
        or cmd_lower.startswith("conda create ")
        or cmd_lower.startswith("conda env create ")
        or cmd_lower.startswith("conda env update ")
    )


def _conda_channel_flags() -> str:
    return " ".join(_shell_quote(part) for part in _conda_channel_args())


def _conda_channel_args() -> list[str]:
    args = ["--override-channels"]
    for channel in CONDA_CHANNELS:
        args.extend(["-c", channel])
    return args


def _normalize_pip_command(cmd: str) -> str:
    """Force pip install commands through the configured mirror and pip timeout."""
    if not _is_pip_install_command(cmd):
        return cmd

    is_torch_install = _is_torch_pip_install_command(cmd)
    cleaned = cmd
    patterns = [
        r"\s+--default-timeout(?:=|\s+)\S+",
        r"\s+--timeout(?:=|\s+)\S+",
        r"\s+--retries(?:=|\s+)\S+",
        r"\s+(?:-i|--index-url)(?:=|\s+)\S+",
        r"\s+--trusted-host(?:=|\s+)\S+",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned)

    index_url = _existing_pip_index_url(cmd) if is_torch_install else ""
    if is_torch_install and not index_url:
        index_url = PYTORCH_WHEEL_INDEX

    normalized = f"{cleaned.strip()} --default-timeout={PIP_DEFAULT_TIMEOUT} --retries={PIP_RETRIES}"
    if index_url:
        return f"{normalized} --index-url {index_url}"
    return f"{normalized} --index-url {PIP_INDEX_URL} --trusted-host {PIP_TRUSTED_HOST}"


def _is_pip_install_command(cmd: str) -> bool:
    cmd_lower = cmd.strip().lower()
    return (
        cmd_lower.startswith("pip install ")
        or cmd_lower.startswith("python -m pip install ")
        or cmd_lower.startswith("python3 -m pip install ")
    )


def _is_torch_pip_install_command(cmd: str) -> bool:
    if not _is_pip_install_command(cmd):
        return False
    tokens = {token.strip().strip("'\"").split("==", 1)[0].lower() for token in re.findall(r"[^\s]+", cmd)}
    return bool(tokens & {"torch", "torchvision", "torchaudio"})


def _existing_pip_index_url(cmd: str) -> str:
    match = re.search(r"(?:-i|--index-url)(?:=|\s+)(\S+)", cmd)
    return match.group(1) if match else ""


def executor(state: CodeAgentState) -> dict:
    _install_sigint_handler()
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
        ok, log = _ensure_conda_env(env_name, repo_dir, state.get("base_env", ""))
        _terminal_log(log)
        if not ok:
            return {
                "status": "failed",
                "execution_logs": [log],
                "reward": -0.5,
            }

    cmd = plan[step]
    logs = []
    _terminal_log(f"Step {step}/{len(plan)} command timeout={TIMEOUT}s: {cmd}")

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
        timeout_log = f"[Step {step}] TIMEOUT ({TIMEOUT}s): {cmd}"
        _terminal_log(timeout_log)
        logs.append(timeout_log)
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
    if "typeerror" in stderr_lower:
        return "type_error"
    if "packagesnotfounderror" in stderr_lower or "package not found" in stderr_lower or "could not solve" in stderr_lower:
        return "dependency_solver_error"
    if _is_retryable_hf_download_error(stderr):
        return "hf_download_timeout"
    if "cuda" in stderr_lower or "gpu" in stderr_lower:
        return "gpu_error"
    if "permission" in stderr_lower:
        return "permission_error"
    if "memory" in stderr_lower or "oom" in stderr_lower:
        return "memory_error"
    return "runtime_error"
