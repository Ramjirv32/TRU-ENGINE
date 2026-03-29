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

# Import existing serper functionality
import sys
sys.path.append('/home/ramji/Videos/scap/college_scraper')
from serper import (
    COLLEGES, QUERIES, build_curl_command, run_curl, 
    extract_structured_json, extract_reconstructed_markdown,
    normalize_college
)

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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

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
    """Transform the normalized data structure to match frontend expectations"""
    transformed = {}
    
    # Basic info
    if "basic_info" in data:
        basic = data["basic_info"]
        transformed.update({
            "college_name": basic.get("college_name", ""),
            "short_name": basic.get("short_name", ""),
            "established": basic.get("established", ""),
            "institution_type": basic.get("institution_type", ""),
            "country": basic.get("country", ""),
            "location": basic.get("location", ""),
            "website": basic.get("website", ""),
            "about": basic.get("about", ""),
            "summary": basic.get("summary", ""),
            "rankings": basic.get("rankings", {}),
            "accreditations": basic.get("accreditations", []),
            "affiliations": basic.get("affiliations", "").split(", ") if basic.get("affiliations") else [],
            "recognition": basic.get("recognition", ""),
            "campus_area": basic.get("campus_area", ""),
            "contact_info": basic.get("contact_info", {}),
        })
        
        # Student statistics detail
        if "student_statistics" in basic:
            student_stats = basic["student_statistics"]
            transformed["student_statistics_detail"] = student_stats
            transformed["student_statistics"] = [{
                "category": "Total students",
                "value": student_stats.get("total_enrollment", 0)
            }, {
                "category": "UG Students",
                "value": student_stats.get("ug_students", 0)
            }, {
                "category": "PG Students", 
                "value": student_stats.get("pg_students", 0)
            }, {
                "category": "PhD Students",
                "value": student_stats.get("phd_students", 0)
            }, {
                "category": "Annual Intake",
                "value": student_stats.get("annual_intake", 0)
            }, {
                "category": "Male students",
                "value": student_stats.get("male_percent", 0)
            }, {
                "category": "Female students",
                "value": student_stats.get("female_percent", 0)
            }, {
                "category": "Total UG Courses",
                "value": student_stats.get("total_ug_courses", 0)
            }, {
                "category": "Total PG Courses",
                "value": student_stats.get("total_pg_courses", 0)
            }, {
                "category": "Total PhD Courses",
                "value": student_stats.get("total_phd_courses", 0)
            }]
            
            # Add faculty staff for pie chart
            if "faculty_staff" in basic:
                faculty = basic["faculty_staff"]
                transformed["student_statistics"].extend([
                    {
                        "category": "Faculty",
                        "value": faculty.get("total_faculty", 0)
                    },
                    {
                        "category": "Staff",
                        "value": faculty.get("total_faculty", 0)
                    }
                ])
            
            # Add international students if available
            if "student_history" in basic and "international_students" in basic["student_history"]:
                transformed["student_statistics"].append({
                    "category": "International students",
                    "value": basic["student_history"]["international_students"]
                })
                
            # Add placement data if available
            if "placements" in data:
                placements = data["placements"]
                if "placements" in placements:
                    placement_data = placements["placements"]
                    transformed["student_statistics"].extend([
                        {
                            "category": "Total students placed",
                            "value": placement_data.get("total_students_placed", 0)
                        },
                        {
                            "category": "Placement rate",
                            "value": placement_data.get("placement_rate_percent", 0)
                        }
                    ])
        
        # Faculty staff detail
        if "faculty_staff" in basic:
            faculty = basic["faculty_staff"]
            transformed["faculty_staff_detail"] = faculty
        
        # Student history
        if "student_history" in basic:
            transformed["student_history"] = basic["student_history"]
    
    # Programs data
    if "programs" in data:
        programs = data["programs"]
        transformed["programs_data"] = {
            "ug_programs": programs.get("ug_programs", []),
            "pg_programs": programs.get("pg_programs", []),
            "phd_programs": programs.get("phd_programs", []),
            "departments": programs.get("departments", []),
        }
        # Also flatten to top level for frontend compatibility
        transformed.update({
            "ug_programs": programs.get("ug_programs", []),
            "pg_programs": programs.get("pg_programs", []),
            "phd_programs": programs.get("phd_programs", []),
            "departments": programs.get("departments", []),
        })
    
    # Placements data
    if "placements" in data:
        placements = data["placements"]
        transformed["placements_data"] = {
            "placements": placements.get("placements", {}),
            "placement_comparison_last_3_years": placements.get("placement_comparison_last_3_years", []),
            "gender_based_placement_last_3_years": placements.get("gender_based_placement_last_3_years", []),
            "sector_wise_placement_last_3_years": placements.get("sector_wise_placement_last_3_years", []),
            "top_recruiters": placements.get("top_recruiters", []),
            "placement_highlights": placements.get("placement_highlights", ""),
        }
        # Also flatten to top level for frontend compatibility
        transformed.update({
            "placements": placements.get("placements", {}),
            "placement_comparison_last_3_years": placements.get("placement_comparison_last_3_years", []),
            "gender_based_placement_last_3_years": placements.get("gender_based_placement_last_3_years", []),
            "sector_wise_placement_last_3_years": placements.get("sector_wise_placement_last_3_years", []),
            "top_recruiters": placements.get("top_recruiters", []),
            "placement_highlights": placements.get("placement_highlights", ""),
        })
    
    # Fees data
    if "fees" in data:
        fees = data["fees"]
        transformed["fees_data"] = {
            "fees": fees.get("fees", {}),
            "fees_by_year": fees.get("fees_by_year", []),
            "fees_note": fees.get("fees_note", ""),
            "scholarships_detail": fees.get("scholarships_detail", []),
        }
        # Also flatten to top level for frontend compatibility
        transformed.update({
            "fees": fees.get("fees", {}),
            "fees_by_year": fees.get("fees_by_year", []),
            "fees_note": fees.get("fees_note", ""),
            "scholarships_detail": fees.get("scholarships_detail", []),
        })
    
    # Infrastructure data
    if "infrastructure" in data:
        infra = data["infrastructure"]
        transformed["infrastructure_data"] = {
            "infrastructure": infra.get("infrastructure", []),
            "hostel_details": infra.get("hostel_details", {}),
            "library_details": infra.get("library_details", {}),
            "transport_details": infra.get("transport_details", {}),
            "scholarships": infra.get("scholarships", []),
        }
        # Also flatten to top level for frontend compatibility
        transformed.update({
            "infrastructure": infra.get("infrastructure", []),
            "hostel_details": infra.get("hostel_details", {}),
            "library_details": infra.get("library_details", {}),
            "transport_details": infra.get("transport_details", {}),
            "scholarships": infra.get("scholarships", []),
        })
    
    # Keep metadata
    if "_metadata" in data:
        transformed["_metadata"] = data["_metadata"]
    
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
    """Save college data to MongoDB"""
    if college_collection is not None:
        try:
            # Check if college already exists
            existing = college_collection.find_one({"college_name": college_data["college_name"]})
            
            # Add timestamps
            college_data["updated_at"] = datetime.now(timezone.utc)
            if not existing:
                college_data["created_at"] = datetime.now(timezone.utc)
                college_data["approval_status"] = "pending"
            
            # Use upsert to either insert or update
            college_collection.replace_one(
                {"college_name": college_data["college_name"]},
                college_data,
                upsert=True
            )
            print(f"✅ Saved to MongoDB: {college_data['college_name']}")
            
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

