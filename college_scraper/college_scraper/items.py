"""
Scrapy Item definitions for college data.

Each field mirrors the target JSON schema from the prompt so that the
pipeline can serialize the item directly to the required format.
"""
import scrapy


class CollegeItem(scrapy.Item):
    # ── Basic identity ─────────────────────────────────────────────────────
    college_name        = scrapy.Field()
    country             = scrapy.Field()
    about               = scrapy.Field()
    location            = scrapy.Field()
    summary             = scrapy.Field()

    # ── Programmes ────────────────────────────────────────────────────────
    ug_programs         = scrapy.Field()   # list[str]
    pg_programs         = scrapy.Field()   # list[str]
    phd_programs        = scrapy.Field()   # list[str]

    # ── Fees (INR per year) ───────────────────────────────────────────────
    fees                = scrapy.Field()   # dict with ug/pg/phd min/max keys

    # ── Scholarships ──────────────────────────────────────────────────────
    scholarships        = scrapy.Field()   # list[str]

    # ── Student profile ───────────────────────────────────────────────────
    student_gender_ratio    = scrapy.Field()  # {male_percentage, female_percentage}
    faculty_staff           = scrapy.Field()  # int
    international_students  = scrapy.Field()  # int

    # ── Rankings ──────────────────────────────────────────────────────────
    global_ranking      = scrapy.Field()   # str

    # ── Departments ───────────────────────────────────────────────────────
    departments         = scrapy.Field()   # list[str]

    # ── Detailed stats ────────────────────────────────────────────────────
    student_statistics  = scrapy.Field()   # list[{category, value}]
    additional_details  = scrapy.Field()   # list[{category, value}]

    # ── Attribution ───────────────────────────────────────────────────────
    sources             = scrapy.Field()   # list[str]

    # ── Internal metadata ────────────────────────────────────────────────
    source_url          = scrapy.Field()   # page the data was scraped from
