"""
College data extractor — Two-Phase approach.

Phase 1 (Groq, ~2s):   college name/about, current rankings, current student stats, total faculty
Phase 2 (Gemini, parallel): programs, departments, placements, fees, rankings history,
                            student history, additional info
"""

import json
import sys
import time
import re
import concurrent.futures
import google.genai as genai
from groq import Groq

# Gemini (Phase 2)
GEMINI_API_KEY = "AIzaSyBi8uFkM7rhjtA56DfQGdFpGqFl5hbQni8"
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

# Groq (Phase 1 — fast)
GROQ_API_KEY = "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"
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # has live web search built-in


# ---------------------------------------------------------------------------
# PHASE 1 — single fast prompt, targets ~5s response
# Returns the "above the fold" snapshot
# ---------------------------------------------------------------------------

PHASE1_PROMPT = """You are a university data expert. Using ONLY your verified training knowledge about "{name}", return a single JSON object with these keys:

college_name: full official name
short_name: abbreviation or common name
established: founding year (integer)
institution_type: "Public" or "Private"
location: "City, State/Region, Country"
country: country name
website: official URL
about: 2-3 factual sentences about founding, affiliations, global standing, notable strengths

rankings: object with keys:
  nirf_2025 (integer or "not_available" — only for Indian colleges),
  nirf_2024 (integer or "not_available" — only for Indian colleges),
  qs_world (integer — fill if known, else "not_available"),
  qs_asia (integer — fill if known, else "not_available"),
  the_world (integer — fill if known, else "not_available"),
  national_rank (integer — rank within the country, fill if known),
  state_rank (integer — rank within the state/region, fill if known)

student_statistics: object with keys:
  total_enrollment (total headcount all students currently enrolled, integer),
  ug_students (undergraduate only — DO NOT include postgrad or research students),
  pg_students (taught postgraduate/coursework masters — DO NOT include PhD/research students here),
  phd_students (ONLY doctoral/PhD research candidates — typically a much smaller number than pg_students, e.g. 1,000–3,000 for large universities, NOT 6,000+),
  annual_intake (new students admitted per year),
  male_percent (percentage male — note: many modern universities have more female than male students, e.g. 40–45% male is common),
  female_percent (percentage female),
  total_ug_courses (SEARCH: total number of distinct UG degree programs/courses currently offered by this college — search the official website or course catalog),
  total_pg_courses (SEARCH: total number of distinct PG/masters degree programs currently offered),
  total_phd_courses (SEARCH: total number of distinct PhD/doctoral programs currently offered)

faculty_staff: object with keys:
  total_faculty (current, best estimate),
  student_faculty_ratio,
  phd_faculty_percent

departments: array of faculty/department names this college has

CRITICAL RULES FOR STUDENT STATISTICS:
- phd_students = ONLY research doctoral candidates, NOT all postgraduate students. For most universities this is 1,000–4,000, almost never above 10% of total enrollment.
- pg_students = coursework/taught masters students only. Do NOT double-count PhD students here.
- total_enrollment = ug_students + pg_students + phd_students (these three should add up roughly).
- Gender: at most modern universities females outnumber males (55–60% female is common). Do not default to near-50/50 unless you are certain.
- If you are not certain of exact numbers, give your best estimate — do NOT invent false precision.
- For total_ug_courses / total_pg_courses / total_phd_courses: SEARCH the web for "[college name] total courses offered" or "[college name] course catalog" to get the actual count. These are course/program counts, NOT student counts.
- NEVER use "not_applicable". Use "not_available" only if you genuinely cannot find the data.
- NIRF rankings apply to Indian colleges only; set "not_available" for all others.
- No markdown fences. Return valid JSON only."""


# ---------------------------------------------------------------------------
# PHASE 2 — heavier sections, all run in parallel after Phase 1
# ---------------------------------------------------------------------------

