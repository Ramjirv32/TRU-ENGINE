"""
ans_audit.py — Direct LLM audit using Brave Search Answer API.

Uses micro-queries (3-6 fields each) because Brave's Answer API returns
live web-search grounded answers but with a small per-response output window.
No scraping / no audit JSON needed — all data comes from Brave's live search.

Usage:
    python ans_audit.py "IIT Madras"
    python ans_audit.py "Udayana University"

Output saved as: 2nd_test_<college_slug>.json  (same directory)
"""

import asyncio
import json
import os
import re
import sys
import time

from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# Brave API client
# ---------------------------------------------------------------------------

BRAVE_API_KEY = "BSA0I82aPo-iuQy0y3rzv11qa4QkyIK"

brave_client = AsyncOpenAI(
    api_key=BRAVE_API_KEY,
    base_url="https://api.search.brave.com/res/v1",
)

# ---------------------------------------------------------------------------
# Import finalize_output + helpers from audit_processor
# ---------------------------------------------------------------------------
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from audit_processor import (
    _repair_json,
    finalize_output,
)

# ---------------------------------------------------------------------------
# Core Brave call — single message, strip <usage> tag, parse JSON
# ---------------------------------------------------------------------------

def _close_truncated_json(text: str) -> str:
    """Attempt to close a truncated JSON string by counting brackets."""
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()
    # Close any open strings first
    if in_string:
        text += '"'
    # Close open brackets in reverse order
    text = text + "".join(reversed(stack))
    return text


