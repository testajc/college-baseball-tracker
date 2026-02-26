#!/usr/bin/env python3
"""
build_master_list.py

Cross-references NCSA, Wikipedia, and existing schools_database.csv to produce
an updated master school list with gap analysis.

Steps:
  1. Load NCSA results (ncsa_schools.json)
  2. Load Wikipedia results (wikipedia_schools.json)
  3. Load existing schools_database.csv
  4. Fuzzy-match school names across sources
  5. Identify gaps, dead URLs, and new schools
  6. Output updated schools_database.csv and gap_report.json

Usage:
    python build_master_list.py                    # Full cross-reference
    python build_master_list.py --dry-run          # Show changes without writing
    python build_master_list.py --report-only      # Only generate gap report
"""

import argparse
import csv
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SCRAPER_DIR = Path(__file__).parent
NCSA_FILE = SCRAPER_DIR / 'ncsa_schools.json'
WIKIPEDIA_FILE = SCRAPER_DIR / 'wikipedia_schools.json'
CSV_FILE = SCRAPER_DIR / 'schools_database.csv'
OUTPUT_CSV = SCRAPER_DIR / 'schools_database.csv'
GAP_REPORT_FILE = SCRAPER_DIR / 'gap_report.json'

CSV_FIELDS = [
    'school_name', 'division', 'conference', 'athletics_base_url',
    'roster_url', 'stats_url', 'last_scraped', 'scrape_priority'
]

# Common name variations for fuzzy matching
NAME_ALIASES = {
    # Abbreviation -> Full (or vice versa)
    'unc': 'north carolina',
    'unc greensboro': 'north carolina-greensboro',
    'unc wilmington': 'north carolina-wilmington',
    'unc asheville': 'north carolina-asheville',
    'uconn': 'connecticut',
    'umass': 'massachusetts',
    'umass lowell': 'massachusetts-lowell',
    'umbc': 'maryland-baltimore county',
    'unlv': 'nevada-las vegas',
    'utep': 'texas-el paso',
    'utsa': 'texas-san antonio',
    'ut arlington': 'texas-arlington',
    'ut martin': 'tennessee-martin',
    'usc upstate': 'south carolina upstate',
    'usc': 'southern california',
    'ucf': 'central florida',
    'ucsb': 'uc santa barbara',
    'ucla': 'california-los angeles',
    'lsu': 'louisiana state',
    'ole miss': 'mississippi',
    'pitt': 'pittsburgh',
    'smu': 'southern methodist',
    'tcu': 'texas christian',
    'vcu': 'virginia commonwealth',
    'fiu': 'florida international',
    'fau': 'florida atlantic',
    'liu': 'long island',
    'njit': 'new jersey institute of technology',
    'siue': 'southern illinois-edwardsville',
    'siu': 'southern illinois',
    'iupui': 'indiana-purdue-indianapolis',
    'ipfw': 'indiana-purdue-fort wayne',
    'suny': 'state university of new york',
    'penn': 'pennsylvania',
    'penn st.': 'penn state',
    'ohio st.': 'ohio state',
    'michigan st.': 'michigan state',
    'florida st.': 'florida state',
    'mississippi st.': 'mississippi state',
    'oklahoma st.': 'oklahoma state',
    'oregon st.': 'oregon state',
    'washington st.': 'washington state',
    'kansas st.': 'kansas state',
    'iowa st.': 'iowa state',
    'arizona st.': 'arizona state',
    'ball st.': 'ball state',
    'boise st.': 'boise state',
    'fresno st.': 'fresno state',
    'san diego st.': 'san diego state',
    'san jose st.': 'san jose state',
}


def normalize_name(name: str) -> str:
    """Normalize a school name for comparison."""
    n = name.lower().strip()
    # Remove common suffixes
    n = re.sub(r'\buniversity\b', '', n)
    n = re.sub(r'\bcollege\b', '', n)
    n = re.sub(r'\bstate\b', 'st.', n)
    n = re.sub(r'\buniv\.?\b', '', n)
    # Normalize punctuation
    n = re.sub(r'[\'"`]', '', n)
    n = re.sub(r'\s*-\s*', '-', n)
    n = re.sub(r'\s+', ' ', n).strip()
    n = n.rstrip('.')
    return n


def _build_norm_key(name: str) -> str:
    """Build an even more aggressive normalized key for matching."""
    n = name.lower().strip()
    # Remove all common suffixes
    for suffix in ['university', 'college', 'institute of technology',
                   'state university', 'university of', 'the']:
        n = n.replace(suffix, '')
    # Remove punctuation
    n = re.sub(r'[^a-z0-9 ]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def fuzzy_match_score(name1: str, name2: str) -> float:
    """Simple fuzzy match score between two names (0.0-1.0)."""
    # Try thefuzz if available, otherwise use simple approach
    try:
        from thefuzz import fuzz
        return fuzz.token_sort_ratio(name1, name2) / 100.0
    except ImportError:
        # Simple fallback: word overlap ratio
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)


