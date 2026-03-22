import subprocess
import json
import time
import os
import re
import concurrent.futures
import redis
import pymongo
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_KEY = "c138d04299d00500bdf9168ba3a04143fadcae1fab8437f2c4bb9b5437dc24d8"

COLLEGES = [
    {"name": "Udayana University", "country": "Indonesia", "location": "Bali"},
]

QUERIES = {
    "basic_info": "For college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide latest verified institutional data for current academic year and comparisons for the past three years. Return only valid JSON with exact fields: college_name, country, location, short_name, established, institution_type, website, about, summary, rankings (nirf_rank, qs_world, national_rank, state_rank, guessed_data), student_statistics (total_enrollment, ug_students, pg_students, phd_students, annual_intake, male_percent, female_percent, total_ug_courses, total_pg_courses, total_phd_courses, guessed_data), faculty_staff (total_faculty, student_faculty_ratio, phd_faculty_percent, guessed_data), student_history (student_count_comparison_last_3_years, international_students, guessed_data), accreditations (MUST be a list of objects with fields: body, grade, year), affiliations, recognition, campus_area, contact_info (phone, email, address), and sources_verified (array of URLs or document names). IMPORTANT: For student_history, provide data for the current year and the two preceding years. If a number is not known, use -1; if a string is not known, use N/A. Do not add any extra text, only JSON.",
    "programs": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), list every officially offered UG, PG, and PhD program and department as of the current academic session. Use only official college website, NIRF, AICTE, or UGC‑recognized sources. Do not invent any program. Return only valid JSON with keys: ug_programs (list of strings), pg_programs (list of strings), phd_programs (list of strings), departments (list of strings). If a level has no programs, use an empty array []. Include a \"sources_verified\" array with URLs or document names.",
    "placements": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest verified placement data for the most recent available batch and comparison for the past three years (current and two prior years). Return only valid JSON. IMPORTANT: Salary packages MUST be in the units specified by 'package_currency' (e.g., if currency is LPA, return 22.5 for 22.5 Lakhs, NOT 2250000). Fields: {\"guessed_data\": false, \"data_year\": \"current\", \"sources\": [\"URL\"], \"placements\": {\"year\": \"current\", \"highest_package\": number_in_lpa, \"average_package\": number_in_lpa, \"median_package\": number_in_lpa, \"package_currency\": \"LPA\", \"placement_rate_percent\": number, \"total_students_placed\": integer, \"total_companies_visited\": integer, \"graduate_outcomes_note\": \"note\"}, \"placement_comparison_last_3_years\": [{\"year\":\"current\", \"average_package\": number_in_lpa, \"employment_rate_percent\": number, \"package_currency\": \"LPA\"}, {\"year\":\"prior year 1\", \"average_package\": number_in_lpa, \"employment_rate_percent\": number, \"package_currency\": string}, {\"year\":\"prior year 2\", \"average_package\": number_in_lpa, \"employment_rate_percent\": number, \"package_currency\": string}], \"top_recruiters\": [\"names\"], \"placement_highlights\": \"summary\"}. Use conservative estimates if needed and set guessed_data: true.",
    "fees": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest official fee structure for the current academic session and the two preceding sessions. Use only official college website, AICTE mandatory disclosure, NIRF, or UGC‑recognized portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"current\", \"sources\": [\"official fee PDF URL or document name\"], \"fees\": {\"UG\": {\"per_year\": real_number_or_NA, \"total_course\": real_number_or_NA, \"currency\": \"INR\" for India, \"USD\" for US, \"GBP\" for UK}, \"PG\": {\"per_year\": real_number_or_NA, \"total_course\": real_number_or_NA, \"currency\": string}, \"hostel_per_year\": real_number_or_NA}}, \"fees_by_year\": [{\"year\": \"current\", \"program_type\": \"UG\", \"per_year_local\": real_number_or_NA, \"total_course_local\": real_number_or_NA, \"hostel_per_year_local\": real_number_or_NA, \"currency\": string}, {\"year\": \"prior year 1\", \"program_type\": \"UG\", \"per_year_local\": real_number_or_NA, \"total_course_local\": real_number_or_NA, \"hostel_per_year_local\": real_number_or_NA, \"currency\": string}, {\"year\": \"prior year 2\", \"program_type\": \"UG\", \"per_year_local\": real_number_or_NA, \"total_course_local\": real_number_or_NA, \"hostel_per_year_local\": real_number_or_NA, \"currency\": string}], \"fees_note\": \"short description\", \"scholarships_detail\": [{\"name\": \"scholarship name\", \"amount\": real_number_or_NA, \"eligibility\": \"criteria\", \"provider\": \"who\"}]}. IMPORTANT: Prepare fees_by_year for the current year and the two prior years. If exact fee is not published, provide a realistic estimate and set \"guessed_data\": true. Do not use 0 for amounts; use N/A instead. Do not add any extra text, only JSON.",
    "infrastructure": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), describe the existing campus infrastructure for the current academic session. Only list facilities that actually exist. Return only valid JSON with: {\"guessed_data\": false, \"sources_verified\": [\"official URL or document\"], \"infrastructure\": [{\"facility\": \"facility name\", \"details\": \"description\"}], \"hostel_details\": {\"available\": true_or_false, \"boys_capacity\": integer_or_NA, \"girls_capacity\": integer_or_NA, \"total_capacity\": integer_or_NA, \"type\": \"description\"}, \"library_details\": {\"total_books\": integer_or_NA, \"journals\": \"description\", \"e_resources\": [\"e‑resource names\"], \"area_sqft\": integer_or_Not Available, \"total_capacity\": integer_or_NA, \"type\": \"description\"}, \"library_details\": {\"total_books\": integer_or_NA, \"journals\": \"description\", \"e_resources\": [\"e‑resource names\"], \"area_sqft\": integer_or_NA}, \"transport_details\": {\"buses\": integer_or_NA, \"routes\": \"description\"}}. If capacities are unknown but can be reasonably estimated, use estimates and set \"guessed_data\": true. Do not invent facilities. Do not add any extra text, only JSON.",
}

