# SOTA-Bench Agent 项目规划

> 目标：构建一个从论文调研到代码复现的一体化智能体系统，融合强化学习思想实现自我改进闭环。

> 当前状态：主调研图、代码复现子图、奖励函数、Best-of-N、经验回放、评估模块和 Streamlit 界面均已实现；本文件同时作为项目规划与完成记录。

---

## 一、项目总览

### 1.1 定位

SOTA-Bench Agent 是一个面向 AI 研究主题的多级智能体系统：

- 输入一个研究主题
- 自动检索论文、代码、benchmark
- 结构化分析并生成调研报告
- （进阶）自动复现代码并验证结果

### 1.2 核心能力矩阵

| 能力 | 实现方式 | 对应模块 |
|------|---------|---------|
| Planning | Query Planner + Execution Planner | 查询规划 / 执行规划 |
| Tool Use | Search API / Docker / Git | 搜索 / 代码执行 |
| Memory | State + 向量存储 + 经验回放 | 状态管理 / 长期记忆 |
| Reflection | Reflexion 循环 + LLM-as-Judge | 反思模块 |
| Self-Improvement | 奖励信号 + 经验回放 + Best-of-N | RL 模块 |

### 1.3 等级路线

```
Level 2（调研 Agent）→ Level 2.5（反思 + RL 循环）→ Level 3（代码执行闭环）
```

### 1.4 已完成能力概览

| 能力 | 当前状态 | 对应实现 |
|------|---------|---------|
| 调研规划 | 已完成 | Query Planner + Search Agent + Paper Filter |
| 结构化抽取 | 已完成 | Info Extractor + GitHub URL 校验 |
| 反思循环 | 已完成 | Reflector + Decision Node |
| 报告生成 | 已完成 | Report Writer + Markdown 输出 |
| 代码复现闭环 | 已完成 | Repo Fetcher → Executor → Patch Generator |
| 奖励机制 | 已完成 | `rl/reward.py` |
| Best-of-N | 已完成 | `rl/best_of_n.py` |
| 经验回放 | 已完成 | `rl/experience_buffer.py` |
| 评估模块 | 已完成 | `evaluation/metrics.py`、`evaluation/ablation.py`、`evaluation/visualize.py` |

---

## 二、系统架构

### 2.1 LangGraph 主流程

```
用户输入研究主题
       │
       ▼
┌─────────────┐
│ Query Planner│  ← 生成多角度搜索查询
└──────┬──────┘
       ▼
┌─────────────┐
│ Search Agent │  ← 调用 Tavily/SerpAPI
└──────┬──────┘
       ▼
┌─────────────┐
│ Paper Filter │  ← 去重、筛选、排序
└──────┬──────┘
       ▼
┌──────────────┐
│Info Extractor │  ← 结构化提取论文信息
└──────┬───────┘
       ▼
┌─────────────┐
│  Reflector   │  ← 评估质量，生成反馈
└──────┬──────┘
       ▼
┌──────────────┐     ┌────────────────┐
│ Decision Node│────▶│ Report Writer  │ → 输出报告
└──────┬───────┘     └────────────────┘
       │ (有可复现代码)
       ▼
┌──────────────┐
│  Code Agent  │  ← 进入三级子图
└──────────────┘
```

### 2.2 Code Agent 子图

```
Repo Fetcher → Code Parser → Execution Planner
       │                            │
       │                            ▼
       │                     Code Executor
       │                            │
       │                     ┌──────┴──────┐
       │                     │ 成功?        │
       │                     ├── 是 → 记录结果，退出
       │                     └── 否 ↓
       │                     Error Analyzer
       │                            │
       │                     Patch Generator
       │                            │
       │                     (循环，最多 N 次)
       └────────────────────────────┘
```

### 2.3 状态设计

```python
from typing import TypedDict, Annotated
import operator

class PaperInfo(TypedDict, total=False):
  title: str
  year: int
  method: str
  dataset: str
  code_url: str
  contribution: str
  relevance_score: float
  paper_type: str


class ResearchState(TypedDict, total=False):
  topic: str
  search_queries: list[str]
  raw_results: Annotated[list[dict], operator.add]
  extracted_papers: list[PaperInfo]

  reflection_feedback: str
  reward_scores: Annotated[list[float], operator.add]
  loop_count: int

  final_report: str

  target_repo_url: str
  repo_files: dict[str, str]
  execution_logs: str
  reproduction_status: str
  code_reward_scores: Annotated[list[float], operator.add]
```

