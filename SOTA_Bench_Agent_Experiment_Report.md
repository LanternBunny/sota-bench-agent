# SOTA-Bench Agent 实验报告

## 1. 实验概述与核心思想

SOTA-Bench Agent 的目标不是单点问答，而是把一套完整的科研工作流拆解成可执行、可追踪、可反复优化的智能体系统。它面向的不是“回答一个问题”，而是“完成一次小型研究任务”：先检索和筛选论文，再抽取结构化信息，然后根据结果决定是否继续搜索、是否输出综述报告，最后在有可复现代码时自动进入代码复现流程。

从系统设计上看，它采用 LangGraph 作为编排底座，把复杂流程表示成带状态的图。这样做的好处是每一步的输入、输出、回路条件和终止条件都显式可见，便于调试和扩展，也便于把“搜索-反思-再搜索”的研究习惯编码成稳定的执行逻辑。

整个系统可以分成三层：
1. 调研层：负责把主题扩展成搜索词、执行网络搜索、去重排序、提取论文信息、判断是否继续搜索。
2. 复现层：当论文中存在可信 GitHub 代码时，自动进入代码仓库克隆、结构解析、执行计划、报错分析和修复循环。
3. 优化层：利用反思、采样和经验回放，让系统随着任务运行不断积累高质量轨迹，而不是每次都从零开始。

这个架构的核心理念是把“科研调研”视为一个有明确中间状态的决策过程，而不是一次性生成文本。模型的能力不只体现在生成，更体现在选择、验证、纠错和继续探索。

### 1.1 代码实现对照总览

| 组件 | 代码位置 | 作用 | 关键输入 | 关键输出 |
|---|---|---|---|---|
| 主研究图 | [graph.py](graph.py) | 组织调研流程和回路 | `topic`, `loop_count` | 最终报告或代码复现分支 |
| 查询规划 | [agents/query_planner.py](agents/query_planner.py) | 生成多角度搜索词 | `topic` | `search_queries` |
| 搜索执行 | [agents/search_agent.py](agents/search_agent.py) | 调用 Tavily 检索 | `search_queries` | `raw_results` |
| 论文筛选 | [agents/paper_filter.py](agents/paper_filter.py) | 去重和排序 | `raw_results` | 精简后的 `raw_results` |
| 信息抽取 | [agents/info_extractor.py](agents/info_extractor.py) | 结构化提取论文信息 | `raw_results`, `topic` | `extracted_papers` |
| 反思评估 | [agents/reflector.py](agents/reflector.py) | 评估质量和补充检索方向 | `extracted_papers`, `loop_count` | `reflection_feedback`, `search_queries` |
| 路由决策 | [agents/decision.py](agents/decision.py) | 决定继续搜索、复现或写报告 | `reflection_feedback`, `papers` | 分支路由结果 |
| 报告生成 | [agents/report_writer.py](agents/report_writer.py) | 输出 Markdown 报告 | `extracted_papers` | `final_report` |
| 代码复现图 | [code_agent/graph.py](code_agent/graph.py) | 组织仓库复现流程 | `repo_url` | `status`, `reward` |
| 代码克隆 | [code_agent/repo_fetcher.py](code_agent/repo_fetcher.py) | 克隆 GitHub 仓库 | `repo_url` | `repo_dir` |
| 仓库解析 | [code_agent/code_parser.py](code_agent/code_parser.py) | 读取 README、依赖和入口 | `repo_dir` | `readme_content`, `requirements_content`, `entry_file` |
| 执行规划 | [code_agent/execution_planner.py](code_agent/execution_planner.py) | 生成命令序列 | `readme_content`, `requirements_content` | `execution_plan` |
| 命令执行 | [code_agent/executor.py](code_agent/executor.py) | Conda 隔离执行 | `execution_plan`, `repo_dir` | `status`, `error_type`, `current_step` |
| 错误分析 | [code_agent/error_analyzer.py](code_agent/error_analyzer.py) | 生成修复建议 | `error_type`, `error_message` | `patch` |
| 补丁应用 | [code_agent/patch_generator.py](code_agent/patch_generator.py) | 执行修复动作 | `patch`, `repo_dir` | `fix_count`, `execution_logs` |

### 1.2 关键参数总览

| 参数 | 默认值 | 代码来源 | 作用 |
|---|---|---|---|
| `MAX_SEARCH_LOOPS` | 3 | [config.py](config.py) | 限制调研反思循环次数 |
| `MAX_CODE_FIX_LOOPS` | 5 | [config.py](config.py) | 限制复现修复次数 |
| `BEST_OF_N` | 3 | [config.py](config.py) | Info Extractor 的候选采样数 |
| Tavily 每轮返回条数 | 5 | [agents/search_agent.py](agents/search_agent.py) | 控制每个 query 的搜索规模 |
| Paper Filter 截断数 | 20 | [agents/paper_filter.py](agents/paper_filter.py) | 控制进入 LLM 的上下文量 |
| 代码抽取验证窗口 | 前 15 条搜索结果 | [agents/info_extractor.py](agents/info_extractor.py) | 兼顾覆盖和上下文长度 |

