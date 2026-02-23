#!/usr/bin/env python3
"""
Validate & fix failed schools.

Classifies why schools failed during scraping (dead DNS, parked domains,
no baseball program, wrong URLs, etc.) and auto-discovers correct domains
for fixable schools.

Usage:
    python validate_schools.py --classify                    # Phase 1: classify all failed schools
    python validate_schools.py --fix                         # Phase 2: auto-discover via domain guessing
    python validate_schools.py --discover-from-conferences   # Phase 2b: scrape conference websites
    python validate_schools.py --update-csv                  # Phase 3: apply fixes to schools_database.csv
    python validate_schools.py --rescrape                    # Phase 4: re-run scraper on fixed schools only
    python validate_schools.py --all                         # Run all phases sequentially
"""

import argparse
import csv
import json
import logging
import os
import re
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse, quote_plus

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Add parent dir so we can import sibling modules
sys.path.insert(0, str(Path(__file__).parent))

from config import INITIAL_SCRAPE_CONFIG, ERROR_CONFIG
from database import DatabaseManager
from request_handler import ProtectedRequestHandler

load_dotenv(Path(__file__).parent.parent / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('validate_schools')


# ---------------------------------------------------------------------------
# Classification enum
# ---------------------------------------------------------------------------

class SchoolClassification(Enum):
    DNS_DEAD = "DNS_DEAD"
    PARKED_DOMAIN = "PARKED_DOMAIN"
    NO_BASEBALL = "NO_BASEBALL"
    WRONG_URLS = "WRONG_URLS"
    REDIRECT_DOMAIN = "REDIRECT_DOMAIN"
    SSL_ERROR = "SSL_ERROR"
    BLOCKED = "BLOCKED"
    ZERO_PLAYERS = "ZERO_PLAYERS"
    TIMEOUT = "TIMEOUT"
    OK = "OK"


PARKED_INDICATORS = [
    "domain is for sale",
    "buy this domain",
    "parked",
    "godaddy",
    "sedo.com",
    "afternic",
    "this domain",
    "domain parking",
    "hugedomains",
    "dan.com",
    "is for sale",
    "domainmarket",
]


# ---------------------------------------------------------------------------
# SchoolValidator
# ---------------------------------------------------------------------------

class SchoolValidator:
    def __init__(self, schools_csv_path: str = None, db_manager: DatabaseManager = None):
        if schools_csv_path is None:
            schools_csv_path = str(Path(__file__).parent / 'schools_database.csv')
        self.schools_csv_path = schools_csv_path
        self.schools = self._load_csv(schools_csv_path)
        self.db = db_manager or DatabaseManager()
        self.schools_in_db = self.db.get_schools_in_db()
        logger.info(f"Loaded {len(self.schools)} schools from CSV, {len(self.schools_in_db)} already in DB")

    def _load_csv(self, path: str) -> list:
        schools = []
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                schools.append(row)
        return schools

    def get_failed_schools(self) -> list:
        return [s for s in self.schools if s['school_name'] not in self.schools_in_db]

    def classify_all(self, failed_schools: list) -> dict:
        """Classify all failed schools. Returns dict: school_name -> {classification, details, base_url}."""
        results = {}

        # Step 1: parallel DNS resolution
        logger.info(f"Phase 1: DNS resolution for {len(failed_schools)} schools...")
        dns_results = self._parallel_dns(failed_schools)

        dns_dead = []
        dns_alive = []
        for school in failed_schools:
            name = school['school_name']
            if dns_results.get(name):
                dns_alive.append(school)
            else:
                dns_dead.append(school)
                results[name] = {
                    'classification': SchoolClassification.DNS_DEAD,
                    'details': f"DNS resolution failed for {urlparse(school['athletics_base_url']).hostname}",
                    'base_url': school['athletics_base_url'],
                    'school': school,
                }

        logger.info(f"DNS results: {len(dns_alive)} alive, {len(dns_dead)} dead")

        # Step 2: HTTP classification for DNS-reachable schools
        logger.info(f"Phase 2: HTTP classification for {len(dns_alive)} DNS-reachable schools...")
        handler = ProtectedRequestHandler(INITIAL_SCRAPE_CONFIG, ERROR_CONFIG)

        for i, school in enumerate(dns_alive):
            name = school['school_name']
            base_url = school['athletics_base_url'].rstrip('/')
            logger.info(f"  [{i+1}/{len(dns_alive)}] Classifying {name} ({base_url})")

            result = self._classify_school(school, base_url, handler)
            results[name] = result

            # Brief delay between requests
            time.sleep(0.5)

        return results

    def _parallel_dns(self, schools: list) -> dict:
        """Resolve DNS for all schools in parallel. Returns dict: school_name -> bool."""
        results = {}

        def resolve(school):
            name = school['school_name']
            url = school['athletics_base_url']
            hostname = urlparse(url).hostname
            if not hostname:
                return name, False
            try:
                socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
                return name, True
            except (socket.gaierror, socket.herror, OSError):
                return name, False

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(resolve, s): s for s in schools}
            for future in as_completed(futures):
                name, alive = future.result()
                results[name] = alive

        return results

    def _classify_school(self, school: dict, base_url: str, handler: ProtectedRequestHandler) -> dict:
        """Classify a single DNS-reachable school by HTTP probing."""
        name = school['school_name']

        try:
            resp = requests.get(base_url, timeout=10, allow_redirects=True, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
        except requests.exceptions.SSLError as e:
            return {
                'classification': SchoolClassification.SSL_ERROR,
                'details': f"SSL error: {str(e)[:100]}",
                'base_url': base_url,
                'school': school,
            }
        except requests.exceptions.Timeout:
            return {
                'classification': SchoolClassification.TIMEOUT,
                'details': "Connection timed out (10s)",
                'base_url': base_url,
                'school': school,
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'classification': SchoolClassification.DNS_DEAD,
                'details': f"Connection failed: {str(e)[:100]}",
                'base_url': base_url,
                'school': school,
            }
        except requests.exceptions.RequestException as e:
            return {
                'classification': SchoolClassification.TIMEOUT,
                'details': f"Request error: {str(e)[:100]}",
                'base_url': base_url,
                'school': school,
            }

        # Check for redirect to different host
        original_host = urlparse(base_url).hostname
        final_host = urlparse(resp.url).hostname
        if original_host and final_host and original_host != final_host:
            # Redirect to a different domain
            new_base = f"{urlparse(resp.url).scheme}://{final_host}"
            return {
                'classification': SchoolClassification.REDIRECT_DOMAIN,
                'details': f"Redirects to {final_host} (was {original_host})",
                'base_url': base_url,
                'new_url': new_base,
                'school': school,
            }

        # Check HTTP status
        if resp.status_code == 403:
            return {
                'classification': SchoolClassification.BLOCKED,
                'details': "HTTP 403 on homepage",
                'base_url': base_url,
                'school': school,
            }

        if resp.status_code >= 400:
            return {
                'classification': SchoolClassification.BLOCKED,
                'details': f"HTTP {resp.status_code} on homepage",
                'base_url': base_url,
                'school': school,
            }

        # Check page content for parked indicators
        page_text = resp.text.lower()
        for indicator in PARKED_INDICATORS:
            if indicator in page_text:
                return {
                    'classification': SchoolClassification.PARKED_DOMAIN,
                    'details': f"Parked domain (matched: '{indicator}')",
                    'base_url': base_url,
                    'school': school,
                }

        # Check for baseball references
        has_baseball = self._check_for_baseball(resp.text, base_url)
        if not has_baseball:
            return {
                'classification': SchoolClassification.NO_BASEBALL,
                'details': "No baseball references found on athletics site",
                'base_url': base_url,
                'school': school,
            }

        # Baseball exists but scraper still failed — wrong URLs or zero players
        # Try fetching a roster page to distinguish
        roster_paths = [
            '/sports/baseball/roster',
            '/sports/baseball/roster/2026',
            '/sport/m-basebl/roster',
            '/sports/bsb/roster',
        ]
        for path in roster_paths:
            try:
                roster_url = f"{base_url}{path}"
                r = requests.get(roster_url, timeout=10, allow_redirects=True, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                })
                if r.status_code == 200 and len(r.text) > 1000:
                    # Page loads but scraper couldn't parse it → likely JS-rendered
                    return {
                        'classification': SchoolClassification.ZERO_PLAYERS,
                        'details': f"Roster page loads ({path}) but scraper found 0 players (likely JS-rendered)",
                        'base_url': base_url,
                        'school': school,
                    }
            except requests.exceptions.RequestException:
                continue

        return {
            'classification': SchoolClassification.WRONG_URLS,
            'details': "Baseball content exists but standard roster paths failed",
            'base_url': base_url,
            'school': school,
        }

    def _check_for_baseball(self, html: str, base_url: str) -> bool:
        """Check if the page has baseball-related content in nav/links."""
        soup = BeautifulSoup(html, 'lxml')
        # Check links for baseball references
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            if 'baseball' in href or 'baseball' in text:
                return True
            if 'bsb' in href or 'm-basebl' in href:
                return True

        # Check full text as fallback
        text = soup.get_text(separator=' ').lower()
        if 'baseball' in text:
            return True

        return False


