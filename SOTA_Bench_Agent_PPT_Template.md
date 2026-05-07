# SOTA-Bench Agent PPT 汇报模版

> 建议页数：14-16 页。汇报主线是“为什么需要工作流智能体 -> 系统怎么设计 -> Prompt/Agent/Graph 如何协同 -> 代码复现如何闭环 -> LangSmith 如何支撑可观测实验 -> 结果与总结”。

## 第 1 页：标题页

**标题**：SOTA-Bench Agent：面向科研调研与代码复现的工作流智能体

**副标题**：基于 LangGraph、Prompt 约束、自动复现闭环与 LangSmith 可观测性的实验系统

**页面元素**：项目名称、汇报人、日期、关键词。

**讲述重点**：本项目不是单轮问答系统，而是一个能够搜索、反思、复现、修复和记录经验的端到端科研助手。

## 第 2 页：研究背景与问题

**页面标题**：科研调研和复现为什么难自动化

**核心内容**：

| 痛点 | 具体表现 | 对 Agent 的要求 |
|---|---|---|
| 文献入口分散 | 论文、项目页、GitHub、博客结果混杂 | 多查询检索与去重筛选 |
| 信息不结构化 | 方法、数据集、代码链接散落在网页文本中 | 稳定 JSON 抽取和链接验证 |
| 代码复现复杂 | README 不统一，依赖和模型下载容易失败 | 自动规划、隔离执行、错误修复 |
| 过程不可解释 | 只看最终结果无法复盘失败原因 | Graph 状态追踪和 LangSmith Trace |

**讲述重点**：传统脚本只能处理固定流程，科研任务需要动态搜索、判断和纠错。

## 第 3 页：项目目标与核心思想

**页面标题**：把科研任务建模为可追踪的工作流

**核心内容**：

| 层次 | 目标 | 对应能力 |
|---|---|---|
| 调研层 | 从主题找到高质量论文 | Query Planner、Search Agent、Info Extractor、Reflector |
| 复现层 | 从代码链接进入自动复现 | Repo Fetcher、Code Parser、Execution Planner、Executor |
| 优化层 | 让系统随运行积累经验 | Reward、Best-of-N、Experience Buffer |
| 观测层 | 让每次运行可解释可复盘 | LangSmith、LangGraph Studio、日志报告 |

**讲述重点**：系统能力来自“节点能力 + 图结构 + 状态追踪”，不是单个大模型调用。

## 第 4 页：总体架构图

**页面标题**：SOTA-Bench Agent 总体架构

**建议画图**：

```text
用户主题
  -> Query Planner
  -> Search Agent
  -> Paper Filter
  -> Info Extractor
  -> Reflector
  -> Decision Node
       -> 继续搜索
       -> Report Writer
       -> Code Agent Subgraph
              -> Repo Fetcher
              -> Code Parser
              -> Execution Planner
              -> Executor
              -> Error Analyzer
              -> Patch Generator
              -> Executor
```

**讲述重点**：主图负责研究闭环，代码子图负责复现闭环，二者通过论文中的 `code_url` 连接。

## 第 5 页：Research Graph 设计

**页面标题**：从宽泛主题到结构化论文知识

**核心内容**：

| 节点 | 输入 | 输出 | 设计目的 |
|---|---|---|---|
| Query Planner | `topic` | `search_queries` | 多角度扩展检索词 |
| Search Agent | 查询词 | `raw_results` | 调用 Tavily 获取候选结果 |
| Paper Filter | 原始结果 | 去重 Top-K | 降噪和控制上下文长度 |
| Info Extractor | 搜索结果 | `extracted_papers` | 结构化抽取论文与代码链接 |
| Reflector | 当前论文列表 | 质量反馈和新查询 | 判断是否继续搜索 |
| Decision Node | 反思结果 | 下一步路由 | 控制搜索、报告和复现分支 |

**讲述重点**：Research Graph 的关键是反思回路，系统发现信息不足时会主动补充搜索。

## 第 6 页：Prompt 设计思想

**页面标题**：按 Agent 职责拆分 Prompt，而不是一个超级 Prompt

**核心内容**：

| Prompt | 目标 | 关键约束 |
|---|---|---|
| `QUERY_PLANNER_PROMPT` | 生成多角度检索词 | 覆盖综述、代码、benchmark、年份 |
| `EXTRACT_PROMPT` | 抽取结构化论文 | JSON 输出，禁止编造 GitHub 链接 |
| `REFLECT_PROMPT` | 判断质量缺口 | 输出分数、缺失项、是否继续 |
| `REPORT_PROMPT` | 生成 Markdown 报告 | 围绕方法、数据集、趋势组织 |
| `EXECUTION_PLANNER_PROMPT` | 生成复现命令 | 只能用真实文件，禁止 Conda 激活命令 |
| `ERROR_ANALYZER_PROMPT` | 生成修复动作 | TypeError 必须参考源码上下文 |