## 2. 总体工作流

一次完整运行通常经历以下阶段：
1. 用户输入研究主题。
2. Query Planner 将主题转成多个可搜索查询。
3. Search Agent 调用搜索引擎收集候选结果。
4. Paper Filter 去重并按相关性排序。
5. Info Extractor 将网页结果转成结构化论文条目。
6. Reflector 评估当前证据是否足够、是否需要继续搜索。
7. Decision Node 根据反思结果决定走向报告输出、继续搜索或进入代码复现。
8. 如果有可用 GitHub 代码，选择最佳论文并进入 Code Agent 子图。
9. Code Agent 依次完成克隆、解析、计划、执行、报错分析和修复。
10. 最终 Report Writer 生成 Markdown 报告，并在结束时记录经验。

这个流程不是线性流水线，而是带回路的图结构。尤其在“搜索”和“反思”之间存在循环，系统会根据质量反馈持续调整检索方向，这一点是它区别于普通信息抽取脚本的关键。

## 3. Research Graph 核心模块详细设计

调研图是系统的主干，它解决的是“如何从一个宽泛主题，逐步收敛到可用结论和可复现代码”的问题。每个节点都负责一个明确的局部任务，节点之间通过状态字典传递信息，避免把复杂逻辑塞进单个大提示词里。

### 3.0 调研图节点总表

| 节点 | 主要职责 | 代码中的核心操作 | 输出状态 |
|---|---|---|---|
| Query Planner | 将主题拆成多个搜索视角 | 调用 LLM 生成 JSON 查询列表 | `search_queries` |
| Search Agent | 根据查询检索外部结果 | Tavily API 深度搜索 | `raw_results` |
| Paper Filter | 去重并控制噪音 | 按 URL 去重、按分数排序、截断 Top 20 | `raw_results` |
| Info Extractor | 把网页结果结构化为论文条目 | 生成 JSON 论文列表并验证 GitHub 链接 | `extracted_papers` |
| Reflector | 判断信息是否足够 | 基于当前论文和上一轮反馈再次评估 | `reflection_feedback`, `search_queries` |
| Decision Node | 控制流程走向 | 在搜索、复现、写报告之间切换 | 路由结果 |
| Report Writer | 生成最终报告 | 将论文列表转成 Markdown | `final_report` |

从实现角度看，这个表对应的是 [graph.py](graph.py) 中的图编排，以及 [agents/](agents/) 下各节点的独立函数。它的特点是每个节点都有单一职责，并且节点间传递的不是“对象”，而是经过标准化的状态字段。

### 3.1 Query Planner（查询规划器）

Query Planner 的作用是把用户输入的粗粒度主题转成多种检索视角。它的设计思想是，不要只用一个搜索词去碰运气，而要把主题拆成若干种“学术搜索切面”，例如方法名、任务名、应用场景、数据集、综述词、代码词和年份词。

在实现上，节点读取状态中的 `topic`，再用 `QUERY_PLANNER_PROMPT` 让 LLM 生成 JSON 格式的查询列表。这个输出不是自由文本，而是可直接消费的结构化数组，这样后续搜索节点可以直接遍历执行，不需要再做文本解析。

这个节点的关键价值在于提高召回率。很多论文不会只在标题里重复主题词，如果只靠单一关键词，很容易漏掉方法名不同但研究对象相同的工作。通过把主题分解成多个方向，系统能覆盖更多论文入口。

### 3.2 Search Agent（搜索执行器）

Search Agent 负责真正访问外部搜索服务并收集候选结果。它的核心思想不是“精准搜索一条结果”，而是“宽覆盖采集一批结果”，因为后面还有筛选、抽取和反思步骤来逐层收紧。

实现上，它从状态里读取 `search_queries`，然后逐条调用 Tavily Search API，并设置 `search_depth="advanced"`。每个查询只取前 5 条结果，控制噪音和成本。返回的条目会保留标题、链接、摘要内容和搜索分数，并统一整理进 `raw_results`。

这一层的设计关注两个平衡：一是覆盖率，二是成本。覆盖率来自多查询并行，成本来自每个查询只拿少量结果。如果一开始就抓太多结果，后面的提取环节会被大量无关文本淹没；如果抓太少，又可能错过关键论文。因此这里选择“少量多路”的方式。

### 3.3 Paper Filter（论文筛选与去重器）

Paper Filter 的任务不是理解论文，而是把原始搜索结果整理成更干净的输入。它面对的问题通常是重复链接、相似页面、同一篇论文的多个转载页，以及搜索引擎返回的低相关结果。

实现时先按 URL 做去重，再按搜索分数倒序排序，最后截取前 20 条。这个策略简单但有效，因为在调研阶段，很多冗余都来自同一条链接被不同 query 重复命中。先去重再排序，可以减少 LLM 后续上下文浪费，也能让信息提取更集中在高质量条目上。

