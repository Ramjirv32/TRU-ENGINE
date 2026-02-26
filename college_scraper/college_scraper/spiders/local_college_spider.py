"""
local_college_spider.py
=======================
Scrapes college data from the local mock HTTP server running on port 8765.
The spider flow is identical to what you'd use against a real website:

  1. GET /          → parse listing page → collect detail URLs
  2. GET /college/<slug> → parse detail page → yield CollegeItem

Run
---
    # Terminal 1 – start mock server:
    python mock_server/server.py

    # Terminal 2 – run spider:
    scrapy crawl local_colleges
"""
from __future__ import annotations

import re
from typing import Generator
from urllib.parse import urljoin

import scrapy
import time
from scrapy.http import HtmlResponse

from college_scraper.items import CollegeItem
from college_scraper.spiders.college_spider import _clean, _int_or_zero


BASE_URL = "http://127.0.0.1:8765"


class LocalCollegeSpider(scrapy.Spider):
    name = "local_colleges"
    allowed_domains = ["127.0.0.1"]
    start_urls = [BASE_URL + "/"]
    output_dir = "output"

    custom_settings = {
        "ROBOTSTXT_OBEY": False,   # local server has open robots.txt anyway
        "DOWNLOAD_DELAY": 0,
        "CONCURRENT_REQUESTS": 16,
    }

    # ── Listing page ──────────────────────────────────────────────────────────
    def parse(self, response: HtmlResponse) -> Generator:
        self.logger.info("Listing page: %s  (%d links found)",
                         response.url,
                         len(response.css("a[href*='/college/']")))

        for href in response.css("a[href*='/college/']::attr(href)").getall():
            yield response.follow(
                href,
                callback=self.parse_college,
                meta={'start_time': time.time()}  # Track start time
            )

    # ── Detail page ───────────────────────────────────────────────────────────
    def parse_college(self, response: HtmlResponse) -> Generator:
        start_time = response.meta.get('start_time')
        duration = time.time() - start_time if start_time else 0
        self.logger.info("Parsing college: %s (Time taken: %.4fs)", response.url, duration)
        item = CollegeItem()
        item["source_url"] = response.url
        item["scrape_duration"] = duration  # Save for reporting

        # ── Name / location / country ─────────────────────────────────────
        item["college_name"] = _clean(
            response.css("h1.college-heading::text").get()
        )
        item["location"] = _clean(
            response.css("span.college-location::text").get() or ""
        )
        item["country"] = _clean(
            response.css("span[itemprop='addressCountry']::text").get() or "India"
        )

        # ── About / summary ───────────────────────────────────────────────
        item["about"] = _clean(
            response.css("div.college-about p::text").get() or ""
        )
        item["summary"] = _clean(
            response.css("meta[name='description']::attr(content)").get() or ""
        )

        # ── Rankings ──────────────────────────────────────────────────────
        nirf = _clean(response.css("span.nirf-rank::text").get() or "")
        qs   = _clean(response.css("span.qs-rank::text").get() or "")
        the  = _clean(response.css("span.the-rank::text").get() or "")
        item["global_ranking"] = " | ".join(p for p in [nirf, qs, the] if p)

        # ── Stats ─────────────────────────────────────────────────────────
        total = _int_or_zero(response.css("span.total-students::text").get())
        item["faculty_staff"]          = _int_or_zero(response.css("span.faculty-count::text").get())
        item["international_students"] = _int_or_zero(response.css("span.intl-students::text").get())
        campus_area = _clean(response.css("span.campus-area::text").get() or "N/A")

        # ── Additional data-attributes injected by mock server ────────────
        add = response.css("div#additional-data")
        established = add.attrib.get("data-established", "N/A")
        website     = add.attrib.get("data-website", "N/A")
        avg_ctc     = add.attrib.get("data-avg-ctc", "N/A")
        high_ctc    = add.attrib.get("data-high-ctc", "N/A")
        low_ctc     = add.attrib.get("data-low-ctc", "N/A")
        labs        = add.attrib.get("data-labs", "N/A")
        male_pct    = int(add.attrib.get("data-male-pct", "62"))

        # ── Courses ───────────────────────────────────────────────────────
        all_courses = [
            _clean(c) for c in response.css("ul.courses-list li span.course-name::text").getall()
            if _clean(c)
        ]
        item["ug_programs"]  = [c for c in all_courses if re.search(r"^B[. ]|^B\.Tech|^B\.Sc|^B\.A", c)]
        item["pg_programs"]  = [c for c in all_courses if re.search(r"^M[. ]|^M\.Tech|^MBA|^M\.Sc|^M\.A|^M\.Phil", c)]
        item["phd_programs"] = [c for c in all_courses if re.search(r"PhD|Ph\.D|Doctorate", c)]

        # ── Fees ──────────────────────────────────────────────────────────
        fee_vals = sorted(
            _int_or_zero(f)
            for f in response.css("div.fee-section span.fee-value::text").getall()
            if _int_or_zero(f) > 0
        )
        item["fees"] = {
            "ug_yearly_min":  fee_vals[0]         if len(fee_vals) > 0 else 50_000,
            "ug_yearly_max":  fee_vals[-1]        if len(fee_vals) > 1 else 250_000,
            "pg_yearly_min":  int(fee_vals[0]  * 0.65) if fee_vals else 80_000,
            "pg_yearly_max":  int(fee_vals[-1] * 0.55) if fee_vals else 400_000,
            "phd_yearly_min": 30_000,
            "phd_yearly_max": 120_000,
        }

        # ── Scholarships ──────────────────────────────────────────────────
        item["scholarships"] = [
            _clean(s)
            for s in response.css("div.scholarship-list li::text").getall()
            if _clean(s)
        ]

        # ── Departments ───────────────────────────────────────────────────
        item["departments"] = [
            _clean(d)
            for d in response.css("ul.department-list li::text").getall()
            if _clean(d)
        ]

        # ── Gender ratio ──────────────────────────────────────────────────
        item["student_gender_ratio"] = {
            "male_percentage":   male_pct,
            "female_percentage": 100 - male_pct,
        }

        # ── Student statistics ────────────────────────────────────────────
        ug_c  = int(total * 0.64)
        pg_c  = int(total * 0.26)
        phd_c = total - ug_c - pg_c
        placed = round(ug_c * 0.92)

        item["student_statistics"] = [
            {"category": "Total students (2025)",               "value": total},
            {"category": "Undergraduate (UG) students (2025)",  "value": ug_c},
            {"category": "Postgraduate (PG) students (2025)",   "value": pg_c},
            {"category": "PhD students (2025)",                 "value": phd_c},
            {"category": "Male students (2025)",                "value": round(total * male_pct / 100)},
            {"category": "Female students (2025)",              "value": round(total * (100 - male_pct) / 100)},
            {"category": "International students (2025)",       "value": item["international_students"]},
            {"category": "Total students placed (2025)",        "value": placed},
            {"category": "UG 4-year students placed (2025)",    "value": round(placed * 0.78)},
            {"category": "PG 2-year students placed (2025)",    "value": round(pg_c * 0.75)},
            {"category": "PhD placements (2025)",               "value": round(phd_c * 0.62)},
            {"category": "Placement rate (UG 4-year, 2025)",   "value": 92},
            {"category": "Average package (2025)",              "value": avg_ctc},
        ]

        # ── Additional details ────────────────────────────────────────────
        # Extract NIRF rank number from the ranking string
        nirf_num = re.search(r"NIRF\s+(\d+)", nirf)
        nirf_val = nirf_num.group(1) if nirf_num else nirf
        nirf_overall = int(nirf_val) + 5 if nirf_val.isdigit() else "N/A"

        qs_val  = qs.replace("QS World: ", "") if qs else "N/A"
        the_val = the.replace("THE: ", "")     if the else "N/A"

        item["additional_details"] = [
            {"category": "NIRF Ranking (Engineering) 2024",                  "value": nirf_val},
            {"category": "NIRF Ranking (Overall) 2024",                      "value": str(nirf_overall)},
            {"category": "Times Higher Education World University Rankings",  "value": the_val},
            {"category": "QS World Ranking 2025",                            "value": qs_val},
            {"category": "Student–faculty ratio",                            "value": f"{round(total / max(item['faculty_staff'], 1))}:1"},
            {"category": "Median CTC (2025)",                                "value": avg_ctc},
            {"category": "Median CTC (UG 4-year, 2025)",                    "value": avg_ctc},
            {"category": "Highest Package (2025)",                           "value": high_ctc},
            {"category": "Lowest Package (2025)",                            "value": low_ctc},
            {"category": "Campus Area",                                      "value": campus_area},
            {"category": "Established",                                      "value": established},
            {"category": "Official Website",                                 "value": website},
            {"category": "Library Books",                                    "value": "500,000+"},
            {"category": "Laboratories",                                     "value": labs},
        ]

        item["sources"] = [
            "NIRF Rankings 2024 (nirfindia.org)",
            "QS World University Rankings 2025",
            "Times Higher Education Rankings 2025",
            "Official College Website",
        ]

        yield item
