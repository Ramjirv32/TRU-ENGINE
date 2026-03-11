#!/usr/bin/env python3
"""
validate_sections.py  —  Audit-section-by-section Gemini validator.

Usage:
    python validate_sections.py <structured_json> <audit_json> [section1 section2 ...]

If no sections given, runs: faculty_students  placements

Each logical group sends only its relevant audit snippets to Gemini,
gets back a corrected JSON subset, and patches the structured file in-place.
"""

import json, os, sys, re, time, concurrent.futures
import google.genai as genai
from google.genai import types

GEMINI_API_KEY = "AIzaSyBi8uFkM7rhjtA56DfQGdFpGqFl5hbQni8"
GEMINI_MODEL   = "gemini-2.5-flash"
gemini_client  = genai.Client(api_key=GEMINI_API_KEY)

# ── section configs ────────────────────────────────────────────────────────────
SECTIONS = {
    "faculty_students": {
        "audit_sections": ["Faculty_Staff", "Student_Statistics",
                           "Student_Gender_Ratio", "International_Students"],
        "struct_keys": [
            "faculty_staff", "student_statistics", "student_gender_ratio",
            "student_count_comparison_last_3_years", "international_students"
        ],
        "prompt": """You are a college data validator.
Below are RAW SCRAPED SNIPPETS from the college website (audit data) and the CURRENT extracted JSON for faculty & student statistics.

Your job:
1. Read the audit snippets carefully.
2. Compare against the CURRENT JSON values.
3. Fix any wrong/missing values using the audit data.
4. If something is still missing after checking audit, use your own knowledge for this specific college.
5. Return ONLY a corrected JSON object with these exact keys:
   faculty_staff, student_statistics, student_gender_ratio,
   student_count_comparison_last_3_years, international_students

Schema reminders:
- faculty_staff: {total_faculty, phd_faculty_count, phd_faculty_percent, student_faculty_ratio, professors, associate_professors, assistant_professors}
- student_statistics: {total_enrollment, ug_students, pg_students, phd_students, annual_intake}
- student_gender_ratio: {total_male, total_female, male_percent, female_percent}
- student_count_comparison_last_3_years: [{year, total_enrolled, ug, pg, phd}] for 2023,2024,2025
- international_students: {total_count, countries_represented, nri_students}

Use "not_available" for genuinely unknown values. Return ONLY valid JSON, no markdown fences."""
    },
    "placements": {
        "audit_sections": ["Placements_General", "Placement_Yearly_Counts",
                           "Placement_Gender_Stats", "Sector_Wise_Placements"],
        "struct_keys": [
            "placements", "placement_comparison_last_3_years",
            "gender_based_placement_last_3_years", "sector_wise_placement_last_3_years"
        ],
        "prompt": """You are a college placement data validator.
Below are RAW SCRAPED SNIPPETS from the college website (audit data) and the CURRENT extracted JSON for placement statistics.

Your job:
1. Read the audit snippets carefully.
2. Compare against the CURRENT JSON values.
3. Fix any wrong/missing values using the audit data.
4. If something is still missing after checking audit, use your own knowledge for this specific college.
5. Return ONLY a corrected JSON object with these exact keys:
   placements, placement_comparison_last_3_years,
   gender_based_placement_last_3_years, sector_wise_placement_last_3_years

Schema reminders:
- placements: {year, highest_package(float LPA), average_package(float LPA), median_package, package_currency:"LPA", placement_rate_percent(float), total_students_placed(int), total_companies_visited(int)}
- placement_comparison_last_3_years: [{year, highest_package, average_package, median_package, package_currency, students_placed, placement_rate_percent}]  for 2023,2024,2025
- gender_based_placement_last_3_years: [{year, male_placed, female_placed, male_percent, female_percent, package_currency}] for 2023,2024,2025
- sector_wise_placement_last_3_years: [{year, sector, companies:[list], percent}]

Do NOT inflate numbers. Typical private engineering: avg 3-6 LPA, highest 10-25 LPA.
Use "not_available" for genuinely unknown values. Return ONLY valid JSON, no markdown fences."""
    },
    "gender_placements": {
        "audit_sections": ["Placement_Gender_Stats", "Placements_General",
                           "Student_Gender_Ratio", "Student_Statistics"],
        "struct_keys": ["gender_based_placement_last_3_years", "student_count_comparison_last_3_years"],
        "prompt": """You are a college data validator specialising in gender statistics and student enrollment.
Below are RAW SCRAPED SNIPPETS from the college website and the CURRENT extracted JSON.

Your job:
1. Check audit snippets for any gender-wise placement numbers or enrollment counts.
2. Fix any values you find from audit data.
3. For fields still "not_available" after audit check — use YOUR OWN KNOWLEDGE about this specific college
   to provide REALISTIC APPROXIMATIONS. DO NOT leave everything as not_available.
   - For gender_based_placement: use known male/female ratio for this college type/region.
     Typical private engineering in Tamil Nadu: ~55-65% male, ~35-45% female.
     Compute male_placed and female_placed from total_students_placed if known.
   - For student_count_comparison: use total enrollment trend you know for this college.
     Fill ug/pg/phd from known program counts if total is known.
4. Add a "_note": "approximate" field to any value that is estimated, NOT from audit.

Return ONLY a JSON object with exactly these two keys:
  gender_based_placement_last_3_years, student_count_comparison_last_3_years

Schemas:
- gender_based_placement_last_3_years: [{year(int), male_placed(int or "not_available"), female_placed(int or "not_available"), male_percent(float or "not_available"), female_percent(float or "not_available"), package_currency:"LPA"}]  — entries for 2023, 2024, 2025
- student_count_comparison_last_3_years: [{year(str), total_enrolled(int or "not_available"), ug(int or "not_available"), pg(int or "not_available"), phd(int or "not_available")}] — entries for "2023","2024","2025"

Return ONLY valid JSON, no markdown fences, no commentary."""
    },
}

