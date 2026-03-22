import subprocess
import json
import time
import os
import re
import concurrent.futures

API_KEY = "79883d891d5add0dd4ed54fc5843da80bdda387a2e56a4c94de154261e0928e5"

COLLEGES = [
    {"name": "University of Melbourne", "country": "Australia", "location": "Melbourne"},
]

QUERIES = {
    "basic_info": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified institutional data for the current academic year and the past three years. Return only valid JSON with the exact fields: college_name, short_name, established, institution_type, country, location, website, about, summary, rankings (nirf_rank, qs_world, national_rank, state_rank, guessed_data), student_statistics (total_enrollment, ug_students, pg_students, phd_students, annual_intake, male_percent, female_percent, total_ug_courses, total_pg_courses, total_phd_courses, guessed_data), faculty_staff (total_faculty, student_faculty_ratio, phd_faculty_percent, guessed_data), student_history (student_count_comparison_last_3_years, international_students, guessed_data), accreditations (MUST be a list of objects with fields: body, grade, year), affiliations, recognition, campus_area, contact_info (phone, email, address), and sources_verified (array of URLs or document names). IMPORTANT: Provide student count comparisons specifically for the current year and the two preceding years. GUIDELINES FOR MISSING DATA: 1) If exact numbers aren't available, make educated estimates based on typical university patterns. 2) Always mark guessed_data field with what was estimated. If no reasonable estimate possible, use 'Not Available'. Do not add any extra text, only JSON.",
    "programs": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), list every officially offered UG, PG, and PhD program and department as of the current academic session. Use only official college website, latest NIRF, AICTE, or UGC‑recognized sources. Do not invent any program. Return only valid JSON with keys: ug_programs (list of strings), pg_programs (list of strings), phd_programs (list of strings), departments (list of strings). If a level has no programs, use an empty array []. Include a \"sources_verified\" array with URLs or document names.",
    "details": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide a comprehensive report covering PLACEMENTS, FEES, and INFRASTRUCTURE for the current year and past 2 years. Return only valid JSON with exactly three keys: 'placements', 'fees', and 'infrastructure'. \n1) 'placements': {guessed_data, data_year, sources, placements: {year, highest_package, average_package, median_package, package_currency, placement_rate_percent, total_students_placed, total_companies_visited, graduate_outcomes_note}, placement_comparison_last_3_years (current and prior 2 years), gender_based_placement, sector_wise_placement, top_recruiters, placement_highlights}.\n2) 'fees': {guessed_data, data_year, sources, fees: {UG: {per_year, total_course, currency}, PG: {per_year, total_course, currency}, hostel_per_year}, fees_by_year (current and prior 2 years), fees_note, scholarships_detail: [{name, amount, eligibility, provider}]}.\n3) 'infrastructure': {guessed_data, sources_verified, infrastructure: [{facility, details}], hostel_details: {available, total_capacity, type}, library_details: {total_books, journals, e_resources, area_sqft}, transport_details: {buses, routes}}. \nIMPORTANT: Maintain the exact structure for each section. If data is missing, make educated estimates and set 'guessed_data' to true with details. Use 'Not Available' only if zero estimates are possible. Return only JSON."
}

def build_curl_command(query, college):
    q = query.replace("%COLLEGE_NAME%", college["name"]).replace("%COUNTRY%", college["country"]).replace("%LOCATION%", college["location"])
    cmd = [
        "curl", "--get", "https://serpapi.com/search",
        "--data-urlencode", "engine=google_ai_mode",
        "--data-urlencode", f"q={q}",
        "--data-urlencode", f"api_key={API_KEY}"
    ]
    return cmd

def run_curl(cmd):
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    return result.stdout, elapsed

