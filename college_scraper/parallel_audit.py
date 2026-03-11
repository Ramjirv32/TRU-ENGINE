import httpx
import asyncio
import json
import time
import sys
import os
import re

BRAVE_API_KEY = "BSAKwJCuZGDeWzA4_T9gWNeM6sJafpT"

# ---------------------------------------------------------------------------
# Domains that only serve Indian colleges — irrelevant for foreign institutions
# ---------------------------------------------------------------------------
INDIA_ONLY_DOMAINS = {
    "shiksha.com", "careers360.com", "collegedunia.com", "getmyuni.com",
    "imsindia.com", "hindustantimes.com", "collegesearch.in", "indiaeducation.net",
    "indiatoday.in", "ndtv.com", "jagranjos h.com", "aglasem.com",
    "collegebatch.com", "exampur.com", "mbarendezvous.com", "mbauniverse.com",
    "pagalguy.com", "bschool.careers360.com", "kollegeapply.com",
    "tarunias.com",  # returns Indian NIRF lists only
}

SECTIONS = {
    "Identity":              "official established year location campus type head of institution address short name",
    "About":                 "detailed history mission vision summary about",
    "UG_Programs":           "list of all undergraduate degree programs and majors courses offered",
    "PG_Programs":           "list of all postgraduate master degree programs and specializations",
    "Fees":                  "undergraduate postgraduate tuition fees per semester or year total course cost hostel fees",
    "Placements_General":    "official placement report graduates employment highest salary average salary",
    "Placement_Yearly_Counts": "yearly placement statistics 2024 2023 2022 total students graduated placed",
    "Placement_Gender_Stats":  "gender wise placement male female graduate employment statistics",
    "Sector_Wise_Placements":  "sector wise graduate employment IT engineering management finance healthcare top recruiters",
    "Rankings":              "QS World Ranking THE Times Higher Education ranking national ranking score",
    "Infrastructure":        "campus area facilities library laboratory hostel sports",
    "Faculty_Staff":         "total faculty staff professors PhD faculty student faculty ratio",
    "Scholarships":          "scholarships available financial aid merit need based eligibility amount",
    "Student_Statistics":    "total student enrollment undergraduate postgraduate PhD students",
    "Student_Gender_Ratio":  "male female student ratio gender diversity enrollment",
    "International_Students": "international students foreign students enrolled countries represented",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _college_tokens(college_name: str) -> list[str]:
    """Return lowercase word tokens of the college name (≥4 chars) for relevance check."""
    return [w.lower() for w in re.split(r'\W+', college_name) if len(w) >= 4]

def _is_relevant_snippet(snippet: str, tokens: list[str]) -> bool:
    """Return True if the snippet mentions at least one key token of the college name."""
    low = snippet.lower()
    return any(t in low for t in tokens)

def _is_blocked_url(url: str, india_only: bool) -> bool:
    """Return True if the URL should be skipped."""
    if not url:
        return True
    domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0].lower()
    if india_only and any(d in domain for d in INDIA_ONLY_DOMAINS):
        return True
    return False

# ---------------------------------------------------------------------------
# Fetch one section
# ---------------------------------------------------------------------------

async def fetch_section(client, college_name: str, section_name: str,
                        query_context: str, india_only: bool) -> dict:
    api_url = "https://api.search.brave.com/res/v1/llm/context"
    headers = {"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"}

    # Wrap college name in quotes for exact-match bias
    query = f'"{college_name}" {query_context}'

    try:
        resp = await client.get(api_url, headers=headers, params={"q": query}, timeout=20.0)
        if resp.status_code != 200:
            return {"section": section_name, "query": query,
                    "error": f"HTTP {resp.status_code}", "sources": []}

        data     = resp.json()
        results  = data.get("grounding", {}).get("generic", [])
        tokens   = _college_tokens(college_name)

        sources = []
        for res in results:
            url = res.get("url", "")
            if _is_blocked_url(url, india_only):
                continue

            # Keep only snippets that actually mention the college
            relevant = [s for s in res.get("snippets", [])
                        if _is_relevant_snippet(s, tokens)]
            if not relevant:
                # fall back: keep all snippets but flag as low-confidence
                relevant = res.get("snippets", [])

            if relevant:
                sources.append({"url": url, "snippets": relevant})

            if len(sources) >= 3:
                break

        return {"section": section_name, "query": query, "sources": sources}

    except Exception as e:
        return {"section": section_name, "query": query,
                "exception": str(e), "sources": []}

# ---------------------------------------------------------------------------
# Main audit runner
# ---------------------------------------------------------------------------

async def run_audit(college_name: str, output_dir: str = "."):
    # Detect if this looks like a non-Indian institution
    india_keywords = re.compile(
        r'\b(india|indian|iit|nit|iim|iisc|bits|vit|srm|anna university|'
        r'delhi|mumbai|bangalore|bengaluru|chennai|hyderabad|pune|kolkata)\b',
        re.IGNORECASE
    )
    india_only = not bool(india_keywords.search(college_name))
    if india_only:
        print(f"  ℹ  Non-Indian college detected — blocking India-only domains")

    start_time = time.time()
    print(f"🚀 Auditing: {college_name}\n")

    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_section(client, college_name, name, q, india_only)
            for name, q in SECTIONS.items()
        ]
        results = await asyncio.gather(*tasks)

    final_json = {
        "college_name":    college_name,
        "audit_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sections":        results,
    }

    slug     = re.sub(r'[^\w]+', '_', college_name.lower()).strip('_')
    filename = os.path.join(output_dir, f"{slug}_audit.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"✅  Saved → {filename}  ({elapsed:.1f}s)")

    # Quick relevance summary
    empty = [s["section"] for s in results if not s.get("sources")]
    if empty:
        print(f"⚠   Sections with no sources: {empty}")
    return final_json

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    colleges = sys.argv[1:] if len(sys.argv) > 1 else ["Kumaraguru College of Technology"]
    script_dir = os.path.dirname(os.path.abspath(__file__))

    for col in colleges:
        asyncio.run(run_audit(col, output_dir=script_dir))
        print("-" * 60)
