"""
Scrapy Item definitions for college data.

Each field mirrors the target JSON schema from the prompt so that the
pipeline can serialize the item directly to the required format.

Fields are classified by data accuracy level:

  🟢 Level 1 – Official Static Data (99% reliable)
     established, campus, website, departments, programs

  🟡 Level 2 – Verified External Rankings
     NIRF, QS, THE rankings (from official sources only)

  🔴 Level 3 – Dynamic / Risky Data
     placements, salary, student count, faculty count
     (change every year – require official PDF verification)
"""
import scrapy


class CollegeItem(scrapy.Item):
    # ── Basic identity (🟢 Level 1) ───────────────────────────────────────
    college_name        = scrapy.Field()
    country             = scrapy.Field()
    about               = scrapy.Field()
    location            = scrapy.Field()
    summary             = scrapy.Field()

    # ── Programmes (🟢 Level 1) ───────────────────────────────────────────
    ug_programs         = scrapy.Field()   # list[str]
    pg_programs         = scrapy.Field()   # list[str]
    phd_programs        = scrapy.Field()   # list[str]

    # ── Fees (🔴 Level 3) ─────────────────────────────────────────────────
    fees                = scrapy.Field()   # dict with ug/pg/phd min/max keys

    # ── Scholarships (🟢 Level 1) ─────────────────────────────────────────
    scholarships        = scrapy.Field()   # list[str]

    # ── Student profile (🔴 Level 3) ──────────────────────────────────────
    student_gender_ratio    = scrapy.Field()  # {male_percentage, female_percentage}
    faculty_staff           = scrapy.Field()  # int
    international_students  = scrapy.Field()  # int

    # ── Rankings (🟡 Level 2) ─────────────────────────────────────────────
    global_ranking      = scrapy.Field()   # str

    # ── Departments (🟢 Level 1) ──────────────────────────────────────────
    departments         = scrapy.Field()   # list[str]

    # ── Detailed stats (🔴 Level 3) ───────────────────────────────────────
    student_statistics  = scrapy.Field()   # list[{category, value}]
    additional_details  = scrapy.Field()   # list[{category, value}]

    # ── Attribution ───────────────────────────────────────────────────────
    sources             = scrapy.Field()   # list[str]

    # ── Internal metadata ────────────────────────────────────────────────
    source_url          = scrapy.Field()   # page the data was scraped from

    # ── 🆕  Data quality / verification metadata ─────────────────────────
    data_confidence_score = scrapy.Field()  # float 0.0–1.0
    data_version          = scrapy.Field()  # e.g. "2026.1"
    last_updated          = scrapy.Field()  # ISO date e.g. "2026-02-26"
    manual_verified       = scrapy.Field()  # bool
    validation_report     = scrapy.Field()  # dict from ValidationEngine
    sources_metadata      = scrapy.Field()  # dict of URL → extraction status
    field_confidence      = scrapy.Field()  # per-field confidence breakdown
    scrape_duration       = scrapy.Field()  # Time taken to scrape this college