这版状态定义与当前代码一致，重点是把论文信息抽成 `PaperInfo`，并让可累加字段通过 `Annotated[..., operator.add]` 聚合。

---

## 三、强化学习策略

这是本项目的核心差异化设计。我们不做模型权重微调，而是在 Agent 运行时层面引入 RL 思想。

### 3.1 整体 RL 框架

```
                    ┌─────────────────────────┐
                    │     Environment          │
                    │  (搜索引擎 / 代码沙箱)     │
                    └────────┬────────────────┘
                             │ observation
                             ▼
┌──────────┐  action  ┌─────────────┐  reward  ┌──────────────┐
│  Policy  │ ───────▶ │   Agent     │ ◀─────── │ Reward Model │
│ (Prompt  │          │ (LangGraph) │          │ (LLM-Judge)  │
│ Selection)│         └─────────────┘          └──────────────┘
└──────────┘                │
      ▲                     │ trajectory
      │              ┌──────▼──────┐
      └───────────── │  Experience │
                     │   Buffer    │
                     └─────────────┘
```

### 3.2 三层 RL 机制

#### 第一层：Reflexion 循环（核心，必做）

在调研 Agent 中实现 Reflexion 模式：

```
Act → Evaluate → Reflect → Retry
```

具体实现：
- Agent 完成一轮搜索和信息提取后，Reflector 节点评估结果质量
- 生成结构化反馈：缺失维度、查询改进建议、置信度分数
- 反馈注入下一轮的 prompt context，指导 Agent 改进

```python
def reflector(state: ResearchState) -> dict:
    papers = state["extracted_papers"]
    feedback = llm.invoke(f"""
    评估以下论文集合的质量：
    {json.dumps(papers, ensure_ascii=False)}

    评估维度：
    1. 覆盖度（是否涵盖主要方法、数据集、benchmark）
    2. 时效性（是否包含最新工作）
    3. 多样性（是否涵盖不同技术路线）
    4. 代码可用性（有多少论文附带代码）

    输出 JSON：
    {{
        "score": 0.0-1.0,
        "missing": ["缺失的维度"],
        "query_refinement": "改进的搜索建议",
        "should_continue": true/false
    }}
    """)
    return {
        "reflection_feedback": feedback,
        "reward_scores": state["reward_scores"] + [feedback["score"]],
        "loop_count": state["loop_count"] + 1
    }
```

  当前实现中，反思节点还会在没有真实 GitHub 代码时自动增强查询，并把新查询写回 `search_queries`，这一点在 `agents/reflector.py` 里已经落地。

#### 第二层：Best-of-N 采样 + 奖励排序（推荐）

对关键节点（Query Planner、Info Extractor）生成 N 个候选输出，用奖励函数选最优：

```python
def best_of_n_extract(state: ResearchState, n: int = 3) -> dict:
    candidates = []
    for _ in range(n):
        result = info_extractor.invoke(state, temperature=0.7)
        score = reward_model.score(result, state["topic"])
        candidates.append((result, score))

    best = max(candidates, key=lambda x: x[1])
    return {"extracted_papers": best[0], "reward_scores": [..., best[1]]}
```

  当前代码默认在主图中启用 `best_of_n_extract`，以提高抽取稳定性。

奖励函数设计：

| 维度 | 权重 | 评分方式 |
|------|------|---------|
| 信息完整度 | 0.3 | 必填字段填充率 |
| 与主题相关性 | 0.3 | LLM-as-Judge 评分 |
| 代码可用性 | 0.2 | code_url 是否有效 |
| 时效性 | 0.2 | 年份加权 |

#### 第三层：经验回放 + Prompt 进化（加分项）

存储成功的 Agent 轨迹，在后续任务中作为 few-shot 示例：

