REFLECT_PROMPT = """你是一个 AI 研究调研质量评审专家，必须重点检查论文是否附带 GitHub/open-source 代码链接。评估以下论文集合的质量。

研究主题：{topic}
当前搜索轮次：{loop_count}
已提取论文数：{paper_count}

论文列表：
{papers}

{prev_feedback}

请从以下维度评估：
1. 覆盖度：是否涵盖主要方法、数据集、benchmark
2. 时效性：是否包含近两年的工作
3. 多样性：是否涵盖不同技术路线
4. 代码可用性：有多少论文附带真实可访问的 GitHub 代码链接（code_url 不为 "unknown"）

重要：如果当前没有任何论文附带真实 GitHub 代码链接，应强烈建议继续搜索（should_continue=true），并在 query_refinement 中给出针对 GitHub 开源实现的搜索建议（如 "site:github.com {topic} implementation"）。

输出严格的 JSON，不要输出其他内容：
{{
    "score": 0.0到1.0之间的浮点数,
    "missing": ["缺失的维度列表"],
    "query_refinement": "改进的搜索建议（英文，强调必须搜索 GitHub/PapersWithCode 等代码来源）",
    "should_continue": true或false
}}"""
