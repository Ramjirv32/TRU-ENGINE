import subprocess
import json
import time
import os
import re
import concurrent.futures

API_KEY = "33115710653096606c6bef7b3e4221d0509fa024d616153e064891a2bbe63b7e"

COLLEGES = [
    {"name": "Psg College of Technology", "country": "India", "location": "Coimbatore"},

]

QUERIES = {
    "basic_info": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified institutional data for the current academic year or the latest available year if the current is not published. Return only valid JSON with the exact fields: college_name, short_name, established, institution_type, country, location, website, about, summary, rankings (nirf_latest, nirf_previous, qs_world, national_rank, state_rank, guessed_data), student_statistics (total_enrollment, ug_students, pg_students, phd_students, annual_intake, male_percent, female_percent, total_ug_courses, total_pg_courses, total_phd_courses, guessed_data), faculty_staff (total_faculty, student_faculty_ratio, phd_faculty_percent, guessed_data), student_history (student_count_comparison_last_3_years with latest_year, previous_year, year_before_previous, international_students, guessed_data, categorywise_student_comparison_last_3_years: [{\"year\": \"latest_year\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}, {\"year\": \"previous_year\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}, {\"year\": \"year_before_previous\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}]), accreditations (body, grade, year), affiliations, recognition, campus_area, contact_info (phone, email, address), and sources_verified (array of URLs or document names). If a number is not known, use -1; if a string is not known, use N/A. Do not add any extra text, only JSON.",
    "programs": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide a COMPREHENSIVE list of ALL officially offered UG, PG, and PhD programs and departments as of the current academic year. Use only official college website, latest NIRF, AICTE, or UGC‑recognized sources. Do not invent any program. Return only valid JSON with keys: ug_programs (complete list of ALL undergraduate programs with specializations), pg_programs (complete list of ALL postgraduate programs with specializations), phd_programs (complete list of ALL doctoral programs with specializations), departments (complete list of ALL academic departments). If a level has no programs, use an empty array []. Include a \"sources_verified\" array with URLs or document names. IMPORTANT: List EVERY single program offered, including all branches, specializations, and interdisciplinary programs. Do not group or summarize programs - list each one individually.",
    "placements": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest verified placement data for the past three years if available. Use only official placement reports, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"latest_year\", \"sources\": [\"source URL or document name\"], \"placements\": {\"year\": \"latest_year\", \"highest_package\": real_number, \"average_package\": real_number, \"median_package\": real_number, \"package_currency\": \"LPA\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges, \"placement_rate_percent\": real_percent, \"total_students_placed\": integer, \"total_companies_visited\": integer, \"graduate_outcomes_note\": \"factual note\"}, \"placement_comparison_last_3_years\": [{\"year\":\"latest_year\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":\"previous_year\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":\"year_before_previous\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}], \"gender_based_placement_last_3_years\": [{\"year\":\"latest_year\", \"male_placed\": integer, \"female_placed\": integer, \"male_percent\": real_percent, \"female_percent\": real_percent}], \"sector_wise_placement_last_3_years\": [{\"year\":\"latest_year\", \"sector\": \"sector name\", \"companies\": [\"company names\"], \"percent\": real_percent}], \"top_recruiters\": [\"company names\"], \"placement_highlights\": \"2-3 sentence factual summary\"}. IMPORTANT: Always include currency_type field for all monetary values. If exact numbers are unavailable, use conservative estimates and set \"guessed_data\": true. Do not inflate numbers; for Indian Tier‑2 private engineering colleges, average package is usually 5–8 LPA. Do not return any extra text, only JSON.",
    "fees": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified fee structure for the current academic year. Use only official college website, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"latest_year\", \"sources\": [\"source URL or document name\"], \"fees\": {\"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"hostel_per_year\": real_number}, \"fees_by_year\": [{\"year\": \"latest_year\", \"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"hostel_per_year\": real_number}], \"fees_note\": \"2-3 sentence factual summary\", \"scholarships_detail\": [{\"name\": \"scholarship name\", \"amount\": real_number, \"currency_type\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges, \"eligibility\": \"eligibility criteria\", \"provider\": \"provider name\"}]}. IMPORTANT: Always include currency_type field for all monetary values. If exact numbers are unavailable, use conservative estimates and set \"guessed_data\": true. Do not inflate numbers. Do not return any extra text, only JSON.",
    "infrastructure": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified infrastructure details and available scholarships. Use only official college website, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"sources_verified\": [\"source URL or document name\"], \"infrastructure\": [{\"facility\": \"facility name\", \"details\": \"facility details\"}], \"hostel_details\": {\"available\": boolean, \"total_capacity\": integer, \"type\": \"hostel type\"}, \"library_details\": {\"total_books\": integer, \"journals\": integer, \"e_resources\": integer, \"area_sqft\": real_number}, \"transport_details\": {\"buses\": integer, \"routes\": integer}, \"scholarships\": [{\"name\": \"scholarship name\", \"amount\": real_number_or_NA, \"currency_type\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges, \"eligibility\": \"eligibility criteria\", \"provider\": \"provider name\", \"type\": \"merit/need/specific\", \"application_deadline\": \"date_or_NA\"}]}. IMPORTANT: Always include currency_type field for all monetary amounts. List ALL available scholarships including merit-based, need-based, government, private, and international student scholarships. Do not return any extra text, only JSON."
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
    
    # Create separate files for each college
    for college, data in colleges_data.items():
        # Sanitize college name for filename
        safe_college_name = re.sub(r'[^\w\s-]', '', college).strip().replace(' ', '_')
        output_file = f"/home/ramji/Videos/scap/college_scraper/{safe_college_name}.json"
        
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"\n{college}: {data['_metadata']['total_time']:.2f}s")
        print(f"Saved to: {output_file}")
    
    print(f"\n{'='*50}")
    print(f"Total time taken: {total_time_taken_seconds} seconds")
    print(f"Individual college files created successfully!")

if __name__ == "__main__":
    main()
