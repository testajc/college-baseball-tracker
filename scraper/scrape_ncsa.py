#!/usr/bin/env python3
"""
scrape_ncsa.py

Scrapes NCSA Sports division pages to build an authoritative list of all
NCAA baseball programs across D1, D2, and D3.

Uses Playwright to render JS content (the college lists are client-side rendered).

Output: ncsa_schools.json

Usage:
    pip install playwright && playwright install chromium
    python scrape_ncsa.py
"""

import json
import logging
import time
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    logger.error("Playwright is required. Install with: pip install playwright && playwright install chromium")
    sys.exit(1)

OUTPUT_FILE = Path(__file__).parent / 'ncsa_schools.json'

DIVISION_URLS = {
    'D1': 'https://www.ncsasports.org/baseball/division-1-colleges',
    'D2': 'https://www.ncsasports.org/baseball/division-2-colleges',
    'D3': 'https://www.ncsasports.org/baseball/division-3-colleges',
}

EXPECTED_COUNTS = {
    'D1': 300,
    'D2': 263,
    'D3': 390,
}


def scrape_division(page, division: str, url: str, max_retries: int = 3) -> list:
    """Scrape a single NCSA division page for school entries."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[{division}] Attempt {attempt}: navigating to {url}")
            page.goto(url, wait_until='networkidle', timeout=60000)

            # Wait for the college list to render
            # NCSA uses various selectors - try multiple
            selectors = [
                '.college-list',
                '.wp-block-ncsa-college-list',
                '[class*="CollegeList"]',
                '[data-testid*="college"]',
                'table',
            ]

            list_found = False
            for selector in selectors:
                try:
                    page.wait_for_selector(selector, timeout=10000)
                    list_found = True
                    logger.info(f"[{division}] Found content with selector: {selector}")
                    break
                except Exception:
                    continue

            if not list_found:
                logger.warning(f"[{division}] No known selector matched, will try parsing page anyway")

            # Scroll to bottom to trigger lazy-loading
            _scroll_to_bottom(page)

            # Give extra time for any final renders
            time.sleep(2)

            # Extract schools from the rendered page
            schools = _extract_schools(page, division)

            if schools:
                logger.info(f"[{division}] Extracted {len(schools)} schools")
                return schools
            else:
                logger.warning(f"[{division}] Attempt {attempt}: no schools extracted")

        except Exception as e:
            logger.error(f"[{division}] Attempt {attempt} failed: {e}")

        if attempt < max_retries:
            backoff = 2 ** attempt
            logger.info(f"[{division}] Retrying in {backoff}s...")
            time.sleep(backoff)

    logger.error(f"[{division}] All {max_retries} attempts failed")
    return []


def _scroll_to_bottom(page):
    """Scroll page incrementally to trigger lazy-loaded content."""
    prev_height = 0
    for _ in range(20):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
        curr_height = page.evaluate("document.body.scrollHeight")
        if curr_height == prev_height:
            break
        prev_height = curr_height


def _extract_schools(page, division: str) -> list:
    """Extract school entries from the rendered page using multiple strategies."""
    schools = []

    # Strategy 1: Look for structured college list items (links with school names)
    schools = page.evaluate("""() => {
        const results = [];
        const seen = new Set();

        // Strategy A: Look for college card/list items
        const cards = document.querySelectorAll(
            '.college-card, .college-item, [class*="CollegeCard"], ' +
            '[class*="college-list"] li, [class*="college-list"] a, ' +
            'table tbody tr'
        );

        for (const card of cards) {
            // Try to find name, state, conference
            let name = '';
            let state = '';
            let conference = '';
            let link = '';

            // Check if it's a table row
            const cells = card.querySelectorAll('td');
            if (cells.length >= 2) {
                name = cells[0]?.textContent?.trim() || '';
                state = cells.length >= 3 ? cells[1]?.textContent?.trim() : '';
                conference = cells.length >= 3 ? cells[2]?.textContent?.trim() :
                             cells[1]?.textContent?.trim() || '';
                const a = cells[0]?.querySelector('a');
                if (a) link = a.href || '';
            } else {
                // Card/list layout
                const nameEl = card.querySelector(
                    'h3, h4, .college-name, [class*="name"], a'
                );
                name = nameEl?.textContent?.trim() || card.textContent?.trim() || '';

                const stateEl = card.querySelector(
                    '.college-state, [class*="state"], [class*="location"]'
                );
                state = stateEl?.textContent?.trim() || '';

                const confEl = card.querySelector(
                    '.college-conference, [class*="conference"]'
                );
                conference = confEl?.textContent?.trim() || '';

                const a = card.tagName === 'A' ? card : card.querySelector('a');
                if (a) link = a.href || '';
            }

            // Clean up name (remove extra whitespace, trailing state/conf info)
            name = name.replace(/\\s+/g, ' ').trim();

            // Skip empty or too-short names, header rows, etc.
            if (!name || name.length < 3 || seen.has(name.toLowerCase())) continue;
            if (/^(school|college|university|name|institution)$/i.test(name)) continue;

            seen.add(name.toLowerCase());
            results.push({ name, state, conference, link });
        }

        // Strategy B: If few results, try all links that look like school pages
        if (results.length < 50) {
            const links = document.querySelectorAll('a[href*="/baseball/"]');
            for (const a of links) {
                const name = a.textContent?.trim();
                if (!name || name.length < 3 || seen.has(name.toLowerCase())) continue;
                if (/roster|stats|schedule|recruit|division/i.test(name)) continue;
                seen.add(name.toLowerCase());
                results.push({ name, state: '', conference: '', link: a.href || '' });
            }
        }

        return results;
    }""")

    # Post-process: add division tag
    for school in schools:
        school['division'] = division

    return schools


def scrape_ncsa_school_page(page, school_url: str) -> dict:
    """Try to scrape an individual NCSA school page for the athletics URL."""
    try:
        page.goto(school_url, wait_until='networkidle', timeout=30000)
        info = page.evaluate("""() => {
            const result = {};
            // Look for athletics website link
            const links = document.querySelectorAll('a[href]');
            for (const a of links) {
                const text = a.textContent?.toLowerCase() || '';
                const href = a.href || '';
                if ((text.includes('athletics') || text.includes('official site') ||
                     text.includes('website')) && href.includes('http')) {
                    result.athletics_url = href;
                    break;
                }
            }
            return result;
        }""")
        return info
    except Exception:
        return {}


def main():
    logger.info("=" * 60)
    logger.info("NCSA Baseball Program Scraper")
    logger.info("=" * 60)

    all_schools = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        for division, url in DIVISION_URLS.items():
            schools = scrape_division(page, division, url)
            all_schools.extend(schools)
            logger.info(f"[{division}] Total: {len(schools)} schools")
            time.sleep(2)

        browser.close()

    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_schools, f, indent=2)
    logger.info(f"Saved {len(all_schools)} schools to {OUTPUT_FILE}")

    # Validation summary
    print("\n" + "=" * 60)
    print("NCSA Scrape Results")
    print("=" * 60)

    division_counts = {}
    for s in all_schools:
        div = s.get('division', '?')
        division_counts[div] = division_counts.get(div, 0) + 1

    all_ok = True
    for div in ['D1', 'D2', 'D3']:
        count = division_counts.get(div, 0)
        expected = EXPECTED_COUNTS.get(div, 0)
        pct = (count / expected * 100) if expected > 0 else 0
        status = 'OK' if pct >= 95 else 'LOW'
        if pct < 95:
            all_ok = False
        print(f"  {div}: {count:>4} schools (expected ~{expected}, {pct:.0f}%) [{status}]")

    total = len(all_schools)
    total_expected = sum(EXPECTED_COUNTS.values())
    print(f"  Total: {total} schools (expected ~{total_expected})")
    print("=" * 60)

    if not all_ok:
        logger.warning("Some divisions are below 95% of expected count!")
        logger.warning("Check if NCSA page structure has changed.")

    return all_schools


if __name__ == '__main__':
    main()
