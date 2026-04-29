import os
from code_agent.state import CodeAgentState


def code_parser(state: CodeAgentState) -> dict:
    repo_dir = state.get("repo_dir", "")
    if not repo_dir or not os.path.isdir(repo_dir):
        return {"status": "failed", "execution_logs": ["repo_dir not found"]}

    readme = ""
    for name in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
        path = os.path.join(repo_dir, name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                readme = f.read()[:5000]
            break

    requirements = ""
    for name in ["requirements.txt", "setup.py", "pyproject.toml", "environment.yml"]:
        path = os.path.join(repo_dir, name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                requirements = f.read()[:3000]
            break

    entry_file = ""
    candidates = [
        "main.py", "run.py", "demo.py", "train.py", "test.py",
        "app.py", "inference.py", "eval.py", "evaluate.py",
    ]
    for name in candidates:
        path = os.path.join(repo_dir, name)
        if os.path.exists(path):
            entry_file = name
            break

    if not entry_file:
        for root, dirs, files in os.walk(repo_dir):
            for f in files:
                if f.endswith(".py"):
                    rel = os.path.relpath(os.path.join(root, f), repo_dir)
                    entry_file = rel
                    break
            if entry_file:
                break

    structure_lines = []
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".eggs", "node_modules")]
        level = root.replace(repo_dir, "").count(os.sep)
        if level > 2:
            continue
        indent = "  " * level
        structure_lines.append(f"{indent}{os.path.basename(root)}/")
        for f in files[:15]:
            structure_lines.append(f"{indent}  {f}")

    return {
        "readme_content": readme,
        "requirements_content": requirements,
        "entry_file": entry_file,
        "repo_structure": "\n".join(structure_lines[:80]),
        "execution_logs": [f"Parsed repo: entry={entry_file}, has_readme={bool(readme)}, has_requirements={bool(requirements)}"],
    }