这个节点的核心价值在于“降噪”。对于后续 LLM 来说，输入越干净，抽取越稳定，幻觉越少。它相当于给整个调研链路做了一次预清洗。

### 3.4 Info Extractor（结构化信息提取器）

Info Extractor 是调研图中最关键的语义节点，它负责把网页文本转成结构化论文信息。这里的设计思想是：搜索只是找到候选，真正能用于报告和复现的，必须是被结构化描述过、并且尽可能经过验证的信息。

| 子步骤 | 代码行为 | 目的 |
|---|---|---|
| 取样输入 | 只使用前 15 条搜索结果 | 兼顾上下文长度和信息覆盖 |
| 结构化提取 | 通过 `EXTRACT_PROMPT` 让 LLM 输出 JSON | 降低自由文本歧义 |
| 链接交叉检查 | 从原始结果中提取 GitHub URL 集合 | 过滤幻觉代码链接 |
| 仓库有效性验证 | 对 `code_url` 发起 HEAD 请求 | 剔除 404 或不可达链接 |
| 质量过滤 | 保留 `relevance_score >= 2` | 把明显不相关结果挡在后面 |

节点会把过滤后的结果列表转成 JSON 字符串，注入到 `EXTRACT_PROMPT` 中，要求 LLM 输出论文数组。每篇论文通常包含标题、年份、方法、数据集、贡献、代码链接和相关性分数等字段。这一步的输出不是为了好看，而是为了后续可计算、可排序、可复用。

这个节点最重要的特点是引入了代码链接验证。系统会先从原始搜索结果中提取所有可能的 GitHub URL，再对 LLM 给出的 `code_url` 做核验。核验方式包括格式检查和对仓库地址发起 HEAD 请求。如果链接格式不对，或者仓库不存在，就会把链接置为 `unknown`。这样做的目的是降低“看起来像代码、实际上不可用”的风险。

此外，它还会过滤 `relevance_score` 低于 2 的条目，避免把明显不相关的论文带入最终报告。也就是说，这个节点同时承担了抽取、验证和粗筛三种职责，是连接原始搜索和最终结构化知识库的桥梁。

### 3.5 Reflector（自我反思评估器）

Reflector 的作用不是再抽取新信息，而是判断“当前信息是否够好，是否值得继续搜索”。这是整个系统里最像人类研究员的一步，因为真正的研究过程通常不是一次检索就结束，而是不断发现缺口、补充证据、修正方向。

| 反思字段 | 含义 | 对控制流的影响 |
|---|---|---|
| `score` | 当前结果质量分数 | 作为奖励记录到 `reward_scores` |
| `missing` | 当前证据缺口 | 指导下一轮补充搜索方向 |
| `query_refinement` | 具体的查询修正建议 | 直接覆盖 `search_queries` |
| `should_continue` | 是否继续搜索 | 影响 Decision Node 路由 |

实现时，节点会把当前提取的论文列表、循环次数 `loop_count`、上一轮反馈内容一起交给 LLM。LLM 需要输出一个包含 `score`、`missing`、`query_refinement` 和 `should_continue` 的反馈 JSON。这样系统就能把“主观判断”变成可执行信号。

在控制逻辑上，如果当前还没有找到真实 GitHub 代码，而且搜索轮次没有超过上限，Reflector 会主动增强检索方向，比如追加 `site:github.com {topic} implementation code` 这类约束词。这个机制很重要，因为很多论文摘要虽然提到了方法，但没有直接暴露代码链接；通过强制加入代码站点约束，系统能显著提高找到可复现仓库的概率。

### 3.6 Decision Node（动态路由判断节点）

Decision Node 是调研图的路由中枢。它不是做内容理解，而是根据反思结果决定流程下一步该去哪里。

其决策逻辑主要有三种：
1. 如果反思结果显示仍然需要继续搜索，并且没有超过最大循环次数，就回到搜索流程。
2. 如果已经找到足够多的含代码论文，系统就转入代码复现分支。
3. 如果证据足够但不适合复现，或者搜索轮次耗尽，就直接进入报告生成。

这个节点的意义在于把“探索”和“收敛”统一到一个控制点上。没有它，系统很容易要么过早停止，要么无限搜索。它在整个图里承担的是停止条件和分支选择器的角色。

### 3.7 Report Writer（报告生成器）

Report Writer 负责把调研阶段的结构化结果转化成自然语言报告。它不是简单拼接，而是利用 LLM 根据论文列表生成一篇结构清晰、逻辑连贯的 Markdown 综述。

节点输入主要有两部分：一是 `topic`，二是最终的 `extracted_papers`。LLM 会围绕研究背景、方法演进、主要工作、趋势分析和结论建议等维度组织内容。系统还会在末尾追加附录，记录循环次数、论文数量和反思奖励等运行统计。

这个附录的意义在于把“生成结果”与“运行过程”绑定起来。报告不只是研究结论，也包含了智能体如何一步步得到这些结论的过程信息，这对实验复盘很重要。

