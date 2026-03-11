import json
import os
import sys
import re
import html
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq

GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compress_snippet(text: str) -> str:
    """Remove HTML entities, excessive whitespace and raw JSON blobs to save tokens."""
    text = html.unescape(text)                          # &amp; -> &, &nbsp; -> space
    text = re.sub(r'\{\"@(type|graph|context)[^}]{0,2000}\}', '', text)  # strip JSON-LD blobs
    text = re.sub(r'!\[Image[^\]]*\]\([^)]*\)', '', text)  # strip image markdown
    text = re.sub(r'https?://\S+', '', text)            # strip raw URLs
    text = re.sub(r'\n{3,}', '\n\n', text)              # collapse blank lines
    text = re.sub(r'[ \t]{2,}', ' ', text)              # collapse spaces
    return text.strip()

def build_context(sections: list, names: list, char_limit: int) -> str:
    """Build compressed context string from specified section names.
    Each section gets a fair share of the budget so no single section
    crowds out the others.
    """
    # Step 1: collect compressed text per section
    section_texts = {}
    for s in sections:
        name = s.get("section")
        if name not in names:
            continue
        parts = []
        for src in s.get("sources", []):
            for snip in src.get("snippets", []):
                compressed = compress_snippet(snip)
                if compressed:
                    parts.append(compressed)
        if parts:
            section_texts[name] = "\n".join(parts)

    # Step 2: allocate budget evenly across present sections
    n = len(section_texts)
    if n == 0:
        return ""
    per_section_budget = max(800, char_limit // n)

    ctx = ""
    for name in names:          # preserve priority order
        if name not in section_texts:
            continue
        text = section_texts[name][:per_section_budget]
        ctx += f"\n[{name}]\n{text}\n"

    return ctx

def _repair_json(text: str) -> str:
    """Strip ~ prefixes and fix common LLM JSON mistakes."""
    text = re.sub(r':\s*"?~([0-9][0-9,.]*)\"?', lambda m: ': ' + m.group(1).replace(',', ''), text)
    text = re.sub(r'"~([^"]+)"', r'"\1"', text)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text


def call_groq(system_prompt: str, user_content: str, label: str) -> dict | None:
    """Call Groq and return parsed JSON, with retry on rate-limit or parse error."""
    for attempt in range(3):
        try:
            print(f"  ↳ Groq call '{label}' (attempt {attempt+1})…")
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0,
                max_tokens=8192,
                stream=False,
            )
            text = resp.choices[0].message.content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                try:
                    return json.loads(_repair_json(text))
                except json.JSONDecodeError:
                    if attempt < 2:
                        print(f"  ⚠  JSON parse error, retrying…")
                        time.sleep(3)
                        continue
                    print(f"  ✗ JSON parse error ({label}) — giving up")
                    return None
        except Exception as e:
            msg = str(e)
            if "tokens per day" in msg or "TPD" in msg:
                # Extract wait time if present
                wait_match = re.search(r'try again in ([\dhms ]+)', msg)
                wait_str = wait_match.group(1).strip() if wait_match else "some time"
                print(f"\n  ✗ DAILY TOKEN LIMIT EXHAUSTED (100k tokens/day on free tier).")
                print(f"    Please wait {wait_str} and run again.")
                print(f"    Or upgrade at: https://console.groq.com/settings/billing")
                return None
            elif "rate_limit" in msg or "413" in msg or "tokens per minute" in msg:
                wait = 65 * (attempt + 1)
                print(f"  ⚠  Per-minute rate-limit hit, waiting {wait}s…")
                time.sleep(wait)
            else:
                print(f"  ✗ Groq error ({label}): {e}")
                return None
    return None

# ---------------------------------------------------------------------------
# Three-batch prompts  (smaller per-call token usage → stays under 12k TPM)
# ---------------------------------------------------------------------------

# Shared preamble injected into every prompt
_KNOWLEDGE_HINT = """
IMPORTANT RULES:
1. Return ONLY valid, parseable JSON — no markdown fences, no commentary.
2. For NUMBER fields: always output a plain number (integer or float). Never use commas or symbols.
3. For STRING fields: if the exact value is unknown but estimable, prefix with "~" (e.g. "~5000").
4. NEVER leave a field null if you can provide a reasonable estimate — use your web search + training knowledge.
5. Fill in ALL fields — zero is valid for numbers, "unknown" only as absolute last resort.
6. ACCURACY IS CRITICAL — do NOT hallucinate or inflate figures. Verify numbers before outputting.
   - Faculty count for a college of ~10,000 students is typically 300-800, never 5000+.
   - Enrollment for a mid-size Indian private college is 5,000-15,000, never 50,000+.
   - International student % for Indian colleges is typically <5%.
7. For Indian colleges: fees are in INR, placements in LPA. For non-Indian: use local currency.
8. Search the web / use latest available data for rankings, fees, and placement figures."""

