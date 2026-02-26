"""
llm/verifier.py – LLM-Powered Data Verification & Correction
==============================================================
Sends scraped college JSON to Groq (Llama 3.3 70B) to:

  1. Fact-check all fields against its training knowledge
  2. Correct inaccurate data (rankings, stats, fees, placements)
  3. Mark estimated vs verified fields
  4. Return a fully corrected JSON

This is the final quality layer that pushes confidence from 64% → 85-90%.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

from groq import Groq


# ── Current year the scraper runs — update when year rolls over ────────────────
CURRENT_YEAR = 2025          # most-recent placement/stats year
STATS_YEARS  = [2023, 2024, 2025]   # the three years we track

SYSTEM_PROMPT = f"""\
You are an expert fact-checker for Indian colleges and universities.

ASSUME THE JSON I GIVE YOU IS COMPLETELY WRONG. Every single field may have
invalid, outdated, or made-up data. Your job is to check and correct ALL fields.

Go through EVERY field one by one:
- college_name, short_name: correct spelling and official name
- location, country: verify city, state
- established: verify founding year from official records
- affiliation: university / autonomous / deemed — correct it
- institution_type: private / government / deemed — correct it
- accreditation: NAAC grade (A, A+, A++, B, etc.), NBA status — use real data
- campus_area: correct acreage
- official_website: correct URL
- global_ranking / rankings: use REAL 2024/2025 NIRF bands, QS, THE ranks —
  if the college appears in NIRF list give exact band/rank; if not write "Not Ranked"
- rankings_history: verify NIRF Engineering, NIRF Overall, QS World, THE for each of
  {STATS_YEARS}. Correct any wrong rank. If a college was not ranked in a year, write
  "Not Ranked".
- departments: correct list of departments that actually exist
- ug_programs, pg_programs, phd_programs: correct programme names that exist
- fees: correct INR fee ranges per year for UG/PG/PhD
- scholarships: correct scholarship names offered
- faculty_staff: correct faculty count, student-faculty ratio
- yearly_statistics: three-year block ({STATS_YEARS[0]}, {STATS_YEARS[1]}, {STATS_YEARS[2]}).
  For EACH year verify and correct:
    total_students, ug_students, pg_students, phd_students,
    male_students, female_students, international_students,
    total_placed, ug_placed, pg_placed, phd_placed,
    placement_rate_ug, average_package, median_package, highest_package, lowest_package
  MATH CHECKS (fix any year that fails):
    • total_students = ug_students + pg_students + phd_students
    • male_students + female_students = total_students
    • total_placed = ug_placed + pg_placed + phd_placed
    • placement_rate_ug = (ug_placed / ug_students) × 100  (round to 2 dp)
    • PhD placed: realistic — typically 30–60 % of PhD batch, or 0 if PhD don't sit campus drives
    • Packages must increase year-over-year (2023 ≤ 2024 ≤ 2025)
    • Mark any number you cannot verify with "_estimated": true
- placements_by_year: summary for each of {STATS_YEARS} with:
    placement_rate, highest_package, median_package, average_package, lowest_package
  Must be consistent with yearly_statistics for each year.
- infrastructure: correct library book count, lab count

RULES:
1. If you KNOW the correct value — replace it
2. If you are NOT 100% sure — keep the value but add "_estimated": true beside it
3. Never leave known-wrong data unchanged
4. Return ONLY valid JSON — no markdown, no explanation outside JSON
5. Keep exact same keys/structure as input
6. The "additional_details" list contains AUTHORITATIVE scraped values per year:
   - "Highest Package (YYYY)" → use this for placements_by_year[YYYY].highest_package
   - "Median CTC (YYYY)"      → use this for placements_by_year[YYYY].median_package
   - "Lowest Package (YYYY)"  → use this for placements_by_year[YYYY].lowest_package
   - "NIRF Ranking (Engineering) YYYY" → use this for rankings_history[YYYY].NIRF Engineering
   - "Established" → use this for the established year
   - "Campus Area"  → use this for campus_area
   Preserve additional_details exactly — NEVER empty it or remove entries.
7. Add at the very end:
   "llm_verified": true,
   "llm_corrections": ["field[year]: old → new (reason)", ...],
   "placement_data_type": "verified" or "estimated"
"""

USER_PROMPT_TEMPLATE = """\
The JSON below has INVALID and INCORRECT data in multiple fields. \
Check every field against your knowledge, correct all wrong values, \
and return the full corrected JSON.

Do NOT trust any value in this JSON — verify each one:

{json_data}