**讲述重点**：Prompt 负责表达意图和边界，执行器负责强约束，不能把稳定性全部寄托在 LLM 上。

## 第 7 页：Code Agent Subgraph 设计

**页面标题**：代码复现被建模为自动排障闭环

**核心内容**：

| 阶段 | 作用 | 典型状态 |
|---|---|---|
| Repo Fetcher | 克隆并标准化 GitHub 仓库 | `repo_dir` |
| Code Parser | 读取 README、依赖和目录树 | `readme_content`, `entry_file` |
| Execution Planner | 生成命令序列 | `execution_plan` |
| Executor | Conda 隔离执行 | `current_step`, `error_type` |
| Error Analyzer | 分析失败根因 | `patch` |
| Patch Generator | 执行修复动作 | `fix_count` |

**讲述重点**：失败不是流程终点，而是进入错误分析和修复分支。

## 第 8 页：复现鲁棒性加固

**页面标题**：从 LLaVA 复现实验中沉淀工程规则

**核心内容**：

| 问题 | 系统改进 |
|---|---|
| Planner 生成 `conda activate/init/create` | Prompt 禁止，执行器过滤，统一用 `conda run` |
| 把 `load_pretrained_model` 当下载命令 | HF 下载改用 `huggingface-cli download` |
| `pytorch-cuda=12.1` Conda 缺包 | 自动改写为 PyTorch CUDA wheel 安装 |
| HF/Xet `Read timed out` | 关闭 Xet、使用 HF 镜像、加长超时、自动重试 |
| TypeError 被误判为 GPU 错误 | 调整错误分类优先级，TypeError 优先 |
| 函数签名猜错 | 从仓库源码提取函数定义注入 Error Analyzer |

**讲述重点**：自动复现系统需要大量确定性工程兜底，不能只依赖模型临场推理。

## 第 9 页：强化学习式优化机制

**页面标题**：轻量 RL 思想提升稳定性

**核心内容**：

| 机制 | 做法 | 收益 |
|---|---|---|
| Reward | 完整度、相关性、代码可用性、时效性加权 | 把质量变成可比较分数 |
| Judge LLM | 用评审模型做语义评分 | 弥补规则评分的语义不足 |
| Best-of-N | 多次抽取后按奖励择优 | 降低单次生成波动 |
| Experience Buffer | 保存高质量轨迹作为 Few-Shot | 复用成功搜索策略 |

**讲述重点**：这里的 RL 更接近轨迹质量优化，不是传统训练，而是工程化的“多试、评分、复用”。

## 第 10 页：LangSmith 与 LangGraph Studio

**页面标题**：让 Agent 运行过程可观察、可解释、可复盘

**核心内容**：

| 工具 | 观察内容 | 汇报价值 |
|---|---|---|
| LangGraph Studio | 图结构、节点、边、子图入口 | 展示系统不是线性脚本 |
| LangSmith Trace | LLM 调用、Tool 调用、状态输入输出 | 解释每一步为什么这样执行 |
| 节点级调试 | Prompt、模型输出、解析结果 | 定位抽取失败、路由异常、JSON 错误 |
| Code Agent Trace | 失败命令、stderr、错误分类、修复建议 | 复盘自动复现失败和修复路径 |

**建议截图**：LangGraph Studio 的图结构截图，LangSmith 某次运行的 Trace 时间线截图。

**讲述重点**：LangSmith 是实验显微镜，证明系统过程可控，而不是只展示最终结果。

## 第 11 页：状态与控制设计

**页面标题**：为什么使用 Graph 而不是线性 Chain

**核心内容**：

| 需求 | Chain 的问题 | Graph 的解决方式 |
|---|---|---|
| 多轮搜索 | 循环逻辑不透明 | `reflector -> decision_node -> query_planner` |
| 可选代码复现 | 分支混在主函数里 | `code_reproduction` 路由进入子图 |
| 失败自动修复 | 异常处理分散 | `executor -> error_analyzer -> patch_generator` |
| 可观测调试 | 中间状态难统一查看 | 状态字段统一进入 Trace |

**讲述重点**：Graph 适合表达科研任务中的不确定路径和失败修复。

## 第 12 页：实验设置与运行方式

**页面标题**：实验环境、入口与关键参数

**核心内容**：