# Batch A: Rankings + Faculty + Students
BATCH_A_PROMPT = """Search the web for the most current and accurate data for this college, then return ONLY valid JSON.
Extraction hints:
- nirf_2025/nirf_2024: NIRF Ranking 2025 / 2024 — only for Indian colleges (e.g. "45" or "12")
- qs_asia_2025: QS Asia Rankings 2025 or 2026 (e.g. "301-350")
- qs_world: QS World University Rankings latest year (e.g. "800-850")
- the_world_2024: Times Higher Education World ranking (e.g. "601-800")
- national_rank: overall rank within the college's country from any credible ranking body
- total_faculty: ACTUAL faculty/teaching staff headcount — do NOT confuse with total staff/employees
  (for a college with 10,000 students, expect 300-800 faculty, NOT thousands)
- phd_faculty_count: number of faculty who hold a PhD
- student_faculty_ratio: e.g. "15:1"
- total_enrollment: total students currently enrolled (UG + PG + PhD)
  (for a mid-size private Indian college expect 5,000-20,000, NOT 50,000+)
- male_percent/female_percent: gender split as percentage numbers (e.g. 60, 40)
- For student_count_comparison use years 2023, 2024, 2025
""" + _KNOWLEDGE_HINT + """

{
"rankings":{"nirf_2025":"","nirf_2024":"","qs_asia_2025":"","qs_world":"","the_world_2024":"","national_rank":""},
"rankings_history":[{"year":"","ranking_body":"","rank":"","score":""}],
"global_ranking":{"qs_world":"","the_world":"","us_news_global":""},
"faculty_staff":{"total_faculty":null,"phd_faculty_count":null,"student_faculty_ratio":"","professors":null,"associate_professors":null,"assistant_professors":null},
"student_statistics":{"total_enrollment":null,"ug_students":null,"pg_students":null,"phd_students":null,"annual_intake":null},
"student_gender_ratio":{"total_male":null,"total_female":null,"male_percent":null,"female_percent":null},
"student_count_comparison_last_3_years":[{"year":"2023","total_enrolled":null,"ug":null,"pg":null},{"year":"2024","total_enrolled":null,"ug":null,"pg":null},{"year":"2025","total_enrolled":null,"ug":null,"pg":null}],
"international_students":{"total_count":null,"countries_represented":null,"nri_students":null}
}"""

# Batch B: Placements
BATCH_B_PROMPT = """Search the web for the latest placement / career outcomes data for this college, then return ONLY valid JSON.
Extraction hints:
- Use years 2023, 2024, 2025 for placement_comparison_last_3_years
- For INDIAN colleges: package in LPA (e.g. 18.5 = 18.5 LPA), package_currency = "LPA"
  Typical private engineering college avg: 5-12 LPA. Top IITs avg: 20-30 LPA. Do NOT invent figures.
- For NON-INDIAN colleges: annual salary in local currency, package_currency = "IDR"/"USD"/etc.
- highest_package: single highest offer received — must be realistic (not 10x the average)
- average_package: mean CTC/salary across all placed students
- placement_rate_percent: % of eligible students placed within 6 months (e.g. 85)
- total_students_placed: absolute headcount placed
- total_companies_visited: number of recruiters who visited campus
- sector_wise: realistic sectors for this college type (IT/Core/Consulting/Finance for engineering)
- VERIFY figures — do not extrapolate or multiply; if unknown use null
""" + _KNOWLEDGE_HINT + """

{
"placements":{"year":"2025","highest_package":null,"average_package":null,"median_package":null,"package_currency":"","placement_rate_percent":null,"total_students_placed":null,"total_companies_visited":null},
"placement_comparison_last_3_years":[{"year":"2023","highest_package":null,"average_package":null,"median_package":null,"package_currency":"","students_placed":null,"placement_rate_percent":null},{"year":"2024","highest_package":null,"average_package":null,"median_package":null,"package_currency":"","students_placed":null,"placement_rate_percent":null},{"year":"2025","highest_package":null,"average_package":null,"median_package":null,"package_currency":"","students_placed":null,"placement_rate_percent":null}],
"gender_based_placement_last_3_years":[{"year":"2023","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null},{"year":"2024","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null},{"year":"2025","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null}],
"sector_wise_placement_last_3_years":[{"year":"2025","sector":"","companies":[],"percent":null}]
}"""

# Batch C1: Identity + About + UG / PG / PhD Programs (all as arrays)
BATCH_C1_PROMPT = """Search the web for accurate program and identity information for this college, then return ONLY valid JSON.
Extraction hints:
- college_name: full official name as per NAAC/UGC/official website
- short_name: commonly used abbreviation (e.g. PSG Tech, IIT-M, BITS Pilani)
- established: integer year founded per official records
- institution_type: "Autonomous" / "Deemed University" / "Private" / "Government" / "Central University"
- location: city, district, state (e.g. "Coimbatore, Tamil Nadu")
- country: country name only — NOT a city or province
- campus_area: e.g. "75 acres" — search official site if needed
- about: 3 factual sentences covering founding year, affiliation/accreditation (NAAC grade, NBA, NIRF), and key strengths
- List EVERY individual UG/PG/PhD program as a SEPARATE object with FULL specialization name
  (e.g. "B.Tech in Artificial Intelligence and Data Science", NOT just "B.Tech")
- seats: official intake per program from TNEA/JOSAA/official brochure
- fees_total_local: total course fees in INR (or local currency) — NOT per year
- departments: full list of academic departments

""" + _KNOWLEDGE_HINT + """

{
"college_name":"",
"short_name":"",
"location":"",
"country":"",
"established":null,
"institution_type":"",
"campus_area":"",
"about":"",
"additional_details":[{"category":"","value":""}],
"departments":[],
"ug_programs":[{"name":"","duration":"","seats":null,"fees_total_local":null}],
"pg_programs":[{"name":"","duration":"","seats":null,"fees_total_local":null}],
"phd_programs":[{"name":"","duration":"","seats":null}],
"sources":[]
}"""