PHASE2_SECTIONS = {
    "programs": """You are a college programs expert. Using ONLY your verified training knowledge about "{name}", return a JSON object:
- total_ug_programs: integer — total number of UG programs offered (approximate is fine)
- total_pg_programs: integer — total number of PG programs offered
- total_phd_programs: integer — total number of PhD/doctoral programs
- ug_programs: top 10 most popular/notable UG programs — array of objects with keys: name, duration (e.g. "3 years"), seats (integer or null), fees_total_local (number or null)
- pg_programs: top 10 most popular/notable PG programs, same structure
- phd_programs: top 5 notable PhD programs — array of objects with keys: name, duration, seats

RULES:
- India: 4-year BE/BTech, 2-year ME/MTech. Europe/Australia: 3-year BSc/BA, 2-year MSc/MA.
- Only list programs you KNOW this college actually offers.
- Use "not_available" (never "not_applicable") for unknown totals.
No markdown fences. Return valid JSON only.""",

    "rankings_history": """You are a college rankings expert. Using ONLY your verified training knowledge about "{name}", return a JSON object:
- rankings_history: array of ranking entries for years 2021 to 2025 only, each object with keys: year (integer), ranking_body (string), rank (integer or string), category (e.g. "World", "Asia", "National", or subject name). Include QS, THE, ARWU, US News, national rankings only — maximum 20 entries total.
- global_ranking: object with keys qs_world, the_world, us_news_global, arwu, webometrics — most recent values, "not_available" if unknown

RULES: NEVER fabricate numbers. Max 20 entries in rankings_history. No markdown fences. Return valid JSON only.""",

    "placements": """You are a college employment/placement expert. Using ONLY your verified training knowledge about "{name}", return a JSON object:

For non-Indian colleges: use graduate employment rate, median salary in local currency. Provide best estimates if exact figures are unavailable — note them as estimates.
For Indian colleges: use placement rate, packages in LPA.

placements: object with keys:
  year (most recent available),
  highest_package, average_package, median_package,
  package_currency (e.g. "LPA", "AUD/year", "USD/year"),
  placement_rate_percent (Indian) or employment_rate_percent (non-Indian),
  total_students_placed, total_companies_visited,
  graduate_outcomes_note (text summary)

placement_comparison_last_3_years: array of 3 objects with keys: year, average_package, employment_rate_percent, package_currency
gender_based_placement_last_3_years: array of 3 objects with keys: year, male_placed, female_placed, male_percent, female_percent
sector_wise_placement_last_3_years: array of objects with keys: year, sector, companies, percent
top_recruiters: array of company names known to hire from this college
placement_highlights: detailed paragraph on graduate employment, salary ranges, top employers

RULE: NEVER use "not_applicable". Use "not_available" only if truly unknown.
No markdown fences. Return valid JSON only.""",

    "fees_infra": """You are a college fees and infrastructure expert. Using ONLY your verified training knowledge about "{name}", return a JSON object:

fees: object with keys UG (object: per_year, total_course, currency), PG (same), hostel_per_year
fees_note: explain domestic vs international fee differences, tuition-free status, or any important fee context
fees_by_year: array of objects with keys year, program_type, per_year_local, total_course_local, hostel_per_year_local, currency — for 2023-24, 2024-25, 2025-26
scholarships: array of objects with keys name, amount, eligibility, provider — only scholarships specifically available at THIS college
infrastructure: array of objects with keys facility, details
hostel_details: object with keys available, boys_capacity, girls_capacity, total_capacity, type
transport_details: object with keys buses, routes
library_details: object with keys total_books, journals, e_resources, area_sqft

RULES:
- Provide fees in local currency. Approximate ranges are acceptable — add an estimate note.
- NEVER use "not_applicable". Use "not_available" only if truly unknown.
- No double braces. Return clean JSON only, no markdown fences.""",

    "student_history": """You are a college statistics expert. Using ONLY your verified training knowledge about "{name}", return a JSON object:

student_count_comparison_last_3_years: array of 3 objects each with keys year, total_enrolled, ug, pg, phd — for years 2023, 2024, 2025
student_gender_ratio: object with keys total_male, total_female, male_percent, female_percent
international_students: object with keys total_count, countries_represented, international_percent
notable_faculty: array of objects with keys name, designation, specialization — only real confirmed names
faculty_achievements: text summary of faculty recognition/awards or null

RULES: Provide best estimates if exact figures unavailable. NEVER use "not_applicable".
No markdown fences. Return valid JSON only.""",

    "identity_details": """You are a college information expert. Using ONLY your verified training knowledge about "{name}", return a JSON object:

accreditations: array of objects with keys body, grade, year — only confirmed accreditations
affiliations: array of confirmed membership organizations/networks/alliances
recognition: text describing government/ministry recognitions
campus_area: campus size e.g. "150 acres" or null if unknown
contact_info: object with keys phone, email, address
additional_details: array of notable verified facts about this college (history, achievements, firsts, records)

RULES: Only list confirmed facts. NEVER use "not_applicable". Return valid JSON only, no markdown fences."""
}



