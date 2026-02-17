# scraper/config.py

# Phase 1: Initial Scrape — different domain per school, so minimal delays
INITIAL_SCRAPE_CONFIG = {
    'between_requests': (2, 4),            # 2-4 seconds between requests
    'between_pages_same_school': (1, 3),   # roster → stats on same domain
    'between_schools': (3, 6),             # different domain, less delay needed
    'max_schools_per_day': 1000,           # DB checkpoint handles dedup; 6hr timeout is the real limit
    'max_requests_per_hour': 600,
}

# Phase 2: Daily Updates
DAILY_UPDATE_CONFIG = {
    'between_requests': (3, 6),            # 3-6 seconds between requests
    'between_pages_same_school': (2, 4),
    'between_schools': (10, 20),           # 10-20 seconds between schools
    'max_schools_per_day': 500,
    'max_requests_per_hour': 300,
}

# Error handling
ERROR_CONFIG = {
    'retry_delay_base': 5,
    'retry_delay_max': 15,
    'max_retries': 1,                      # No retries — if first attempt fails, move on
    'consecutive_failures_limit': 20,
    'circuit_breaker_cooldown': 300,       # 5 minutes
}

# Stop signals - if we see these, pause immediately
STOP_SIGNALS = [429, 403, 503]

# Season start date - D1 opening weekend is mid-February 2026
SEASON_START_DATE = '2026-02-14'