# Batch C2: Fees by year — last 3 academic years
BATCH_C2_PROMPT = """Search the web for the official fee structure of this college, then return ONLY valid JSON.
Extraction hints:
- per_year: annual tuition fee per student in local currency (plain integer, no commas/symbols)
- total_course: total fees for the entire program duration (4 years for B.Tech, 2 years for M.Tech, etc.)
- hostel_per_year: annual hostel + mess charges (search official fee notice)
- fees_by_year: provide ONE row per program_type (UG/PG) per academic year for 2023-24, 2024-25, 2025-26
- For Indian colleges: amounts are in INR. For others: local currency.
- If an exact year's fee is unknown, estimate based on ~5-8% annual hike from a known base year.
- DO NOT use USD values for Indian colleges.
- Typical B.Tech fees at private Tamil Nadu colleges: INR 80,000 - 200,000 per year.
""" + _KNOWLEDGE_HINT + """

{
"fees":{
  "UG":{"per_year":null,"total_course":null},
  "PG":{"per_year":null,"total_course":null},
  "hostel_per_year":null
},
"fees_by_year":[
  {"year":"2023-24","program_type":"UG","per_year_inr":null,"total_course_inr":null,"hostel_per_year_inr":null},
  {"year":"2023-24","program_type":"PG","per_year_inr":null,"total_course_inr":null,"hostel_per_year_inr":null},
  {"year":"2024-25","program_type":"UG","per_year_inr":null,"total_course_inr":null,"hostel_per_year_inr":null},
  {"year":"2024-25","program_type":"PG","per_year_inr":null,"total_course_inr":null,"hostel_per_year_inr":null},
  {"year":"2025-26","program_type":"UG","per_year_inr":null,"total_course_inr":null,"hostel_per_year_inr":null},
  {"year":"2025-26","program_type":"PG","per_year_inr":null,"total_course_inr":null,"hostel_per_year_inr":null}
]
}"""

# Batch C3: Scholarships + Infrastructure
BATCH_C3_PROMPT = """Search the web for scholarship and infrastructure details of this college, then return ONLY valid JSON.
Extraction hints:
- scholarships: list EVERY scholarship available to students at this college:
  * College-specific merit/need scholarships
  * State government scholarships (e.g. Tamil Nadu government for Tamil Nadu colleges)
  * Central government: AICTE Pragati, AICTE Saksham, NSP scholarships
  * Management quota fee waivers, sports quota benefits
  amount: descriptive string with actual INR/currency amount (e.g. "INR 50,000/year")
  eligibility: concise condition (e.g. "Top 5% in class; family income < INR 6 Lakhs")
- infrastructure: list EVERY distinct physical facility on campus with accurate details:
  * Library (number of volumes, digital journals, seating)
  * Computer labs (number of systems, software)
  * Hostels (capacity, blocks, amenities)
  * Sports facilities (grounds, indoor courts, gym)
  * Auditorium (seating capacity)
  * Health centre / hospital
  * Canteen / food courts
  * Research labs / centres of excellence
  Search the college website or official brochure for real figures.
""" + _KNOWLEDGE_HINT + """

{
"scholarships":[{"name":"","amount":"","eligibility":""}],
"infrastructure":[{"facility":"","details":""}]
}"""

# ---------------------------------------------------------------------------
# Raw-data patcher — fills values Groq missed using regex on raw snippets
# ---------------------------------------------------------------------------

def _all_snippets(sections: list, *names) -> str:
    """Return concatenated raw snippets for given section names."""
    out = []
    for s in sections:
        if not names or s.get("section") in names:
            for src in s.get("sources", []):
                for snip in src.get("snippets", []):
                    out.append(html.unescape(snip))
    return " ".join(out)