```python
class ExperienceBuffer:
    def __init__(self, max_size=100):
        self.buffer = []

    def add(self, trajectory: dict, reward: float):
        self.buffer.append({"trajectory": trajectory, "reward": reward})
        self.buffer.sort(key=lambda x: x["reward"], reverse=True)
        self.buffer = self.buffer[:self.max_size]

    def sample_best(self, k=3) -> list:
        return self.buffer[:k]
```

  主图结束时会调用 `save_experience()` 将轨迹写入 `outputs/experience_buffer.json`，为后续任务提供 few-shot 示例。

将高奖励轨迹注入 prompt：

```python
def build_prompt_with_experience(topic, buffer):
    best_examples = buffer.sample_best(k=2)
    few_shot = "\n".join([
        f"示例：主题={ex['trajectory']['topic']}, "
        f"查询策略={ex['trajectory']['queries']}, "
        f"结果评分={ex['reward']}"
        for ex in best_examples
    ])
    return f"参考以下成功案例：\n{few_shot}\n\n当前主题：{topic}"
```

### 3.3 Code Agent 的 RL 闭环

代码复现模块天然适合 RL，因为有明确的奖励信号（代码是否执行成功）：

```
生成执行计划 → 执行 → 获取 reward
                         │
                    ┌─────┴─────┐
                    │ 成功(+1.0) │ 失败(-0.5) │
                    └─────┬─────┘
                          │
                   Error Analyzer
                          │
                   Patch Generator
                          │
                   重新执行（reward 累积）
```

奖励信号：

| 事件 | 奖励 |
|------|------|
| 依赖安装成功 | +0.2 |
| 代码无语法错误 | +0.3 |
| 代码执行完成 | +0.5 |
| 输出与论文结果一致 | +1.0 |
| 执行超时 | -0.3 |
| 运行时错误 | -0.5 |

---

## 四、微调策略

本项目以 Prompt Engineering + 运行时 RL 为主，但提供可选的轻量微调路径。

### 4.1 Prompt 层微调（零成本，必做）

不修改模型权重，通过优化 prompt 实现"微调"效果：

**Query Planner Prompt 迭代：**

```
版本 v1（基线）：
  "为研究主题生成搜索查询"

版本 v2（加入结构约束）：
  "生成 5 个搜索查询，覆盖：1 个综述类、2 个 benchmark 类、
   1 个 GitHub 代码类、1 个最新年份类"

版本 v3（加入经验回放）：
  "参考以下成功案例的查询策略：{few_shot}
   为当前主题生成搜索查询..."
```

通过 A/B 测试不同 prompt 版本，用奖励分数选择最优版本。

**Prompt 版本管理：**

```python
PROMPT_REGISTRY = {
    "query_planner": {
        "v1": "基线 prompt...",
        "v2": "结构化 prompt...",
        "v3": "经验增强 prompt...",
    }
}

PROMPT_SCORES = {
    "query_planner": {"v1": 0.65, "v2": 0.78, "v3": 0.85}
}

def select_prompt(agent_name: str) -> str:
    scores = PROMPT_SCORES[agent_name]
    best_version = max(scores, key=scores.get)
    return PROMPT_REGISTRY[agent_name][best_version]
```

### 4.2 DPO 偏好微调（可选进阶）

如果有 GPU 资源，可对小模型（如 Qwen2.5-7B）做 DPO 微调：

**数据收集：**
- 在 Agent 运行过程中，收集 (query, good_response, bad_response) 三元组
- good_response：奖励分数 > 0.8 的输出
- bad_response：奖励分数 < 0.4 的输出

**微调流程：**

```
收集偏好数据 → 构建 DPO 数据集 → 微调小模型 → 替换特定节点的 LLM
```

适用节点：Info Extractor（结构化输出质量直接影响下游）

**数据格式：**

```json
{
  "prompt": "从以下搜索结果中提取论文信息...",
  "chosen": {"title": "...", "method": "...", "score": 4.5},
  "rejected": {"title": "...", "method": "unknown", "score": 1.2}
}
```

### 4.3 RAG 增强（推荐）

用向量数据库存储已处理的论文，避免重复搜索：

