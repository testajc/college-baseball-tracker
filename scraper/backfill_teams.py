#!/usr/bin/env python3
"""
backfill_teams.py

Ensures every school in the master CSV exists as a team in the database,
even if no roster data has been scraped yet. This guarantees 100% team
coverage on the website — teams without players simply show empty rosters.

Uses database.py:upsert_team() which handles conflict resolution via
a stable ncaa_id generated from school_name + division.

Usage:
    python backfill_teams.py                # Backfill all teams
    python backfill_teams.py --dry-run      # Show what would be backfilled
    python backfill_teams.py --stats        # Show current DB vs CSV coverage
"""

import argparse
import csv
import logging
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

SCRAPER_DIR = Path(__file__).parent
CSV_FILE = SCRAPER_DIR / 'schools_database.csv'


def load_csv_schools() -> list:
    """Load schools from the CSV database."""
    if not CSV_FILE.exists():
        logger.error(f"CSV file not found: {CSV_FILE}")
        sys.exit(1)

    schools = []
    with open(CSV_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            schools.append(dict(row))
    return schools


def main():
    parser = argparse.ArgumentParser(description='Backfill all teams into database')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be backfilled without writing to DB')
    parser.add_argument('--stats', action='store_true',
                        help='Show current coverage stats')
    args = parser.parse_args()

    from database import DatabaseManager
    db = DatabaseManager()

    csv_schools = load_csv_schools()
    existing_teams = db.get_schools_in_db()

    logger.info(f"CSV schools: {len(csv_schools)}")
    logger.info(f"Teams already in DB: {len(existing_teams)}")

    # Find schools not yet in DB
    missing = [s for s in csv_schools if s['school_name'] not in existing_teams]

    # Division breakdown
    div_counts = {}
    for s in csv_schools:
        div = s.get('division', '?')
        div_counts[div] = div_counts.get(div, 0) + 1

    div_in_db = {}
    for s in csv_schools:
        if s['school_name'] in existing_teams:
            div = s.get('division', '?')
            div_in_db[div] = div_in_db.get(div, 0) + 1

    # Show stats
    print("\n" + "=" * 60)
    print("Team Coverage Report")
    print("=" * 60)
    print(f"{'Division':<10} {'In DB':<8} {'In CSV':<8} {'Missing':<8} {'Coverage'}")
    print("-" * 50)
    for div in ['D1', 'D2', 'D3']:
        total = div_counts.get(div, 0)
        in_db = div_in_db.get(div, 0)
        miss = total - in_db
        pct = (in_db / total * 100) if total > 0 else 0
        print(f"{div:<10} {in_db:<8} {total:<8} {miss:<8} {pct:.1f}%")

    total_csv = len(csv_schools)
    total_db = len(existing_teams)
    total_missing = len(missing)
    total_pct = (total_db / total_csv * 100) if total_csv > 0 else 0
    print("-" * 50)
    print(f"{'Total':<10} {total_db:<8} {total_csv:<8} {total_missing:<8} {total_pct:.1f}%")
    print("=" * 60)

    if args.stats:
        db.close()
        return

    if not missing:
        print("\nAll teams already in DB — nothing to backfill!")
        db.close()
        return

    print(f"\nSchools to backfill: {len(missing)}")

    if args.dry_run:
        print("\nDRY RUN — would backfill these schools:")
        for s in missing[:30]:
            print(f"  + {s['school_name']} ({s.get('division', '?')}) "
                  f"[{s.get('conference', '')}]")
        if len(missing) > 30:
            print(f"  ... and {len(missing) - 30} more")
        db.close()
        return

    # Backfill all missing teams
    success = 0
    errors = 0

    for school in missing:
        name = school['school_name']
        division = school.get('division', 'D3')
        conference = school.get('conference', '')

        try:
            team_id = db.upsert_team(name, division, conference)
            success += 1
            if success % 50 == 0:
                logger.info(f"Backfilled {success}/{len(missing)} teams...")
        except Exception as e:
            logger.error(f"Failed to backfill {name}: {e}")
            errors += 1

    db.close()

    print(f"\nBackfill complete!")
    print(f"  Successfully backfilled: {success} teams")
    if errors:
        print(f"  Errors: {errors}")

    # Show final coverage
    print(f"  Total teams in DB: ~{total_db + success}")
    final_pct = ((total_db + success) / total_csv * 100) if total_csv > 0 else 0
    print(f"  Coverage: {final_pct:.1f}%")


if __name__ == '__main__':
    main()