# ---------------------------------------------------------------------------
# DomainFixer
# ---------------------------------------------------------------------------

class DomainFixer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def fix_domains(self, classified_schools: dict) -> list:
        """Try to find correct domains for fixable schools.
        Returns list of {school_name, old_url, new_url, method, confidence}."""
        fixes = []
        fixable = {
            name: info for name, info in classified_schools.items()
            if info['classification'] in (
                SchoolClassification.PARKED_DOMAIN,
                SchoolClassification.REDIRECT_DOMAIN,
                SchoolClassification.DNS_DEAD,
                SchoolClassification.SSL_ERROR,
            )
        }

        logger.info(f"Attempting to fix {len(fixable)} schools...")

        for i, (name, info) in enumerate(fixable.items()):
            logger.info(f"  [{i+1}/{len(fixable)}] Fixing {name}...")
            classification = info['classification']
            school = info['school']

            # Strategy 3: Redirect — just use the redirect target
            if classification == SchoolClassification.REDIRECT_DOMAIN and 'new_url' in info:
                new_url = info['new_url']
                if self._validate_athletics_domain(new_url):
                    fixes.append({
                        'school_name': name,
                        'old_url': info['base_url'],
                        'new_url': new_url,
                        'method': 'redirect_follow',
                        'confidence': 'high',
                    })
                    logger.info(f"    -> Fixed via redirect: {new_url}")
                    continue

            # Strategy 1: Domain variations
            fix = self._try_domain_variations(name, info)
            if fix:
                fixes.append(fix)
                logger.info(f"    -> Fixed via domain variation: {fix['new_url']}")
                continue

            # Strategy 2: DuckDuckGo search
            fix = self._try_duckduckgo_search(name, info)
            if fix:
                fixes.append(fix)
                logger.info(f"    -> Fixed via DuckDuckGo search: {fix['new_url']}")
                continue

            logger.info(f"    -> Could not fix {name}")

        return fixes

    def _try_domain_variations(self, name: str, info: dict) -> dict | None:
        """Try common domain name variations."""
        old_url = info['base_url']
        hostname = urlparse(old_url).hostname
        if not hostname:
            return None

        # Extract parts from the hostname
        domain_base = hostname.replace('.com', '').replace('.org', '').replace('.net', '')

        # Generate variations
        variations = set()

        # Swap athletics <-> sports
        if 'athletics' in domain_base:
            variations.add(domain_base.replace('athletics', 'sports') + '.com')
        if 'sports' in domain_base:
            variations.add(domain_base.replace('sports', 'athletics') + '.com')

        # Add/remove common prefixes
        for prefix in ['go', 'the']:
            if domain_base.startswith(prefix):
                stripped = domain_base[len(prefix):]
                variations.add(stripped + '.com')
            else:
                variations.add(prefix + domain_base + '.com')

        # Try school name-based domains
        school_slug = re.sub(r'[^a-z0-9]', '', name.lower().split('(')[0].strip())
        variations.add(f"{school_slug}athletics.com")
        variations.add(f"{school_slug}sports.com")
        variations.add(f"go{school_slug}.com")

        # Remove the original domain from variations
        variations.discard(hostname)

        for variation in variations:
            url = f"https://{variation}"
            if self._validate_athletics_domain(url):
                return {
                    'school_name': name,
                    'old_url': old_url,
                    'new_url': url,
                    'method': 'domain_variation',
                    'confidence': 'medium',
                }
            time.sleep(0.3)

        return None

    def _try_duckduckgo_search(self, name: str, info: dict) -> dict | None:
        """Search DuckDuckGo for the school's baseball roster page."""
        query = f'"{name}" baseball roster'
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

        try:
            resp = self.session.get(search_url, timeout=10)
            if resp.status_code != 200:
                return None
        except requests.exceptions.RequestException:
            return None

        soup = BeautifulSoup(resp.text, 'lxml')

        # Parse result links — DuckDuckGo HTML results are in <a class="result__a">
        candidates = set()
        for link in soup.find_all('a', class_='result__a'):
            href = link.get('href', '')
            # DuckDuckGo wraps URLs; extract the actual URL
            if 'uddg=' in href:
                from urllib.parse import parse_qs
                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                if 'uddg' in qs:
                    href = qs['uddg'][0]

            parsed = urlparse(href)
            if not parsed.hostname:
                continue

            host = parsed.hostname
            # Prefer .edu or known athletics domains
            if any(pat in host for pat in ['.edu', 'athletics', 'sports', 'sidearmsports']):
                base = f"{parsed.scheme}://{host}"
                candidates.add(base)

        # Also check all links on the page
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if 'uddg=' in href:
                from urllib.parse import parse_qs
                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                if 'uddg' in qs:
                    href = qs['uddg'][0]
            parsed = urlparse(href)
            if parsed.hostname and 'baseball' in href.lower():
                base = f"{parsed.scheme}://{parsed.hostname}"
                candidates.add(base)

        old_host = urlparse(info['base_url']).hostname
        candidates.discard(info['base_url'])

        for candidate in candidates:
            candidate_host = urlparse(candidate).hostname
            if candidate_host == old_host:
                continue
            if self._validate_athletics_domain(candidate):
                return {
                    'school_name': name,
                    'old_url': info['base_url'],
                    'new_url': candidate,
                    'method': 'duckduckgo_search',
                    'confidence': 'medium',
                }
            time.sleep(0.3)

        # Brief delay between DuckDuckGo searches to be polite
        time.sleep(1.0)
        return None

    def _validate_athletics_domain(self, url: str) -> bool:
        """Check if a URL points to a working athletics site with baseball content."""
        try:
            resp = self.session.get(url, timeout=10, allow_redirects=True)
            if resp.status_code != 200:
                return False

            text = resp.text.lower()
            # Check it's not a parked page
            for indicator in PARKED_INDICATORS:
                if indicator in text:
                    return False

            # Check for athletics/sports content
            soup = BeautifulSoup(resp.text, 'lxml')
            sports_keywords = ['baseball', 'roster', 'schedule', 'athletics', 'sports']
            found = sum(1 for kw in sports_keywords if kw in text)
            return found >= 2

        except requests.exceptions.RequestException:
            return False


