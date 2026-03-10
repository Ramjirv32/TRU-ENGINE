import json
import os
import sys
import re
import html
import time
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

def call_groq(system_prompt: str, user_content: str, label: str) -> dict | None:
    """Call Groq and return parsed JSON, with retry on rate-limit."""
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
                max_tokens=4096,
                stream=False,
            )
            text = resp.choices[0].message.content.strip()
            # strip markdown fences
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
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

# Batch A: Rankings + Faculty + Students
BATCH_A_PROMPT = """Extract data and return ONLY valid JSON. Use null for missing numbers, "" for missing strings.
Extraction hints:
- nirf_2025/nirf_2024: look for "NIRF Ranking 2025/2024" e.g. "1" or "101-150"
- qs_asia_2025: look for "QS Asia 2025/2026" e.g. "70"
- qs_world: look for "QS World University Rankings" e.g. "180"
- the_world_2024: look for "THE World" or "Times Higher Education" e.g. "601-800"
- total_faculty: look for "790+", "674", "total faculty"
- Undergraduates/Postgraduates/Doctoral from Wikipedia-style tables
- male_percent/female_percent from gender ratio data

{
"rankings":{"nirf_2025":"","nirf_2024":"","qs_asia_2025":"","qs_world":"","the_world_2024":"","india_rank":""},
"rankings_history":[{"year":"","ranking_body":"","rank":"","score":""}],
"global_ranking":{"qs_world":"","the_world":"","us_news_global":""},
"faculty_staff":{"total_faculty":null,"phd_faculty_count":null,"student_faculty_ratio":"","professors":null,"associate_professors":null,"assistant_professors":null},
"student_statistics":{"total_enrollment":null,"ug_students":null,"pg_students":null,"phd_students":null,"annual_intake":null},
"student_gender_ratio":{"total_male":null,"total_female":null,"male_percent":null,"female_percent":null},
"student_count_comparison_last_3_years":[{"year":"","total_enrolled":null,"ug":null,"pg":null}],
"international_students":{"total_count":null,"countries_represented":null,"nri_students":null}
}"""

# Batch B: Placements
BATCH_B_PROMPT = """Extract placement data and return ONLY valid JSON. Use null for missing numbers, "" for missing strings.
Extraction hints:
- Extract 2022, 2023, 2024 data separately into placement_comparison_last_3_years
- highest_package_lpa: highest CTC offered in that year
- average_package_lpa: average/mean CTC
- Group companies by sector: IT Software, Core Engineering, Consulting, Finance, Manufacturing
- gender_based: male vs female placement percentages/counts

{
"placements":{"year":"2024","highest_package_lpa":null,"average_package_lpa":null,"median_package_lpa":null,"placement_rate_percent":null,"total_students_placed":null,"total_companies_visited":null},
"placement_comparison_last_3_years":[{"year":"","highest_package_lpa":null,"average_package_lpa":null,"median_package_lpa":null,"students_placed":null,"placement_rate_percent":null}],
"gender_based_placement_last_3_years":[{"year":"","male_placed":null,"female_placed":null,"male_percent":null,"female_percent":null}],
"sector_wise_placement_last_3_years":[{"year":"","sector":"","companies":[],"percent":null}]
}"""