# ---------------------------------------------------------------------------
# Core callers
# ---------------------------------------------------------------------------

def _call_groq(label: str, prompt: str, max_tokens: int = 4096) -> tuple:
    """Call Groq for Phase 1. compound-beta has live web search built-in."""
    t0 = time.time()
    max_tokens = min(max_tokens, 8192)  # Groq hard limit
    for attempt in range(1, 4):
        try:
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            # compound-beta may use tool calls internally; final content is in choices[0].message.content
            msg = resp.choices[0].message
            text = msg.content
            if not text:
                # fallback: check all choices for a non-empty content
                for choice in resp.choices:
                    if choice.message.content:
                        text = choice.message.content
                        break
            if not text:
                raise ValueError("Empty response from Groq compound-beta")

            text = text.strip()
            if not text:
                raise ValueError("Empty content after strip")
            text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*```$', '', text)
            text = re.sub(r',\s*([}\]])', r'\1', text)

            result = json.loads(text)
            elapsed = round(time.time() - t0, 2)
            # show search sources used if available
            sources = getattr(msg, 'tool_calls', None)
            src_note = f"  [web search used]" if sources else ""
            print(f"  ✓ [groq:{label}] done in {elapsed}s{src_note}")
            return label, result, elapsed

        except json.JSONDecodeError as e:
            if attempt < 3:
                print(f"  ⚠  [groq:{label}] JSON error attempt {attempt}, retrying…")
                time.sleep(0.5)
                continue
            elapsed = round(time.time() - t0, 2)
            print(f"  ✗ [groq:{label}] failed ({elapsed}s): {e}")
            return label, None, elapsed
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"  ✗ [groq:{label}] error ({elapsed}s): {e}")
            return label, None, elapsed

    return label, None, round(time.time() - t0, 2)


def _call_gemini(label: str, prompt: str, max_tokens: int = 8192) -> tuple:
    """Call Gemini with a prompt. Returns (label, result_dict_or_None, elapsed)."""
    t0 = time.time()
    for attempt in range(1, 4):
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=max_tokens,
                )
            )
            text = response.text.strip()
            text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*```$', '', text)
            text = re.sub(r',\s*([}\]])', r'\1', text)

            result = json.loads(text)
            elapsed = round(time.time() - t0, 2)
            print(f"  ✓ [{label}] done in {elapsed}s")
            return label, result, elapsed

        except json.JSONDecodeError as e:
            if attempt < 3:
                print(f"  ⚠  [{label}] JSON error attempt {attempt}, retrying…")
                time.sleep(1)
                continue
            elapsed = round(time.time() - t0, 2)
            print(f"  ✗ [{label}] failed ({elapsed}s): {e}")
            return label, None, elapsed
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"  ✗ [{label}] error ({elapsed}s): {e}")
            return label, None, elapsed

    return label, None, round(time.time() - t0, 2)


# ---------------------------------------------------------------------------
# Reconcile: replace Groq fields with Gemini where they differ (deep)
# ---------------------------------------------------------------------------

