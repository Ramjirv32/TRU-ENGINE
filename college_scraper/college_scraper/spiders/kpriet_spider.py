"""
kpriet_spider.py
================
Targeted spider — scrapes ONLY the KPRIET college page from the local
mock server and writes the result to  output/kpriet.json

Run:
    scrapy crawl kpriet
"""
from __future__ import annotations

from typing import Generator

from scrapy.http import HtmlResponse

from college_scraper.spiders.local_college_spider import LocalCollegeSpider


class KprietSpider(LocalCollegeSpider):
    """
    Inherits all HTML-parsing logic from LocalCollegeSpider.
    Overrides start_urls and parse() so only the KPRIET detail page
    is requested (no listing page needed).
    Output goes to output/kpriet.json via both the pipeline and
    Scrapy's feed exporter.
    """
    name       = "kpriet"
    start_urls = ["http://127.0.0.1:8765/college/kpriet"]
    output_dir = "output"

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 0,
        "CONCURRENT_REQUESTS": 1,
        "LOG_LEVEL": "INFO",
        # Pretty-printed single JSON file for KPRIET
        "FEEDS": {
            "output/kpriet.json": {
                "format": "json",
                "encoding": "utf8",
                "overwrite": True,
                "indent": 2,
            }
        },
    }

    # Jump straight to parse_college — no listing page step needed
    def parse(self, response: HtmlResponse) -> Generator:
        yield from self.parse_college(response)
