import streamlit as st
import json
import time
import os
import logging
import subprocess
import signal
import shlex
import sys
from datetime import datetime
from graph import compile_graph
from agents.info_extractor import _is_probable_code_repo
from evaluation.visualize import plot_reward_curve, plot_experience_trend

# ---------------------------------------------------------------------------
# Terminal logging — all agent events print to the terminal running streamlit
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sota_bench")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPORT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "reports")
REPRO_LOG_DIR = os.path.join(os.path.dirname(__file__), "outputs", "reproduction_logs")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "outputs", "history.json")
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(REPRO_LOG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------
def load_history() -> list[dict]:
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(history: list[dict]):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_history_entry(topic: str, paper_count: int, loop_count: int,
                      avg_reward: float, report_path: str, papers: list[dict]):
    history = load_history()
    history.insert(0, {
        "topic": topic,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "paper_count": paper_count,
        "loop_count": loop_count,
        "avg_reward": round(avg_reward, 3),
        "report_path": report_path,
        "papers": papers,
        "code_candidates": get_papers_with_code(papers),
    })
    history = history[:50]
    save_history(history)


def list_conda_envs() -> list[str]:
    try:
        result = subprocess.run(
            ["conda", "env", "list"], capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    envs = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace("*", " ").split()
        if parts:
            envs.append(parts[0])
    return envs


def get_papers_with_code(papers: list[dict]) -> list[dict]:
    return [
        p for p in papers
        if p.get("code_url") not in (None, "", "unknown")
        and "github.com" in p.get("code_url", "")
        and _is_probable_code_repo(p.get("code_url", ""))
    ]


def candidates_to_papers(candidates: list[dict]) -> list[dict]:
    return [
        {
            "title": c.get("title", "Unknown"),
            "code_url": c.get("code_url", ""),
            "method": c.get("method", ""),
            "dataset": c.get("dataset", ""),
            "relevance_score": c.get("relevance_score", 0),
        }
        for c in candidates
        if c.get("code_url")
    ]


def start_reproduction_job(repo_url: str, workspace_name: str, base_env: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = workspace_name.replace(" ", "_").replace("/", "_")[:50] or "manual_reproduction"
    log_path = os.path.join(REPRO_LOG_DIR, f"repro_{safe_name}_{timestamp}.log")
    cmd = [
        sys.executable, "-m", "code_agent.run_reproduction",
        "--repo-url", repo_url,
        "--workspace-name", workspace_name,
    ]
    if base_env:
        cmd.extend(["--base-env", base_env])
    shell_cmd = " ".join(shlex.quote(part) for part in cmd)
    wrapped = f"{shell_cmd} 2>&1 | tee -a {shlex.quote(log_path)}"
    process = subprocess.Popen(
        ["bash", "-lc", wrapped],
        cwd=os.path.dirname(__file__),
        start_new_session=True,
    )
    st.session_state["repro_job"] = {
        "pid": process.pid,
        "repo_url": repo_url,
        "workspace_name": workspace_name,
        "base_env": base_env,
        "log_path": log_path,
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    logger.info(f"后台代码复现已启动 PID={process.pid}, log={log_path}")


def is_reproduction_job_active(job: dict) -> bool:
    if not job or not job.get("pid"):
        return False
    log_text = read_reproduction_log(job.get("log_path", ""), max_chars=4000)
    if "[CodeAgentJob] finished status=" in log_text:
        return False
    try:
        os.kill(job["pid"], 0)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        return False


def stop_reproduction_job():
    job = st.session_state.get("repro_job") or {}
    pid = job.get("pid")
    if not pid:
        return False
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except Exception as exc:
        logger.warning(f"停止复现失败: {exc}")
        return False
    st.session_state["repro_job"] = {}
    return True


def read_reproduction_log(log_path: str, max_chars: int = 12000) -> str:
    if not log_path or not os.path.exists(log_path):
        return ""
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()
    return data[-max_chars:]


def extract_reproduction_report_path(log_text: str) -> str:
    marker = "[CodeAgentJob] reproduction_report="
    for line in reversed(log_text.splitlines()):
        if line.startswith(marker):
            return line[len(marker):].strip()
    return ""


# ---------------------------------------------------------------------------
# Page config & custom CSS
# ---------------------------------------------------------------------------
st.set_page_config(page_title="SOTA-Bench Agent", page_icon="🔬", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    div[data-testid="stMetric"] {
        background: #f8f9fa; border-radius: 8px; padding: 12px 16px;
        border-left: 4px solid #4A90D9;
    }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 8px; }
    .history-card {
        background: #f8f9fa; border-radius: 8px; padding: 12px 16px;
        margin-bottom: 8px; border-left: 3px solid #6c757d;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — config + history
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 配置")
    use_best_of_n = st.checkbox("启用 Best-of-N 采样", value=True)
    auto_reproduce_code = st.checkbox(
        "自动复现 Top 仓库",
        value=False,
        help="调研完成后让主图把最高相关度 GitHub 仓库交给 Code Agent；关闭时只收集候选仓库供人工选择。",
    )
    conda_envs = list_conda_envs()
    preferred_envs = [e for e in [os.getenv("CONDA_DEFAULT_ENV", ""), "langgraph"] if e in conda_envs]
    env_options = ["自动选择"] + preferred_envs + [e for e in conda_envs if e not in preferred_envs]
    base_env_choice = st.selectbox(
        "复现基础 conda 环境",
        options=env_options or ["自动选择"],
        help="创建每个仓库的隔离环境时，优先 clone 这里选择的基础环境，再安装该仓库依赖。",
    )
    selected_base_env = "" if base_env_choice == "自动选择" else base_env_choice
    st.divider()

    st.header("📜 历史记录")
    history = load_history()
    if history:
        st.caption("点击“打开报告”会把历史报告加载到主页面，方便继续人工选择代码复现。")
        for i, entry in enumerate(history[:10]):
            report_path = entry.get("report_path", "")
            label = f"{entry['topic'][:30]}  ({entry['time']})"
            with st.expander(label):
                st.caption(f"论文 {entry['paper_count']} 篇  ·  轮次 {entry.get('loop_count', '?')}  ·  奖励 {entry['avg_reward']}")
                if report_path and os.path.exists(report_path):
                    with open(report_path, "r", encoding="utf-8") as f:
                        report_content = f.read()
                    if st.button("打开报告", key=f"hist_open_{i}"):
                        st.session_state["last_report"] = report_content
                        st.session_state["last_topic"] = entry.get("topic", "")
                        st.session_state["last_papers"] = entry.get("papers", [])
                        st.session_state["papers_with_code"] = entry.get("code_candidates") or get_papers_with_code(entry.get("papers", []))
                        st.rerun()
                    st.download_button(
                        "📥 下载报告", data=report_content,
                        file_name=os.path.basename(report_path),
                        mime="text/markdown",
                        key=f"hist_dl_{i}",
                    )
                else:
                    st.caption("报告文件不存在")
        if len(history) > 10:
            st.caption(f"还有 {len(history) - 10} 条更早的记录")
    else:
        st.caption("暂无历史记录，完成一次调研后会自动保存。")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("🔬 SOTA-Bench Agent")
st.caption("先完成论文调研报告，再由人工反馈决定是否复现以及复现哪个仓库。")

topic = st.text_input(
    "输入研究主题",
    placeholder="例如：multimodal hallucination detection",
)

if "papers_with_code" not in st.session_state:
    st.session_state["papers_with_code"] = []
if "last_topic" not in st.session_state:
    st.session_state["last_topic"] = ""
if "last_report" not in st.session_state:
    st.session_state["last_report"] = ""
if "last_papers" not in st.session_state:
    st.session_state["last_papers"] = []
if "repro_job" not in st.session_state:
    st.session_state["repro_job"] = {}

action_col1, action_col2, action_col3 = st.columns([1, 1, 2])
start_research = action_col1.button("开始调研", type="primary", disabled=not topic)
if action_col2.button("清空当前结果", type="secondary"):
    st.session_state["papers_with_code"] = []
    st.session_state["last_report"] = ""
    st.session_state["last_papers"] = []
    st.session_state["last_topic"] = ""
    st.rerun()
action_col3.caption("复现任务已改为后台进程；停止复现请使用页面里的停止按钮，不要 Ctrl+C Streamlit 主进程。")

if st.session_state.get("last_report") and not start_research:
    st.divider()
    st.header("📊 当前/历史调研报告")
    if st.session_state.get("last_topic"):
        st.caption(f"主题：{st.session_state['last_topic']}")
    st.markdown(st.session_state["last_report"])


# ---------------------------------------------------------------------------
# Helper: log to both terminal and streamlit status
# ---------------------------------------------------------------------------
def log_event(msg: str, st_status_writer=None, level="info"):
    getattr(logger, level)(msg)
    if st_status_writer:
        st_status_writer(msg)


# ---------------------------------------------------------------------------
# Research flow
# ---------------------------------------------------------------------------
if start_research:
    st.session_state["last_topic"] = topic
    logger.info(f"{'='*60}")
    logger.info(f"开始调研: {topic}")
    logger.info(f"{'='*60}")

    app = compile_graph(use_best_of_n=use_best_of_n)
    config = {"configurable": {"thread_id": f"st-{int(time.time())}"}}

    with st.status("Agent 运行中...", expanded=True) as status:
        final_report = ""
        extracted_papers = []
        reward_scores = []
        loop_count = 0

        for event in app.stream(
            {
                "topic": topic,
                "loop_count": 0,
                "base_env": selected_base_env,
                "auto_reproduce_code": auto_reproduce_code,
            },
            config,
            stream_mode="updates",
            subgraphs=True,
        ):
            if isinstance(event, tuple) and len(event) == 2:
                ns, payload = event
            else:
                ns, payload = (), event

            for node_name, node_output in payload.items():
                if node_name == "query_planner":
                    queries = node_output.get("search_queries", [])
                    log_event(f"Query Planner: 生成 {len(queries)} 个查询", st.write)
                    for q in queries:
                        logger.info(f"  query: {q}")
                        st.code(q, language=None)

                elif node_name == "search_agent":
                    raw = node_output.get("raw_results", [])
                    log_event(f"Search Agent: 获取 {len(raw)} 条结果", st.write)

                elif node_name == "paper_filter":
                    raw = node_output.get("raw_results", [])
                    log_event(f"Paper Filter: 筛选后 {len(raw)} 条", st.write)

                elif node_name == "info_extractor":
                    papers = node_output.get("extracted_papers", [])
                    scores = node_output.get("reward_scores", [])
                    extracted_papers = papers
                    reward_scores.extend(scores)
                    msg = f"Info Extractor: {len(papers)} 篇论文"
                    if scores:
                        msg += f", 奖励 {scores[-1]:.3f}"
                    log_event(msg, st.write)

                elif node_name == "reflector":
                    fb = node_output.get("reflection_feedback", "{}")
                    loop_count = node_output.get("loop_count", loop_count)
                    try:
                        fb_dict = json.loads(fb)
                        score = fb_dict.get("score", "?")
                        log_event(f"Reflector: 评分 {score}", st.write)
                        if fb_dict.get("missing"):
                            log_event(f"  缺失: {fb_dict['missing']}", st.write)
                        if fb_dict.get("should_continue"):
                            log_event("  决策: 继续搜索", st.write)
                        else:
                            log_event("  决策: 生成报告", st.write)
                    except json.JSONDecodeError:
                        log_event("Reflector: 完成评估", st.write)

                elif node_name == "pdf_agent":
                    papers = node_output.get("extracted_papers", [])
                    extracted_papers = papers
                    log_event(f"PDF Agent: 补充论文下载、代码和指标信息后保留 {len(papers)} 条", st.write)

                elif node_name == "prepare_code_candidates":
                    candidates = node_output.get("code_candidates", [])
                    st.session_state["papers_with_code"] = candidates_to_papers(candidates)
                    target_repo_url = node_output.get("target_repo_url", "")
                    msg = f"Code Candidates: 发现 {len(candidates)} 个可复现候选仓库"
                    if target_repo_url:
                        msg += f"，已选择 {target_repo_url}"
                    log_event(msg, st.write)

                elif node_name == "code_reproduction":
                    status_text = node_output.get("reproduction_status") or node_output.get("status", "unknown")
                    log_event(f"Code Reproduction: {status_text}", st.write)

                elif node_name == "report_writer":
                    log_event("Report Writer: 报告生成完成", st.write)
                    final_report = node_output.get("final_report", "")

                elif node_name == "save_experience":
                    log_event("经验已保存到回放缓冲区", st.write)

        status.update(label="调研完成 ✓", state="complete")
        logger.info("调研完成")

    # Fallback: read from final state
    if not final_report:
        final_state = app.get_state(config)
        final_report = final_state.values.get("final_report", "")
        if not extracted_papers:
            extracted_papers = final_state.values.get("extracted_papers", [])

    # -----------------------------------------------------------------------
    # Report display + save + history
    # -----------------------------------------------------------------------
    if final_report:
        st.divider()
        st.header("📊 调研报告")

        avg_reward = sum(reward_scores) / len(reward_scores) if reward_scores else 0
        col1, col2, col3 = st.columns(3)
        col1.metric("论文数", len(extracted_papers))
        col2.metric("搜索轮次", loop_count)
        col3.metric("平均奖励", f"{avg_reward:.3f}")

        if extracted_papers:
            st.subheader("📑 提取的论文/代码条目")
            st.dataframe(
                [
                    {
                        "标题": p.get("title", ""),
                        "方法": p.get("method", ""),
                        "数据集": p.get("datasets", p.get("dataset", "")),
                        "SOTA指标": p.get("sota_metrics", "unknown"),
                        "代码": p.get("code_url", "unknown"),
                        "下载论文": p.get("download_url", ""),
                    }
                    for p in extracted_papers
                ],
                width="stretch",
            )

        st.markdown(final_report)

        safe_topic = topic.replace(" ", "_").replace("/", "_")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{safe_topic}_{timestamp}.md"
        filepath = os.path.join(REPORT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_report)
        logger.info(f"报告已保存: {filepath}")

        add_history_entry(topic, len(extracted_papers), loop_count, avg_reward, filepath, extracted_papers)

        st.download_button(
            "📥 下载报告 (Markdown)",
            data=final_report,
            file_name=filename,
            mime="text/markdown",
        )
        st.session_state["last_report"] = final_report
        st.session_state["last_papers"] = extracted_papers

    # Save papers_with_code to session_state so code reproduction survives rerun
    papers_with_code = get_papers_with_code(extracted_papers)
    if papers_with_code:
        st.session_state["papers_with_code"] = papers_with_code

    # -----------------------------------------------------------------------
    # Evaluation visualization (after research completes)
    # -----------------------------------------------------------------------
    if reward_scores and len(reward_scores) > 1:
        st.divider()
        st.header("📈 评估分析")
        fig = plot_reward_curve(reward_scores, topic)
        st.pyplot(fig)
        import matplotlib.pyplot as plt
        plt.close(fig)

# ---------------------------------------------------------------------------
# Code reproduction section (persists across reruns via session_state)
# ---------------------------------------------------------------------------
st.divider()
st.header("🔧 代码复现")
st.caption("复现会在独立 conda 环境中运行，仓库放在 outputs/repos/搜索主题/仓库名。pip 完整过程会实时显示在终端。")

papers_with_code = get_papers_with_code(st.session_state.get("papers_with_code", []))
st.session_state["papers_with_code"] = papers_with_code
active_job = st.session_state.get("repro_job") or {}
job_is_active = is_reproduction_job_active(active_job)

if active_job:
    status_label = "运行中" if job_is_active else "已结束或已停止"
    st.subheader("当前复现任务")
    job_col1, job_col2, job_col3 = st.columns([2, 1, 1])
    job_col1.markdown(f"**仓库：** [{active_job.get('repo_url', '')}]({active_job.get('repo_url', '')})")
    job_col2.caption(f"PID: {active_job.get('pid', '-')}")
    job_col3.caption(f"状态: {status_label}")
    st.caption(f"日志文件：`{active_job.get('log_path', '')}`")

    stop_col, refresh_col, clear_col = st.columns(3)
    if stop_col.button("停止当前复现", type="secondary", disabled=not job_is_active):
        if stop_reproduction_job():
            st.success("已发送停止信号。")
        else:
            st.warning("停止信号发送失败或任务已经结束。")
        st.rerun()
    if refresh_col.button("刷新复现日志"):
        st.rerun()
    if clear_col.button("清除任务记录", disabled=job_is_active):
        st.session_state["repro_job"] = {}
        st.rerun()

    log_text = read_reproduction_log(active_job.get("log_path", ""))
    if log_text:
        repro_report = extract_reproduction_report_path(log_text)
        if repro_report:
            st.success(f"复现报告已保存：{repro_report}")
        st.text_area("复现日志（最近内容）", value=log_text, height=320)
    else:
        st.info("日志尚未写入，稍后点击刷新。")

repo_tab, manual_tab, env_tab = st.tabs(["发现的仓库", "手动输入仓库", "环境与停止说明"])

with repo_tab:
    st.write(f"发现 {len(papers_with_code)} 个可尝试复现的 GitHub 仓库。")
    if papers_with_code:
        selected = st.selectbox(
            "选择仓库",
            options=range(len(papers_with_code)),
            format_func=lambda i: f"{papers_with_code[i].get('title', 'Unknown')} ({papers_with_code[i]['code_url']})",
        )
        selected_paper = papers_with_code[selected]
        st.markdown(f"**代码：** [{selected_paper['code_url']}]({selected_paper['code_url']})")
        st.caption(f"基础环境：{selected_base_env or '自动选择'}")
        if st.button("复现选中仓库", type="primary", key="run_selected_repo", disabled=job_is_active):
            start_reproduction_job(
                selected_paper["code_url"],
                st.session_state.get("last_topic", topic) or topic or "manual_reproduction",
                selected_base_env,
            )
            st.success("后台复现任务已启动。")
            st.rerun()
    else:
        st.info("当前还没有可复现仓库。可以先调研，或在“手动输入仓库”里直接复现 GitHub URL。")

with manual_tab:
    manual_repo_url = st.text_input(
        "GitHub 仓库 URL",
        placeholder="https://github.com/owner/repo",
        key="manual_repo_url",
    )
    manual_workspace = st.text_input(
        "复现主题目录",
        value=st.session_state.get("last_topic", topic) or "manual_reproduction",
        key="manual_workspace",
    )
    if manual_repo_url and not _is_probable_code_repo(manual_repo_url):
        st.warning("该 URL 看起来像资料列表/Survey/Awesome 仓库，默认不建议复现。")
    if st.button("复现手动仓库", type="secondary", disabled=(not manual_repo_url or job_is_active), key="run_manual_repo"):
        start_reproduction_job(manual_repo_url, manual_workspace, selected_base_env)
        st.success("后台复现任务已启动。")
        st.rerun()

with env_tab:
    st.write("当前复现环境策略：")
    st.code(
        "\n".join([
            f"base_env={selected_base_env or 'auto'}",
            "repo_env=sota_repo_<repo_name>",
            "create_strategy=conda create --clone <base_env>，找不到基础环境时回退 python=3.10",
            "pip_index=https://pypi.tuna.tsinghua.edu.cn/simple",
            "pip_timeout=3000",
            "command_timeout=3600",
        ]),
        language="text",
    )
    st.warning("不要用 Ctrl+C 直接停止 Streamlit 主进程。复现命令已经放入独立进程组；如果需要中断，请使用“停止当前复现”按钮。")

# ---------------------------------------------------------------------------
# Evaluation section (always visible, independent of research run)
# ---------------------------------------------------------------------------
st.divider()
st.header("📚 历史与评估")

history_tab, eval_tab1 = st.tabs(["历史报告", "历史奖励趋势"])

with history_tab:
    history_data = load_history()
    if history_data:
        st.dataframe(
            [
                {
                    "主题": item.get("topic", ""),
                    "时间": item.get("time", ""),
                    "论文数": item.get("paper_count", 0),
                    "搜索轮次": item.get("loop_count", ""),
                    "平均奖励": item.get("avg_reward", ""),
                    "报告路径": item.get("report_path", ""),
                }
                for item in history_data
            ],
            width="stretch",
        )
        selected_history_idx = st.selectbox(
            "打开历史报告",
            options=range(len(history_data)),
            format_func=lambda i: f"{history_data[i].get('topic', '')} ({history_data[i].get('time', '')})",
            key="main_history_open_select",
        )
        if st.button("加载选中的历史报告", key="main_history_open_button"):
            selected_history = history_data[selected_history_idx]
            report_path = selected_history.get("report_path", "")
            if report_path and os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    st.session_state["last_report"] = f.read()
                st.session_state["last_topic"] = selected_history.get("topic", "")
                st.session_state["last_papers"] = selected_history.get("papers", [])
                st.session_state["papers_with_code"] = selected_history.get("code_candidates") or get_papers_with_code(selected_history.get("papers", []))
                st.rerun()
            else:
                st.warning("报告文件不存在。")
    else:
        st.caption("暂无历史报告。完成一次调研后会自动出现在这里。")

with eval_tab1:
    history_data = load_history()
    if history_data and len(history_data) >= 2:
        fig_trend = plot_experience_trend()
        st.pyplot(fig_trend)
        import matplotlib.pyplot as plt
        plt.close(fig_trend)
    else:
        st.caption("需要至少 2 次调研记录才能展示趋势图。")
