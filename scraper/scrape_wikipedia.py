#!/usr/bin/env python3
"""
scrape_wikipedia.py

Scrapes Wikipedia's structured HTML tables for NCAA D1 and D2 baseball programs.
D3 has no single Wikipedia table, so we rely on NCSA for D3.

Output: wikipedia_schools.json

Usage:
    python scrape_wikipedia.py
"""

import json
import logging
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

OUTPUT_FILE = Path(__file__).parent / 'wikipedia_schools.json'

WIKIPEDIA_URLS = {
    'D1': 'https://en.wikipedia.org/wiki/List_of_NCAA_Division_I_baseball_programs',
    'D2': 'https://en.wikipedia.org/wiki/List_of_NCAA_Division_II_baseball_programs',
}

HEADERS = {
    'User-Agent': 'CollegeBaseballTracker/1.0 (educational project; '
                  'https://github.com/testajc/college-baseball-tracker)'
}


def scrape_wikipedia_table(url: str, division: str) -> list:
    """Scrape a Wikipedia list-of-programs page for school entries."""
    logger.info(f"[{division}] Fetching {url}")

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')
    schools = []

    # Wikipedia program tables are typically <table class="wikitable sortable">
    tables = soup.find_all('table', class_='wikitable')
    logger.info(f"[{division}] Found {len(tables)} wikitables")

    for table in tables:
        headers = []
        for th in table.find_all('th'):
            headers.append(th.get_text(strip=True).lower())

        # Identify which column contains what
        name_col = _find_column(headers, ['school', 'team', 'institution', 'university', 'program'])
        conf_col = _find_column(headers, ['conference', 'conf'])
        state_col = _find_column(headers, ['state', 'location', 'city'])
        nickname_col = _find_column(headers, ['nickname', 'mascot'])

        if name_col is None:
            continue

        logger.info(f"[{division}] Parsing table with columns: {headers}")

        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) <= name_col:
                continue

            name = cells[name_col].get_text(strip=True)
            # Clean up name — remove footnote references like [1], [a]
            name = re.sub(r'\[.*?\]', '', name).strip()

            if not name or len(name) < 2:
                continue

            # Skip header-like rows
            if name.lower() in ('school', 'team', 'institution', 'total'):
                continue

            school = {
                'name': name,
                'division': division,
                'conference': '',
                'state': '',
                'nickname': '',
            }

            if conf_col is not None and conf_col < len(cells):
                conf = cells[conf_col].get_text(strip=True)
                school['conference'] = re.sub(r'\[.*?\]', '', conf).strip()

            if state_col is not None and state_col < len(cells):
                state = cells[state_col].get_text(strip=True)
                school['state'] = re.sub(r'\[.*?\]', '', state).strip()

            if nickname_col is not None and nickname_col < len(cells):
                nick = cells[nickname_col].get_text(strip=True)
                school['nickname'] = re.sub(r'\[.*?\]', '', nick).strip()

            # Try to extract athletics URL from link in name cell
            link = cells[name_col].find('a', href=True)
            if link:
                href = link.get('href', '')
                if href.startswith('/wiki/'):
                    school['wikipedia_url'] = f"https://en.wikipedia.org{href}"

            schools.append(school)

        if schools:
            break  # Use first table that yields results

    logger.info(f"[{division}] Extracted {len(schools)} schools")
    return schools


def _find_column(headers: list, keywords: list) -> int:
    """Find the index of a column matching any of the keywords."""
    for i, h in enumerate(headers):
        for kw in keywords:
            if kw in h:
                return i
    return None


def main():
    logger.info("=" * 60)
    logger.info("Wikipedia NCAA Baseball Program Scraper")
    logger.info("=" * 60)

    all_schools = []

    for division, url in WIKIPEDIA_URLS.items():
        schools = scrape_wikipedia_table(url, division)
        all_schools.extend(schools)
        logger.info(f"[{division}] Total: {len(schools)} schools")
        time.sleep(2)  # Be respectful

    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_schools, f, indent=2)
    logger.info(f"Saved {len(all_schools)} schools to {OUTPUT_FILE}")

    # Summary
    print("\n" + "=" * 60)
    print("Wikipedia Scrape Results")
    print("=" * 60)

    for div in ['D1', 'D2']:
        count = sum(1 for s in all_schools if s['division'] == div)
        print(f"  {div}: {count} schools")

    print(f"  Total: {len(all_schools)} schools (D1 + D2 only)")
    print("  Note: D3 not available on Wikipedia — use NCSA for D3")
    print("=" * 60)

    return all_schools


if __name__ == '__main__':
    main()
