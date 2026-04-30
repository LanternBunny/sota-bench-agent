REPORT_JUDGE_PROMPT = """你是一个 AI 研究调研报告的评审专家。请对以下报告打分（1-5 分）。

研究主题：{topic}

报告内容：
{report}

评分维度：
1. completeness（完整性）：是否涵盖主要方法、数据集、benchmark
2. accuracy（准确性）：论文信息是否正确、引用是否合理
3. structure（结构性）：报告是否清晰有条理、表格是否规范
4. insight（洞察性）：是否提供有价值的趋势分析和方法分类
5. actionability（可操作性）：选题建议是否具体可行

输出严格的 JSON，不要输出其他内容：
{{"completeness": 1-5, "accuracy": 1-5, "structure": 1-5, "insight": 1-5, "actionability": 1-5, "overall": 1-5, "comments": "简短评语"}}"""
