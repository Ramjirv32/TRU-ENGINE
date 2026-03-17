import subprocess
import json
import time
import re
import concurrent.futures

API_KEY = "c138d04299d00500bdf9168ba3a04143fadcae1fab8437f2c4bb9b5437dc24d8"

COLLEGES = [
    {"name": "National Institute of Technology Tiruchirappalli", "country": "India", "location": "Tiruchirappalli, Tamil Nadu"},
]

QUERIES = {
    "basic_info": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified institutional data for the 2024-2025 academic year or 2023-24 if 2024-25 is not published. Return only valid JSON with the exact fields: college_name, short_name, established, institution_type, country, location, website, about, summary, rankings (nirf_2025, nirf_2024, qs_world, national_rank, state_rank, guessed_data), student_statistics (total_enrollment, ug_students, pg_students, phd_students, annual_intake, male_percent, female_percent, total_ug_courses, total_pg_courses, total_phd_courses, guessed_data), faculty_staff (total_faculty, student_faculty_ratio, phd_faculty_percent, guessed_data), student_history (student_count_comparison_last_3_years with 2024, 2023, 2022, international_students, guessed_data), accreditations (body, grade, year), affiliations, recognition, campus_area, contact_info (phone, email, address), and sources_verified (array of URLs or document names). If a number is not known, use N/A; if a string is not known, use N/A. Do not add any extra text, only JSON.",
    "programs": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), list every officially offered UG, PG, and PhD program and department as of 2024-25. Use only official college website, NIRF 2024/2025, AICTE, or UGC‑recognized sources. Do not invent any program. Return only valid JSON with keys: ug_programs (list of strings), pg_programs (list of strings), phd_programs (list of strings), departments (list of strings). If a level has no programs, use an empty array []. Include a \"sources_verified\" array with URLs or document names.",
    "placements": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest verified placement data for 2023 or 2024 if available. Use only official placement reports, NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": 2023, \"sources\": [\"source URL or document name\"], \"placements\": {\"year\": 2023, \"highest_package\": real_number, \"average_package\": real_number, \"median_package\": real_number, \"package_currency\": \"LPA\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"placement_rate_percent\": real_percent, \"total_students_placed\": integer, \"total_companies_visited\": integer, \"graduate_outcomes_note\": \"factual note\"}, \"placement_comparison_last_3_years\": [{\"year\":2023, \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":2022, \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":2021, \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}], \"gender_based_placement_last_3_years\": [{\"year\":2023, \"male_placed\": integer, \"female_placed\": integer, \"male_percent\": real_percent, \"female_percent\": real_percent}], \"sector_wise_placement_last_3_years\": [{\"year\":2023, \"sector\": \"sector name\", \"companies\": [\"company names\"], \"percent\": real_percent}], \"top_recruiters\": [\"company names\"], \"placement_highlights\": \"2-3 sentence factual summary\"}. If exact numbers are unavailable, use conservative estimates and set \"guessed_data\": true. Do not inflate numbers; for Indian Tier‑2 private engineering colleges, average package is usually 5–8 LPA. Do not return any extra text, only JSON.",
    "fees": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest official fee structure for 2024-2025 or 2023-2024 if 2024-2025 is not published. Use only official college website, AICTE mandatory disclosure, NIRF, or UGC‑recognized portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"2024-25\", \"sources\": [\"official fee PDF URL or document name\"], \"fees\": {\"UG\": {\"per_year\": real_number_or_NA, \"total_course\": real_number_or_NA, \"currency\": \"INR\" for India, \"USD\" for US, \"GBP\" for UK}, \"PG\": {\"per_year\": real_number_or_NA, \"total_course\": real_number_or_NA, \"currency\": string}, \"hostel_per_year\": real_number_or_NA}}, \"fees_by_year\": [{\"year\": \"2024\", \"program_type\": \"UG\", \"per_year_local\": real_number_or_NA, \"total_course_local\": real_number_or_NA, \"hostel_per_year_local\": real_number_or_NA, \"currency\": string}, {\"year\": \"2024\", \"program_type\": \"PG\", \"per_year_local\": real_number_or_NA, \"total_course_local\": real_number_or_NA, \"hostel_per_year_local\": real_number_or_NA, \"currency\": string}], \"fees_note\": \"short description\", \"scholarships_detail\": [{\"name\": \"scholarship name\", \"amount\": real_number_or_NA, \"eligibility\": \"criteria\", \"provider\": \"who\"}]}. If exact fee is not published, provide a realistic estimate and set \"guessed_data\": true. Do not use 0 for amounts; use N/A instead. Do not add any extra text, only JSON.",
    "infrastructure": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), describe the existing campus infrastructure for 2024-25. Only list facilities that actually exist. Return only valid JSON with: {\"guessed_data\": false, \"sources_verified\": [\"official URL or document\"], \"infrastructure\": [{\"facility\": \"facility name\", \"details\": \"description\"}], \"hostel_details\": {\"available\": true_or_false, \"boys_capacity\": integer_or_NA, \"girls_capacity\": integer_or_NA, \"total_capacity\": integer_or_NA, \"type\": \"description\"}, \"library_details\": {\"total_books\": integer_or_NA, \"journals\": \"description\", \"e_resources\": [\"e‑resource names\"], \"area_sqft\": integer_or_NA}, \"transport_details\": {\"buses\": integer_or_NA, \"routes\": \"description\"}}. If capacities are unknown but can be reasonably estimated, use estimates and set \"guessed_data\": true. Do not invent facilities. Do not add any extra text, only JSON.",
}

