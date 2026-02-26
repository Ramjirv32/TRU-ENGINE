"""
Pipelines for the college_scraper project.

3-pipeline architecture:

  1. NormalizationPipeline  (priority 100)
     Normalizes programme/department names, deduplicates

  2. ValidationPipeline     (priority 200)
     Runs ValidationEngine on every item, computes data confidence score
     Attaches validation_report + data_confidence_score to item

  3. CollegeJsonPipeline    (priority 300)
     Serialises each CollegeItem to an individual, pretty-printed JSON file
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import date
from typing import Any

from itemadapter import ItemAdapter

from college_scraper.validators.engine import ValidationEngine
from college_scraper.validators.normalizer import normalize_college_data
from college_scraper.scoring.confidence import ConfidenceScorer


def _slugify(text: str) -> str:
    """Return a filesystem-safe slug for *text*."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "_", text)


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline 1: Normalization (priority 100)
# ═══════════════════════════════════════════════════════════════════════════════
class NormalizationPipeline:
    """Normalize all programme/department names and deduplicate."""

    @classmethod
    def from_crawler(cls, crawler: Any) -> "NormalizationPipeline":
        return cls()

    def process_item(self, item: Any) -> Any:
        adapter = ItemAdapter(item)
        data = dict(adapter)
        normalized = normalize_college_data(data)

        # Write normalised values back to the item
        for key in ("ug_programs", "pg_programs", "phd_programs", "departments"):
            if key in normalized:
                item[key] = normalized[key]

        return item


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline 2: Validation + Confidence Scoring (priority 200)
# ═══════════════════════════════════════════════════════════════════════════════
class ValidationPipeline:
    """
    Run 7 validation rules + compute data confidence score.
    Attaches metadata fields to each item before JSON serialisation.
    """

    def __init__(self) -> None:
        self.engine = ValidationEngine()
        self.scorer = ConfidenceScorer()
        self.stats: dict[str, int] = {
            "total": 0, "passed": 0, "warnings": 0, "errors": 0,
        }

    @classmethod
    def from_crawler(cls, crawler: Any) -> "ValidationPipeline":
        return cls()

    def process_item(self, item: Any) -> Any:
        adapter = ItemAdapter(item)
        data = dict(adapter)

        # ── Validate ──────────────────────────────────────────────────
        report = self.engine.validate(data)
        item["validation_report"] = report.to_dict()

        # ── Confidence score ──────────────────────────────────────────
        conf = self.scorer.score(
            data,
            validation_score=report.validation_score,
        )
        item["data_confidence_score"] = conf.overall_score
        item["field_confidence"] = conf.to_dict().get("field_confidence", {})

        # ── Data versioning ───────────────────────────────────────────
        item["data_version"] = "2026.1"
        item["last_updated"] = str(date.today())
        item["manual_verified"] = False

        # ── Source metadata ───────────────────────────────────────────
        item["sources_metadata"] = {
            "mock_server": {
                "url": data.get("source_url", ""),
                "status": "extracted",
            },
            "nirf_official": {"url": "", "status": "not_scraped"},
            "qs_official": {"url": "", "status": "not_scraped"},
            "the_official": {"url": "", "status": "not_scraped"},
            "placement_pdf": {"url": "", "status": "not_parsed"},
        }

        # ── Stats tracking ────────────────────────────────────────────
        self.stats["total"] += 1
        if report.error_count == 0:
            self.stats["passed"] += 1
        if report.warning_count > 0:
            self.stats["warnings"] += 1
        if report.error_count > 0:
            self.stats["errors"] += 1

        # Log validation result
        emoji = "✅" if report.error_count == 0 else "⚠️" if report.warning_count > 0 else "❌"
        print(
            f"[validation] {emoji} {data.get('college_name', '?')} | "
            f"score: {report.validation_score} | "
            f"confidence: {conf.overall_score} | "
            f"{report.summary}"
        )

        return item

    def close_spider(self) -> None:
        print(
            f"\n[validation] ═══ SUMMARY ═══\n"
            f"  Total:    {self.stats['total']}\n"
            f"  Passed:   {self.stats['passed']}\n"
            f"  Warnings: {self.stats['warnings']}\n"
            f"  Errors:   {self.stats['errors']}\n"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline 3: JSON Serialisation (priority 300)
# ═══════════════════════════════════════════════════════════════════════════════
class CollegeJsonPipeline:
    """Write each college item as a separate pretty-printed JSON file."""

    @classmethod
    def from_crawler(cls, crawler: Any) -> "CollegeJsonPipeline":
        instance = cls()
        instance.output_dir = crawler.settings.get("OUTPUT_DIR", "output")
        return instance

    def open_spider(self) -> None:  # type: ignore[override]
        os.makedirs(self.output_dir, exist_ok=True)

    def process_item(self, item: Any) -> Any:  # type: ignore[override]
        adapter = ItemAdapter(item)
        data = dict(adapter)

        college_name: str = data.get("college_name") or "unknown_college"
        filename = _slugify(college_name) + ".json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

        print(f"[pipeline] Saved: {college_name}  →  {filepath}")
        return item