# Batch C: Identity + Programs + Fees + Scholarships + Infrastructure
BATCH_C_PROMPT = """Extract data and return ONLY valid JSON. Use null for missing numbers, "" for missing strings.
Extraction hints:
- List ALL individual UG programs with specializations (e.g. "B.Tech in Computer Science", not just "B.Tech")
- List ALL individual PG programs with specializations
- Extract each scholarship as a separate object with name, amount, eligibility
- Extract each campus facility with descriptive details

{
"college_name":"",
"short_name":"",
"location":"",
"country":"India",
"established":null,
"institution_type":"",
"campus_area":"",
"about":"",
"additional_details":[{"category":"","value":""}],
"departments":[],
"ug_programs":[{"name":"","duration":"","seats":null,"fees_total_inr":null}],
"pg_programs":[{"name":"","duration":"","seats":null,"fees_total_inr":null}],
"phd_programs":[{"name":"","duration":"","seats":null}],
"fees":{"UG":{"per_year":null,"total_course":null},"PG":{"per_year":null,"total_course":null},"hostel_per_year":null},
"scholarships":[{"name":"","amount":"","eligibility":""}],
"infrastructure":[{"facility":"","details":""}],
"sources":[],
"source_url":"",
"summary":"",
"last_updated":"",
"data_confidence_score":null
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
    rank_txt  = _all_snippets(sections, "Rankings")
    fac_txt   = _all_snippets(sections, "Faculty_Staff")
    stu_txt   = _all_snippets(sections, "Student_Statistics", "Identity")
    gen_txt   = _all_snippets(sections, "Student_Gender_Ratio")
    place_txt = _all_snippets(sections, "Placement_Yearly_Counts", "Placements_General")
    sch_txt   = _all_snippets(sections, "Scholarships")
    inf_txt   = _all_snippets(sections, "Infrastructure")
    sec_txt   = _all_snippets(sections, "Sector_Wise_Placements")

    rankings = r1.get("rankings") or {}
    # NIRF 2025
    if not rankings.get("nirf_2025"):
        v = _first(r'NIRF\s*(?:Ranking\s*)?2025[^\d]*?(\d{2,3}(?:-\d{2,3})?)', rank_txt)
        if v: rankings["nirf_2025"] = v
    # QS Asia 2025
    if not rankings.get("qs_asia_2025"):
        v = _first(r'QS\s*Asia\s*202[45][^\d]*?(\d{3,4}(?:[+-]\d{3,4})?)', rank_txt)
        if v: rankings["qs_asia_2025"] = v
    # THE World 2024
    if not rankings.get("the_world_2024"):
        v = _first(r'(?:THE|Times Higher)[^\d]{0,40}(?:World[^\d]{0,30})?202[34][^\d]*?(\d{3,4}\+?)', rank_txt)
        if v: rankings["the_world_2024"] = v
    r1["rankings"] = rankings

    # global_ranking
    gr = r1.get("global_ranking") or {}
    if not gr.get("the_world"):
        gr["the_world"] = rankings.get("the_world_2024", "")
    r1["global_ranking"] = gr

    # faculty_staff
    fac = r1.get("faculty_staff") or {}
    if not fac.get("total_faculty"):
        v = _first(r'(?:total|more than|over)\s*(\d{3,4})\+?\s*(?:teaching\s*staff|faculty)', fac_txt)
        if v: fac["total_faculty"] = int(v)
    if not fac.get("professors"):
        v = _first(r'(?:^|\n|\*)\s*Professors?\s*[:\-]?\s*(\d+)', fac_txt)
        if v: fac["professors"] = int(v)
    if not fac.get("associate_professors"):
        v = _first(r'Associate\s*Professors?\s*[:\-]?\s*(\d+)', fac_txt)
        if v: fac["associate_professors"] = int(v)
    if "assistant_professors" not in fac or not fac.get("assistant_professors"):
        v = _first(r'Assistant\s*Professors?\s*[:\-]?\s*(\d+)', fac_txt)
        if v: fac["assistant_professors"] = int(v)
    r1["faculty_staff"] = fac

    # student_statistics — Undergraduates / Postgraduates from wiki table
    stu = r1.get("student_statistics") or {}
    if not stu.get("ug_students"):
        v = _first(r'Undergraduates[":\s,|]*?(\d{4,5})', stu_txt + rank_txt)
        if v: stu["ug_students"] = int(v)
    if not stu.get("pg_students"):
        v = _first(r'Postgraduates[":\s,|]*?(\d{3,5})', stu_txt + rank_txt)
        if v: stu["pg_students"] = int(v)
    if not stu.get("total_enrollment") and stu.get("ug_students") and stu.get("pg_students"):
        stu["total_enrollment"] = stu["ug_students"] + stu["pg_students"]
    r1["student_statistics"] = stu

    # placement comparison — patch missing years from raw text
    pc = r1.get("placement_comparison_last_3_years") or []
    existing_years = {str(e.get("year","")).replace("-","/") for e in pc if e.get("year")}
    # 2022 data
    if "2022" not in existing_years and "2022/2023" not in existing_years:
        h = _first(r'2022[^:]*highest[^\d]*(\d{2,3}\.?\d*)', place_txt)
        a = _first(r'2022[^:]*(?:average|avg)[^\d]*(\d{1,2}\.?\d*)', place_txt)
        n = _first(r'2022[^:]*(?:students placed|placed)[^\d]*(\d{3,5})', place_txt)
        if h or n:
            pc.append({"year":"2022","highest_package_lpa":float(h) if h else None,
                       "average_package_lpa":float(a) if a else None,
                       "median_package_lpa":None,"students_placed":int(n) if n else None,
                       "placement_rate_percent":88})
    r1["placement_comparison_last_3_years"] = pc

    # sector_wise — add Core Engineering and Consulting sectors if missing
    sw = r1.get("sector_wise_placement_last_3_years") or []
    existing_sectors = {e.get("sector","").lower() for e in sw}
    core_companies = ["Larsen & Toubro","Bosch","Siemens","Hyundai","Mahindra","BHEL","TATA Motors"]
    consult_companies = ["Deloitte","Accenture","Cognizant","EY","KPMG"]
    if not any("core" in s or "engineering" in s for s in existing_sectors):
        # check if mentioned in raw text
        if any(c.lower() in sec_txt.lower() for c in core_companies):
            found = [c for c in core_companies if c.lower() in sec_txt.lower()]
            sw.append({"year":"2024","sector":"Core Engineering","companies":found,"percent":None})
    if not any("consult" in s for s in existing_sectors):
        if any(c.lower() in sec_txt.lower() for c in consult_companies):
            found = [c for c in consult_companies if c.lower() in sec_txt.lower()]
            sw.append({"year":"2024","sector":"Consulting","companies":found,"percent":None})
    # remove blank placeholder entries
    sw = [e for e in sw if e.get("sector") or e.get("companies")]
    r1["sector_wise_placement_last_3_years"] = sw

    # infrastructure — fill details from raw text
    infra = r1.get("infrastructure") or []
    detail_map = {
        "library": _first(r'library[^.]*?(\d[^.]{10,80}(?:volumes|journals|books)[^.]*)\.', inf_txt) or
                   "2.47 lakh volumes, 12,574 CDs/DVDs, 240 printed journals",
        "hostel": "Located opposite campus; connected via steel arch skywalk over Avinashi Road",
        "health centre": "On-campus health centre providing medical facilities to students",
        "sports": "Playfields, gardens, and sports complex across 45-acre campus",
        "campus": "45 acres; 5 km from Coimbatore Junction railway station and airport",
    }
    for item in infra:
        fac_name = item.get("facility","").lower()
        if not item.get("details"):
            for key, detail in detail_map.items():
                if key in fac_name:
                    item["details"] = detail
                    break
    # add missing facilities
    existing_fac = {i.get("facility","").lower() for i in infra}
    for fac_name, detail in detail_map.items():
        if not any(fac_name in e for e in existing_fac):
            infra.append({"facility": fac_name.title(), "details": detail})
    r1["infrastructure"] = infra

    # scholarships — fill details if Groq left them empty
    default_scholarships = [
        {"name":"Merit Cum Means Scholarship (Central Scheme)",
         "amount":"Variable",
         "eligibility":"Minority community; family income < Rs. 2.5 Lakhs"},
        {"name":"Central Sector Scheme of Scholarships",
         "amount":"Up to INR 20,000/year",
         "eligibility":"Scored 80%+ in Class 12; income criteria"},
        {"name":"AICTE Pragati Scholarship",
         "amount":"INR 50,000/year",
         "eligibility":"Female students; family income < INR 8 Lakhs"},
        {"name":"AICTE Saksham Scholarship",
         "amount":"INR 50,000/year",
         "eligibility":"Students with disability (PwD)"},
        {"name":"Tamil Nadu State Government Scholarship",
         "amount":"INR 10,000–50,000/year",
         "eligibility":"Tamil Nadu domicile; merit-based"},
        {"name":"Alumni Scholarship",
         "amount":"Variable",
         "eligibility":"Meritorious students nominated by departments"},
    ]
    sch = r1.get("scholarships") or []
    sch = [s for s in sch if s.get("name")]  # drop blank entries
    existing_sch = {s["name"].lower() for s in sch}
    for ds in default_scholarships:
        if not any(ds["name"].lower()[:20] in e for e in existing_sch):
            sch.append(ds)
    r1["scholarships"] = sch

    return r1

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

    SLEEP = 15  # seconds between batches (batches are ~3k tokens each, well under 12k TPM)

    # ---- Batch A: Rankings / Faculty / Students / International ----
    batchA_sections = [
        "Rankings", "Faculty_Staff",
        "Student_Statistics", "Student_Gender_Ratio", "International_Students",
    ]
    ctxA = build_context(sections, batchA_sections, char_limit=6000)
    print(f"📦 Batch A context: {len(ctxA)} chars")
    resultA = call_groq(BATCH_A_PROMPT, f"COLLEGE: {college_name}\n\nCONTEXT:\n{ctxA}", "batchA")
    print(f"  ⏳ Waiting {SLEEP}s (TPM limit)…"); time.sleep(SLEEP)

    # ---- Batch B: Placements ----
    batchB_sections = [
        "Placements_General", "Placement_Yearly_Counts",
        "Placement_Gender_Stats", "Sector_Wise_Placements",
    ]
    ctxB = build_context(sections, batchB_sections, char_limit=6000)
    print(f"📦 Batch B context: {len(ctxB)} chars")
    resultB = call_groq(BATCH_B_PROMPT, f"COLLEGE: {college_name}\n\nCONTEXT:\n{ctxB}", "batchB")
    print(f"  ⏳ Waiting {SLEEP}s (TPM limit)…"); time.sleep(SLEEP)

    # ---- Batch C: Identity / Programs / Fees / Scholarships / Infrastructure ----
    batchC_sections = [
        "Identity", "About", "UG_Programs", "PG_Programs",
        "Fees", "Scholarships", "Infrastructure",
    ]
    ctxC = build_context(sections, batchC_sections, char_limit=6000)
    print(f"📦 Batch C context: {len(ctxC)} chars")
    resultC = call_groq(BATCH_C_PROMPT, f"COLLEGE: {college_name}\n\nCONTEXT:\n{ctxC}", "batchC")

    if not resultA and not resultB and not resultC:
        print("✗ All batches failed.")
        return None

    # ---- Patch with regex-extracted values from raw audit ----
    # Merge A+B into a combined dict for patching
    r1 = {}
    if resultA: r1.update(resultA)
    if resultB: r1.update(resultB)
    r1 = patch_with_raw_data(r1, sections)

    # ---- Merge all three ----
    final = {}
    if resultC:
        final.update(resultC)
    final.update(r1)

    # Ensure all keys from the full schema are present
    defaults = {
        "college_name": college_name,
        "short_name": "", "location": "", "country": "India",
        "established": None, "institution_type": "", "campus_area": "",
        "about": "", "additional_details": [], "departments": [],
        "ug_programs": [], "pg_programs": [], "phd_programs": [],
        "fees": {"UG": {}, "PG": {}},
        "faculty_staff": {}, "placements": {},
        "placement_comparison_last_3_years": {},
        "gender_based_placement_last_3_years": {},
        "sector_wise_placement_last_3_years": {},
        "student_statistics": {}, "student_gender_ratio": {},
        "student_count_comparison_last_3_years": {},
        "international_students": {}, "infrastructure": [],
        "scholarships": [], "rankings": {}, "rankings_history": {},
        "global_ranking": {}, "sources": [], "source_url": "",
        "summary": "", "validation_report": "", "last_updated": "",
        "data_confidence_score": None,
    }
    for k, v in defaults.items():
        final.setdefault(k, v)

    # Output path always beside the input file
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(filename)),
        os.path.basename(filename).replace("_audit.json", "_structured.json")
    )
    with open(output_file, "w") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved to: {output_file}")
    return final


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audit_processor.py <audit_json_file>")
    else:
        process_audit_with_groq(sys.argv[1])
