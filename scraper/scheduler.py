# scraper/scheduler.py

from datetime import date
from typing import List, Dict
import csv
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SmartScheduler:
    """
    Determines which schools to scrape each day based on:
    - Division priority (D1 > D2 > D3)
    - Last scrape time
    - Day of week rotation
    """

    # How often each division should be updated
    UPDATE_FREQUENCY = {
        'D1': 1,  # Every day
        'D2': 2,  # Every 2 days
        'D3': 3,  # Every 3 days
    }

    def __init__(self, schools_db_path: str = None):
        if schools_db_path is None:
            schools_db_path = str(Path(__file__).parent / 'schools_database.csv')
        self.schools_db_path = schools_db_path
        self.schools = self._load_schools(schools_db_path)
        self.history_file = Path(__file__).parent / 'scrape_history.json'
        self.scrape_history = self._load_history()

    def _load_schools(self, path: str) -> List[Dict]:
        """Load schools from CSV"""
        schools = []
        p = Path(path)
        if not p.exists():
            logger.warning(f"Schools database not found at {path}")
            return schools
        with open(p, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                schools.append(row)
        logger.info(f"Loaded {len(schools)} schools from database")
        return schools

    def _load_history(self) -> Dict:
        """Load scrape history"""
        if self.history_file.exists():
            return json.loads(self.history_file.read_text())
        return {'last_scraped': {}, 'initial_scrape_complete': False}

    def _save_history(self):
        """Save scrape history"""
        self.history_file.write_text(json.dumps(self.scrape_history, indent=2))

    def mark_scraped(self, school_name: str):
        """Mark a school as scraped today"""
        self.scrape_history['last_scraped'][school_name] = date.today().isoformat()
        self._save_history()

    def is_initial_scrape_complete(self) -> bool:
        """Check if we've scraped all schools at least once"""
        if self.scrape_history.get('initial_scrape_complete'):
            return True

        scraped_schools = set(self.scrape_history['last_scraped'].keys())
        all_schools = set(s['school_name'] for s in self.schools)

        if not all_schools:
            return False

        if scraped_schools >= all_schools:
            self.scrape_history['initial_scrape_complete'] = True
            self._save_history()
            return True

        return False

    def get_schools_to_scrape_today(self) -> List[Dict]:
        """Get list of schools that should be scraped today"""
        today = date.today()

        # If initial scrape not complete, return unscraped schools
        if not self.is_initial_scrape_complete():
            return self._get_initial_scrape_batch()

        # Otherwise, use smart rotation
        return self._get_daily_update_batch(today)

    def _get_initial_scrape_batch(self) -> List[Dict]:
        """Get next batch for initial scrape (100 schools)"""
        scraped = set(self.scrape_history['last_scraped'].keys())
        unscraped = [s for s in self.schools if s['school_name'] not in scraped]

        # Prioritize by division: D1 first, then D2, then D3
        unscraped.sort(key=lambda x: {'D1': 0, 'D2': 1, 'D3': 2}.get(x.get('division', ''), 3))

        from config import INITIAL_SCRAPE_CONFIG
        max_schools = INITIAL_SCRAPE_CONFIG['max_schools_per_day']

        return unscraped[:max_schools]

    def _get_daily_update_batch(self, today: date) -> List[Dict]:
        """Get schools for daily update based on rotation"""
        schools_to_scrape = []

        for school in self.schools:
            division = school.get('division', '')
            frequency = self.UPDATE_FREQUENCY.get(division, 3)

            # Check when last scraped
            last_scraped_str = self.scrape_history['last_scraped'].get(school['school_name'])

            if last_scraped_str:
                last_scraped = date.fromisoformat(last_scraped_str)
                days_since = (today - last_scraped).days

                # Scrape if enough days have passed
                if days_since >= frequency:
                    schools_to_scrape.append(school)
            else:
                # Never scraped - add it
                schools_to_scrape.append(school)

        # Sort by priority: D1 first (most important to be fresh)
        schools_to_scrape.sort(key=lambda x: {'D1': 0, 'D2': 1, 'D3': 2}.get(x.get('division', ''), 3))

        return schools_to_scrape

    def get_scrape_config(self) -> Dict:
        """Get appropriate config based on scrape phase"""
        if self.is_initial_scrape_complete():
            from config import DAILY_UPDATE_CONFIG
            return DAILY_UPDATE_CONFIG
        else:
            from config import INITIAL_SCRAPE_CONFIG
            return INITIAL_SCRAPE_CONFIG

    def get_status_report(self) -> str:
        """Get human-readable status report"""
        total_schools = len(self.schools)
        scraped_schools = len(self.scrape_history['last_scraped'])

        if total_schools == 0:
            return (
                "\n========================================\n"
                "SCRAPER STATUS REPORT\n"
                "========================================\n"
                "No schools in database. Run 'python build_schools_db.py' first.\n"
                "========================================\n"
            )

        d1_total = len([s for s in self.schools if s.get('division') == 'D1'])
        d2_total = len([s for s in self.schools if s.get('division') == 'D2'])
        d3_total = len([s for s in self.schools if s.get('division') == 'D3'])

        d1_scraped = len([s for s in self.schools
                         if s.get('division') == 'D1'
                         and s['school_name'] in self.scrape_history['last_scraped']])
        d2_scraped = len([s for s in self.schools
                         if s.get('division') == 'D2'
                         and s['school_name'] in self.scrape_history['last_scraped']])
        d3_scraped = len([s for s in self.schools
                         if s.get('division') == 'D3'
                         and s['school_name'] in self.scrape_history['last_scraped']])

        phase = 'Daily Updates' if self.is_initial_scrape_complete() else 'Initial Scrape'
        pct = 100 * scraped_schools / total_schools

        d1_pct = (100 * d1_scraped / d1_total) if d1_total else 0
        d2_pct = (100 * d2_scraped / d2_total) if d2_total else 0
        d3_pct = (100 * d3_scraped / d3_total) if d3_total else 0

        today_count = len(self.get_schools_to_scrape_today())

        report = f"""
========================================
SCRAPER STATUS REPORT
========================================
Phase: {phase}

Overall Progress: {scraped_schools}/{total_schools} schools ({pct:.1f}%)

By Division:
  D1: {d1_scraped}/{d1_total} ({d1_pct:.1f}%) - Updated daily
  D2: {d2_scraped}/{d2_total} ({d2_pct:.1f}%) - Updated every 2 days
  D3: {d3_scraped}/{d3_total} ({d3_pct:.1f}%) - Updated every 3 days

Schools to scrape today: {today_count}
========================================
"""
        return report