## 4. Code Agent Subgraph 核心模块详细设计

当系统识别到有值得复现的 GitHub 代码时，就会进入代码复现子图。这个子图的设计思路非常接近实际工程师的排错流程：先拉代码，再看结构，再想怎么跑，跑失败后看错误，再做修复。

### 4.0 代码复现闭环总表

| 阶段 | 输入 | 核心实现 | 典型输出 |
|---|---|---|---|
| Repo Fetcher | `code_url` | `git clone --depth 1` + URL 标准化 | `repo_dir` |
| Code Parser | `repo_dir` | 读 README、依赖文件、入口文件和目录树 | `readme_content`, `requirements_content`, `entry_file` |
| Execution Planner | 解析结果 | LLM 生成 JSON 命令序列 | `execution_plan` |
| Executor | 命令序列 + 仓库目录 | Conda 环境隔离运行 | `status`, `current_step`, `error_type` |
| Error Analyzer | 错误日志 | LLM 生成修复建议 | `patch` |
| Patch Generator | 修复建议 | 执行命令或修改文件 | `fix_count`, `execution_logs` |

这个闭环的设计非常接近真实复现工作的节奏：先观察，再尝试，再失败，再分析，再修正。与其说这是一个“自动执行器”，不如说它是一个“自动排障流水线”。

### 4.1 Repo Fetcher（代码仓库克隆器）

Repo Fetcher 负责从 GitHub 获取真实代码仓库。它的输入是论文中的 `code_url`，输出是本地仓库路径 `repo_dir`。为了避免把论文页面、目录页或 blob 页面当成仓库，它会先对 URL 做标准化处理，去掉 `tree`、`blob` 和多余尾斜杠，然后再补 `.git`。

| 代码点 | 说明 |
|---|---|
| `_is_github_repo` | 先用正则判断是否是 GitHub 仓库链接 |
| `_normalize_repo_url` | 去掉 `tree/blob` 路径并补 `.git` |
| `WORKSPACE_DIR` | 统一把仓库放到 `outputs/repos/` |
| `shutil.rmtree(repo_dir)` | 克隆前清空旧仓库，避免脏目录影响 |

克隆时使用的是 `git clone --depth 1`，也就是浅克隆。这么做可以减少下载体积和时间，适合自动化复现场景。仓库会统一放到 `outputs/repos/` 下，确保与主项目隔离。

这个节点的价值在于把互联网上的代码链接变成可操作的本地工作区，是后续所有自动化复现步骤的物理起点。

### 4.2 Code Parser（代码树解析器）

Code Parser 的目标是快速回答三个问题：这个项目是什么、依赖是什么、怎么启动。

它会先尝试读取 README，因为 README 往往包含项目简介、安装方式和运行命令。随后会检查常见依赖文件，比如 `requirements.txt`、`setup.py`、`pyproject.toml` 和 `environment.yml`。接着它会从常见入口文件中猜测主入口，例如 `main.py`、`run.py`、`train.py`、`demo.py` 等；如果这些都没有，就回退到仓库中找到的第一个 Python 文件。

此外，它还会使用 `os.walk` 枚举目录结构，并限制层级深度，生成一个轻量的仓库树摘要。这个摘要的目的不是完整建模项目，而是给后续执行规划提供足够上下文。

Code Parser 的设计是一种典型的“启发式理解”方法。它不追求完全正确，但追求足够好，以便让执行计划生成器能够开始工作。

### 4.3 Execution Planner（执行指引规划器）

Execution Planner 的职责是把仓库信息翻译成可执行命令序列。它相当于让 LLM 扮演一个熟悉 Bash 和 Python 项目的运维助手，提前规划出一个最可能跑通的执行路径。

输入给它的主要上下文有 README、依赖文件内容、目录结构和入口文件名。LLM 根据这些信息输出一个 JSON 数组形式的命令列表，比如安装依赖、运行主程序、执行评测脚本等。系统将结果存入 `execution_plan`，并把 `current_step` 初始化为 0。

这个节点解决的是“从自然语言项目描述到具体命令”的转换问题。很多仓库并没有统一入口，直接盲跑通常会失败；有了执行规划，系统至少先有了一条合理的尝试路径。

### 4.4 Executor（环境隔离与沙盒执行器）

Executor 是代码复现子图里最接近真实执行环境的模块。它的核心思想是把每个仓库放进独立环境里跑，避免依赖冲突污染主环境，同时保留标准输出和标准错误用于后续分析。

| 执行细节 | 代码实现 | 作用 |
|---|---|---|
| 环境命名 | `sota_repo_{repo_name}` | 为每个仓库隔离依赖 |
| 环境创建 | `conda create -n ... python=3.10` | 保证基础运行环境一致 |
| 命令执行 | `conda run --no-capture-output` | 在目标环境中执行脚本 |
| 超时控制 | `TIMEOUT = 180` | 避免命令卡死 |
| 错误分类 | `_classify_error` | 为后续修复提供粗粒度信号 |