def _reconcile(groq_data: dict, gemini_data: dict) -> tuple:
    """Deep-compare groq vs gemini. Returns (reconciled_dict, list_of_changes).
    Gemini wins for all fields EXCEPT web-searched course counts where Groq wins."""
    if not gemini_data:
        return groq_data, []

    # Fields inside student_statistics where Groq compound-beta wins
    # (it web-searched these, so its values are more reliable than Gemini training data)
    GROQ_WINS_SUBKEYS = {"total_ug_courses", "total_pg_courses", "total_phd_courses"}

    changes = []
    result = dict(groq_data)

    for key, gem_val in gemini_data.items():
        groq_val = groq_data.get(key)
        if groq_val is None and gem_val is not None:
            result[key] = gem_val
            changes.append(f"  + {key}: added from Gemini")
        elif isinstance(gem_val, dict) and isinstance(groq_val, dict):
            merged_sub = dict(groq_val)
            for sk, sv in gem_val.items():
                gv = groq_val.get(sk)
                # Groq wins for web-searched course counts
                if sk in GROQ_WINS_SUBKEYS:
                    if gv and gv != "not_available":
                        pass  # keep Groq's web-searched value
                    elif sv not in (None, "not_available"):
                        merged_sub[sk] = sv  # use Gemini if Groq didn't get it
                elif gv != sv and sv not in (None, "not_available"):
                    merged_sub[sk] = sv
                    changes.append(f"  ~ {key}.{sk}: {gv!r} → {sv!r}")
            result[key] = merged_sub
        elif gem_val != groq_val and gem_val not in (None, "not_available"):
            result[key] = gem_val
            changes.append(f"  ~ {key}: {groq_val!r} → {gem_val!r}")

    return result, changes


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------

