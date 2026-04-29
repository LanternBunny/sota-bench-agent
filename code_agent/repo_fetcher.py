import subprocess
import os
import shutil
import re
from code_agent.state import CodeAgentState

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "repos")


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
    repo_dir = os.path.abspath(os.path.join(WORKSPACE_DIR, repo_name))

    os.makedirs(WORKSPACE_DIR, exist_ok=True)

    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, repo_dir],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return {
                "status": "failed",
                "execution_logs": [f"git clone failed: {result.stderr[:500]}"],
                "repo_dir": "",
            }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "execution_logs": ["git clone timed out (120s)"],
            "repo_dir": "",
        }

    return {
        "repo_dir": repo_dir,
        "execution_logs": [f"Cloned {repo_url} -> {repo_dir}"],
        "status": "running",
    }
