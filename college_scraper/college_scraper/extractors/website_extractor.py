"""
extractors/website_extractor.py – 🟢 Level 1 Official Website Extractor
=========================================================================
Extracts **static, official data** from a college's own website HTML:

  • Established year
  • Campus area
  • Departments
  • Programme lists (UG / PG / PhD)
  • Scholarships
  • Official website URL

Confidence: 0.95 (data comes from the official source).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from scrapy.http import HtmlResponse


@dataclass
class WebsiteExtractionResult:
    """Structured result from an official website extraction."""
    college_name: str = ""
    location: str = ""
    country: str = "India"
    about: str = ""
    established: str = ""
    campus_area: str = ""
    official_website: str = ""
    departments: list[str] = field(default_factory=list)
    ug_programs: list[str] = field(default_factory=list)
    pg_programs: list[str] = field(default_factory=list)
    phd_programs: list[str] = field(default_factory=list)
    scholarships: list[str] = field(default_factory=list)
    faculty_count: int = 0
    total_students: int = 0
    international_students: int = 0
    male_pct: int = 62
    extraction_confidence: float = 0.0
    raw_fields_found: int = 0
    raw_fields_expected: int = 15
    errors: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        """Compute extraction confidence based on fields successfully found."""
        if self.raw_fields_expected == 0:
            return 0.0
        return round(min(self.raw_fields_found / self.raw_fields_expected, 1.0), 3)

    def to_dict(self) -> dict:
        d = {
            "college_name": self.college_name,
            "location": self.location,
            "country": self.country,
            "about": self.about,
            "established": self.established,
            "campus_area": self.campus_area,
            "official_website": self.official_website,
            "departments": self.departments,
            "ug_programs": self.ug_programs,
            "pg_programs": self.pg_programs,
            "phd_programs": self.phd_programs,
            "scholarships": self.scholarships,
            "faculty_count": self.faculty_count,
            "total_students": self.total_students,
            "international_students": self.international_students,
            "male_pct": self.male_pct,
            "extraction_confidence": self.confidence,
            "errors": self.errors,
        }
        return d


def _clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _int_or_zero(text: Optional[str]) -> int:
    if not text:
        return 0
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


class WebsiteExtractor:
    """
    Extract Level-1 official data from a college detail page (HTML).

    This extractor is designed to work with:
      • The local mock server (CSS selectors matching mock HTML)
      • Any real college website (extensible per-college selector config)
    """

    # Default CSS selectors (matching mock server HTML structure)
    SELECTORS = {
        "name":          "h1.college-heading::text",
        "location":      "span.college-location::text",
        "country":       "span[itemprop='addressCountry']::text",
        "about":         "div.college-about p::text",
        "courses":       "ul.courses-list li span.course-name::text",
        "departments":   "ul.department-list li::text",
        "scholarships":  "div.scholarship-list li::text",
        "total_students":"span.total-students::text",
        "faculty":       "span.faculty-count::text",
        "intl_students": "span.intl-students::text",
        "campus_area":   "span.campus-area::text",
    }

    def extract(self, response: HtmlResponse) -> WebsiteExtractionResult:
        """Run extraction on a single detail page response."""
        result = WebsiteExtractionResult()
        found = 0

        # ── College name ──────────────────────────────────────────────
        name = _clean(response.css(self.SELECTORS["name"]).get())
        if name:
            result.college_name = name
            found += 1
        else:
            result.errors.append("college_name not found")

        # ── Location / Country ────────────────────────────────────────
        loc = _clean(response.css(self.SELECTORS["location"]).get() or "")
        if loc:
            result.location = loc
            found += 1

        country = _clean(response.css(self.SELECTORS["country"]).get() or "India")
        result.country = country
        found += 1

        # ── About ─────────────────────────────────────────────────────
        about = _clean(response.css(self.SELECTORS["about"]).get() or "")
        if about:
            result.about = about
            found += 1

        # ── Additional data attributes ────────────────────────────────
        add = response.css("div#additional-data")
        established = add.attrib.get("data-established", "")
        if established:
            result.established = established
            found += 1

        website = add.attrib.get("data-website", "")
        if website:
            result.official_website = website
            found += 1

        campus = _clean(response.css(self.SELECTORS["campus_area"]).get() or "")
        if campus:
            result.campus_area = campus
            found += 1

        male_pct_raw = add.attrib.get("data-male-pct", "")
        if male_pct_raw:
            result.male_pct = int(male_pct_raw)

        # ── Programmes ────────────────────────────────────────────────
        all_courses = [
            _clean(c) for c in
            response.css(self.SELECTORS["courses"]).getall()
            if _clean(c)
        ]
        result.ug_programs = [
            c for c in all_courses
            if re.search(r"^B[. ]|^B\.Tech|^B\.Sc|^B\.A|^B\.Arch", c)
        ]
        result.pg_programs = [
            c for c in all_courses
            if re.search(r"^M[. ]|^M\.Tech|^MBA|^M\.Sc|^M\.A|^M\.Phil|^M\.E", c)
        ]
        result.phd_programs = [
            c for c in all_courses
            if re.search(r"PhD|Ph\.D|Doctorate", c)
        ]
        if result.ug_programs:
            found += 1
        if result.pg_programs:
            found += 1
        if result.phd_programs:
            found += 1

        # ── Departments ───────────────────────────────────────────────
        result.departments = [
            _clean(d) for d in
            response.css(self.SELECTORS["departments"]).getall()
            if _clean(d)
        ]
        if result.departments:
            found += 1

        # ── Scholarships ──────────────────────────────────────────────
        result.scholarships = [
            _clean(s) for s in
            response.css(self.SELECTORS["scholarships"]).getall()
            if _clean(s)
        ]
        if result.scholarships:
            found += 1

        # ── Numeric stats ─────────────────────────────────────────────
        total = _int_or_zero(response.css(self.SELECTORS["total_students"]).get())
        if total:
            result.total_students = total
            found += 1

        fac = _int_or_zero(response.css(self.SELECTORS["faculty"]).get())
        if fac:
            result.faculty_count = fac
            found += 1

        intl = _int_or_zero(response.css(self.SELECTORS["intl_students"]).get())
        if intl:
            result.international_students = intl
            found += 1

        result.raw_fields_found = found
        result.extraction_confidence = result.confidence
        return result