在实现上，系统会基于仓库名称创建对应的 Conda 环境，命名规则为 `sota_repo_{repo_name}`。第一次执行时会检查环境是否存在，如果没有则创建 Python 3.10 环境。随后每个命令都会通过 `conda run --no-capture-output` 在该环境下执行。

执行结果分成几类：
1. 成功执行，更新 `current_step`，继续下一个命令。
2. 命令失败，记录错误日志、错误类型和错误消息，进入错误分析阶段。
3. 命令超时，标记为 timeout，作为一种特殊错误处理。

错误类型会做粗分类，例如缺少模块、导入错误、文件不存在、语法错误、GPU 相关错误、权限错误、内存错误等。这个分类本身不一定能直接修复，但能帮助后面的 LLM 更快定位问题。

Executor 的本质是把“执行”与“观察”绑定在一起。它不只是跑命令，还记录足够多的执行痕迹，让系统有机会进行后续纠错。

### 4.5 Error Analyzer（修复分析评估器）

Error Analyzer 在代码复现流程中的角色类似于工程师读报错日志。它不直接改代码，而是根据执行失败的命令、错误类型、错误消息、仓库结构和依赖信息，判断问题出在哪里，以及更可能适合哪种修复方式。

LLM 输出的分析结果通常包括根因、修复类型、修复命令和需要修改的文件。修复类型可能是跳过当前步骤、替换命令、安装依赖，或者修改源代码。系统把这些信息写入 `patch` 状态，供下一个节点应用。

这个节点的价值在于把“错误”变成“可执行的修复建议”。在自动化复现里，失败不是终点，关键是失败后能否给出下一步最合理动作。

### 4.6 Patch Generator（自动补丁部署器）

Patch Generator 负责把错误分析结果真正落地。它支持三类典型修复：一是直接执行环境修复命令，二是替换当前执行计划中的命令，三是对源码做字符串级替换。

如果分析结果建议安装缺失依赖，它会在仓库目录中直接运行对应命令；如果建议更换执行命令，则更新 `execution_plan` 中当前步骤；如果建议修改文件，它会读取目标文件内容、匹配旧字符串并替换成新字符串。

修复过程中，`fix_count` 会递增，作为最大修复次数的统计。若累计修复超过 `MAX_CODE_FIX_LOOPS`，系统就会放弃当前仓库，避免无限循环。

这个节点体现的是“从建议到动作”的最后一跳。没有它，错误分析只能停留在文字层；有了它，系统才真正具备闭环修复能力。

## 5. 强化学习与动态优化机制

这套系统之所以不仅能跑一次，还能越跑越好，是因为它在流程外层加入了三种轻量强化学习式优化机制。这里的强化学习并不是传统的环境交互学习，而是更贴近“轨迹质量优化”的工程化设计。

### 5.0 奖励与采样总表

| 机制 | 实现文件 | 作用 | 输出 |
|---|---|---|---|
| 规则奖励 | [rl/reward.py](rl/reward.py) | 用固定权重给论文打分 | 标量奖励 |
| LLM 奖励 | [rl/reward.py](rl/reward.py) | 用 Judge LLM 评估论文 | 标量奖励 |
| Best-of-N | [rl/best_of_n.py](rl/best_of_n.py) | 多次抽取择优 | 最优论文列表 |
| 经验回放 | [rl/experience_buffer.py](rl/experience_buffer.py) | 存储成功轨迹 | Few-shot 示例 |

### 5.1 Reward Node（奖励评价系统）

Reward 的目标是把论文条目的质量转成可比较的分数。当前实现中，分数由四部分组成：完整度、相关性、代码可用性和时效性。

完整度衡量论文条目中关键信息是否填满，比如标题、年份、方法、数据集和贡献；相关性衡量条目与主题的贴合程度；代码可用性判断是否存在真实 GitHub 仓库；时效性则偏向较新的工作。

这种设计的意义在于把报告质量从“主观感觉”转成“可计算指标”。系统既可以用规则计算奖励，也可以调用 Judge LLM 做更语义化的评分。二者结合后，奖励既保留了稳定性，也保留了一定的理解能力。

### 5.2 Best-of-N 采样

Best-of-N 的思想是“同一个节点多生成几次，再选最好的结果”。它适用于输出波动较大的环节，尤其是 Info Extractor。因为结构化抽取很容易受提示词和上下文扰动影响，同一批输入多跑几次，结果可能差异很大。

系统会用较快的模型以一定温度生成多个候选抽取结果，再用奖励函数给每个候选打分，最后选得分最高者作为最终输出。这种方式不依赖复杂训练，却能显著提升单次运行的稳定性。

它的本质是把“随机生成”变成“多次尝试后的择优”。在研究型任务里，这比单次生成更稳健，也更接近人工筛选的行为模式。

### 5.3 Experience Buffer（经验回放）

Experience Buffer 用于保存高质量轨迹。每次系统运行结束后，它会把主题、查询策略、论文数量和平均奖励写入 `experience_buffer.json`，并按奖励从高到低保留有限数量的成功样本。

