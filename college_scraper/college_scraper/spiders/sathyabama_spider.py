from __future__ import annotations
from typing import Generator
from scrapy.http import HtmlResponse
from college_scraper.spiders.local_college_spider import LocalCollegeSpider


class SathyabamaSpider(LocalCollegeSpider):
    name       = "sathyabama"
    start_urls = ["http://127.0.0.1:8765/college/sathyabama"]
    output_dir = "output"

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 0,
        "CONCURRENT_REQUESTS": 1,
        "LOG_LEVEL": "INFO",
        "FEEDS": {
            "output/sathyabama.json": {
                "format": "json",
                "encoding": "utf8",
                "overwrite": True,
                "indent": 2,
            }
        },
    }

    def parse(self, response: HtmlResponse) -> Generator:
        yield from self.parse_college(response)
