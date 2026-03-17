import subprocess, json, time, re, concurrent.futures

API_KEY = "c138d04299d00500bdf9168ba3a04143fadcae1fab8437f2c4bb9b5437dc24d8"
COLLEGE = {"name": "RVS College of Engineering and Technology", "country": "India", "location": "Tamil Nadu"}

QUERIES = {
    "basic_info": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified institutional data for the 2024-2025 academic year. Return only valid JSON with the exact fields: college_name, short_name, established, institution_type, country, location, website, about, summary, rankings, student_statistics, faculty_staff, student_history, accreditations, affiliations, recognition, campus_area, contact_info, sources_verified. If unknown, use N/A. Do not add any extra text, only JSON.",
    "programs": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), list every officially offered UG, PG, and PhD program and department as of 2024-25. Return only valid JSON with keys: ug_programs, pg_programs, phd_programs, departments, sources_verified. Do not add any extra text, only JSON.",
    "placements": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest verified placement data for 2023 or 2024. Return only valid JSON with: guessed_data, data_year, sources, placements, placement_comparison_last_3_years, top_recruiters, placement_highlights. Do not add any extra text, only JSON.",
    "fees": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest official fee structure for 2024-25. Return only valid JSON with: guessed_data, data_year, sources, fees, fees_by_year, fees_note, scholarships_detail. Do not add any extra text, only JSON.",
    "infrastructure": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), describe the existing campus infrastructure for 2024-25. Return only valid JSON with: guessed_data, sources_verified, infrastructure, hostel_details, library_details, transport_details. Do not add any extra text, only JSON."
}

def run_curl(qt, query):
    q = query.replace("%COLLEGE_NAME%", COLLEGE["name"]).replace("%COUNTRY%", COLLEGE["country"]).replace("%LOCATION%", COLLEGE["location"])
    cmd = ["curl", "--get", "https://serpapi.com/search", "--data-urlencode", "engine=google_ai_mode", "--data-urlencode", f"q={q}", "--data-urlencode", f"api_key={API_KEY}"]
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    try:
        data = json.loads(result.stdout)
        markdown = data.get("reconstructed_markdown", "")
        match = re.search(r"```json\s*(.*?)\s*```", markdown, re.DOTALL)
        parsed = json.loads(match.group(1)) if match else None
    except Exception as e:
        parsed = None
        print(f"Error: {e}")
    return qt, parsed, elapsed

results = {"total_start_time": time.time(), "colleges": {}}
results["colleges"][COLLEGE["name"]] = {"queries": {}, "total_time": 0}

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(run_curl, qt, q): qt for qt, q in QUERIES.items()}
    for future in concurrent.futures.as_completed(futures):
        qt, parsed, elapsed = future.result()
        results["colleges"][COLLEGE["name"]]["queries"][qt] = {"parsed_json": parsed, "time_taken_seconds": round(elapsed, 2)}
        results["colleges"][COLLEGE["name"]]["total_time"] += elapsed
        print(f"✓ {qt}: {elapsed:.2f}s")

results["total_time_taken_seconds"] = round(time.time() - results["total_start_time"], 2)
with open("/home/ramji/Videos/scap/college_scraper/rvs_cet_serper.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nTotal: {results['total_time_taken_seconds']}s")
