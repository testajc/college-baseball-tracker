# scraper/parsers/sidearm_parser.py

from bs4 import BeautifulSoup
from typing import Optional, Dict, List, Tuple
import re
import json
import logging

logger = logging.getLogger(__name__)


class SidearmParser:
    """
    Parser for SIDEARM Sports athletics websites.
    Used by the majority of college athletics departments.
    """

    def parse_roster(self, html: str, school_name: str) -> List[Dict]:
        """Parse roster page to get all players"""
        soup = BeautifulSoup(html, 'html.parser')
        players = []

        # Strategy 0: Nuxt devalue payload (SIDEARM v3 nextgen sites)
        # These sites render rosters entirely client-side; HTML has no tables/cards.
        players = self.parse_nuxt_roster(html, school_name)
        if players:
            logger.debug(f"Found {len(players)} players via Nuxt payload")
            return players

        # Strategy 1: Table with roster-specific class
        roster_table = soup.find('table', class_=re.compile(r'roster|sidearm-table', re.I))
        if roster_table:
            players = self._parse_table_roster(roster_table)
            if players:
                logger.debug(f"Found {len(players)} players via roster-class table")

        # Strategy 2: Any table with player-like headers (Name, No., etc.)
        if not players:
            tables = soup.find_all('table')
            for table in tables:
                headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                if any(h in headers for h in ['name', 'player', 'no.', '#']):
                    rows = table.find_all('tr')
                    # Must have enough rows to be a real roster (header + at least 5 players)
                    if len(rows) >= 6:
                        players = self._parse_table_roster(table)
                        if players:
                            logger.debug(f"Found {len(players)} players via generic table")
                            break

        # Strategy 3: Card-based roster (SIDEARM player cards only)
        if not players:
            # Use exact class match to avoid grabbing share/header divs
            player_cards = soup.find_all(
                ['li', 'div'],
                class_=lambda c: c and isinstance(c, list) and any(
                    cls in ['sidearm-roster-player', 'roster-player', 's-person-card']
                    for cls in c
                )
            )
            if not player_cards:
                # Fallback: look for elements with sidearm-roster-player in class string
                player_cards = soup.find_all(
                    ['li', 'div'],
                    class_=re.compile(r'^sidearm-roster-player$|^roster-player$', re.I)
                )
            if player_cards:
                players = self._parse_card_roster(player_cards)
                if players:
                    logger.debug(f"Found {len(players)} players via card parser")

        # Strategy 4: JSON-LD Schema.org Person data (some SIDEARM D2/D3 sites)
        if not players:
            players = self._parse_jsonld_roster(soup)
            if players:
                logger.debug(f"Found {len(players)} players via JSON-LD")

        # Strategy 5: Generic roster detection for non-SIDEARM sites
        if not players:
            players = self._parse_generic_roster(soup)
            if players:
                logger.debug(f"Found {len(players)} players via generic roster parser")

        # Sanity check: a baseball roster should have 15-55 players
        if len(players) > 60:
            logger.warning(f"Roster has {len(players)} players (unusually large), may include non-players")

        # Add school name to each player
        for p in players:
            p['school'] = school_name

        return players

    def _clean_cell_text(self, cell) -> str:
        """Extract clean text from a SIDEARM table cell.

        Handles:
        - Mobile labels like <span class="label d-md-none">Pos.:</span>
        - Duplicate text in name cells (first/last printed twice)
        """
        # Remove mobile-only label spans before extracting text
        cell_copy = cell.__copy__() if hasattr(cell, '__copy__') else cell
        for span in cell.find_all('span', class_=re.compile(r'd-md-none|d-print-none|label', re.I)):
            span.decompose()

        text = cell.get_text(' ', strip=True)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_name(self, cell) -> str:
        """Extract a clean player name from a name cell.

        Handles SIDEARM patterns:
        - data-sort="Last, First" attribute (most reliable)
        - Link text with whitespace: "First\\r\\n\\t\\tLast"
        - Duplicate name text from mobile/desktop views
        - Jersey number appended to name: "First Last 0"
        """
        # Best source: data-sort attribute (e.g. "Ellis, Briggs")
        data_sort = cell.get('data-sort', '')
        if data_sort and ',' in data_sort:
            parts = data_sort.split(',', 1)
            name = f"{parts[1].strip()} {parts[0].strip()}"
            if name.strip():
                return name

        # Try getting name from the first non-empty link
        links = cell.find_all('a')
        for link in links:
            raw = link.get_text()
            # Collapse all whitespace (handles \r\n\t between first/last)
            cleaned = re.sub(r'\s+', ' ', raw).strip()
            if cleaned:
                # Remove trailing jersey number (e.g. "Briggs Ellis 0")
                cleaned = re.sub(r'\s+\d{1,2}$', '', cleaned)
                if cleaned:
                    # Normalize "Last, First" to "First Last"
                    if ',' in cleaned:
                        parts = cleaned.split(',', 1)
                        cleaned = f"{parts[1].strip()} {parts[0].strip()}"
                    return cleaned

        # Fallback: direct cell text
        text = self._clean_cell_text(cell)
        # Remove trailing jersey number
        text = re.sub(r'\s+\d{1,2}$', '', text)
        # Normalize "Last, First" to "First Last"
        if ',' in text:
            parts = text.split(',', 1)
            text = f"{parts[1].strip()} {parts[0].strip()}"
        return text

    def _parse_table_roster(self, table) -> List[Dict]:
        """Parse traditional HTML table roster"""
        players = []

        # Find headers - use only direct th/td in thead to avoid data leaking in
        headers = []
        header_row = table.find('thead')
        if header_row:
            header_cells = header_row.find('tr')
            if header_cells:
                headers = [th.get_text(strip=True).lower() for th in header_cells.find_all(['th', 'td'])]

        if not headers:
            first_row = table.find('tr')
            if first_row:
                headers = [cell.get_text(strip=True).lower() for cell in first_row.find_all(['th', 'td'])]

        # Normalize headers
        header_map = {}
        for i, h in enumerate(headers):
            h_clean = h.replace('.', '').replace('#', 'no').strip()
            if h_clean in ['name', 'player'] or ('name' in h_clean and 'team' not in h_clean):
                header_map['name'] = i
            elif h_clean in ['no', 'number', 'num']:
                header_map['jersey_number'] = i
            elif 'pos' in h_clean and 'previous' not in h_clean:
                header_map['position'] = i
            elif h_clean in ['yr', 'cl', 'class', 'elig', 'eligibility'] or 'year' in h_clean:
                header_map['class_year'] = i
            elif h_clean in ['bt', 'b/t', 'b-t']:
                header_map['bats_throws'] = i
            elif h_clean in ['ht', 'height']:
                header_map['height'] = i
            elif h_clean in ['wt', 'weight']:
                header_map['weight'] = i
            elif 'hometown' in h_clean:
                header_map['hometown'] = i
            elif 'high school' in h_clean or h_clean == 'hs' or 'previous' in h_clean:
                header_map['high_school'] = i

        # Parse data rows (skip header row)
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
        else:
            rows = table.find_all('tr')
            rows = rows[1:] if headers else rows

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue

            player = {}
            for field, idx in header_map.items():
                if idx < len(cells):
                    cell = cells[idx]

                    if field == 'name':
                        value = self._extract_name(cell)
                        # Get profile link
                        link = cell.find('a')
                        if link and link.get('href'):
                            player['profile_url'] = link.get('href')
                    else:
                        value = self._clean_cell_text(cell)

                    if value and value != '-':
                        player[field] = value

            if player.get('name'):
                players.append(player)

        return players

    def _parse_jsonld_roster(self, soup) -> List[Dict]:
        """Parse JSON-LD Schema.org Person data from roster pages.
        Some SIDEARM D2/D3 sites embed roster in JSON-LD script tags."""
        import json as _json
        players = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = _json.loads(script.string or '')
            except (ValueError, TypeError):
                continue

            items = []
            # Can be a single object or a list
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # ItemList with itemListElement
                if data.get('@type') == 'ItemList':
                    items = [el.get('item', el) for el in data.get('itemListElement', [])]
                elif data.get('@type') == 'Person':
                    items = [data]

            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get('@type') != 'Person':
                    continue
                name = item.get('name', '').strip()
                if not name:
                    continue
                players.append({
                    'name': name,
                    'position': None,
                    'class_year': None,
                    'height': None,
                    'weight': None,
                    'bats': None,
                    'throws': None,
                })

        return players

    def _parse_card_roster(self, cards) -> List[Dict]:
        """Parse card-style roster layout"""
        players = []

        for card in cards:
            player = {}

            # Name
            name_elem = card.find(['h3', 'h4', 'a'], class_=re.compile(r'name|title', re.I))
            if not name_elem:
                name_elem = card.find(['h3', 'h4'])
            if name_elem:
                player['name'] = name_elem.get_text(strip=True)
                if name_elem.name == 'a' and name_elem.get('href'):
                    player['profile_url'] = name_elem.get('href')

            # Number
            num_elem = card.find(class_=re.compile(r'number|jersey', re.I))
            if num_elem:
                player['jersey_number'] = num_elem.get_text(strip=True).replace('#', '')

            # Position
            pos_elem = card.find(class_=re.compile(r'position', re.I))
            if pos_elem:
                player['position'] = pos_elem.get_text(strip=True)

            # Other details - look for spans with info
            for span in card.find_all(['span', 'div'], class_=re.compile(r'detail|info|meta', re.I)):
                text = span.get_text(strip=True)

                # Class year patterns
                if re.match(r'^(Fr\.|So\.|Jr\.|Sr\.|Gr\.|Freshman|Sophomore|Junior|Senior|Graduate)', text, re.I):
                    player['class_year'] = text
                # Height pattern (5-10, 6-2, etc.)
                elif re.match(r'^\d-\d{1,2}$', text):
                    player['height'] = text
                # Weight pattern (180, 205, etc.)
                elif re.match(r'^\d{3}$', text):
                    player['weight'] = text
                # Bats/Throws (R/R, L/L, S/R, etc.)
                elif re.match(r'^[RLS]/[RLS]$', text, re.I):
                    player['bats_throws'] = text

            if player.get('name'):
                players.append(player)

        return players

    # ── Generic parsers (non-SIDEARM fallback) ──────────────────────

    def _parse_generic_roster(self, soup) -> List[Dict]:
        """
        Strategy 5: Generic roster parser for non-SIDEARM sites.
        Scores all tables by how "roster-like" they are and parses the best one.
        Also tries non-table layouts (repeating div/li patterns).
        """
        # Score all tables
        tables = soup.find_all('table')
        scored_tables = []

        for table in tables:
            score = 0
            headers = []

            thead = table.find('thead')
            if thead:
                headers = [th.get_text(strip=True).lower() for th in thead.find_all(['th', 'td'])]
            else:
                first_row = table.find('tr')
                if first_row:
                    headers = [c.get_text(strip=True).lower() for c in first_row.find_all(['th', 'td'])]

            headers_lower = [h.replace('.', '').replace('#', 'no').strip() for h in headers]

            # Positive signals
            if any(h in ('name', 'player') or 'name' in h for h in headers_lower):
                score += 3
            if any(h in ('pos', 'position') for h in headers_lower):
                score += 2
            if any(h in ('yr', 'cl', 'class', 'year', 'elig') for h in headers_lower):
                score += 2
            if any(h in ('no', 'number', 'num') for h in headers_lower):
                score += 1
            if any(h in ('ht', 'height') for h in headers_lower):
                score += 1
            if any(h in ('wt', 'weight') for h in headers_lower):
                score += 1
            if any(h in ('hometown', 'high school', 'hs') for h in headers_lower):
                score += 1

            # Row count bonus (baseball rosters typically 15-55 players)
            rows = table.find_all('tr')
            row_count = len(rows) - 1  # subtract header
            if 15 <= row_count <= 55:
                score += 1

            # Negative signals: this is a schedule, standings, or stats table
            if any(h in ('schedule', 'date', 'opponent', 'opp', 'location', 'result',
                         'avg', 'era', 'ab', 'ip', 'rbi', 'w-l')
                   for h in headers_lower):
                score -= 5

            if score >= 5:
                scored_tables.append((score, table))

        # Parse the highest-scoring table
        if scored_tables:
            scored_tables.sort(key=lambda x: -x[0])
            best_table = scored_tables[0][1]
            players = self._parse_table_roster(best_table)
            if players:
                return players

        # Non-table fallback: look for repeating div/li patterns
        players = self._parse_repeating_elements_roster(soup)
        return players

    def _parse_repeating_elements_roster(self, soup) -> List[Dict]:
        """
        Parse non-table roster layouts where players are in repeating
        div or li elements with the same class structure.
        """
        # Look for containers that have many similar children
        candidates = []

        for container_tag in ['ul', 'ol', 'div', 'section']:
            for container in soup.find_all(container_tag):
                children = container.find_all(recursive=False)
                if len(children) < 10:
                    continue

                # Check if children share common class patterns
                class_counter = {}
                for child in children:
                    cls = tuple(sorted(child.get('class', [])))
                    if cls:
                        class_counter[cls] = class_counter.get(cls, 0) + 1

                # Need at least 10 siblings with the same class (roster-sized)
                for cls, count in class_counter.items():
                    if count >= 10:
                        matching = [c for c in children
                                    if tuple(sorted(c.get('class', []))) == cls]
                        candidates.append((count, matching))

        if not candidates:
            return []

        # Try the largest group of matching elements
        candidates.sort(key=lambda x: -x[0])
        elements = candidates[0][1]

        players = []
        for elem in elements:
            player = self._extract_player_from_element(elem)
            if player and player.get('name'):
                players.append(player)

        # Only return if it looks roster-sized
        if len(players) >= 10:
            return players
        return []

    def _extract_player_from_element(self, elem) -> Optional[Dict]:
        """Extract player data from a generic HTML element."""
        player = {}

        # Try to find name: headings, links with name-like content
        for tag in ['h3', 'h4', 'h2', 'h5', 'a']:
            name_elem = elem.find(tag)
            if name_elem:
                text = name_elem.get_text(strip=True)
                # Must look like a name (2+ words, not a number)
                if text and ' ' in text and not re.match(r'^[\d.\-/]+$', text):
                    player['name'] = re.sub(r'\s+', ' ', text).strip()
                    break

        if not player.get('name'):
            return None

        # Extract other fields from text content
        all_text = elem.get_text(' ', strip=True)

        # Position (common baseball positions)
        pos_match = re.search(
            r'\b(RHP|LHP|P|C|1B|2B|3B|SS|LF|CF|RF|OF|DH|INF|IF|UT|UTIL)\b',
            all_text
        )
        if pos_match:
            player['position'] = pos_match.group(1)

        # Class year
        yr_match = re.search(
            r'\b(Fr\.|So\.|Jr\.|Sr\.|Gr\.|Freshman|Sophomore|Junior|Senior|Graduate|R-Fr\.|R-So\.|R-Jr\.|R-Sr\.)\b',
            all_text, re.I
        )
        if yr_match:
            player['class_year'] = yr_match.group(1)

        # Height (e.g., 6-2, 5-11, 6'2")
        ht_match = re.search(r'\b(\d)[\'′\-](\d{1,2})[\"″]?\b', all_text)
        if ht_match:
            player['height'] = f"{ht_match.group(1)}-{ht_match.group(2)}"

        # Weight (3-digit number near height context)
        wt_match = re.search(r'\b(1[5-9]\d|2[0-9]\d|3[0-3]\d)\s*(?:lbs?\.?)?\b', all_text)
        if wt_match:
            player['weight'] = wt_match.group(1)

        # Bats/Throws
        bt_match = re.search(r'\b([RLS])\s*/\s*([RLS])\b', all_text, re.I)
        if bt_match:
            player['bats_throws'] = f"{bt_match.group(1).upper()}/{bt_match.group(2).upper()}"

        return player

    def parse_generic_batting_stats(self, html: str) -> Dict[str, Dict]:
        """
        Parse batting stats from non-SIDEARM pages by scoring tables.
        Falls back when standard batting table detection fails.
        """
        soup = BeautifulSoup(html, 'html.parser')
        return self._find_and_parse_generic_stats(soup, 'batting')

    def parse_generic_pitching_stats(self, html: str) -> Dict[str, Dict]:
        """
        Parse pitching stats from non-SIDEARM pages by scoring tables.
        Falls back when standard pitching table detection fails.
        """
        soup = BeautifulSoup(html, 'html.parser')
        return self._find_and_parse_generic_stats(soup, 'pitching')

    def _find_and_parse_generic_stats(self, soup, stat_type: str) -> Dict[str, Dict]:
        """
        Score all tables for how likely they are to contain batting/pitching stats.
        """
        tables = soup.find_all('table')
        scored_tables = []

        batting_indicators = {'avg', 'ab', 'hr', 'rbi', 'obp', 'slg', 'ops', 'h', 'r', 'bb'}
        pitching_indicators = {'era', 'ip', 'w', 'sv', 'whip', 'so', 'er', 'gs', 'bb'}

        indicators = batting_indicators if stat_type == 'batting' else pitching_indicators

        for table in tables:
            headers = []
            thead = table.find('thead')
            if thead:
                headers = [th.get_text(strip=True).lower().replace('.', '').replace('%', '')
                           for th in thead.find_all(['th', 'td'])]
            else:
                first_row = table.find('tr')
                if first_row:
                    headers = [c.get_text(strip=True).lower().replace('.', '').replace('%', '')
                               for c in first_row.find_all(['th', 'td'])]

            headers_set = set(headers)
            matches = len(headers_set & indicators)

            if matches >= 3:
                # Disambiguate: batting tables have 'avg'/'rbi', pitching have 'era'/'ip'
                if stat_type == 'batting' and 'era' in headers_set:
                    continue  # This is a pitching table
                if stat_type == 'pitching' and ('avg' in headers_set or 'rbi' in headers_set):
                    if 'era' not in headers_set:
                        continue  # This is a batting table

                scored_tables.append((matches, table))

        if not scored_tables:
            return {}

        scored_tables.sort(key=lambda x: -x[0])
        best_table = scored_tables[0][1]
        return self._parse_stats_table(best_table, stat_type)

    # ── Nuxt payload parser (SIDEARM v3) ─────────────────────────────

    def _extract_nuxt_payload(self, html: str):
        """Extract devalue-serialized Nuxt payload from HTML script tags.
        Returns the parsed JSON list or None."""
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for s in scripts:
            s = s.strip()
            if s.startswith('[["ShallowReactive"') or s.startswith('[["Reactive"'):
                try:
                    return json.loads(s)
                except json.JSONDecodeError:
                    continue
        return None

    def parse_nuxt_roster(self, html: str, school_name: str) -> List[Dict]:
        """
        Extract roster data from a SIDEARM v3 Nuxt devalue payload.
        The payload is embedded in a <script type="application/json" id="__NUXT_DATA__"> tag.

        Payload structure (after devalue resolution):
          payload[1]["data"] -> (resolve ShallowReactive) -> dict with keys like:
            "roster-{id}-players-list-page-{n}" -> {"players": [...], "meta": {...}}

        Each player entry contains:
          - player: {first_name, last_name, full_name, slug}
          - player_position: {abbreviation, name}  (e.g. "INF", "RHP", "C")
          - class_level: {name}  (e.g. "Redshirt Junior", "Sophomore")
          - height_feet, height_inches, weight, jersey_number
          - profile_field_values: [{profileField: {name: "B/T"}, value: "R/R"}]

        Returns list of player dicts in the same format as parse_roster().
        """
        payload = self._extract_nuxt_payload(html)
        if not payload:
            return []

        # Navigate to the roster players list
        try:
            root = payload[1]
            data_idx = root.get('data')
            if data_idx is None:
                return []
            data_obj = payload[data_idx]
            # Resolve ShallowReactive/Reactive wrapper
            if isinstance(data_obj, list) and len(data_obj) == 2 and isinstance(data_obj[0], str) \
                    and data_obj[0] in ('ShallowReactive', 'Reactive'):
                data_obj = payload[data_obj[1]]
            if not isinstance(data_obj, dict):
                return []

            # Find the roster players key (pattern: "roster-{id}-players-list-page-{n}")
            roster_key = None
            for k in data_obj.keys():
                if 'roster' in k and 'players-list' in k:
                    roster_key = k
                    break
            if not roster_key:
                return []

            roster_ref = data_obj[roster_key]
            roster_container = payload[roster_ref]  # {'players': X, 'meta': Y}
            players_list_ref = roster_container['players']
            player_refs = payload[players_list_ref]  # list of indices
        except (IndexError, KeyError, TypeError, AttributeError) as e:
            logger.debug(f"Nuxt roster navigation failed: {e}")
            return []

        # Resolve each player entry individually (avoid resolving entire tree)
        players = []
        for ref in player_refs:
            try:
                player_data = self._resolve_nuxt_payload(payload, ref)
                if not isinstance(player_data, dict):
                    continue

                player_obj = player_data.get('player', {})
                pos_obj = player_data.get('player_position', {})
                class_obj = player_data.get('class_level', {})

                name = player_obj.get('full_name', '') if isinstance(player_obj, dict) else ''
                if not name:
                    continue

                entry = {'name': name, 'school': school_name}

                jn = player_data.get('jersey_number')
                if jn is not None:
                    entry['jersey_number'] = str(jn)

                if isinstance(pos_obj, dict):
                    entry['position'] = pos_obj.get('abbreviation') or pos_obj.get('name', '')

                if isinstance(class_obj, dict):
                    entry['class_year'] = class_obj.get('name', '')

                ht_ft = player_data.get('height_feet')
                ht_in = player_data.get('height_inches')
                if ht_ft is not None and ht_in is not None:
                    entry['height'] = f"{ht_ft}-{ht_in}"

                wt = player_data.get('weight')
                if wt is not None:
                    entry['weight'] = str(wt)

                # Extract B/T from profile_field_values
                pfvs = player_data.get('profile_field_values', [])
                if isinstance(pfvs, list):
                    for pfv in pfvs:
                        if isinstance(pfv, dict):
                            pf = pfv.get('profileField', pfv.get('profile_field', {}))
                            if isinstance(pf, dict) and pf.get('name') == 'B/T':
                                entry['bats_throws'] = pfv.get('value', '')

                players.append(entry)
            except Exception as e:
                logger.debug(f"Failed to resolve Nuxt roster player: {e}")
                continue

        if players:
            logger.info(f"  Nuxt roster: {len(players)} players from {school_name}")

        return players

    def _resolve_nuxt_payload(self, payload: list, idx: int, depth: int = 0):
        """Recursively resolve Nuxt devalue references."""
        if depth > 20 or not isinstance(idx, int) or idx < 0 or idx >= len(payload):
            return idx
        val = payload[idx]
        if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str) \
                and val[0] in ("ShallowReactive", "Reactive", "ShallowRef", "Ref"):
            return self._resolve_nuxt_payload(payload, val[1], depth + 1)
        if isinstance(val, dict):
            return {k: self._resolve_nuxt_payload(payload, v, depth + 1) for k, v in val.items()}
        if isinstance(val, list):
            return [self._resolve_nuxt_payload(payload, item, depth + 1) for item in val]
        return val

    def parse_nuxt_stats(self, html: str) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
        """
        Extract batting and pitching stats from a SIDEARM v3 Nuxt payload.
        Returns (batting_stats, pitching_stats) dicts keyed by player name.
        Returns ({}, {}) if no Nuxt payload found.
        """
        batting = {}
        pitching = {}

        # Find the devalue payload script
        payload = self._extract_nuxt_payload(html)

        if not payload:
            return batting, pitching

        # Navigate: root → pinia → statsSeason → cumulativeStats → first season → overallIndividualStats
        try:
            root = payload[1]  # root state object
            pinia_idx = root.get('pinia')
            if pinia_idx is None:
                return batting, pitching
            pinia = payload[pinia_idx]
            if isinstance(pinia, list):
                pinia = payload[pinia[1]] if len(pinia) == 2 else {}

            stats_season_idx = pinia.get('statsSeason')
            if stats_season_idx is None:
                return batting, pitching
            stats_season = self._resolve_nuxt_payload(payload, stats_season_idx)

            cume = stats_season.get('cumulativeStats', {})
            if not cume:
                return batting, pitching

            # Get first (usually only) season entry
            first_season_key = next(iter(cume))
            season_data = cume[first_season_key]

            # Early-season: cumulativeStats can have {season_id: None}
            if not season_data:
                return batting, pitching

            individual = season_data.get('overallIndividualStats', {})
            ind_stats = individual.get('individualStats', {})

            hitting_list = ind_stats.get('individualHittingStats', [])
            pitching_list = ind_stats.get('individualPitchingStats', [])

        except (IndexError, KeyError, TypeError, StopIteration, AttributeError) as e:
            logger.debug(f"Nuxt payload navigation failed: {e}")
            return batting, pitching

        # Map hitting stats
        HITTING_MAP = {
            'atBats': 'at_bats', 'runs': 'runs', 'hits': 'hits',
            'doubles': 'doubles', 'triples': 'triples', 'homeRuns': 'home_runs',
            'runsBattedIn': 'rbi', 'walks': 'walks', 'strikeouts': 'strikeouts',
            'stolenBases': 'stolen_bases', 'caughtStealing': 'caught_stealing',
            'hitByPitch': 'hit_by_pitch', 'sacrificeFlies': 'sacrifice_flies',
            'sacrificeHits': 'sacrifice_hits', 'totalBases': 'total_bases',
            'gamesPlayed': 'games', 'groundedIntoDoublePlay': 'grounded_into_dp',
        }
        HITTING_FLOAT_MAP = {
            'battingAverage': 'batting_average', 'onBasePercentage': 'on_base_percentage',
            'sluggingPercentage': 'slugging_percentage', 'ops': 'ops',
        }

        for p in hitting_list:
            if p.get('isAFooterStat'):
                continue
            name = p.get('playerName', '')
            if not name:
                continue
            # Normalize "Last, First" to "First Last"
            if ',' in name:
                parts = name.split(',', 1)
                name = f"{parts[1].strip()} {parts[0].strip()}"

            stats = {}
            for src, dst in HITTING_MAP.items():
                val = p.get(src)
                if val is not None:
                    try:
                        stats[dst] = int(float(val))
                    except (ValueError, TypeError):
                        pass
            for src, dst in HITTING_FLOAT_MAP.items():
                val = p.get(src)
                if val is not None:
                    try:
                        stats[dst] = float(val)
                    except (ValueError, TypeError):
                        pass

            if stats:
                stats = self._calc_batting_derived(stats)
                batting[name] = stats

        # Map pitching stats
        PITCHING_MAP = {
            'appearances': 'appearances', 'gamesStarted': 'games_started',
            'wins': 'wins', 'losses': 'losses', 'saves': 'saves',
            'combinedShutouts': 'shutouts', 'hitsAllowed': 'hits_allowed',
            'runsAllowed': 'runs_allowed', 'earnedRunsAllowed': 'earned_runs',
            'walksAllowed': 'walks', 'strikeouts': 'strikeouts',
            'homeRunsAllowed': 'home_runs_allowed', 'hitBatters': 'hit_batters',
            'wildPitches': 'wild_pitches', 'balks': 'balks',
        }
        PITCHING_FLOAT_MAP = {
            'earnedRunAverage': 'era', 'whip': 'whip',
        }

        for p in pitching_list:
            if p.get('isAFooterStat'):
                continue
            name = p.get('playerName', '')
            if not name:
                continue
            if ',' in name:
                parts = name.split(',', 1)
                name = f"{parts[1].strip()} {parts[0].strip()}"

            stats = {}
            for src, dst in PITCHING_MAP.items():
                val = p.get(src)
                if val is not None:
                    try:
                        stats[dst] = int(float(val))
                    except (ValueError, TypeError):
                        pass
            for src, dst in PITCHING_FLOAT_MAP.items():
                val = p.get(src)
                if val is not None:
                    try:
                        stats[dst] = float(val)
                    except (ValueError, TypeError):
                        pass

            # Innings pitched needs special handling (string like "4.1")
            ip_val = p.get('inningsPitched')
            if ip_val is not None:
                stats['innings_pitched'] = self._parse_stat_value(str(ip_val), 'innings_pitched')

            if stats:
                stats = self._calc_pitching_derived(stats)
                pitching[name] = stats

        if batting or pitching:
            logger.info(f"  Nuxt payload: {len(batting)} batting, {len(pitching)} pitching")

        return batting, pitching

    def parse_sidearm_api_stats(self, data) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
        """Parse stats from a SIDEARM JSON API response.
        The API may return various formats; try common structures."""
        batting = {}
        pitching = {}

        if not isinstance(data, (dict, list)):
            return batting, pitching

        # Format 1: {"hitting": [...], "pitching": [...]}
        hitting_list = None
        pitching_list = None

        if isinstance(data, dict):
            # Try direct keys
            for key in ('hitting', 'hittingStats', 'batting', 'battingStats',
                        'individualHittingStats'):
                if key in data and isinstance(data[key], list):
                    hitting_list = data[key]
                    break
            for key in ('pitching', 'pitchingStats', 'individualPitchingStats'):
                if key in data and isinstance(data[key], list):
                    pitching_list = data[key]
                    break

            # Try nested: data.stats.hitting / data.individualStats.*
            if not hitting_list:
                stats = data.get('stats', data.get('individualStats', {}))
                if isinstance(stats, dict):
                    for key in ('hitting', 'hittingStats', 'batting',
                                'individualHittingStats'):
                        if key in stats and isinstance(stats[key], list):
                            hitting_list = stats[key]
                            break
                    for key in ('pitching', 'pitchingStats',
                                'individualPitchingStats'):
                        if key in stats and isinstance(stats[key], list):
                            pitching_list = stats[key]
                            break

        if hitting_list:
            batting = self._parse_api_stat_list(hitting_list, 'batting')
        if pitching_list:
            pitching = self._parse_api_stat_list(pitching_list, 'pitching')

        return batting, pitching

    def _parse_api_stat_list(self, stat_list: list, stat_type: str) -> Dict[str, Dict]:
        """Parse a list of player stat objects from an API response."""
        result = {}

        HITTING_MAP = {
            'atBats': 'at_bats', 'ab': 'at_bats',
            'runs': 'runs', 'r': 'runs',
            'hits': 'hits', 'h': 'hits',
            'doubles': 'doubles', '2b': 'doubles',
            'triples': 'triples', '3b': 'triples',
            'homeRuns': 'home_runs', 'hr': 'home_runs',
            'runsBattedIn': 'rbi', 'rbi': 'rbi',
            'walks': 'walks', 'bb': 'walks',
            'strikeouts': 'strikeouts', 'so': 'strikeouts', 'k': 'strikeouts',
            'stolenBases': 'stolen_bases', 'sb': 'stolen_bases',
            'caughtStealing': 'caught_stealing', 'cs': 'caught_stealing',
            'hitByPitch': 'hit_by_pitch', 'hbp': 'hit_by_pitch',
            'sacrificeFlies': 'sacrifice_flies', 'sf': 'sacrifice_flies',
            'sacrificeHits': 'sacrifice_hits', 'sh': 'sacrifice_hits',
            'gamesPlayed': 'games', 'g': 'games', 'gp': 'games',
        }
        HITTING_FLOAT = {
            'battingAverage': 'batting_average', 'avg': 'batting_average',
            'onBasePercentage': 'on_base_percentage', 'obp': 'on_base_percentage',
            'sluggingPercentage': 'slugging_percentage', 'slg': 'slugging_percentage',
            'ops': 'ops',
        }
        PITCHING_MAP = {
            'appearances': 'appearances', 'app': 'appearances', 'g': 'appearances',
            'gamesStarted': 'games_started', 'gs': 'games_started',
            'wins': 'wins', 'w': 'wins',
            'losses': 'losses', 'l': 'losses',
            'saves': 'saves', 'sv': 'saves',
            'hitsAllowed': 'hits_allowed',
            'runsAllowed': 'runs_allowed',
            'earnedRunsAllowed': 'earned_runs', 'er': 'earned_runs',
            'walksAllowed': 'walks', 'bb': 'walks',
            'strikeouts': 'strikeouts', 'so': 'strikeouts', 'k': 'strikeouts',
            'homeRunsAllowed': 'home_runs_allowed',
            'hitBatters': 'hit_batters', 'hb': 'hit_batters',
            'wildPitches': 'wild_pitches', 'wp': 'wild_pitches',
        }
        PITCHING_FLOAT = {
            'earnedRunAverage': 'era', 'era': 'era',
            'whip': 'whip',
        }

        int_map = HITTING_MAP if stat_type == 'batting' else PITCHING_MAP
        float_map = HITTING_FLOAT if stat_type == 'batting' else PITCHING_FLOAT

        for p in stat_list:
            if not isinstance(p, dict):
                continue
            if p.get('isAFooterStat') or p.get('isFooter'):
                continue

            name = p.get('playerName', p.get('name', p.get('player', '')))
            if not name or not isinstance(name, str):
                continue
            # Normalize "Last, First" to "First Last"
            if ',' in name:
                parts = name.split(',', 1)
                name = f"{parts[1].strip()} {parts[0].strip()}"

            stats = {}
            for src, dst in int_map.items():
                val = p.get(src)
                if val is not None:
                    try:
                        stats[dst] = int(float(val))
                    except (ValueError, TypeError):
                        pass
            for src, dst in float_map.items():
                val = p.get(src)
                if val is not None:
                    try:
                        stats[dst] = float(val)
                    except (ValueError, TypeError):
                        pass

            # Innings pitched special handling
            if stat_type == 'pitching':
                ip_val = p.get('inningsPitched', p.get('ip'))
                if ip_val is not None:
                    stats['innings_pitched'] = self._parse_stat_value(
                        str(ip_val), 'innings_pitched')

            if stats:
                if stat_type == 'batting':
                    stats = self._calc_batting_derived(stats)
                else:
                    stats = self._calc_pitching_derived(stats)
                result[name] = stats

        return result

    # ── HTML table parsers ───────────────────────────────────────────

    def parse_batting_stats(self, html: str) -> Dict[str, Dict]:
        """Parse batting statistics page"""
        soup = BeautifulSoup(html, 'html.parser')
        stats = {}

        # Find batting/hitting stats table
        stats_table = None

        for selector in [
            ('table', {'id': re.compile(r'batting|hitting|offensive', re.I)}),
            ('table', {'class': re.compile(r'batting|hitting|offensive', re.I)}),
            ('section', {'id': re.compile(r'batting|hitting', re.I)}),
        ]:
            elem = soup.find(*selector)
            if elem:
                stats_table = elem if elem.name == 'table' else elem.find('table')
                break

        # Try finding by heading
        if not stats_table:
            for heading in soup.find_all(['h2', 'h3', 'h4']):
                if re.search(r'batting|hitting|offensive', heading.get_text(), re.I):
                    stats_table = heading.find_next('table')
                    break

        # Fallback: find table with batting-like column headers (SIDEARM v3)
        if not stats_table:
            for table in soup.find_all('table'):
                thead = table.find('thead')
                if not thead:
                    continue
                headers = {th.get_text(strip=True).lower().replace('.', '').replace('%', '')
                           for th in thead.find_all(['th', 'td'])}
                batting_indicators = {'avg', 'ab', 'rbi', 'slg', 'obp', 'ops'}
                if len(headers & batting_indicators) >= 3:
                    stats_table = table
                    logger.debug("Found batting table via column header detection")
                    break

        if not stats_table:
            logger.debug("No batting stats table found")
            return stats

        stats = self._parse_stats_table(stats_table, 'batting')
        return stats

    def parse_pitching_stats(self, html: str) -> Dict[str, Dict]:
        """Parse pitching statistics page"""
        soup = BeautifulSoup(html, 'html.parser')
        stats = {}

        stats_table = None

        for selector in [
            ('table', {'id': re.compile(r'pitching', re.I)}),
            ('table', {'class': re.compile(r'pitching', re.I)}),
            ('section', {'id': re.compile(r'pitching', re.I)}),
        ]:
            elem = soup.find(*selector)
            if elem:
                stats_table = elem if elem.name == 'table' else elem.find('table')
                break

        if not stats_table:
            for heading in soup.find_all(['h2', 'h3', 'h4']):
                if re.search(r'pitching', heading.get_text(), re.I):
                    stats_table = heading.find_next('table')
                    break

        # Fallback: find table with pitching-like column headers
        if not stats_table:
            for table in soup.find_all('table'):
                thead = table.find('thead')
                if not thead:
                    continue
                headers = {th.get_text(strip=True).lower().replace('.', '').replace('%', '')
                           for th in thead.find_all(['th', 'td'])}
                pitching_indicators = {'era', 'ip', 'whip', 'sv', 'gs'}
                if len(headers & pitching_indicators) >= 3:
                    stats_table = table
                    logger.debug("Found pitching table via column header detection")
                    break

        if not stats_table:
            logger.debug("No pitching stats table found")
            return stats

        stats = self._parse_stats_table(stats_table, 'pitching')
        return stats

    def _parse_stats_table(self, table, stat_type: str) -> Dict[str, Dict]:
        """Generic stats table parser"""
        stats = {}

        BATTING_COLS = {
            'g': 'games', 'gp': 'games', 'gp-gs': 'games',
            'ab': 'at_bats',
            'r': 'runs',
            'h': 'hits',
            '2b': 'doubles',
            '3b': 'triples',
            'hr': 'home_runs',
            'rbi': 'rbi',
            'bb': 'walks',
            'so': 'strikeouts', 'k': 'strikeouts',
            'sb': 'stolen_bases', 'sb-att': 'stolen_bases',
            'cs': 'caught_stealing',
            'avg': 'batting_average', 'ba': 'batting_average',
            'obp': 'on_base_percentage', 'ob': 'on_base_percentage',
            'slg': 'slugging_percentage', 'slg%': 'slugging_percentage',
            'ops': 'ops',
            'hbp': 'hit_by_pitch',
            'sf': 'sacrifice_flies',
            'sh': 'sacrifice_hits',
            'tb': 'total_bases',
        }

        PITCHING_COLS = {
            'app': 'appearances', 'g': 'appearances',
            'gs': 'games_started',
            'w': 'wins',
            'l': 'losses',
            'sv': 'saves',
            'cg': 'complete_games',
            'sho': 'shutouts',
            'ip': 'innings_pitched',
            'h': 'hits_allowed',
            'r': 'runs_allowed',
            'er': 'earned_runs',
            'bb': 'walks',
            'so': 'strikeouts', 'k': 'strikeouts',
            'hr': 'home_runs_allowed',
            'era': 'era',
            'whip': 'whip',
            'hbp': 'hit_batters',
            'wp': 'wild_pitches',
            'bk': 'balks',
        }

        col_map = BATTING_COLS if stat_type == 'batting' else PITCHING_COLS

        # Get headers
        headers = []
        header_row = table.find('thead')
        if header_row:
            headers = [th.get_text(strip=True).lower().replace('.', '').replace('%', '')
                       for th in header_row.find_all(['th', 'td'])]
        else:
            first_row = table.find('tr')
            if first_row:
                headers = [cell.get_text(strip=True).lower().replace('.', '').replace('%', '')
                           for cell in first_row.find_all(['th', 'td'])]

        # Find name column index
        name_idx = None
        for i, h in enumerate(headers):
            if h in ['name', 'player', 'athlete']:
                name_idx = i
                break

        # Parse rows
        rows = table.find_all('tr')
        start_idx = 1 if headers else 0

        for row in rows[start_idx:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                continue

            # Skip total/team rows
            row_text = row.get_text().lower()
            if 'total' in row_text or 'team' in row_text or 'opponent' in row_text:
                continue

            player_name = None
            player_stats = {}

            for i, cell in enumerate(cells):
                if i >= len(headers):
                    continue

                header = headers[i]
                value = cell.get_text(strip=True)

                # Player name
                if i == name_idx or header in ['name', 'player', 'athlete']:
                    player_name = self._extract_name(cell)
                    continue

                # Skip jersey number
                if header in ['no', 'number', '#']:
                    continue

                # Map stat
                stat_key = col_map.get(header)
                if stat_key:
                    parsed_value = self._parse_stat_value(value, stat_key)
                    if parsed_value is not None:
                        player_stats[stat_key] = parsed_value

            # Reject names that look like stat values (e.g. ".500", "12", "4-2")
            if player_name and re.match(r'^[\d.\-/]+$', player_name):
                player_name = None

            if player_name and player_stats:
                if stat_type == 'batting':
                    player_stats = self._calc_batting_derived(player_stats)
                else:
                    player_stats = self._calc_pitching_derived(player_stats)

                stats[player_name] = player_stats

        return stats

    def _parse_stat_value(self, value: str, stat_key: str):
        """Parse a stat value to appropriate type"""
        if not value or value.strip() in ['', '-', 'N/A', '.', '--']:
            return None

        value = value.strip()

        # Handle "X - Y" format (GP-GS, SB-ATT) - take first number
        if ' - ' in value:
            value = value.split(' - ')[0].strip()

        try:
            if stat_key == 'innings_pitched':
                # Handle 45.1 (45 and 1/3 innings) format
                if '.' in value:
                    parts = value.split('.')
                    whole = int(parts[0])
                    partial = int(parts[1]) if len(parts) > 1 else 0
                    return whole + (partial / 3)
                return float(value)

            if stat_key in ['batting_average', 'on_base_percentage', 'slugging_percentage',
                            'ops', 'era', 'whip']:
                return float(value)

            return int(float(value))

        except (ValueError, TypeError):
            return None

    def _calc_batting_derived(self, stats: Dict) -> Dict:
        """Calculate XBH, XBH:K, etc."""
        doubles = stats.get('doubles') or 0
        triples = stats.get('triples') or 0
        home_runs = stats.get('home_runs') or 0
        strikeouts = stats.get('strikeouts') or 0

        stats['extra_base_hits'] = doubles + triples + home_runs

        if strikeouts > 0:
            stats['xbh_to_k'] = round(stats['extra_base_hits'] / strikeouts, 3)
        else:
            stats['xbh_to_k'] = None

        # OPS if missing
        if not stats.get('ops'):
            obp = stats.get('on_base_percentage')
            slg = stats.get('slugging_percentage')
            if obp is not None and slg is not None:
                stats['ops'] = round(obp + slg, 3)

        return stats

    def _calc_pitching_derived(self, stats: Dict) -> Dict:
        """Calculate K/9, BB/9, K:BB"""
        ip = stats.get('innings_pitched') or 0
        strikeouts = stats.get('strikeouts') or 0
        walks = stats.get('walks') or 0

        if ip > 0:
            stats['k_per_9'] = round((strikeouts / ip) * 9, 2)
            stats['bb_per_9'] = round((walks / ip) * 9, 2)
        else:
            stats['k_per_9'] = None
            stats['bb_per_9'] = None

        if walks > 0:
            stats['k_to_bb'] = round(strikeouts / walks, 2)
        else:
            stats['k_to_bb'] = None

        return stats