def build_curl_command(query, college):
    q = query.replace("%COLLEGE_NAME%", college["name"]).replace("%COUNTRY%", college["country"]).replace("%LOCATION%", college["location"])
    cmd = [
        "curl", "--get", "https://serpapi.com/search",
        "--max-time", "30",
        "--connect-timeout", "10",
        "--data-urlencode", "engine=google_ai_mode",
        "--data-urlencode", f"q={q}",
        "--data-urlencode", f"api_key={API_KEY}"
    ]
    return cmd

def run_curl(cmd, query_type="unknown"):
    start = time.time()
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=35
        )
        elapsed = time.time() - start
        if result.returncode != 0:
            print(f"⚠️  Error in {query_type}")
            return "", elapsed
        return result.stdout, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"⏱️  Timeout {query_type}:{elapsed:.1f}s")
        return "", elapsed
    except Exception as e:
        elapsed = time.time() - start
        return "", elapsed

def extract_structured_json(md_text):
    if not md_text:
        return {}
    
    # 1. Strip all code block markers
    text = re.sub(r'```(?:json)?', '', md_text).strip()
    
    # 2. Find first '{' and last '}' to isolate JSON object
    start = text.find('{')
    end = text.rfind('}')
    
    if start == -1 or end == -1:
        # No braces found, might be raw or invalid
        try:
            return json.loads(text)
        except:
            return {"raw_output": md_text, "error": "No JSON braces found"}
            
    json_str = text[start:end+1]
    
    # 3. Sanitize common AI markdown escaping issues
    # AI models sometimes escape underscores \_ which is invalid in standard JSON
    json_str = json_str.replace(r'\_', '_')
    json_str = json_str.replace(r'\[', '[').replace(r'\]', ']')
    json_str = json_str.replace(r'\{', '{').replace(r'\}', '}')
    json_str = json_str.replace(r'\n', '\n') # handle escaped newlines
    
    # 4. Try parsing
    try:
        # Try strict first
        return json.loads(json_str)
    except:
        try:
            # Try non-strict to allow literal newlines/control chars
            return json.loads(json_str, strict=False)
        except Exception as e:
            # Final attempt: try to fix common trailing commas or other minor issues
            try:
                # Basic fix for trailing commas in arrays/objects
                fixed_str = re.sub(r',\s*([\]}])', r'\1', json_str)
                # Fix unescaped quotes within strings (very aggressive, use with caution)
                # fixed_str = re.sub(r'(?<!\\)"', r'\"', fixed_str) 
                return json.loads(fixed_str, strict=False)
            except:
                return {
                    "raw_output": md_text, 
                    "error": f"JSON parse error: {str(e)}",
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

def store_in_redis(college_name, country, data):
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        college_slug = college_name.lower().strip().replace(' ', '_')
        country_slug = country.lower().strip()
        key = f"{college_slug}_{country_slug}".rstrip('_')
        r.set(key, json.dumps(data))
        print(f"✓ Stored in Redis: {key}")
        return True
    except Exception as e:
        print(f"✗ Redis error: {e}")
        return False

def fetch_from_redis(college_name, country):
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        college_slug = college_name.lower().strip().replace(' ', '_')
        country_slug = country.lower().strip()
        key = f"{college_slug}_{country_slug}".rstrip('_')
        data = r.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"✗ Redis fetch error: {e}")
        return None
