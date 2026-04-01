"""
JSON Normalization and Formatting Module
Ensures consistent structure across MongoDB and Redis storage
Follows big company standards: camelCase, ISO dates, predictable nesting
"""

import json
from datetime import datetime
from typing import Any, Dict
from dateutil import parser as date_parser

class JSONNormalizer:
    """Normalizes JSON to consistent structure for MongoDB/Redis storage"""
    
    # Standard field mapping from snake_case to camelCase
    FIELD_MAPPINGS = {
        "college_name": "collegeName",
        "short_name": "shortName",
        "institution_type": "institutionType",
        "established": "established",
        "country": "country",
        "campus_area": "campusArea",
        "contact_info": "contactInfo",
        "student_statistics": "studentStatistics",
        "faculty_staff": "facultyStaff",
        "student_history": "studentHistory",
        "ug_programs": "ugPrograms",
        "pg_programs": "pgPrograms",
        "phd_programs": "phdPrograms",
        "placement_highlights": "placementHighlights",
        "top_recruiters": "topRecruiters",
        "placement_rate_percent": "placementRatePercent",
        "total_students_placed": "totalStudentsPlaced",
        "highest_package": "highestPackage",
        "average_package": "averagePackage",
        "median_package": "medianPackage",
        "package_currency": "packageCurrency",
        "total_companies_visited": "totalCompaniesVisited",
        "scholarship_detail": "scholarshipDetail",
        "scholarship_details": "scholarshipDetails",
        "fees_by_year": "feesByYear",
        "fees_note": "feesNote",
        "hostel_details": "hostelDetails",
        "library_details": "libraryDetails",
        "transport_details": "transportDetails",
        "gender_based_placement_last_3_years": "genderBasedPlacementLast3Years",
        "sector_wise_placement_last_3_years": "sectorWisePlacementLast3Years",
        "placement_comparison_last_3_years": "placementComparisonLast3Years",
        "student_count_comparison_last_3_years": "studentCountComparisonLast3Years",
        "international_students": "internationalStudents",
        "phd_faculty_percent": "phdFacultyPercent",
        "total_faculty": "totalFaculty",
        "male_percent": "malePercent",
        "female_percent": "femalePercent",
        "total_enrollment": "totalEnrollment",
        "ug_students": "ugStudents",
        "pg_students": "pgStudents",
        "phd_students": "phdStudents",
        "annual_intake": "annualIntake",
        "male_students": "maleStudents",
        "female_students": "femaleStudents",
        "national_rank": "nationalRank",
        "state_rank": "stateRank",
        "nirf_latest": "nirfLatest",
        "nirf_previous": "nirfPrevious",
        "guessed_data": "guessedData",
        "serper_sections": "serperSections",
        "basic_info": "basicInfo",
        "approval_status": "approvalStatus",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "_metadata": "metadata",
        "scraped_at": "scrapedAt",
        "qs_world": "qsWorld",
        "the_world": "theWorld",
    }

    @staticmethod
    def normalize_key(key: str) -> str:
        """Convert snake_case to camelCase"""
        if key.startswith("_"):
            key = key[1:]
        return JSONNormalizer.FIELD_MAPPINGS.get(key, key)

    @staticmethod
    def normalize_datetime(value: Any) -> str:
        """Ensure datetime is in ISO format (YYYY-MM-DDTHH:mm:ssZ)"""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                # Parse various datetime formats and convert to ISO
                dt = date_parser.parse(value)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except:
                return value
        elif isinstance(value, datetime):
            return value.strftime("%Y-%m-%dT%H:%M:%SZ")
        return str(value)

    @staticmethod
    def normalize_value(value: Any) -> Any:
        """Normalize individual values to standard types"""
        if value is None or value == "" or value == "N/A":
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            return value
        
        if isinstance(value, str):
            # Try to parse as number
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except:
                pass
            # Keep as string
            return value
        
        if isinstance(value, dict):
            return JSONNormalizer.normalize_object(value)
        
        if isinstance(value, list):
            return [JSONNormalizer.normalize_value(v) for v in value]
        
        return value

    @staticmethod
    def normalize_object(obj: Dict[str, Any], allowed_keys: list = None) -> Dict[str, Any]:
        """Recursively normalize object to camelCase with consistent structure"""
        if not isinstance(obj, dict):
            return obj
        
        normalized = {}
        
        for key, value in obj.items():
            # Skip None values and empty strings
            if value is None or value == "" or value == -1:
                continue
            
            # Normalize key name
            normalized_key = JSONNormalizer.normalize_key(key)
            
            # Handle datetime fields
            if isinstance(value, (str, datetime)) and any(dt_key in key for dt_key in ["at", "date", "time"]):
                normalized[normalized_key] = JSONNormalizer.normalize_datetime(value)
            # Handle nested objects
            elif isinstance(value, dict):
                normalized[normalized_key] = JSONNormalizer.normalize_object(value)
            # Handle arrays
            elif isinstance(value, list):
                normalized[normalized_key] = [
                    JSONNormalizer.normalize_object(item) if isinstance(item, dict) else JSONNormalizer.normalize_value(item)
                    for item in value
                ]
            # Handle primitive values
            else:
                normalized[normalized_key] = JSONNormalizer.normalize_value(value)
        
        return normalized

    @staticmethod
    def format_for_storage(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for MongoDB/Redis storage with consistent structure.
        Uses snake_case to match Go struct BSON tags
        """
        if not isinstance(data, dict):
            return data
        
        formatted = JSONNormalizer.normalize_object(data)
        
        # Extract programs from serper_sections if they exist
        serper_sections = formatted.get("serperSections", {})
        programs_data = serper_sections.get("programs_data", {})
        
        # Build programs section from serper_sections (handle camelCase from normalize_object)
        extracted_programs = {}
        if programs_data:
            extracted_programs = {
                "ug_programs": programs_data.get("ugPrograms", []),
                "pg_programs": programs_data.get("pgPrograms", []),
                "phd_programs": programs_data.get("phdPrograms", []),
                "departments": programs_data.get("departments", []),
            }
        else:
            # Fallback to individual program sections
            extracted_programs = {
                "ug_programs": serper_sections.get("ugPrograms", []),
                "pg_programs": serper_sections.get("pgPrograms", []),
                "phd_programs": serper_sections.get("phdPrograms", []),
                "departments": serper_sections.get("departments", []),
            }
        
        # Extract other sections from serper_sections
        basic_info = serper_sections.get("basic_info", {})
        placements_data = serper_sections.get("placements_data", {})
        fees_data = serper_sections.get("fees_data", {})
        
        # Ensure standard root-level fields exist (snake_case for MongoDB/Go)
        standard_structure = {
            "college_name": formatted.get("collegeName", "") or basic_info.get("college_name", ""),
            "short_name": formatted.get("shortName", "") or basic_info.get("short_name", ""),
            "established": formatted.get("established", -1) or basic_info.get("established", -1),
            "institution_type": formatted.get("institutionType", "") or basic_info.get("institution_type", ""),
            "country": formatted.get("country", "") or basic_info.get("country", ""),
            "location": formatted.get("location", "") or basic_info.get("location", ""),
            "about": formatted.get("about", "") or basic_info.get("about", ""),
            "summary": formatted.get("summary", "") or basic_info.get("summary", ""),
            "website": formatted.get("website", "") or basic_info.get("website", ""),
            "campus_area": formatted.get("campusArea", "") or basic_info.get("campus_area", ""),
            "approval_status": "pending",
            "created_at": datetime.now().isoformat() + "Z",
            "updated_at": datetime.now().isoformat() + "Z",
            
            # Programs - extracted from serper_sections (snake_case)
            "ug_programs": extracted_programs.get("ug_programs", []),
            "pg_programs": extracted_programs.get("pg_programs", []),
            "phd_programs": extracted_programs.get("phd_programs", []),
            "departments": extracted_programs.get("departments", []),
            
            # Rankings from basic_info
            "rankings": formatted.get("rankings", {}) or basic_info.get("rankings", {}),
            
            # Student statistics
            "student_statistics_detail": formatted.get("studentStatisticsDetail", {}) or serper_sections.get("student_statistics_detail", {}),
            
            # Faculty staff
            "faculty_staff_detail": formatted.get("facultyStaffDetail", {}) or serper_sections.get("faculty_staff_detail", {}),
            
            # Placements (snake_case)
            "placements": formatted.get("placements", {}) or placements_data.get("placements", {}),
            "placement_comparison_last_3_years": formatted.get("placementComparisonLast3Years", []) or placements_data.get("placement_comparison_last_3_years", []) or serper_sections.get("placement_comparison_last_3_years", []),
            "gender_based_placement_last_3_years": formatted.get("genderBasedPlacementLast3Years", []) or placements_data.get("gender_based_placement_last_3_years", []) or serper_sections.get("gender_based_placement_last_3_years", []),
            "sector_wise_placement_last_3_years": formatted.get("sectorWisePlacementLast3Years", []) or placements_data.get("sector_wise_placement_last_3_years", []) or serper_sections.get("sector_wise_placement_last_3_years", []),
            "top_recruiters": formatted.get("topRecruiters", []) or placements_data.get("top_recruiters", []) or serper_sections.get("top_recruiters", []),
            "placement_highlights": formatted.get("placementHighlights", "") or placements_data.get("placement_highlights", "") or serper_sections.get("placement_highlights", ""),
            
            # Fees (snake_case)
            "fees": formatted.get("fees", {}) or fees_data.get("fees", {}) or serper_sections.get("fees", {}),
            "fees_by_year": formatted.get("feesByYear", []) or fees_data.get("fees_by_year", []) or serper_sections.get("fees_by_year", []),
            "fees_note": formatted.get("feesNote", "") or fees_data.get("fees_note", "") or serper_sections.get("fees_note", ""),
            "scholarships_detail": formatted.get("scholarshipsDetail", []) or fees_data.get("scholarships_detail", []) or serper_sections.get("scholarships_detail", []),
            
            # Infrastructure (snake_case)
            "infrastructure": formatted.get("infrastructure", []) or serper_sections.get("infrastructure", []),
            "hostel_details": formatted.get("hostelDetails", {}) or serper_sections.get("hostel_details", {}),
            "library_details": formatted.get("libraryDetails", {}) or serper_sections.get("library_details", {}),
            "transport_details": formatted.get("transportDetails", {}) or serper_sections.get("transport_details", {}),
            
            # Additional fields
            "accreditations": formatted.get("accreditations", []) or basic_info.get("accreditations", []),
            "affiliations": formatted.get("affiliations", []) or basic_info.get("affiliations", []),
            "recognition": formatted.get("recognition", "") or basic_info.get("recognition", ""),
            "contact_info": formatted.get("contactInfo", {}) or basic_info.get("contact_info", {}),
            
            # Keep original serper sections for reference
            "serper_sections": formatted.get("serperSections", {}),
        }
        
        return standard_structure

    @staticmethod
    def to_json_string(data: Dict[str, Any], pretty: bool = True) -> str:
        """Convert to formatted JSON string"""
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False)
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    @staticmethod
    def validate_structure(data: Dict[str, Any]) -> bool:
        """Validate that data has expected structure"""
        required_fields = ["college_name", "country", "approval_status"]
        return all(field in data for field in required_fields)


def normalize_college_data(college_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point: Normalize college data for storage
    Usage: normalized = normalize_college_data(scraped_data)
    """
    normalized = JSONNormalizer.format_for_storage(college_data)
    
    # Validate structure
    if JSONNormalizer.validate_structure(normalized):
        print(f"✅ JSON normalized for storage: {normalized.get('collegeName', 'Unknown')}")
        return normalized
    else:
        print(f"⚠️  JSON validation warning: Missing required fields")
        return normalized


# Test example
if __name__ == "__main__":
    test_data = {
        "college_name": "Test University",
        "country": "India",
        "location": "Mumbai",
        "student_statistics": {
            "total_enrollment": 5000,
            "male_percent": 60,
            "female_percent": 40
        },
        "ug_programs": ["B.E. CSE", "B.E. Mechanical"],
        "created_at": "2026-04-01T10:00:00Z"
    }
    
    result = normalize_college_data(test_data)
    print(json.dumps(result, indent=2))