| 字段 | 含义 | 来自哪里 |
|---|---|---|
| `topic` | 本次研究主题 | 主图状态 |
| `queries` | 查询策略 | `search_queries` |
| `paper_count` | 论文数量 | `extracted_papers` 的长度 |
| `reward` | 轨迹奖励 | `reward_scores` 的平均值 |

这些样本不仅是日志，还会反过来用于后续任务的 Few-Shot 提示。也就是说，系统可以把“曾经成功过的搜索策略”拿出来，帮助下一次生成更好的查询或报告结构。

这个机制的价值在于经验复用。它让系统逐渐积累“什么样的搜索方式更容易得到高质量结果”，而不是每次运行都从头探索。

## 6. 实验设置

这一部分把系统“怎么跑、跑什么、用什么参数跑”说清楚。结合代码实现来看，本项目的实验设置不是传统单模型评测，而是一个带状态图、反思回路和代码执行子图的端到端工作流实验。

### 6.1 实验环境

| 项目 | 配置 | 代码依据 |
|---|---|---|
| 主流程框架 | LangGraph StateGraph | [graph.py](graph.py) |
| 代码复现子图 | LangGraph StateGraph | [code_agent/graph.py](code_agent/graph.py) |
| 主要搜索服务 | Tavily Search API | [agents/search_agent.py](agents/search_agent.py) |
| 主模型 | `LLM_MODEL=deepseek-ai/DeepSeek-V3` | [config.py](config.py) |
| 评审模型 | `JUDGE_MODEL=Qwen/Qwen2.5-72B-Instruct` | [config.py](config.py) |
| 快速采样模型 | `FAST_MODEL=deepseek-ai/DeepSeek-V3` | [config.py](config.py) |
| 代码隔离 | Conda 环境 `sota_repo_{repo_name}` | [code_agent/executor.py](code_agent/executor.py) |
| 输出目录 | `outputs/reports/`, `outputs/repos/` | [README.md](README.md) |

### 6.2 运行参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `MAX_SEARCH_LOOPS` | 3 | 调研反思最多循环 3 轮 |
| `BEST_OF_N` | 3 | 信息抽取时采样 3 个候选结果 |
| `MAX_CODE_FIX_LOOPS` | 5 | 代码复现最多修复 5 次 |
| Tavily 每轮返回数 | 5 | 每个查询抓取前 5 条结果 |
| Paper Filter Top-K | 20 | 过滤后最多保留 20 条搜索结果 |
| Code Extract Window | 前 15 条 | 供 Info Extractor 处理的原始搜索结果数 |

### 6.3 评测任务设置

本项目当前采用的评测对象并不是单一基准集，而是“主题驱动”的研究任务。也就是说，实验输入是一个研究主题，系统自动完成检索、抽取、反思、报告和复现。

| 任务类型 | 示例输入 | 主要观察点 |
|---|---|---|
| 文献调研 | `multimodal hallucination detection` | 论文召回、结构化抽取、报告质量 |
| 代码复现 | 论文中的 GitHub 仓库链接 | 环境构建、执行计划、修复闭环 |
| 经验复用 | 新主题与历史成功轨迹 | 查询策略是否被经验回放改善 |

### 6.4 关键实现片段

#### 主图的条件路由

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

这段代码说明主图并不是线性执行，而是根据反思结果动态转向搜索、报告或代码复现。

#### 代码执行的隔离环境

```python
env_name = _get_env_name(repo_dir)
result = _run_in_conda(cmd, env_name, repo_dir)
```

这段逻辑说明每个仓库都在独立 Conda 环境中执行，避免环境污染。

#### 奖励函数的四维加权

```python
total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
return round(total, 3)
```

奖励函数不是黑盒，而是显式组合完整度、相关性、代码可用性和时效性。

## 7. 运行结果

结合当前仓库的实现和附录记录，可以把系统运行结果分成调研结果、复现结果和学习结果三类。

### 7.1 调研结果

| 指标 | 当前实现观察 | 代码依据 |
|---|---|---|
| 输出形式 | Markdown 调研报告 | [agents/report_writer.py](agents/report_writer.py) |
| 文献结构 | 标题、年份、方法、数据集、贡献、代码链接 | [state.py](state.py) 中 `PaperInfo` |
| 代码链接控制 | 白名单校验 + HEAD 验证 | [agents/info_extractor.py](agents/info_extractor.py) |
| 结果压缩 | Top-K 过滤 + 反思重试 | [agents/paper_filter.py](agents/paper_filter.py)、[agents/reflector.py](agents/reflector.py) |

从运行路径看，调研结果不只是“找到一些论文”，而是形成了可以直接进入下一阶段的结构化知识。这个知识层会被报告生成器直接消费，也会在存在代码链接时进入复现分支。

### 7.2 复现结果