def extract_college(college_name: str) -> dict:
    timings = {}
    all_results = {}  # will hold phase1_overview + all phase2 sections

    # ── PHASE 1: Groq + Gemini fired simultaneously ───────────────────────
    print(f"\n🚀 [{college_name}]  Phase 1 — Groq + Gemini in parallel…")
    p1_prompt = PHASE1_PROMPT.replace("{name}", college_name)

    def _print_snapshot(data, source, elapsed):
        if not data:
            print(f"  ✗ Phase 1 [{source}] failed ({elapsed}s)")
            return
        rnk = data.get("rankings", {})
        stu = data.get("student_statistics", {})
        fac = data.get("faculty_staff", {})
        print(f"\n{'─'*60}")
        print(f"  ✅ Phase 1 [{source}] done in {elapsed}s")
        print(f"  College  : {data.get('college_name')}  ({data.get('country')})")
        print(f"  About    : {str(data.get('about',''))[:120]}…")
        print(f"  Rankings : QS={rnk.get('qs_world')}  THE={rnk.get('the_world')}  "
              f"NIRF={rnk.get('nirf_2025','n/a')}  National={rnk.get('national_rank')}")
        print(f"  Students : {stu.get('total_enrollment')} total  "
              f"(UG={stu.get('ug_students')} PG={stu.get('pg_students')} "
              f"PhD={stu.get('phd_students')})  "
              f"Male={stu.get('male_percent')}%  Female={stu.get('female_percent')}%")
        if stu.get('total_ug_courses'):
            print(f"  Courses  : UG={stu.get('total_ug_courses')}  "
                  f"PG={stu.get('total_pg_courses')}  PhD={stu.get('total_phd_courses')}")
        print(f"  Faculty  : {fac.get('total_faculty')} total  "
              f"Ratio={fac.get('student_faculty_ratio')}")
        print(f"{'─'*60}")

    # Fire both at once
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p1_ex:
        groq_fut   = p1_ex.submit(_call_groq,   "phase1_groq",   p1_prompt, 4096)
        gemini_fut = p1_ex.submit(_call_gemini, "phase1_gemini", p1_prompt, 4096)

        # Groq finishes first — show snapshot immediately
        _, groq_result, groq_elapsed = groq_fut.result()
        timings["phase1_groq"] = groq_elapsed
        _print_snapshot(groq_result, "Groq", groq_elapsed)

        # Wait for Gemini Phase 1
        _, gemini_result, gemini_elapsed = gemini_fut.result()
        timings["phase1_gemini"] = gemini_elapsed
        _print_snapshot(gemini_result, "Gemini", gemini_elapsed)

    # Reconcile: Groq is base, Gemini overrides where values differ
    if groq_result and gemini_result:
        p1_result, changes = _reconcile(groq_result, gemini_result)
        if changes:
            print(f"\n🔄 Reconciled {len(changes)} field(s) — Gemini wins:")
            for c in changes:
                print(c)
        else:
            print("\n✅ Groq ≡ Gemini for Phase 1 — no changes needed")
    elif groq_result:
        p1_result = groq_result
        print("  ⚠  Gemini Phase 1 failed — using Groq-only result")
    elif gemini_result:
        p1_result = gemini_result
        print("  ⚠  Groq Phase 1 failed — using Gemini-only result")
    else:
        p1_result = None
        print("  ✗ Both Phase 1 sources failed")

    p1_wall = round(max(
        timings.get("phase1_groq", 0),
        timings.get("phase1_gemini", 0)
    ), 2)
    all_results["phase1_overview"] = p1_result
    timings["phase1_overview"] = p1_wall
    print(f"\n[✔] Phase 1 complete in {p1_wall}s  "
          f"(Groq={timings.get('phase1_groq')}s  Gemini={timings.get('phase1_gemini')}s)\n")

    # ── PHASE 2: all heavy sections — Groq + Gemini in parallel ──────────
    print(f"🔄 Phase 2 — {len(PHASE2_SECTIONS)} sections × 2 models in parallel…\n")
    wall_p2_start = time.time()

    # per-section token budgets (default 8192)
    SECTION_TOKENS = {
        "fees_infra": 10000,
        "placements": 10000,
        "programs":   10000,
    }

    # Submit Groq + Gemini for every section simultaneously
    groq_p2: dict   = {}
    gemini_p2: dict = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(PHASE2_SECTIONS) * 2) as ex:
        g_futs = {
            ex.submit(
                _call_groq, f"groq:{sec}",
                PHASE2_SECTIONS[sec].replace("{name}", college_name),
                SECTION_TOKENS.get(sec, 8192)
            ): sec
            for sec in PHASE2_SECTIONS
        }
        gem_futs = {
            ex.submit(
                _call_gemini, f"gemini:{sec}",
                PHASE2_SECTIONS[sec].replace("{name}", college_name),
                SECTION_TOKENS.get(sec, 8192)
            ): sec
            for sec in PHASE2_SECTIONS
        }

        for fut, sec in g_futs.items():
            _, result, elapsed = fut.result()
            groq_p2[sec]            = result
            timings[f"groq2:{sec}"] = elapsed

        for fut, sec in gem_futs.items():
            _, result, elapsed = fut.result()
            gemini_p2[sec]            = result
            timings[f"gemini2:{sec}"] = elapsed

    # Reconcile each section: Gemini wins on mismatches (same as Phase 1)
    for sec in PHASE2_SECTIONS:
        g_res   = groq_p2.get(sec)
        gem_res = gemini_p2.get(sec)
        if g_res and gem_res:
            rec, changes = _reconcile(g_res, gem_res)
            if changes:
                print(f"  🔄 [{sec}] reconciled {len(changes)} field(s) — Gemini wins:")
                for c in changes:
                    print(c)
            all_results[sec] = rec
        elif g_res:
            print(f"  ⚠  [{sec}] Gemini failed — using Groq only")
            all_results[sec] = g_res
        elif gem_res:
            print(f"  ⚠  [{sec}] Groq failed — using Gemini only")
            all_results[sec] = gem_res
        else:
            all_results[sec] = None
        # wall time = slower of the two models
        timings[sec] = max(
            timings.get(f"groq2:{sec}", 0),
            timings.get(f"gemini2:{sec}", 0)
        )

    wall_p2 = round(time.time() - wall_p2_start, 2)
    wall_total = round(p1_wall + wall_p2, 2)

    # ── Merge everything into one flat dict ────────────────────────────────
    merged = {}
    if p1_result:
        merged.update(p1_result)
    for sec_name, result in all_results.items():
        if sec_name == "phase1_overview":
            continue
        if isinstance(result, dict):
            merged.update(result)

    groq_college_name   = (groq_result   or {}).get("college_name") or college_name
    gemini_college_name = (gemini_result or {}).get("college_name") or college_name
    final_college_name  = merged.get("college_name") or college_name

    merged["college_name"]        = final_college_name
    merged["groq_college_name"]   = groq_college_name
    merged["gemini_college_name"] = gemini_college_name
    merged["final_college_name"]  = final_college_name
    merged["_meta"] = {
        "source": "groq+gemini-phase1 / groq+gemini-phase2",
        "groq_college_name": groq_college_name,
        "gemini_college_name": gemini_college_name,
        "final_college_name": final_college_name,
        "phase1_groq_model": GROQ_MODEL,
        "phase1_gemini_model": GEMINI_MODEL,
        "phase2_model": GEMINI_MODEL,
        "phase1_groq_seconds": timings.get("phase1_groq"),
        "phase1_gemini_seconds": timings.get("phase1_gemini"),
        "phase1_wall_seconds": timings.get("phase1_overview"),
        "phase2_seconds": wall_p2,
        "total_seconds": wall_total,
        "timings": {k: {"elapsed": timings[k], "ok": all_results.get(k) is not None}
                    for k in timings}
    }

    # ── Summary ────────────────────────────────────────────────────────────
    # Groq/Gemini Phase 2 wall = max of their individual section times (all ran in parallel)
    groq_p2_wall   = round(max((timings.get(f"groq2:{s}",   0) for s in PHASE2_SECTIONS), default=0), 2)
    gemini_p2_wall = round(max((timings.get(f"gemini2:{s}", 0) for s in PHASE2_SECTIONS), default=0), 2)

    print(f"\n{'─'*50}")
    print(f"⏱  Phase 1 (Groq={timings.get('phase1_groq')}s + Gemini={timings.get('phase1_gemini')}s, wall={p1_wall}s)")
    print(f"⏱  Phase 2 — Groq wall={groq_p2_wall}s  |  Gemini wall={gemini_p2_wall}s  |  Combined wall={wall_p2}s  ({len(PHASE2_SECTIONS)} sections)")
    print(f"⏱  Total wall-clock   : {wall_total}s")
    print(f"\n{'Section':<28} {'Groq':>7}  {'Gemini':>7}  {'Wall':>7}  Status")
    print("─" * 62)
    for sec in ["phase1_overview"] + list(PHASE2_SECTIONS.keys()):
        if sec == "phase1_overview":
            tg  = timings.get("phase1_groq",   "—")
            tm  = timings.get("phase1_gemini",  "—")
            tw  = timings.get("phase1_overview","—")
        else:
            tg  = timings.get(f"groq2:{sec}",  "—")
            tm  = timings.get(f"gemini2:{sec}", "—")
            tw  = timings.get(sec, "—")
        ok = "✓" if all_results.get(sec) else "✗"
        tg_s  = f"{tg}s"  if tg  != "—" else "—"
        tm_s  = f"{tm}s"  if tm  != "—" else "—"
        tw_s  = f"{tw}s"  if tw  != "—" else "—"
        print(f"  {sec:<26} {tg_s:>7}  {tm_s:>8}  {tw_s:>7}  {ok}")

    ok_count = sum(1 for r in all_results.values() if r is not None)
    print(f"\n  {ok_count}/{len(all_results)} sections succeeded")

    return merged


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "Bifröst University"

    data = extract_college(name)

    def _safe(s: str) -> str:
        return s.lower().replace(" ", "_").replace("/", "_").replace(",", "")

    groq_name   = data.get("groq_college_name",   name)
    gemini_name = data.get("gemini_college_name",  name)
    final_name  = data.get("final_college_name",   name)

    out_path = (
        f"college_scraper/"
        f"groq_{_safe(groq_name)}__"
        f"gemini_{_safe(gemini_name)}__"
        f"final_{_safe(final_name)}.json"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved → {out_path}")
    print(f"   groq_college_name  : {groq_name}")
    print(f"   gemini_college_name: {gemini_name}")
    print(f"   final_college_name : {final_name}")
    print(f"   Total keys: {len([k for k in data if not k.startswith('_')])}")
