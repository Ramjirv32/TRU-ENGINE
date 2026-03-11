import json
import os
import sys
import re
import html
import time
import concurrent.futures
from groq import Groq
import google.genai as genai
from google.genai import types

GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)

# Gemini config for validation step
GEMINI_API_KEY = "AIzaSyBi8uFkM7rhjtA56DfQGdFpGqFl5hbQni8"
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

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
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0,
                max_tokens=4096,
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
CRITICAL ACCURACY RULES:
1. Return ONLY valid, parseable JSON — no markdown fences, no commentary.
2. ONLY output data that is EXPLICITLY found in the CONTEXT provided — do NOT invent or hallucinate.
3. If a value is NOT in the context and you are NOT confident from your training data, output null.
4. For NUMBER fields: plain integer or float only. No commas, no symbols.
5. NEVER fabricate rankings (QS/THE/NIRF) — if not explicitly mentioned in context, set to null.
6. SANITY CHECKS — reject implausible values:
   - Private engineering college faculty: typically 150-400, NEVER 1000+
   - PhD students at private colleges: typically 20-80, NEVER 500+
   - PhD faculty %: typically 30-50% at private colleges, NEVER 70%+
   - Total enrollment for mid-size private college: 2000-8000
   - Only list programs/departments ACTUALLY mentioned in the context
7. PREFER exact numbers from context over round estimates.
8. If context says "205 Members" for faculty, output 205 — not 350."""

# Batch A: Rankings + Faculty + Students
BATCH_A_PROMPT = """Extract ONLY from the provided CONTEXT. Return valid JSON.
Extraction hints:
- nirf_2025/nirf_2024: ONLY if "NIRF" ranking is explicitly mentioned. Most private colleges are NOT ranked.
- qs_asia_2025/qs_world/the_world_2024: ONLY if explicitly mentioned. Small private colleges are NOT in QS/THE.
  If not found in context → set to null. Do NOT guess ranking bands.
- total_faculty: use EXACT number from context (e.g. "205 Members" → 205). Do NOT inflate.
- phd_faculty_count: only if explicitly stated. If not, estimate 40-50% of total faculty for private colleges.
- student_faculty_ratio: compute from total_students / total_faculty if both known.
- total_enrollment / No. of students: use EXACT number from context.
- phd_students: for private engineering colleges typically 20-80. NEVER output 500+ unless context says so.
- student_count_comparison: use years 2023, 2024, 2025 — null if not in context.
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
BATCH_B_PROMPT = """Extract placement data ONLY from provided CONTEXT. Return valid JSON.
Extraction hints:
- Use years 2023, 2024, 2025 for placement_comparison_last_3_years
- For INDIAN colleges: package in LPA (e.g. 3.52 means 3.52 LPA), package_currency = "LPA"
- Use EXACT figures from context: if context says "Average Package 3.52 LPA" → output 3.52
- If context says "100% Placement Rate" → placement_rate_percent = 100
- Do NOT inflate packages: typical private college avg is 3-6 LPA, NOT 15-20 LPA.
- highest_package: only if explicitly stated in context, else null
- sector_wise: only list companies/sectors ACTUALLY mentioned in context
- If a year's data is not in context, set all fields for that year to null
""" + _KNOWLEDGE_HINT + """

{
"placements":{"year":"2025","highest_package":null,"average_package":null,"median_package":null,"package_currency":"","placement_rate_percent":null,"total_students_placed":null,"total_companies_visited":null},
"placement_comparison_last_3_years":[{"year":"2023","highest_package":null,"average_package":null,"median_package":null,"package_currency":"","students_placed":null,"placement_rate_percent":null},{"year":"2024","highest_package":null,"average_package":null,"median_package":null,"package_currency":"","students_placed":null,"placement_rate_percent":null},{"year":"2025","highest_package":null,"average_package":null,"median_package":null,"package_currency":"","students_placed":null,"placement_rate_percent":null}],
"gender_based_placement_last_3_years":[{"year":"2023","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null},{"year":"2024","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null},{"year":"2025","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null}],
"sector_wise_placement_last_3_years":[{"year":"2025","sector":"","companies":[],"percent":null}]
}"""