```python
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
vectorstore = FAISS.from_documents(processed_papers, embeddings)

def search_with_rag(query: str, state: ResearchState):
    cached = vectorstore.similarity_search(query, k=3)
    if cached and cached[0].metadata["score"] > 0.85:
        return cached  # 命中缓存
    else:
        return search_api.search(query)  # 调用外部 API
```

---

## 五、评估策略

### 5.1 调研 Agent 评估

#### 自动评估指标

| 指标 | 计算方式 | 目标值 |
|------|---------|-------|
| 覆盖率 | 找到的相关论文数 / 金标准论文数 | > 0.7 |
| 准确率 | 提取信息正确的字段数 / 总字段数 | > 0.8 |
| 时效性 | 最近 2 年论文占比 | > 0.5 |
| 代码可用率 | 附带有效代码链接的论文占比 | > 0.3 |
| 报告质量 | LLM-as-Judge 1-5 分 | > 3.5 |

#### LLM-as-Judge 评估 Prompt

```python
JUDGE_PROMPT = """
你是一个 AI 研究调研报告的评审专家。请对以下报告打分（1-5）：

评分维度：
1. 完整性：是否涵盖主要方法、数据集、benchmark
2. 准确性：论文信息是否正确
3. 结构性：报告是否清晰有条理
4. 洞察性：是否提供有价值的分析和建议
5. 可操作性：选题建议是否具体可行

报告内容：
{report}

输出 JSON：
{{
    "completeness": 1-5,
    "accuracy": 1-5,
    "structure": 1-5,
    "insight": 1-5,
    "actionability": 1-5,
    "overall": 1-5,
    "comments": "..."
}}
"""
```

#### 对比基线

| 方法 | 描述 |
|------|------|
| 基线 A | 单次搜索，无反思 |
| 基线 B | 多次搜索，简单重试（papers < 5 则重试） |
| 本系统 | Reflexion + Best-of-N + 经验回放 |

预期结果：本系统在覆盖率和报告质量上显著优于基线。

### 5.2 Code Agent 评估

| 指标 | 计算方式 | 目标值 |
|------|---------|-------|
| 执行成功率 | 成功执行的 repo 数 / 总尝试数 | > 0.4 |
| 修复成功率 | 自动修复后成功的数 / 首次失败数 | > 0.3 |
| 平均修复轮次 | 成功修复所需的平均循环次数 | < 3 |
| 结果一致性 | 复现结果与论文报告值的偏差 | < 10% |

### 5.3 RL 效果评估

追踪奖励分数随循环次数的变化，验证 RL 机制的有效性：

```python
def plot_reward_curve(reward_history: List[float]):
    """绘制奖励曲线，展示 Agent 的自我改进趋势"""
    import matplotlib.pyplot as plt
    plt.plot(reward_history)
    plt.xlabel("Iteration")
    plt.ylabel("Reward Score")
    plt.title("Agent Self-Improvement Curve")
    plt.savefig("outputs/reward_curve.png")
```

评估维度：
- 奖励分数是否随循环次数递增（学习效果）
- 经验回放是否降低了新主题的搜索轮次（迁移效果）
- Best-of-N 是否优于单次生成（采样效果）

### 5.4 消融实验

| 实验 | 配置 | 目的 |
|------|------|------|
| Full System | Reflexion + Best-of-N + 经验回放 | 完整系统 |
| - Reflexion | 去掉反思循环 | 验证反思的价值 |
| - Best-of-N | 只生成 1 个候选 | 验证采样的价值 |
| - Experience | 不使用经验回放 | 验证记忆的价值 |

---

## 六、开发计划

### Phase 1：MVP 基础（Day 1-2）

**Day 1 上午：项目骨架 + 搜索接入**
- [ ] 初始化项目结构
- [ ] 接入 Tavily Search API
- [ ] 实现 Query Planner（v1 基线 prompt）
- [ ] 实现 Search Agent

**Day 1 下午：信息提取 + 基础流程**
- [ ] 实现 Paper Filter
- [ ] 实现 Info Extractor
- [ ] 用 LangGraph 串联基础流程
- [ ] 端到端测试：输入主题 → 输出结构化论文列表