# ---------------------------------------------------------------------------
# Conference URL directory
# ---------------------------------------------------------------------------

# Maps conference abbreviation (from CSV) to conference website URL.
# For conferences that share an abbreviation across divisions (e.g., MIAA),
# use "{abbrev}_D2" or "{abbrev}_D3" keys; lookup tries qualified key first.
CONFERENCE_URLS = {
    # D2 conferences
    'SIAC': 'https://thesiac.com',
    'PSAC': 'https://psacsports.org',
    'CACC': 'https://caccathletics.com',
    'CIAA': 'https://theciaa.com',
    'MIAA_D2': 'https://themiaa.com',
    'MEC': 'https://mountaineast.org',
    'RMAC': 'https://rmacsports.org',
    'GAC': 'https://thegac.com',
    'LSC': 'https://lonestarconference.org',
    'GNAC_D2': 'https://gnacsports.com',
    'GLVC': 'https://glvcsports.com',
    'CCAA': 'https://goccaa.org',
    'G-MAC': 'https://gmacsports.com',
    'NSIC': 'https://nsicsports.org',
    'NE10': 'https://northeast10.org',
    'ECC': 'https://eccsports.org',
    'PacWest': 'https://pacwest.org',
    'SSC': 'https://sunshinestateconference.com',
    'GSC': 'https://gscsports.org',
    'PBC': 'https://peachbeltconference.org',
    'Conference Carolinas': 'https://conferencecarolinas.com',
    'SAC': 'https://thesac.com',
    'GLIAC': 'https://gliac.org',
    # D3 conferences (from d3baseball.com/conferences)
    'SUNYAC': 'https://sunyacsports.com',
    'CUNYAC': 'https://cunyathletics.com',
    'NAC': 'https://nacathletics.com',
    'NEAC': 'https://gounitedeast.com',
    'Empire 8': 'https://empire8.com',
    'Skyline': 'https://skylineconference.org',
    'AMCC': 'https://amccsports.org',
    'SLIAC': 'https://sliac.org',
    'UMAC': 'https://umacathletics.com',
    'PAC': 'https://pacathletics.org',
    'MASCAC': 'https://mascac.com',
    'GNAC_D3': 'https://thegnac.com',
    'USA South': 'https://usasouth.net',
    'ASC': 'https://ascsports.org',
    'Midwest': 'https://midwestconference.org',
    'SCAC': 'https://scacsports.com',
    'CAC': 'https://cacsports.com',
    'CSAC': 'https://gounitedeast.com',
    'Little East': 'https://littleeast.com',
    'OAC': 'https://oac.org',
    'WIAC': 'https://wiacsports.com',
    'CCIW': 'https://cciw.org',
    'Centennial': 'https://centennial.org',
    'UAA': 'https://uaasports.info',
    'NCAC': 'https://northcoast.org',
    'Landmark': 'https://landmarkconference.org',
    'NJAC': 'https://njacsports.com',
    'Heartland': 'https://heartlandconf.org',
    'MIAA_D3': 'https://miaa.org',
    'NACC': 'https://naccsports.org',
    'Atlantic East': 'https://atlanticeast.com',
    'CCC': 'https://cnesports.org',
    'MAC': 'https://gomacsports.com',
    'MIAC': 'https://miacathletics.com',
    'American Rivers': 'https://rollrivers.com',
    'SCIAC': 'https://thesciac.org',
}