# ── helpers ────────────────────────────────────────────────────────────────────
def get_audit_snippets(audit_sections_data: list, names: list) -> str:
    parts = []
    for s in audit_sections_data:
        if s.get("section") not in names:
            continue
        sec_text = f"\n=== {s['section']} ===\n"
        for src in s.get("sources", []):
            for snip in src.get("snippets", []):
                snip = re.sub(r'https?://\S+', '', snip)
                snip = re.sub(r'\s{2,}', ' ', snip)
                snip = snip.strip()
                if snip:
                    sec_text += snip + "\n"
        parts.append(sec_text)
    return "\n".join(parts)[:8000]  # keep under token budget


def call_gemini(prompt: str, label: str):
    t0 = time.time()
    for attempt in range(3):
        try:
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You validate structured college data. Return ONLY valid JSON, no markdown fences.",
                    temperature=0,
                    max_output_tokens=8192,
                ),
            )
            text = resp.text.strip()
            # strip markdown fences
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            # extract from first { to last }
            start = text.find('{')
            end   = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]
            # repair: trailing commas, control chars
            text = re.sub(r',\s*([}\]])', r'\1', text)
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)
            # try parse; if fails, balance braces and retry once
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                open_b = text.count('{') - text.count('}')
                open_s = text.count('[') - text.count(']')
                text += '}' * max(0, open_b) + ']' * max(0, open_s)
                result = json.loads(text)
            elapsed = round(time.time() - t0, 2)
            print(f"  ✓ [{label}] done in {elapsed}s")
            return result
        except json.JSONDecodeError as e:
            if attempt < 2:
                print(f"  ⚠  [{label}] JSON parse error attempt {attempt+1}, retrying…")
                time.sleep(1)
                continue
            print(f"  ✗ [{label}] failed: {e}\n     RAW tail: {text[-300:]}")
            return None
        except Exception as e:
            print(f"  ✗ [{label}] error: {e}")
            return None
    return None


def run_section(sec_name, cfg, structured, audit_sections_data, college_name):
    snippets = get_audit_snippets(audit_sections_data, cfg["audit_sections"])
    current_subset = {k: structured.get(k, "not_available") for k in cfg["struct_keys"]}

    full_prompt = (
        f"{cfg['prompt']}\n\n"
        f"COLLEGE: {college_name}\n\n"
        f"CURRENT JSON:\n{json.dumps(current_subset, indent=2)}\n\n"
        f"AUDIT SNIPPETS:\n{snippets}"
    )
    print(f"  ↳ Sending '{sec_name}' to Gemini…")
    return sec_name, call_gemini(full_prompt, sec_name)


# ── main ────────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 3:
        print("Usage: python validate_sections.py <structured.json> <audit.json> [sections...]")
        sys.exit(1)

    struct_file = sys.argv[1]
    audit_file  = sys.argv[2]
    run_sections = sys.argv[3:] if len(sys.argv) > 3 else list(SECTIONS.keys())

    with open(struct_file) as f:  structured = json.load(f)
    with open(audit_file)  as f:  audit = json.load(f)
    audit_sections_data = audit.get("sections", [])
    college_name = structured.get("college_name", "Unknown College")

    # backup
    backup = struct_file.replace(".json", ".bak.json")
    with open(backup, "w") as f: json.dump(structured, f, indent=2, ensure_ascii=False)
    print(f"📦 Backup: {backup}")
    print(f"🚀 Running sections in parallel: {run_sections}\n")

    # parallel execution
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(run_sections)) as ex:
        futures = {
            ex.submit(run_section, sn, SECTIONS[sn], structured, audit_sections_data, college_name): sn
            for sn in run_sections if sn in SECTIONS
        }
        for fut in concurrent.futures.as_completed(futures):
            sec_name, result = fut.result()
            results[sec_name] = result

    # patch structured JSON
    corrections = 0
    for sec_name, result in results.items():
        if result is None:
            print(f"  ⚠  No result for '{sec_name}', skipping.")
            continue
        for key, new_val in result.items():
            old_val = structured.get(key)
            if new_val != old_val:
                print(f"  ✏  {key}: changed")
                structured[key] = new_val
                corrections += 1

    with open(struct_file, "w") as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done — {corrections} fields updated → {struct_file}")


if __name__ == "__main__":
    main()
