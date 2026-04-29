EXTRACT_PROMPT = """你是一个 AI 论文信息提取专家。从以下搜索结果中提取论文/项目信息。

搜索结果：
{results}

研究主题：{topic}

对每条相关结果，提取以下字段：
- title: 论文/项目标题
- year: 发表年份（整数，未知则填 0）
- method: 核心方法/技术
- dataset: 使用的数据集或 benchmark
- code_url: 代码链接（没有则填 "unknown"）
- contribution: 主要贡献（一句话）
- relevance_score: 与主题的相关性（1-5 分）
- paper_type: 类型（paper / benchmark / code / survey / other）

只提取与研究主题相关的结果，忽略无关内容。
输出严格的 JSON 数组。不要输出其他内容。"""
