import subprocess
import os
import shutil
import re
from code_agent.state import CodeAgentState

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "repos")
MAX_WORKSPACE_NAME_LENGTH = 80
GIT_CLONE_TIMEOUT = int(os.getenv("CODE_AGENT_GIT_CLONE_TIMEOUT", "600"))
GIT_SSL_BACKEND = os.getenv("CODE_AGENT_GIT_SSL_BACKEND", "gnutls")


def _terminal_log(message: str):
    print(f"[CodeAgent] {message}", flush=True)


def _is_github_repo(url: str) -> bool:
    """检查 URL 是否是 GitHub 仓库链接（而非论文页面、博客等）。"""
    pattern = r"https?://github\.com/[\w\-\.]+/[\w\-\.]+"
    return bool(re.match(pattern, url))


def _normalize_repo_url(url: str) -> str:
    """清理 URL，去掉 tree/blob 路径、尾部斜杠等。"""
    url = url.split("/tree/")[0]
    url = url.split("/blob/")[0]
    url = url.rstrip("/")
    if not url.endswith(".git"):
        url = url + ".git"
    return url


def _safe_workspace_name(name: str) -> str:
    """Return a filesystem-safe directory name for a search topic."""
    name = re.sub(r"[\\/]+", "_", name.strip())
    name = re.sub(r"[^\w\-.\u4e00-\u9fff ]+", "_", name)
    name = re.sub(r"\s+", "_", name).strip("._ ")
    return name[:MAX_WORKSPACE_NAME_LENGTH] or "untitled"


def repo_fetcher(state: CodeAgentState) -> dict:
    repo_url = state["repo_url"]

    if not _is_github_repo(repo_url):
        return {
            "status": "failed",
            "execution_logs": [f"Not a valid GitHub repo URL: {repo_url}"],
            "repo_dir": "",
        }

    repo_url = _normalize_repo_url(repo_url)
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    workspace_name = state.get("workspace_name", "")
    workspace_dir = WORKSPACE_DIR
    if workspace_name:
        workspace_dir = os.path.join(WORKSPACE_DIR, _safe_workspace_name(workspace_name))
    repo_dir = os.path.abspath(os.path.join(workspace_dir, repo_name))

    os.makedirs(workspace_dir, exist_ok=True)

    if os.path.exists(repo_dir):
        _terminal_log(f"Removing existing repo dir: {repo_dir}")
        shutil.rmtree(repo_dir)

    try:
        _terminal_log(f"Cloning {repo_url} -> {repo_dir} (timeout={GIT_CLONE_TIMEOUT}s)")
        result = subprocess.run(
            [
                "git", "-c", f"http.sslBackend={GIT_SSL_BACKEND}",
                "clone", "--depth", "1", "--filter=blob:none", repo_url, repo_dir,
            ],
            capture_output=True, text=True, timeout=GIT_CLONE_TIMEOUT,
        )
        if result.returncode != 0:
            _terminal_log(f"git clone failed: {result.stderr[:500]}")
            return {
                "status": "failed",
                "execution_logs": [f"git clone failed: {result.stderr[:500]}"],
                "repo_dir": "",
            }
    except subprocess.TimeoutExpired:
        _terminal_log(f"git clone timed out ({GIT_CLONE_TIMEOUT}s): {repo_url}")
        return {
            "status": "failed",
            "execution_logs": [f"git clone timed out ({GIT_CLONE_TIMEOUT}s)"],
            "repo_dir": "",
        }

    _terminal_log(f"Cloned {repo_url} -> {repo_dir}")
    return {
        "repo_dir": repo_dir,
        "execution_logs": [f"Cloned {repo_url} -> {repo_dir}"],
        "status": "running",
    }
