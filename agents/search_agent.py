from tavily import TavilyClient
from state import ResearchState
from config import TAVILY_API_KEY


def search_agent(state: ResearchState) -> dict:
    client = TavilyClient(api_key=TAVILY_API_KEY)
    queries = state["search_queries"]
    all_results = []

    for query in queries:
        try:
            response = client.search(
                query=query,
                max_results=5,
                search_depth="advanced",
                include_answer=False,
            )
            for r in response.get("results", []):
                all_results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                    "query": query,
                })
        except Exception as e:
            print(f"搜索失败 [{query}]: {e}")

    return {"raw_results": all_results}
