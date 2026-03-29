#!/usr/bin/env python3

import json
import pymongo
import redis
from datetime import datetime
import os

# Database configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

def store_college_data(file_path=None):
    """Store college data in MongoDB and Redis"""
    
    # Auto-detect the latest normalized file if not specified
    if file_path is None:
        import glob
        normalized_files = glob.glob('/home/ramji/Videos/scap/college_scraper/*_normalized.json')
        if not normalized_files:
            print("❌ No normalized files found!")
            return False
        
        # Use the most recent file
        file_path = max(normalized_files, key=os.path.getctime)
        print(f"🔍 Auto-detected latest file: {os.path.basename(file_path)}")
    
    # Load the normalized data
    with open(file_path, 'r') as f:
        college_data = json.load(f)
    
    print(f"📊 Loaded data for: {college_data['basic_info']['college_name']}")
    
    # Connect to MongoDB
    try:
        mongo_client = pymongo.MongoClient(MONGO_URI)
        db = mongo_client["erdth"]  # Same database as go-Engine
        collection = db["college_details"]  # Same collection as go-Engine
        
        # Prepare data for MongoDB
        mongo_data = {
            "college_name": college_data["basic_info"]["college_name"],
            "country": college_data["basic_info"]["country"],
            "approval_status": "approved",  # Auto-approve scraped data
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **college_data  # Include all normalized data
        }
        
        # Check if exists and update/insert
        existing = collection.find_one({"college_name": college_data["basic_info"]["college_name"]})
        if existing:
            collection.update_one(
                {"college_name": college_data["basic_info"]["college_name"]},
                {"$set": mongo_data}
            )
            print("✅ Updated existing record in MongoDB")
        else:
            collection.insert_one(mongo_data)
            print("✅ Inserted new record in MongoDB")
            
        mongo_client.close()
        
    except Exception as e:
        print(f"❌ MongoDB error: {e}")
        return False
    
    # Connect to Redis
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )
        
        # Cache the data
        cache_key = f"college:{college_data['basic_info']['college_name'].lower().replace(' ', '_')}"
        redis_client.setex(cache_key, 3600, json.dumps(mongo_data, default=str))  # Cache for 1 hour
        
        print("✅ Cached data in Redis")
        redis_client.close()
        
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False
    
    print(f"🎉 Successfully stored {college_data['basic_info']['college_name']} data!")
    return True

if __name__ == "__main__":
    print("🚀 Storing Anna University data in MongoDB and Redis...")
    store_college_data()