def _first(pattern, text, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def patch_with_raw_data(r1: dict, sections: list) -> dict:
    """Directly extract values that Groq reliably misses."""
    college_name = r1.get("college_name", "")
    # Key tokens of the college name used for contamination detection
    name_tokens = [w.lower() for w in re.split(r'\W+', college_name) if len(w) >= 4]

    rank_txt  = _all_snippets(sections, "Rankings")
    fac_txt   = _all_snippets(sections, "Faculty_Staff")
    stu_txt   = _all_snippets(sections, "Student_Statistics", "Identity")
    place_txt = _all_snippets(sections, "Placement_Yearly_Counts", "Placements_General")
    sec_txt   = _all_snippets(sections, "Sector_Wise_Placements")
    inf_txt   = _all_snippets(sections, "Infrastructure")
    sch_txt   = _all_snippets(sections, "Scholarships")

    # --- Rankings ---
    rankings = r1.get("rankings") or {}
    if not rankings.get("nirf_2025"):
        v = _first(r'NIRF\s*(?:Ranking\s*)?2025[^\d]*?(\d{2,3}(?:-\d{2,3})?)', rank_txt)
        if v: rankings["nirf_2025"] = v
    if not rankings.get("qs_asia_2025"):
        v = _first(r'QS\s*Asia\s*202[45][^\d]*?(\d{3,4}(?:[+-]\d{3,4})?)', rank_txt)
        if v: rankings["qs_asia_2025"] = v
    if not rankings.get("the_world_2024"):
        v = _first(r'(?:THE|Times Higher)[^\d]{0,40}(?:World[^\d]{0,30})?202[34][^\d]*?(\d{3,4}\+?)', rank_txt)
        if v: rankings["the_world_2024"] = v
    # National rank for any country
    if not rankings.get("national_rank") and not rankings.get("india_rank"):
        v = _first(
            r'ranked\s+(\d+)(?:st|nd|rd|th)?\s+in\s+'
            r'(?:Indonesia|India|Malaysia|China|Japan|Thailand|Australia|'
            r'United\s+Kingdom|UK|Germany|France|Canada|Singapore|South\s+Korea)',
            rank_txt, re.IGNORECASE)
        if v: rankings["national_rank"] = v
    r1["rankings"] = rankings

    # Extract edurank-style subject rankings into rankings_history if empty
    rh = r1.get("rankings_history") or []
    if not rh or (len(rh) == 1 and not rh[0].get("rank")):
        subject_matches = re.findall(
            r'"(?:Indonesia|Asia|World)\s+ranking["\s:]+(\d+)"[^}]*"(?:Indonesia|Asia|World)\s+ranking["\s:]+\d+',
            rank_txt, re.IGNORECASE)
        # Alternative: table rows like Indonesia ranking: 3  Asia ranking: 22  World rank: 306
        rows = re.findall(
            r'Indonesia ranking["\s:]+(\d+)["\s,}]+Asia ranking["\s:]+(\d+)["\s,}]+World rank["\s:]+(\d+)',
            rank_txt, re.IGNORECASE)
        for row in rows[:5]:
            rh.append({"year": "2025", "ranking_body": "EduRank",
                       "indonesia_rank": row[0], "asia_rank": row[1], "world_rank": row[2], "score": ""})
        if rh:
            r1["rankings_history"] = rh

    # global_ranking
    gr = r1.get("global_ranking") or {}
    if not gr.get("the_world"):
        gr["the_world"] = rankings.get("the_world_2024", "")
    if not gr.get("qs_world"):
        gr["qs_world"] = rankings.get("qs_world", "")
    r1["global_ranking"] = gr

    # --- Faculty ---
    fac = r1.get("faculty_staff") or {}
    if not fac.get("total_faculty"):
        v = _first(r'(?:total|more than|over)\s*(\d{3,4})\+?\s*(?:teaching\s*staff|faculty)', fac_txt)
        if v: fac["total_faculty"] = int(v)
    # "Now Has 241 Professors" or "Inaugurates 11 Professors, Now Has 241"
    if not fac.get("professors"):
        v = (_first(r'Now\s+Has\s+(\d+)\s+Professors?', fac_txt) or
             _first(r'total\s+of\s+(\d+)\s+Professors?', fac_txt) or
             _first(r'(\d+)\s+Professors?\b', fac_txt))
        if v: fac["professors"] = int(v)
    if not fac.get("associate_professors"):
        v = _first(r'Associate\s*Professors?\s*[:\-]?\s*(\d+)', fac_txt)
        if v: fac["associate_professors"] = int(v)
    if not fac.get("assistant_professors"):
        v = _first(r'Assistant\s*Professors?\s*[:\-]?\s*(\d+)', fac_txt)
        if v: fac["assistant_professors"] = int(v)
    r1["faculty_staff"] = fac

    # --- Student statistics ---
    stu = r1.get("student_statistics") or {}
    if not stu.get("ug_students"):
        v = _first(r'Undergraduates[":\s,|]*?(\d{4,5})', stu_txt + rank_txt)
        if v: stu["ug_students"] = int(v)
    if not stu.get("pg_students"):
        v = _first(r'Postgraduates[":\s,|]*?(\d{3,5})', stu_txt + rank_txt)
        if v: stu["pg_students"] = int(v)
    # topuniversities.com "Total students 30,715" style
    if not stu.get("total_enrollment"):
        v = _first(r'Total\s+students\s+([\d,]+)', stu_txt)
        if v: stu["total_enrollment"] = int(v.replace(",", ""))
    if not stu.get("total_enrollment") and stu.get("ug_students") and stu.get("pg_students"):
        stu["total_enrollment"] = stu["ug_students"] + stu["pg_students"]
    r1["student_statistics"] = stu

    # --- International students ---
    intl = r1.get("international_students") or {}
    if not intl.get("total_count"):
        v = _first(r'International\s+students\s+([\d,]+)', stu_txt)
        if v: intl["total_count"] = int(v.replace(",", ""))
    r1["international_students"] = intl

    # --- Placement contamination guard ---
    # If placement text doesn't mention the college, null out LLM-filled fields
    placement_relevant = any(t in place_txt.lower() for t in name_tokens)
    sector_relevant    = any(t in sec_txt.lower() for t in name_tokens)

    if not placement_relevant:
        print(f"  ⚠  Placement snippets don't mention '{college_name}' — nullifying placement data")
        r1["placements"] = {
            "year": None, "highest_package": None, "average_package": None,
            "median_package": None, "package_currency": None,
            "placement_rate_percent": None,
            "total_students_placed": None, "total_companies_visited": None,
        }
        r1["placement_comparison_last_3_years"] = [
            {"year": y, "highest_package": None, "average_package": None,
             "median_package": None, "package_currency": None,
             "students_placed": None, "placement_rate_percent": None}
            for y in [2023, 2024, 2025]
        ]
        r1["gender_based_placement_last_3_years"] = [
            {"year": y, "male_placed": None, "female_placed": None,
             "male_percent": None, "female_percent": None}
            for y in [2023, 2024, 2025]
        ]
    else:
        # patch missing 2022 year only if data is from the right college
        pc = r1.get("placement_comparison_last_3_years") or []
        existing_years = {str(e.get("year", "")) for e in pc if e.get("year")}
        if "2022" not in existing_years:
            h = _first(r'2022[^:]*highest[^\d]*(\d{2,3}\.?\d*)', place_txt)
            a = _first(r'2022[^:]*(?:average|avg)[^\d]*(\d{1,2}\.?\d*)', place_txt)
            n = _first(r'2022[^:]*(?:students placed|placed)[^\d]*(\d{3,5})', place_txt)
            if h or n:
                pc.append({"year": "2022",
                           "highest_package": float(h) if h else None,
                           "average_package":  float(a) if a else None,
                           "median_package": None,
                           "students_placed": int(n) if n else None,
                           "placement_rate_percent": None})
        r1["placement_comparison_last_3_years"] = pc

    if not sector_relevant:
        r1["sector_wise_placement_last_3_years"] = []
    else:
        sw = r1.get("sector_wise_placement_last_3_years") or []
        sw = [e for e in sw if e.get("sector") or e.get("companies")]
        r1["sector_wise_placement_last_3_years"] = sw

    # --- Infrastructure: only use what was actually scraped ---
    infra = r1.get("infrastructure") or []
    # Remove entries with no details that just came from hardcoded defaults
    infra = [i for i in infra if i.get("facility") and i.get("details")]
    # Try to extract campus area from raw text
    area = _first(r'campus[^.]*?([\d,]+)\s*(?:acres|hectares|sq)', inf_txt)
    if area:
        found = any("campus" in i.get("facility", "").lower() for i in infra)
        if not found:
            infra.append({"facility": "Campus", "details": f"Campus area: {area} acres/hectares"})
    r1["infrastructure"] = infra

    # --- Scholarships: only use what was scraped & relevant ---
    sch = r1.get("scholarships") or []
    sch = [s for s in sch if s.get("name")]
    # Only inject generic defaults for Indian colleges
    is_indian = any(kw in college_name.lower()
                    for kw in ["india", "iit", "nit", "iim", "bits", "vit", "srm",
                               "anna", "kumaraguru", "psg", "kpr"])
    if is_indian and not sch:
        sch = [
            {"name": "Merit Cum Means Scholarship (Central Scheme)",
             "amount": "Variable", "eligibility": "Minority community; family income < Rs. 2.5 Lakhs"},
            {"name": "Central Sector Scheme of Scholarships",
             "amount": "Up to INR 20,000/year", "eligibility": "Scored 80%+ in Class 12; income criteria"},
            {"name": "AICTE Pragati Scholarship",
             "amount": "INR 50,000/year", "eligibility": "Female students; family income < INR 8 Lakhs"},
            {"name": "AICTE Saksham Scholarship",
             "amount": "INR 50,000/year", "eligibility": "Students with disability (PwD)"},
        ]
    # --- Scholarship contamination guard ---
    # If scholarship names don't mention college tokens, they're from a wrong source
    if sch and name_tokens:
        matched = [s for s in sch
                   if any(t in (s.get("name", "") + s.get("eligibility", "")).lower()
                          for t in name_tokens)
                   or is_indian]          # keep all for Indian (generic national schemes OK)
        if not matched:
            print(f"  ⚠  Scholarship snippets don't mention '{college_name}' — clearing scholarships")
            sch = []
    r1["scholarships"] = sch

    # --- Location, Country, About from Identity/About snippets ---
    id_txt = _all_snippets(sections, "Identity")
    ab_txt = _all_snippets(sections, "About")

    if not r1.get("location"):
        v = (_first(r'"Location"\s*:\s*"([^"]+)"', id_txt) or
             _first(r'University\s+in\s+([^,.<"]+(?:,\s*[^,.<"]+)?)', id_txt))
        if v:
            r1["location"] = v.strip()

    if not r1.get("country"):
        # Try explicit "Country" table cell first
        v = _first(r'"Country"\s*:\s*"([^"]+)"', id_txt)
        if not v:
            # "University in Jimbaran, Indonesia" — grab LAST comma token = country
            m = re.search(r'[Uu]niversity\s+in\s+[^,<"\n]+(,\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?))', id_txt)
            if m:
                v = m.group(2)
        if not v:
            # "Short description: University in Bali, Indonesia"
            m = re.search(r'[Uu]niversity\s+in\s+(?:[^,]+,\s*){1}([A-Z][a-zA-Z\s]+?)(?:[.\"<]|$)', id_txt)
            if m:
                v = m.group(1)
        if v:
            r1["country"] = v.strip()

    if not r1.get("about"):
        combined = (ab_txt or "") + " " + (id_txt or "")
        sentences = re.split(r'(?<=[.!?])\s+', combined)
        # Prefer sentences that mention college name tokens
        good = [s.strip() for s in sentences
                if len(s.strip()) > 80
                and not s.strip().startswith('{')
                and not s.strip().startswith('#')
                and not s.strip().startswith('|')
                and any(t in s.lower() for t in name_tokens)]
        if not good:
            good = [s.strip() for s in sentences
                    if len(s.strip()) > 80
                    and not s.strip().startswith('{')
                    and not s.strip().startswith('#')
                    and not s.strip().startswith('|')]
        if good:
            r1["about"] = ' '.join(good[:3])[:600]

    return r1

# ---------------------------------------------------------------------------
# Country / currency helpers
# ---------------------------------------------------------------------------

CITY_TO_COUNTRY = {
    "bali": "Indonesia", "jakarta": "Indonesia", "bandung": "Indonesia",
    "surabaya": "Indonesia", "yogyakarta": "Indonesia", "jimbaran": "Indonesia",
    "denpasar": "Indonesia", "makassar": "Indonesia", "semarang": "Indonesia",
    "kuala lumpur": "Malaysia", "petaling jaya": "Malaysia", "penang": "Malaysia",
    "bangkok": "Thailand", "chiang mai": "Thailand",
    "beijing": "China", "shanghai": "China", "guangzhou": "China",
    "tokyo": "Japan", "osaka": "Japan",
    "seoul": "South Korea", "busan": "South Korea",
    "singapore": "Singapore",
    "sydney": "Australia", "melbourne": "Australia", "brisbane": "Australia",
    "london": "United Kingdom", "manchester": "United Kingdom",
    "paris": "France", "lyon": "France",
    "berlin": "Germany", "munich": "Germany",
    "new york": "USA", "los angeles": "USA", "chicago": "USA",
    "toronto": "Canada", "vancouver": "Canada",
    "mumbai": "India", "delhi": "India", "chennai": "India",
    "bangalore": "India", "hyderabad": "India", "coimbatore": "India",
}

COUNTRY_CURRENCY = {
    "indonesia": ("IDR", "Rp"),
    "india": ("INR", "₹"),
    "united states": ("USD", "$"), "usa": ("USD", "$"),
    "united kingdom": ("GBP", "£"),
    "australia": ("AUD", "A$"),
    "canada": ("CAD", "CA$"),
    "germany": ("EUR", "€"), "france": ("EUR", "€"),
    "china": ("CNY", "¥"), "japan": ("JPY", "¥"),
    "malaysia": ("MYR", "RM"), "singapore": ("SGD", "SGD"),
    "south korea": ("KRW", "₩"), "thailand": ("THB", "฿"),
}

# India-specific fields that are not applicable for foreign colleges
_LPA_FIELDS = {"highest_package_lpa", "average_package_lpa", "median_package_lpa"}
_INDIA_RANK_FIELDS = {"nirf_2025", "nirf_2024", "india_rank"}


def _resolve_currency(country: str, location: str) -> tuple:
    c = (country or "").lower().strip()
    if c in COUNTRY_CURRENCY:
        return COUNTRY_CURRENCY[c]
    loc = (location or "").lower()
    for city, ctry in CITY_TO_COUNTRY.items():
        if city in loc:
            return COUNTRY_CURRENCY.get(ctry.lower(), ("", ""))
    return ("", "")


def _normalize_country(country: str, location: str) -> str:
    if not country:
        return ""
    c_lo = country.lower().strip()
    if c_lo in COUNTRY_CURRENCY:
        return country.title()
    resolved = CITY_TO_COUNTRY.get(c_lo)
    if resolved:
        return resolved
    loc = (location or "").lower()
    for city, ctry in CITY_TO_COUNTRY.items():
        if city in loc:
            return ctry
    return country


def _is_indian_college(final: dict) -> bool:
    name = (final.get("college_name") or "").lower()
    country = (_normalize_country(final.get("country", ""), final.get("location", "")) or "").lower()
    return "india" in country or any(
        kw in name for kw in ["iit", "nit", "iim", "bits", "vit", "srm",
                               "anna", "kumaraguru", "psg", "kpr"])


def finalize_output(final: dict) -> dict:
    """Post-process merged dict: currency, null → meaningful string."""
    # Normalize country first
    final["country"] = _normalize_country(final.get("country", ""), final.get("location", ""))

    is_indian = _is_indian_college(final)
    currency_code, currency_sym = _resolve_currency(final.get("country", ""), final.get("location", ""))
    if not currency_code and is_indian:
        currency_code, currency_sym = "INR", "₹"
    # Last resort: infer country from currency
    if not final.get("country") and currency_code == "IDR":
        final["country"] = "Indonesia"

    final["currency"] = currency_code or "not_available"

    # Stamp currency on fees + rename _inr suffix to _local in fees_by_year
    if currency_code:
        fees = final.get("fees") or {}
        for prog in fees.values():
            if isinstance(prog, dict):
                prog["currency"] = currency_code
        final["fees"] = fees
        new_fby = []
        for entry in (final.get("fees_by_year") or []):
            if not isinstance(entry, dict):
                continue
            renamed = {}
            for k, v in entry.items():
                new_k = k.replace("_inr", "_local")
                renamed[new_k] = v
            renamed["currency"] = currency_code
            new_fby.append(renamed)
        final["fees_by_year"] = new_fby

    # Mark India-specific ranking fields not_applicable for foreign colleges (unconditional)
    rankings = final.get("rankings") or {}
    if not is_indian:
        for fld in _INDIA_RANK_FIELDS:
            rankings[fld] = "not_applicable"
    # Rename india_rank → national_rank if present
    if "national_rank" in rankings or ("india_rank" in rankings and not is_indian):
        final["rankings"] = {k if k != "india_rank" else "national_rank": v
                              for k, v in rankings.items()}
    else:
        final["rankings"] = rankings
    # Empty strings in rankings → not_available
    for k, v in final["rankings"].items():
        if v == "" or v is None:
            final["rankings"][k] = "not_available"

    # global_ranking: empty → not_available
    gr2 = final.get("global_ranking")
    if isinstance(gr2, dict):
        for k in gr2:
            if not gr2[k]:
                gr2[k] = "not_available"

    def _na(val, field=""):
        """null → not_available"""
        if val is not None:
            return val
        return "not_available"

    def _fill_dict(d, fields):
        for f in fields:
            d[f] = _na(d.get(f), f)
        return d

    def _zero_to_na(d, fields):
        """Replace 0 with not_available for fields where 0 is implausible."""
        for f in fields:
            if d.get(f) == 0:
                d[f] = "not_available"
        return d

    # Placements object — unified keys (highest_package / average_package / median_package)
    # package_currency distinguishes unit: "LPA" for Indian, "IDR"/"USD"/etc. for others
    pl = final.get("placements")
    if isinstance(pl, dict):
        _fill_dict(pl, ["highest_package", "average_package", "median_package",
                        "year", "package_currency", "placement_rate_percent",
                        "total_students_placed", "total_companies_visited"])
        # Fix wrong currency: if non-Indian and LLM wrote "USD", replace with local currency
        if not is_indian and pl.get("package_currency") == "USD" and currency_code and currency_code != "USD":
            pl["package_currency"] = currency_code
        # Default package_currency for Indian colleges
        if is_indian and (not pl.get("package_currency") or pl["package_currency"] in ("not_available", "")):
            pl["package_currency"] = "LPA"
        final["placements"] = pl

    # Placement comparison lists
    for list_key, fields in [
        ("placement_comparison_last_3_years",
         ["highest_package", "average_package", "median_package",
          "package_currency", "students_placed", "placement_rate_percent"]),
        ("gender_based_placement_last_3_years",
         ["male_placed", "female_placed", "male_percent", "female_percent"]),
    ]:
        lst = final.get(list_key)
        if isinstance(lst, list):
            # Deduplicate by year (keep last occurrence)
            seen_years, deduped = set(), []
            for e in reversed(lst):
                yr = str(e.get("year", ""))
                if yr and yr not in seen_years:
                    seen_years.add(yr)
                    deduped.insert(0, e)
            lst = deduped
            for entry in lst:
                if isinstance(entry, dict):
                    _fill_dict(entry, fields)
                    # Fix wrong currency per row
                    if not is_indian and entry.get("package_currency") == "USD" and currency_code and currency_code != "USD":
                        entry["package_currency"] = currency_code
                    if is_indian and (not entry.get("package_currency") or
                                      entry["package_currency"] in ("not_available", "")):
                        entry["package_currency"] = "LPA"
            final[list_key] = lst

    # Sector-wise: keep if Groq returned meaningful data, else not_available
    sw = final.get("sector_wise_placement_last_3_years")
    if isinstance(sw, list):
        sw = [e for e in sw if e.get("sector") and
              (e.get("percent") is not None or e.get("companies"))]
        final["sector_wise_placement_last_3_years"] = sw or "not_available"

    # Student statistics
    ss = final.get("student_statistics")
    if isinstance(ss, dict):
        _fill_dict(ss, ["total_enrollment", "ug_students", "pg_students",
                        "phd_students", "annual_intake"])
        _zero_to_na(ss, ["phd_students", "annual_intake"])

    # Faculty
    fac = final.get("faculty_staff")
    if isinstance(fac, dict):
        _fill_dict(fac, ["total_faculty", "phd_faculty_count", "student_faculty_ratio",
                         "professors", "associate_professors", "assistant_professors"])
        _zero_to_na(fac, ["phd_faculty_count", "associate_professors", "assistant_professors"])

    # International students
    intl = final.get("international_students")
    if isinstance(intl, dict):
        _fill_dict(intl, ["total_count", "countries_represented", "nri_students"])
        _zero_to_na(intl, ["total_count", "countries_represented"])
        if not is_indian:
            intl["nri_students"] = "not_applicable"

    # Gender ratio
    gr = final.get("student_gender_ratio")
    if isinstance(gr, dict):
        _fill_dict(gr, ["total_male", "total_female", "male_percent", "female_percent"])

    # Infrastructure: remove entries with no details
    infra = final.get("infrastructure")
    if isinstance(infra, list):
        infra = [i for i in infra if i.get("facility") and i.get("details")]
        final["infrastructure"] = infra if infra else "not_available"

    # Scholarships: remove entries with no name; also filter USD-only entries for non-USD colleges
    sch = final.get("scholarships")
    if isinstance(sch, list):
        sch = [s for s in sch if s.get("name")]
        # If college isn't in a USD country but all scholarships show $ amounts → wrong source
        usd_countries = {"usa", "united states", "canada", "australia", "new zealand"}
        college_country = (final.get("country") or "").lower()
        if college_country not in usd_countries and currency_code not in ("USD", "CAD", "AUD"):
            usd_only = sch and all("$" in (s.get("amount") or "") for s in sch)
            if usd_only:
                print(f"  ⚠  All scholarships use $ amounts for non-USD college — clearing contaminated scholarships")
                sch = []
        final["scholarships"] = sch if sch else "not_available"

    # rankings_history: remove blank template rows
    rh = final.get("rankings_history")
    if isinstance(rh, list):
        rh = [e for e in rh if isinstance(e, dict) and any(
            str(e.get(k, "")).strip() for k in ["year", "ranking_body", "rank", "indonesia_rank", "world_rank"])]
        final["rankings_history"] = rh if rh else "not_available"

    # student_count_comparison: drop blank template rows
    scc = final.get("student_count_comparison_last_3_years")
    if isinstance(scc, list):
        scc = [e for e in scc if e.get("total_enrolled") or e.get("ug")]
        final["student_count_comparison_last_3_years"] = scc or "not_available"

    # Scalar fields
    for k in ["summary", "validation_report", "last_updated", "campus_area",
               "source_url", "about", "location", "country"]:
        if not final.get(k) or final[k] == "":
            final[k] = "not_available"

    if final.get("data_confidence_score") is None:
        final["data_confidence_score"] = "not_available"

    return final


# ---------------------------------------------------------------------------
# Main processor
# ---------------------------------------------------------------------------

def process_audit_with_groq(college_name: str):
    # college_name is passed directly — no audit file needed
    sections = []   # no raw snippets; LLM uses training knowledge only

    print(f"\n🚀 Processing: {college_name} (knowledge-only, no audit)")

    _KB = (
        f"COLLEGE: {college_name}\n\n"
        f"Use your training knowledge about {college_name} to fill ALL fields accurately. "
        f"Numbers must be plain integers or floats (no commas, no symbols). "
        f"Do NOT hallucinate or invent numbers — if genuinely unknown use null."
    )

    # ---- Run all 5 batches in PARALLEL (staggered 2s apart to avoid TPM spike) ----
    batch_specs = [
        ("batchA",  BATCH_A_PROMPT),
        ("batchB",  BATCH_B_PROMPT),
        ("batchC1", BATCH_C1_PROMPT),
        ("batchC2", BATCH_C2_PROMPT),
        ("batchC3", BATCH_C3_PROMPT),
    ]
    results_map = {}
    _wall = time.time()
    STAGGER = 2  # seconds between each thread start

    def _staggered_call(args):
        idx, label, prompt = args
        time.sleep(idx * STAGGER)
        return label, call_groq(prompt, _KB, label)

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_staggered_call, (i, label, prompt)): label
                   for i, (label, prompt) in enumerate(batch_specs)}
        for fut in as_completed(futures):
            label, result = fut.result()
            results_map[label] = result
            print(f"  ✓ {label} done")
    print(f"  ⏱  All batches finished in {time.time()-_wall:.1f}s (parallel)")

    resultA  = results_map.get("batchA")
    resultB  = results_map.get("batchB")
    resultC1 = results_map.get("batchC1")
    resultC2 = results_map.get("batchC2")
    resultC3 = results_map.get("batchC3")

    if not any([resultA, resultB, resultC1, resultC2, resultC3]):
        print("✗ All batches failed.")
        return None

    # ---- Merge A+B results ----
    r1 = {}
    if resultA: r1.update(resultA)
    if resultB: r1.update(resultB)
    r1["college_name"] = college_name

    # ---- Merge all five batches (C1 base, then C2/C3 overlay, then A/B) ----
    def _is_empty(v) -> bool:
        """Return True if value is logically absent (None, "", empty list/dict)."""
        if v is None: return True
        if isinstance(v, str): return v.strip() == ""
        if isinstance(v, (list, dict)): return len(v) == 0
        return False

    def smart_update(base: dict, overlay: dict):
        """Update base with overlay values only when overlay value is non-empty."""
        for k, v in overlay.items():
            if not _is_empty(v):
                base[k] = v

    final = {}
    if resultC1: final.update(resultC1)
    if resultC2: smart_update(final, resultC2)
    if resultC3: smart_update(final, resultC3)
    smart_update(final, r1)   # A+B wins only when they have real data

    # Ensure all keys from the full schema are present
    defaults = {
        "college_name": college_name,
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

    # ---- Final post-processing: currency + null → meaningful strings ----
    final = finalize_output(final)

    # Output path: college_scraper/<slug>_structured.json
    slug = re.sub(r'[^\w]+', '_', college_name.lower()).strip('_')
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"{slug}_structured.json"
    )
    with open(output_file, "w") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved to: {output_file}")
    return final


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python groqbatch.py "College Name"')
    else:
        process_audit_with_groq(sys.argv[1])