async def ask(question: str, label: str = "") -> dict | None:
    """Ask Brave a focused question; expect JSON back. Returns parsed dict or None."""
    for attempt in range(2):
        try:
            full_text = ""
            stream = await brave_client.chat.completions.create(
                messages=[{"role": "user", "content": question}],
                model="brave",
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_text += delta

            # Strip trailing <usage>...</usage> metadata that Brave appends
            text = re.sub(r"<usage>.*", "", full_text, flags=re.DOTALL).strip()

            # Strip markdown code fences if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            # Try to extract JSON object/array even if wrapped in prose
            m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
            if m:
                text = m.group(1)

            # Try progressively more aggressive repairs
            for candidate in [text, _repair_json(text), _close_truncated_json(text),
                               _repair_json(_close_truncated_json(text))]:
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

            print(f"  ⚠  JSON parse fail [{label}]: {text[:200]}")
            if attempt < 1:
                await asyncio.sleep(2)
            return None

        except Exception as e:
            print(f"  ✗ Brave error [{label}]: {e}")
            if attempt < 1:
                await asyncio.sleep(3)
    return None


def _q(college: str, what: str, fields: str) -> str:
    """Build a compact JSON-only question for Brave."""
    return (
        f"{college} — {what}. "
        f"Answer as compact JSON ONLY (no explanation, no markdown): "
        f"{fields}"
    )


# ---------------------------------------------------------------------------
# Micro-query groups
# ---------------------------------------------------------------------------

async def q_identity(c: str) -> dict:
    return await ask(
        _q(c, "full official name, common abbreviation, city+state location, country, year established, public or private, campus area in acres",
           '{"college_name":"","short_name":"","location":"","country":"","established":0,"institution_type":"","campus_area":""}'),
        "identity"
    ) or {}

async def q_about(c: str) -> dict:
    return await ask(
        _q(c, "2-sentence history and academic strengths summary",
           '{"about":""}'),
        "about"
    ) or {}

async def q_rankings(c: str) -> dict:
    return await ask(
        _q(c, "NIRF 2025 rank, NIRF 2024 rank, QS World 2025 rank, QS Asia 2025 rank, THE World 2024 rank, national rank in home country",
           '{"nirf_2025":"","nirf_2024":"","qs_world":"","qs_asia_2025":"","the_world_2024":"","national_rank":""}'),
        "rankings"
    ) or {}

async def q_global_ranking(c: str) -> dict:
    return await ask(
        _q(c, "QS World rank, THE World rank, US News Global rank (numbers only or range like 601-650)",
           '{"qs_world":"","the_world":"","us_news_global":""}'),
        "global_ranking"
    ) or {}

async def q_faculty(c: str) -> dict:
    return await ask(
        _q(c, "total faculty count, number with PhD, student-to-faculty ratio, number of professors, associate professors, assistant professors",
           '{"total_faculty":0,"phd_faculty_count":0,"student_faculty_ratio":"","professors":0,"associate_professors":0,"assistant_professors":0}'),
        "faculty"
    ) or {}

async def q_students(c: str) -> dict:
    return await ask(
        _q(c, "total enrollment, UG students, PG students, PhD students, annual intake, male percentage, female percentage",
           '{"total_enrollment":0,"ug_students":0,"pg_students":0,"phd_students":0,"annual_intake":0,"male_percent":0,"female_percent":0}'),
        "students"
    ) or {}

async def q_international(c: str) -> dict:
    return await ask(
        _q(c, "international students count, countries represented, NRI students",
           '{"total_count":0,"countries_represented":0,"nri_students":0}'),
        "international"
    ) or {}

async def q_departments(c: str) -> dict:
    return await ask(
        _q(c, "list all departments or schools/faculties",
           '{"departments":[]}'),
        "departments"
    ) or {}

async def q_stats_snapshot(c: str) -> dict:
    """Single-call snapshot of the most important student & placement stats."""
    return await ask(
        _q(c,
           "current year (2025) key stats: total students enrolled, UG students, PG students, PhD students, "
           "annual intake, total male students count, total female students count, male percent, female percent, "
           "international students count, total students placed, placement rate percent, average package (number), "
           "package currency (LPA for India / USD,IDR etc otherwise), highest package (number)",
           '{"total_enrollment":0,"ug_students":0,"pg_students":0,"phd_students":0,"annual_intake":0,'
           '"total_male":0,"total_female":0,"male_percent":0,"female_percent":0,'
           '"international_students":0,"total_placed":0,"placement_rate_percent":0,'
           '"average_package":0,"highest_package":0,"package_currency":""}'),
        "stats_snapshot"
    ) or {}

async def q_ug_programs(c: str) -> dict:
    return await ask(
        _q(c, "list all UG programs with full specialization name, duration, seats, and approximate total course fee in local currency (number only)",
           '{"ug_programs":[{"name":"","duration":"","seats":0,"fees_total_local":0}]}'),
        "ug_programs"
    ) or {}

async def q_pg_programs(c: str) -> dict:
    return await ask(
        _q(c, "list top 10 most popular PG programs (Masters/MBA/M.Tech etc.) with full specialization name, duration, seats, approximate total course fee in local currency (number only)",
           '{"pg_programs":[{"name":"","duration":"","seats":0,"fees_total_local":0}]}'),
        "pg_programs"
    ) or {}

async def q_phd_programs(c: str) -> dict:
    return await ask(
        _q(c, "list all PhD programs with department name, duration, seats",
           '{"phd_programs":[{"name":"","duration":"","seats":0}]}'),
        "phd_programs"
    ) or {}

async def q_fees(c: str) -> dict:
    return await ask(
        _q(c, "UG per-year fee, UG total course fee, PG per-year fee, PG total course fee, hostel per-year cost — all as plain numbers in local currency",
           '{"fees":{"UG":{"per_year":0,"total_course":0},"PG":{"per_year":0,"total_course":0},"hostel_per_year":0}}'),
        "fees"
    ) or {}

async def q_fees_history(c: str) -> dict:
    return await ask(
        _q(c, "UG and PG fees for academic years 2023-24, 2024-25, 2025-26 — per-year and total-course, hostel per year, all as plain numbers in local currency",
           '{"fees_by_year":['
           '{"year":"2023-24","program_type":"UG","per_year_inr":0,"total_course_inr":0,"hostel_per_year_inr":0},'
           '{"year":"2023-24","program_type":"PG","per_year_inr":0,"total_course_inr":0,"hostel_per_year_inr":0},'
           '{"year":"2024-25","program_type":"UG","per_year_inr":0,"total_course_inr":0,"hostel_per_year_inr":0},'
           '{"year":"2024-25","program_type":"PG","per_year_inr":0,"total_course_inr":0,"hostel_per_year_inr":0},'
           '{"year":"2025-26","program_type":"UG","per_year_inr":0,"total_course_inr":0,"hostel_per_year_inr":0},'
           '{"year":"2025-26","program_type":"PG","per_year_inr":0,"total_course_inr":0,"hostel_per_year_inr":0}'
           ']}'),
        "fees_history"
    ) or {}

async def q_placements(c: str) -> dict:
    return await ask(
        _q(c, "2025 placements: highest package, average package, median package, currency (LPA for India / IDR,USD etc otherwise), placement rate %, students placed, companies visited",
           '{"placements":{"year":"2025","highest_package":0,"average_package":0,"median_package":0,"package_currency":"","placement_rate_percent":0,"total_students_placed":0,"total_companies_visited":0}}'),
        "placements"
    ) or {}

async def q_placement_history(c: str) -> dict:
    return await ask(
        _q(c, "placement data for 2023, 2024, 2025: highest package, average package, median package, currency, students placed, placement rate %",
           '{"placement_comparison_last_3_years":['
           '{"year":"2023","highest_package":0,"average_package":0,"median_package":0,"package_currency":"","students_placed":0,"placement_rate_percent":0},'
           '{"year":"2024","highest_package":0,"average_package":0,"median_package":0,"package_currency":"","students_placed":0,"placement_rate_percent":0},'
           '{"year":"2025","highest_package":0,"average_package":0,"median_package":0,"package_currency":"","students_placed":0,"placement_rate_percent":0}'
           ']}'),
        "placement_history"
    ) or {}

async def q_sectors(c: str) -> dict:
    return await ask(
        _q(c, "top hiring sectors in 2025 placements with sector name, top companies list, and percentage of students placed in each",
           '{"sector_wise_placement_last_3_years":[{"year":"2025","sector":"","companies":[],"percent":0}]}'),
        "sectors"
    ) or {}

async def q_scholarships(c: str) -> dict:
    return await ask(
        _q(c, "list all scholarships, grants, fellowships available at this college — name, amount per year or one-time, eligibility criteria, and whether it is renewable (yes/no and condition)",
           '{"scholarships":[{"name":"","amount":"","eligibility":"","renewable":""}]}'),
        "scholarships"
    ) or {}

async def q_infrastructure(c: str) -> dict:
    return await ask(
        _q(c, "list top 8 major campus facilities (library, labs, hostel, sports, health centre, auditorium, etc.) with one-line details",
           '{"infrastructure":[{"facility":"","details":""}]}'),
        "infrastructure"
    ) or {}

async def q_student_count_history(c: str) -> dict:
    return await ask(
        _q(c, "total enrolled students, UG and PG counts for years 2023, 2024, 2025",
           '{"student_count_comparison_last_3_years":['
           '{"year":"2023","total_enrolled":0,"ug":0,"pg":0},'
           '{"year":"2024","total_enrolled":0,"ug":0,"pg":0},'
           '{"year":"2025","total_enrolled":0,"ug":0,"pg":0}'
           ']}'),
        "student_count_history"
    ) or {}

async def q_gender_placement(c: str) -> dict:
    return await ask(
        _q(c, "campus placement stats split by gender for 2023, 2024, 2025: number of male and female students placed, and their percentage of total placed. Use null if not known.",
           '{"gender_based_placement_last_3_years":['
           '{"year":"2023","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null},'
           '{"year":"2024","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null},'
           '{"year":"2025","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null}'
           ']}'),
        "gender_placement"
    ) or {}

# ---------------------------------------------------------------------------
# Main async processor
# ---------------------------------------------------------------------------

async def process_college(college_name: str):
    slug = re.sub(r"[^a-z0-9]+", "_", college_name.lower()).strip("_")
    out_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(out_dir, f"2nd_test_{slug}.json")

    wall_start = time.time()
    print(f"\n🚀 Direct LLM audit: {college_name}")
    print(f"   Output → {output_file}\n")

    async def run(label: str, coro):
        t = time.time()
        result = await coro
        elapsed = time.time() - t
        keys = list(result.keys())[:6] if result else []
        status = "✓" if result else "⚠ "
        print(f"  {status} {label:<20} ({elapsed:.1f}s)  keys: {keys}")
        return result or {}

    # ── STEP 1: Stats snapshot (single call, fastest possible) ─────────────
    print("── Quick Stats Snapshot ──────────────────────────────────────────")
    t0 = time.time()
    snap = await q_stats_snapshot(college_name)
    snap_time = time.time() - t0
    if snap:
        cur = snap.get("package_currency", "")
        def _s(v): return "?" if v is None else str(v)
        print(f"  ✓ stats_snapshot fetched in {snap_time:.1f}s")
        print(f"  ┌─────────────────────────────────────────┐")
        print(f"  │ Total Students  : {_s(snap.get('total_enrollment')):>8}              │")
        print(f"  │ UG / PG / PhD   : {_s(snap.get('ug_students'))} / {_s(snap.get('pg_students'))} / {_s(snap.get('phd_students'))}       │")
        print(f"  │ Male / Female   : {_s(snap.get('total_male'))} / {_s(snap.get('total_female'))} ({_s(snap.get('male_percent'))}%/{_s(snap.get('female_percent'))}%)│")
        print(f"  │ International   : {_s(snap.get('international_students')):>8}              │")
        print(f"  │ Placed / Rate   : {_s(snap.get('total_placed'))} / {_s(snap.get('placement_rate_percent'))}%           │")
        print(f"  │ Avg Package     : {_s(snap.get('average_package'))} {cur:<6}              │")
        print(f"  │ Highest Package : {_s(snap.get('highest_package'))} {cur:<6}              │")
        print(f"  └─────────────────────────────────────────┘")
    else:
        print(f"  ⚠  stats_snapshot failed ({snap_time:.1f}s)")

    # ── STEP 2: Full parallel batch ───────────────────────────────────────
    print(f"\n── Full Audit (20 queries, parallel) ─────────────────────────────")

    # Brave rate limit = 2 req/s but each query takes 3-12s,
    # so 4 concurrent never actually hits 2/s in practice.
    _sem = asyncio.Semaphore(4)

    async def throttled(label: str, coro):
        async with _sem:
            result = await run(label, coro)
        return result   # slot released before any delay

    (
        identity, about,
        rankings_raw, global_rank,
        faculty, students, intl, depts, stu_hist,
        ug, pg, phd,
        fees, fees_hist,
        placements, pl_history, gender_pl, sectors,
        sch, infra,
    ) = await asyncio.gather(
        throttled("identity",    q_identity(college_name)),
        throttled("about",       q_about(college_name)),
        throttled("rankings",    q_rankings(college_name)),
        throttled("global_rank", q_global_ranking(college_name)),
        throttled("faculty",     q_faculty(college_name)),
        throttled("students",    q_students(college_name)),
        throttled("intl",        q_international(college_name)),
        throttled("depts",       q_departments(college_name)),
        throttled("stu_hist",    q_student_count_history(college_name)),
        throttled("ug_progs",    q_ug_programs(college_name)),
        throttled("pg_progs",    q_pg_programs(college_name)),
        throttled("phd_progs",   q_phd_programs(college_name)),
        throttled("fees",        q_fees(college_name)),
        throttled("fees_hist",   q_fees_history(college_name)),
        throttled("placements",  q_placements(college_name)),
        throttled("pl_history",  q_placement_history(college_name)),
        throttled("gender_pl",   q_gender_placement(college_name)),
        throttled("sectors",     q_sectors(college_name)),
        throttled("scholarships",q_scholarships(college_name)),
        throttled("infra",       q_infrastructure(college_name)),
    )

    print(f"\n⏱  All queries done in {time.time()-wall_start:.1f}s")

    # ---- Assemble final dict ----
    final: dict = {}

    # Identity
    final.update(identity)
    final.update(about)

    # Rankings
    final["rankings"]      = rankings_raw
    final["global_ranking"] = global_rank

    # Faculty / students  (snapshot fills gaps if main query missed fields)
    final["faculty_staff"] = faculty
    def _pick(key, from_dict, fallback_dict):
        v = from_dict.get(key)
        return v if v not in (None, 0, "") else fallback_dict.get(key)

    final["student_statistics"] = {
        "total_enrollment": _pick("total_enrollment", students, snap),
        "ug_students":      _pick("ug_students",      students, snap),
        "pg_students":      _pick("pg_students",      students, snap),
        "phd_students":     _pick("phd_students",     students, snap),
        "annual_intake":    _pick("annual_intake",    students, snap),
    }
    final["student_gender_ratio"] = {
        "total_male":    _pick("total_male",    students, snap),
        "total_female":  _pick("total_female",  students, snap),
        "male_percent":  _pick("male_percent",  students, snap),
        "female_percent":_pick("female_percent",students, snap),
    }
    # Backfill international_students.total_count from snapshot if missing
    intl_merged = dict(intl)
    if not intl_merged.get("total_count"):
        intl_merged["total_count"] = snap.get("international_students")
    final["international_students"] = intl_merged
    final["departments"]               = depts.get("departments", [])
    final["student_count_comparison_last_3_years"] = stu_hist.get("student_count_comparison_last_3_years", [])

    # Programs
    final["ug_programs"]  = ug.get("ug_programs", [])
    final["pg_programs"]  = pg.get("pg_programs", [])
    final["phd_programs"] = phd.get("phd_programs", [])

    # Fees
    final["fees"]         = fees.get("fees", {})
    final["fees_by_year"] = fees_hist.get("fees_by_year", [])

    # Placements
    final["placements"]                          = placements.get("placements", {})
    final["placement_comparison_last_3_years"]   = pl_history.get("placement_comparison_last_3_years", [])
    # Clean gender placement: replace 0 counts/percents with not_available
    _gpl = gender_pl.get("gender_based_placement_last_3_years", [])
    _gpl_fields = ["male_placed", "female_placed", "male_percent", "female_percent"]
    for row in _gpl:
        row.pop("package_currency", None)   # remove stray field if LLM added it
        for f in _gpl_fields:
            if row.get(f) in (0, None):
                row[f] = "not_available"
    final["gender_based_placement_last_3_years"] = _gpl
    final["sector_wise_placement_last_3_years"]  = sectors.get("sector_wise_placement_last_3_years", [])

    # Scholarships / Infrastructure
    final["scholarships"]  = sch.get("scholarships", [])
    final["infrastructure"] = infra.get("infrastructure", [])

    # Force college_name (Brave may have overwritten with formatted version)
    final["college_name"] = college_name

    # ---- Schema defaults ----
    defaults = {
        "short_name": "", "location": "", "country": "",
        "established": None, "institution_type": "", "campus_area": "",
        "about": "", "additional_details": [], "departments": [],
        "ug_programs": [], "pg_programs": [], "phd_programs": [],
        "fees": {"UG": {}, "PG": {}}, "fees_by_year": [],
        "faculty_staff": {}, "placements": {},
        "placement_comparison_last_3_years": [],
        "gender_based_placement_last_3_years": [],
        "sector_wise_placement_last_3_years": [],
        "student_statistics": {}, "student_gender_ratio": {},
        "student_count_comparison_last_3_years": [],
        "international_students": {}, "infrastructure": [],
        "scholarships": [], "rankings": {}, "rankings_history": [],
        "global_ranking": {}, "sources": [], "source_url": "",
        "summary": "", "validation_report": "", "last_updated": "",
        "data_confidence_score": None,
    }
    for k, v in defaults.items():
        final.setdefault(k, v)

    # ---- Post-processing: currency, integrity checks, not_available fills ----
    final = finalize_output(final)

    with open(output_file, "w") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved → {output_file}")
    return final


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ans_audit.py \"College Name\"")
        print("Example: python ans_audit.py \"IIT Madras\"")
        sys.exit(1)

    college = " ".join(sys.argv[1:])
    asyncio.run(process_college(college))
