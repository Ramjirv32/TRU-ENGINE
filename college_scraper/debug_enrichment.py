#!/usr/bin/env python3
"""Debug script to test enrichment and completeness tracking"""

import json
import sys

# Load raw JSON
with open("Lomonosov_Moscow_State_University.json") as f:
    raw_data = json.load(f)

print("=" * 80)
print("STEP 1: Check raw programs section")
print("=" * 80)
programs_raw = raw_data.get("programs", {})
print(f"Raw programs: {json.dumps(programs_raw, indent=2)}")
print(f"Has 'error' key: {'error' in programs_raw}")

print("\n" + "=" * 80)
print("STEP 2: Check basic_info student_statistics")
print("=" * 80)
basic_info = raw_data.get("basic_info", {})
ss = basic_info.get("student_statistics", {})
print(f"Total UG courses: {ss.get('total_ug_courses')}")
print(f"Total PG courses: {ss.get('total_pg_courses')}")
print(f"Total PhD courses: {ss.get('total_phd_courses')}")
print(f"Total departments: {ss.get('total_departments')}")

print("\n" + "=" * 80)
print("STEP 3: Simulate enrichment")
print("=" * 80)
if "error" in programs_raw and basic_info:
    print("✓ Programs have error and basic_info exists - enrichment should run")
    programs_raw["department_count"] = ss.get("total_departments", -1)
    programs_raw["ug_count"] = ss.get("total_ug_courses", -1)
    programs_raw["pg_count"] = ss.get("total_pg_courses", -1)
    programs_raw["phd_count"] = ss.get("total_phd_courses", -1)
    print(f"Enriched programs: {json.dumps(programs_raw, indent=2)}")
else:
    print(f"✗ Enrichment should NOT run - error={('error' in programs_raw)}, has basic_info={bool(basic_info)}")

print("\n" + "=" * 80)
print("STEP 4: Check normalized version")
print("=" * 80)
with open("Lomonosov_Moscow_State_University_normalized.json") as f:
    normalized = json.load(f)
programs_norm = normalized.get("programs", {})
print(f"Normalized programs keys: {list(programs_norm.keys())}")
print(f"Has 'completeness': {'completeness' in programs_norm}")
if 'completeness' in programs_norm:
    print(f"Completeness: {json.dumps(programs_norm['completeness'], indent=2)}")
