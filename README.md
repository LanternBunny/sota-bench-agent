# SOTA-Bench Agent

从论文调研到代码复现的一体化智能体系统，融合强化学习思想实现自我改进闭环。

## 当前状态

项目主流程已经完成，包括调研图、代码复现子图、奖励函数、Best-of-N、经验回放、评估模块与 Streamlit 界面。更详细的实验说明见 [SOTA_Bench_Agent_Experiment_Report.md](SOTA_Bench_Agent_Experiment_Report.md)，项目规划与完成记录见 [PLAN.md](PLAN.md)。

## 功能概览

- 输入一个研究主题，自动检索论文、代码、benchmark
- 结构化分析并生成 Markdown 调研报告
- 自动复现论文代码（GitHub 仓库克隆 → 执行 → 错误修复）
- Reflexion 反思循环 + Best-of-N 采样 + 经验回放，持续提升输出质量

## 实验与评估

当前仓库不仅提供运行入口，也内置了完整的实验与评估能力：

| 方向 | 能力 | 代码位置 |
|---|---|---|
| 调研实验 | 主题驱动的论文检索、抽取、反思、报告生成 | [graph.py](graph.py)、[agents/](agents/) |
| 代码复现实验 | GitHub 克隆、环境隔离、执行计划、报错修复闭环 | [code_agent/](code_agent/) |
| RL 评估 | 奖励函数、Best-of-N、经验回放 | [rl/](rl/) |
| 指标与消融 | 报告质量、奖励曲线、配置对比 | [evaluation/](evaluation/) |

已支持的实验任务包括：

| 任务 | 输入 | 输出 |
|---|---|---|
| 文献调研 | 一个研究主题 | Markdown 报告 + 结构化论文列表 |
| 代码复现 | 论文中的 GitHub 仓库链接 | 执行日志 + 修复过程 + 成功/失败状态 |
| 消融实验 | 多个主题 | 4 种配置的对比结果 |

如果你想直接查看实验结论，可以优先打开 [SOTA_Bench_Agent_Experiment_Report.md](SOTA_Bench_Agent_Experiment_Report.md)。

## 环境准备

### 1. 创建 Conda 环境

```bash
conda activate langgraph
```

### 2. 安装依赖

```bash
cd /home/chengyuxuan/Agent/sota-bench-agent
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env` 文件并填入你的 API Key：

```bash
cp .env.example .env
```

需要配置的变量：

| 变量 | 说明 |
|------|------|
| `SILICONFLOW_API_KEY` | SiliconFlow API 密钥（兼容 OpenAI 格式） |
| `SILICONFLOW_BASE_URL` | SiliconFlow API 地址 |
| `TAVILY_API_KEY` | Tavily 搜索 API 密钥 |
| `LANGSMITH_API_KEY` | LangSmith 追踪密钥（可选） |
| `LANGSMITH_TRACING` | 设为 `true` 启用追踪 |
| `LANGSMITH_PROJECT` | LangSmith 项目名 |
| `LLM_MODEL` | 主模型，默认 `deepseek-ai/DeepSeek-V3` |
| `JUDGE_MODEL` | 评审模型，默认 `Qwen/Qwen2.5-72B-Instruct` |

## 使用方式

### 方式一：Streamlit Web 界面（推荐）

```bash
streamlit run app.py
```

打开浏览器访问 `http://localhost:8501`，输入研究主题即可开始调研。

界面功能：
- 输入主题后点击「开始调研」，实时展示各节点执行进度
- 调研完成后展示报告，支持下载 Markdown 文件
- 侧边栏可开启 Best-of-N 采样、自动代码复现
- 历史记录自动保存，支持回看和下载

### 方式一补充：使用 start.sh 一键启动

仓库新增了 [start.sh](start.sh)，可以同时启动 LangGraph dev 和 Streamlit，并自动处理端口占用问题：

```bash
bash start.sh
```

脚本默认使用两个端口：

| 服务 | 默认端口 | 说明 |
|---|---|---|
| LangGraph dev | 2026 | 用于 LangGraph Studio 连接 |
| Streamlit | 8502 | 用于打开 Web 界面 |

如果默认端口已经被占用，脚本会从当前端口开始向后顺延，自动寻找可用端口后再启动服务。

启动后终端会输出两个访问地址：

| 入口 | 地址 |
|---|---|
| Streamlit | http://localhost:8502 |
| LangGraph Studio | https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2026 |

如果你需要修改端口，可以直接编辑 [start.sh](start.sh) 顶部的 `LG_PORT` 和 `ST_PORT` 两个变量，然后重新执行脚本。

### 方式二：命令行直接运行

```bash
python graph.py
```

默认会对内置主题执行一次完整调研流程，输出报告到 `outputs/reports/`。

### 方式三：代码复现（单独运行）

```bash
python code_agent/graph.py https://github.com/用户/仓库
```

对指定 GitHub 仓库执行自动复现：克隆 → 解析 → 生成执行计划 → 执行 → 错误修复循环。

代码复现采用的是 Conda 隔离环境，而不是 Docker 沙箱。每个仓库都会被分配一个独立环境，命名形式为 `sota_repo_{repo_name}`，以减少依赖冲突和环境污染。

### 方式四：LangGraph Studio 可视化

启动开发服务器：

```bash
bash start.sh
```

然后在浏览器打开：

```
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2026
```

可以在 LangSmith Studio 中交互式查看 Graph 结构、运行工作流、调试节点。

如果通过 SSH 远程连接，需要先做端口转发：

```bash
ssh -L 8502:127.0.0.1:8502 -L 2026:127.0.0.1:2026 你的服务器地址
```

