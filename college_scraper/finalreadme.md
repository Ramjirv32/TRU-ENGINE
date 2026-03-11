# College Data Extractor — `geminni-scarpjson.py`

Two-phase parallel pipeline: **Groq** (fast first-pass) + **Gemini** (quality validation), reconciled field-by-field.

---

## How to Run

```bash
# Single college
python college_scraper/geminni-scarpjson.py "University of Melbourne"

# Indian college
python college_scraper/geminni-scarpjson.py "IIT Madras"

# Any college worldwide
python college_scraper/geminni-scarpjson.py "MIT"
```

**Output file** is saved as:
```
college_scraper/groq_<groq_name>__gemini_<gemini_name>__final_<final_name>.json
```

---

## What it Does

| Phase | Model | Calls | What |
|-------|-------|-------|------|
| Phase 1 | Groq + Gemini (parallel) | 2 | Overview: name, rankings, students, faculty |
| Phase 2 | Groq + Gemini × 6 (parallel) | 12 | Programs, rankings history, placements, fees, student history, identity |
| Reconcile | — | — | Gemini wins all fields except Groq wins course counts |

**Total calls per college: 14** (2 Phase 1 + 12 Phase 2)

---

## Typical Runtime (per college)

| Stage | Time |
|-------|------|
| Phase 1 wall | ~15–17s (Groq: ~2s, Gemini: ~15s) |
| Phase 2 wall | ~22–30s (all 12 calls concurrent) |
| **Total wall** | **~37–47s** |

---

## Cost Estimate for 10,000 Colleges

### Token Usage (per college)

| Call type | Input tokens | Output tokens | Calls |
|-----------|-------------|---------------|-------|
| Phase 1 (each model) | ~1,200 | ~700 | 2 |
| Phase 2 section (each model) | ~450 | ~1,600 | 12 |
| **Total per college** | **~6,600** | **~20,600** | **14** |

---

### Groq — `meta-llama/llama-4-scout-17b-16e-instruct`

| | Rate | Per college | 10,000 colleges |
|-|------|-------------|-----------------|
| Input | $0.11 / 1M tokens | $0.00073 | **$7.26** |
| Output | $0.34 / 1M tokens | $0.00700 | **$70.04** |
| **Total** | | **$0.0077** | **$77.30** |

---

### Gemini — `gemini-2.5-flash`

| | Rate | Per college | 10,000 colleges |
|-|------|-------------|-----------------|
| Input | $0.075 / 1M tokens | $0.00050 | **$4.95** |
| Output | $0.30 / 1M tokens | $0.00618 | **$61.80** |
| **Total** | | **$0.0067** | **$66.75** |

---

### Combined Total

| | Per college | 10,000 colleges |
|-|-------------|-----------------|
| Groq | $0.0077 | $77.30 |
| Gemini | $0.0067 | $66.75 |
| **Grand Total** | **~$0.014** | **~$144** |

> Estimates assume average output lengths. Verbose colleges (large programs list, long fee tables) may run 20–30% higher.

---

### Actual Amount After Free Tier

Free tier gives **35 colleges/day at $0** (Gemini bottleneck).  
Remaining **9,965 colleges** are paid.

| | Free (35 colleges) | Paid (9,965 colleges) | **Total you pay** |
|-|-------------------|----------------------|-------------------|
| Groq | $0 | $76.73 | $76.73 |
| Gemini | $0 | $66.75 | $66.75 |
| **Grand Total** | **$0** | **$143.48** | **~$144** |

> Free tier barely dents 10,000 colleges (only 0.35%). For any serious batch, budget **~$144 total**.

---

### Time for 10,000 Colleges

| Mode | Time |
|------|------|
| Sequential (1 at a time) | ~42s × 10,000 = **~117 hours** |
| 5 colleges concurrent | ~23 hours |
| 10 colleges concurrent | ~12 hours |
| 20 colleges concurrent | ~6 hours |

> Groq rate limit: ~30 req/min on free tier, ~100 req/min on paid.  
> Gemini 2.5 Flash: 10 req/min free, 1000 req/min paid.  
> With paid tiers, 20 concurrent is safe. With free tiers, stick to 2–3 concurrent.

---

## Free Tier Daily Limits

Each college makes **7 Groq calls** + **7 Gemini calls** (1 Phase 1 + 6 Phase 2 each).

### Groq — `meta-llama/llama-4-scout-17b-16e-instruct` (Free)

| Limit | Value | Colleges/day |
|-------|-------|--------------|
| Requests/day (RPD) | ~1,000 req/day | **~142 colleges/day** |
| Requests/min (RPM) | 30 req/min | (rate limit, not daily cap) |
| Tokens/day | ~500,000 tokens/day | ~71 colleges (if token-bound) |

> **Effective free limit: ~70–140 colleges/day on Groq free tier**

### Gemini 2.5 Flash (Free — Google AI Studio)

| Limit | Value | Colleges/day |
|-------|-------|--------------|
| Requests/day (RPD) | 250 req/day | **~35 colleges/day** |
| Requests/min (RPM) | 10 req/min | (rate limit, not daily cap) |

> **Effective free limit: ~35 colleges/day on Gemini free tier**

### Combined Free Tier Bottleneck

| | Daily limit |
|-|-------------|
| Groq alone | ~70–140 colleges |
| Gemini alone | ~35 colleges |
| **Both together (bottleneck = Gemini)** | **~35 colleges/day FREE** |

To process 10,000 colleges on free tiers: **~286 days**  
To process 10,000 colleges on paid tiers: **~6 hours (20 concurrent)**

---

## Output JSON Structure

```
{
  "college_name":         "The University of Melbourne",
  "groq_college_name":    "The University of Melbourne",
  "gemini_college_name":  "The University of Melbourne",
  "final_college_name":   "The University of Melbourne",
  "short_name":           "UniMelb",
  "established":          1853,
  "rankings":             { qs_world, the_world, nirf_2025, ... },
  "student_statistics":   { total_enrollment, ug_students, pg_students, phd_students, ... },
  "faculty_staff":        { total_faculty, student_faculty_ratio, phd_faculty_percent },
  "departments":          [...],
  "programs":             { ug_programs, pg_programs, phd_programs, ... },
  "rankings_history":     [...],
  "placements":           { highest_package, average_package, employment_rate_percent, ... },
  "fees_infra":           { fees, scholarships, infrastructure, hostel_details, ... },
  "student_history":      { student_count_comparison_last_3_years, gender_ratio, ... },
  "identity_details":     { accreditations, affiliations, campus_area, contact_info, ... },
  "_meta":                { timings, models, seconds, ... }
}
```

---

## API Keys (replace before sharing)

```python
GEMINI_API_KEY = "..."   # Google AI Studio — aistudio.google.com
GROQ_API_KEY   = "..."   # Groq Console — console.groq.com
```
