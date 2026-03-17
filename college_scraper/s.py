import httpx, asyncio, json, time, sys, os, re

SERP_API_KEY = "c138d04299d00500bdf9168ba3a04143fadcae1fab8437f2c4bb9b5437dc24d8"

# Multiple queries per section to improve coverage
QUERIES = {
    "Student_Statistics": [
     

"Udayana University students"

"Udayana University enrollment"

"Udayana University total student count"
    ]
}

async def fetch_serpapi(client, college, section, query_text):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_ai_mode",
        "q": f"{college} {query_text}",
        "api_key": SERP_API_KEY
    }

    try:
        res = await client.get(url, params=params, timeout=30.0)
        if res.status_code != 200:
            return {
                "section": section,
                "query": params["q"],
                "error": f"HTTP {res.status_code}",
                "sources": []
            }

        data = res.json()
        sources = []

        # ✅ AI Mode block
        ai_block = data.get("ai_mode", {})
        for item in ai_block.get("sources", [])[:10]:
            sources.append({
                "url": item.get("link"),
                "title": item.get("title"),
                "snippet": item.get("snippet", "")
            })

        # ✅ Answer Box fallback
        answer_box = data.get("answer_box", {})
        if answer_box and answer_box.get("snippet"):
            sources.append({
                "url": answer_box.get("link"),
                "title": answer_box.get("title"),
                "snippet": answer_box.get("snippet")
            })

        # ✅ Organic Results fallback
        if not sources:
            for r in data.get("organic_results", [])[:10]:
                sources.append({
                    "url": r.get("link"),
                    "title": r.get("title"),
                    "snippet": r.get("snippet", "")
                })

        # ✅ Filter snippets with numbers (likely student counts)
        filtered_sources = []
        for s in sources:
            if re.search(r"\d{3,}", s.get("snippet", "")):
                filtered_sources.append(s)

        return {
            "section": section,
            "query": params["q"],
            "sources": filtered_sources or sources
        }

    except Exception as e:
        return {
            "section": section,
            "query": params["q"],
            "exception": str(e),
            "sources": []
        }

async def run(college, out="."):
    print(f"🚀 SERPAPI Scraping: {college}")

    async with httpx.AsyncClient() as client:
        results = []
        for sec, queries in QUERIES.items():
            section_results = await asyncio.gather(*[
                fetch_serpapi(client, college, sec, q) for q in queries
            ])
            merged_sources = []
            for r in section_results:
                merged_sources.extend(r["sources"])
            results.append({
                "section": sec,
                "query": "; ".join(queries),
                "sources": merged_sources
            })

    slug = college.lower().replace(" ", "_")
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    output = {
        "college_name": college,
        "scraped_at": ts,
        "sections": results
    }

    # Save file
    fname = os.path.join(out, f"{slug}_serp_student_stats.json")
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Console output
    for r in results:
        print(f"  {'✅' if r['sources'] else '❌'} {r['section']} → {len(r['sources'])} sources")

    print(f"✅ Saved → {fname}")

if __name__ == "__main__":
    colleges = sys.argv[1:] or ["Udayana University"]
    for c in colleges:
        asyncio.run(run(c, os.path.dirname(os.path.abspath(__file__))))
