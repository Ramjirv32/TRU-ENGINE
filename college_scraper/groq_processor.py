import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from groq import Groq

# Configuration
GROQ_API_KEY = "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"
AUDIT_DIR = "/home/ramji/Videos/scap/college_scraper/autidtkpr"
OUTPUT_DIR = "/home/ramji/Videos/scap/college_scraper/autidtkpr/verified_v2"
FINAL_OUTPUT = "/home/ramji/Videos/scap/college_scraper/final.json"

client = Groq(api_key=GROQ_API_KEY)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# The Reference Structure provided by the user
REFERENCE_STRUCTURE = {
  "about": "",
  "accreditations": [
    {
      "body": "NAAC",
      "grade": "",
      "year": 2022
    }
  ],
  "additional_details": [
    {
      "category": "Global Ranking",
      "value": ""
    },
    {
      "category": "Established Year",
      "value": 0
    },
    {
      "category": "Institution Type",
      "value": ""
    },
    {
      "category": "Location",
      "value": ""
    },
    {
      "category": "Median CTC (2025)",
      "value": 0
    }
  ],
  "additional_details_list": None,
  "affiliations": [],
  "approval_status": "pending",
  "campus_area": "",
  "college_name": "",
  "contact_info": {
    "phone": "",
    "email": "",
    "address": ""
  },
  "country": "India",
  "departments": [],
  "established": 0,
  "faculty_staff": 0,
  "faculty_staff_detail": {
    "total_faculty": 0,
    "student_faculty_ratio": 0,
    "phd_faculty_percent": 0
  },
  "fees": {
    "UG": {
      "per_year": "N/A",
      "total_course": "N/A",
      "currency": "INR"
    },
    "PG": {
      "per_year": "N/A",
      "total_course": "N/A",
      "currency": "INR"
    },
    "hostel_per_year": "N/A",
    "ug_yearly_min": 0,
    "ug_yearly_max": 0,
    "pg_yearly_min": 0,
    "pg_yearly_max": 0,
    "phd_yearly_min": 0,
    "phd_yearly_max": 0
  },
  "fees_by_year": [
    {
      "year": "",
      "program_type": "",
      "per_year_local": "",
      "total_course_local": "",
      "hostel_per_year_local": "",
      "currency": "INR"
    }
  ],
  "fees_note": "",
  "gender_based_placement_last_3_years": [
    {
      "year": 0,
      "male_placed": 0,
      "female_placed": 0,
      "male_percent": 0,
      "female_percent": 0
    }
  ],
  "global_ranking": {
    "qs_world": None,
    "the_world": None,
    "us_news_global": None,
    "arwu": None,
    "webometrics": None
  },
  "global_ranking_legacy": "",
  "hostel_details": {
    "available": True,
    "boys_capacity": 0,
    "girls_capacity": 0,
    "total_capacity": 0,
    "type": ""
  },
  "infrastructure": [
    {
      "facility": "",
      "details": ""
    }
  ],
  "institution_type": "",
  "international_students": 0,
  "library_details": {
    "total_books": "",
    "journals": "",
    "e_resources": "",
    "area_sqft": ""
  },
  "location": "",
  "pg_programs": [],
  "phd_programs": [],
  "placement_comparison_last_3_years": [
    {
      "year": 0,
      "average_package": 0,
      "employment_rate_percent": 0,
      "package_currency": "LPA"
    }
  ],
  "placement_highlights": "",
  "placements": {
    "year": 0,
    "highest_package": 0,
    "average_package": 0,
    "median_package": 0,
    "package_currency": "LPA",
    "placement_rate_percent": 0,
    "total_students_placed": 0,
    "total_companies_visited": 0,
    "graduate_outcomes_note": ""
  },
  "rankings": {
    "nirf_2025": "N/A",
    "nirf_2024": "N/A",
    "qs_world": "N/A",
    "qs_asia": None,
    "the_world": None,
    "national_rank": "N/A",
    "state_rank": "N/A"
  },
  "rankings_history": None,
  "recognition": "",
  "scholarships_detail": None,
  "sector_wise_placement_last_3_years": [
    {
      "year": 0,
      "sector": "",
      "companies": "",
      "percent": 0
    }
  ],
  "short_name": "",
  "sources": None,
  "student_gender_ratio": {
    "male_percentage": 0,
    "female_percentage": 0
  },
  "student_history": {
    "student_count_comparison_last_3_years": [
      {
        "year": 0,
        "total_enrolled": -1,
        "ug": -1,
        "pg": -1,
        "phd": -1
      }
    ],
    "student_gender_ratio": {
      "total_male": 0,
      "total_female": 0,
      "male_percent": 0,
      "female_percent": 0
    },
    "international_students": {
      "total_count": 0,
      "countries_represented": None,
      "international_percent": 0
    },
    "notable_faculty": None,
    "faculty_achievements": ""
  },
  "student_statistics": [
    {
      "category": "",
      "value": 0
    }
  ],
  "student_statistics_detail": {
    "total_enrollment": 0,
    "ug_students": 0,
    "pg_students": 0,
    "phd_students": 0,
    "annual_intake": 0,
    "male_percent": 0,
    "female_percent": 0,
    "total_ug_courses": 0,
    "total_pg_courses": 0,
    "total_phd_courses": 0
  },
  "summary": "",
  "top_recruiters": [],
  "transport_details": {
    "buses": "",
    "routes": ""
  },
  "ug_programs": [],
  "website": "",
  "gemini_sections": {
    "programs": {
      "ug_programs": [],
      "pg_programs": [],
      "phd_programs": [],
      "departments": []
    },
    "fees": {
      "fees_by_year": [],
      "guessed_data": True,
      "data_year": "",
      "sources": [],
      "fees": {}
    },
    "placements": {
      "sector_wise_placement_last_3_years": [],
      "top_recruiters": [],
      "guessed_data": True,
      "data_year": 0,
      "placement_highlights": "",
      "sources": [],
      "placements": {},
      "placement_comparison_last_3_years": [],
      "gender_based_placement_last_3_years": []
    },
    "infrastructure": {
      "guessed_data": True,
      "infrastructure": [],
      "hostel_details": {},
      "library_details": {},
      "transport_details": {}
    },
    "general": {
      "institution_type": "",
      "country": "India",
      "summary": "",
      "website": "",
      "student_statistics": {},
      "faculty_staff": {},
      "student_history": {},
      "recognition": "",
      "contact_info": {},
      "college_name": "",
      "location": "",
      "about": "",
      "rankings": {},
      "accreditations": [],
      "affiliations": [],
      "campus_area": 0,
      "established": 0,
      "sources_verified": [],
      "short_name": ""
    }
  }
}

