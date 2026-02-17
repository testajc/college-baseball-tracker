# scraper/config.py

# Phase 1: Initial Scrape
INITIAL_SCRAPE_CONFIG = {
    'between_requests': (5, 10),           # 5-10 seconds between requests
    'between_pages_same_school': (3, 6),
    'between_schools': (10, 18),           # 10-18 seconds between different sites
    'max_schools_per_day': 1000,            # DB checkpoint handles dedup; 6hr timeout is the real limit
    'max_requests_per_hour': 300,
}

# Phase 2: Daily Updates (faster, since we're just refreshing)
DAILY_UPDATE_CONFIG = {
    'between_requests': (3, 6),            # 3-6 seconds between requests
    'between_pages_same_school': (2, 4),
    'between_schools': (10, 20),           # 10-20 seconds between schools
    'max_schools_per_day': 500,            # Can do more per day
    'max_requests_per_hour': 300,
}

# Error handling (same for both phases)
ERROR_CONFIG = {
    'retry_delay_base': 10,
    'retry_delay_max': 30,
    'max_retries': 2,
    'consecutive_failures_limit': 10,
    'circuit_breaker_cooldown': 600,       # 10 minutes (was 30 — dead domains no longer trip it)
}

# Stop signals - if we see these, pause immediately
STOP_SIGNALS = [429, 403, 503]

# Season start date - D1 opening weekend is mid-February 2026
SEASON_START_DATE = '2026-02-14'