| 项目 | 设置 |
|---|---|
| 主模型 | `deepseek-ai/DeepSeek-V3` |
| 评审模型 | `Qwen/Qwen2.5-72B-Instruct` |
| 搜索服务 | Tavily Search API |
| 图编排 | LangGraph StateGraph |
| 代码隔离 | Conda 环境 `sota_repo_{repo}` |
| 运行入口 | `streamlit run app.py`, `python graph.py "topic"`, `python -m code_agent.run_reproduction ...` |
| 可观测配置 | `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT=...` |

**讲述重点**：实验不是离线生成，而是能调用搜索、克隆代码、创建环境、执行命令的端到端系统。

## 第 13 页：运行结果与案例

**页面标题**：调研报告、复现日志和 Trace 共同构成结果证据

**核心内容**：

| 场景 | 输出 | 证明点 |
|---|---|---|
| 主题调研 | Markdown 报告、结构化论文列表 | 能从主题收敛到论文综述 |
| 代码复现 | `reproduction_report.md`、执行日志 | 能进入真实仓库并尝试复现 |
| 失败修复 | 错误分类、Patch、再次执行 | 具备自动排障闭环 |
| LangSmith Trace | 节点时间线、状态变化 | 能解释一次运行的完整过程 |

**建议展示**：选择一个真实主题报告截图，一个 LLaVA 复现失败到修复策略的 Trace 或日志截图。

## 第 14 页：设计亮点

**页面标题**：系统创新点总结

**核心内容**：

| 亮点 | 说明 |
|---|---|
| 图式科研工作流 | 把搜索、反思、报告、复现建模为状态图 |
| 结构化抽取与验证 | JSON 输出、GitHub 链接校验、Top-K 降噪 |
| 自动代码复现闭环 | 克隆、解析、规划、执行、分析、修复一体化 |
| Prompt 与规则双层约束 | LLM 做语义规划，执行器做确定性兜底 |
| 轻量 RL 优化 | Reward、Best-of-N、经验回放提升稳定性 |
| LangSmith 可观测性 | 让每个节点决策和失败路径可复盘 |

**讲述重点**：项目亮点不是某一个算法点，而是把多个 Agent 工程能力组合成可运行系统。

## 第 15 页：不足与未来工作

**页面标题**：当前局限与下一步优化

**核心内容**：

| 不足 | 后续方向 |
|---|---|
| LLM 输出 JSON 仍可能不稳定 | 增强 schema 校验和自动重试 |
| 代码修复以命令级和字符串级为主 | 引入更精细的补丁生成和测试反馈 |
| 搜索质量依赖外部搜索服务 | 增加多源检索和本地缓存 |
| 经验回放仍是轻量轨迹缓存 | 进一步做策略学习或任务聚类 |
| 大模型仓库复现成本高 | 增加资源感知调度和小样例 smoke test |

**讲述重点**：系统已经验证了方向，但还可以在稳定性、可扩展性和深度修复能力上继续增强。

## 第 16 页：总结页

**页面标题**：结论

**核心结论**：

SOTA-Bench Agent 将文献调研和代码复现整合成一个可执行、可追踪、可优化的工作流智能体。它通过 LangGraph 管理复杂流程，通过 Prompt 与确定性规则约束 Agent 行为，通过 Code Agent 实现自动复现闭环，通过 LangSmith 让实验过程可解释和可复盘。

**收束表达**：未来的科研助手不应只是生成答案，而应该能搜索证据、判断质量、执行代码、修复失败，并把整个过程透明地记录下来。

## 备用页 A：核心状态字段

| 状态字段 | 含义 |
|---|---|
| `topic` | 用户研究主题 |
| `search_queries` | 查询规划结果 |
| `raw_results` | 搜索原始结果 |
| `extracted_papers` | 结构化论文列表 |
| `reflection_feedback` | 反思反馈 |
| `execution_plan` | 复现命令列表 |
| `error_type` | 执行失败类型 |
| `patch` | 修复建议 |

## 备用页 B：答辩问题准备

| 可能问题 | 回答要点 |
|---|---|
| 为什么不用普通 Chain | 因为任务存在搜索回路、复现分支和失败修复，需要显式状态图 |
| LangSmith 的作用是什么 | 不是核心算法，而是可观测性、调试和实验复盘平台 |
| Prompt 如何防止幻觉 | 结构化输出、真实文件约束、真实 GitHub 链接约束、禁止无效命令 |
| 复现失败怎么办 | Executor 分类错误，Error Analyzer 生成修复，Patch Generator 落地后回到执行器 |
| 项目最大价值是什么 | 把科研调研和工程复现统一成可运行、可解释、可迭代的 Agent 系统 |