# Common paths to try on conference sites to find member school listings
CONFERENCE_MEMBER_PATHS = [
    '',  # homepage
    '/index.aspx?path=baseball',
    '/sports/baseball',
    '/sports/bsb/index',
    '/member-institutions',
    '/about/member-institutions',
    '/standings.aspx?path=baseball',
]

# Domains to ignore when extracting external links from conference pages
IGNORE_DOMAINS = {
    'twitter.com', 'x.com', 'facebook.com', 'instagram.com', 'youtube.com',
    'tiktok.com', 'linkedin.com', 'ncaa.org', 'ncaa.com', 'google.com',
    'apple.com', 'spotify.com', 'amazon.com', 'sidearmstats.com',
    'sidearmsports.com', 'prestosports.com', 'daysmartrecreation.com',
    'hudl.com', 'nfhsnetwork.com', 'herosp.com', 'balldontlie.com',
    'hugedomains.com', 'sedo.com', 'godaddy.com',
}


def _get_conference_url(conference: str, division: str) -> str | None:
    """Look up conference website URL, handling division-qualified keys."""
    # Try division-qualified key first (for MIAA, GNAC which differ by division)
    qualified = f"{conference}_{division}"
    if qualified in CONFERENCE_URLS:
        return CONFERENCE_URLS[qualified]
    if conference in CONFERENCE_URLS:
        return CONFERENCE_URLS[conference]
    return None


