"""
sources/collector.py – Layer 1: Source Collector
=================================================
For each college, collects and stores all known data-source URLs:

  • official_site   – university homepage
  • nirf_url        – NIRF profile/ranking page
  • qs_url          – QS ranking page
  • placement_pdf   – latest placement report PDF link
  • annual_report   – annual report PDF link

The collector acts as the **single source of truth** for where data
should be fetched from.  Extractors (Layer 2) only operate on URLs
provided by the collector — never on arbitrary/blog sources.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Optional


@dataclass
class CollegeSource:
    """One college's verified data-source URLs."""
    slug: str
    name: str
    official_site: str = ""
    nirf_url: str = ""
    qs_url: str = ""
    the_url: str = ""
    placement_pdf: str = ""
    annual_report_pdf: str = ""
    mock_server_url: str = ""          # for local dev / testing
    source_verified_date: str = ""     # ISO date of last manual check
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CollegeSource":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class SourceCollector:
    """
    Manages a JSON database of college data sources.

    Usage::

        sc = SourceCollector("sources_db.json")
        sc.add(CollegeSource(
            slug="iit-madras",
            name="IIT Madras",
            official_site="https://www.iitm.ac.in",
            nirf_url="https://nirfindia.org/...",
        ))
        sc.save()

        # Later, get sources for scraping:
        for src in sc.all():
            print(src.official_site, src.nirf_url)
    """

    def __init__(self, db_path: str = "sources_db.json") -> None:
        self.db_path = db_path
        self._sources: dict[str, CollegeSource] = {}
        if os.path.exists(db_path):
            self._load()

    # ── persistence ───────────────────────────────────────────────────────
    def _load(self) -> None:
        with open(self.db_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for entry in raw:
            cs = CollegeSource.from_dict(entry)
            self._sources[cs.slug] = cs

    def save(self) -> None:
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(
                [s.to_dict() for s in self._sources.values()],
                f, ensure_ascii=False, indent=2,
            )

    # ── CRUD ──────────────────────────────────────────────────────────────
    def add(self, source: CollegeSource) -> None:
        self._sources[source.slug] = source

    def get(self, slug: str) -> Optional[CollegeSource]:
        return self._sources.get(slug)

    def all(self) -> list[CollegeSource]:
        return list(self._sources.values())

    def count(self) -> int:
        return len(self._sources)

    def remove(self, slug: str) -> None:
        self._sources.pop(slug, None)

    # ── Bulk populate from mock server data ───────────────────────────────
    def populate_from_mock_data(self, colleges: list[dict],
                                 mock_base: str = "http://127.0.0.1:8765") -> int:
        """
        Import college records from the mock_server data.py list and
        set mock_server_url + official_site.  Returns count added.
        """
        added = 0
        for c in colleges:
            slug = c["slug"]
            if slug not in self._sources:
                self._sources[slug] = CollegeSource(
                    slug=slug,
                    name=c["name"],
                    official_site=c.get("website", ""),
                    mock_server_url=f"{mock_base}/college/{slug}",
                    source_verified_date=str(date.today()),
                )
                added += 1
            else:
                # update mock URL if missing
                if not self._sources[slug].mock_server_url:
                    self._sources[slug].mock_server_url = f"{mock_base}/college/{slug}"
        return added

    # ── Generate NIRF / QS placeholder URLs ──────────────────────────────
    def generate_ranking_urls(self) -> None:
        """
        For every college in the DB, generate the NIRF and QS lookup URL.
        In production, these would be verified manually or via a search API.
        """
        for src in self._sources.values():
            slug_clean = src.slug.replace("-", "+")
            if not src.nirf_url:
                src.nirf_url = (
                    f"https://www.nirfindia.org/Rankings/"
                    f"?searchVal={slug_clean}"
                )
            if not src.qs_url:
                src.qs_url = (
                    f"https://www.topuniversities.com/universities/"
                    f"{src.slug}"
                )
            if not src.the_url:
                src.the_url = (
                    f"https://www.timeshighereducation.com/world-university-rankings/"
                    f"{src.slug}"
                )
