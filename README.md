# College Scraper

Scrapes college data from the web and extracts structured information using an LLM (Groq).

## How It Works

```
parallel_audit.py  →  <college>_audit.json  →  audit_processor.py  →  <college>_structured.json
   (Brave API)              (raw data)               (Groq LLM)           (clean JSON)
```

### Step 1 — Scrape (parallel_audit.py)
- Queries the **Brave Search LLM Context API** in parallel for 16 sections
- Sections: Identity, About, UG/PG Programs, Fees, Placements (General / Yearly / Gender / Sector), Rankings, Infrastructure, Faculty, Scholarships, Student Statistics, Gender Ratio, International Students
- Saves raw data as `<college_name>_audit.json`
- Typical scrape time: **~2 seconds** (all 16 sections fetched in parallel)

### Step 2 — Process (audit_processor.py)
- Sends audit data to **Groq (llama-3.3-70b-versatile)** in 3 focused batches:
  - **Batch A** — Rankings, Faculty, Students, Gender Ratio, International Students
  - **Batch B** — Placements (general, yearly, gender, sector-wise)
  - **Batch C** — Identity, Programs, Fees, Scholarships, Infrastructure
- Regex patcher fills any values Groq misses
- Saves structured output as `<college_name>_structured.json`
- Typical LLM time: **~6 seconds** (Groq API) + 30s sleep (free tier TPM limit)

## Timing Summary

| Step | Time |
|------|------|
| Scrape (Brave API, 16 sections parallel) | ~2s |
| LLM Batch A | ~2s |
| Sleep (TPM rate limit) | 15s |
| LLM Batch B | ~2s |
| Sleep (TPM rate limit) | 15s |
| LLM Batch C | ~2s |
| **Total** | **~38s** |

> Note: The 30s of sleep is only required on Groq's **free tier** (12k tokens/minute limit).  
> On a paid plan with higher limits, total time drops to **~8 seconds**.

## Usage

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Scrape a college
python college_scraper/parallel_audit.py "IIT Madras"

# 3. Move audit file to college_scraper/
mv iit_madras_audit.json college_scraper/

# 4. Process through LLM
python college_scraper/audit_processor.py college_scraper/iit_madras_audit.json
```

Output will be saved as `college_scraper/iit_madras_structured.json`.

## Structured Output Schema

```json
{
  "college_name": "",
  "short_name": "",
  "location": "",
  "established": 1959,
  "institution_type": "",
  "campus_area": "",
  "about": "",
  "ug_programs": [{"name": "", "duration": "", "seats": null, "fees_total_inr": null}],
  "pg_programs": [{"name": "", "duration": "", "seats": null, "fees_total_inr": null}],
  "phd_programs": [{"name": "", "duration": "", "seats": null}],
  "fees": {"UG": {"per_year": null, "total_course": null}, "PG": {}, "hostel_per_year": null},
  "rankings": {"nirf_2025": "", "qs_world": "", "the_world_2024": ""},
  "faculty_staff": {"total_faculty": null, "professors": null, "associate_professors": null},
  "student_statistics": {"total_enrollment": null, "ug_students": null, "pg_students": null},
  "student_gender_ratio": {"male_percent": null, "female_percent": null},
  "placements": {"highest_package_lpa": null, "average_package_lpa": null},
  "placement_comparison_last_3_years": [],
  "sector_wise_placement_last_3_years": [],
  "scholarships": [{"name": "", "amount": "", "eligibility": ""}],
  "infrastructure": [{"facility": "", "details": ""}],
  "international_students": {"total_count": null}
}
```

## APIs Used

| API | Purpose | Free Tier |
|-----|---------|-----------|
| [Brave Search LLM Context](https://api.search.brave.com) | Web scraping | 2000 req/month |
| [Groq](https://console.groq.com) | LLM extraction | 100k tokens/day, 12k tokens/min |

## Requirements

```
httpx
groq
```

Install with:
```bash
pip install httpx groq
```

## Files

```
college_scraper/
├── parallel_audit.py              # Step 1: Brave API scraper
├── audit_processor.py             # Step 2: Groq LLM processor
├── iit_madras_audit.json          # Raw scraped data (example)
├── iit_madras_structured.json     # Final structured output (example)
├── psg_college_of_technology_audit.json
├── psg_college_of_technology_structured.json
├── kpr_institute_of_engineering_and_technology_audit.json
└── kpr_institute_of_engineering_and_technology_structured.json
```
# TRU-ENGINE