# Batch C1: Identity + About + UG / PG / PhD Programs (all as arrays)
BATCH_C1_PROMPT = """Extract data ONLY from provided CONTEXT. Return valid JSON.
Extraction hints:
- college_name: full official name from context
- short_name: abbreviation from context (e.g. "KPRIEnT")
- established: year from context (e.g. 2009)
- institution_type: "Private" or "Public" as stated in context
- location: city and state from context
- country: "India" for Indian colleges
- campus_area: EXACT value from context (e.g. "150 Acres")
- about: 2-3 sentences using ONLY facts from the context (founding year, affiliation, accreditation)
- PROGRAMS: List ONLY programs explicitly mentioned in the context.
  Do NOT invent programs not found in context (e.g. do not add Aerospace if not mentioned).
  Each program must be a separate object with full name (e.g. "B.E. in Computer Science and Engineering")
- PhD programs: list ONLY those explicitly mentioned. Private colleges typically have PhD in 3-5 depts only.
- departments: ONLY those mentioned in context

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
BATCH_C2_PROMPT = """Extract fee data ONLY from provided CONTEXT. Return valid JSON.
Extraction hints:
- fees: extract EXACT per-year and total-course amounts from context as plain numbers
- If context shows specific fee amounts, use those exact numbers
- fees_by_year: one entry per program-type per academic year for 2023-24, 2024-25, 2025-26
- hostel_per_year: annual hostel cost from context
- All monetary values as plain numbers (no currency symbols, no commas, no "INR" prefix)
- If a specific year's fee is NOT in context, use null — do NOT fabricate
- For years without data, estimate ~5% increase from known year, prefix with ~
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
BATCH_C3_PROMPT = """Extract data ONLY from provided CONTEXT. Return valid JSON.
Extraction hints:
- scholarships: list ONLY scholarships explicitly mentioned in context.
  amount: use exact amount from context; eligibility: brief condition from context.
  If context mentions "Post-Metric Scholarship" → include it. Do NOT invent scholarship names.
- infrastructure: list ONLY facilities mentioned in context with EXACT details.
  e.g. context says "Library: 930 sq.mt., 22132 Books, 309 International Journals" → use those exact numbers.
  context says "5 Hostels for Boys, 3 Hostels for Girls" → include exactly that.
  context says "19 Buses" → include transport with that detail.
  Do NOT invent capacity numbers not in context.
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

    # Top recruiters: clean up
    tr = final.get("top_recruiters")
    if isinstance(tr, list):
        tr = [r for r in tr if r.get("company")]
        final["top_recruiters"] = tr if tr else "not_available"
    elif not tr:
        final["top_recruiters"] = "not_available"

    # Accreditations: clean up
    acc = final.get("accreditations")
    if isinstance(acc, list):
        acc = [a for a in acc if a.get("body") or a.get("name")]
        final["accreditations"] = acc if acc else "not_available"
    elif not acc:
        final["accreditations"] = "not_available"

    # Notable faculty: clean up
    nf = final.get("notable_faculty")
    if isinstance(nf, list):
        nf = [f for f in nf if f.get("name")]
        final["notable_faculty"] = nf if nf else "not_available"
    elif not nf:
        final["notable_faculty"] = "not_available"

    # Industry collaborations: clean up
    ic = final.get("industry_collaborations")
    if isinstance(ic, list):
        ic = [c for c in ic if c.get("company")]
        final["industry_collaborations"] = ic if ic else "not_available"
    elif not ic:
        final["industry_collaborations"] = "not_available"

    # Achievements awards: clean up
    aa = final.get("achievements_awards")
    if isinstance(aa, list):
        aa = [a for a in aa if a.get("award")]
        final["achievements_awards"] = aa if aa else "not_available"
    elif not aa:
        final["achievements_awards"] = "not_available"

    # Student clubs: clean up
    sc = final.get("student_clubs_activities")
    if isinstance(sc, list):
        sc = [c for c in sc if c.get("name")]
        final["student_clubs_activities"] = sc if sc else "not_available"
    elif not sc:
        final["student_clubs_activities"] = "not_available"

    # Alumni info
    ai = final.get("alumni_info")
    if not ai or ai == {}:
        final["alumni_info"] = "not_available"

    # Admission process
    ap = final.get("admission_process")
    if not ap or ap == {}:
        final["admission_process"] = "not_available"

    # Research and development
    rd = final.get("research_and_development")
    if not rd or rd == {}:
        final["research_and_development"] = "not_available"

    # Hostel / transport / library sub-objects
    for k in ["hostel_details", "transport_details", "library_details"]:
        v = final.get(k)
        if not v or v == {}:
            final[k] = "not_available"

    # Scalar string fields
    for k in ["summary", "validation_report", "last_updated", "campus_area",
               "source_url", "about", "location", "country", "website",
               "recognition", "placement_highlights", "faculty_achievements",
               "affiliations"]:
        val = final.get(k)
        if not val or val == "" or val == []:
            final[k] = "not_available"

    # contact_info
    ci = final.get("contact_info")
    if not ci or ci == {}:
        final["contact_info"] = "not_available"

    if final.get("data_confidence_score") is None:
        final["data_confidence_score"] = "not_available"

    return final


# ---------------------------------------------------------------------------
# Main processor
# ---------------------------------------------------------------------------

def process_audit_with_groq(filename: str):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    with open(filename, "r") as f:
        audit_data = json.load(f)

    college_name = audit_data.get("college_name", "Unknown")
    sections = audit_data.get("sections", [])

    print(f"\n🚀 Processing: {college_name}")
    print(f"   Sections in audit: {[s.get('section') for s in sections]}\n")

    SLEEP = 1  # seconds between batches (safe minimum for 12k TPM free tier)

    # ---- Batch A: Rankings / Faculty / Students / International ----
    batchA_sections = [
        "Rankings", "Faculty_Staff",
        "Student_Statistics", "Student_Gender_Ratio", "International_Students",
    ]
    ctxA = build_context(sections, batchA_sections, char_limit=6000)
    print(f"📦 Batch A context: {len(ctxA)} chars")
    _t = time.time(); resultA = call_groq(BATCH_A_PROMPT, f"COLLEGE: {college_name}\n\nCONTEXT:\n{ctxA}", "batchA")
    print(f"  ⏱  Batch A took {time.time()-_t:.1f}s")
    print(f"  ⏳ Waiting {SLEEP}s (TPM limit)…"); time.sleep(SLEEP)

    # ---- Batch B: Placements ----
    batchB_sections = [
        "Placements_General", "Placement_Yearly_Counts",
        "Placement_Gender_Stats", "Sector_Wise_Placements",
    ]
    ctxB = build_context(sections, batchB_sections, char_limit=6000)
    print(f"📦 Batch B context: {len(ctxB)} chars")
    _t = time.time(); resultB = call_groq(BATCH_B_PROMPT, f"COLLEGE: {college_name}\n\nCONTEXT:\n{ctxB}", "batchB")
    if resultB is None:
        print("  ↻ No placement data scraped — using LLM knowledge fallback…")
        time.sleep(SLEEP)
        resultB = call_groq(BATCH_B_PROMPT,
            f"COLLEGE: {college_name}\n\nNo web context. Use your training knowledge about {college_name} "
            f"to fill ALL fields with reasonable estimates. Numbers must be plain numbers (no commas, no symbols).",
            "batchB-kb")
    print(f"  ⏱  Batch B took {time.time()-_t:.1f}s")
    print(f"  ⏳ Waiting {SLEEP}s (TPM limit)…"); time.sleep(SLEEP)

    # ---- Batch C1: Identity + About + UG / PG / PhD Programs ----
    batchC1_sections = ["Identity", "About", "UG_Programs", "PG_Programs"]
    ctxC1 = build_context(sections, batchC1_sections, char_limit=6000)
    print(f"📦 Batch C1 context: {len(ctxC1)} chars")
    _t = time.time(); resultC1 = call_groq(BATCH_C1_PROMPT, f"COLLEGE: {college_name}\n\nCONTEXT:\n{ctxC1}", "batchC1")
    print(f"  ⏱  Batch C1 took {time.time()-_t:.1f}s")
    print(f"  ⏳ Waiting {SLEEP}s (TPM limit)…"); time.sleep(SLEEP)

    # ---- Batch C2: Fees by year (last 3 years) ----
    batchC2_sections = ["Fees"]
    ctxC2 = build_context(sections, batchC2_sections, char_limit=6000)
    print(f"📦 Batch C2 context: {len(ctxC2)} chars")
    _t = time.time(); resultC2 = call_groq(BATCH_C2_PROMPT, f"COLLEGE: {college_name}\n\nCONTEXT:\n{ctxC2}", "batchC2")
    if resultC2 is None:
        print("  ↻ No fee data scraped — using LLM knowledge fallback…")
        time.sleep(SLEEP)
        resultC2 = call_groq(BATCH_C2_PROMPT,
            f"COLLEGE: {college_name}\n\nNo web context. Use your training knowledge about {college_name} "
            f"to fill ALL fee fields with reasonable estimates in local currency. "
            f"Numbers must be plain numbers only (no commas, no symbols, no ~ prefix).",
            "batchC2-kb")
    print(f"  ⏱  Batch C2 took {time.time()-_t:.1f}s")
    print(f"  ⏳ Waiting {SLEEP}s (TPM limit)…"); time.sleep(SLEEP)

    # ---- Batch C3: Scholarships + Infrastructure ----
    batchC3_sections = ["Scholarships", "Infrastructure"]
    ctxC3 = build_context(sections, batchC3_sections, char_limit=6000)
    print(f"📦 Batch C3 context: {len(ctxC3)} chars")
    _t = time.time(); resultC3 = call_groq(BATCH_C3_PROMPT, f"COLLEGE: {college_name}\n\nCONTEXT:\n{ctxC3}", "batchC3")
    print(f"  ⏱  Batch C3 took {time.time()-_t:.1f}s")

    if not any([resultA, resultB, resultC1, resultC2, resultC3]):
        print("✗ All batches failed.")
        return None

    # ---- Patch with regex-extracted values from raw audit ----
    # Merge A+B into a combined dict for patching
    r1 = {}
    if resultA: r1.update(resultA)
    if resultB: r1.update(resultB)
    r1["college_name"] = college_name   # ensure name is available for contamination guard
    r1 = patch_with_raw_data(r1, sections)

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
        "accreditations": [], "affiliations": [], "website": "",
        "contact_info": {}, "recognition": "",
        "ug_programs": [], "pg_programs": [], "phd_programs": [],
        "fees": {"UG": {}, "PG": {}}, "fees_by_year": [],
        "hostel_details": {}, "transport_details": {}, "library_details": {},
        "faculty_staff": {}, "placements": {},
        "placement_comparison_last_3_years": [],
        "gender_based_placement_last_3_years": [],
        "sector_wise_placement_last_3_years": [],
        "top_recruiters": [], "placement_highlights": "",
        "student_statistics": {}, "student_gender_ratio": {},
        "student_count_comparison_last_3_years": [],
        "international_students": {},
        "faculty_achievements": "", "notable_faculty": [],
        "infrastructure": [], "scholarships": [],
        "rankings": {}, "rankings_history": [], "global_ranking": {},
        "research_and_development": {}, "industry_collaborations": [],
        "achievements_awards": [], "student_clubs_activities": [],
        "alumni_info": {}, "admission_process": {},
        "sources": [], "source_url": "",
        "summary": "", "validation_report": "", "last_updated": "",
        "data_confidence_score": None,
    }
    for k, v in defaults.items():
        final.setdefault(k, v)

    # ---- Final post-processing: currency + null → meaningful strings ----
    final = finalize_output(final)

    # Output path always beside the input file
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(filename)),
        os.path.basename(filename).replace("_audit.json", "_structured.json")
    )
    with open(output_file, "w") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Groq output saved to: {output_file}")

    # ---- Gemini Validation Step ----
    print(f"\n🔍 Starting Gemini validation & correction…")
    validated = validate_with_gemini(final, sections, college_name)
    if validated:
        with open(output_file, "w") as f:
            json.dump(validated, f, indent=2, ensure_ascii=False)
        print(f"✅ Gemini-validated output saved to: {output_file}")
    else:
        print(f"⚠  Gemini validation failed, keeping Groq output as-is.")

    return validated or final


# ---------------------------------------------------------------------------
# Gemini Validation — parallel section-by-section
# ---------------------------------------------------------------------------

_ANTI_CONTAMINATION_RULES = """
ANTI-CONTAMINATION RULES (CRITICAL — NEVER VIOLATE):
1. ONLY use data explicitly found in the SCRAPED CONTEXT or that you are 100% certain is true for THIS SPECIFIC institution from your training knowledge.
2. NEVER copy patterns from other institutions. Do NOT apply Indian B-school metrics to non-Indian colleges.
3. NEVER use data from generic college ranking portals (Shiksha, Collegedunia) for a different college.
4. COUNTRY AWARENESS:
   - "placement_rate_percent", "highest_package", "average_package", "median_package", "total_students_placed", "total_companies_visited" → these fields use the Indian B-school reporting format. For NON-INDIAN colleges, set ALL of these to "not_applicable" UNLESS the context explicitly uses this format.
   - European/Western universities track "graduate employment rate" (%) through national surveys, NOT campus-drive style placement cells. If the college is NOT in India, set placement fields to "not_applicable" and only record employment_rate_percent if found in context.