def load_ncsa_schools() -> List[dict]:
    """Load NCSA scraped results."""
    if not NCSA_FILE.exists():
        logger.warning(f"NCSA file not found: {NCSA_FILE}")
        logger.warning("Run scrape_ncsa.py first")
        return []
    with open(NCSA_FILE) as f:
        return json.load(f)


def load_wikipedia_schools() -> List[dict]:
    """Load Wikipedia scraped results."""
    if not WIKIPEDIA_FILE.exists():
        logger.warning(f"Wikipedia file not found: {WIKIPEDIA_FILE}")
        logger.warning("Run scrape_wikipedia.py first (optional)")
        return []
    with open(WIKIPEDIA_FILE) as f:
        return json.load(f)


def load_csv_schools() -> List[dict]:
    """Load existing schools_database.csv."""
    if not CSV_FILE.exists():
        logger.warning(f"CSV file not found: {CSV_FILE}")
        return []
    schools = []
    with open(CSV_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            schools.append(dict(row))
    return schools


def build_name_index(schools: List[dict], name_key: str = 'name') -> Dict[str, dict]:
    """Build a lookup from normalized name to school entry."""
    index = {}
    for s in schools:
        name = s.get(name_key, s.get('school_name', ''))
        norm = normalize_name(name)
        key = _build_norm_key(name)
        index[norm] = s
        if key != norm:
            index[key] = s
        # Also index any known aliases
        for alias, canonical in NAME_ALIASES.items():
            if alias in norm or canonical in norm:
                index[alias] = s
                index[canonical] = s
    return index


def find_best_match(name: str, index: Dict[str, dict],
                    all_names: List[str]) -> Optional[Tuple[str, float]]:
    """Find the best match for a name in the index."""
    norm = normalize_name(name)
    key = _build_norm_key(name)

    # Exact match
    if norm in index:
        return norm, 1.0
    if key in index:
        return key, 1.0

    # Check aliases
    lower = name.lower().strip()
    if lower in NAME_ALIASES:
        alias_norm = normalize_name(NAME_ALIASES[lower])
        if alias_norm in index:
            return alias_norm, 1.0

    # Fuzzy match against all names
    best_match = None
    best_score = 0.0

    for candidate in all_names:
        score = fuzzy_match_score(norm, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= 0.80:
        return best_match, best_score

    return None


def cross_reference(ncsa: List[dict], wikipedia: List[dict],
                    csv_schools: List[dict]) -> dict:
    """Cross-reference all three sources and produce a master analysis."""
    # Build indexes
    csv_index = build_name_index(csv_schools, 'school_name')
    csv_names = list(csv_index.keys())

    wiki_index = build_name_index(wikipedia, 'name')

    results = {
        'matched': [],         # In NCSA and CSV
        'new_schools': [],     # In NCSA but NOT in CSV (need to add)
        'csv_only': [],        # In CSV but NOT in NCSA (potentially defunct)
        'url_updates': [],     # In CSV but URL might need updating
        'stats': {},
    }

    ncsa_matched_csv = set()

    for school in ncsa:
        ncsa_name = school.get('name', '')
        division = school.get('division', '')

        match = find_best_match(ncsa_name, csv_index, csv_names)

        if match:
            match_name, score = match
            csv_entry = csv_index[match_name]
            ncsa_matched_csv.add(csv_entry.get('school_name', ''))

            results['matched'].append({
                'ncsa_name': ncsa_name,
                'csv_name': csv_entry.get('school_name', ''),
                'division': division,
                'conference': school.get('conference', '') or csv_entry.get('conference', ''),
                'match_score': score,
                'has_url': bool(csv_entry.get('athletics_base_url', '')),
            })
        else:
            # Check Wikipedia for additional info
            wiki_match = find_best_match(ncsa_name, wiki_index, list(wiki_index.keys()))
            wiki_conf = ''
            if wiki_match:
                wiki_entry = wiki_index.get(wiki_match[0], {})
                wiki_conf = wiki_entry.get('conference', '')

            results['new_schools'].append({
                'name': ncsa_name,
                'division': division,
                'conference': school.get('conference', '') or wiki_conf,
                'state': school.get('state', ''),
                'ncsa_link': school.get('link', ''),
                'in_wikipedia': wiki_match is not None,
            })

    # Find CSV schools not in NCSA
    for csv_school in csv_schools:
        csv_name = csv_school.get('school_name', '')
        if csv_name not in ncsa_matched_csv:
            results['csv_only'].append({
                'name': csv_name,
                'division': csv_school.get('division', ''),
                'conference': csv_school.get('conference', ''),
                'url': csv_school.get('athletics_base_url', ''),
            })

    # Stats
    results['stats'] = {
        'ncsa_total': len(ncsa),
        'wikipedia_total': len(wikipedia),
        'csv_total': len(csv_schools),
        'matched': len(results['matched']),
        'new_schools': len(results['new_schools']),
        'csv_only': len(results['csv_only']),
        'by_division': {},
    }

    for div in ['D1', 'D2', 'D3']:
        div_ncsa = sum(1 for s in ncsa if s.get('division') == div)
        div_matched = sum(1 for s in results['matched'] if s.get('division') == div)
        div_new = sum(1 for s in results['new_schools'] if s.get('division') == div)
        results['stats']['by_division'][div] = {
            'ncsa': div_ncsa,
            'matched': div_matched,
            'new': div_new,
        }

    return results


def update_csv(csv_schools: List[dict], new_schools: List[dict],
               dry_run: bool = False) -> List[dict]:
    """Add new schools to the CSV school list."""
    existing_names = {s['school_name'].lower() for s in csv_schools}
    added = 0

    for school in new_schools:
        name = school['name']
        if name.lower() in existing_names:
            continue

        division = school.get('division', 'D3')
        conference = school.get('conference', '')

        # Set priority based on division
        priority = {'D1': 'high', 'D2': 'medium', 'D3': 'low'}.get(division, 'low')

        new_entry = {
            'school_name': name,
            'division': division,
            'conference': conference,
            'athletics_base_url': '',  # Unknown — will need discovery
            'roster_url': '/sports/baseball/roster',
            'stats_url': '/sports/baseball/stats',
            'last_scraped': '',
            'scrape_priority': priority,
        }

        csv_schools.append(new_entry)
        existing_names.add(name.lower())
        added += 1

    logger.info(f"Added {added} new schools to the list")
    return csv_schools


def write_csv(schools: List[dict], output_path: Path):
    """Write schools to CSV file."""
    # Sort by division then name
    div_order = {'D1': 0, 'D2': 1, 'D3': 2}
    schools.sort(key=lambda s: (div_order.get(s.get('division', 'D3'), 3),
                                s.get('school_name', '')))

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for school in schools:
            # Ensure all fields exist
            row = {field: school.get(field, '') for field in CSV_FIELDS}
            writer.writerow(row)

    logger.info(f"Wrote {len(schools)} schools to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Cross-reference school sources')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show changes without writing')
    parser.add_argument('--report-only', action='store_true',
                        help='Only generate gap report')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Building Master School List")
    logger.info("=" * 60)

    # Load all sources
    ncsa = load_ncsa_schools()
    wikipedia = load_wikipedia_schools()
    csv_schools = load_csv_schools()

    if not ncsa:
        logger.error("No NCSA data available. Run scrape_ncsa.py first.")
        return

    logger.info(f"Loaded: NCSA={len(ncsa)}, Wikipedia={len(wikipedia)}, CSV={len(csv_schools)}")

    # Cross-reference
    results = cross_reference(ncsa, wikipedia, csv_schools)

    # Save gap report
    with open(GAP_REPORT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Gap report saved to {GAP_REPORT_FILE}")

    # Print summary
    print("\n" + "=" * 60)
    print("Cross-Reference Summary")
    print("=" * 60)
    print(f"  NCSA schools:      {results['stats']['ncsa_total']}")
    print(f"  Wikipedia schools:  {results['stats']['wikipedia_total']}")
    print(f"  CSV schools:        {results['stats']['csv_total']}")
    print(f"  Matched (NCSA+CSV): {results['stats']['matched']}")
    print(f"  New (NCSA only):    {results['stats']['new_schools']}")
    print(f"  CSV only (not NCSA):{results['stats']['csv_only']}")
    print()

    for div in ['D1', 'D2', 'D3']:
        ds = results['stats']['by_division'].get(div, {})
        print(f"  {div}: {ds.get('ncsa', 0)} NCSA, "
              f"{ds.get('matched', 0)} matched, "
              f"{ds.get('new', 0)} new to add")

    if results['new_schools']:
        print(f"\n  New schools to add ({len(results['new_schools'])}):")
        for s in results['new_schools'][:20]:
            wiki_tag = ' [wiki]' if s.get('in_wikipedia') else ''
            print(f"    + {s['name']} ({s['division']}) "
                  f"{s.get('conference', '')}{wiki_tag}")
        if len(results['new_schools']) > 20:
            print(f"    ... and {len(results['new_schools']) - 20} more")

    if results['csv_only']:
        print(f"\n  CSV-only schools (not in NCSA, possibly defunct): "
              f"{len(results['csv_only'])}")
        for s in results['csv_only'][:10]:
            print(f"    ? {s['name']} ({s['division']}) {s.get('conference', '')}")
        if len(results['csv_only']) > 10:
            print(f"    ... and {len(results['csv_only']) - 10} more")

    print("=" * 60)

    if args.report_only:
        logger.info("Report-only mode — not updating CSV")
        return

    # Update CSV with new schools
    if results['new_schools']:
        if args.dry_run:
            logger.info(f"DRY RUN: Would add {len(results['new_schools'])} new schools to CSV")
        else:
            csv_schools = update_csv(csv_schools, results['new_schools'])
            write_csv(csv_schools, OUTPUT_CSV)
            logger.info(f"Updated {OUTPUT_CSV} with {len(csv_schools)} total schools")
    else:
        logger.info("No new schools to add — CSV is already complete")


if __name__ == '__main__':
    main()
