import httpx
import asyncio
import json
import os
import sys

BRAVE_API_KEY = "BSAKwJCuZGDeWzA4_T9gWNeM6sJafpT"

SECTIONS = {
    "Identity": "official established year location campus type head of institution address",
    "About": "history mission vision summary",
    "Ranking": "nirf ranking india ranking qs ranking world ranking"
}

async def fetch_section(client, college_name, section_name, query_context):
    api_url = "https://api.search.brave.com/res/v1/llm/context"
    headers = {"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"}
    query = f'"{college_name}" India {query_context}'
    
    try:
        resp = await client.get(api_url, headers=headers, params={"q": query}, timeout=30.0)
        if resp.status_code != 200:
            return {"section": section_name, "error": f"HTTP {resp.status_code}"}
        
        data = resp.json()
        results = data.get("grounding", {}).get("generic", [])
        
        if not results:
            return {"section": section_name, "error": "No data"}
        
        sources = []
        seen = set()
        
        for res in results:
            url = res.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            
            snippets = res.get("snippets", [])
            cleaned_snippets = []
            for s in snippets:
                s = ' '.join(s.split())
                if len(s) >= 50:
                    cleaned_snippets.append(s)
            
            if cleaned_snippets:
                sources.append({"url": url, "snippets": cleaned_snippets})
            
            if len(sources) >= 5:
                break
        
        return {"section": section_name, "sources": sources}
        
    except Exception as e:
        return {"section": section_name, "error": str(e)}

async def main(college_name):
    async with httpx.AsyncClient() as client:
        tasks = [fetch_section(client, college_name, name, q) for name, q in SECTIONS.items()]
        results = await asyncio.gather(*tasks)

    output = {"college_name": college_name, "data": {}}

    for res in results:
        if "error" in res:
            output["data"][res["section"]] = {"error": res["error"]}
        else:
            output["data"][res["section"]] = res["sources"]

    slug = college_name.lower().replace(' ', '_').replace('.', '_')
    filename = f"{slug}_about.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <college_name>")
    else:
        asyncio.run(main(" ".join(sys.argv[1:])))
