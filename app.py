import streamlit as st
import json
import time
import os
import logging
from datetime import datetime
from graph import compile_graph
from code_agent.graph import compile_code_agent
from config import MAX_CODE_FIX_LOOPS

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
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "outputs", "history.json")
os.makedirs(REPORT_DIR, exist_ok=True)


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
                      avg_reward: float, report_path: str):
    history = load_history()
    history.insert(0, {
        "topic": topic,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "paper_count": paper_count,
        "loop_count": loop_count,
        "avg_reward": round(avg_reward, 3),
        "report_path": report_path,
    })
    history = history[:50]
    save_history(history)


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
    auto_code_agent = st.checkbox("自动触发代码复现", value=False,
                                  help="调研完成后自动对有代码的论文执行复现")
    st.divider()

    st.header("📜 历史记录")
    history = load_history()
    if history:
        for i, entry in enumerate(history[:10]):
            with st.container():
                col_t, col_s = st.columns([3, 1])
                with col_t:
                    st.markdown(f"**{entry['topic'][:40]}**")
                    st.caption(f"{entry['time']}  ·  {entry['paper_count']} 篇  ·  奖励 {entry['avg_reward']}")
                with col_s:
                    report_path = entry.get("report_path", "")
                    if report_path and os.path.exists(report_path):
                        with open(report_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                "📥", data=f.read(),
                                file_name=os.path.basename(report_path),
                                mime="text/markdown",
                                key=f"hist_dl_{i}",
                            )
                st.divider()
        if len(history) > 10:
            st.caption(f"还有 {len(history) - 10} 条更早的记录")
    else:
        st.caption("暂无历史记录，完成一次调研后会自动保存。")


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("🔬 SOTA-Bench Agent")
st.caption("AI 论文调研与 Benchmark 对比智能体  ·  Reflexion + Best-of-N + 经验回放")

topic = st.text_input(
    "输入研究主题",
    placeholder="例如：multimodal hallucination detection",
)


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
if st.button("开始调研", type="primary", disabled=not topic):
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
            {"topic": topic, "loop_count": 0},
            config,
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
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

                elif node_name == "code_agent":
                    repo_status = node_output.get("reproduction_status", "unknown")
                    repo_url = node_output.get("target_repo_url", "")
                    log_event(f"Code Agent: {repo_status} ({repo_url})", st.write)
                    code_logs = node_output.get("execution_logs", "")
                    if code_logs:
                        logger.info(f"  Code Agent logs:\n{code_logs}")
                        with st.expander("执行日志"):
                            st.text(code_logs)

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

        st.markdown(final_report)

        safe_topic = topic.replace(" ", "_").replace("/", "_")[:50]
        filename = f"report_{safe_topic}.md"
        filepath = os.path.join(REPORT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_report)
        logger.info(f"报告已保存: {filepath}")

        add_history_entry(topic, len(extracted_papers), loop_count, avg_reward, filepath)

        st.download_button(
            "📥 下载报告 (Markdown)",
            data=final_report,
            file_name=filename,
            mime="text/markdown",
        )

    # -----------------------------------------------------------------------
    # Code reproduction section
    # -----------------------------------------------------------------------
    papers_with_code = [
        p for p in extracted_papers
        if p.get("code_url") not in (None, "", "unknown")
        and "github.com" in p.get("code_url", "")
    ]

    if papers_with_code:
        st.divider()
        st.header("🔧 代码复现")
        st.write(f"发现 {len(papers_with_code)} 篇论文附带 GitHub 代码：")

        for i, p in enumerate(papers_with_code):
            st.markdown(f"**{i+1}. {p.get('title', 'Unknown')}** — [{p['code_url']}]({p['code_url']})")

        selected = st.selectbox(
            "选择要复现的仓库",
            options=range(len(papers_with_code)),
            format_func=lambda i: f"{papers_with_code[i].get('title', 'Unknown')} ({papers_with_code[i]['code_url']})",
        )

        if st.button("开始代码复现", type="secondary"):
            repo_url = papers_with_code[selected]["code_url"]
            logger.info(f"开始代码复现: {repo_url}")
            code_app = compile_code_agent()

            with st.status(f"Code Agent: 复现中...", expanded=True) as code_status:
                code_result = None
                for event in code_app.stream(
                    {
                        "repo_url": repo_url,
                        "fix_count": 0,
                        "max_fixes": MAX_CODE_FIX_LOOPS,
                        "status": "pending",
                    },
                    stream_mode="updates",
                ):
                    for node_name, node_output in event.items():
                        if node_name == "repo_fetcher":
                            log_msg = node_output.get("execution_logs", [""])[0]
                            log_event(f"Repo Fetcher: {log_msg}", st.write)
                        elif node_name == "code_parser":
                            entry = node_output.get("entry_file", "?")
                            log_event(f"Code Parser: 入口文件 = {entry}", st.write)
                        elif node_name == "execution_planner":
                            plan = node_output.get("execution_plan", [])
                            log_event(f"Execution Planner: {len(plan)} 步", st.write)
                            for j, cmd in enumerate(plan):
                                logger.info(f"  [{j}] {cmd}")
                                st.code(f"[{j}] {cmd}", language="bash")
                        elif node_name == "executor":
                            for log in node_output.get("execution_logs", []):
                                log_event(log, st.text)
                        elif node_name == "error_analyzer":
                            for log in node_output.get("execution_logs", []):
                                log_event(log, st.warning, "warning")
                        elif node_name == "patch_generator":
                            for log in node_output.get("execution_logs", []):
                                log_event(log, st.info)
                        elif node_name in ("finalize_success", "finalize_failure"):
                            code_result = node_output

                if code_result:
                    s = code_result.get("status", "unknown")
                    if s == "success":
                        code_status.update(label="复现成功 ✓", state="complete")
                        logger.info("代码复现成功")
                    else:
                        code_status.update(label="复现失败 ✗", state="error")
                        logger.warning("代码复现失败")
                else:
                    code_status.update(label="复现结束", state="complete")