def extract_structured_json(md_text):
    if not md_text:
        return {}
    
    # 1. Strip all code block markers
    text = re.sub(r'```(?:json)?', '', md_text).strip()
    
    # 2. Find the first '{' and last '}' to isolate the JSON object
    start = text.find('{')
    end = text.rfind('}')
    
    if start == -1 or end == -1:
        # No braces found, might be raw or invalid
        try:
            return json.loads(text)
        except:
            return {"raw_output": md_text, "error": "No JSON braces found"}
            
    json_str = text[start:end+1]
    
    # 3. Clean common LLM formatting issues (backslashes before underscores, hyphens)
    # This is often seen when LLMs generate JSON inside markdown
    json_str = json_str.replace('\\_', '_').replace('\\-', '-')
    
    # 3. Try parsing
    try:
        # Try strict first
        return json.loads(json_str)
    except Exception as first_error:
        try:
            # Try non-strict to allow literal newlines/control chars
            return json.loads(json_str, strict=False)
        except Exception as second_error:
            # Final attempt: try to fix common trailing comma or other minor issues
            # If still failing, return the error and raw content
            return {
                "raw_output": md_text, 
                "error": f"JSON parse error: {str(first_error)}",
                "extracted_content": json_str
            }

def extract_reconstructed_markdown(response_text):
    try:
        data = json.loads(response_text)
        if "reconstructed_markdown" in data:
            return data["reconstructed_markdown"], None
        else:
            return None, "No reconstructed_markdown key in response"
    except json.JSONDecodeError as e:
        return None, f"JSON decode error: {str(e)}"

def main():
    output_file = "/home/ramji/Videos/scap/college_scraper/serper_results.json"
    colleges_data = {}
    
    # Load existing data to merge
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                colleges_data = json.load(f)
            print(f"✓ Loaded {len(colleges_data)} existing colleges from JSON")
        except:
            print("⚠️  Could not load existing JSON, starting fresh.")
            
    total_start_time = time.time()

    
    all_tasks = []
    for college in COLLEGES:
        for query_type, query in QUERIES.items():
            cmd = build_curl_command(query, college)
            all_tasks.append({
                "college": college["name"],
                "query_type": query_type,
                "cmd": cmd
            })
    
    print(f"Running {len(all_tasks)} parallel curl requests...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for task in all_tasks:
            future = executor.submit(run_curl, task["cmd"])
            futures[future] = task
        
        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            college_name = task["college"]
            query_type = task["query_type"]
            
            try:
                stdout, elapsed = future.result()
                markdown, error = extract_reconstructed_markdown(stdout)
                
                if college_name not in colleges_data:
                    # Order the sections as requested: basic_info, programs, placements, fees, infrastructure
                    init_data = {
                        "basic_info": {},
                        "programs": {},
                        "placements": {},
                        "fees": {},
                        "infrastructure": {},
                        "_metadata": {"total_time": 0, "errors": {}}
                    }
                    colleges_data[college_name] = init_data
                
                structured_data = extract_structured_json(markdown) if markdown else {"error": error}
                current_college = colleges_data[college_name]
                
                if query_type == "details":
                    # Unpack combined details into their respective keys
                    for key in ["placements", "fees", "infrastructure"]:
                        if key in structured_data:
                            current_college[key] = structured_data[key]
                        else:
                            current_college[key] = {"error": "Missing in combined details"}
                else:
                    current_college[query_type] = structured_data
                
                meta = current_college["_metadata"]
                meta["total_time"] += elapsed
                if error:
                    meta["errors"][query_type] = error
                
                print(f"✓ {college_name} - {query_type}: {elapsed:.2f}s")
            except Exception as e:
                print(f"✗ {college_name} - {query_type}: Error - {str(e)}")
    
    total_end_time = time.time()
    total_time_taken_seconds = round(total_end_time - total_start_time, 2)
    
    output_file = "/home/ramji/Videos/scap/college_scraper/serper_results.json"
    with open(output_file, "w") as f:
        json.dump(colleges_data, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"Total time taken: {total_time_taken_seconds} seconds")
    print(f"Results saved to: {output_file}")
    
    for college, data in colleges_data.items():
        print(f"\n{college}: {data['_metadata']['total_time']:.2f}s")

if __name__ == "__main__":
    main()
