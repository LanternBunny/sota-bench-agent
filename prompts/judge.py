JUDGE_PROMPT = """你是一个 AI 研究调研质量评审专家。请对以下论文提取结果打分。

研究主题：{topic}

论文信息：
{paper}

评分维度（每项 0-1 分）：
1. 信息完整度：必填字段（title, year, method, dataset, contribution）是否都有有效值
2. 与主题相关性：该论文与研究主题的相关程度
3. 代码可用性：是否提供了有效的代码链接
4. 时效性：年份是否在近 3 年内

输出严格的 JSON，不要输出其他内容：
{{"completeness": 0.0-1.0, "relevance": 0.0-1.0, "code_availability": 0.0-1.0, "recency": 0.0-1.0}}"""