# Mapping of file name keywords to relevant keys in REFERENCE_STRUCTURE
MAPPING = {
    "identity": ["college_name", "location", "country", "established", "short_name", "website", "institution_type", "recognition", "affiliations", "accreditations", "campus_area", "contact_info", "approval_status"],
    "about": ["about", "summary"],
    "faculty_staff": ["faculty_staff", "faculty_staff_detail"],
    "student_statistics": ["student_statistics", "student_statistics_detail", "student_history"],
    "student_gender_ratio": ["student_gender_ratio"],
    "international_students": ["international_students"],
    "scholarships": ["scholarships_detail"],
    "ug_programs": ["ug_programs", "departments"],
    "pg_programs": ["pg_programs"],
    "phd_programs": ["phd_programs"],
    "fees": ["fees", "fees_by_year", "fees_note"],
    "infrastructure": ["infrastructure", "hostel_details", "library_details", "transport_details"],
    "placements_general": ["placements", "placement_highlights"],
    "placement_yearly_counts": ["placement_comparison_last_3_years"],
    "placement_gender_stats": ["gender_based_placement_last_3_years"],
    "sector_wise_placements": ["sector_wise_placement_last_3_years", "top_recruiters"],
    "rankings": ["rankings", "rankings_history", "global_ranking", "global_ranking_legacy"],
    "full_audit": list(REFERENCE_STRUCTURE.keys())
}

# Shared results dictionary
final_results = json.loads(json.dumps(REFERENCE_STRUCTURE)) # Deep copy
results_lock = threading.Lock()