5. FEES: If context or your knowledge indicates this is a tuition-free / government-funded institution, set fees to 0 or "free" - do NOT insert random figures.
6. SCHOLARSHIPS: ONLY list scholarships that you know are specifically available TO students of THIS institution. Do NOT paste generic global scholarship lists (Fulbright, Erasmus+ is OK if the college is actually a partner, but ACES/Canadian scholarships → NOT for this college).
7. NUMBERS: Never round-trip plausible-but-invented figures (e.g. exactly 153 placed, 40 companies). If the number is not in context, set to null or "not_available".
8. RETURN null / "not_available" over a plausible fabrication. Accuracy > completeness.
"""

GEMINI_SECTIONS = {
    "identity": {
        "keys": ["college_name", "short_name", "established", "institution_type",
                 "location", "country", "campus_area", "about", "departments",
                 "accreditations", "affiliations", "website", "contact_info",
                 "recognition", "additional_details"],
        "audit_sections": ["Identity", "About"],
        "prompt": """You are an expert college data validator. Given CURRENT DATA (extracted by another AI) and ORIGINAL SCRAPED CONTEXT, correct and enrich the data.

RULES:
- FIX any wrong values using context.
- ENRICH from your training knowledge ONLY for THIS specific institution (name/location specified in the prompt).
- "campus_area": use context value. If not in context but you know it from training, fill it. Otherwise "not_available".
- "about": 2-3 clean factual sentences. Only verified facts.
- "departments": list departments CONFIRMED in context or well-known from training for THIS college.
- "accreditations": list only accreditations you can confirm for this institution.
- "affiliations": confirmed affiliations only.
- "website": official URL if confirmed.
- "contact_info": from context only.
- "additional_details": list of strings with notable verified facts about this college.
""" + _ANTI_CONTAMINATION_RULES + """
RETURN a JSON object with ALL keys. Use "not_available" only when genuinely unknown. No markdown fences."""
    },
    "programs": {
        "keys": ["ug_programs", "pg_programs", "phd_programs"],
        "audit_sections": ["UG_Programs", "PG_Programs", "About"],
        "prompt": """You are an expert college programs validator. Given CURRENT DATA and ORIGINAL SCRAPED CONTEXT, correct and enrich the programs list.

