EXTRACT_PROMPT = """你是一个 AI 论文信息提取专家。从以下搜索结果中提取论文/项目信息。请使用中文输出中文字段，专业术语可保留英文。

搜索结果：
{results}

研究主题：{topic}

对每条相关结果，提取以下字段：
- title: 论文/项目标题
- year: 发表年份（整数，未知则填 0）
- method: 核心方法/技术（中文描述）
- dataset: 使用的数据集或 benchmark
- code_url: 代码仓库链接（**必须是搜索结果原文中明确出现的 URL**，不要自行推测或编造链接。如果原文没有提供代码链接，填 "unknown"）
- download_url: 论文下载链接。如果搜索结果提供 download_url，优先使用；arxiv/openreview 可使用结果中已经转换好的 pdf 链接；没有则填空字符串。
- contribution: 主要贡献（一句话中文总结）
- relevance_score: 与主题的相关性（1-5 分）
- paper_type: 类型（paper / benchmark / code / survey / other）

重要规则：
1. 只提取与研究主题相关的结果，忽略无关内容
2. code_url 只能填写搜索结果原文中实际包含的链接，绝对不要凭记忆或猜测填写 GitHub 链接
3. 如果搜索结果中的链接指向 arxiv、博客、新闻网站等非代码仓库，code_url 应填 "unknown"
4. 如果搜索结果里包含 code_url 字段且是 GitHub 仓库链接，应优先作为该条目的 code_url

输出严格的 JSON 数组。不要输出其他内容。"""
