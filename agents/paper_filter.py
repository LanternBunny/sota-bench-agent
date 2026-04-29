from state import ResearchState


def paper_filter(state: ResearchState) -> dict:
    raw = state.get("raw_results", [])

    seen_urls = set()
    unique = []
    for r in raw:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)

    scored = sorted(unique, key=lambda x: x.get("score", 0), reverse=True)

    top_results = scored[:20]

    return {"raw_results": top_results}