RULES:
- FIX/ADD programs found in context.
- USE your training knowledge to add programs you can CONFIRM this specific college offers.
- Duration: Use standard durations (3 years UG/Bologna, 2 years PG in Europe; 4 years BE/BTech in India).
- Fees: Use CONTEXT values. If the college is government-funded or tuition-free, set fees to 0 or null.
- Seats: Use context values. If not found, set to null — do NOT invent seat counts.
- phd_programs: set to [] if the college does not offer PhDs.
""" + _ANTI_CONTAMINATION_RULES + """
RETURN JSON: {"ug_programs": [...], "pg_programs": [...], "phd_programs": [...]}. No markdown fences."""
    },
    "rankings": {
        "keys": ["rankings", "rankings_history", "global_ranking"],
        "audit_sections": ["Rankings", "About", "Identity"],
        "prompt": """You are an expert college rankings validator. Given CURRENT DATA and ORIGINAL SCRAPED CONTEXT:

RULES:
- FIX any wrong ranking from context.
- Fill rankings you can CONFIRM from your training knowledge for THIS specific institution.
- "nirf_2025", "nirf_2024": → "not_applicable" for all non-Indian colleges.
- "qs_asia_2025": → "not_applicable" for non-Asian colleges.
- For small/regional colleges not in major global rankings → "not_applicable" (NOT "not_available").
- "national_rank": Use country-specific ranking bodies. Only fill if confirmed.
- rankings_history: Only include confirmed ranking entries.
""" + _ANTI_CONTAMINATION_RULES + """
RETURN JSON: {"rankings": {...}, "rankings_history": [...], "global_ranking": {...}}. No markdown fences."""
    },
    "faculty_students": {
        "keys": ["faculty_staff", "student_statistics", "student_gender_ratio",
                 "student_count_comparison_last_3_years", "international_students",
                 "faculty_achievements", "notable_faculty"],
        "audit_sections": ["Faculty_Staff", "Student_Statistics", "Student_Gender_Ratio", "International_Students"],
        "prompt": """You are an expert college statistics validator. Given CURRENT DATA and ORIGINAL SCRAPED CONTEXT:

RULES:
- FIX any wrong statistics using context (use EXACT numbers, e.g. "23 faculty" → 23).
- ENRICH from training knowledge ONLY for THIS specific institution.
- If total_faculty is known, distribute into ranks (Professors 20%, Assoc 30%, Asst 40%, Visiting 10%) marked as approximate.
- If total_enrollment is known, split UG/PG proportionally (65/35 for general; adjust for specialist colleges).
- student_gender_ratio: estimate based on known field composition ONLY if you can confirm the trend for this college.
- international_students: only if confirmed in context or training data.
- annual_intake: estimate ~25-30% of total enrollment only if total enrollment is known.
- notable_faculty: ONLY names you are certain about from training knowledge.
- "nri_students": → "not_applicable" for non-Indian colleges.
""" + _ANTI_CONTAMINATION_RULES + """
RETURN JSON with all keys. No markdown fences."""
    },
    "placements": {
        "keys": ["placements", "placement_comparison_last_3_years",
                 "gender_based_placement_last_3_years", "sector_wise_placement_last_3_years",
                 "top_recruiters", "placement_highlights"],
        "audit_sections": ["Placements_General", "Placement_Yearly_Counts",
                           "Placement_Gender_Stats", "Sector_Wise_Placements"],
        "prompt": """You are an expert employment/placement data validator. Given CURRENT DATA and ORIGINAL SCRAPED CONTEXT:

