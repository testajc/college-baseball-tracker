# scraper/main.py

import argparse
import logging
import time
import random
import sys
from datetime import datetime, date
from pathlib import Path

from config import INITIAL_SCRAPE_CONFIG, DAILY_UPDATE_CONFIG, ERROR_CONFIG, SEASON_START_DATE, BROWSER_CONFIG
from scheduler import SmartScheduler
from request_handler import ProtectedRequestHandler
from parsers.sidearm_parser import SidearmParser
from database import DatabaseManager
from url_discovery import UrlDiscoverer
from browser_scraper import BrowserScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CollegeBaseballScraper:
    def __init__(self):
        self.scheduler = SmartScheduler()
        self.config = self.scheduler.get_scrape_config()
        self.request_handler = ProtectedRequestHandler(self.config, ERROR_CONFIG)
        self.parser = SidearmParser()
        self.db = DatabaseManager()
        self.url_discoverer = UrlDiscoverer()
        self.browser_scraper = BrowserScraper(self.parser, BROWSER_CONFIG)
        self.schools_scraped_today = 0
        self.total_players_scraped = 0

    def should_scrape(self, force: bool = False) -> bool:
        """Check if season has started"""
        if force:
            logger.warning("Force flag set - scraping even though season may not have started")
            return True

        season_start = datetime.strptime(SEASON_START_DATE, '%Y-%m-%d').date()
        today = date.today()

        if today < season_start:
            days_until = (season_start - today).days
            logger.warning(f"2026 season hasn't started yet!")
            logger.warning(f"Season starts: {season_start.strftime('%B %d, %Y')}")
            logger.warning(f"Days until season: {days_until}")
            logger.warning("Use --force to scrape anyway (will get old/no data)")
            return False

        return True

    def scrape_school(self, school: dict) -> dict:
        """Scrape a single school"""
        school_name = school['school_name']
        base_url = school.get('athletics_base_url', '').rstrip('/')

        logger.info(f"Scraping: {school_name} ({school.get('division', '?')})")

        result = {
            'school': school_name,
            'division': school.get('division', ''),
            'conference': school.get('conference', ''),
            'players': [],
            'success': False,
            'errors': []
        }

        if not base_url:
            result['errors'].append(f"No athletics URL for {school_name}")
            return result

        # URL patterns to try for roster and stats
        # SIDEARM standard paths first, then PrestoSports / non-SIDEARM fallbacks
        ROSTER_PATHS = [
            school.get('roster_url', '/sports/baseball/roster'),
            '/sports/baseball/roster',
            '/sports/baseball/roster/2026',
            # PrestoSports / non-SIDEARM patterns
            '/sport/m-basebl/roster',
            '/sports/bsb/roster',
            '/sports/mens-baseball/roster',
            '/teams/baseball/roster',
            '/roster.aspx?path=baseball',
            '/athletics/baseball/roster',
            '/baseball/roster/',
        ]
        STATS_PATHS = [
            school.get('stats_url', '/sports/baseball/stats'),
            '/sports/baseball/stats',
            '/sports/baseball/stats/2026',
            # PrestoSports / non-SIDEARM patterns
            '/sport/m-basebl/stats',
            '/sports/bsb/stats',
            '/sports/mens-baseball/stats',
            '/teams/baseball/stats',
            '/teamstats.aspx?path=baseball',
            '/athletics/baseball/stats',
            '/baseball/stats/',
        ]
        # Deduplicate while preserving order
        ROSTER_PATHS = list(dict.fromkeys(ROSTER_PATHS))
        STATS_PATHS = list(dict.fromkeys(STATS_PATHS))

        # Try roster URL patterns
        response = None
        roster_url = None
        base_domain = base_url.split('//')[1].split('/')[0] if '//' in base_url else base_url
        effective_base_url = base_url  # May change if we follow a redirect
        for path in ROSTER_PATHS:
            url = f"{effective_base_url}{path}" if not path.startswith('http') else path
            logger.debug(f"Trying roster: {url}")
            resp = self.request_handler.get(url)
            if resp:
                resp_domain = resp.url.split('//')[1].split('/')[0] if '//' in resp.url else ''
                resp_path = resp.url.split(resp_domain, 1)[1] if resp_domain in resp.url else '/'

                if resp_domain != base_domain:
                    # Check if it's a related domain (subdomain/sibling)
                    if UrlDiscoverer._is_related_domain(resp_domain, base_domain):
                        # Follow the redirect — update base URL for remaining paths
                        scheme = resp.url.split('//')[0] if '//' in resp.url else 'https:'
                        new_base = f"{scheme}//{resp_domain}"
                        logger.info(f"  Redirected to related domain ({resp_domain}), "
                                    f"updating base URL to {new_base}")
                        effective_base_url = new_base

                        # Only accept if the path is meaningful (not just homepage)
                        if len(resp_path.strip('/')) < 5:
                            logger.info(f"  Redirected to homepage of related domain, "
                                        f"trying remaining paths on {new_base}")
                            continue
                    else:
                        # Truly unrelated domain — skip
                        logger.info(f"  Redirected to unrelated domain ({resp_domain}), skipping")
                        break

                # Skip homepage redirects on same domain
                if resp_domain == base_domain and len(resp_path.strip('/')) < 5:
                    final_url = resp.url.rstrip('/')
                    base_clean = effective_base_url.rstrip('/')
                    if final_url == base_clean or final_url == base_clean + '/':
                        logger.debug(f"  Redirected to homepage, trying next path")
                        continue

                response = resp
                roster_url = url
                break
            # Domain unreachable or timing out — don't waste time on more paths
            if self.request_handler.last_error_type in ('connection', 'ssl', 'timeout'):
                logger.info(f"  Domain down/timeout, skipping remaining roster paths")
                break

        # URL discovery fallback: if all paths returned 404/405 (site is up,
        # just wrong paths), crawl the homepage to find the right URLs
        if not response and self.request_handler.last_error_type == 'http':
            discovered = self.url_discoverer.discover_baseball_urls(base_url, self.request_handler)
            if discovered and discovered.get('roster_url'):
                resp = self.request_handler.get(discovered['roster_url'])
                if resp:
                    response = resp
                    roster_url = discovered['roster_url']
                    # Also update stats paths if discovered
                    if discovered.get('stats_url'):
                        STATS_PATHS.insert(0, discovered['stats_url'])
                        STATS_PATHS = list(dict.fromkeys(STATS_PATHS))

        if not response:
            result['errors'].append(f"Failed to fetch roster from {base_url}")
            return result

        roster = self.parser.parse_roster(response.text, school_name)
        logger.info(f"  Found {len(roster)} players on roster")

        if not roster:
            result['errors'].append("No players parsed from roster page")
            result['found_0_players'] = True  # Flag for browser retry
            return result  # No point fetching stats if roster is empty

        # Wait before stats request
        time.sleep(random.uniform(*self.config['between_pages_same_school']))

        # Try stats URL patterns (use effective_base_url in case roster redirected us)
        stats_response = None
        for path in STATS_PATHS:
            url = f"{effective_base_url}{path}" if not path.startswith('http') else path
            logger.debug(f"Trying stats: {url}")
            resp = self.request_handler.get(
                url,
                delay_type='between_pages_same_school',
                referer=roster_url
            )
            if resp:
                # Skip if redirected to homepage (common on SIDEARM v3 for bad paths)
                final_url = resp.url.rstrip('/')
                base_clean = effective_base_url.rstrip('/')
                orig_clean = base_url.rstrip('/')
                if (final_url == base_clean or final_url == base_clean + '/' or
                        final_url == orig_clean or final_url == orig_clean + '/'):
                    logger.debug(f"  Redirected to homepage, skipping: {url}")
                    continue
                stats_response = resp
                break
            # Domain unreachable or timing out — skip remaining stats paths
            if self.request_handler.last_error_type in ('connection', 'ssl', 'timeout'):
                logger.info(f"  Domain down/timeout, skipping remaining stats paths")
                break

        batting_stats = {}
        pitching_stats = {}
        response = stats_response

        if response:
            # Try Nuxt payload first (SIDEARM v3 - has both batting + pitching)
            batting_stats, pitching_stats = self.parser.parse_nuxt_stats(response.text)

            # Fall back to HTML table parsing
            if not batting_stats:
                batting_stats = self.parser.parse_batting_stats(response.text)
            if not pitching_stats:
                pitching_stats = self.parser.parse_pitching_stats(response.text)

            # Generic stats fallback for non-SIDEARM sites
            if not batting_stats:
                batting_stats = self.parser.parse_generic_batting_stats(response.text)
            if not pitching_stats:
                pitching_stats = self.parser.parse_generic_pitching_stats(response.text)

            logger.info(f"  Batting stats: {len(batting_stats)} players")
            logger.info(f"  Pitching stats: {len(pitching_stats)} players")
        else:
            result['errors'].append(f"Failed to fetch stats from {base_url} (tried {len(STATS_PATHS)} paths)")

        # SIDEARM API fallback: for Nuxt SPA sites where stats are loaded
        # client-side only (e.g., Iowa, BYU, Nebraska, Colorado)
        if not batting_stats and not pitching_stats:
            api_batting, api_pitching = self._try_sidearm_api_stats(effective_base_url, roster_url)
            if api_batting:
                batting_stats = api_batting
            if api_pitching:
                pitching_stats = api_pitching
            if api_batting or api_pitching:
                logger.info(f"  SIDEARM API: {len(batting_stats)} batting, {len(pitching_stats)} pitching")

        # Merge data
        for player in roster:
            player_name = player.get('name', '')
            player['batting_stats'] = batting_stats.get(player_name)
            player['pitching_stats'] = pitching_stats.get(player_name)
            result['players'].append(player)

        # Add any players in stats but not roster
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

        if result['success']:
            logger.info(f"  Success: {len(result['players'])} total players")
        else:
            logger.warning(f"  Failed: No players found")

        return result

    def _try_sidearm_api_stats(self, base_url: str, referer: str = None):
        """Try SIDEARM API endpoints as a fallback for Nuxt SPA sites
        where stats are only loaded client-side."""
        SIDEARM_API_PATHS = [
            '/services/responsive-calendar.ashx?type=stats&sport=baseball&year=2026',
            '/services/responsive-calendar.ashx?type=stats&sport=baseball',
            '/api/stats/baseball',
        ]

        for path in SIDEARM_API_PATHS:
            url = f"{base_url}{path}"
            logger.debug(f"Trying SIDEARM API: {url}")
            resp = self.request_handler.get(
                url,
                delay_type='between_pages_same_school',
                referer=referer
            )
            if not resp:
                continue

            # Check if we got JSON back
            content_type = resp.headers.get('content-type', '')
            if 'json' in content_type or 'javascript' in content_type:
                try:
                    data = resp.json()
                    batting, pitching = self.parser.parse_sidearm_api_stats(data)
                    if batting or pitching:
                        return batting, pitching
                except Exception as e:
                    logger.debug(f"  SIDEARM API parse error: {e}")
                    continue

            # Some API endpoints return HTML with embedded Nuxt data
            if resp.text:
                batting, pitching = self.parser.parse_nuxt_stats(resp.text)
                if batting or pitching:
                    return batting, pitching

        return {}, {}

    def run(self, force: bool = False, dry_run: bool = False):
        """Main run method - handles both initial and daily scraping"""
        if not self.should_scrape(force):
            return

        # Get schools to scrape today
        schools = self.scheduler.get_schools_to_scrape_today()

        if not schools:
            logger.info("No schools need scraping today")
            return

        # During initial scrape: skip schools already in the DB (survives
        # workflow cancellations/timeouts unlike the JSON artifact).
        # During daily updates: the scheduler handles rotation, no need to filter.
        if not self.scheduler.is_initial_scrape_complete():
            already_done = self.db.get_schools_in_db()
            if already_done:
                before = len(schools)
                schools = [s for s in schools if s['school_name'] not in already_done]
                skipped = before - len(schools)
                if skipped:
                    logger.info(f"Skipping {skipped} schools already in DB (initial scrape checkpoint)")

        if not schools:
            logger.info("All schools already scraped")
            return

        # Print status
        print(self.scheduler.get_status_report())

        logger.info(f"Schools to scrape today: {len(schools)}")

        if dry_run:
            logger.info("DRY RUN - would scrape these schools:")
            for s in schools[:20]:
                logger.info(f"  {s['school_name']} ({s.get('division', '?')})")
            if len(schools) > 20:
                logger.info(f"  ... and {len(schools) - 20} more")
            return

        max_schools = self.config.get('max_schools_per_day', 100)
        log_id = self.db.log_scrape_start()
        errors = []
        browser_retry_schools = []
        run_start = datetime.now()

        try:
            for i, school in enumerate(schools):
                if self.schools_scraped_today >= max_schools:
                    logger.info(f"Daily limit reached ({max_schools} schools)")
                    break

                try:
                    result = self.scrape_school(school)

                    if result['success']:
                        players_saved = self.db.save_school_data(result)
                        self.scheduler.mark_scraped(school['school_name'])
                        self.schools_scraped_today += 1
                        self.total_players_scraped += players_saved
                    elif result.get('found_0_players'):
                        # Site was reachable but parser couldn't read — candidate for browser retry
                        browser_retry_schools.append(school)

                    if result['errors']:
                        errors.extend(result['errors'])

                    # Progress update
                    if (i + 1) % 5 == 0:
                        elapsed = (datetime.now() - run_start).total_seconds() / 60
                        logger.info(f"Progress: {i + 1}/{len(schools)} schools processed "
                                    f"({self.schools_scraped_today} saved, "
                                    f"{self.total_players_scraped} players) "
                                    f"[{elapsed:.0f}m elapsed, "
                                    f"{self.request_handler.hourly_request_count} reqs]")

                    # Wait between schools
                    if i < len(schools) - 1:
                        delay = random.uniform(*self.config['between_schools'])
                        time.sleep(delay)

                except KeyboardInterrupt:
                    logger.warning("Interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Error scraping {school['school_name']}: {e}")
                    errors.append(f"{school['school_name']}: {str(e)}")
                    continue

            # Browser retry pass for schools that returned 0 players
            if browser_retry_schools and self.browser_scraper.available:
                logger.info(f"Browser retry pass: {len(browser_retry_schools)} schools")
                browser_results = self.browser_scraper.scrape_schools(browser_retry_schools)
                for result in browser_results:
                    if result['success']:
                        players_saved = self.db.save_school_data(result)
                        self.scheduler.mark_scraped(result['school'])
                        self.schools_scraped_today += 1
                        self.total_players_scraped += players_saved
                        logger.info(f"  Browser recovered: {result['school']} ({players_saved} players)")
            elif browser_retry_schools:
                logger.info(f"Skipping browser retry ({len(browser_retry_schools)} candidates) — "
                           "Playwright not installed")

        finally:
            self.db.log_scrape_end(
                log_id,
                self.schools_scraped_today,
                self.total_players_scraped,
                errors[:50],  # Cap errors stored
                success=self.schools_scraped_today > 0
            )
            self.db.close()

        logger.info(f"Scrape session complete. "
                    f"Schools: {self.schools_scraped_today}, "
                    f"Players: {self.total_players_scraped}")

    def run_diagnostic(self):
        """Test on representative schools from each parser strategy"""
        test_schools = [
            {
                'school_name': 'Louisville',
                'division': 'D1',
                'conference': 'ACC',
                'athletics_base_url': 'https://gocards.com',
                'roster_url': '/sports/baseball/roster',
                'stats_url': '/sports/baseball/stats'
            },
            {
                'school_name': 'Arizona St.',
                'division': 'D1',
                'conference': 'Big 12',
                'athletics_base_url': 'https://thesundevils.com',
                'roster_url': '/sports/baseball/roster',
                'stats_url': '/sports/baseball/stats'
            },
            {
                'school_name': 'Cincinnati',
                'division': 'D1',
                'conference': 'Big 12',
                'athletics_base_url': 'https://gobearcats.com',
                'roster_url': '/sports/baseball/roster',
                'stats_url': '/sports/baseball/stats'
            },
            {
                'school_name': 'Arkansas',
                'division': 'D1',
                'conference': 'SEC',
                'athletics_base_url': 'https://arkansasrazorbacks.com',
                'roster_url': '/sport/m-basebl/roster/',
                'stats_url': 'https://arkansasrazorbacks.com/stats/baseball/2026/teamcume.htm'
            },
            {
                'school_name': 'Jackson St.',
                'division': 'D1',
                'conference': 'SWAC',
                'athletics_base_url': 'https://gojsutigers.com',
                'roster_url': '/sports/baseball/roster',
                'stats_url': '/sports/baseball/stats'
            },
            {
                'school_name': 'Clemson',
                'division': 'D1',
                'conference': 'ACC',
                'athletics_base_url': 'https://clemsontigers.com',
                'roster_url': '/sports/baseball/roster',
                'stats_url': 'https://data.clemsontigers.com/Stats/Baseball/2026/teamcume.htm'
            },
            {
                'school_name': 'Chapman',
                'division': 'D3',
                'conference': 'SCIAC',
                'athletics_base_url': 'https://chapmanathletics.com',
                'roster_url': '/sports/baseball/roster',
                'stats_url': '/sports/baseball/stats'
            },
        ]

        print("\n" + "=" * 60)
        print(f"DIAGNOSTIC MODE - Testing {len(test_schools)} Schools")
        print("=" * 60)

        for school in test_schools:
            result = self.scrape_school(school)

            print(f"\n--- {school['school_name']} ({school['division']}) ---")
            print(f"Success: {result['success']}")
            print(f"Players: {len(result['players'])}")

            if result['errors']:
                print(f"Errors: {result['errors']}")

            if result['players'][:3]:
                print("Sample players:")
                for p in result['players'][:3]:
                    print(f"  - {p.get('name')} - {p.get('position', 'N/A')} "
                          f"({p.get('class_year', 'N/A')})")
                    if p.get('batting_stats'):
                        bs = p['batting_stats']
                        print(f"    Batting: {bs.get('batting_average', 'N/A')} AVG, "
                              f"{bs.get('home_runs', 0)} HR, "
                              f"XBH:K={bs.get('xbh_to_k', 'N/A')}")
                    if p.get('pitching_stats'):
                        ps = p['pitching_stats']
                        print(f"    Pitching: {ps.get('era', 'N/A')} ERA, "
                              f"K/9={ps.get('k_per_9', 'N/A')}, "
                              f"BB/9={ps.get('bb_per_9', 'N/A')}")

            # Wait between test schools
            time.sleep(15)

        print("\n" + "=" * 60)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 60)


    def run_recover(self, dry_run: bool = False):
        """Re-attempt scraping on schools that previously failed.

        Targets schools that are in the scheduler's history as "scraped" but
        have no players in the DB, or schools that were never scraped due to
        errors (not in DB at all despite being in scrape_history).
        """
        logger.info("Recovery mode: finding failed schools to retry")

        all_schools = self.scheduler.schools
        already_in_db = self.db.get_schools_in_db()

        # Find schools not in DB (either never scraped or scraped with 0 players)
        failed_schools = [s for s in all_schools if s['school_name'] not in already_in_db]

        if not failed_schools:
            logger.info("No failed schools to recover — all schools are in DB")
            return

        logger.info(f"Found {len(failed_schools)} schools not in DB")

        if dry_run:
            logger.info("DRY RUN - would attempt recovery on:")
            for s in failed_schools[:30]:
                logger.info(f"  {s['school_name']} ({s.get('division', '?')}) - {s.get('athletics_base_url', 'no URL')}")
            if len(failed_schools) > 30:
                logger.info(f"  ... and {len(failed_schools) - 30} more")
            return

        log_id = self.db.log_scrape_start()
        errors = []
        browser_retry_schools = []
        run_start = datetime.now()

        try:
            for i, school in enumerate(failed_schools):
                try:
                    result = self.scrape_school(school)

                    if result['success']:
                        players_saved = self.db.save_school_data(result)
                        self.scheduler.mark_scraped(school['school_name'])
                        self.schools_scraped_today += 1
                        self.total_players_scraped += players_saved
                        logger.info(f"  Recovered: {school['school_name']} ({players_saved} players)")
                    elif result.get('found_0_players'):
                        browser_retry_schools.append(school)

                    if result['errors']:
                        errors.extend(result['errors'])

                    if (i + 1) % 5 == 0:
                        elapsed = (datetime.now() - run_start).total_seconds() / 60
                        logger.info(f"Recovery progress: {i + 1}/{len(failed_schools)} "
                                    f"({self.schools_scraped_today} recovered) [{elapsed:.0f}m]")

                    if i < len(failed_schools) - 1:
                        delay = random.uniform(*self.config['between_schools'])
                        time.sleep(delay)

                except KeyboardInterrupt:
                    logger.warning("Interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Recovery error for {school['school_name']}: {e}")
                    errors.append(f"{school['school_name']}: {str(e)}")
                    continue

            # Browser retry pass
            if browser_retry_schools and self.browser_scraper.available:
                logger.info(f"Browser retry pass: {len(browser_retry_schools)} schools")
                browser_results = self.browser_scraper.scrape_schools(browser_retry_schools)
                for result in browser_results:
                    if result['success']:
                        players_saved = self.db.save_school_data(result)
                        self.scheduler.mark_scraped(result['school'])
                        self.schools_scraped_today += 1
                        self.total_players_scraped += players_saved

        finally:
            self.db.log_scrape_end(
                log_id,
                self.schools_scraped_today,
                self.total_players_scraped,
                errors[:50],
                success=self.schools_scraped_today > 0
            )
            self.db.close()

        logger.info(f"Recovery complete. Recovered: {self.schools_scraped_today} schools, "
                    f"{self.total_players_scraped} players")

    def run_cleanup(self):
        """Delete players with invalid names (stat values as names)"""
        import psycopg2
        conn = psycopg2.connect(self.db.database_url)
        with conn.cursor() as cur:
            # Find bad players: first_name looks like a stat (.500, 1.000, etc.)
            cur.execute("""
                SELECT COUNT(*) FROM players
                WHERE first_name ~ '^[\\d.\\-/]+$' OR (first_name = '' AND last_name = '')
            """)
            count = cur.fetchone()[0]
            if count == 0:
                print("No bad records found.")
                conn.close()
                return

            print(f"Found {count} players with invalid names (stat values). Deleting...")

            # Delete associated stats first (cascade should handle this, but be explicit)
            cur.execute("""
                DELETE FROM hitting_stats WHERE player_id IN (
                    SELECT id FROM players
                    WHERE first_name ~ '^[\\d.\\-/]+$' OR (first_name = '' AND last_name = '')
                )
            """)
            print(f"  Deleted {cur.rowcount} hitting_stats records")

            cur.execute("""
                DELETE FROM pitching_stats WHERE player_id IN (
                    SELECT id FROM players
                    WHERE first_name ~ '^[\\d.\\-/]+$' OR (first_name = '' AND last_name = '')
                )
            """)
            print(f"  Deleted {cur.rowcount} pitching_stats records")

            cur.execute("""
                DELETE FROM players
                WHERE first_name ~ '^[\\d.\\-/]+$' OR (first_name = '' AND last_name = '')
            """)
            print(f"  Deleted {cur.rowcount} player records")

            conn.commit()
        conn.close()
        print("Cleanup complete.")


def main():
    parser = argparse.ArgumentParser(description='College Baseball Stats Scraper')
    parser.add_argument('command', choices=['run', 'diagnostic', 'status', 'cleanup', 'recover'],
                        help='run=daily scrape, diagnostic=test schools, status=show progress, '
                             'cleanup=fix bad data, recover=retry failed schools')
    parser.add_argument('--force', '-f', action='store_true',
                        help='Force scrape even if season has not started')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be scraped without actually scraping')

    args = parser.parse_args()

    scraper = CollegeBaseballScraper()

    if args.command == 'run':
        scraper.run(force=args.force, dry_run=args.dry_run)
    elif args.command == 'diagnostic':
        scraper.run_diagnostic()
    elif args.command == 'status':
        print(scraper.scheduler.get_status_report())
    elif args.command == 'cleanup':
        scraper.run_cleanup()
    elif args.command == 'recover':
        scraper.run_recover(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
