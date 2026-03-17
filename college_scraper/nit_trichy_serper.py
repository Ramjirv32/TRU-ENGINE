import subprocess
import json
import time
import re

API_KEY = "c138d04299d00500bdf9168ba3a04143fadcae1fab8437f2c4bb9b5437dc24d8"

COLLEGE = {"name": "National Institute of Technology Tiruchirappalli", "country": "India", "location": "Tiruchirappalli, Tamil Nadu"}

QUERY = "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified institutional data for the 2024-2025 academic year or 2023-24 if 2024-25 is not published. Return only valid JSON with the exact fields: college_name, short_name, established, institution_type, country, location, website, about, summary, rankings (nirf_2025, nirf_2024, qs_world, national_rank, state_rank, guessed_data), student_statistics (total_enrollment, ug_students, pg_students, phd_students, annual_intake, male_percent, female_percent, total_ug_courses, total_pg_courses, total_phd_courses, guessed_data), faculty_staff (total_faculty, student_faculty_ratio, phd_faculty_percent, guessed_data), student_history (student_count_comparison_last_3_years with 2024, 2023, 2022, international_students, guessed_data), accreditations (body, grade, year), affiliations, recognition, campus_area, contact_info (phone, email, address), and sources_verified (array of URLs or document names). If a number is not known, use N/A; if a string is not known, use N/A. Do not add any extra text, only JSON."

q = QUERY.replace("%COLLEGE_NAME%", COLLEGE["name"]).replace("%COUNTRY%", COLLEGE["country"]).replace("%LOCATION%", COLLEGE["location"])
cmd = ["curl", "--get", "https://serpapi.com/search", "--data-urlencode", "engine=google_ai_mode", "--data-urlencode", f"q={q}", "--data-urlencode", f"api_key={API_KEY}"]

start = time.time()
result = subprocess.run(cmd, capture_output=True, text=True)
elapsed = time.time() - start

data = json.loads(result.stdout)
markdown = data.get("reconstructed_markdown", "")
match = re.search(r"```json\s*(.*?)\s*```", markdown, re.DOTALL)
parsed = json.loads(match.group(1)) if match else None

output = {"reconstructed_markdown": markdown, "parsed_json": parsed, "time_taken_seconds": round(elapsed, 2)}
with open("/home/ramji/Videos/scap/college_scraper/nit_trichy_serper.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"Done: {elapsed:.2f}s")
print(json.dumps(parsed, indent=2)[:1500])
