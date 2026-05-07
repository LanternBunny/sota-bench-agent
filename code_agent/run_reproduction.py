import argparse
import json
import os
from datetime import datetime

from code_agent.graph import compile_code_agent
from config import MAX_CODE_FIX_LOOPS


def _write_reproduction_report(state: dict, args) -> str:
    repo_dir = state.get("repo_dir", "")
    if not repo_dir:
        return ""

    os.makedirs(repo_dir, exist_ok=True)
    report_path = os.path.join(repo_dir, "reproduction_report.md")
    logs = state.get("execution_logs", [])
    if isinstance(logs, str):
        logs = [logs]
    plan = state.get("execution_plan", [])

    content = [
        "# 代码复现报告",
        "",
        f"- 仓库：{args.repo_url}",
        f"- 复现主题目录：{args.workspace_name}",
        f"- 基础 conda 环境：{args.base_env or 'auto'}",
        f"- 复现状态：{state.get('status', 'unknown')}",
        f"- 奖励分数：{state.get('reward', 0.0)}",
        f"- 仓库目录：{repo_dir}",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 执行计划",
        "",
    ]
    if plan:
        content.extend(f"{i + 1}. `{cmd}`" for i, cmd in enumerate(plan))
    else:
        content.append("未生成可执行计划。")

    content.extend([
        "",
        "## 关键信息",
        "",
        f"- 入口文件：{state.get('entry_file', 'unknown')}",
        f"- 当前步骤：{state.get('current_step', 0)}",
        f"- 修复次数：{state.get('fix_count', 0)} / {state.get('max_fixes', MAX_CODE_FIX_LOOPS)}",
        f"- 错误类型：{state.get('error_type', 'none')}",
        f"- 错误信息：{state.get('error_message', 'none')}",
        "",
        "## 执行日志",
        "",
        "```text",
        "\n".join(str(log) for log in logs),
        "```",
        "",
    ])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Run code reproduction in a separate process.")
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--workspace-name", default="manual_reproduction")
    parser.add_argument("--base-env", default="")
    args = parser.parse_args()

    print(f"[CodeAgentJob] repo_url={args.repo_url}", flush=True)
    print(f"[CodeAgentJob] workspace_name={args.workspace_name}", flush=True)
    print(f"[CodeAgentJob] base_env={args.base_env or 'auto'}", flush=True)

    app = compile_code_agent()
    final_status = "unknown"
    state = {}
    for event in app.stream(
        {
            "repo_url": args.repo_url,
            "workspace_name": args.workspace_name,
            "base_env": args.base_env,
            "fix_count": 0,
            "max_fixes": MAX_CODE_FIX_LOOPS,
            "status": "pending",
        },
        stream_mode="updates",
    ):
        for node_name, node_output in event.items():
            for key, value in node_output.items():
                if key == "execution_logs" and key in state:
                    old_logs = state.get(key, [])
                    if isinstance(old_logs, str):
                        old_logs = [old_logs]
                    new_logs = value if isinstance(value, list) else [value]
                    state[key] = old_logs + new_logs
                else:
                    state[key] = value
            logs = node_output.get("execution_logs", [])
            if isinstance(logs, str):
                logs = [logs]
            print(f"[CodeAgentJob] node={node_name}", flush=True)
            for log in logs:
                print(log, flush=True)
            if node_name in ("finalize_success", "finalize_failure"):
                final_status = node_output.get("status", "unknown")
                print("[CodeAgentJob] final=" + json.dumps(node_output, ensure_ascii=False), flush=True)

    report_path = _write_reproduction_report(state, args)
    if report_path:
        print(f"[CodeAgentJob] reproduction_report={report_path}", flush=True)
    print(f"[CodeAgentJob] finished status={final_status}", flush=True)


if __name__ == "__main__":
    main()