如果你已经修改了 [start.sh](start.sh) 里的端口配置，这里的转发参数也要同步修改，保证本地端口和脚本端口一致。

## 系统架构

```
用户输入研究主题
       │
       ▼
┌─────────────┐
│ Query Planner│  生成多角度搜索查询
└──────┬──────┘
       ▼
┌─────────────┐
│ Search Agent │  调用 Tavily 搜索
└──────┬──────┘
       ▼
┌─────────────┐
│ Paper Filter │  去重、评分排序
└──────┬──────┘
       ▼
┌──────────────┐
│Info Extractor │  LLM 结构化提取论文信息
└──────┬───────┘
       ▼
┌─────────────┐
│  Reflector   │  评估质量，决策是否继续搜索
└──────┬──────┘
       │
       ├── 继续搜索 → 回到 Search Agent
       ├── 生成报告 → Report Writer → 保存经验
       └── 代码复现 → Code Agent 子图
```

### Code Agent 子图

```
Repo Fetcher → Code Parser → Execution Planner → Executor
                                                     │
                                              ┌──────┴──────┐
                                              │ 成功 → 结束  │
                                              │ 失败 ↓       │
                                              │ Error Analyzer│
                                              │      ↓       │
                                              │Patch Generator│
                                              │      ↓       │
                                              │ 重新执行      │
                                              └──────────────┘
                                              (最多 5 次修复)
```

实际实现中，Executor 使用 Conda 运行命令，流程会在 `code_agent/executor.py` 中创建和复用仓库对应环境，然后通过 `conda run` 执行计划中的每一步。

## 项目结构

```
sota-bench-agent/
├── app.py                  # Streamlit Web 入口
├── config.py               # API 配置、模型选择
├── graph.py                # LangGraph 主图定义
├── state.py                # 主图状态定义
├── langgraph.json          # LangGraph Dev Server 配置
├── .env                    # 环境变量（不要提交到 git）
├── requirements.txt        # Python 依赖
│
├── agents/                 # 调研 Agent 各节点
│   ├── query_planner.py    # 查询规划
│   ├── search_agent.py     # 搜索执行
│   ├── paper_filter.py     # 论文筛选
│   ├── info_extractor.py   # 信息提取
│   ├── reflector.py        # 反思评估
│   ├── decision.py         # 路由决策
│   └── report_writer.py    # 报告生成
│
├── code_agent/             # 代码复现 Agent
│   ├── graph.py            # Code Agent 子图定义
│   ├── state.py            # 子图状态
│   ├── repo_fetcher.py     # 仓库克隆
│   ├── code_parser.py      # 代码解析
│   ├── execution_planner.py# 执行计划生成
│   ├── executor.py         # 命令执行（Conda 隔离）
│   ├── error_analyzer.py   # 错误分析
│   └── patch_generator.py  # 自动修复
│
├── rl/                     # 强化学习模块
│   ├── reward.py           # 奖励函数
│   ├── best_of_n.py        # Best-of-N 采样
│   └── experience_buffer.py# 经验回放
│
├── prompts/                # Prompt 模板集中管理
│   ├── query_planner.py
│   ├── info_extractor.py
│   ├── reflector.py
│   ├── report_writer.py
│   ├── judge.py
│   ├── execution_planner.py
│   └── error_analyzer.py
│
└── outputs/                # 输出目录
    ├── reports/            # 生成的调研报告
    ├── experiments/        # 实验结果
    ├── repos/              # 克隆的代码仓库
    ├── reward_curves/      # 奖励曲线
    ├── history.json        # 调研历史记录
    └── experience_buffer.json  # 经验回放数据
```

## 强化学习机制

系统在运行时层面引入三层 RL 机制：

1. **Reflexion 循环** — 每轮搜索后评估结果质量，生成反馈指导下一轮改进
2. **Best-of-N 采样** — 关键节点生成 N=3 个候选，用奖励函数选最优
3. **经验回放** — 存储高奖励轨迹，作为 few-shot 示例注入后续任务

奖励函数四维加权：

| 维度 | 权重 |
|------|------|
| 信息完整度 | 0.3 |
| 主题相关性 | 0.3 |
| 代码可用性 | 0.2 |
| 时效性 | 0.2 |

## 代码说明

下面这段代码展示了主图是如何根据反思结果动态路由的：

```python
graph.add_conditional_edges(
       "reflector",
       decision_node,
       {
              "search": "query_planner",
              "report": "report_writer",
              "code_reproduction": "select_paper",
       },
)
```

这段代码展示了代码复现阶段的隔离执行方式：

```python
env_name = _get_env_name(repo_dir)
result = _run_in_conda(cmd, env_name, repo_dir)
```

如果你想直接看完整实验过程，请打开 [SOTA_Bench_Agent_Experiment_Report.md](SOTA_Bench_Agent_Experiment_Report.md)。

## 配置说明

`config.py` 中的关键参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX_SEARCH_LOOPS` | 3 | 最大搜索反思循环次数 |
| `MAX_CODE_FIX_LOOPS` | 5 | 代码修复最大尝试次数 |
| `BEST_OF_N` | 3 | Best-of-N 采样候选数 |

## 输出示例

调研完成后在 `outputs/reports/` 生成 Markdown 报告，包含：

- 研究主题概述
- 论文列表（标题、年份、方法、数据集、代码链接）
- 方法对比分析
- Benchmark 结果汇总
- 研究趋势与建议

## 技术栈

| 组件 | 选择 |
|------|------|
| Agent 编排 | LangGraph |
| LLM | DeepSeek-V3 + Qwen2.5-72B（via SiliconFlow） |
| 搜索 | Tavily Search API |
| 代码隔离 | Conda 环境 |
| 追踪 | LangSmith |
| 前端 | Streamlit |