@app.get("/api/college-statistics")
async def get_college_statistics_get(college_name: str, country: str = None, city: str = None):
    """Get college statistics via GET method - for frontend compatibility"""
    return await process_college_statistics(college_name, country, city)

async def process_college_statistics(college_name: str, country: str = None, city: str = None):
    """Process college statistics request - shared logic for GET and POST"""
    try:
        # Check cache first
        cached_data = get_cached_college_data(college_name)
        if cached_data:
            print(f"📋 Serving cached data for: {college_name}")
            return cached_data
        
        # Check MongoDB
        if college_collection is not None:
            existing = college_collection.find_one({"college_name": college_name})
            if existing and existing.get("approval_status") == "approved":
                print(f"📋 Serving MongoDB data for: {college_name}")
                # Convert ObjectId to string for JSON serialization
                existing["_id"] = str(existing["_id"])
                # Convert all datetime objects to strings recursively
                existing = convert_datetime_to_str(existing)
                
                # Transform data structure to match frontend expectations
                transformed_data = transform_data_for_frontend(existing)
                cache_college_data(college_name, transformed_data)
                return transformed_data
        
        # If not found, trigger scraping
        print(f"🔍 Starting scraping for: {college_name}")
        
        # Create a temporary college entry for scraping
        temp_college = {
            "name": college_name,
            "country": country or "Unknown",
            "location": city or "Unknown"
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
                safe_name = re.sub(r'[^\w\s-]', '', college_name).strip().replace(' ', '_')
                file_path = f"/home/ramji/Videos/scap/college_scraper/{safe_name}_normalized.json"
                
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        scraped_data = json.load(f)
                    
                    # Prepare data for MongoDB
                    mongo_data = {
                        "college_name": college_name,
                        "country": country or "Unknown",
                        "approval_status": "pending",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        **scraped_data
                    }
                    
                    # Save to MongoDB
                    save_college_to_mongodb(mongo_data)
                    
                    # Transform data for frontend before caching and returning
                    transformed_data = transform_data_for_frontend(mongo_data)
                    
                    # Cache the transformed data
                    cache_college_data(college_name, transformed_data)
                    
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
    print("🚀 Starting Serper API Server on port 8501...")
    uvicorn.run(app, host="0.0.0.0", port=8501)
