# scraper/config.py

# Phase 1: Initial Scrape — different domain per school, so minimal delays
INITIAL_SCRAPE_CONFIG = {
    'between_requests': (0.5, 1.5),        # different domain each time — minimal delay
    'between_pages_same_school': (1, 2),   # roster → stats on same domain
    'between_schools': (1, 2),             # different domain, no courtesy needed
    'max_schools_per_day': 1000,           # DB checkpoint handles dedup; 6hr timeout is the real limit
    'max_requests_per_hour': 9999,         # no limit (cross-domain, logging only)
}

# Phase 2: Daily Updates
DAILY_UPDATE_CONFIG = {
    'between_requests': (2, 4),            # 2-4 seconds between requests
    'between_pages_same_school': (2, 4),
    'between_schools': (3, 6),             # 3-6 seconds between schools (different domains)
    'max_schools_per_day': 500,
    'max_requests_per_hour': 9999,         # no limit (cross-domain, logging only)
}

# Error handling
ERROR_CONFIG = {
    'retry_delay_base': 5,
    'retry_delay_max': 15,
    'max_retries': 1,                      # No retries — if first attempt fails, move on
    'consecutive_failures_limit': 20,
    'circuit_breaker_cooldown': 300,       # 5 minutes
}

# Stop signals - only 429 triggers a pause (actual rate limiting)
STOP_SIGNALS = [429]

# Browser scraping (Playwright headless Chromium)
BROWSER_CONFIG = {
    'page_load_timeout': 15000,   # ms — max wait for JS rendering
    'max_schools_per_run': 50,    # limit browser-based scraping per run
}

# Season start date - D1 opening weekend is mid-February 2026
SEASON_START_DATE = '2026-02-14'
