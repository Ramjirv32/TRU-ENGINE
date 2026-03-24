#!/usr/bin/env python3
"""
Schema Validator & MongoDB Helper
Validates JSON files against schema and provides MongoDB insertion utilities
"""

import json
import os
from typing import Dict, Any, List, Tuple
from datetime import datetime

# ============================================================================
# SCHEMA VALIDATION
# ============================================================================

def validate_schema(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates data against expected schema
    Returns: (is_valid, list_of_errors)
    """
    errors = []
    
    # Required top-level keys
    required_keys = ["basic_info", "programs", "placements", "fees", "infrastructure", "_metadata"]
    for key in required_keys:
        if key not in data:
            errors.append(f"Missing top-level key: {key}")
    
    # Validate basic_info
    if "basic_info" in data:
        bi = data["basic_info"]
        required_bi = ["college_name", "country", "location", "website", "rankings", 
                       "student_statistics", "faculty_staff", "accreditations"]
        for key in required_bi:
            if key not in bi:
                errors.append(f"basic_info missing: {key}")
        
        # Accreditations must be array
        if "accreditations" in bi and not isinstance(bi["accreditations"], list):
            errors.append(f"basic_info.accreditations must be array, got {type(bi['accreditations'])}")
    
    # Validate programs
    if "programs" in data:
        prog = data["programs"]
        required_prog = ["ug_programs", "pg_programs", "phd_programs", "departments"]
        for key in required_prog:
            if key not in prog:
                errors.append(f"programs missing: {key}")
            elif not isinstance(prog[key], list):
                errors.append(f"programs.{key} must be array, got {type(prog[key])}")
    
    # Validate placements
    if "placements" in data:
        plc = data["placements"]
        if "placements" in plc:
            inner = plc["placements"]
            if "package_currency" not in inner:
                errors.append("placements.placements missing: package_currency")
    
    # Validate fees
    if "fees" in data:
        fees = data["fees"]
        if "fees" in fees:
            fee_struct = fees["fees"]
            for level in ["UG", "PG"]:
                if level in fee_struct:
                    if "currency" not in fee_struct[level]:
                        errors.append(f"fees.fees.{level} missing: currency")
    
    # Validate infrastructure
    if "infrastructure" in data:
        infra = data["infrastructure"]
        required_infra = ["infrastructure", "hostel_details", "library_details", "scholarships"]
        for key in required_infra:
            if key not in infra:
                errors.append(f"infrastructure missing: {key}")
    
    return (len(errors) == 0, errors)

def validate_file(filepath: str) -> None:
    """Validate a single JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        is_valid, errors = validate_schema(data)
        
        filename = os.path.basename(filepath)
        print(f"\n{'='*70}")
        print(f"📄 {filename}")
        print(f"{'='*70}")
        
        if is_valid:
            print("✅ VALID - Schema matches expected structure")
            
            # Print summary
            college_name = data.get("_metadata", {}).get("college_name", "Unknown")
            print(f"\n📊 Summary:")
            print(f"   College: {college_name}")
            print(f"   UG Programs: {len(data.get('programs', {}).get('ug_programs', []))}")
            print(f"   PG Programs: {len(data.get('programs', {}).get('pg_programs', []))}")
            print(f"   PhD Programs: {len(data.get('programs', {}).get('phd_programs', []))}")
            print(f"   Departments: {len(data.get('programs', {}).get('departments', []))}")
            print(f"   Accreditations: {len(data.get('basic_info', {}).get('accreditations', []))}")
            print(f"   Scholarships: {len(data.get('infrastructure', {}).get('scholarships', []))}")
        else:
            print("❌ INVALID - Schema errors found:")
            for i, error in enumerate(errors, 1):
                print(f"   {i}. {error}")
        
        print()
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {str(e)}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

# ============================================================================
# MONGODB HELPERS
# ============================================================================

def generate_mongodb_insert_script(data: Dict[str, Any], collection_name: str = "colleges") -> str:
    """Generate MongoDB insertion script"""
    
    script = f"""// MongoDB Insertion Script
// Generated: {datetime.utcnow().isoformat()}

use college_db;

db.{collection_name}.insertOne({json.dumps(data, indent=2, ensure_ascii=False)});
"""
    return script

def export_to_mongodb_script(input_dir: str, output_file: str) -> None:
    """Export all JSON files to MongoDB script"""
    
    files = [f for f in os.listdir(input_dir) if f.endswith('_normalized.json')]
    
    script = f"""// MongoDB Bulk Insert Script
// Generated: {datetime.utcnow().isoformat()}
// Files: {len(files)}

use college_db;

db.colleges.insertMany([
"""
    
    documents = []
    for i, filename in enumerate(files):
        filepath = os.path.join(input_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)
            documents.append(json.dumps(data, indent=2, ensure_ascii=False))
    
    script += ",\n".join(documents)
    script += "\n]);\n"
    
    with open(output_file, 'w') as f:
        f.write(script)
    
    print(f"✅ MongoDB script saved: {output_file}")
    print(f"   Documents: {len(documents)}")

# ============================================================================
# PYMONGO EXAMPLE
# ============================================================================

def print_pymongo_example():
    """Print example PyMongo code"""
    
    code = """
# ============================================================================
# PyMongo Insertion Example
# ============================================================================

from pymongo import MongoClient
import json
import os

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["college_db"]
collection = db["colleges"]

# Create indexes
collection.create_index("basic_info.college_name")
collection.create_index("basic_info.country")
collection.create_index("basic_info.rankings.qs_world")
collection.create_index("_metadata.scraped_at")

# Insert from directory
input_dir = "/home/ramji/Videos/scap/college_scraper"

for filename in os.listdir(input_dir):
    if filename.endswith("_normalized.json"):
        filepath = os.path.join(input_dir, filename)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Upsert (update if exists, insert if not)
        collection.update_one(
            {"basic_info.college_name": data["basic_info"]["college_name"]},
            {"$set": data},
            upsert=True
        )
        
        print(f"✅ Inserted: {data['basic_info']['college_name']}")

print(f"\\n✨ Total documents in collection: {collection.count_documents({})}")

# Query examples
print("\\n📊 Query Examples:")

# 1. Find top QS ranked universities
print("\\n1. Top 5 QS Ranked:")
for doc in collection.find({"basic_info.rankings.qs_world": {"$gt": 0}}).sort("basic_info.rankings.qs_world", 1).limit(5):
    print(f"   {doc['basic_info']['college_name']}: QS #{doc['basic_info']['rankings']['qs_world']}")

# 2. Find by country
print("\\n2. Indian Universities:")
for doc in collection.find({"basic_info.country": "India"}):
    print(f"   {doc['basic_info']['college_name']}")

# 3. Find with highest placement package
print("\\n3. Highest Placement Package:")
for doc in collection.find({"placements.placements.highest_package": {"$gt": 0}}).sort("placements.placements.highest_package", -1).limit(3):
    pkg = doc['placements']['placements']['highest_package']
    curr = doc['placements']['placements']['package_currency']
    print(f"   {doc['basic_info']['college_name']}: {pkg} {curr}")

"""
    
    print(code)

# ============================================================================
# MAIN CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python validate_schema.py validate <file_or_directory>")
        print("  python validate_schema.py export <input_dir> <output_script>")
        print("  python validate_schema.py pymongo-example")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        target = sys.argv[2] if len(sys.argv) > 2 else "/home/ramji/Videos/scap/college_scraper"
        
        if os.path.isfile(target):
            validate_file(target)
        elif os.path.isdir(target):
            files = [f for f in os.listdir(target) if f.endswith('_normalized.json')]
            print(f"\n🔍 Validating {len(files)} files in {target}...\n")
            
            for filename in files:
                filepath = os.path.join(target, filename)
                validate_file(filepath)
        else:
            print(f"❌ Not found: {target}")
    
    elif command == "export":
        input_dir = sys.argv[2] if len(sys.argv) > 2 else "/home/ramji/Videos/scap/college_scraper"
        output_file = sys.argv[3] if len(sys.argv) > 3 else "mongodb_insert.js"
        export_to_mongodb_script(input_dir, output_file)
    
    elif command == "pymongo-example":
        print_pymongo_example()
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)