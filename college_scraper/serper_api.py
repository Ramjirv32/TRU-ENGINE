from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
import os
import subprocess
import time
import re
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import pymongo
from pymongo import MongoClient
import redis
from concurrent.futures import ThreadPoolExecutor
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import existing serper functionality
import sys
sys.path.append('/home/ramji/Videos/scap/college_scraper')
from serper import (
    COLLEGES, QUERIES, build_curl_command, run_curl, 
    extract_structured_json, extract_reconstructed_markdown,
    normalize_college
)
from json_formatter import normalize_college_data, JSONNormalizer
from groq_college_validator import validate_college_name

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_database()
    yield
    # Shutdown (if needed)
    pass

app = FastAPI(title="Serper College Scraper API", version="1.0.0", lifespan=lifespan)

# Configuration Variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8501"))
BACKEND_URL = os.getenv("BACKEND_URL", "https://api.cloudlab.works")  # Go backend URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://tru.cloudlab.works")  # Frontend URL

# Allowed origins for CORS (Security: Only these domains can access the API)
ALLOWED_ORIGINS = [
    # Production domains
    "https://ai.cloudlab.works",
    "https://tru.cloudlab.works",
    "https://api.cloudlab.works",
    # Local development
    "http://localhost:3000",
    "http://localhost:9000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:9000",
]

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Restrict to specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Custom middleware to log security events
@app.middleware("http")
async def log_security_events(request, call_next):
    origin = request.headers.get("origin", "Unknown")
    
    # Check if origin is allowed
    if origin != "Unknown" and origin not in ALLOWED_ORIGINS:
        print(f"⚠️  SECURITY: Rejected request from unauthorized origin: {origin} | Path: {request.url.path} | Method: {request.method}")
    
    response = await call_next(request)
    return response

# Database Connections
mongo_client = None
db = None
college_collection = None
redis_client = None

# Pydantic Models
class CollegeSearchRequest(BaseModel):
    college_name: str
    country: Optional[str] = None
    city: Optional[str] = None

class CollegeResponse(BaseModel):
    college_name: str
    country: str
    basic_info: Dict[str, Any]
    programs: Dict[str, Any]
    placements: Dict[str, Any]
    fees: Dict[str, Any]
    infrastructure: Dict[str, Any]
    _metadata: Dict[str, Any]

class CountryResponse(BaseModel):
    id: str
    name: str

class CollegeListItem(BaseModel):
    id: str
    name: str
    country: str
    data: Optional[List[Dict[str, Any]]] = None

# Database Initialization
def init_database():
    global mongo_client, db, college_collection, redis_client
    
    try:
        # MongoDB Connection
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client["erdth"]  # Same database as go-Engine
        college_collection = db["college_details"]  # Same collection as go-Engine
        print(f"✅ Connected to MongoDB - Database: erdth, Collection: college_details")
        
        # Redis Connection
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")

