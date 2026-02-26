"""
scoring/confidence.py – Data Confidence Score Calculator
=========================================================
Computes a 0.0–1.0 confidence score for each college based on:

  40% – Official website data quality  (Level 1 fields present)
  30% – Ranking verification status     (Level 2 verified sources)
  20% – PDF-verified numbers            (Level 3 placement/stats data)
  10% – Internal consistency            (ValidationEngine score)

Also computes per-field confidence breakdowns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Weight configuration ──────────────────────────────────────────────────────
WEIGHTS = {
    "official_website": 0.40,      # Level 1 static data
    "ranking_verification": 0.30,  # Level 2 rankings
    "pdf_verified": 0.20,          # Level 3 dynamic data
    "internal_consistency": 0.10,  # Validation engine score
}

# Level 1 (official static) fields and their sub-weights
LEVEL1_FIELDS = {
    "college_name":   0.10,
    "location":       0.08,
    "about":          0.08,
    "departments":    0.15,
    "ug_programs":    0.15,
    "pg_programs":    0.12,
    "phd_programs":   0.10,
    "scholarships":   0.07,
    "established":    0.05,
    "campus_area":    0.05,
    "official_website": 0.05,
}

# Level 2 ranking sources
LEVEL2_SOURCES = {
    "nirf_verified":  0.40,
    "qs_verified":    0.30,
    "the_verified":   0.30,
}


@dataclass
class ConfidenceReport:
    """Full confidence breakdown for one college."""
    college_name: str = ""
    overall_score: float = 0.0
    official_website_score: float = 0.0
    ranking_verification_score: float = 0.0
    pdf_verified_score: float = 0.0
    internal_consistency_score: float = 0.0
    field_confidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "breakdown": {
                "official_website_data": {
                    "weight": WEIGHTS["official_website"],
                    "score": self.official_website_score,
                },
                "ranking_verification": {
                    "weight": WEIGHTS["ranking_verification"],
                    "score": self.ranking_verification_score,
                },
                "pdf_verified_numbers": {
                    "weight": WEIGHTS["pdf_verified"],
                    "score": self.pdf_verified_score,
                },
                "internal_consistency": {
                    "weight": WEIGHTS["internal_consistency"],
                    "score": self.internal_consistency_score,
                },
            },
            "field_confidence": self.field_confidence,
        }


class ConfidenceScorer:
    """
    Compute data confidence score for a scraped college item.

    Usage::

        scorer = ConfidenceScorer()
        report = scorer.score(item_dict, validation_score=0.85)
        print(report.overall_score)  # 0.93
    """

    def score(
        self,
        data: dict,
        ranking_data: Optional[dict] = None,
        pdf_data: Optional[dict] = None,
        validation_score: float = 0.0,
    ) -> ConfidenceReport:
        """
        Compute confidence score.

        Args:
            data: The scraped college item dict
            ranking_data: Optional ranking extractor result dict
            pdf_data: Optional PDF extractor result dict
            validation_score: Score from ValidationEngine (0–1)
        """
        report = ConfidenceReport()
        report.college_name = data.get("college_name", "Unknown")

        # ── 40% : Official website data ───────────────────────────────
        l1_score = 0.0
        for fld, weight in LEVEL1_FIELDS.items():
            val = data.get(fld)
            # Check additional_details for established / campus / website
            if fld in ("established", "campus_area", "official_website"):
                val = self._find_in_additional(data, fld)

            if self._field_present(val):
                l1_score += weight
                report.field_confidence[fld] = 1.0
            else:
                report.field_confidence[fld] = 0.0

        report.official_website_score = round(l1_score, 3)

        # ── 30% : Ranking verification ────────────────────────────────
        l2_score = 0.0
        if ranking_data:
            for source, weight in LEVEL2_SOURCES.items():
                if ranking_data.get(source, False):
                    l2_score += weight
        else:
            # If no explicit ranking data, infer from global_ranking field
            ranking_str = data.get("global_ranking", "")
            if "NIRF" in ranking_str and "N/A" not in ranking_str.split("|")[0]:
                l2_score += LEVEL2_SOURCES["nirf_verified"]
            if "QS" in ranking_str and "N/A" not in ranking_str.split("|")[1] if "|" in ranking_str else False:
                l2_score += LEVEL2_SOURCES["qs_verified"]
            if "THE" in ranking_str and "N/A" not in ranking_str.split("|")[-1]:
                l2_score += LEVEL2_SOURCES["the_verified"]

        report.ranking_verification_score = round(l2_score, 3)

        # ── 20% : PDF verified numbers ────────────────────────────────
        l3_score = 0.0
        if pdf_data:
            pdf_conf = pdf_data.get("extraction_confidence", 0.0)
            l3_score = pdf_conf
        else:
            # No PDF data — give partial credit if student stats exist
            stats = data.get("student_statistics", [])
            if len(stats) >= 5:
                l3_score = 0.5   # partial credit for having stats
            if data.get("fees") and len(data["fees"]) >= 4:
                l3_score += 0.2

        report.pdf_verified_score = round(min(l3_score, 1.0), 3)

        # ── 10% : Internal consistency ────────────────────────────────
        report.internal_consistency_score = round(validation_score, 3)

        # ── Overall weighted score ────────────────────────────────────
        report.overall_score = round(
            report.official_website_score * WEIGHTS["official_website"]
            + report.ranking_verification_score * WEIGHTS["ranking_verification"]
            + report.pdf_verified_score * WEIGHTS["pdf_verified"]
            + report.internal_consistency_score * WEIGHTS["internal_consistency"],
            3,
        )

        # ── Per-field confidence for Level 2/3 ────────────────────────
        report.field_confidence["global_ranking"] = 1.0 if l2_score > 0.5 else 0.5
        report.field_confidence["student_statistics"] = 0.7 if l3_score > 0 else 0.3
        report.field_confidence["fees"] = 0.8 if data.get("fees") else 0.0
        report.field_confidence["faculty_staff"] = 0.6 if data.get("faculty_staff") else 0.0
        report.field_confidence["international_students"] = 0.5 if data.get("international_students") else 0.0

        return report

    # ── Helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _field_present(val: Any) -> bool:
        """Check if a field contains meaningful data."""
        if val is None:
            return False
        if isinstance(val, str) and val.strip() in ("", "N/A"):
            return False
        if isinstance(val, list) and len(val) == 0:
            return False
        if isinstance(val, dict) and len(val) == 0:
            return False
        if isinstance(val, (int, float)) and val == 0:
            return False
        return True

    @staticmethod
    def _find_in_additional(data: dict, field_name: str) -> Any:
        """Look up a value from additional_details by fuzzy matching."""
        details = data.get("additional_details", [])
        keywords = {
            "established": "established",
            "campus_area": "campus",
            "official_website": "website",
        }
        kw = keywords.get(field_name, field_name)
        for d in details:
            if isinstance(d, dict) and kw.lower() in d.get("category", "").lower():
                return d.get("value")
        return None
