"""
gemini_processor.py  — process a college audit JSON using Gemini 2.5 Flash
Usage:  python college_scraper/gemini_processor.py <audit_json>

All 6 batches run in parallel via ThreadPoolExecutor.
"""

import json
import os
import sys
import re
import html
import time
import concurrent.futures

import google.genai as genai
from google.genai import types

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GEMINI_API_KEY = "AIzaSyDSHDs1VGDJwJ3G1bJrueLBB6M55KyVjhE"
client_gemini = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compress_snippet(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r'\{"@(type|graph|context)[^}]{0,2000}\}', '', text)
    text = re.sub(r'!\[Image[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def build_context(sections: list, names: list, char_limit: int = 6000) -> str:
    section_texts = {}
    for s in sections:
        name = s.get("section")
        if name not in names:
            continue
        parts = []
        for src in s.get("sources", []):
            for snip in src.get("snippets", []):
                c = compress_snippet(snip)
                if c:
                    parts.append(c)
        if parts:
            section_texts[name] = "\n".join(parts)

    n = len(section_texts)
    if n == 0:
        return ""
    budget = max(800, char_limit // n)
    ctx = ""
    for name in names:
        if name in section_texts:
            ctx += f"\n[{name}]\n{section_texts[name][:budget]}\n"
    return ctx


def _repair_json(text: str) -> str:
    text = re.sub(r':\s*"?~([0-9][0-9,.]*)\"?', lambda m: ': ' + m.group(1).replace(',', ''), text)
    text = re.sub(r'"~([^"]+)"', r'"\1"', text)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text


def _extract_url(sections: list) -> str:
    for s in sections:
        if s.get("section") == "Identity":
            for src in s.get("sources", []):
                url = src.get("url", "")
                if url.startswith("http"):
                    return url
    for s in sections:
        for src in s.get("sources", []):
            url = src.get("url", "")
            if url.startswith("http"):
                return url
    return ""


def _extract_about(sections: list) -> str:
    for s in sections:
        if s.get("section") == "About":
            for src in s.get("sources", []):
                for snip in src.get("snippets", []):
                    clean = html.unescape(snip)
                    if clean.strip().startswith("{"):
                        continue
                    clean = re.sub(r'https?://\S+', '', clean).strip()
                    if len(clean) > 100:
                        return clean[:1500]
    return ""


# ---------------------------------------------------------------------------
# Batch prompts (identical to audit_processor.py)
# ---------------------------------------------------------------------------
_RULES = """
IMPORTANT RULES:
1. Return ONLY valid parseable JSON — no markdown fences, no commentary.
2. NUMBER fields: plain number (int or float).
3. STRING fields: use "~value" prefix if estimating.
4. Never leave a field null if you can reasonably estimate it.
5. Fill ALL fields."""

BATCH_A1 = """Extract rankings. Return ONLY valid JSON. Never use a year as a rank value.
""" + _RULES + """
{"rankings":{"nirf_2025":"","nirf_2024":"","nirf_2023":"","qs_world":"","qs_asia_2025":"","the_world_2024":"","india_rank":"","us_news":""},"rankings_history":[{"year":"","ranking_body":"","rank":""}],"global_ranking":{"qs_world":"","the_world":"","us_news_global":""}}"""

BATCH_A2 = """Extract faculty and student stats. Return ONLY valid JSON. male_percent/female_percent whole numbers (e.g. 74). student_faculty_ratio format "X:1".
""" + _RULES + """
{"faculty_staff":{"total_faculty":null,"phd_faculty_count":null,"student_faculty_ratio":"","professors":null,"associate_professors":null,"assistant_professors":null},"student_statistics":{"total_enrollment":null,"ug_students":null,"pg_students":null,"phd_students":null,"annual_intake":null},"student_gender_ratio":{"total_male":null,"total_female":null,"male_percent":null,"female_percent":null},"ratio_based_indicators":{"student_faculty_ratio":"","ug_pg_ratio":"","male_female_ratio":"","phd_percent":null,"ug_percent":null,"pg_percent":null},"international_students":{"total_count":null,"countries_represented":null,"nri_students":null},"student_count_comparison_last_3_years":[{"year":"","total_enrolled":null,"ug":null,"pg":null,"phd":null}]}"""

BATCH_B = """Extract placement data for the OVERALL INSTITUTE (not a single department). Return ONLY valid JSON. Package values in LPA. Never use a year as a package value. placement_rate_percent is 0-100.
""" + _RULES + """
{"placements":{"year":"","highest_package_lpa":null,"average_package_lpa":null,"median_package_lpa":null,"placement_rate_percent":null,"total_students_placed":null,"total_companies_visited":null},"placement_comparison_last_3_years":[{"year":"","highest_package_lpa":null,"average_package_lpa":null,"students_placed":null,"placement_rate_percent":null}],"gender_based_placement_last_3_years":[{"year":"","male_placed":null,"female_placed":null}],"sector_wise_placement_last_3_years":[{"year":"","sector":"","companies":[],"percent":null}]}"""

BATCH_C1 = """Extract all academic programs. Return ONLY valid JSON. Each program must be an object with name, duration (e.g. "4 years"), seats (int or null), fees_per_year (number or null). No empty entries.
""" + _RULES + """
{"ug_programs":[{"name":"","duration":"","seats":null,"fees_per_year":null}],"pg_programs":[{"name":"","duration":"","seats":null,"fees_per_year":null}],"phd_programs":[{"name":"","duration":"","seats":null,"fees_per_year":null}]}"""

BATCH_C2A = """Extract college identity and fees. Return ONLY valid JSON.
""" + _RULES + """
{"college_name":"","short_name":"","location":"","country":"","established":null,"institution_type":"","campus_area":"","data_confidence_score":null,"fees":{"UG":{"per_year":null,"total_course":null},"PG":{"per_year":null,"total_course":null},"hostel_per_year":null}}"""

BATCH_C2B = """Extract scholarships, departments and infrastructure. Return ONLY valid JSON. Scholarships must include name, amount and eligibility. Infrastructure as objects with facility name and details.
""" + _RULES + """
{"departments":[],"scholarships":[{"name":"","amount":"","eligibility":""}],"infrastructure":[{"facility":"","details":""}]}"""

BATCHES = [
    ("A1",  BATCH_A1,  ["Rankings", "About", "Identity"]),
    ("A2",  BATCH_A2,  ["Faculty_Staff", "Student_Statistics", "Student_Gender_Ratio", "International_Students"]),
    ("B",   BATCH_B,   ["Placements_General", "Placement_Yearly_Counts", "Placement_Gender_Stats", "Sector_Wise_Placements"]),
    ("C1",  BATCH_C1,  ["UG_Programs", "PG_Programs"]),
    ("C2A", BATCH_C2A, ["Identity", "Fees"]),
    ("C2B", BATCH_C2B, ["About", "Scholarships", "Infrastructure"]),
]

# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------

def call_gemini(system_prompt: str, context: str, label: str) -> dict | None:
    full_prompt = system_prompt + "\n\n=== SCRAPED CONTEXT ===\n" + context
    t0 = time.time()
    try:
        print(f"  ↳ Gemini call '{label}'…")
        resp = client_gemini.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction="You extract structured college data from scraped web content. Return ONLY valid JSON, no markdown.",
                temperature=0,
                max_output_tokens=4096,
            ),
        )
        elapsed = round(time.time() - t0, 2)
        text = resp.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            result = json.loads(_repair_json(text))
        print(f"     ✓ '{label}' done in {elapsed}s")
        return result, elapsed
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"  ✗ Gemini error '{label}' ({elapsed}s): {e}")
        return None, elapsed