# Helper Functions
def transform_data_for_frontend(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform data for frontend - handles both camelCase (normalized) and snake_case (legacy)
    Always returns snake_case for frontend compatibility
    """
    transformed = {}
    
    # Helper to get value from either camelCase or snake_case key
    def get_value(obj, camel_key, snake_key, default=None):
        return obj.get(camel_key) or obj.get(snake_key, default)
    
    # Detect if data is in camelCase (normalized) or snake_case (legacy)
    is_normalized = "collegeName" in data or "basicInfo" in data
    
    # Get base info (handle both camelCase and snake_case)
    basic_source = get_value(data, "basicInfo", "basic_info", {})
    if not basic_source or len(basic_source) < 2:
        serper = get_value(data, "serperSections", "serper_sections", {})
        basic_source = get_value(serper, "basicInfo", "basic_info", serper)
    
    # Get programs (handle both formats)
    programs_source = get_value(data, "programs", "programs", {})
    if not programs_source or (not programs_source.get("ug_programs") and not programs_source.get("ugPrograms")):
        serper = get_value(data, "serperSections", "serper_sections", {})
        programs_source = get_value(serper, "programs", "programs", serper)
    
    # Get placements
    placements_source = get_value(data, "placements", "placements", {})
    if not placements_source:
        serper = get_value(data, "serperSections", "serper_sections", {})
        placements_source = get_value(serper, "placements", "placements", serper.get("placements_data", {}))
    
    # Get fees
    fees_source = get_value(data, "fees", "fees", {})
    if not fees_source:
        serper = get_value(data, "serperSections", "serper_sections", {})
        fees_source = get_value(serper, "fees", "fees", serper.get("fees_data", {}))
    
    # Get infrastructure
    infrastructure_source = get_value(data, "infrastructure", "infrastructure") or \
                           get_value(data, "serperSections", "serper_sections", {}).get("infrastructure_data", {})
    
    # Extract basic info (convert from camelCase if needed)
    college_name = get_value(basic_source, "collegeName", "college_name") or get_value(data, "collegeName", "college_name", "")
    
    transformed.update({
        "college_name": college_name,
        "short_name": get_value(basic_source, "shortName", "short_name", ""),
        "established": get_value(basic_source, "established", "established", ""),
        "institution_type": get_value(basic_source, "institutionType", "institution_type", ""),
        "country": get_value(basic_source, "country", "country") or get_value(data, "country", "country", ""),
        "location": get_value(basic_source, "location", "location") or get_value(data, "location", "location", ""),
        "website": get_value(basic_source, "website", "website", ""),
        "about": get_value(basic_source, "about", "about", ""),
        "summary": get_value(basic_source, "summary", "summary", ""),
        "rankings": get_value(basic_source, "rankings", "rankings", {}),
        "accreditations": get_value(basic_source, "accreditations", "accreditations", []),
        "recognition": get_value(basic_source, "recognition", "recognition", ""),
        "campus_area": get_value(basic_source, "campusArea", "campus_area", ""),
        "contact_info": get_value(basic_source, "contactInfo", "contact_info", {}),
    })
    
    # Student statistics (handle camelCase)
    student_stats = get_value(basic_source, "studentStatistics", "student_statistics", {})
    if student_stats:
        transformed["student_statistics_detail"] = {
            "total_enrollment": get_value(student_stats, "totalEnrollment", "total_enrollment", 0),
            "ug_students": get_value(student_stats, "ugStudents", "ug_students", 0),
            "pg_students": get_value(student_stats, "pgStudents", "pg_students", 0),
            "phd_students": get_value(student_stats, "phdStudents", "phd_students", 0),
            "male_percent": get_value(student_stats, "malePercent", "male_percent", 0),
            "female_percent": get_value(student_stats, "femalePercent", "female_percent", 0),
            "total_ug_courses": get_value(student_stats, "totalUgCourses", "total_ug_courses", 0),
            "total_pg_courses": get_value(student_stats, "totalPgCourses", "total_pg_courses", 0),
            "total_phd_courses": get_value(student_stats, "totalPhdCourses", "total_phd_courses", 0),
            "total_faculty_count": get_value(student_stats, "totalFacultyCount", "total_faculty_count", 0),
            "total_departments_count": get_value(student_stats, "totalDepartmentsCount", "total_departments_count", 0),
        }
        transformed["student_statistics"] = [
            {"category": "Total students", "value": transformed["student_statistics_detail"]["total_enrollment"]},
            {"category": "UG Students", "value": transformed["student_statistics_detail"]["ug_students"]},
            {"category": "PG Students", "value": transformed["student_statistics_detail"]["pg_students"]},
            {"category": "PhD Students", "value": transformed["student_statistics_detail"]["phd_students"]},
            {"category": "Male students", "value": transformed["student_statistics_detail"]["male_percent"]},
            {"category": "Female students", "value": transformed["student_statistics_detail"]["female_percent"]},
            {"category": "UG Courses", "value": transformed["student_statistics_detail"]["total_ug_courses"]},
            {"category": "PG Courses", "value": transformed["student_statistics_detail"]["total_pg_courses"]},
            {"category": "PhD Courses", "value": transformed["student_statistics_detail"]["total_phd_courses"]},
            {"category": "Total Faculty", "value": transformed["student_statistics_detail"]["total_faculty_count"]},
            {"category": "Departments", "value": transformed["student_statistics_detail"]["total_departments_count"]},
        ]
    
    # Faculty staff (handle camelCase)
    faculty = get_value(basic_source, "facultyStaff", "faculty_staff", {})
    if faculty:
        transformed["faculty_staff_detail"] = {
            "total_faculty": get_value(faculty, "totalFaculty", "total_faculty", 0),
            "phd_faculty_percent": get_value(faculty, "phdFacultyPercent", "phd_faculty_percent", 0),
        }
    
    # Programs (handle both formats)
    if programs_source:
        transformed["programs_data"] = {
            "ug_programs": get_value(programs_source, "ugPrograms", "ug_programs", []),
            "pg_programs": get_value(programs_source, "pgPrograms", "pg_programs", []),
            "phd_programs": get_value(programs_source, "phdPrograms", "phd_programs", []),
            "departments": get_value(programs_source, "departments", "departments", []),
        }
        transformed.update(transformed["programs_data"])
    
    # Departments fallback - check root level if not found in programs_data
    if not transformed.get("departments") or len(transformed.get("departments", [])) == 0:
        transformed["departments"] = get_value(data, "departments", "departments", [])
    
    # Placements (handle both formats)
    if placements_source:
        placements_obj = placements_source.get("placements", placements_source) if "placements" in placements_source else placements_source
        
        transformed["placements_data"] = {
            "placements": placements_obj,
            "placement_comparison_last_3_years": get_value(placements_source, "placementComparisonLast3Years", "placement_comparison_last_3_years", []),
            "gender_based_placement_last_3_years": get_value(placements_source, "genderBasedPlacementLast3Years", "gender_based_placement_last_3_years", []),
            "sector_wise_placement_last_3_years": get_value(placements_source, "sectorWisePlacementLast3Years", "sector_wise_placement_last_3_years", []),
            "top_recruiters": get_value(placements_source, "topRecruiters", "top_recruiters", []),
            "placement_highlights": get_value(placements_source, "placementHighlights", "placement_highlights", ""),
        }
        transformed.update({k: v for k, v in transformed["placements_data"].items() if k != "placements_data"})
    
    # Fees (handle both formats)
    if fees_source:
        fees_obj = fees_source.get("fees", fees_source) if "fees" in fees_source else fees_source
        
        transformed["fees_data"] = {
            "fees": fees_obj,
            "fees_by_year": get_value(fees_source, "feesByYear", "fees_by_year", []),
            "fees_note": get_value(fees_source, "feesNote", "fees_note", ""),
            "scholarships_detail": get_value(fees_source, "scholarshipDetails", "scholarships_detail", []),
        }
        transformed.update({k: v for k, v in transformed["fees_data"].items() if k != "fees_data"})
    
    # Infrastructure (handle both formats)
    if infrastructure_source and isinstance(infrastructure_source, dict):
        transformed["infrastructure_data"] = {
            "infrastructure": get_value(infrastructure_source, "infrastructure", "infrastructure", []),
            "hostel_details": get_value(infrastructure_source, "hostelDetails", "hostel_details", {}),
            "library_details": get_value(infrastructure_source, "libraryDetails", "library_details", {}),
            "transport_details": get_value(infrastructure_source, "transportDetails", "transport_details", {}),
            "scholarships": get_value(infrastructure_source, "scholarships", "scholarships", []),
        }
        transformed.update({k: v for k, v in transformed["infrastructure_data"].items() if k != "infrastructure_data"})
    
    return transformed


def convert_datetime_to_str(obj):
    """Recursively convert datetime objects to strings"""
    if isinstance(obj, datetime):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    else:
        return obj

def cache_college_data(college_name: str, data: Dict[str, Any]):
    """Cache college data in Redis"""
    if redis_client is not None:
        cache_key = f"college:{college_name.lower().replace(' ', '_')}"
        redis_client.setex(cache_key, 3600, json.dumps(data, default=str))  # Cache for 1 hour

def get_cached_college_data(college_name: str) -> Optional[Dict[str, Any]]:
    """Get cached college data from Redis"""
    if redis_client is not None:
        cache_key = f"college:{college_name.lower().replace(' ', '_')}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    return None

def save_college_to_mongodb(college_data: Dict[str, Any]):
    """Save college data to MongoDB with normalized JSON structure"""
    if college_collection is not None:
        try:
            # Normalize data to consistent structure (camelCase, ISO dates, predictable nesting)
            normalized_data = normalize_college_data(college_data)
            
            # Add timestamps with ISO format
            normalized_data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if "created_at" not in normalized_data or not normalized_data["created_at"]:
                normalized_data["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Set approval status if not present
            if "approval_status" not in normalized_data:
                normalized_data["approval_status"] = "pending"
            
            # Get college name from either camelCase or snake_case key
            college_name = normalized_data.get("collegeName") or normalized_data.get("college_name") or "Unknown"
            
            # Use upsert to either insert or update
            college_collection.replace_one(
                {"college_name": college_name},
                normalized_data,
                upsert=True
            )
            print(f"✅ Saved to MongoDB (normalized): {college_name}")
            
        except Exception as e:
            print(f"❌ Error saving to MongoDB: {e}")


def extract_college_list_from_db() -> List[CollegeListItem]:
    """Extract college list from MongoDB"""
    colleges = []
    if college_collection is not None:
        try:
            cursor = college_collection.find(
                {"college_name": {"$exists": True}, "approval_status": "approved"},
                {"college_name": 1, "country": 1, "student_statistics": 1}
            )
            for doc in cursor:
                colleges.append(CollegeListItem(
                    id=str(doc["_id"]),
                    name=doc["college_name"],
                    country=doc.get("country", "Unknown"),
                    data=doc.get("student_statistics", [])
                ))
        except Exception as e:
            print(f"❌ Error fetching college list: {e}")
    return colleges

def get_countries_list() -> List[CountryResponse]:
    """Get unique countries from college data"""
    countries = []
    if college_collection is not None:
        try:
            pipeline = [
                {"$match": {"country": {"$exists": True, "$ne": ""}}},
                {"$group": {"_id": "$country", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            cursor = college_collection.aggregate(pipeline)
            for i, doc in enumerate(cursor):
                countries.append(CountryResponse(
                    id=f"country_{i}",
                    name=doc["_id"]
                ))
        except Exception as e:
            print(f"❌ Error fetching countries: {e}")
    
    # Fallback to basic list if no data
    if not countries:
        countries = [
            CountryResponse(id="india", name="India"),
            CountryResponse(id="us", name="United States"),
            CountryResponse(id="uk", name="United Kingdom"),
        ]
    
    return countries

# API Routes
@app.get("/")
async def root():
    return {"message": "Serper College Scraper API", "version": "1.0.0", "port": 8500}

@app.get("/api/countries")
async def get_countries():
    """Get list of countries"""
    try:
        countries = get_countries_list()
        return countries
    except Exception as e:
        print(f"Error in countries endpoint: {e}")
        # Return fallback countries
        return [
            CountryResponse(id="india", name="India"),
            CountryResponse(id="us", name="United States"),
            CountryResponse(id="uk", name="United Kingdom"),
        ]

@app.get("/api/colleges-by-country")
async def get_colleges_by_country(country: str):
    """Get colleges by country"""
    try:
        if college_collection is None:
            # Return mock data for testing
            return [
                {"id": "1", "name": f"Mock University in {country}", "country": country},
                {"id": "2", "name": f"Test College in {country}", "country": country}
            ]
        
        colleges = []
        cursor = college_collection.find(
            {"country": country, "approval_status": "approved"},
            {"college_name": 1, "country": 1, "student_statistics": 1}
        )
        
        for doc in cursor:
            colleges.append({
                "id": str(doc["_id"]),
                "name": doc["college_name"],
                "country": doc.get("country", "Unknown"),
                "data": doc.get("student_statistics", [])
            })
        
        return colleges
        
    except Exception as e:
        print(f"Error in colleges-by-country endpoint: {e}")
        # Return fallback data
        return [
            {"id": "1", "name": f"Mock University in {country}", "country": country},
            {"id": "2", "name": f"Test College in {country}", "country": country}
        ]

@app.post("/api/college-statistics")
async def get_college_statistics(request: CollegeSearchRequest):
    """Get college statistics - this triggers scraping if needed"""
    return await process_college_statistics(request.college_name, request.country, request.city)

@app.get("/api/validate-college")
async def validate_college_endpoint(college_name: str, country: str = None, city: str = None):
    """Validate college name using Groq before scraping"""
    try:
        validated_college = validate_college_name(college_name, country or "", city or "")
        return {
            "success": True,
            "original_input": {
                "college_name": college_name,
                "country": country,
                "city": city
            },
            "validated_result": validated_college
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/college-statistics")
async def get_college_statistics_get(college_name: str, country: str = None, city: str = None):
    """Get college statistics via GET method - for frontend compatibility"""
    return await process_college_statistics(college_name, country, city)

async def process_college_statistics(college_name: str, country: str = None, city: str = None):
    """Process college statistics request - shared logic for GET and POST"""
    try:
        print(f"🔍 Validating college name: {college_name}")
        
        # Step 1: Validate college name with Groq
        validated_college = validate_college_name(college_name, country or "", city or "")
        
        if not validated_college.get("is_valid", False):
            raise HTTPException(status_code=400, detail=f"Invalid college name: {validated_college.get('error', 'Unknown error')}")
        
        validated_college_name = validated_college["name"]
        validated_country = validated_college["country"]
        validated_location = validated_college["location"]
        
        print(f"✅ College validated: {validated_college_name} ({validated_country}, {validated_location})")
        
        # Step 2: Check cache first using validated name
        cached_data = get_cached_college_data(validated_college_name)
        if cached_data:
            print(f"📋 Serving cached data for: {validated_college_name}")
            return cached_data
        
        # Step 3: Check MongoDB using validated name
        if college_collection is not None:
            existing = college_collection.find_one({"college_name": validated_college_name})
            if existing and existing.get("approval_status") == "approved":
                print(f"📋 Serving MongoDB data for: {validated_college_name}")
                # Convert ObjectId to string for JSON serialization
                existing["_id"] = str(existing["_id"])
                # Convert all datetime objects to strings recursively
                existing = convert_datetime_to_str(existing)
                
                # Ensure basic_info has the validated college information
                if "basic_info" in existing:
                    existing["basic_info"]["college_name"] = validated_college_name
                    existing["basic_info"]["country"] = validated_country
                    existing["basic_info"]["location"] = validated_location
                
                # Transform data structure to match frontend expectations
                transformed_data = transform_data_for_frontend(existing)
                cache_college_data(validated_college_name, transformed_data)
                return transformed_data
        
        # Step 4: If not found, trigger scraping with validated data
        print(f"🔍 Starting scraping for: {validated_college_name}")
        
        # Create a validated college entry for scraping
        temp_college = {
            "name": validated_college_name,
            "country": validated_country,
            "location": validated_location
        }
        
        # Run the scraper in a separate thread
        loop = asyncio.get_event_loop()
        
        def scrape_college():
            # Temporarily modify COLLEGES list
            original_colleges = COLLEGES.copy()
            COLLEGES.clear()
            COLLEGES.append(temp_college)
            
            try:
                # Import and run the main scraping logic
                from serper import main as scrape_main
                scrape_main()
                
                # Read the generated file
                safe_name = re.sub(r'[^\w\s-]', '', validated_college_name).strip().replace(' ', '_')
                file_path = f"/home/ramji/Videos/scap/college_scraper/{safe_name}_normalized.json"
                
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        scraped_data = json.load(f)
                    
                    print(f"📖 Scraped data loaded for: {validated_college_name}")
                    print(f"📊 Sections found in scraped data: {list(scraped_data.keys())}")
                    
                    # Prepare data for MongoDB - simple approach with raw serper sections
                    mongo_data = {
                        "college_name": validated_college_name,
                        "country": validated_country,
                        "location": validated_location,
                        "approval_status": "pending",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        # Store raw scraped data
                        "serper_sections": scraped_data
                    }
                    
                    # Save to MongoDB
                    save_college_to_mongodb(mongo_data)
                    print(f"💾 Saved college data to MongoDB")
                    
                    # Transform data for frontend before caching and returning
                    transformed_data = transform_data_for_frontend(mongo_data)
                    print(f"🔄 Transformed for frontend compatibility")
                    
                    # Cache the transformed data using validated name
                    cache_college_data(validated_college_name, transformed_data)
                    print(f"⚡ Cached data in Redis")
                    
                    return transformed_data
                    
            except Exception as e:
                print(f"❌ Scraping error: {e}")
                return {"error": str(e)}
            
            finally:
                # Restore original COLLEGES list
                COLLEGES.clear()
                COLLEGES.extend(original_colleges)
        
        # Run scraping asynchronously
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, scrape_college)
        
        if result and "error" not in result:
            return result
        else:
            raise HTTPException(status_code=404, detail="College not found or scraping failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/most-searched")
async def get_most_searched(limit: int = 6):
    """Get most searched colleges"""
    try:
        if college_collection is None:
            # Return mock data
            return [
                {"college_name": "MIT", "country": "United States"},
                {"college_name": "Stanford", "country": "United States"},
                {"college_name": "IIT Bombay", "country": "India"},
            ]
        
        colleges = []
        cursor = college_collection.find(
            {"approval_status": "approved"},
            {"college_name": 1, "country": 1}
        ).sort("updated_at", -1).limit(limit)
        
        for doc in cursor:
            colleges.append({
                "college_name": doc["college_name"],
                "country": doc.get("country", "Unknown")
            })
        
        return colleges
        
    except Exception as e:
        print(f"Error in most-searched endpoint: {e}")
        # Return fallback data
        return [
            {"college_name": "Anna University", "country": "India"},
            {"college_name": "MIT", "country": "United States"},
            {"college_name": "Stanford", "country": "United States"},
        ]

# WebSocket endpoints for real-time updates
@app.websocket("/ws/countries")
async def websocket_countries(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or handle country updates
            await manager.send_personal_message(f"Received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/colleges")
async def websocket_colleges(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Parse message to determine country
            try:
                message = json.loads(data)
                if message.get("type") == "subscribe_country":
                    country = message.get("country")
                    # Send college list for specific country
                    colleges = await get_colleges_by_country(country)
                    await manager.send_personal_message(
                        json.dumps({"type": "colleges_update", "colleges": colleges}),
                        websocket
                    )
            except json.JSONDecodeError:
                await manager.send_personal_message(f"Received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mongodb": "connected" if mongo_client is not None else "disconnected",
        "redis": "connected" if redis_client is not None else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    print(f"🚀 Starting Serper API Server on {API_HOST}:{API_PORT}...")
    uvicorn.run(app, host=API_HOST, port=API_PORT)
