# scraper/database.py

import os
import re
import hashlib
import logging
from typing import Dict, Optional
from datetime import datetime

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles all database operations for the scraper, matching the Prisma schema."""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.environ.get('DATABASE_URL', '')
        self.conn = None

    def _get_conn(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.database_url)
        return self.conn

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()

    def _generate_ncaa_id(self, name: str, division: str) -> int:
        """Generate a stable numeric ID from school name + division"""
        key = f"{name.lower().strip()}:{division}"
        h = hashlib.md5(key.encode()).hexdigest()
        return int(h[:8], 16) % 900000 + 100000  # 6-digit ID

    def _parse_height(self, height_str: str) -> Optional[int]:
        """Parse height string to inches. Supports '6-2', '6'2\"', '74'."""
        if not height_str:
            return None
        height_str = height_str.strip()

        # "6-2" or "6-02"
        m = re.match(r'^(\d)\s*[-]\s*(\d{1,2})$', height_str)
        if m:
            return int(m.group(1)) * 12 + int(m.group(2))

        # "6'2" or "6'2\""
        m = re.match(r'^(\d)\s*[\'"]\s*(\d{1,2})', height_str)
        if m:
            return int(m.group(1)) * 12 + int(m.group(2))

        # Raw inches
        m = re.match(r'^(\d{2})$', height_str)
        if m:
            val = int(m.group(1))
            if 60 <= val <= 84:
                return val

        return None

    def _parse_weight(self, weight_str: str) -> Optional[int]:
        """Parse weight string to lbs."""
        if not weight_str:
            return None
        weight_str = weight_str.strip().replace('lbs', '').replace('lb', '').strip()
        try:
            val = int(weight_str)
            if 100 <= val <= 350:
                return val
        except ValueError:
            pass
        return None

    def _split_name(self, full_name: str) -> tuple:
        """Split 'Last, First' or 'First Last' into (first, last)"""
        if not full_name:
            return ('', '')
        name = full_name.strip()
        if ',' in name:
            parts = name.split(',', 1)
            return (parts[1].strip(), parts[0].strip())
        parts = name.split(None, 1)
        if len(parts) == 2:
            return (parts[0].strip(), parts[1].strip())
        return (name, '')

    def _normalize_class_year(self, year_str: str) -> Optional[str]:
        """Normalize class year to Fr./So./Jr./Sr./Gr."""
        if not year_str:
            return None
        y = year_str.strip().lower().rstrip('.')
        mapping = {
            'fr': 'Fr.', 'freshman': 'Fr.',
            'so': 'So.', 'sophomore': 'So.',
            'jr': 'Jr.', 'junior': 'Jr.',
            'sr': 'Sr.', 'senior': 'Sr.',
            'gr': 'Gr.', 'graduate': 'Gr.', 'grad': 'Gr.',
            'r-fr': 'Fr.', 'r-so': 'So.', 'r-jr': 'Jr.', 'r-sr': 'Sr.',
        }
        return mapping.get(y, year_str.strip())

    def _normalize_position(self, pos_str: str) -> Optional[str]:
        """Normalize position string"""
        if not pos_str:
            return None
        pos = pos_str.strip().upper()
        mapping = {
            'PITCHER': 'P', 'RHP': 'P', 'LHP': 'P',
            'CATCHER': 'C',
            'FIRST BASE': '1B', 'FIRST BASEMAN': '1B',
            'SECOND BASE': '2B', 'SECOND BASEMAN': '2B',
            'THIRD BASE': '3B', 'THIRD BASEMAN': '3B',
            'SHORTSTOP': 'SS',
            'LEFT FIELD': 'LF', 'LEFT FIELDER': 'LF',
            'CENTER FIELD': 'CF', 'CENTER FIELDER': 'CF',
            'RIGHT FIELD': 'RF', 'RIGHT FIELDER': 'RF',
            'DESIGNATED HITTER': 'DH',
            'OUTFIELD': 'OF', 'OUTFIELDER': 'OF',
            'INFIELD': 'INF', 'INFIELDER': 'INF',
            'UTILITY': 'UT',
        }
        return mapping.get(pos, pos)

    def upsert_team(self, school_name: str, division: str, conference: str = '') -> int:
        """Upsert a team and return its ID"""
        conn = self._get_conn()
        ncaa_id = self._generate_ncaa_id(school_name, division)

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO teams (ncaa_id, name, division, conference, updated_at)
                VALUES (%s, %s, %s::\"Division\", %s, NOW())
                ON CONFLICT (ncaa_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    conference = EXCLUDED.conference,
                    updated_at = NOW()
                RETURNING id
            """, (ncaa_id, school_name, division, conference or ''))
            team_id = cur.fetchone()[0]
            conn.commit()

        return team_id

    def upsert_player(self, team_id: int, player_data: dict) -> int:
        """Upsert a player and return their ID"""
        conn = self._get_conn()

        first_name, last_name = self._split_name(player_data.get('name', ''))

        # Reject names that look like stat values (e.g. ".500", "1.000")
        if not first_name or re.match(r'^[\d.\-/]+$', first_name):
            return -1
        position = self._normalize_position(player_data.get('position'))
        class_year = self._normalize_class_year(player_data.get('class_year'))
        height = self._parse_height(player_data.get('height'))
        weight = self._parse_weight(player_data.get('weight'))

        bats = None
        throws = None
        bt = player_data.get('bats_throws', '')
        if bt and '/' in bt:
            parts = bt.split('/')
            bats = parts[0].strip().upper() if parts[0].strip() else None
            throws = parts[1].strip().upper() if len(parts) > 1 and parts[1].strip() else None

        hometown = player_data.get('hometown')
        high_school = player_data.get('high_school')

        with conn.cursor() as cur:
            # Try to find existing player by name + team
            cur.execute("""
                SELECT id FROM players
                WHERE first_name = %s AND last_name = %s AND team_id = %s
            """, (first_name, last_name, team_id))
            row = cur.fetchone()

            if row:
                player_id = row[0]
                # Update existing player
                updates = []
                params = []
                if position:
                    updates.append("position = %s")
                    params.append(position)
                if class_year:
                    updates.append("class_year = %s")
                    params.append(class_year)
                if height:
                    updates.append("height_inches = %s")
                    params.append(height)
                if weight:
                    updates.append("weight_lbs = %s")
                    params.append(weight)
                if bats:
                    updates.append("bats = %s")
                    params.append(bats)
                if throws:
                    updates.append("throws = %s")
                    params.append(throws)
                if hometown:
                    updates.append("hometown = %s")
                    params.append(hometown)
                if high_school:
                    updates.append("high_school = %s")
                    params.append(high_school)

                if updates:
                    updates.append("updated_at = NOW()")
                    params.append(player_id)
                    cur.execute(
                        f"UPDATE players SET {', '.join(updates)} WHERE id = %s",
                        params
                    )
            else:
                # Insert new player
                cur.execute("""
                    INSERT INTO players (first_name, last_name, position, class_year,
                        height_inches, weight_lbs, bats, throws, hometown, high_school,
                        team_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (first_name, last_name, position, class_year,
                      height, weight, bats, throws, hometown, high_school, team_id))
                player_id = cur.fetchone()[0]

            conn.commit()

        return player_id

    def upsert_hitting_stats(self, player_id: int, stats: dict):
        """Upsert hitting stats for a player"""
        if not stats:
            return

        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hitting_stats (player_id, season,
                    g, ab, r, h, "2b", "3b", hr, rbi, bb, k,
                    sb, cs, hbp, sf, sh, gidp,
                    avg, obp, slg, ops, xbh, xbh_to_k, tb,
                    created_at, updated_at)
                VALUES (%s, 2026,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    NOW(), NOW())
                ON CONFLICT (player_id) DO UPDATE SET
                    g = EXCLUDED.g, ab = EXCLUDED.ab, r = EXCLUDED.r,
                    h = EXCLUDED.h, "2b" = EXCLUDED."2b", "3b" = EXCLUDED."3b",
                    hr = EXCLUDED.hr, rbi = EXCLUDED.rbi, bb = EXCLUDED.bb,
                    k = EXCLUDED.k, sb = EXCLUDED.sb, cs = EXCLUDED.cs,
                    hbp = EXCLUDED.hbp, sf = EXCLUDED.sf, sh = EXCLUDED.sh,
                    gidp = EXCLUDED.gidp,
                    avg = EXCLUDED.avg, obp = EXCLUDED.obp,
                    slg = EXCLUDED.slg, ops = EXCLUDED.ops,
                    xbh = EXCLUDED.xbh, xbh_to_k = EXCLUDED.xbh_to_k,
                    tb = EXCLUDED.tb,
                    updated_at = NOW()
            """, (
                player_id,
                stats.get('games', 0),
                stats.get('at_bats', 0),
                stats.get('runs', 0),
                stats.get('hits', 0),
                stats.get('doubles', 0),
                stats.get('triples', 0),
                stats.get('home_runs', 0),
                stats.get('rbi', 0),
                stats.get('walks', 0),
                stats.get('strikeouts', 0),
                stats.get('stolen_bases', 0),
                stats.get('caught_stealing', 0),
                stats.get('hit_by_pitch', 0),
                stats.get('sacrifice_flies', 0),
                stats.get('sacrifice_hits', 0),
                stats.get('gidp', 0),
                stats.get('batting_average'),
                stats.get('on_base_percentage'),
                stats.get('slugging_percentage'),
                stats.get('ops'),
                stats.get('extra_base_hits'),
                stats.get('xbh_to_k'),
                stats.get('total_bases'),
            ))
            conn.commit()

    def upsert_pitching_stats(self, player_id: int, stats: dict):
        """Upsert pitching stats for a player"""
        if not stats:
            return

        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pitching_stats (player_id, season,
                    app, gs, w, l, sv, cg, sho,
                    ip, h, r, er, bb, k, hr_allowed, hb, wp, bk,
                    era, whip, k_per_9, bb_per_9, k_to_bb,
                    created_at, updated_at)
                VALUES (%s, 2026,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    NOW(), NOW())
                ON CONFLICT (player_id) DO UPDATE SET
                    app = EXCLUDED.app, gs = EXCLUDED.gs,
                    w = EXCLUDED.w, l = EXCLUDED.l, sv = EXCLUDED.sv,
                    cg = EXCLUDED.cg, sho = EXCLUDED.sho,
                    ip = EXCLUDED.ip, h = EXCLUDED.h, r = EXCLUDED.r,
                    er = EXCLUDED.er, bb = EXCLUDED.bb, k = EXCLUDED.k,
                    hr_allowed = EXCLUDED.hr_allowed, hb = EXCLUDED.hb,
                    wp = EXCLUDED.wp, bk = EXCLUDED.bk,
                    era = EXCLUDED.era, whip = EXCLUDED.whip,
                    k_per_9 = EXCLUDED.k_per_9, bb_per_9 = EXCLUDED.bb_per_9,
                    k_to_bb = EXCLUDED.k_to_bb,
                    updated_at = NOW()
            """, (
                player_id,
                stats.get('appearances', 0),
                stats.get('games_started', 0),
                stats.get('wins', 0),
                stats.get('losses', 0),
                stats.get('saves', 0),
                stats.get('complete_games', 0),
                stats.get('shutouts', 0),
                stats.get('innings_pitched', 0),
                stats.get('hits_allowed', 0),
                stats.get('runs_allowed', 0),
                stats.get('earned_runs', 0),
                stats.get('walks', 0),
                stats.get('strikeouts', 0),
                stats.get('home_runs_allowed', 0),
                stats.get('hit_batters', 0),
                stats.get('wild_pitches', 0),
                stats.get('balks', 0),
                stats.get('era'),
                stats.get('whip'),
                stats.get('k_per_9'),
                stats.get('bb_per_9'),
                stats.get('k_to_bb'),
            ))
            conn.commit()

    def log_scrape_start(self, division: str = None) -> int:
        """Log the start of a scrape session"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            if division:
                cur.execute("""
                    INSERT INTO scrape_logs (status, division, started_at)
                    VALUES ('RUNNING'::\"ScrapeStatus\", %s::\"Division\", NOW())
                    RETURNING id
                """, (division,))
            else:
                cur.execute("""
                    INSERT INTO scrape_logs (status, started_at)
                    VALUES ('RUNNING'::\"ScrapeStatus\", NOW())
                    RETURNING id
                """)
            log_id = cur.fetchone()[0]
            conn.commit()
        return log_id

    def log_scrape_end(self, log_id: int, teams_scraped: int,
                       players_scraped: int, errors: list, success: bool = True):
        """Log the end of a scrape session"""
        conn = self._get_conn()
        status = 'COMPLETED' if success else 'FAILED'
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE scrape_logs SET
                    status = %s::\"ScrapeStatus\",
                    completed_at = NOW(),
                    teams_scraped = %s,
                    players_scraped = %s,
                    errors = %s
                WHERE id = %s
            """, (status, teams_scraped, players_scraped, errors, log_id))
            conn.commit()

    def get_schools_scraped_today(self) -> set:
        """Return set of school names already scraped today (based on teams.updated_at)"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM teams WHERE updated_at >= CURRENT_DATE")
            return {row[0] for row in cur.fetchall()}

    def save_school_data(self, result: dict):
        """Save a full school scrape result to the database"""
        school_name = result['school']
        division = result['division']
        conference = result.get('conference', '')

        # Upsert team
        team_id = self.upsert_team(school_name, division, conference)

        players_saved = 0
        for player_data in result.get('players', []):
            try:
                player_id = self.upsert_player(team_id, player_data)
                if player_id < 0:
                    continue

                if player_data.get('batting_stats'):
                    self.upsert_hitting_stats(player_id, player_data['batting_stats'])

                if player_data.get('pitching_stats'):
                    self.upsert_pitching_stats(player_id, player_data['pitching_stats'])

                players_saved += 1
            except Exception as e:
                logger.error(f"Error saving player {player_data.get('name', '?')}: {e}")

        logger.info(f"Saved {players_saved} players for {school_name}")
        return players_saved