def process_file(file_path):
    file_name = os.path.basename(file_path)
    
    # Identify which keys this file should fill
    relevant_keys = []
    for key in MAPPING:
        if key in file_name:
            relevant_keys.extend(MAPPING[key])
            break
            
    if not relevant_keys and "full_audit" not in file_name:
        return

    print(f"Processing {file_name}...")
    
    with open(file_path, 'r') as f:
        audit_data = json.load(f)

    # Extract snippets
    snippets = []
    for source in audit_data.get("sources", []):
        snippets.extend(source.get("snippets", []))
    
    context = "\n---\n".join(snippets[:30]) # Use more snippets
    
    # Create a structure containing only the relevant keys
    target_structure = {k: REFERENCE_STRUCTURE[k] for k in relevant_keys if k in REFERENCE_STRUCTURE}
    
    prompt = f"""
I am providing you with research snippets about a college. 
Your task is to extract the relevant data and format it EXCLUSIVELY in the following JSON structure.
Use the provided structure as a template.

REFERENCE STRUCTURE FOR OUTPUT:
{json.dumps(target_structure, indent=2)}

RESEARCH SNIPPETS:
{context}

RULES:
1. Return ONLY the JSON object. No other text.
2. If data is not found, use null or empty string/array as appropriate.
3. For numbers, provide plain numbers without units.
4. Be as accurate as possible based on the snippets.
5. If multiple values exist, choose the most recent.
"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a data extraction expert. You output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        
        response_text = completion.choices[0].message.content.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:-3].strip()
            
        parsed_response = json.loads(response_text)
        
        # Save individual result
        output_file = os.path.join(OUTPUT_DIR, f"verified_{file_name}")
        with open(output_file, 'w') as f:
            json.dump(parsed_response, f, indent=2)
            
        # Merge into final_results
        with results_lock:
            for k, v in parsed_response.items():
                if k in final_results:
                    # Basic merge: only overwrite if value is not empty/null
                    if v not in [None, "", [], {}] or final_results[k] in [None, "", [], {}]:
                        final_results[k] = v
        
        print(f"Successfully processed {file_name}")
        
    except Exception as e:
        print(f"Error processing {file_name}: {e}")

def main():
    files = [f for f in os.listdir(AUDIT_DIR) if f.endswith(".json")]
    
    print(f"Found {len(files)} files to process.")
    
    # Process in parallel with 1s gap
    with ThreadPoolExecutor(max_workers=10) as executor:
        for f in files:
            executor.submit(process_file, os.path.join(AUDIT_DIR, f))
            time.sleep(1) # 1 second gap as requested

    # After processing all, populate gemini_sections based on the extracted data
    # This is a bit complex but let's do a simple version
    with results_lock:
        gs = final_results["gemini_sections"]
        gs["programs"]["ug_programs"] = final_results.get("ug_programs", [])
        gs["programs"]["pg_programs"] = final_results.get("pg_programs", [])
        gs["programs"]["phd_programs"] = final_results.get("phd_programs", [])
        gs["programs"]["departments"] = final_results.get("departments", [])
        
        gs["fees"]["fees_by_year"] = final_results.get("fees_by_year", [])
        gs["fees"]["fees"] = final_results.get("fees", {})
        
        gs["placements"]["sector_wise_placement_last_3_years"] = final_results.get("sector_wise_placement_last_3_years", [])
        gs["placements"]["top_recruiters"] = final_results.get("top_recruiters", [])
        gs["placements"]["placement_highlights"] = final_results.get("placement_highlights", "")
        gs["placements"]["placements"] = final_results.get("placements", {})
        gs["placements"]["placement_comparison_last_3_years"] = final_results.get("placement_comparison_last_3_years", [])
        gs["placements"]["gender_based_placement_last_3_years"] = final_results.get("gender_based_placement_last_3_years", [])
        
        gs["infrastructure"]["infrastructure"] = final_results.get("infrastructure", [])
        gs["infrastructure"]["hostel_details"] = final_results.get("hostel_details", {})
        gs["infrastructure"]["library_details"] = final_results.get("library_details", {})
        gs["infrastructure"]["transport_details"] = final_results.get("transport_details", {})
        
        gs["general"]["institution_type"] = final_results.get("institution_type", "")
        gs["general"]["country"] = final_results.get("country", "India")
        gs["general"]["summary"] = final_results.get("summary", "")
        gs["general"]["website"] = final_results.get("website", "")
        gs["general"]["college_name"] = final_results.get("college_name", "")
        gs["general"]["location"] = final_results.get("location", "")
        gs["general"]["about"] = final_results.get("about", "")
        gs["general"]["recognition"] = final_results.get("recognition", "")
        gs["general"]["contact_info"] = final_results.get("contact_info", {})
        gs["general"]["accreditations"] = final_results.get("accreditations", [])
        gs["general"]["affiliations"] = final_results.get("affiliations", [])
        gs["general"]["rankings"] = final_results.get("rankings", {})
        gs["general"]["established"] = final_results.get("established", 0)

    # Save final.json
    with open(FINAL_OUTPUT, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"Final combined results saved to {FINAL_OUTPUT}")

if __name__ == "__main__":
    main()