CRITICAL — COUNTRY-AWARE PLACEMENT FORMAT:
- INDIA only: Use "placement_rate_percent", "highest_package", "average_package", "median_package", "total_students_placed", "total_companies_visited", "package_currency" = "LPA". Fill from context only.
- NON-INDIA (Europe, USA, Australia, etc.): The Indian B-school campus-drive placement format does NOT apply. Set "highest_package", "average_package", "median_package", "total_students_placed", "total_companies_visited", "placement_comparison_last_3_years", "gender_based_placement_last_3_years" → ALL to "not_applicable".
  - Instead, look for "graduate_employment_rate" or "employment_within_X_months" in context. Put that in "placement_highlights" if found.
  - "top_recruiters": Only include if context explicitly names companies that hire from THIS college. Do NOT invent a list.
  - "sector_wise_placement_last_3_years": ONLY if context explicitly has this breakdown. Otherwise "not_applicable".

RULES for INDIA:
- Use EXACT figures from context. Do NOT inflate: typical private college avg 3-6 LPA.
- If context says "100% Placement Rate" → placement_rate_percent = 100.
- If data for a year is missing, set all fields for that year to null — do NOT estimate year-on-year fabrications.
""" + _ANTI_CONTAMINATION_RULES + """
RETURN JSON with all keys. No markdown fences."""
    },
    "fees_schol_infra": {
        "keys": ["fees", "fees_by_year", "scholarships", "infrastructure",
                 "hostel_details", "transport_details", "library_details"],
        "audit_sections": ["Fees", "Scholarships", "Infrastructure"],
        "prompt": """You are an expert college facilities and fees validator. Given CURRENT DATA and ORIGINAL SCRAPED CONTEXT:

RULES:
- FEES: Use EXACT figures from context. If context or training knowledge indicates the college is tuition-free / government-funded, set per_year=0 and add a note. Do NOT invent fee amounts.
- FEES BY YEAR: Only fill years where you have actual data. Do NOT extrapolate fabricated year-on-year figures.
- SCHOLARSHIPS: ONLY include scholarships you can CONFIRM are available to students of THIS specific institution. Do NOT paste a generic list of global scholarships. Erasmus+ is valid for European partner institutions. TNAA/GATE/AICTE scholarships are valid for Indian colleges only.
- INFRASTRUCTURE: Use context values. If context confirms specific facilities (gym, sauna, preschool, distance learning), list them. Do NOT invent capacity numbers.
- LIBRARY: Use context numbers if available. If not, set to "not_available" — do NOT estimate.
- HOSTEL: Use context numbers. If context confirms residential campus, note it. Do NOT invent capacity counts.
""" + _ANTI_CONTAMINATION_RULES + """
RETURN JSON with all keys. No markdown fences."""
    },
    "additional_info": {
        "keys": ["research_and_development", "industry_collaborations", "achievements_awards",
                 "student_clubs_activities", "alumni_info", "admission_process"],
        "audit_sections": ["About", "Identity"],
        "prompt": """You are validating additional college information. Given CURRENT DATA and ORIGINAL SCRAPED CONTEXT:

