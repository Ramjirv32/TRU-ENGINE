import subprocess
import json
import time
import os
import re
import concurrent.futures
from typing import Dict, Any, List
from datetime import datetime

API_KEY = "c138d04299d00500bdf9168ba3a04143fadcae1fab8437f2c4bb9b5437dc24d8"

COLLEGES = [
    {"name": "Anna University", "country": "India", "location": "chennai"},

]

QUERIES = {
    "basic_info": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified institutional data for the 2026 academic year or the latest available year if 2026 data is not published. Return only valid JSON with the exact fields: college_name, short_name, established, institution_type, country, location, website, about, summary, rankings (nirf_latest, nirf_previous, qs_world, national_rank, state_rank, guessed_data), student_statistics (total_enrollment, ug_students, pg_students, phd_students, annual_intake, male_percent, female_percent, total_ug_courses, total_pg_courses, total_phd_courses, guessed_data), faculty_staff (total_faculty, student_faculty_ratio, phd_faculty_percent, guessed_data), student_history (student_count_comparison_last_3_years with 2026, 2025, 2024, international_students, guessed_data, categorywise_student_comparison_last_3_years: [{\"year\": \"2026\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}, {\"year\": \"2025\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}, {\"year\": \"2024\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}]), accreditations (body, grade, year), affiliations, recognition, campus_area, contact_info (phone, email, address), and sources_verified (array of URLs or document names). IMPORTANT: Find actual numerical values from official sources for 2026. For past years (2025=2026-1, 2024=2026-2), provide comparative data if available. Do not use -1 unless data is genuinely unavailable. Provide estimates based on similar institutions if exact data is not found, but mark as guessed_data: true. Do not add any extra text, only JSON.",
    "programs": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide a COMPREHENSIVE list of ALL officially offered UG, PG, and PhD programs and departments as of the 2026 academic year. Use only official college website, latest NIRF, AICTE, or UGC‑recognized sources. Do not invent any program. Return only valid JSON with keys: ug_programs (complete list of ALL undergraduate programs with specializations), pg_programs (complete list of ALL postgraduate programs with specializations), phd_programs (complete list of ALL doctoral programs with specializations), departments (complete list of ALL academic departments). If a level has no programs, use an empty array []. Include a \"sources_verified\" array with URLs or document names. IMPORTANT: Find actual program counts and lists from official sources for 2026. Do not use -1 for program counts - provide actual numbers or 0 if none exist. List EVERY single program offered, including all branches, specializations, and interdisciplinary programs. Do not group or summarize programs - list each one individually.",
    "placements": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest verified placement data for 2026, 2025, and 2024. Use only official placement reports, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"2026\", \"sources\": [\"source URL or document name\"], \"placements\": {\"year\": \"2026\", \"highest_package\": real_number, \"average_package\": real_number, \"median_package\": real_number, \"package_currency\": \"LPA\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges, \"placement_rate_percent\": real_percent, \"total_students_placed\": integer, \"total_companies_visited\": integer, \"graduate_outcomes_note\": \"factual note\"}, \"placement_comparison_last_3_years\": [{\"year\":\"2026\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":\"2025\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":\"2024\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}], \"gender_based_placement_last_3_years\": [{\"year\":\"2026\", \"male_placed\": integer, \"female_placed\": integer, \"male_percent\": real_percent, \"female_percent\": real_percent}], \"sector_wise_placement_last_3_years\": [{\"year\":\"2026\", \"sector\": \"sector name\", \"companies\": [\"company names\"], \"percent\": real_percent}], \"top_recruiters\": [\"company names\"], \"placement_highlights\": \"2-3 sentence factual summary\"}. IMPORTANT: Find actual placement statistics from official sources for each year. Do not use -1 unless data is genuinely unavailable. Provide reasonable estimates based on similar institutions if exact data is not found, but mark as guessed_data: true. Always include currency_type field for all monetary values.",
    "fees": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified fee structure for 2026, 2025, and 2024. Use only official college website, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"2026\", \"sources\": [\"source URL or document name\"], \"fees\": {\"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PhD\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"hostel_per_year\": real_number}, \"fees_by_year\": [{\"year\": \"2026\", \"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PhD\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"hostel_per_year\": real_number}, {\"year\": \"2025\", \"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PhD\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"hostel_per_year\": real_number}, {\"year\": \"2024\", \"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PhD\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"hostel_per_year\": real_number}], \"fees_note\": \"2-3 sentence factual summary\", \"scholarships_detail\": [{\"name\": \"scholarship name\", \"amount\": real_number, \"currency_type\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges, \"eligibility\": \"eligibility criteria\", \"provider\": \"provider name\"}]}. IMPORTANT: Find actual fee amounts from official sources for each year. Do not use -1 unless data is genuinely unavailable. Provide reasonable estimates based on similar institutions if exact data is not found, but mark as guessed_data: true. Always include currency_type field for all monetary values.",
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

# ============================================================================
# NORMALIZER FUNCTIONS - INTEGRATED FROM normalizer.py
# ============================================================================

def get_default_schema() -> Dict[str, Any]:
    """Returns the canonical MongoDB schema with default values"""
    return {
        "basic_info": {
            "college_name": "N/A",
            "short_name": "N/A",
            "established": -1,
            "institution_type": "N/A",
            "country": "N/A",
            "location": "N/A",
            "website": "N/A",
            "about": "N/A",
            "summary": "N/A",
            "rankings": {
                "nirf_latest": -1,
                "nirf_previous": -1,
                "qs_world": -1,
                "national_rank": -1,
                "state_rank": -1,
                "guessed_data": False
            },
            "student_statistics": {
                "total_enrollment": -1,
                "ug_students": -1,
                "pg_students": -1,
                "phd_students": -1,
                "annual_intake": -1,
                "male_percent": -1,
                "female_percent": -1,
                "total_ug_courses": -1,
                "total_pg_courses": -1,
                "total_phd_courses": -1,
                "guessed_data": False
            },
            "faculty_staff": {
                "total_faculty": -1,
                "student_faculty_ratio": -1,
                "phd_faculty_percent": -1,
                "guessed_data": False
            },
            "student_history": {
                "student_count_comparison_last_3_years": {
                    "latest_year": -1,
                    "previous_year": -1,
                    "year_before_previous": -1
                },
                "international_students": -1,
                "guessed_data": False,
                "categorywise_student_comparison_last_3_years": [
                    {
                        "year": "latest_year",
                        "ug_students": -1,
                        "pg_students": -1,
                        "phd_students": -1,
                        "international_students": -1,
                        "domestic_students": -1,
                        "male_students": -1,
                        "female_students": -1
                    },
                    {
                        "year": "previous_year",
                        "ug_students": -1,
                        "pg_students": -1,
                        "phd_students": -1,
                        "international_students": -1,
                        "domestic_students": -1,
                        "male_students": -1,
                        "female_students": -1
                    },
                    {
                        "year": "year_before_previous",
                        "ug_students": -1,
                        "pg_students": -1,
                        "phd_students": -1,
                        "international_students": -1,
                        "domestic_students": -1,
                        "male_students": -1,
                        "female_students": -1
                    }
                ]
            },
            "accreditations": [],
            "affiliations": "N/A",
            "recognition": "N/A",
            "campus_area": "N/A",
            "contact_info": {
                "phone": "N/A",
                "email": "N/A",
                "address": "N/A"
            },
            "sources_verified": []
        },
        "programs": {
            "ug_programs": [],
            "pg_programs": [],
            "phd_programs": [],
            "departments": [],
            "sources_verified": []
        },
        "placements": {
            "guessed_data": False,
            "data_year": "N/A",
            "sources": [],
            "placements": {
                "year": "N/A",
                "highest_package": -1,
                "average_package": -1,
                "median_package": -1,
                "package_currency": "N/A",
                "placement_rate_percent": -1,
                "total_students_placed": -1,
                "total_companies_visited": -1,
                "graduate_outcomes_note": "N/A"
            },
            "placement_comparison_last_3_years": [],
            "gender_based_placement_last_3_years": [],
            "sector_wise_placement_last_3_years": [],
            "top_recruiters": [],
            "placement_highlights": "N/A"
        },
        "fees": {
            "guessed_data": False,
            "data_year": "N/A",
            "sources": [],
            "fees": {
                "UG": {
                    "per_year": -1,
                    "total_course": -1,
                    "currency": "N/A"
                },
                "PG": {
                    "per_year": -1,
                    "total_course": -1,
                    "currency": "N/A"
                },
                "hostel_per_year": -1
            },
            "fees_by_year": [],
            "fees_note": "N/A",
            "scholarships_detail": []
        },
        "infrastructure": {
            "guessed_data": False,
            "sources_verified": [],
            "infrastructure": [],
            "hostel_details": {
                "available": False,
                "total_capacity": -1,
                "type": "N/A"
            },
            "library_details": {
                "total_books": -1,
                "journals": -1,
                "e_resources": -1,
                "area_sqft": -1
            },
            "transport_details": {
                "buses": -1,
                "routes": -1
            },
            "scholarships": []
        },
        "_metadata": {
            "scraped_at": datetime.utcnow().isoformat(),
            "total_time": 0,
            "errors": {},
            "validation_warnings": []
        }
    }

# ============================================================================
# TYPE NORMALIZATION
# ============================================================================

def to_int(value: Any, default: int = -1) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    
    value_str = str(value).strip()
    
    # Handle explicit "N/A" values
    if value_str.upper() in ("N/A", "NA", "NULL", "NONE", "UNDEFINED", "-1"):
        return default
    
    # Special handling for ranking values with "+", ">", etc.
    if "+" in value_str or ">" in value_str:
        # For rankings like "1401+" or ">1000", extract the number part
        import re
        match = re.search(r'(\d+)', value_str)
        if match:
            return int(match.group(1))
        else:
            return default
    
    try:
        return int(float(value_str))
    except (ValueError, TypeError):
        return default

def to_float(value: Any, default: float = -1.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    
    value_str = str(value).strip()
    
    # Handle explicit "N/A" values
    if value_str.upper() in ("N/A", "NA", "NULL", "NONE", "UNDEFINED", "-1"):
        return default
    
    try:
        return round(float(value_str), 2)
    except (ValueError, TypeError):
        return default

def to_str(value: Any, default: str = "N/A") -> str:
    if value is None or str(value).strip() == "":
        return default
    cleaned = str(value).strip()
    # Normalize sentinel variants: "NA", "na", "n/a", "null", "none"
    if cleaned.lower() in ("na", "n/a", "null", "none", "undefined"):
        return "N/A"
    return cleaned

def to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return default

def to_list(value: Any, default: list = None) -> list:
    if default is None:
        default = []
    if isinstance(value, list):
        return value
    return default

# ============================================================================
# SECTION NORMALIZERS
# ============================================================================

def normalize_basic_info(raw: Dict) -> Dict:
    warnings = []

    # --- Rankings ---
    rankings_raw = raw.get("rankings", {}) or {}
    rankings = {
        "nirf_latest":   to_int(rankings_raw.get("nirf_latest"), -1),
        "nirf_previous": to_int(rankings_raw.get("nirf_previous"), -1),
        "qs_world":      to_int(rankings_raw.get("qs_world"), -1),
        "national_rank": to_int(rankings_raw.get("national_rank"), -1),
        "state_rank":    to_int(rankings_raw.get("state_rank"), -1),
        "guessed_data":  to_bool(rankings_raw.get("guessed_data"), False),
    }

    # --- Student Statistics ---
    ss_raw = raw.get("student_statistics", {}) or {}
    ug  = to_int(ss_raw.get("ug_students"), -1)
    pg  = to_int(ss_raw.get("pg_students"), -1)
    phd = to_int(ss_raw.get("phd_students"), -1)

    # Compute correct total_enrollment
    reported_total = to_int(ss_raw.get("total_enrollment"), -1)
    known_parts = [v for v in [ug, pg, phd] if v != -1]
    computed_total = sum(known_parts) if known_parts else -1

    if reported_total != -1 and computed_total != -1 and reported_total < max(ug, pg, phd):
        warnings.append(
            f"FIX-1 [CRITICAL]: total_enrollment={reported_total} was less than "
            f"ug_students={ug}. Corrected to computed value {computed_total} (ug+pg+phd)."
        )
        total_enrollment = computed_total
    elif reported_total == -1 and computed_total != -1:
        total_enrollment = computed_total
        warnings.append(
            f"FIX-1 [AUTO]: total_enrollment was missing; computed as {computed_total}."
        )
    else:
        total_enrollment = reported_total

    student_statistics = {
        "total_enrollment": total_enrollment,
        "ug_students":      ug,
        "pg_students":      pg,
        "phd_students":     phd,
        "annual_intake":    to_int(ss_raw.get("annual_intake"), -1),
        "male_percent":     to_float(ss_raw.get("male_percent"), -1.0),
        "female_percent":   to_float(ss_raw.get("female_percent"), -1.0),
        "total_ug_courses": to_int(ss_raw.get("total_ug_courses"), -1),
        "total_pg_courses": to_int(ss_raw.get("total_pg_courses"), -1),
        "total_phd_courses":to_int(ss_raw.get("total_phd_courses"), -1),
        "guessed_data":     to_bool(ss_raw.get("guessed_data"), False),
    }

    # --- Faculty ---
    fac_raw = raw.get("faculty_staff", {}) or {}
    faculty_staff = {
        "total_faculty":        to_int(fac_raw.get("total_faculty"), -1),
        "student_faculty_ratio":to_float(fac_raw.get("student_faculty_ratio"), -1.0),
        "phd_faculty_percent":  to_float(fac_raw.get("phd_faculty_percent"), -1.0),
        "guessed_data":         to_bool(fac_raw.get("guessed_data"), False),
    }

    # --- Student History ---
    sh_raw = raw.get("student_history", {}) or {}
    sc_raw = sh_raw.get("student_count_comparison_last_3_years", {}) or {}
    student_history = {
        "student_count_comparison_last_3_years": {
            "latest_year":          to_int(sc_raw.get("latest_year"), -1),
            "previous_year":        to_int(sc_raw.get("previous_year"), -1),
            "year_before_previous": to_int(sc_raw.get("year_before_previous"), -1),
        },
        "international_students": to_int(sh_raw.get("international_students"), -1),
        "guessed_data":           to_bool(sh_raw.get("guessed_data"), False),
        "categorywise_student_comparison_last_3_years": normalize_categorywise(
            to_list(sh_raw.get("categorywise_student_comparison_last_3_years")),
            warnings
        ),
    }

    # --- Accreditations (always array) ---
    acc_raw = raw.get("accreditations", [])
    if isinstance(acc_raw, dict):
        acc_raw = [acc_raw]
        warnings.append("FIX: accreditations was a dict; converted to array.")
    accreditations = [
        {
            "body":  to_str(a.get("body")),
            "grade": to_str(a.get("grade")),
            "year":  to_int(a.get("year"), -1),
        }
        for a in to_list(acc_raw)
    ]

    # --- Contact ---
    ct_raw = raw.get("contact_info", {}) or {}
    contact_info = {
        "phone":   to_str(ct_raw.get("phone")),
        "email":   to_str(ct_raw.get("email")),
        "address": to_str(ct_raw.get("address")),
    }

    return {
        "college_name":      to_str(raw.get("college_name")),
        "short_name":        to_str(raw.get("short_name")),
        "established":       to_int(raw.get("established"), -1),
        "institution_type":  to_str(raw.get("institution_type")),
        "country":           to_str(raw.get("country")),
        "location":          to_str(raw.get("location")),
        "website":           to_str(raw.get("website")),
        "about":             to_str(raw.get("about")),
        "summary":           to_str(raw.get("summary")),
        "rankings":          rankings,
        "student_statistics":student_statistics,
        "faculty_staff":     faculty_staff,
        "student_history":   student_history,
        "accreditations":    accreditations,
        "affiliations":      to_str(raw.get("affiliations")),
        "recognition":       to_str(raw.get("recognition")),
        "campus_area":       to_str(raw.get("campus_area")),
        "contact_info":      contact_info,
        "sources_verified":  to_list(raw.get("sources_verified")),
        "_warnings":         warnings,
    }

def normalize_categorywise(rows: List[Dict], warnings: List[str]) -> List[Dict]:
    """Ensures all 3 year rows have the full set of keys."""
    REQUIRED_KEYS = [
        "year", "ug_students", "pg_students", "phd_students",
        "international_students", "domestic_students",
        "male_students", "female_students",
    ]
    normalized = []
    for row in rows:
        norm_row = {"year": to_str(row.get("year"), "N/A")}
        for key in REQUIRED_KEYS[1:]:  # skip "year"
            norm_row[key] = to_int(row.get(key), -1)

        # Auto-compute domestic_students if missing but computable
        if norm_row["domestic_students"] == -1:
            parts = [norm_row[k] for k in ("ug_students", "pg_students", "phd_students")
                     if norm_row[k] != -1]
            intl = norm_row["international_students"]
            if parts:
                computed = sum(parts) - (intl if intl != -1 else 0)
                norm_row["domestic_students"] = computed
                warnings.append(
                    f"FIX-3 [AUTO]: domestic_students computed as {computed} "
                    f"for year {norm_row['year']}."
                )

        # Flag any still-missing keys
        missing = [k for k in REQUIRED_KEYS if k not in row]
        if missing:
            warnings.append(
                f"FIX-3 [SCHEMA]: Added missing keys {missing} "
                f"for year {norm_row['year']} (set to -1)."
            )

        normalized.append(norm_row)

    return normalized

def normalize_programs(raw: Dict) -> Dict:
    return {
        "ug_programs":      to_list(raw.get("ug_programs")),
        "pg_programs":      to_list(raw.get("pg_programs")),
        "phd_programs":     to_list(raw.get("phd_programs")),
        "departments":      to_list(raw.get("departments")),
        "sources_verified": to_list(raw.get("sources_verified")),
    }

def normalize_placements(raw: Dict) -> Dict:
    warnings = []

    p_raw = raw.get("placements", {}) or {}
    placements = {
        "year":                   to_str(p_raw.get("year")),
        "highest_package":        to_float(p_raw.get("highest_package"), -1.0),
        "average_package":        to_float(p_raw.get("average_package"), -1.0),
        "median_package":         to_float(p_raw.get("median_package"), -1.0),
        "package_currency":       to_str(p_raw.get("package_currency")),
        "placement_rate_percent": to_float(p_raw.get("placement_rate_percent"), -1.0),
        "total_students_placed":  to_int(p_raw.get("total_students_placed"), -1),
        "total_companies_visited":to_int(p_raw.get("total_companies_visited"), -1),
        "graduate_outcomes_note": to_str(p_raw.get("graduate_outcomes_note")),
    }

    # Clean dirty source strings (e.g. "\n\nNIRF...\n\n")
    raw_sources = to_list(raw.get("sources"))
    clean_sources = [s.strip() for s in raw_sources if isinstance(s, str) and s.strip()]
    if len(clean_sources) != len(raw_sources):
        warnings.append("FIX-BONUS: Removed whitespace/empty entries from sources array.")

    def norm_comparison(row: Dict) -> Dict:
        return {
            "year":                   to_str(row.get("year")),
            "average_package":        to_float(row.get("average_package"), -1.0),
            "employment_rate_percent":to_float(row.get("employment_rate_percent"), -1.0),
            "package_currency":       to_str(row.get("package_currency")),
        }

    def norm_gender(row: Dict) -> Dict:
        return {
            "year":           to_str(row.get("year")),
            "male_placed":    to_int(row.get("male_placed"), -1),
            "female_placed":  to_int(row.get("female_placed"), -1),
            "male_percent":   to_float(row.get("male_percent"), -1.0),
            "female_percent": to_float(row.get("female_percent"), -1.0),
        }

    def norm_sector(row: Dict) -> Dict:
        return {
            "year":      to_str(row.get("year")),
            "sector":    to_str(row.get("sector")),
            "companies": to_list(row.get("companies")),
            "percent":   to_float(row.get("percent"), -1.0),
        }

    return {
        "guessed_data":    to_bool(raw.get("guessed_data"), False),
        "data_year":       to_str(raw.get("data_year")),
        "sources":         clean_sources,
        "placements":      placements,
        "placement_comparison_last_3_years":  [norm_comparison(r) for r in to_list(raw.get("placement_comparison_last_3_years"))],
        "gender_based_placement_last_3_years":[norm_gender(r)     for r in to_list(raw.get("gender_based_placement_last_3_years"))],
        "sector_wise_placement_last_3_years": [norm_sector(r)     for r in to_list(raw.get("sector_wise_placement_last_3_years"))],
        "top_recruiters":        to_list(raw.get("top_recruiters")),
        "placement_highlights":  to_str(raw.get("placement_highlights")),
        "_warnings":             warnings,
    }

def normalize_fees(raw: Dict) -> Dict:
    def norm_fee_block(block: Dict) -> Dict:
        return {
            "per_year":     to_float(block.get("per_year"), -1.0),
            "total_course": to_float(block.get("total_course"), -1.0),
            "currency":     to_str(block.get("currency")),
        }

    def norm_scholarship(s: Dict) -> Dict:
        return {
            "name":          to_str(s.get("name")),
            "amount":        to_float(s.get("amount"), -1.0),  # null → -1.0
            "currency_type": to_str(s.get("currency_type")),
            "eligibility":   to_str(s.get("eligibility")),
            "provider":      to_str(s.get("provider")),
        }

    fees_raw = raw.get("fees", {}) or {}
    fees = {
        "UG":            norm_fee_block(fees_raw.get("UG", {})),
        "PG":            norm_fee_block(fees_raw.get("PG", {})),
        "hostel_per_year": to_float(fees_raw.get("hostel_per_year"), -1.0),
    }

    fees_by_year = []
    for entry in to_list(raw.get("fees_by_year")):
        fees_by_year.append({
            "year": to_str(entry.get("year")),
            "UG":   norm_fee_block(entry.get("UG", {})),
            "PG":   norm_fee_block(entry.get("PG", {})),
            "hostel_per_year": to_float(entry.get("hostel_per_year"), -1.0),
        })

    return {
        "guessed_data":       to_bool(raw.get("guessed_data"), False),
        "data_year":          to_str(raw.get("data_year")),
        "sources":            to_list(raw.get("sources")),
        "fees":               fees,
        "fees_by_year":       fees_by_year,
        "fees_note":          to_str(raw.get("fees_note")),
        "scholarships_detail":[norm_scholarship(s) for s in to_list(raw.get("scholarships_detail"))],
    }

def normalize_infrastructure(raw: Dict) -> Dict:
    def norm_scholarship(s: Dict) -> Dict:
        return {
            "name":                 to_str(s.get("name")),
            "amount":               to_float(s.get("amount"), -1.0),  # null → -1.0
            "currency_type":        to_str(s.get("currency_type")),
            "eligibility":          to_str(s.get("eligibility")),
            "provider":             to_str(s.get("provider")),
            "type":                 to_str(s.get("type")),
            "application_deadline": to_str(s.get("application_deadline")),  # "NA" → "N/A"
        }

    hd_raw = raw.get("hostel_details", {}) or {}
    hostel_details = {
        "available":      to_bool(hd_raw.get("available"), False),
        "total_capacity": to_int(hd_raw.get("total_capacity"), -1),
        "type":           to_str(hd_raw.get("type")),
    }

    ld_raw = raw.get("library_details", {}) or {}
    library_details = {
        "total_books": to_int(ld_raw.get("total_books"), -1),
        "journals":    to_int(ld_raw.get("journals"), -1),
        "e_resources": to_int(ld_raw.get("e_resources"), -1),
        "area_sqft":   to_float(ld_raw.get("area_sqft"), -1.0),   # FIX-2: always DECIMAL float
    }

    td_raw = raw.get("transport_details", {}) or {}
    transport_details = {
        "buses":  to_int(td_raw.get("buses"), -1),
        "routes": to_int(td_raw.get("routes"), -1),
    }

    return {
        "guessed_data":     to_bool(raw.get("guessed_data"), False),
        "sources_verified": to_list(raw.get("sources_verified")),
        "infrastructure":   to_list(raw.get("infrastructure")),
        "hostel_details":   hostel_details,
        "library_details":  library_details,
        "transport_details":transport_details,
        "scholarships":     [norm_scholarship(s) for s in to_list(raw.get("scholarships"))],
    }

# ============================================================================
# MASTER NORMALIZER  —  single entry point
# ============================================================================

SECTION_NORMALIZERS = {
    "basic_info":     normalize_basic_info,
    "programs":       normalize_programs,
    "placements":     normalize_placements,
    "fees":           normalize_fees,
    "infrastructure": normalize_infrastructure,
}

def normalize_to_schema(raw_data: Dict, section: str) -> Dict:
    """
    Normalize raw LLM output to match the MongoDB schema.
    Applies all type fixes, sentinel normalization, and validation rules.
    Returns the normalized dict for the given section.
    """
    if not raw_data or not isinstance(raw_data, dict):
        return {}

    normalizer = SECTION_NORMALIZERS.get(section)
    if not normalizer:
        raise ValueError(f"Unknown section: '{section}'. Valid: {list(SECTION_NORMALIZERS)}")

    return normalizer(raw_data)

def normalize_college(college_raw: Dict) -> Dict:
    """
    Normalize a full college record (all sections at once).
    Collects all _warnings into _metadata.validation_warnings.
    """
    all_warnings = []
    normalized = {}

    for section in SECTION_NORMALIZERS:
        raw_section = college_raw.get(section, {})
        result = normalize_to_schema(raw_section, section)

        # Collect and remove per-section _warnings
        all_warnings.extend(result.pop("_warnings", []))
        normalized[section] = result

    # Rebuild metadata
    meta = college_raw.get("_metadata", {})
    normalized["_metadata"] = {
        "scraped_at":          meta.get("scraped_at", datetime.utcnow().isoformat()),
        "total_time":          meta.get("total_time", 0),
        "errors":              meta.get("errors", {}),
        "validation_warnings": all_warnings,
        "college_name":        meta.get("college_name", "N/A"),
        "country":             meta.get("country", "N/A"),
        "schema_version":      "v1.1",
    }

    return normalized

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
    
    # Create separate files for each college and normalize them
    for college, data in colleges_data.items():
        # Sanitize college name for filename
        safe_college_name = re.sub(r'[^\w\s-]', '', college).strip().replace(' ', '_')
        
        # First, save the raw scraped data
        raw_output_file = f"/home/ramji/Videos/scap/college_scraper/{safe_college_name}.json"
        with open(raw_output_file, "w") as f:
            json.dump(data, f, indent=2)
        
        # Then normalize the data and save normalized version
        print(f"\n🔧 Normalizing {college}...")
        try:
            normalized_data = normalize_college(data)
            normalized_output_file = f"/home/ramji/Videos/scap/college_scraper/{safe_college_name}_normalized.json"
            
            with open(normalized_output_file, "w") as f:
                json.dump(normalized_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ {college}: {data['_metadata']['total_time']:.2f}s")
            print(f"   └─ Raw data saved to: {raw_output_file}")
            print(f"   └─ Normalized data saved to: {normalized_output_file}")
            print(f"   └─ Errors: {len(normalized_data['_metadata']['errors'])}")
            print(f"   └─ Warnings: {len(normalized_data['_metadata']['validation_warnings'])}")
            
        except Exception as e:
            print(f"✗ Error normalizing {college}: {str(e)}")
            print(f"   └─ Raw data still available at: {raw_output_file}")
    
    print(f"\n{'='*50}")
    print(f"Total time taken: {total_time_taken_seconds} seconds")
    print(f"Raw and normalized college files created successfully!")
    print(f"Raw files: College_Name.json")
    print(f"Normalized files: College_Name_normalized.json")

if __name__ == "__main__":
    main()