| 指标 | 当前实现观察 | 代码依据 |
|---|---|---|
| 仓库获取 | 支持 GitHub 仓库浅克隆 | [code_agent/repo_fetcher.py](code_agent/repo_fetcher.py) |
| 运行计划 | LLM 生成有序命令序列 | [code_agent/execution_planner.py](code_agent/execution_planner.py) |
| 错误反馈 | 分类错误类型并生成修复建议 | [code_agent/executor.py](code_agent/executor.py)、[code_agent/error_analyzer.py](code_agent/error_analyzer.py) |
| 自动修复 | 命令替换、依赖安装、文件级补丁 | [code_agent/patch_generator.py](code_agent/patch_generator.py) |

在 `code_agent/graph.py` 中，复现闭环由 `repo_fetcher → code_parser → execution_planner → executor → error_analyzer → patch_generator → executor` 组成。只要执行器还没到成功或放弃条件，图就会继续循环。

### 7.3 学习结果

| 机制 | 观察结果 | 代码依据 |
|---|---|---|
| Reflexion | 反思结果会重写下一轮查询 | [agents/reflector.py](agents/reflector.py) |
| Best-of-N | 多候选输出提升稳定性 | [rl/best_of_n.py](rl/best_of_n.py) |
| 经验回放 | 成功轨迹进入 JSON 持久化文件 | [rl/experience_buffer.py](rl/experience_buffer.py) |

从设计上看，系统的“运行结果”不只体现在最终产出，还体现在中间状态是否被改进：查询是否更聚焦、抽取是否更结构化、修复是否更快收敛。这也是该项目更像实验系统而不是单次脚本的关键。

### 7.4 运行结果示例

下面给出两类典型运行结果，分别对应调研任务和复现任务。

| 场景 | 典型输出 | 说明 |
|---|---|---|
| 主题调研 | 7 篇左右结构化论文 + Markdown 报告 | 结果进入 `outputs/reports/` |
| 代码复现 | 成功/失败状态 + 日志 + 修复轮次 | 结果由 Code Agent 输出 |

如果用附录中的当前记录来看，系统已经完成了调研链路、RL 机制和代码复现链路的主要实现，且加入了评估模块与消融实验工具。换句话说，实验结果不再只是“能不能跑”，而是“能不能稳定地产生可解释的中间状态和可验证的输出”。

## 8. 案例分析

这一部分把代码和运行行为对应起来，看系统在真实流程里是怎么工作的。

### 8.1 案例一：主题调研闭环

以 `multimodal hallucination detection` 这类主题为例，主图的执行顺序通常如下：

| 步骤 | 代码节点 | 发生了什么 |
|---|---|---|
| 1 | Query Planner | 生成多个搜索切面，如方法名、综述词、代码词 |
| 2 | Search Agent | 使用 Tavily 返回多个候选结果 |
| 3 | Paper Filter | 去掉重复 URL，保留高分结果 |
| 4 | Info Extractor | 抽取论文字段并校验 `code_url` |
| 5 | Reflector | 判断是否还缺少真实代码或关键方向 |
| 6 | Decision Node | 决定回搜、输出报告或进入复现 |

这个案例的关键不是某一轮搜索找到了多少条结果，而是系统能否把“发现不够”转化为下一轮搜索策略。例如，Reflector 会在没有真实 GitHub 代码时主动加强 `site:github.com {topic} implementation code` 这样的检索约束。

### 8.2 案例二：代码复现闭环

以一个典型 GitHub 仓库为例，Code Agent 的行为可以概括为：

| 步骤 | 代码节点 | 关键动作 |
|---|---|---|
| 1 | Repo Fetcher | 校验 URL 并浅克隆仓库 |
| 2 | Code Parser | 读取 README、requirements 和入口文件 |
| 3 | Execution Planner | 生成可执行命令列表 |
| 4 | Executor | 在 Conda 环境里执行命令 |
| 5 | Error Analyzer | 从报错中识别根因 |
| 6 | Patch Generator | 改命令、装依赖或补丁修复 |

这里最典型的实现点是，执行器会把错误类型转成明确的修复输入，而不是仅仅打印日志。例如 `missing_module` 通常对应安装依赖，`change_command` 对应替换执行计划中的命令。

### 8.3 案例三：经验回放如何影响下一轮任务

经验回放的作用不是立即让当前任务成功，而是让后续任务更快收敛。其工作方式可以概括为：

| 现象 | 代码对应 | 结果 |
|---|---|---|
| 任务结束后保存轨迹 | `experience_buffer.add(...)` | 成功轨迹进入 JSON 文件 |
| 轨迹按奖励排序 | `self.buffer.sort(...)` | 高质量样本排在前面 |
| 后续任务读取最优样本 | `sample_best(k)` | 作为 few-shot 示例 |

这说明系统已经不是“每次都从零开始猜”，而是在逐步形成一种任务层面的记忆。

### 8.4 案例四：代码片段解释

下面这段逻辑是主图最核心的停止与分支机制之一：

```python
if len(papers_with_code) >= 2:
	return "code_reproduction"
return "report"
```