**Day 2 上午：反思循环 + 报告生成**
- [ ] 实现 Reflector（Reflexion 模式）
- [ ] 实现 Decision Node
- [ ] 实现 Report Writer
- [ ] 完成二级 Agent 闭环

**Day 2 下午：RL 机制集成**
- [ ] 实现奖励函数（LLM-as-Judge）
- [ ] 实现 Best-of-N 采样
- [ ] 实现经验回放 Buffer
- [ ] 集成到 LangGraph 流程

### Phase 2：Code Agent + 评估（Day 3）

**Day 3 上午：Code Agent**
- [ ] 实现 Repo Fetcher（git clone）
- [ ] 实现 Code Parser（解析 README/requirements）
- [ ] 实现 Execution Planner
- [ ] 实现 Code Executor（Docker 沙箱）
- [ ] 实现 Error Analyzer + Patch Generator

**Day 3 下午：评估 + 界面 + 交付**
- [ ] 运行评估实验（对比基线 + 消融实验）
- [ ] 绘制奖励曲线
- [ ] Streamlit 界面
- [ ] 整理 README、输出示例

### Phase 3：可选进阶

- [ ] DPO 微调 Info Extractor
- [ ] RAG 缓存层
- [ ] LATS 树搜索（替代简单 Reflexion）
- [ ] 多主题批量评估

---

## 七、项目结构

```
sota_bench_agent/
├── app.py                      # Streamlit 入口
├── config.py                   # API Key、模型配置
├── graph.py                    # LangGraph 主图定义
│
├── agents/                     # 二级 Agent 模块
│   ├── query_planner.py
│   ├── search_agent.py
│   ├── paper_filter.py
│   ├── info_extractor.py
│   ├── reflector.py
│   ├── decision.py
│   └── report_writer.py
│
├── code_agent/                 # 三级 Code Agent 模块
│   ├── repo_fetcher.py
│   ├── code_parser.py
│   ├── execution_planner.py
│   ├── executor.py
│   ├── error_analyzer.py
│   └── patch_generator.py
│
├── rl/                         # 强化学习模块
│   ├── reward.py               # 奖励函数
│   ├── best_of_n.py            # Best-of-N 采样
│   ├── experience_buffer.py    # 经验回放
│   └── prompt_registry.py      # Prompt 版本管理
│
├── evaluation/                 # 评估模块
│   ├── judge.py                # LLM-as-Judge
│   ├── metrics.py              # 指标计算
│   ├── ablation.py             # 消融实验
│   └── visualize.py            # 奖励曲线可视化
│
├── prompts/                    # Prompt 模板
│   ├── query_planner.txt
│   ├── info_extractor.txt
│   ├── reflector.txt
│   └── report_writer.txt
│
├── outputs/                    # 输出目录
│   ├── reports/
│   ├── reward_curves/
│   └── experiments/
│
├── requirements.txt
└── README.md
```

---

## 八、技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 编排框架 | LangGraph | 原生支持状态图、条件分支、子图、循环 |
| 搜索 API | Tavily Search | 专为 Agent 设计，返回结构化结果 |
| LLM | DeepSeek / 智谱 / OpenAI | 按需选择，支持多模型切换 |
| 前端 | Streamlit | 快速原型，适合演示 |
| 代码沙箱 | Docker | 安全隔离执行环境 |
| 向量存储 | FAISS | 轻量级，无需外部服务 |
| 评估 | LLM-as-Judge + 规则指标 | 兼顾自动化和评估质量 |

---

## 九、风险与应对

| 风险 | 应对 |
|------|------|
| 搜索结果质量不足 | 多源搜索（Tavily + arXiv API + GitHub），Reflector 自动补充 |
| LLM 输出格式不稳定 | 使用 structured output / JSON mode，加入格式校验和重试 |
| API 调用成本 | 缓存机制 + RAG 避免重复搜索，Best-of-N 的 N 可配置 |
| 代码执行安全 | Docker 沙箱隔离，设置超时和资源限制 |
| 3 天时间紧张 | 优先级明确：Day1-2 完成二级 Agent + RL，Day3 做 Code Agent |

---

## 十、答辩亮点

