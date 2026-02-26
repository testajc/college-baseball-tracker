# scraper/browser_scraper.py

import json
import logging
import subprocess
import sys
import time
import random
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Playwright is optional — graceful degradation if not installed
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.info("Playwright not installed — browser scraping disabled. "
                "Install with: pip install playwright && playwright install chromium")


class BrowserScraper:
    """
    Headless browser fallback for JS-rendered pages.
    Uses Playwright (Chromium) to render pages that return 0 players
    with static HTML parsing.

    Reuses a single browser instance across schools for speed.
    """

    def __init__(self, parser, config: dict = None):
        """
        Args:
            parser: SidearmParser instance (reused for HTML parsing)
            config: BROWSER_CONFIG dict with page_load_timeout, max_schools_per_run
        """
        self.parser = parser
        self.config = config or {}
        self.timeout = self.config.get('page_load_timeout', 15000)
        self.max_schools = self.config.get('max_schools_per_run', 50)
        self._playwright = None
        self._browser = None
        self._use_subprocess = False

    @property
    def available(self) -> bool:
        return PLAYWRIGHT_AVAILABLE

    def _ensure_browser(self):
        """Launch browser if not already running.
        Falls back to subprocess mode if sync_playwright() fails
        (e.g., in asyncio environments like GitHub Actions)."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        if self._use_subprocess:
            return True
        if self._browser is None:
            try:
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(headless=True)
                logger.info("Browser launched for JS rendering")
            except RuntimeError as e:
                if 'asyncio' in str(e).lower() or 'event loop' in str(e).lower():
                    logger.warning(f"Playwright sync API failed (asyncio conflict): {e}")
                    logger.info("Will use subprocess fallback for browser scraping")
                    self._use_subprocess = True
                    return True
                raise
        return True

    def close(self):
        """Clean up browser resources."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def scrape_school(self, school: dict) -> dict:
        """
        Scrape a school using headless browser rendering.
        Returns the same result dict format as CollegeBaseballScraper.scrape_school().
        """
        school_name = school['school_name']
        base_url = school.get('athletics_base_url', '').rstrip('/')
        roster_url = school.get('roster_url', '/sports/baseball/roster')
        stats_url = school.get('stats_url', '/sports/baseball/stats')

        result = {
            'school': school_name,
            'division': school.get('division', ''),
            'conference': school.get('conference', ''),
            'players': [],
            'success': False,
            'errors': [],
            'method': 'browser'
        }

        if not base_url:
            result['errors'].append(f"No athletics URL for {school_name}")
            return result

        if not self._ensure_browser():
            result['errors'].append("Playwright not available")
            return result

        # Use subprocess fallback if sync API is blocked by asyncio
        if self._use_subprocess:
            return self._scrape_school_subprocess(school)

        # Build full URLs
        full_roster = f"{base_url}{roster_url}" if not roster_url.startswith('http') else roster_url
        full_stats = f"{base_url}{stats_url}" if not stats_url.startswith('http') else stats_url

        logger.info(f"  Browser scraping: {school_name}")

        page = self._browser.new_page()
        page.set_default_timeout(self.timeout)

        try:
            # Fetch and render roster page
            roster = []
            try:
                page.goto(full_roster, wait_until='networkidle')
                html = page.content()
                roster = self.parser.parse_roster(html, school_name)
                logger.info(f"  Browser roster: {len(roster)} players")
            except Exception as e:
                logger.warning(f"  Browser roster failed for {school_name}: {e}")
                result['errors'].append(f"Browser roster error: {e}")

            if not roster:
                result['errors'].append("Browser: no players found on roster page")
                return result

            # Brief pause before stats
            time.sleep(random.uniform(1, 2))

            # Fetch and render stats page
            batting_stats = {}
            pitching_stats = {}
            try:
                page.goto(full_stats, wait_until='networkidle')
                html = page.content()
                batting_stats, pitching_stats = self.parser.parse_nuxt_stats(html)
                if not batting_stats:
                    batting_stats = self.parser.parse_batting_stats(html)
                if not pitching_stats:
                    pitching_stats = self.parser.parse_pitching_stats(html)
                logger.info(f"  Browser stats: {len(batting_stats)} batting, {len(pitching_stats)} pitching")
            except Exception as e:
                logger.warning(f"  Browser stats failed for {school_name}: {e}")
                result['errors'].append(f"Browser stats error: {e}")

            # Merge data (same logic as main scraper)
            for player in roster:
                player_name = player.get('name', '')
                player['batting_stats'] = batting_stats.get(player_name)
                player['pitching_stats'] = pitching_stats.get(player_name)
                result['players'].append(player)

            roster_names = {p.get('name') for p in roster}
            for name, stats in batting_stats.items():
                if name not in roster_names:
                    result['players'].append({
                        'name': name,
                        'school': school_name,
                        'batting_stats': stats,
                        'pitching_stats': pitching_stats.get(name)
                    })

            result['success'] = len(result['players']) > 0

        finally:
            page.close()

        return result

    def _scrape_school_subprocess(self, school: dict) -> dict:
        """Scrape a school in a separate subprocess to avoid asyncio conflicts.
        Spawns a fresh Python process that uses Playwright's sync API."""
        school_name = school['school_name']
        base_url = school.get('athletics_base_url', '').rstrip('/')
        roster_url = school.get('roster_url', '/sports/baseball/roster')
        stats_url = school.get('stats_url', '/sports/baseball/stats')

        result = {
            'school': school_name,
            'division': school.get('division', ''),
            'conference': school.get('conference', ''),
            'players': [],
            'success': False,
            'errors': [],
            'method': 'browser-subprocess'
        }

        full_roster = f"{base_url}{roster_url}" if not roster_url.startswith('http') else roster_url
        full_stats = f"{base_url}{stats_url}" if not stats_url.startswith('http') else stats_url

        # Pass URLs via argv to avoid f-string issues with URL characters
        input_data = json.dumps({
            'roster_url': full_roster,
            'stats_url': full_stats,
            'timeout': self.timeout,
        })

        script = '''
import json, sys
from playwright.sync_api import sync_playwright

config = json.loads(sys.argv[1])
results = {"roster_html": "", "stats_html": ""}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(config["timeout"])
    try:
        page.goto(config["roster_url"], wait_until="networkidle")
        results["roster_html"] = page.content()
    except Exception as e:
        results["roster_error"] = str(e)
    try:
        page.goto(config["stats_url"], wait_until="networkidle")
        results["stats_html"] = page.content()
    except Exception as e:
        results["stats_error"] = str(e)
    page.close()
    browser.close()
print(json.dumps(results))
'''

        try:
            logger.info(f"  Browser subprocess: {school_name}")
            proc = subprocess.run(
                [sys.executable, '-c', script, input_data],
                capture_output=True, text=True, timeout=120
            )

            if proc.returncode != 0:
                err = proc.stderr.strip()[-200:] if proc.stderr else 'unknown error'
                result['errors'].append(f"Subprocess failed: {err}")
                return result

            data = json.loads(proc.stdout.strip())

            # Parse roster
            roster = []
            if data.get('roster_html'):
                roster = self.parser.parse_roster(data['roster_html'], school_name)
                logger.info(f"  Subprocess roster: {len(roster)} players")

            if not roster:
                result['errors'].append("Subprocess: no players found on roster page")
                return result

            # Parse stats
            batting_stats = {}
            pitching_stats = {}
            if data.get('stats_html'):
                batting_stats, pitching_stats = self.parser.parse_nuxt_stats(data['stats_html'])
                if not batting_stats:
                    batting_stats = self.parser.parse_batting_stats(data['stats_html'])
                if not pitching_stats:
                    pitching_stats = self.parser.parse_pitching_stats(data['stats_html'])

            # Merge
            for player in roster:
                player_name = player.get('name', '')
                player['batting_stats'] = batting_stats.get(player_name)
                player['pitching_stats'] = pitching_stats.get(player_name)
                result['players'].append(player)

            roster_names = {p.get('name') for p in roster}
            for name, stats in batting_stats.items():
                if name not in roster_names:
                    result['players'].append({
                        'name': name,
                        'school': school_name,
                        'batting_stats': stats,
                        'pitching_stats': pitching_stats.get(name)
                    })

            result['success'] = len(result['players']) > 0

        except subprocess.TimeoutExpired:
            result['errors'].append("Subprocess timed out after 120s")
        except Exception as e:
            result['errors'].append(f"Subprocess error: {e}")

        return result

    def scrape_schools(self, schools: List[dict]) -> List[dict]:
        """
        Scrape multiple schools via browser, respecting max_schools_per_run limit.
        Returns list of result dicts.
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not installed — skipping browser scrape pass")
            return []

        if not schools:
            return []

        batch = schools[:self.max_schools]
        if len(schools) > self.max_schools:
            logger.info(f"Browser scrape limited to {self.max_schools} schools "
                       f"(of {len(schools)} candidates)")

        logger.info(f"Browser scrape pass: {len(batch)} schools")
        results = []

        try:
            for i, school in enumerate(batch):
                try:
                    result = self.scrape_school(school)
                    results.append(result)

                    if result['success']:
                        logger.info(f"  Browser recovered {school['school_name']}: "
                                   f"{len(result['players'])} players")

                    # Brief delay between schools
                    if i < len(batch) - 1:
                        time.sleep(random.uniform(2, 4))

                except Exception as e:
                    logger.error(f"Browser error for {school['school_name']}: {e}")
                    continue
        finally:
            self.close()

        recovered = sum(1 for r in results if r['success'])
        logger.info(f"Browser scrape complete: {recovered}/{len(batch)} schools recovered")
        return results