RULES:
- EXTRACT from context: Research centers, achievements, student activities, notable alumni mentioned.
- ENRICH from training knowledge ONLY for THIS specific institution with confirmed facts.
- research_and_development: Only fill fields for confirmed research activity. Use null for unknown counts.
- industry_collaborations: Only confirmed MoUs/tie-ups for THIS college.
- achievements_awards: Only confirmed awards with year and awarding body.
- student_clubs_activities: Only confirmed clubs/events for THIS college.
- alumni_info.notable_alumni: ONLY names you are CERTAIN attended THIS college.
- admission_process: For INDIAN colleges, list entrance exams (TNEA, JEE, TANCET, GATE, CAT, MAT). For NON-INDIAN colleges, describe the actual admission process (application form, transcripts, etc.) — Indian exam names are "not_applicable".
- "management_quota_percent" and "cutoff_rank_general": "not_applicable" for non-Indian colleges.
- "research_funding_inr": rename to "research_funding" and use local currency for non-Indian colleges.
""" + _ANTI_CONTAMINATION_RULES + """
RETURN JSON with all keys. No markdown fences."""
    },
}


def _call_gemini(prompt: str, label: str, max_retries: int = 3) -> tuple:
    """Call Gemini and return (parsed_dict, elapsed_seconds). Retries on JSON parse errors."""
    t0 = time.time()
    for attempt in range(1, max_retries + 1):
        try:
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You validate and correct structured college data. Return ONLY valid JSON, no markdown fences, no commentary, no trailing text.",
                    temperature=0,
                    max_output_tokens=8192,
                ),
            )
            elapsed = round(time.time() - t0, 2)
            text = resp.text.strip()
            # Strip markdown fences if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            # Aggressive JSON repair
            text = re.sub(r',\s*([}\]])', r'\1', text)           # trailing commas
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)  # control chars (keep \t\n\r)
            # Fix unescaped newlines/tabs inside JSON string values only
            # Replace literal newlines between quotes with \\n
            def _escape_strings(m):
                return m.group(0).replace('\n', '\\n').replace('\r', '').replace('\t', '\\t')
            text = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', _escape_strings, text, flags=re.DOTALL)
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                # Attempt 1: truncate at last valid closing brace
                last_brace = max(text.rfind('}'), text.rfind(']'))
                if last_brace > 0:
                    candidate = text[:last_brace + 1]
                    # Balance open braces
                    open_b = candidate.count('{') - candidate.count('}')
                    open_s = candidate.count('[') - candidate.count(']')
                    candidate += '}' * max(0, open_b) + ']' * max(0, open_s)
                    try:
                        result = json.loads(candidate)
                    except json.JSONDecodeError:
                        raise
                else:
                    raise
            print(f"  ✓ Gemini '{label}' done in {elapsed}s")
            return result, elapsed
        except json.JSONDecodeError as e:
            if attempt < max_retries:
                print(f"  ⚠  Gemini '{label}' JSON error (attempt {attempt}), retrying…")
                continue
            elapsed = round(time.time() - t0, 2)
            print(f"  ✗ Gemini '{label}' failed ({elapsed}s): {e}")
            return None, elapsed
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"  ✗ Gemini '{label}' failed ({elapsed}s): {e}")
            return None, elapsed
    return None, round(time.time() - t0, 2)


def _run_gemini_section(args):
    """Worker for parallel Gemini validation."""
    section_name, section_cfg, current_data, audit_sections, college_name = args
    
    # Build current data subset
    current_subset = {}
    for k in section_cfg["keys"]:
        current_subset[k] = current_data.get(k, "not_available")
    
    # Build audit context
    ctx = build_context(audit_sections, section_cfg["audit_sections"], char_limit=6000)
    
    full_prompt = (
        f"{section_cfg['prompt']}\n\n"
        f"COLLEGE: {college_name}\n\n"
        f"CURRENT DATA:\n{json.dumps(current_subset, indent=2, ensure_ascii=False)}\n\n"
        f"ORIGINAL SCRAPED CONTEXT:\n{ctx}"
    )
    
    print(f"  ↳ Gemini validating '{section_name}'…")
    result, elapsed = _call_gemini(full_prompt, section_name)
    return section_name, result, elapsed


def validate_with_gemini(structured_json: dict, audit_sections: list, college_name: str) -> dict | None:
    """Send structured JSON section-by-section to Gemini for validation. All sections run in parallel."""
    
    validated = dict(structured_json)  # start with a copy
    
    batch_args = []
    for sec_name, sec_cfg in GEMINI_SECTIONS.items():
        batch_args.append((sec_name, sec_cfg, structured_json, audit_sections, college_name))
    
    wall_start = time.time()
    results = {}
    timings = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as ex:
        futures = {ex.submit(_run_gemini_section, arg): arg[0] for arg in batch_args}
        for fut in concurrent.futures.as_completed(futures):
            sec_name, result, elapsed = fut.result()
            results[sec_name] = result
            timings[sec_name] = elapsed
    
    wall_total = round(time.time() - wall_start, 2)
    
    # Merge corrections into validated JSON
    corrections_applied = 0
    for sec_name, result in results.items():
        if result is None or not isinstance(result, dict):
            continue
        for key, value in result.items():
            if key in validated:
                old_val = validated.get(key)
                if value != old_val:
                    validated[key] = value
                    corrections_applied += 1
            else:
                validated[key] = value
    
    print(f"\n⏱  Gemini validation (wall-clock = {wall_total}s, all parallel):")
    for sec_name in GEMINI_SECTIONS:
        t = timings.get(sec_name, "—")
        ok = "✓" if results.get(sec_name) else "✗"
        print(f"   {sec_name}: {t}s  {ok}")
    print(f"   Corrections applied: {corrections_applied} fields updated")
    
    return validated


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audit_processor.py <audit_json_file>")
    else:
        process_audit_with_groq(sys.argv[1])