1. **RL 闭环设计**：不是简单的 if-else 重试，而是有奖励信号、经验回放、策略优化的完整 RL 框架
2. **三层递进**：Reflexion → Best-of-N → 经验回放，从简单到复杂逐层叠加
3. **可量化评估**：有奖励曲线、消融实验、对比基线，用数据说话
4. **Code Agent 闭环**：代码执行 → 错误分析 → 自动修复 → 重新执行，天然的 RL 环境
5. **Prompt 进化**：通过奖励信号自动选择最优 prompt 版本，实现无权重微调的"微调"

---

## 附录：已完成工作记录

> 截至 2026-04-30

### Phase 1 完成情况

#### Level 2 调研 Agent（已完成 ✅）

- [x] 项目骨架搭建，接入 SiliconFlow API（DeepSeek-V3 + Qwen2.5-72B）
- [x] 接入 Tavily Search API
- [x] 实现 Query Planner — 生成 5 个多角度搜索查询
- [x] 实现 Search Agent — 调用 Tavily 结构化搜索
- [x] 实现 Paper Filter — 去重、评分排序、保留 Top 20
- [x] 实现 Info Extractor — LLM 结构化提取论文信息（title, year, method, dataset, code_url 等）
- [x] 实现 Reflector — Reflexion 模式，评估质量 + 生成反馈 + 决策是否继续
- [x] 实现 Decision Node — 条件路由（继续搜索 / 生成报告 / 触发代码复现）
- [x] 实现 Report Writer — 生成 Markdown 调研报告
- [x] LangGraph 主图串联，10 个节点完整闭环
- [x] 端到端测试通过：主题 "multimodal hallucination detection"，3 轮搜索，奖励 0.73→0.85 递增，输出 7 篇论文报告

#### RL 机制（已完成 ✅）

- [x] 奖励函数 — 规则评分 `compute_reward()` + LLM-as-Judge `compute_reward_llm()`
  - 四维加权：completeness 0.3, relevance 0.3, code_availability 0.2, recency 0.2
- [x] Best-of-N 采样 — N=3 候选，temperature=0.7，奖励排序选最优
- [x] 经验回放 Buffer — JSON 持久化存储，`sample_best()` + `get_few_shot_prompt()` 注入 prompt

### Phase 2 完成情况

#### Level 3 Code Agent（已完成 ✅）

- [x] Repo Fetcher — GitHub URL 校验 + `git clone --depth 1`
  - 修复：过滤非 GitHub 链接（arxiv、paperswithcode 等），避免无效克隆
  - 修复：`_normalize_repo_url()` 清理 /tree/ /blob/ 路径
- [x] Code Parser — 解析 README、requirements.txt、识别入口文件、构建目录树
- [x] Execution Planner — LLM 生成有序 bash 执行计划
- [x] Executor — **Conda 环境隔离**（非 Docker，轻量方案）
  - 每个 repo 创建独立 conda 环境 `sota_repo_{name}`
  - `conda run -n` 执行命令，避免污染主环境
  - 错误分类：missing_module / import_error / gpu_error / timeout 等 8 类
  - 提供 `cleanup_conda_env()` 清理函数
- [x] Error Analyzer — LLM 分析错误，输出修复类型（install_dep / modify_code / change_command / skip_step）
- [x] Patch Generator — 自动修复：替换命令、安装依赖、文件补丁
  - 修复：`change_command` 类型正确替换 execution_plan 中的命令
- [x] Code Agent 子图 — 条件路由闭环：fetch → parse → plan → execute → (success/analyze/give_up/next_step)
  - 修复：`_route_after_fetch` 处理克隆失败场景
- [x] 测试通过：`pallets/click` 仓库，6 步执行计划，1 次自动修复

#### Prompt 工程化（已完成 ✅）

- [x] 所有 prompt 提取到 `prompts/` 目录，集中管理
  - `query_planner.py`, `info_extractor.py`, `reflector.py`, `report_writer.py`
  - `judge.py`, `execution_planner.py`, `error_analyzer.py`
  - `__init__.py` 统一导出，支持 `from prompts import XXX`

#### Streamlit 应用（已完成 ✅）