def run_batch(args):
    name, prompt, sec_names, sections = args
    ctx = build_context(sections, sec_names)
    result, elapsed = call_gemini(prompt, ctx, name)
    return name, result, elapsed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_audit_with_gemini(filename: str):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    with open(filename) as f:
        audit = json.load(f)

    college_name = audit.get("college_name", "Unknown")
    sections     = audit.get("sections", [])
    print(f"\n🚀 Processing with Gemini 2.5 Flash: {college_name}")
    print(f"   Sections: {[s.get('section') for s in sections]}\n")

    wall_start = time.time()

    # Run all 6 batches in PARALLEL — Gemini has no strict TPM on free tier
    batch_args = [(name, prompt, secs, sections) for name, prompt, secs in BATCHES]
    results = {}
    batch_times = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(run_batch, arg): arg[0] for arg in batch_args}
        for fut in concurrent.futures.as_completed(futures):
            name, result, elapsed = fut.result()
            results[name] = result
            batch_times[name] = elapsed

    wall_total = round(time.time() - wall_start, 2)
    groq_sum   = round(sum(batch_times.values()), 2)

    # Merge (priority: C2A → C2B → C1 → B → A2 → A1)
    merged = {}
    for key in ["C2A", "C2B", "C1", "B", "A2", "A1"]:
        r = results.get(key)
        if r:
            merged.update(r)

    # Inject URL and about directly from audit (no LLM needed)
    merged["source_url"] = _extract_url(sections)
    if not merged.get("about"):
        merged["about"] = _extract_about(sections)
    if not merged.get("summary"):
        merged["summary"] = merged.get("about", "")[:300]

    # Defaults
    defaults = {
        "college_name": college_name, "short_name": "", "location": "", "country": "",
        "established": None, "institution_type": "", "campus_area": "", "about": "",
        "summary": "", "source_url": "", "departments": [],
        "ug_programs": [], "pg_programs": [], "phd_programs": [],
        "fees": {}, "scholarships": [], "infrastructure": [],
        "faculty_staff": {}, "student_statistics": {}, "student_gender_ratio": {},
        "student_count_comparison_last_3_years": [], "ratio_based_indicators": {},
        "international_students": {}, "placements": {},
        "placement_comparison_last_3_years": [],
        "gender_based_placement_last_3_years": [],
        "sector_wise_placement_last_3_years": [],
        "rankings": {}, "rankings_history": [], "global_ranking": {},
        "sources": [], "validation_report": "", "data_confidence_score": None,
    }
    for k, v in defaults.items():
        merged.setdefault(k, v)

    merged["last_updated"] = time.strftime("%Y-%m-%d")
    merged["pipeline_timing"] = {
        "batch_times_seconds": batch_times,
        "wall_clock_seconds": wall_total,
        "gemini_serial_sum_seconds": groq_sum,
        "num_batches": 6,
        "model": MODEL_NAME,
        "mode": "parallel",
    }

    print(f"\n⏱  Timing (wall-clock = {wall_total}s, all parallel):")
    for name in ["A1","A2","B","C1","C2A","C2B"]:
        t = batch_times.get(name, "—")
        ok = "✓" if results.get(name) else "✗"
        print(f"   Batch {name}: {t}s  {ok}")
    print(f"   Gemini serial sum: {groq_sum}s")

    out_path = os.path.join(
        os.path.dirname(os.path.abspath(filename)),
        os.path.basename(filename).replace("_audit.json", "_gemini_structured.json")
    )
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved → {out_path}")
    return merged


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python college_scraper/gemini_processor.py <audit_json>")
        sys.exit(1)
    process_audit_with_gemini(sys.argv[1])