def _normalize_name(name: str) -> str:
    """Normalize a school name for fuzzy matching."""
    n = name.lower().strip()
    # Remove common suffixes
    for suffix in [' university', ' college', ' institute of technology']:
        n = n.replace(suffix, '')
    # Expand abbreviations
    n = n.replace('st.', 'state').replace('mt.', 'mount')
    # Remove parenthetical state qualifiers
    n = re.sub(r'\s*\([^)]*\)', '', n)
    # Remove punctuation
    n = re.sub(r'[^a-z0-9\s]', '', n)
    # Collapse whitespace
    n = re.sub(r'\s+', ' ', n).strip()
    return n


# ---------------------------------------------------------------------------
# ConferenceDiscoverer
# ---------------------------------------------------------------------------

class ConferenceDiscoverer:
    """Scrape conference websites to find correct athletics URLs for missing schools."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def discover_all(self, classifications: dict, csv_schools: list) -> list:
        """Scrape conference sites for schools with incorrect URLs.
        Returns list of {school_name, old_url, new_url, method, confidence}."""
        # Build set of conferences that have fixable missing schools
        target_schools = {}
        for name, info in classifications.items():
            if info['classification'] == SchoolClassification.NO_BASEBALL:
                continue
            conf = info['school']['conference']
            div = info['school']['division']
            if conf == 'Independent':
                continue
            if conf not in target_schools:
                target_schools[conf] = []
            target_schools[conf].append({
                'name': name,
                'division': div,
                'old_url': info['base_url'],
            })

        # Build normalized name lookup from CSV
        name_lookup = {}
        for school in csv_schools:
            norm = _normalize_name(school['school_name'])
            name_lookup[norm] = school['school_name']
            # Also index by just the first word for short-name matching
            first_word = norm.split()[0] if norm.split() else ''
            if first_word and len(first_word) > 3:
                if first_word not in name_lookup:
                    name_lookup[first_word] = school['school_name']

        fixes = []
        conferences_scraped = 0
        total_confs = len(target_schools)

        for conf, missing_schools in sorted(target_schools.items()):
            conferences_scraped += 1
            div = missing_schools[0]['division']
            conf_url = _get_conference_url(conf, div)
            if not conf_url:
                logger.warning(f"  [{conferences_scraped}/{total_confs}] No URL for conference: {conf}")
                continue

            logger.info(f"  [{conferences_scraped}/{total_confs}] Scraping {conf} ({conf_url})...")
            school_urls = self._scrape_conference(conf, conf_url)

            if not school_urls:
                logger.info(f"    No school URLs extracted from {conf}")
                continue

            logger.info(f"    Found {len(school_urls)} school URLs on {conf} site")

            # Match extracted URLs to our missing schools
            missing_names = {s['name'] for s in missing_schools}
            old_url_map = {s['name']: s['old_url'] for s in missing_schools}

            for extracted_name, extracted_url in school_urls.items():
                matched_name = self._match_to_missing(
                    extracted_name, extracted_url, missing_names, name_lookup
                )
                if matched_name:
                    # Validate the URL actually works
                    validated_url = self._validate_url(extracted_url)
                    if validated_url:
                        fixes.append({
                            'school_name': matched_name,
                            'old_url': old_url_map.get(matched_name, ''),
                            'new_url': validated_url,
                            'method': 'conference_site',
                            'confidence': 'high',
                        })
                        missing_names.discard(matched_name)
                        logger.info(f"    -> Matched: {matched_name} = {validated_url}")

            time.sleep(1.0)  # courtesy delay between conferences

        return fixes

    def _scrape_conference(self, conf: str, conf_url: str) -> dict:
        """Fetch conference pages and extract school name → URL pairs."""
        all_school_urls = {}
        conf_host = urlparse(conf_url).hostname

        for path in CONFERENCE_MEMBER_PATHS:
            url = conf_url.rstrip('/') + path
            try:
                resp = self.session.get(url, timeout=15, allow_redirects=True)
                if resp.status_code != 200:
                    continue
            except requests.exceptions.RequestException:
                continue

            school_urls = self._extract_school_urls(resp.text, conf_host)
            all_school_urls.update(school_urls)

            # If we found a decent number of schools, don't need to try more paths
            if len(all_school_urls) >= 8:
                break

            time.sleep(0.5)

        return all_school_urls

    def _extract_school_urls(self, html: str, conf_host: str) -> dict:
        """Parse HTML to find school name → athletics URL pairs.
        Tries three strategies: SIDEARM JSON data, <a> tag extraction, raw URL regex."""
        school_urls = {}

        # Strategy 1: SIDEARM JSON — conference sites embed school data as JSON
        # Pattern: {"title": "School Name", "athletics_website": "http://..."}
        json_schools = self._extract_sidearm_json(html)
        if json_schools:
            school_urls.update(json_schools)

        # Strategy 2: Standard <a> tag extraction
        soup = BeautifulSoup(html, 'lxml')
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href or href.startswith('#') or href.startswith('javascript'):
                continue

            parsed = urlparse(href)
            host = parsed.hostname
            if not host:
                continue

            # Skip internal / non-athletics links
            if conf_host and host.replace('www.', '') == conf_host.replace('www.', ''):
                continue
            base_host = '.'.join(host.rsplit('.', 2)[-2:]) if '.' in host else host
            if base_host in IGNORE_DOMAINS:
                continue
            if any(x in host for x in ['ticketmaster', 'vivenu', 'shopify', 'merch',
                                        'cdninstagram', 'cloudflare', 'scorecardresearch',
                                        'transcend', 'tinyurl', 'statbroadcast']):
                continue

            scheme = parsed.scheme or 'https'
            base_url = f"{scheme}://{host}"

            # Get school name from link text or img alt
            text = link.get_text(strip=True)
            if not text or len(text) < 3 or len(text) > 80:
                img = link.find('img')
                if img and img.get('alt'):
                    text = img['alt'].strip()
                else:
                    continue

            if any(x in text.lower() for x in ['ticket', 'shop', 'store', 'donate',
                                                 'stream', 'watch', 'follow', 'app',
                                                 'privacy', 'terms', 'copyright',
                                                 'service', 'sidearm', 'powered']):
                continue

            if base_url not in {v for v in school_urls.values()}:
                school_urls[text] = base_url

        return school_urls

    def _extract_sidearm_json(self, html: str) -> dict:
        """Extract school name → URL pairs from SIDEARM embedded JSON data.
        SIDEARM conference sites embed school objects in "data":[...] arrays
        with title, athletics_website, and other fields."""
        school_urls = {}

        # Find "data":[ positions and extract the full JSON array via bracket counting
        for match in re.finditer(r'"data"\s*:\s*\[', html):
            start = match.end() - 1  # include the opening [
            depth = 0
            end = start
            for i in range(start, min(start + 100000, len(html))):
                if html[i] == '[':
                    depth += 1
                elif html[i] == ']':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

            if end <= start:
                continue

            try:
                arr = json.loads(html[start:end])
            except (json.JSONDecodeError, ValueError):
                continue

            if not isinstance(arr, list):
                continue

            for obj in arr:
                if not isinstance(obj, dict):
                    continue
                url = obj.get('athletics_website', '')
                if not url or not url.startswith('http'):
                    continue
                name = obj.get('title') or obj.get('short_display') or obj.get('school_name', '')
                if name and 'Logo' not in name:
                    school_urls[name] = url

            # If we found schools, no need to check more data arrays
            if school_urls:
                break

        return school_urls

    def _match_to_missing(self, extracted_name: str, extracted_url: str,
                          missing_names: set, name_lookup: dict) -> str | None:
        """Match an extracted school name/URL to one of our missing schools."""
        # Strategy 1: Exact match
        if extracted_name in missing_names:
            return extracted_name

        # Strategy 2: Normalized match
        norm_extracted = _normalize_name(extracted_name)
        for missing_name in missing_names:
            norm_missing = _normalize_name(missing_name)
            if norm_extracted == norm_missing:
                return missing_name

        # Strategy 3: Substring/containment match
        for missing_name in missing_names:
            norm_missing = _normalize_name(missing_name)
            # "fort valley state" in "fort valley state university"
            if norm_missing in norm_extracted or norm_extracted in norm_missing:
                return missing_name
            # Handle "IUP" / "Indiana (PA)" style — check if first significant word matches
            missing_words = norm_missing.split()
            extracted_words = norm_extracted.split()
            if missing_words and extracted_words:
                if missing_words[0] == extracted_words[0] and len(missing_words[0]) > 3:
                    return missing_name

        # Strategy 4: URL hostname matching — compare extracted URL to the missing schools' old URLs
        extracted_host = urlparse(extracted_url).hostname or ''
        for missing_name in missing_names:
            # Build slug from school name and check if it's in the hostname
            slug = re.sub(r'[^a-z]', '', _normalize_name(missing_name))
            if slug and len(slug) > 4 and slug in extracted_host.replace('.', ''):
                return missing_name

        return None

    def _validate_url(self, url: str) -> str | None:
        """Check URL resolves and isn't parked. Returns final URL after redirects."""
        try:
            resp = self.session.get(url, timeout=10, allow_redirects=True)
            if resp.status_code != 200:
                # Try https if http failed
                if url.startswith('http://'):
                    url_https = url.replace('http://', 'https://', 1)
                    resp = self.session.get(url_https, timeout=10, allow_redirects=True)
                    if resp.status_code != 200:
                        return None
                    url = url_https
                else:
                    return None

            text = resp.text.lower()
            for indicator in PARKED_INDICATORS:
                if indicator in text:
                    return None

            # Use the final URL after redirects (normalize to base)
            final = urlparse(resp.url)
            return f"{final.scheme}://{final.hostname}"

        except requests.exceptions.RequestException:
            return None


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------

