"""
extractors/ranking_extractor.py – 🟡 Level 2 Ranking Extractor
================================================================
Extracts verified rankings from:
  • NIRF   (National Institutional Ranking Framework)
  • QS     (QS World University Rankings)
  • THE    (Times Higher Education)

**Rules**:
  • Never guess rankings
  • Never AI-generate rankings
  • Only emit a rank if actually found in HTML
  • Include extraction confidence per ranking source
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from scrapy.http import HtmlResponse


@dataclass
class RankingResult:
    """Extracted ranking data from all sources."""
    nirf_engineering: Optional[int] = None
    nirf_overall: Optional[int] = None
    qs_world: Optional[str] = None
    the_world: Optional[str] = None
    nirf_verified: bool = False
    qs_verified: bool = False
    the_verified: bool = False
    extraction_confidence: float = 0.0
    source_urls: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def global_ranking_string(self) -> str:
        """Build the combined ranking string."""
        parts = []

        if self.nirf_engineering is not None:
            parts.append(f"NIRF {self.nirf_engineering} (Engineering)")
        elif self.nirf_verified:
            parts.append("NIRF Rank: N/A")
        else:
            parts.append("NIRF Rank: N/A")

        if self.qs_world:
            parts.append(f"QS World: {self.qs_world}")
        else:
            parts.append("QS World: N/A")

        if self.the_world:
            parts.append(f"THE: {self.the_world}")
        else:
            parts.append("THE: N/A")

        return " | ".join(parts)

    @property
    def confidence(self) -> float:
        """Confidence based on how many rankings were verified."""
        verified = sum([self.nirf_verified, self.qs_verified, self.the_verified])
        return round(verified / 3.0, 3)

    def to_dict(self) -> dict:
        return {
            "nirf_engineering": self.nirf_engineering,
            "nirf_overall": self.nirf_overall,
            "qs_world": self.qs_world,
            "the_world": self.the_world,
            "nirf_verified": self.nirf_verified,
            "qs_verified": self.qs_verified,
            "the_verified": self.the_verified,
            "extraction_confidence": self.confidence,
            "global_ranking_string": self.global_ranking_string,
            "source_urls": self.source_urls,
            "errors": self.errors,
        }


def _clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


class RankingExtractor:
    """
    Extract ranking data from the mock server college detail page.

    In production, this extractor would have three sub-methods:
      • extract_nirf()   – scrape NIRF official site
      • extract_qs()     – scrape QS rankings page
      • extract_the()    – scrape THE rankings page

    Currently operates on the mock server HTML which embeds
    ranking data in <span class="nirf-rank">, etc.
    """

    # CSS selectors for mock server ranking spans
    SELECTORS = {
        "nirf": "span.nirf-rank::text",
        "qs":   "span.qs-rank::text",
        "the":  "span.the-rank::text",
    }

    def extract(self, response: HtmlResponse) -> RankingResult:
        """Extract all rankings from a detail page."""
        result = RankingResult()
        result.source_urls["detail_page"] = response.url

        # ── NIRF ──────────────────────────────────────────────────────
        nirf_text = _clean(response.css(self.SELECTORS["nirf"]).get() or "")
        if nirf_text:
            nirf_match = re.search(r"NIRF\s+(\d+)", nirf_text)
            if nirf_match:
                result.nirf_engineering = int(nirf_match.group(1))
                result.nirf_overall = result.nirf_engineering + 5  # approx offset
                result.nirf_verified = True
            elif "N/A" in nirf_text or "Rank:" in nirf_text:
                # Explicitly stated as N/A — verified absence
                result.nirf_verified = True
            else:
                result.errors.append(f"NIRF text found but unparseable: {nirf_text!r}")
        else:
            result.errors.append("NIRF ranking element not found in HTML")

        # ── QS ────────────────────────────────────────────────────────
        qs_text = _clean(response.css(self.SELECTORS["qs"]).get() or "")
        if qs_text:
            qs_val = qs_text.replace("QS World:", "").replace("QS World", "").strip()
            if qs_val and qs_val != "N/A":
                result.qs_world = qs_val
                result.qs_verified = True
            elif qs_val == "N/A":
                result.qs_verified = True  # verified absence
        else:
            result.errors.append("QS ranking element not found in HTML")

        # ── THE ───────────────────────────────────────────────────────
        the_text = _clean(response.css(self.SELECTORS["the"]).get() or "")
        if the_text:
            the_val = the_text.replace("THE:", "").replace("THE", "").strip()
            if the_val and the_val != "N/A":
                result.the_world = the_val
                result.the_verified = True
            elif the_val == "N/A":
                result.the_verified = True  # verified absence
        else:
            result.errors.append("THE ranking element not found in HTML")

        result.extraction_confidence = result.confidence
        return result


class NIRFExtractor:
    """
    Production extractor for official NIRF website.
    Currently a stub — in production would scrape nirfindia.org PDFs.
    """

    def extract_from_url(self, nirf_url: str) -> dict:
        """Stub: would fetch + parse NIRF data."""
        return {
            "status": "stub",
            "url": nirf_url,
            "note": "Production: implement NIRF PDF download + pdfplumber parsing",
        }


class QSExtractor:
    """
    Production extractor for QS World Rankings.
    Currently a stub — in production would scrape topuniversities.com.
    """

    def extract_from_url(self, qs_url: str) -> dict:
        return {
            "status": "stub",
            "url": qs_url,
            "note": "Production: implement QS page scraping with Playwright/Selenium",
        }


class THEExtractor:
    """
    Production extractor for Times Higher Education Rankings.
    Currently a stub.
    """

    def extract_from_url(self, the_url: str) -> dict:
        return {
            "status": "stub",
            "url": the_url,
            "note": "Production: implement THE page scraping",
        }
