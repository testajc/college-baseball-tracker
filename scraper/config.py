# scraper/config.py

# Phase 1: Initial Scrape
INITIAL_SCRAPE_CONFIG = {
    'between_requests': (5, 10),           # 5-10 seconds between requests
    'between_pages_same_school': (3, 6),
    'between_schools': (15, 25),           # 15-25 seconds between schools
    'max_schools_per_day': 500,            # 500 schools per run (~5.5 hours)
    'max_requests_per_hour': 250,
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
