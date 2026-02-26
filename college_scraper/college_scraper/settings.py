# ── Scrapy settings for college_scraper ──────────────────────────────────────

BOT_NAME = "college_scraper"

SPIDER_MODULES = ["college_scraper.spiders"]
NEWSPIDER_MODULE = "college_scraper.spiders"

# Be polite: identify ourselves
USER_AGENT = (
    "college_scraper (+https://github.com/your-org/college_scraper)"
)

# Honour robots.txt
ROBOTSTXT_OBEY = True

# Conservative concurrency so we don't hammer servers
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 1.5           # seconds between requests to the same domain
RANDOMIZE_DOWNLOAD_DELAY = True

CONCURRENT_REQUESTS_PER_DOMAIN = 2

# ── Cookies / AutoThrottle ────────────────────────────────────────────────────
COOKIES_ENABLED = False

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# ── Retry ────────────────────────────────────────────────────────────────────
RETRY_ENABLED = True
RETRY_TIMES = 2

# ── Default request headers ──────────────────────────────────────────────────
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
}

# ── Downloader middlewares ────────────────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
    "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
}

# ── Item pipelines (3-layer architecture) ─────────────────────────────────────
ITEM_PIPELINES = {
    "college_scraper.pipelines.NormalizationPipeline": 100,   # Layer: Normalize & Dedup
    "college_scraper.pipelines.ValidationPipeline": 200,      # Layer: Validate & Score
    "college_scraper.pipelines.CollegeJsonPipeline": 300,     # Layer: Serialise JSON
}

# Output directory for scraped JSON files
OUTPUT_DIR = "output"

# ── Feed export (also write a combined JSONL feed) ────────────────────────────
FEEDS = {
    "output/colleges_all.jsonl": {
        "format": "jsonlines",
        "encoding": "utf8",
        "overwrite": True,
        "indent": None,
    },
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
