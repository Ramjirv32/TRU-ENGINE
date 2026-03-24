import subprocess
import json
import time
import os
import re
import concurrent.futures
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

API_KEY = "33115710653096606c6bef7b3e4221d0509fa024d616153e064891a2bbe63b7e"

COLLEGES = [
    {"name": "Psg College of Technology", "country": "India", "location": "Coimbatore"},
]

QUERIES = {
    "basic_info": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified institutional data for the current academic year or the latest available year if the current is not published. Return only valid JSON with the exact fields: college_name, short_name, established, institution_type, country, location, website, about, summary, rankings (nirf_latest, nirf_previous, qs_world, national_rank, state_rank, guessed_data), student_statistics (total_enrollment, ug_students, pg_students, phd_students, annual_intake, male_percent, female_percent, total_ug_courses, total_pg_courses, total_phd_courses, guessed_data), faculty_staff (total_faculty, student_faculty_ratio, phd_faculty_percent, guessed_data), student_history (student_count_comparison_last_3_years with latest_year, previous_year, year_before_previous, international_students, guessed_data, categorywise_student_comparison_last_3_years: [{\"year\": \"latest_year\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}, {\"year\": \"previous_year\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}, {\"year\": \"year_before_previous\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}]), accreditations (body, grade, year), affiliations, recognition, campus_area, contact_info (phone, email, address), and sources_verified (array of URLs or document names). If a number is not known, use -1; if a string is not known, use N/A. Do not add any extra text, only JSON.",
    "programs": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide a COMPREHENSIVE list of ALL officially offered UG, PG, and PhD programs and departments as of the current academic year. Use only official college website, latest NIRF, AICTE, or UGC‑recognized sources. Do not invent any program. Return only valid JSON with keys: ug_programs (complete list of ALL undergraduate programs with specializations), pg_programs (complete list of ALL postgraduate programs with specializations), phd_programs (complete list of ALL doctoral programs with specializations), departments (complete list of ALL academic departments). If a level has no programs, use an empty array []. Include a \"sources_verified\" array with URLs or document names. IMPORTANT: List EVERY single program offered, including all branches, specializations, and interdisciplinary programs. Do not group or summarize programs - list each one individually.",
    "placements": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest verified placement data for the past three years if available. Use only official placement reports, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"latest_year\", \"sources\": [\"source URL or document name\"], \"placements\": {\"year\": \"latest_year\", \"highest_package\": real_number, \"average_package\": real_number, \"median_package\": real_number, \"package_currency\": \"LPA\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges, \"placement_rate_percent\": real_percent, \"total_students_placed\": integer, \"total_companies_visited\": integer, \"graduate_outcomes_note\": \"factual note\"}, \"placement_comparison_last_3_years\": [{\"year\":\"latest_year\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":\"previous_year\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":\"year_before_previous\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}], \"gender_based_placement_last_3_years\": [{\"year\":\"latest_year\", \"male_placed\": integer, \"female_placed\": integer, \"male_percent\": real_percent, \"female_percent\": real_percent}], \"sector_wise_placement_last_3_years\": [{\"year\":\"latest_year\", \"sector\": \"sector name\", \"companies\": [\"company names\"], \"percent\": real_percent}], \"top_recruiters\": [\"company names\"], \"placement_highlights\": \"2-3 sentence factual summary\"}. IMPORTANT: Always include currency_type field for all monetary values. If exact numbers are unavailable, use conservative estimates and set \"guessed_data\": true. Do not inflate numbers; for Indian Tier‑2 private engineering colleges, average package is usually 5–8 LPA. Do not return any extra text, only JSON.",
    "fees": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified fee structure for the current academic year. Use only official college website, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"latest_year\", \"sources\": [\"source URL or document name\"], \"fees\": {\"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"hostel_per_year\": real_number}, \"fees_by_year\": [{\"year\": \"latest_year\", \"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"hostel_per_year\": real_number}], \"fees_note\": \"2-3 sentence factual summary\", \"scholarships_detail\": [{\"name\": \"scholarship name\", \"amount\": real_number, \"currency_type\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges, \"eligibility\": \"eligibility criteria\", \"provider\": \"provider name\"}]}. IMPORTANT: Always include currency_type field for all monetary values. If exact numbers are unavailable, use conservative estimates and set \"guessed_data\": true. Do not inflate numbers. Do not return any extra text, only JSON.",
    "infrastructure": "For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified infrastructure details and available scholarships. Use only official college website, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"sources_verified\": [\"source URL or document name\"], \"infrastructure\": [{\"facility\": \"facility name\", \"details\": \"facility details\"}], \"hostel_details\": {\"available\": boolean, \"total_capacity\": integer, \"type\": \"hostel type\"}, \"library_details\": {\"total_books\": integer, \"journals\": integer, \"e_resources\": integer, \"area_sqft\": real_number}, \"transport_details\": {\"buses\": integer, \"routes\": integer}, \"scholarships\": [{\"name\": \"scholarship name\", \"amount\": real_number_or_NA, \"currency_type\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges, \"eligibility\": \"eligibility criteria\", \"provider\": \"provider name\", \"type\": \"merit/need/specific\", \"application_deadline\": \"date_or_NA\"}]}. IMPORTANT: Always include currency_type field for all monetary amounts. List ALL available scholarships including merit-based, need-based, government, private, and international student scholarships. Do not return any extra text, only JSON."
}

# ============================================================================
# MONGODB SCHEMA - SINGLE SOURCE OF TRUTH
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
            "accreditations": [],  # Always array
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
    if value is None or value == "" or value == "N/A":
        return default
    if isinstance(value, bool):
        return int(value)
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def to_float(value: Any, default: float = -1.0) -> float:
    if value is None or value == "" or value == "N/A":
        return default
    if isinstance(value, bool):
        return float(value)
    try:
        return round(float(str(value)), 2)
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

# ============================================================================
# CURL & EXTRACTION FUNCTIONS
# ============================================================================

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
    
    # Strip code block markers
    text = re.sub(r'```(?:json)?', '', md_text).strip()
    
    # Find JSON boundaries
    start = text.find('{')
    end = text.rfind('}')
    
    if start == -1 or end == -1:
        try:
            return json.loads(text)
        except:
            return {"raw_output": md_text, "error": "No JSON braces found"}
            
    json_str = text[start:end+1]
    
    # Clean LLM formatting issues
    json_str = json_str.replace('\\_', '_').replace('\\-', '-')
    
    # Try parsing
    try:
        return json.loads(json_str)
    except Exception as first_error:
        try:
            return json.loads(json_str, strict=False)
        except Exception as second_error:
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
        # Log raw response for debugging
        print(f"RAW RESPONSE: {response_text[:500]}...")
        return None, f"JSON decode error: {str(e)}"

# ============================================================================
# MAIN SCRAPER
# ============================================================================

def main():
    output_dir = "/home/ramji/Videos/scap/college_scraper"
    os.makedirs(output_dir, exist_ok=True)
    
    total_start_time = time.time()
    
    # Prepare all tasks
    all_tasks = []
    for college in COLLEGES:
        for query_type, query in QUERIES.items():
            cmd = build_curl_command(query, college)
            all_tasks.append({
                "college": college["name"],
                "country": college["country"],
                "query_type": query_type,
                "cmd": cmd
            })
    
    print(f"🚀 Running {len(all_tasks)} parallel curl requests...")
    print(f"{'='*70}")
    
    # Store results by college
    colleges_data = {}
    
    # Execute in parallel
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
                
                # Parse LLM output
                raw_data = extract_structured_json(markdown) if markdown else {"error": error}
                
                # Store raw data for later normalization
                if college_name not in colleges_data:
                    colleges_data[college_name] = {"_metadata": {"total_time": 0, "errors": {}, "college_name": college_name, "country": task["country"]}}
                
                colleges_data[college_name][query_type] = raw_data
                
                # Update metadata
                colleges_data[college_name]["_metadata"]["total_time"] += elapsed
                if error or "error" in raw_data:
                    colleges_data[college_name]["_metadata"]["errors"][query_type] = error or raw_data.get("error")
                
                print(f"✓ {college_name} - {query_type}: {elapsed:.2f}s")
                
            except Exception as e:
                print(f"✗ {college_name} - {query_type}: Error - {str(e)}")
                if college_name not in colleges_data:
                    colleges_data[college_name] = get_default_schema()
                colleges_data[college_name]["_metadata"]["errors"][query_type] = str(e)
    
    total_end_time = time.time()
    total_time_taken = round(total_end_time - total_start_time, 2)
    
    # ========================================================================
    # SAVE INDIVIDUAL FILES (MONGODB READY)
    # ========================================================================
    
    print(f"\n{'='*70}")
    print("💾 SAVING NORMALIZED JSON FILES...")
    print(f"{'='*70}\n")
    
    for college, raw_data in colleges_data.items():
        # Normalize the entire college record
        normalized_data = normalize_college(raw_data)
        
        # Sanitize filename
        safe_name = re.sub(r'[^\w\s-]', '', college).strip().replace(' ', '_')
        output_file = os.path.join(output_dir, f"{safe_name}_normalized.json")
        
        # Save
        with open(output_file, "w") as f:
            json.dump(normalized_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ {college}")
        print(f"   └─ Saved: {output_file}")
        print(f"   └─ Time: {normalized_data['_metadata']['total_time']:.2f}s")
        print(f"   └─ Errors: {len(normalized_data['_metadata']['errors'])}")
        print(f"   └─ Warnings: {len(normalized_data['_metadata']['validation_warnings'])}")
        print()
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    
    print(f"{'='*70}")
    print(f"✨ COMPLETE! Total time: {total_time_taken}s")
    print(f"{'='*70}")
    print(f"📊 Colleges processed: {len(colleges_data)}")
    print(f"📁 Output directory: {output_dir}")
    print(f"🗄️  Files are MongoDB-ready with normalized schema")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()