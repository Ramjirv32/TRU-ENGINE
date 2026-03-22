from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import json
import time
import os
import sys
import concurrent.futures
import redis

app = Flask(__name__)
CORS(app)

# Redis connection
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
    redis_available = True
except:
    redis_available = False
    print("Redis not available, using file storage fallback")

# Import serper functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from serper import API_KEY, COLLEGES, QUERIES, build_curl_command, run_curl, extract_structured_json, extract_reconstructed_markdown

def fetch_from_redis(college_name, country):
    try:
        key = f"{college_name.lower().replace(' ', '_')}_{country.lower()}"
        data = r.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"Redis fetch error: {e}")
        return None

def store_in_redis(college_name, country, data):
    try:
        key = f"{college_name.lower().replace(' ', '_')}_{country.lower()}"
        r.set(key, json.dumps(data))
        print(f"✓ Stored in Redis: {key}")
        return True
    except Exception as e:
        print(f"✗ Redis error: {e}")
        return False

@app.route('/')
def index():
    return jsonify({
        "message": "College Scraper API Server",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/colleges": "List all available colleges",
            "GET /api/college/<name>": "Get specific college data",
            "POST /api/scrape": "Scrape fresh data for a college"
        }
    })

def get_available_colleges():
    """Read available colleges from results file"""
    try:
        results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "serper_results.json")
        with open(results_path, "r") as f:
            data = json.load(f)
            return list(data.keys())
    except Exception as e:
        print(f"Error reading colleges: {e}")
        return []

@app.route('/api/colleges')
def list_colleges():
    """List all available colleges"""
    colleges = get_available_colleges()
    return jsonify({
        "colleges": colleges,
        "total": len(colleges)
    })

@app.route('/api/college/<college_name>', methods=['GET'])
@app.route('/api/college', methods=['POST'])
def get_college_data(college_name=None):
    """Get college data from Redis cache or scrape fresh"""
    query_type = None
    
    if request.method == 'POST':
        try:
            req_data = request.get_json()
            college_name = req_data.get('college_name')
            query_type = req_data.get('type')
        except:
            return jsonify({"error": "Invalid JSON"}), 400
            
    if not college_name:
        return jsonify({"error": "college_name required"}), 400

    # Try to find college in COLLEGES list
    college_info = next((c for c in COLLEGES if c["name"].lower() == college_name.lower()), None)
    
    # If not in our list, create a generic entry
    if not college_info:
        college_info = {"name": college_name, "country": "Global", "location": "Unknown"}
    
    # Try to get from Redis first
    cached_data = fetch_from_redis(college_info["name"], college_info["country"])
    
    if cached_data:
        # If a specific type was requested and we have it, returned just that (wrapped for frontend merge)
        # However, frontend expects the whole object to be merged, so we return what we have
        if query_type and query_type in cached_data:
            return jsonify({query_type: cached_data[query_type]})
        return jsonify(cached_data)
    
    # If not in cache, scrape
    try:
        print(f"🔄 Fetching fresh data for {college_info['name']}")
        results = scrape_college_data(college_info)
        
        if results and college_info["name"] in results["colleges"]:
            college_data = results["colleges"][college_info["name"]]
            # Store in Redis
            if redis_available:
                store_in_redis(college_info["name"], college_info["country"], college_data)
            
            if query_type and query_type in college_data:
                return jsonify({query_type: college_data[query_type]})
            return jsonify(college_data)
        else:
            return jsonify({"error": "Failed to scrape college data"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape_college():
    """Scrape fresh data for a specific college"""
    data = request.get_json()
    college_name = data.get('college_name')
    
    if not college_name:
        return jsonify({"error": "college_name required"}), 400
    
    college_info = next((c for c in COLLEGES if c["name"].lower() == college_name.lower()), None)
    if not college_info:
        return jsonify({"error": "College not found"}), 404
    
    try:
        results = scrape_college_data(college_info)
        
        if results and college_info["name"] in results["colleges"]:
            college_data = results["colleges"][college_info["name"]]
            
            # Store in Redis
            if redis_available:
                store_in_redis(college_info["name"], college_info["country"], college_data)
            
            return jsonify({
                "college": college_info,
                "data": college_data,
                "source": "fresh_scrape",
                "scrape_time": results.get("total_time_taken_seconds", 0)
            })
        else:
            return jsonify({"error": "Failed to scrape college data"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

def scrape_college_data(college):
    """Scrape data for a single college"""
    results = {
        "total_start_time": time.time(),
        "colleges": {}
    }
    
    all_tasks = []
    
    # Check if data exists in Redis first
    cached_data = fetch_from_redis(college["name"], college["country"])
    if cached_data:
        print(f"✓ Using cached data for {college['name']}")
        results["colleges"][college["name"]] = cached_data
        return results
    
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
                college_name = task["college"]
                country = task["country"]
                query_type = task["query_type"]
                
                try:
                    stdout, elapsed = future.result()
                    markdown, error = extract_reconstructed_markdown(stdout)
                    
                    if college_name not in results["colleges"]:
                        results["colleges"][college_name] = {
                            "basic_info": {},
                            "programs": {},
                            "placements": {},
                            "fees": {},
                            "infrastructure": {},
                            "_metadata": {"total_time": 0, "errors": {}}
                        }
                    
                    structured_data = extract_structured_json(markdown) if markdown else {"error": error}
                    current_college = results["colleges"][college_name]
                    
                    if query_type == "details":
                        # Unpack combined details into their respective keys
                        for key in ["placements", "fees", "infrastructure"]:
                            if key in structured_data:
                                current_college[key] = structured_data[key]
                            else:
                                current_college[key] = {"error": "Missing in combined details"}
                    else:
                        current_college[query_type] = structured_data
                    
                    current_college["_metadata"]["total_time"] += elapsed
                    if error:
                        current_college["_metadata"]["errors"][query_type] = error
                    
                    print(f"✓ {college_name} - {query_type}: {elapsed:.2f}s")
                except Exception as e:
                    print(f"✗ {college_name} - {query_type}: Error - {str(e)}")
    
    results["total_end_time"] = time.time()
    results["total_time_taken_seconds"] = round(results["total_end_time"] - results["total_start_time"], 2)
    
    # Store fresh data in Redis
    if redis_available:
        for college_name, college_data in results["colleges"].items():
            college_info = next((c for c in COLLEGES if c["name"] == college_name), None)
            if college_info:
                store_in_redis(college_name, college_info["country"], college_data)
    
    return results

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "redis_available": redis_available,
        "timestamp": time.time()
    })

if __name__ == '__main__':
    print("Starting College Scraper API Server...")
    print("Server will be available at: http://localhost:5000")
    print("API endpoints:")
    print("  GET /api/colleges - List all colleges")
    print("  GET /api/college/<name> - Get specific college data")
    print("  POST /api/scrape - Scrape fresh data")
    print("  GET /api/health - Health check")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