- [x] 基础调研流程 UI — 输入主题、流式展示 Agent 节点进度、报告展示与下载
- [x] 代码复现 UI — 选择有 GitHub 代码的论文、触发 Code Agent、展示执行日志
- [x] 历史记录功能 — JSON 持久化（`outputs/history.json`），侧边栏展示最近 10 条，支持下载
- [x] UI 美化 — 自定义 CSS（指标卡片蓝色左边框、圆角展开器）、指标行（论文数/轮次/奖励）
- [x] 终端同步输出 — Python logging 模块，`log_event()` 同时写入终端和 Streamlit
- [x] 修复：报告下载格式 bug（去除 ` ```markdown ` 前缀）

### 技术选型变更

| 原计划 | 实际采用 | 原因 |
|--------|---------|------|
| Docker 沙箱 | Conda 环境隔离 | 更轻量，无需 Docker 守护进程，用户偏好 |
| Tavily + arXiv API | 仅 Tavily | Tavily 已覆盖学术搜索需求 |
| DeepSeek / 智谱 / OpenAI | SiliconFlow（DeepSeek-V3 + Qwen2.5-72B） | 统一 API 入口，成本可控 |
| prompts/*.txt | prompts/*.py | Python 模块更便于导入和维护 |

### 待完成项

- [ ] DPO 偏好微调（需 GPU 资源）
- [ ] RAG 缓存层（FAISS 向量存储）
- [ ] LATS 树搜索（替代简单 Reflexion）
- [ ] Prompt 版本管理与自动选择（prompt_registry.py）
- [ ] 多主题批量评估

### 评估模块（已完成 ✅）

- [x] `evaluation/metrics.py` — 指标计算
  - `compute_metrics()`: 从 ResearchState 提取 paper_count / coverage / recency / code_availability / avg_reward / reward_curve
  - `compute_report_quality()`: LLM-as-Judge 报告质量评估（completeness / accuracy / structure / insight / actionability，1-5 分）
- [x] `evaluation/ablation.py` — 消融实验运行器
  - 四种配置：full / no_reflexion / no_best_of_n / no_experience
  - `run_single()`: 单主题单配置运行，临时 patch config 实现配置切换
  - `run_ablation()`: 多主题批量运行，结果保存到 `outputs/ablation_results.json`
  - CLI 入口：`python -m evaluation.ablation "topic1" "topic2"`
- [x] `evaluation/visualize.py` — matplotlib 可视化
  - `plot_reward_curve()`: 单次运行奖励曲线（迭代轮次 vs reward）
  - `plot_ablation_comparison()`: 消融实验分组柱状图（4 配置 × 4 指标）
  - `plot_experience_trend()`: 跨运行奖励趋势（经验回放效果）
  - 支持 `save_path` 保存 PNG 和 Streamlit `st.pyplot()` 展示
- [x] `prompts/report_judge.py` — 报告质量评估 prompt（REPORT_JUDGE_PROMPT）
- [x] `app.py` 集成评估面板
  - 侧边栏：消融实验入口（输入主题 → 运行 4 种配置）
  - 页面底部：评估面板（历史奖励趋势 tab + 消融实验结果 tab）
  - 调研完成后自动展示当次运行的奖励曲线

### 实验报告输出（已完成 ✅）

- [x] `SOTA_Bench_Agent_Experiment_Report.md` — 实验报告补全
  - 新增“实验设置、运行结果、案例分析”章节
  - 增加表格化展示：节点职责、状态字段、关键参数、奖励机制
  - 补充代码片段说明：主图路由、代码执行隔离、奖励函数加权

### Code URL 虚假链接修复（已完成 ✅）

- [x] 强化 EXTRACT_PROMPT — 明确要求 code_url 只能填搜索结果原文中实际出现的链接，禁止编造
- [x] info_extractor 双重 URL 验证
  - `_extract_urls_from_raw()`: 从搜索结果原文正则提取所有 GitHub URL 作为白名单
  - 白名单过滤：LLM 提取的 code_url 不在白名单中 → 标记为 unknown
  - `_validate_github_url()`: HTTP HEAD 请求验证仓库是否真实存在
- [x] query_planner 优化 — GitHub 查询改为 `site:github.com {topic} implementation` 格式
