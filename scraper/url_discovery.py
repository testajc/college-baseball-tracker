# scraper/url_discovery.py

import re
import logging
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class UrlDiscoverer:
    """
    Discovers baseball roster/stats URLs by crawling a school's athletics homepage.
    Used as a fallback when standard SIDEARM URL patterns return 404/405.
    """

    # Patterns that indicate a baseball roster page
    ROSTER_PATTERNS = [
        re.compile(r'baseball.*roster', re.I),
        re.compile(r'roster.*baseball', re.I),
        re.compile(r'/roster\.aspx\?.*baseball', re.I),
        re.compile(r'/sport/m-basebl/roster', re.I),
        re.compile(r'/sports/bsb/.*roster', re.I),
        re.compile(r'/sports/m-baseb[al]*/.*roster', re.I),
        re.compile(r'/teams/baseball/roster', re.I),
        re.compile(r'/athletics/baseball/roster', re.I),
    ]

    # Patterns that indicate a baseball stats page
    STATS_PATTERNS = [
        re.compile(r'baseball.*stat', re.I),
        re.compile(r'stat.*baseball', re.I),
        re.compile(r'/teamstats\.aspx\?.*baseball', re.I),
        re.compile(r'/sport/m-basebl/stat', re.I),
        re.compile(r'/sports/bsb/.*stat', re.I),
        re.compile(r'/sports/m-baseb[al]*/.*stat', re.I),
        re.compile(r'/teams/baseball/stat', re.I),
        re.compile(r'/athletics/baseball/stat', re.I),
        re.compile(r'teamcume\.htm', re.I),
    ]

    # Patterns for a baseball landing/sport page (intermediate step)
    BASEBALL_LANDING_PATTERNS = [
        re.compile(r'/sports?/baseball\b', re.I),
        re.compile(r'/sport/m-basebl\b', re.I),
        re.compile(r'/sports?/bsb\b', re.I),
        re.compile(r'/sports?/m-baseb', re.I),
        re.compile(r'/teams/baseball\b', re.I),
        re.compile(r'\bbaseball\b', re.I),
    ]

    def discover_baseball_urls(self, base_url: str, request_handler) -> Optional[Dict[str, str]]:
        """
        Attempt to discover baseball roster and stats URLs by crawling.

        Returns {'roster_url': ..., 'stats_url': ...} or None if nothing found.
        At minimum, roster_url must be found to return a result.
        """
        base_url = base_url.rstrip('/')
        base_domain = urlparse(base_url).netloc

        logger.info(f"  URL discovery: crawling {base_url}")

        # Step 1: Fetch homepage and look for baseball links
        result = self._scan_page_for_baseball(base_url, base_domain, request_handler)
        if result and result.get('roster_url'):
            logger.info(f"  URL discovery found roster: {result['roster_url']}")
            return result

        # Step 2: If no direct roster/stats links, look for a baseball landing page
        landing_url = self._find_baseball_landing(base_url, base_domain, request_handler)
        if landing_url:
            logger.info(f"  URL discovery: found baseball landing page {landing_url}")
            result = self._scan_page_for_roster_stats(landing_url, base_domain, request_handler)
            if result and result.get('roster_url'):
                logger.info(f"  URL discovery found roster via landing: {result['roster_url']}")
                return result

        # Step 3: Try sitemap.xml as last resort
        result = self._scan_sitemap(base_url, base_domain, request_handler)
        if result and result.get('roster_url'):
            logger.info(f"  URL discovery found roster via sitemap: {result['roster_url']}")
            return result

        logger.info(f"  URL discovery: no baseball URLs found for {base_url}")
        return None

    def _scan_page_for_baseball(self, page_url: str, base_domain: str,
                                request_handler) -> Optional[Dict[str, str]]:
        """Scan a page for baseball roster AND stats links."""
        resp = request_handler.get(page_url)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a', href=True)

        roster_url = None
        stats_url = None

        for link in links:
            href = link['href']
            full_url = urljoin(page_url, href)

            # Only consider same-domain links
            if urlparse(full_url).netloc != base_domain:
                continue

            for pattern in self.ROSTER_PATTERNS:
                if pattern.search(href) or pattern.search(link.get_text()):
                    if not roster_url:
                        roster_url = full_url
                    break

            for pattern in self.STATS_PATTERNS:
                if pattern.search(href) or pattern.search(link.get_text()):
                    if not stats_url:
                        stats_url = full_url
                    break

            if roster_url and stats_url:
                break

        if roster_url:
            return {'roster_url': roster_url, 'stats_url': stats_url}
        return None

    def _find_baseball_landing(self, base_url: str, base_domain: str,
                               request_handler) -> Optional[str]:
        """Find a baseball sport landing page from the homepage."""
        resp = request_handler.get(base_url)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a', href=True)

        candidates = []
        for link in links:
            href = link['href']
            full_url = urljoin(base_url, href)
            text = link.get_text(strip=True).lower()

            if urlparse(full_url).netloc != base_domain:
                continue

            # Score the link as a baseball landing page
            score = 0
            for pattern in self.BASEBALL_LANDING_PATTERNS:
                if pattern.search(href):
                    score += 2
                if pattern.search(text):
                    score += 1

            # Avoid roster/stats pages directly (we want the landing page)
            if re.search(r'roster|stats|schedule|recruit', href, re.I):
                score -= 1

            if score >= 2:
                candidates.append((score, full_url))

        if candidates:
            candidates.sort(key=lambda x: -x[0])
            return candidates[0][1]
        return None

    def _scan_page_for_roster_stats(self, page_url: str, base_domain: str,
                                    request_handler) -> Optional[Dict[str, str]]:
        """Scan a baseball landing page specifically for roster and stats links."""
        resp = request_handler.get(page_url)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a', href=True)

        roster_url = None
        stats_url = None

        for link in links:
            href = link['href']
            full_url = urljoin(page_url, href)
            text = link.get_text(strip=True).lower()

            if urlparse(full_url).netloc != base_domain:
                continue

            # Look for roster link
            if not roster_url:
                if re.search(r'\broster\b', href, re.I) or re.search(r'\broster\b', text, re.I):
                    roster_url = full_url

            # Look for stats link
            if not stats_url:
                if re.search(r'\bstat', href, re.I) or re.search(r'\bstat', text, re.I):
                    stats_url = full_url

            if roster_url and stats_url:
                break

        if roster_url:
            return {'roster_url': roster_url, 'stats_url': stats_url}
        return None

    def _scan_sitemap(self, base_url: str, base_domain: str,
                      request_handler) -> Optional[Dict[str, str]]:
        """Try to find baseball URLs from sitemap.xml."""
        sitemap_url = f"{base_url}/sitemap.xml"
        resp = request_handler.get(sitemap_url)
        if not resp:
            return None

        # Parse XML sitemap for baseball URLs
        try:
            soup = BeautifulSoup(resp.text, 'lxml')
        except Exception:
            soup = BeautifulSoup(resp.text, 'html.parser')

        roster_url = None
        stats_url = None

        # Look through all <loc> tags in sitemap
        for loc in soup.find_all('loc'):
            url_text = loc.get_text(strip=True)
            if not url_text:
                continue

            for pattern in self.ROSTER_PATTERNS:
                if pattern.search(url_text):
                    if not roster_url:
                        roster_url = url_text
                    break

            for pattern in self.STATS_PATTERNS:
                if pattern.search(url_text):
                    if not stats_url:
                        stats_url = url_text
                    break

            if roster_url and stats_url:
                break

        if roster_url:
            return {'roster_url': roster_url, 'stats_url': stats_url}
        return None