它体现了一个很明确的工程决策：只有当结构化抽取到了足够多的可复现代码时，系统才进入复现分支，否则直接生成报告。这样做避免了在代码证据不足时强行进入复现，导致大量无效执行。

另一个关键片段是执行器中的状态推进：

```python
if result.returncode == 0:
	return {
		"current_step": step + 1,
		"status": "running",
	}
```

这段代码说明成功执行后并不会立即结束，而是继续推进到下一个命令；这也是复现闭环能够连续运行的基础。

## 9. 状态与控制设计

## 6. 状态与控制设计

整个系统的关键不是单个节点，而是状态如何流动。Research Graph 和 Code Agent 都围绕状态字典工作，节点之间通过字段传递信息，而不是通过函数参数硬编码。

### 6.1 Research Graph 状态表

| 状态字段 | 类型倾向 | 作用 | 由谁写入 |
|---|---|---|---|
| `topic` | 字符串 | 研究主题 | 用户输入 |
| `search_queries` | 字符串列表 | 搜索词集合 | Query Planner、Reflector |
| `raw_results` | 字典列表 | 原始搜索结果 | Search Agent、Paper Filter |
| `extracted_papers` | 字典列表 | 结构化论文条目 | Info Extractor、Best-of-N |
| `reflection_feedback` | JSON 字符串 | 反思结果 | Reflector |
| `reward_scores` | 浮点数列表 | 每轮奖励记录 | Reflector、Best-of-N |
| `loop_count` | 整数 | 搜索循环次数 | Reflector |

### 6.2 Code Agent 状态表

| 状态字段 | 类型倾向 | 作用 | 由谁写入 |
|---|---|---|---|
| `repo_url` | 字符串 | 目标仓库地址 | 论文代码链接 |
| `repo_dir` | 字符串 | 本地仓库路径 | Repo Fetcher |
| `readme_content` | 字符串 | 仓库说明文本 | Code Parser |
| `requirements_content` | 字符串 | 依赖声明文本 | Code Parser |
| `entry_file` | 字符串 | 推断入口文件 | Code Parser |
| `repo_structure` | 字符串 | 仓库结构摘要 | Code Parser |
| `execution_plan` | 字符串列表 | 执行命令序列 | Execution Planner |
| `current_step` | 整数 | 当前执行到第几步 | Executor |
| `error_message` | 字符串 | 错误详情 | Executor |
| `error_type` | 字符串 | 错误类别 | Executor |
| `patch` | JSON 字符串 | 修复建议 | Error Analyzer |
| `fix_count` | 整数 | 修复尝试次数 | Patch Generator |
| `status` | 字符串 | 当前执行状态 | 全流程节点 |

Research Graph 的关键状态包括：`topic`、`search_queries`、`raw_results`、`extracted_papers`、`reflection_feedback`、`reward_scores` 和 `loop_count`。这些字段分别表示主题、查询列表、原始搜索结果、结构化论文、反思结果、奖励分数和循环次数。

Code Agent 的关键状态包括：`repo_url`、`repo_dir`、`readme_content`、`requirements_content`、`entry_file`、`repo_structure`、`execution_plan`、`current_step`、`error_message`、`error_type`、`patch`、`fix_count` 和 `status`。这些字段覆盖了代码复现的完整生命周期。

这种状态设计有两个好处：一是便于调试，因为每个阶段都能看到中间产物；二是便于扩展，因为未来可以在不改大结构的情况下增加新的节点或新的分支条件。

## 10. 设计亮点与不足

这套系统的主要亮点在于把科研调研和工程复现统一到了同一个图式控制框架下。它不是“先搜再写”的简单脚本，而是一个具有显式反馈回路的智能工作流。它能够在搜索质量不够时继续迭代，在找到代码时自动进入复现，并在执行失败时尝试分析和修复。

另外，它还把结构化输出、验证机制和经验回放结合起来，减少了纯 LLM 生成中常见的空泛描述和幻觉风险。尤其是 GitHub 链接验证、去重排序和反思循环，这些机制明显提高了结果可靠性。

不足也比较明确。第一，很多判断仍然依赖 LLM 输出格式是否稳定，JSON 解析失败时需要回退。第二，代码修复目前以字符串级替换和命令级修复为主，面对复杂工程项目的能力有限。第三，搜索质量受外部搜索引擎和网络结果波动影响较大，主题较冷门时可能召回不足。第四，经验回放目前还是轻量级的轨迹缓存，尚未形成真正在线学习式的策略更新。

## 11. 结论

SOTA-Bench Agent 的价值在于把“文献调研”和“代码复现”这两项通常分散、人工成本很高的工作，整合成一个有状态、有反馈、有优化闭环的智能体系统。它的核心不是单次生成能力，而是持续搜索、主动反思、自动修复和经验积累的组合能力。

从实验角度看，这个系统展示了一个很清晰的方向：未来的研究助手不应只是内容生成器，而应该是能执行任务、能判断质量、能在失败后自动调整策略的工作流智能体。SOTA-Bench Agent 正是在这个方向上的一个完整原型。