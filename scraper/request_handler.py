# scraper/request_handler.py

import time
import random
import logging
from datetime import datetime, timedelta
from typing import Optional
import requests

from config import STOP_SIGNALS

logger = logging.getLogger(__name__)


class ProtectedRequestHandler:
    """
    Makes HTTP requests with protection against IP bans.
    """

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    ]

    def __init__(self, config: dict, error_config: dict):
        self.config = config
        self.error_config = error_config
        self.session = requests.Session()
        self.request_count = 0
        self.hourly_request_count = 0
        self.hour_start = datetime.now()
        self.last_request_time = None
        self.consecutive_failures = 0
        self.current_user_agent_index = 0
        self.is_paused = False
        self.pause_until = None
        self.last_error_type = None  # 'connection', 'timeout', 'http', 'ssl'

    def _rotate_user_agent(self) -> str:
        """Rotate user agent periodically"""
        if self.request_count % random.randint(15, 25) == 0:
            self.current_user_agent_index = random.randint(0, len(self.USER_AGENTS) - 1)
        return self.USER_AGENTS[self.current_user_agent_index]

    def _get_headers(self, referer: str = None) -> dict:
        """Generate realistic browser headers"""
        headers = {
            'User-Agent': self._rotate_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none' if not referer else 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        if referer:
            headers['Referer'] = referer
        return headers

    def _check_hourly_limit(self):
        """Reset hourly counter if hour has passed, wait if limit reached"""
        now = datetime.now()
        if (now - self.hour_start).total_seconds() > 3600:
            self.hourly_request_count = 0
            self.hour_start = now

        max_per_hour = self.config.get('max_requests_per_hour', 200)
        if self.hourly_request_count >= max_per_hour:
            wait_seconds = 3600 - (now - self.hour_start).total_seconds() + 60
            logger.warning(f"Hourly limit ({max_per_hour}) reached. Waiting {wait_seconds / 60:.1f} minutes...")
            time.sleep(max(wait_seconds, 0))
            self.hourly_request_count = 0
            self.hour_start = datetime.now()

    def _wait_between_requests(self, delay_type: str = 'between_requests'):
        """Wait appropriate amount of time between requests"""
        if self.last_request_time:
            delay_range = self.config.get(delay_type, (5, 10))
            delay = random.uniform(*delay_range)
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < delay:
                sleep_time = delay - elapsed
                time.sleep(sleep_time)

    def _handle_error_response(self, response, url: str) -> bool:
        """Handle error responses. Returns True if should retry."""
        status = response.status_code

        if status in STOP_SIGNALS:
            logger.error(f"RECEIVED {status} FROM {url}")
            self.consecutive_failures += 1

            if status == 429:
                retry_after = response.headers.get('Retry-After', 300)
                wait_time = int(retry_after) if str(retry_after).isdigit() else 300
                logger.warning(f"Rate limited (429). Waiting {wait_time} seconds...")
                self.pause_until = datetime.now() + timedelta(seconds=wait_time)
                self.is_paused = True

            elif status == 403:
                logger.error("Forbidden (403). May be IP blocked. Waiting 30 minutes...")
                self.pause_until = datetime.now() + timedelta(minutes=30)
                self.is_paused = True

            elif status == 503:
                logger.warning("Service unavailable (503). Waiting 5 minutes...")
                self.pause_until = datetime.now() + timedelta(minutes=5)
                self.is_paused = True

            return False

        # Other errors (404, 500, etc.) - don't pause, just skip
        if status >= 400:
            logger.warning(f"HTTP {status} for {url} - skipping")
            return False

        return True

    def _check_circuit_breaker(self):
        """Check if circuit breaker should trip"""
        limit = self.error_config.get('consecutive_failures_limit', 5)
        if self.consecutive_failures >= limit:
            cooldown = self.error_config.get('circuit_breaker_cooldown', 1800)
            logger.error(f"Circuit breaker triggered after {self.consecutive_failures} failures")
            logger.info(f"Cooling down for {cooldown / 60:.1f} minutes...")
            time.sleep(cooldown)
            self.consecutive_failures = 0

    def _check_pause(self):
        """Check if we're paused and wait if needed"""
        if self.is_paused and self.pause_until:
            now = datetime.now()
            if now < self.pause_until:
                wait_seconds = (self.pause_until - now).total_seconds()
                logger.info(f"Scraper paused. Resuming in {wait_seconds / 60:.1f} minutes...")
                time.sleep(wait_seconds)
            self.is_paused = False
            self.pause_until = None

    def get(self, url: str, delay_type: str = 'between_requests',
            referer: str = None) -> Optional[requests.Response]:
        """Make a GET request with full protection"""
        self.last_error_type = None

        # Check pause status
        self._check_pause()

        # Check circuit breaker
        self._check_circuit_breaker()

        # Check hourly limit
        self._check_hourly_limit()

        # Wait between requests
        self._wait_between_requests(delay_type)

        # Make request with retries
        max_retries = self.error_config.get('max_retries', 3)
        for attempt in range(max_retries):
            try:
                # Clear cookies between different domains
                response = self.session.get(
                    url,
                    headers=self._get_headers(referer),
                    timeout=30,
                    allow_redirects=True
                )

                self.last_request_time = datetime.now()
                self.request_count += 1
                self.hourly_request_count += 1

                # Check for errors
                if response.status_code != 200:
                    self.last_error_type = 'http'
                    success = self._handle_error_response(response, url)
                    if not success:
                        return None

                # Success - reset failure counter
                self.consecutive_failures = 0

                logger.debug(f"OK {url} ({self.hourly_request_count} req/hr)")
                return response

            except requests.exceptions.SSLError as e:
                self.last_error_type = 'ssl'
                logger.warning(f"SSL error for {url} - skipping host")
                return None

            except requests.exceptions.ConnectionError as e:
                # Domain is unreachable (DNS failure, refused, reset, etc.)
                # This is NOT a rate-limiting signal — don't retry, don't
                # increment the circuit breaker.  The caller should skip
                # remaining URL paths for this domain.
                self.last_error_type = 'connection'
                logger.warning(f"Connection error for {url} - domain unreachable")
                return None

            except requests.Timeout:
                self.last_error_type = 'timeout'
                logger.warning(f"Timeout for {url} (attempt {attempt + 1}/{max_retries})")
                self.consecutive_failures += 1
                if attempt < max_retries - 1:
                    backoff = self.error_config.get('retry_delay_base', 60) * (attempt + 1)
                    time.sleep(min(backoff, self.error_config.get('retry_delay_max', 3600)))

            except requests.RequestException as e:
                self.last_error_type = 'connection'
                logger.error(f"Request failed for {url}: {e} (attempt {attempt + 1}/{max_retries})")
                self.consecutive_failures += 1
                if attempt < max_retries - 1:
                    backoff = self.error_config.get('retry_delay_base', 60) * (attempt + 1)
                    time.sleep(min(backoff, self.error_config.get('retry_delay_max', 3600)))

        return None
