import httpx
import asyncio
import json
import time
import sys
import os

BRAVE_API_KEY = "BSAKwJCuZGDeWzA4_T9gWNeM6sJafpT"

SECTIONS = {
    "Identity": "official established year location campus type head of institution address short name",
    "About": "detailed history mission vision summary about",
    "UG_Programs": "list of all undergraduate B.E. B.Tech degree programs and majors",
    "PG_Programs": "list of all postgraduate M.E. M.Tech MBA degree programs and specializations",
    "Fees": "undergraduate and postgraduate tuition fees per semester or year and total course cost and hostel fees",
    "Placements_General": "official 2024 placement report highest package average package average lpa median package",
    "Placement_Yearly_Counts": "yearly placement statistics 2024 2023 2022 total students graduated vs total students placed counts",
    "Placement_Gender_Stats": "gender wise placement report male vs female student placement percentages and counts",
    "Sector_Wise_Placements": "sector wise placement IT core engineering management finance healthcare companies hired 2024",
    "Rankings": "NIRF 2025 rankings NIRF 2024 QS World Ranking THE ranking global national score",
    "Infrastructure": "campus area in acres infrastructure facilities library lab hostel sports",
    "Faculty_Staff": "total number of faculty staff professors PhD faculty ratio student faculty ratio department wise",
    "Scholarships": "scholarships available merit based need based government scholarships amount eligibility criteria",
    "Student_Statistics": "total student enrollment count 2024 2023 undergraduate postgraduate PhD students admitted per year",
    "Student_Gender_Ratio": "male female student ratio gender diversity total male female students enrolled",
    "International_Students": "international students foreign students NRI students enrolled count countries represented"
}

async def fetch_section(client, college_name, section_name, query_context):
    url = "https://api.search.brave.com/res/v1/llm/context"
    headers = {"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"}
    query = f"{college_name} {query_context}"
    
    try:
        resp = await client.get(url, headers=headers, params={"q": query}, timeout=20.0)
        if resp.status_code == 200:
            data = resp.json()
            grounding = data.get("grounding", {})
            results = grounding.get("generic", [])
            
            section_data = {
                "section": section_name,
                "query": query,
                "sources": []
            }
            
            for res in results[:3]:
                source = {
                    "url": res.get("url"),
                    "snippets": res.get("snippets", [])
                }
                section_data["sources"].append(source)
            
            return section_data
        else:
            return {"section": section_name, "error": f"Status {resp.status_code}"}
    except Exception as e:
        return {"section": section_name, "exception": str(e)}

async def run_audit(college_name):
    start_time = time.time()
    print(f"🚀 Starting Parallel Audit for: {college_name}\n")
    
    async with httpx.AsyncClient() as client:
        tasks = [fetch_section(client, college_name, name, q) for name, q in SECTIONS.items()]
        results = await asyncio.gather(*tasks)
        
        final_json = {
            "college_name": college_name,
            "audit_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sections": results
        }
        
        # Save to file
        filename = college_name.lower().replace(" ", "_").replace(",", "").replace(".", "") + "_audit.json"
        with open(filename, "w") as f:
            json.dump(final_json, f, indent=2)
            
        print(f"✅ Audit results saved to: {filename}")
        print(f"🏁 {college_name} finished in {time.time() - start_time:.2f} seconds.")
        return final_json

if __name__ == "__main__":
    target_colleges = []
    if len(sys.argv) > 1:
        # Join all arguments as a single college name if not quoted, 
        # but for multiple colleges, users might pass them in quotes.
        # Simple approach: if multiple args, treat as separate colleges.
        target_colleges = sys.argv[1:]
    else:
        target_colleges = ["Kumaraguru College of Technology"]

    for col in target_colleges:
        asyncio.run(run_audit(col))
        print("-" * 50)