def store_in_mongodb(college_name, data):
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["mar22"]
        collection = db["colleges"]
        
        # Use simple filter based on college_name to update or insert
        # We also might want to store a slug or canonical name eventually
        query = {"college_name_search": college_name.lower().strip()}
        update_data = {
            "$set": {
                "college_name_search": college_name.lower().strip(),
                "data": data,
                "updated_at": time.time()
            }
        }
        collection.update_one(query, update_data, upsert=True)
        print(f"✓ Stored in MongoDB: {college_name}")
        return True
    except Exception as e:
        print(f"✗ MongoDB error: {e}")
        return False

def fetch_from_mongodb(college_name):
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["mar22"]
        collection = db["colleges"]
        
        result = collection.find_one({"college_name_search": college_name.lower().strip()})
        if result:
            return result.get("data")
        return None
    except Exception as e:
        print(f"✗ MongoDB fetch error: {e}")
        return None
def main():
    json_path = "/home/ramji/Videos/scap/college_scraper/serper_results.json"
    results = {
        "total_start_time": time.time(),
        "colleges": {}
    }
    
    # Load existing data to merge, not overwrite everything
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                results = json.load(f)
                results["total_start_time"] = time.time()
        except:
            print("⚠️  Could not load existing JSON, starting fresh.")
    
    if "colleges" not in results:
        results["colleges"] = {}
    
    all_tasks = []
    for college in COLLEGES:
        # Check if data exists in Redis first
        cached_data = fetch_from_redis(college["name"], college["country"])
        if cached_data:
            print(f"✓ Using cached data for {college['name']}")
            results["colleges"][college["name"]] = cached_data
            continue
            
        print(f"🔄 Fetching fresh data for {college['name']}")
        
        for query_type, query in QUERIES.items():
            cmd = build_curl_command(query, college)
            all_tasks.append({
                "college": college["name"],
                "country": college["country"],
                "query_type": query_type,
                "cmd": cmd
            })
    
    if all_tasks:
        print(f"Running {len(all_tasks)} parallel curl requests...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            for task in all_tasks:
                future = executor.submit(run_curl, task["cmd"])
                futures[future] = task
            
            for future in concurrent.futures.as_completed(futures):
                task = futures[future]
                college_search_name = task["college"]
                country = task["country"]
                query_type = task["query_type"]
                
                try:
                    stdout, elapsed = future.result()
                    markdown, error = extract_reconstructed_markdown(stdout)
                    
                    if college_search_name not in results["colleges"]:
                        results["colleges"][college_search_name] = {
                            "basic_info": {},
                            "programs": {},
                            "placements": {},
                            "fees": {},
                            "infrastructure": {},
                            "_metadata": {"total_time": 0, "errors": {}}
                        }
                    
                    structured_data = extract_structured_json(markdown) if markdown else {"error": error}
                    results["colleges"][college_search_name][query_type] = structured_data
                    
                    results["colleges"][college_search_name]["_metadata"]["total_time"] += elapsed
                    if error:
                        results["colleges"][college_search_name]["_metadata"]["errors"][query_type] = error
                    
                    print(f"✓ {college_search_name} - {query_type}: {elapsed:.2f}s")
                except Exception as e:
                    print(f"✗ {college_search_name} - {query_type}: Error - {str(e)}")
       
        for college_search_name, college_data in results["colleges"].items():
            # Extract official name
            official_name = college_search_name
            if "basic_info" in college_data and isinstance(college_data["basic_info"], dict):
                official_name = college_data["basic_info"].get("college_name", college_search_name)
            
            # Store in Redis
            store_in_redis(official_name, "", college_data)
            if official_name != college_search_name:
                store_in_redis(college_search_name, "", college_data)
                # Map in master results too
                results["colleges"][official_name] = college_data
    
    results["total_end_time"] = time.time()
    results["total_time_taken_seconds"] = round(results["total_end_time"] - results["total_start_time"], 2)
    
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"Total time taken: {results['total_time_taken_seconds']} seconds")
    print(f"Results saved to: {json_path}")
    
    for college, data in results["colleges"].items():
        if "_metadata" in data and "total_time" in data["_metadata"]:
            print(f"\n{college}: {data['_metadata']['total_time']:.2f}s")

# Flask API Endpoints
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "College Intelligence API is running"}), 200