def build_curl_command(query, college):
    q = query.replace("%COLLEGE_NAME%", college["name"]).replace("%COUNTRY%", college["country"]).replace("%LOCATION%", college["location"])
    cmd = ["curl", "--get", "https://serpapi.com/search", "--data-urlencode", "engine=google_ai_mode", "--data-urlencode", f"q={q}", "--data-urlencode", f"api_key={API_KEY}"]
    return cmd

def run_curl(cmd):
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    return result.stdout, elapsed

def extract_reconstructed_markdown(response_text):
    try:
        data = json.loads(response_text)
        return data.get("reconstructed_markdown", ""), None
    except:
        return None, "Error"

def extract_json_from_markdown(markdown):
    match = re.search(r"```json\s*(.*?)\s*```", markdown, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1)), None
        except:
            return None, "Parse error"
    return None, "No json block"

def main():
    results = {"total_start_time": time.time(), "colleges": {}}
    
    all_tasks = []
    for college in COLLEGES:
        for query_type, query in QUERIES.items():
            all_tasks.append({"college": college["name"], "query_type": query_type, "cmd": build_curl_command(query, college)})
    
    print(f"Running {len(all_tasks)} parallel curl requests...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(run_curl, t["cmd"]): t for t in all_tasks}
        
        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            stdout, elapsed = future.result()
            markdown, _ = extract_reconstructed_markdown(stdout)
            parsed, _ = extract_json_from_markdown(markdown)
            
            college_name = task["college"]
            if college_name not in results["colleges"]:
                results["colleges"][college_name] = {"queries": {}, "total_time": 0}
            
            results["colleges"][college_name]["queries"][task["query_type"]] = {
                "reconstructed_markdown": markdown,
                "parsed_json": parsed,
                "time_taken_seconds": round(elapsed, 2)
            }
            results["colleges"][college_name]["total_time"] += elapsed
            print(f"✓ {task['query_type']}: {elapsed:.2f}s")
    
    results["total_time_taken_seconds"] = round(time.time() - results["total_start_time"], 2)
    
    with open("/home/ramji/Videos/scap/college_scraper/nit_trichy_full_serper.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nTotal wall time: {results['total_time_taken_seconds']}s")
    print(f"Saved to: nit_trichy_full_serper.json")

if __name__ == "__main__":
    main()
