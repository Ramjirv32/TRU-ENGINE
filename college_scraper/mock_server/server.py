"""
mock_server/server.py
=====================
Lightweight stdlib HTTP server that serves college detail pages as HTML.
The Scrapy spider scrapes these pages just as it would a real website.

Usage (runs in background; college_scraper/run.py starts it automatically):
    python mock_server/server.py --port 8765
"""
from __future__ import annotations

import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Import our data – when run from the project root this path resolves correctly
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from data import COLLEGES

PORT = 8765
_COLLEGE_MAP = {c["slug"]: c for c in COLLEGES}


# ── HTML templates ────────────────────────────────────────────────────────────

def _college_html(college: dict) -> str:
    """Render a single college dict as an HTML page the spider can parse."""

    def _li(items: list) -> str:
        return "".join(f"<li>{html.escape(str(i))}</li>" for i in items)

    fees = college
    scholarships_html = _li(college.get("scholarships", []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
  <title>{html.escape(college['name'])}</title>
  <meta name="description" content="{html.escape(college['about'][:150])}">
</head>
<body>
  <h1 class="college-heading">{html.escape(college['name'])}</h1>
  <span class="college-location">{html.escape(college['location'])}</span>
  <span itemprop="addressCountry">India</span>

  <div class="college-about">
    <p>{html.escape(college['about'])}</p>
  </div>

  <!-- Rankings -->
  <div class="ranking-box">
    <span class="nirf-rank">{('NIRF ' + str(college['nirf']) + ' (Engineering)') if college['nirf'] not in (None, 'N/A') else 'NIRF Rank: N/A'}</span>
    <span class="qs-rank">QS World: {html.escape(college['qs'])}</span>
    <span class="the-rank">THE: {html.escape(college['the'])}</span>
  </div>

  <!-- Stats widget -->
  <span class="total-students">{college['total_students']}</span>
  <span class="faculty-count">{college['faculty']}</span>
  <span class="intl-students">{college['intl']}</span>
  <span class="campus-area">{html.escape(college['campus'])}</span>

  <!-- Courses -->
  <ul class="courses-list">
    {''.join(f'<li><span class="course-name">{html.escape(c)}</span></li>' for c in college['ug_programs'])}
    {''.join(f'<li><span class="course-name">{html.escape(c)}</span></li>' for c in college['pg_programs'])}
    {''.join(f'<li><span class="course-name">{html.escape(c)}</span></li>' for c in college['phd_programs'])}
  </ul>

  <!-- Fees -->
  <div class="fee-section">
    <span class="fee-value">{college['ug_min']}</span>
    <span class="fee-value">{college['ug_max']}</span>
  </div>

  <!-- Scholarships -->
  <div class="scholarship-list">
    <ul>{scholarships_html}</ul>
  </div>

  <!-- Departments -->
  <ul class="department-list">
    {''.join(f'<li>{html.escape(d)}</li>' for d in college['departments'])}
  </ul>

  <!-- Additional details (data attributes used by spider) -->
  <div id="additional-data"
       data-established="{html.escape(college['established'])}"
       data-website="{html.escape(college['website'])}"
       data-avg-ctc="{html.escape(college['avg_ctc'])}"
       data-high-ctc="{html.escape(college['high_ctc'])}"
       data-low-ctc="{html.escape(college['low_ctc'])}"
       data-labs="{html.escape(college['labs'])}"
       data-male-pct="{college['male_pct']}"
  ></div>
</body>
</html>
"""


def _index_html() -> str:
    """Listing page – links to each college profile."""
    links = "\n".join(
        f'<li><a href="/college/{c["slug"]}" class="clg-name">{html.escape(c["name"])}</a></li>'
        for c in COLLEGES
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Top Engineering Colleges India</title></head>
<body>
  <h1>Top 20 Engineering Colleges in India 2024</h1>
  <ul id="college-list">{links}</ul>
</body>
</html>
"""


# ── HTTP handler ──────────────────────────────────────────────────────────────

class CollegeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args):  # suppress default access log
        pass

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")

        if path == "" or path == "/":
            body = _index_html().encode()
            self._send(200, "text/html; charset=utf-8", body)

        elif path.startswith("/college/"):
            slug = path.split("/college/", 1)[1]
            if slug in _COLLEGE_MAP:
                body = _college_html(_COLLEGE_MAP[slug]).encode()
                self._send(200, "text/html; charset=utf-8", body)
            else:
                self._send(404, "text/plain", b"Not Found")

        elif path == "/robots.txt":
            self._send(200, "text/plain", b"User-agent: *\nDisallow:\n")

        else:
            self._send(404, "text/plain", b"Not Found")

    def _send(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), CollegeHandler)
    print(f"[mock-server] Listening on http://127.0.0.1:{args.port}  ({len(COLLEGES)} colleges)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    print("[mock-server] Stopped.")


if __name__ == "__main__":
    main()
