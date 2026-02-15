# scraper/config.py

# Phase 1: Initial Scrape (conservative)
INITIAL_SCRAPE_CONFIG = {
    'between_requests': (8, 15),           # 8-15 seconds between requests
    'between_pages_same_school': (5, 10),
    'between_schools': (30, 60),           # 30-60 seconds between schools
    'max_schools_per_day': 100,            # 100 schools per day
    'max_requests_per_hour': 150,
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
    'retry_delay_base': 60,
    'retry_delay_max': 3600,
    'max_retries': 3,
    'consecutive_failures_limit': 5,
    'circuit_breaker_cooldown': 1800,      # 30 minutes
}

# Stop signals - if we see these, pause immediately
STOP_SIGNALS = [429, 403, 503]

# Season start date - D1 opening weekend is mid-February 2026
SEASON_START_DATE = '2026-02-14'