@app.route('/api/college', methods=['POST'])
def get_college_data():
    """Fetch or retrieve college data by name"""
    try:
        data = request.get_json()
        college_name = data.get('college_name', '').strip()
        query_type_requested = data.get('type', None)  # new: support individual queries
        
        if not college_name:
            return jsonify({"error": "College name is required"}), 400
        
        # Redis Cache Key
        redis_key = f"{college_name.lower().replace(' ', '_')}"
        
        # Check MongoDB if Redis fails
        if not cached_data:
            cached_data = fetch_from_mongodb(college_name)
            if cached_data:
                print(f"✓ Using MongoDB cached data for {college_name}")
                # Backfill redis if found in mongo
                store_in_redis(college_name, "", cached_data)

        if cached_data:
            if query_type_requested and query_type_requested in cached_data:
                # If specific type requested but we have all, return that
                return jsonify({query_type_requested: cached_data[query_type_requested], "_metadata": {"source": "cache"}}), 200
            elif not query_type_requested:
                cached_data["_metadata"] = cached_data.get("_metadata", {})
                cached_data["_metadata"]["source"] = "cache"
                return jsonify(cached_data), 200
        
        # Fetch fresh data
        print(f"🔄 Fetching fresh data for {college_name} - requested type: {query_type_requested or 'ALL'}")
        
        college = {"name": college_name, "country": "Global", "location": ""}
        
        # Build tasks list
        tasks_to_run = []
        if query_type_requested and query_type_requested in QUERIES:
            tasks_to_run.append({"type": query_type_requested, "query": QUERIES[query_type_requested]})
        else:
            for q_type, q_val in QUERIES.items():
                tasks_to_run.append({"type": q_type, "query": q_val})

        results = {
            "_metadata": {"total_time": 0, "errors": {}, "source": "fresh"}
        }
        for t in tasks_to_run: results[t["type"]] = {}

        if tasks_to_run:
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for task in tasks_to_run:
                    cmd = build_curl_command(task["query"], college)
                    future = executor.submit(run_curl, cmd)
                    futures[future] = task
                
                for future in concurrent.futures.as_completed(futures):
                    task = futures[future]
                    q_type = task["type"]
                    try:
                        stdout, elapsed = future.result()
                        markdown, error = extract_reconstructed_markdown(stdout)
                        structured_data = extract_structured_json(markdown) if markdown else {"error": error}
                        results[q_type] = structured_data
                    except Exception as e:
                        results["_metadata"]["errors"][q_type] = str(e)
            
            # Use official name from basic_info if available
            official_name = college_name
            if "basic_info" in results and isinstance(results["basic_info"], dict):
                official_name = results["basic_info"].get("college_name", college_name)
            
            # Fetch existing data for the official name to merge
            full_college_data = fetch_from_redis(official_name, "") or {"_metadata": {"errors": {}}}
            
            # Merge results into full_college_data
            for k, v in results.items():
                if k != "_metadata":
                    full_college_data[k] = v
            
            # Merge errors
            if "errors" in results["_metadata"]:
                full_college_data["_metadata"].setdefault("errors", {}).update(results["_metadata"]["errors"])
            
            full_college_data["_metadata"]["total_time"] = round(time.time() - start_time, 2)
            full_college_data["_metadata"]["source"] = "fresh"
            
            # Store under official name
            store_in_redis(official_name, "", full_college_data)
            store_in_mongodb(official_name, full_college_data)
            
            # Also store under search name if different to act as an alias/cache
            if official_name.lower().strip() != college_name.lower().strip():
                print(f"🔗 Creating alias: {college_name} -> {official_name}")
                store_in_redis(college_name, "", full_college_data)
                store_in_mongodb(college_name, full_college_data)
            
            # Update master JSON file
            try:
                json_path = "/home/ramji/Videos/scap/college_scraper/serper_results.json"
                master_data = {"colleges": {}}
                if os.path.exists(json_path):
                    try:
                        with open(json_path, 'r') as f:
                            master_data = json.load(f)
                    except:
                        pass
                
                if "colleges" not in master_data:
                    master_data["colleges"] = {}
                
                master_data["colleges"][official_name] = full_college_data
                with open(json_path, 'w') as f:
                    json.dump(master_data, f, indent=2)
                print(f"✓ Updated master JSON: {official_name}")
            except Exception as e:
                print(f"✗ Error updating JSON: {e}")
            
            # Update results for immediate return
            results = full_college_data
        
        return jsonify(results), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/colleges-list', methods=['GET'])
def get_colleges_list():
    """Get list of available colleges"""
    return jsonify({"colleges": COLLEGES}), 200

@app.route('/', methods=['GET'])
def serve_frontend():
    """Serve the main HTML page"""
    return open('/home/ramji/Videos/scap/index.html', 'r').read(), 200, {'Content-Type': 'text/html'}

if __name__ == "__main__":
    import sys
    
    # Check if running as API server
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        print("🚀 Starting College Intelligence API Server...")
        print("📍 Server running at http://localhost:5000")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        # Run as CLI
        main()