class ReportGenerator:
    def __init__(self):
        self.reports_dir = Path(__file__).parent / 'reports'
        self.reports_dir.mkdir(exist_ok=True)

    def print_summary(self, classifications: dict):
        """Print a summary table to the console."""
        counts = {}
        for info in classifications.values():
            cat = info['classification'].value
            counts[cat] = counts.get(cat, 0) + 1

        print("\n" + "=" * 60)
        print("CLASSIFICATION SUMMARY")
        print("=" * 60)
        print(f"{'Category':<25} {'Count':>6}")
        print("-" * 35)

        # Sort by count descending
        for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
            fixable = ""
            if cat in ('PARKED_DOMAIN', 'REDIRECT_DOMAIN'):
                fixable = " [FIXABLE]"
            elif cat in ('DNS_DEAD', 'NO_BASEBALL'):
                fixable = " [skip]"
            elif cat in ('WRONG_URLS', 'ZERO_PLAYERS'):
                fixable = " [maybe]"
            print(f"  {cat:<23} {count:>6}{fixable}")

        total = sum(counts.values())
        print("-" * 35)
        print(f"  {'TOTAL':<23} {total:>6}")
        print("=" * 60)

    def save_classification_csv(self, classifications: dict, path: str = None):
        """Save classifications to CSV."""
        if path is None:
            path = str(self.reports_dir / 'classification_report.csv')

        rows = []
        for name, info in sorted(classifications.items()):
            rows.append({
                'school_name': name,
                'division': info['school']['division'],
                'conference': info['school']['conference'],
                'classification': info['classification'].value,
                'details': info['details'],
                'base_url': info['base_url'],
                'new_url': info.get('new_url', ''),
            })

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'school_name', 'division', 'conference', 'classification',
                'details', 'base_url', 'new_url'
            ])
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"Classification report saved to {path} ({len(rows)} schools)")

    def save_fixes_csv(self, fixes: list, path: str = None):
        """Save domain fixes to CSV."""
        if path is None:
            path = str(self.reports_dir / 'domain_fixes.csv')

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'school_name', 'old_url', 'new_url', 'method', 'confidence'
            ])
            writer.writeheader()
            writer.writerows(fixes)

        logger.info(f"Domain fixes saved to {path} ({len(fixes)} fixes)")

    def update_schools_csv(self, fixes: list, csv_path: str):
        """Apply domain fixes to schools_database.csv."""
        fix_map = {f['school_name']: f['new_url'] for f in fixes}

        # Read existing CSV
        rows = []
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['school_name'] in fix_map:
                    old = row['athletics_base_url']
                    row['athletics_base_url'] = fix_map[row['school_name']]
                    logger.info(f"  Updated {row['school_name']}: {old} -> {row['athletics_base_url']}")
                rows.append(row)

        # Write back
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"Updated {len(fix_map)} schools in {csv_path}")


