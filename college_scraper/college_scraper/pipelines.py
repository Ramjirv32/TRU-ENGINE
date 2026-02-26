"""
Pipelines for the college_scraper project.

CollegeJsonPipeline
    Serialises each CollegeItem to an individual, pretty-printed JSON file
    named after the college (e.g.  output/iit_bombay.json).
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any

from itemadapter import ItemAdapter


def _slugify(text: str) -> str:
    """Return a filesystem-safe slug for *text*."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "_", text)


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