Return ONLY the corrected JSON object. No markdown fences. No explanation text.
"""


class LLMVerifier:
    """
    Send scraped college data to Groq LLM for verification and correction.

    Usage::

        verifier = LLMVerifier(api_key="gsk_...")
        corrected = verifier.verify(scraped_dict)
        # corrected is a dict with llm_verified=True and corrections
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 6000,   # increased — 3-year data is larger
        temperature: float = 0.3,
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = Groq(api_key=self.api_key)

    def verify(self, data: dict) -> dict:
        """
        Send college data to LLM, get corrected version back.

        Returns the corrected dict, or the original with error info
        if the LLM call fails.
        """
        # Strip internal metadata before sending to LLM (save tokens)
        send_data = self._strip_metadata(data)
        json_str = json.dumps(send_data, ensure_ascii=False, indent=2)

        user_msg = USER_PROMPT_TEMPLATE.format(json_data=json_str)

        start_time = time.time()
        max_retries = 4

        for attempt in range(max_retries):
            try:
                # Non-streaming call for JSON response
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=self.temperature,
                    max_completion_tokens=self.max_tokens,
                    top_p=1,
                    stream=False,
                )

                elapsed = round(time.time() - start_time, 2)
                raw_response = completion.choices[0].message.content.strip()

                # Parse the LLM response as JSON
                corrected = self._parse_json_response(raw_response)

                if corrected is None:
                    data["llm_verified"] = False
                    data["llm_error"] = "Failed to parse LLM response as JSON"
                    data["llm_raw_response"] = raw_response[:500]
                    data["llm_processing_time_seconds"] = elapsed
                    return data

                corrected = self._restore_metadata(corrected, data)
                corrected["llm_verified"] = corrected.get("llm_verified", True)
                corrected["llm_processing_time_seconds"] = elapsed
                corrected["llm_model"] = self.model

                print(
                    f"[llm] ✅ {corrected.get('college_name', '?')} verified by {self.model} "
                    f"in {elapsed}s | corrections: {len(corrected.get('llm_corrections', []))}"
                )
                return corrected

            except Exception as exc:
                is_rate_limit = "429" in str(exc) or "rate" in str(exc).lower()
                if is_rate_limit and attempt < max_retries - 1:
                    wait = 30 * (attempt + 1)
                    print(f"[llm] ⏳ Rate limited — retrying in {wait}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait)
                    continue
                elapsed = round(time.time() - start_time, 2)
                print(f"[llm] ❌ LLM verification failed: {exc}")
                data["llm_verified"] = False
                data["llm_error"] = str(exc)
                data["llm_processing_time_seconds"] = elapsed
                return data

    def verify_batch(self, items: list[dict], delay: float = 1.0) -> list[dict]:
        """
        Verify multiple colleges with rate-limiting delay between calls.
        """
        results = []
        for i, item in enumerate(items):
            print(f"[llm] Processing {i+1}/{len(items)}: {item.get('college_name', '?')}")
            result = self.verify(item)
            results.append(result)
            if i < len(items) - 1:
                time.sleep(delay)  # Rate limit
        return results

    @staticmethod
    def _strip_metadata(data: dict) -> dict:
        """Keep only core college fields — strips all pipeline/internal metadata."""
        keep_keys = {
            "college_name", "short_name", "location", "country", "established",
            "affiliation", "institution_type", "accreditation", "campus_area",
            "official_website", "about", "global_ranking", "rankings",
            "rankings_history",          # 3-year ranking history
            "departments", "ug_programs", "pg_programs", "phd_programs",
            "fees", "fees_per_year_inr", "scholarships",
            "faculty_staff", "student_gender_ratio",
            # legacy single-year keys kept for backward compat
            "student_statistics", "placements", "placements_estimated",
            # new 3-year keys
            "yearly_statistics", "placements_by_year",
            "infrastructure", "international_students", "additional_details",
        }
        return {k: v for k, v in data.items() if k in keep_keys}

    @staticmethod
    def _restore_metadata(corrected: dict, original: dict) -> dict:
        """Restore pipeline metadata fields that were stripped before LLM."""
        for key in ("validation_report", "field_confidence", "sources_metadata",
                     "data_confidence_score", "data_version", "last_updated"):
            if key in original and key not in corrected:
                corrected[key] = original[key]
        # Always restore additional_details from original scraped data —
        # LLM must not empty it (it contains authoritative package/ranking values)
        if original.get("additional_details"):
            corrected["additional_details"] = original["additional_details"]
        # If LLM dropped the 3-year blocks, restore them from original
        for multi_key in ("rankings_history", "yearly_statistics", "placements_by_year"):
            if multi_key not in corrected and multi_key in original:
                corrected[multi_key] = original[multi_key]
        return corrected

    @staticmethod
    def _parse_json_response(text: str) -> Optional[dict]:
        """Parse JSON from LLM response, handling markdown fences."""
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            # Remove opening fence
            first_newline = text.index("\n")
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    return None
            return None