# ---------------------------------------------------------------------------
# Rescrape helper
# ---------------------------------------------------------------------------

def rescrape_fixed_schools(fixes: list, csv_path: str):
    """Re-run the scraper on schools that got new domains."""
    from main import CollegeBaseballScraper

    scraper = CollegeBaseballScraper()

    # Reload CSV to get updated rows
    schools = []
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            schools.append(row)

    fixed_names = {f['school_name'] for f in fixes}
    fixed_schools = [s for s in schools if s['school_name'] in fixed_names]

    logger.info(f"Rescraping {len(fixed_schools)} schools with fixed domains...")
    success_count = 0

    for i, school in enumerate(fixed_schools):
        name = school['school_name']
        logger.info(f"  [{i+1}/{len(fixed_schools)}] Scraping {name} ({school['athletics_base_url']})")

        try:
            result = scraper.scrape_school(school)
            if result.get('success') and result.get('players'):
                player_count = scraper.db.save_school_data(result)
                logger.info(f"    -> Saved {player_count} players")
                success_count += 1
            else:
                errors = result.get('errors', [])
                logger.info(f"    -> Failed: {errors[:2] if errors else 'no players found'}")
        except Exception as e:
            logger.error(f"    -> Error: {e}")

    logger.info(f"\nRescrape complete: {success_count}/{len(fixed_schools)} schools succeeded")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_cached_classifications(reports_dir: Path) -> dict | None:
    """Load classifications from the cached CSV report."""
    path = reports_dir / 'classification_report.csv'
    if not path.exists():
        return None

    results = {}
    # Also need to reload school data from CSV for the school dict
    csv_path = str(Path(__file__).parent / 'schools_database.csv')
    school_map = {}
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            school_map[row['school_name']] = row

    with open(path, 'r', newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            name = row['school_name']
            school = school_map.get(name, {
                'school_name': name,
                'division': row.get('division', ''),
                'conference': row.get('conference', ''),
                'athletics_base_url': row.get('base_url', ''),
                'roster_url': '',
                'stats_url': '',
                'last_scraped': '',
                'scrape_priority': '',
            })
            results[name] = {
                'classification': SchoolClassification(row['classification']),
                'details': row['details'],
                'base_url': row['base_url'],
                'new_url': row.get('new_url', ''),
                'school': school,
            }

    logger.info(f"Loaded {len(results)} cached classifications from {path}")
    return results


def load_cached_fixes(reports_dir: Path) -> list | None:
    """Load fixes from the cached CSV report."""
    path = reports_dir / 'domain_fixes.csv'
    if not path.exists():
        return None

    fixes = []
    with open(path, 'r', newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            fixes.append(row)

    logger.info(f"Loaded {len(fixes)} cached fixes from {path}")
    return fixes


def main():
    parser = argparse.ArgumentParser(description='Validate & fix failed schools')
    parser.add_argument('--classify', action='store_true', help='Phase 1: classify all failed schools')
    parser.add_argument('--fix', action='store_true', help='Phase 2: auto-discover correct domains')
    parser.add_argument('--discover-from-conferences', action='store_true',
                        help='Phase 2b: scrape conference websites for correct URLs')
    parser.add_argument('--update-csv', action='store_true', help='Phase 3: apply fixes to schools_database.csv')
    parser.add_argument('--rescrape', action='store_true', help='Phase 4: re-run scraper on fixed schools')
    parser.add_argument('--all', action='store_true', help='Run all phases sequentially')
    args = parser.parse_args()

    if not any([args.classify, args.fix, args.discover_from_conferences,
                args.update_csv, args.rescrape, args.all]):
        parser.print_help()
        sys.exit(1)

    csv_path = str(Path(__file__).parent / 'schools_database.csv')
    reports_dir = Path(__file__).parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    report = ReportGenerator()

    run_classify = args.classify or args.all
    run_fix = args.fix or args.all
    run_conferences = args.discover_from_conferences or args.all
    run_update = args.update_csv or args.all
    run_rescrape = args.rescrape or args.all

    classifications = None
    fixes = None

    # Phase 1: Classify
    if run_classify:
        print("\n>>> Phase 1: Classifying failed schools...")
        validator = SchoolValidator(csv_path)
        failed = validator.get_failed_schools()
        print(f"Found {len(failed)} schools not in DB")

        classifications = validator.classify_all(failed)
        report.print_summary(classifications)
        report.save_classification_csv(classifications)
        validator.db.close()

    # Phase 2: Fix domains (domain variations + DuckDuckGo)
    if run_fix:
        if classifications is None:
            classifications = load_cached_classifications(reports_dir)
            if classifications is None:
                print("ERROR: No classification data. Run --classify first.")
                sys.exit(1)

        print("\n>>> Phase 2: Auto-discovering correct domains...")
        fixer = DomainFixer()
        fixes = fixer.fix_domains(classifications)

        if fixes:
            print(f"\nFound {len(fixes)} domain fixes:")
            for fix in fixes:
                print(f"  {fix['school_name']}: {fix['old_url']} -> {fix['new_url']} [{fix['method']}, {fix['confidence']}]")
        else:
            print("No fixable domains found.")

        report.save_fixes_csv(fixes)

    # Phase 2b: Discover from conference websites
    if run_conferences:
        if classifications is None:
            classifications = load_cached_classifications(reports_dir)
            if classifications is None:
                print("ERROR: No classification data. Run --classify first.")
                sys.exit(1)

        # Load CSV schools for name matching
        csv_schools = []
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                csv_schools.append(row)

        print("\n>>> Phase 2b: Scraping conference websites for correct URLs...")
        discoverer = ConferenceDiscoverer()
        conf_fixes = discoverer.discover_all(classifications, csv_schools)

        if conf_fixes:
            print(f"\nFound {len(conf_fixes)} schools via conference sites:")
            for fix in conf_fixes:
                print(f"  {fix['school_name']}: {fix['old_url']} -> {fix['new_url']}")

        # Save conference fixes separately
        report.save_fixes_csv(conf_fixes, str(reports_dir / 'conference_fixes.csv'))

        # Merge with existing fixes (conference fixes take priority — higher confidence)
        if fixes is None:
            fixes = load_cached_fixes(reports_dir) or []
        existing_names = {f['school_name'] for f in fixes}
        for fix in conf_fixes:
            if fix['school_name'] not in existing_names:
                fixes.append(fix)
        report.save_fixes_csv(fixes)
        print(f"Total fixes after merge: {len(fixes)}")

    # Phase 3: Update CSV
    if run_update:
        if fixes is None:
            fixes = load_cached_fixes(reports_dir)
            if fixes is None:
                print("ERROR: No fix data. Run --fix first.")
                sys.exit(1)

        if not fixes:
            print("\n>>> Phase 3: No fixes to apply.")
        else:
            print(f"\n>>> Phase 3: Applying {len(fixes)} fixes to {csv_path}...")
            report.update_schools_csv(fixes, csv_path)
            print("CSV updated.")

    # Phase 4: Rescrape
    if run_rescrape:
        if fixes is None:
            fixes = load_cached_fixes(reports_dir)
            if fixes is None:
                print("ERROR: No fix data. Run --fix first.")
                sys.exit(1)

        if not fixes:
            print("\n>>> Phase 4: No fixed schools to rescrape.")
        else:
            print(f"\n>>> Phase 4: Rescraping {len(fixes)} fixed schools...")
            rescrape_fixed_schools(fixes, csv_path)

    print("\nDone.")


if __name__ == '__main__':
    main()
