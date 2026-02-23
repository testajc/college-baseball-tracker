# College Baseball Tracker - Project Status

## Overview

A Next.js web application for tracking college baseball players, teams, and transfer portal activity across D1, D2, and D3 divisions.

**Live URL:** https://college-baseball-tracker.vercel.app

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Database:** PostgreSQL with Prisma ORM
- **Auth:** NextAuth.js with credentials provider
- **Styling:** Tailwind CSS 4
- **UI Components:** Radix UI, Lucide icons
- **Tables:** TanStack React Table
- **Email:** Resend
- **Hosting:** Vercel

## What's Been Built

### Pages

| Route | Description |
|-------|-------------|
| `/` | Home/landing page |
| `/login` | Login page |
| `/register` | Registration page (restricted to allowlisted emails) |
| `/players` | Player search with filters and pagination |
| `/players/[id]` | Individual player detail page |
| `/teams` | Team listing with division/search filters |
| `/teams/[id]` | Team detail page with roster |
| `/portal` | Transfer portal players view |
| `/favorites` | User's favorited players (requires auth) |
| `/settings` | User settings (email alerts toggle) |

### API Routes

| Route | Description |
|-------|-------------|
| `/api/auth/[...nextauth]` | NextAuth authentication |
| `/api/auth/register` | User registration with email allowlist |
| `/api/players` | Player search/filter with pagination |
| `/api/players/[id]` | Individual player data |
| `/api/teams` | Team listing + conference list for filters |
| `/api/teams/[id]` | Individual team data |
| `/api/favorites` | Add/remove/list favorites |
| `/api/portal` | Portal players listing |
| `/api/settings` | User settings CRUD |
| `/api/notifications/portal-alert` | Portal alert email notifications |

### Components

- `Navbar` - Navigation with auth state
- `FilterPanel` - Comprehensive filter sidebar for players page
- `PlayerTable` - Sortable player data table
- `SearchBar` - Debounced search input
- `FavoriteButton` - Toggle favorite on players
- `Providers` - NextAuth session provider wrapper

### Data Model

- **Teams:** NCAA teams with division, conference, state, logo
- **Players:** Name, position, class year, physical attributes, team relation
- **HittingStats:** Full batting statistics with calculated rates (AVG, OBP, SLG, OPS, XBH:K)
- **PitchingStats:** Full pitching statistics with calculated rates (ERA, WHIP, K/9, BB/9, K/BB)
- **Users:** Auth with email/password, email alert preferences
- **Favorites:** User-player relationship for tracking
- **PortalAlert:** Tracks which portal alerts have been sent
- **EmailNotification:** Email notification history
- **ScrapeLog:** Data scraping job history

## What's Working

### Authentication
- Login/logout with NextAuth
- Registration restricted to emails in `ALLOWED_EMAILS` env var
- Route protection via middleware - unauthenticated users redirected to `/login`
- Public routes: `/login`, `/register`, `/api/auth/*`

### Player Filtering
Comprehensive filter system with conditional visibility:

**General Filters:**
- Division (D1, D2, D3)
- Position
- Conference
- Year (Fr., So., Jr., Sr., Gr.)
- Portal only checkbox
- Stat type toggle (hitting/pitching)

**Hitting Filters** (visible when hitting selected):
- Min AVG, OBP, SLG, OPS
- Min HR, RBI, SB
- Min XBH:K ratio
- Min AB

**Pitching Filters** (visible when pitching selected):
- Max ERA, WHIP
- Min K/9, K/BB
- Max BB/9
- Min Wins, Saves, IP

### Other Features
- Favorites system (add/remove players)
- Team pages with rosters
- Player detail pages with full stats
- Portal tracking
- Email notification system (Resend integration)

## Environment Variables

Required in Vercel:

```
DATABASE_URL=postgresql://...
NEXTAUTH_SECRET=...
NEXTAUTH_URL=https://college-baseball-tracker.vercel.app
ALLOWED_EMAILS=email1@example.com,email2@example.com
RESEND_API_KEY=... (for email notifications)
```

## Scraper (`scraper/`)

Full Python scraper that pulls rosters and stats from college athletics sites across all divisions.

### Architecture

| File | Description |
|------|-------------|
| `main.py` | Entry point - `run`, `diagnostic`, `status`, `recover` commands |
| `config.py` | Rate limiting, season start date (`2026-02-14`), error thresholds, browser config |
| `scheduler.py` | Smart scheduling - tracks which schools need scraping |
| `request_handler.py` | HTTP client with rate limiting, retries, circuit breaker, UA rotation, SSL bypass |
| `database.py` | PostgreSQL writer - saves scraped data to Prisma-compatible tables |
| `parsers/sidearm_parser.py` | HTML + Nuxt payload + generic table-scoring parser for SIDEARM and non-SIDEARM sites |
| `url_discovery.py` | Homepage crawler that discovers baseball roster/stats URLs when standard paths fail |
| `browser_scraper.py` | Playwright headless browser fallback for JS-rendered pages |
| `validate_schools.py` | Classifies failed schools, discovers correct URLs from conference sites, fixes CSV |
| `build_schools_db.py` | Builds `schools_database.csv` (971 schools across D1/D2/D3) |

### How Stats Parsing Works

Three parsing strategies, tried in order:

1. **Nuxt payload parser** (SIDEARM v3, most D1 schools) - Extracts the devalue-serialized JSON payload embedded in `<script>` tags. Gets batting AND pitching stats in one pass. Path: `statsSeason → cumulativeStats → overallIndividualStats → individualStats`
2. **HTML table parser** (older SIDEARM, D3/some D2) - Finds stats tables by id/class, heading text, or column header detection. Parses `<table>` elements directly.
3. **Generic table-scoring parser** (non-SIDEARM fallback) - Scores all tables on the page for stat-likeness (batting indicators: avg/ab/rbi; pitching indicators: era/ip/whip) and parses the best match.

### Roster Parsing Strategies (5 strategies, tried in order)

1. **Nuxt devalue payload** (SIDEARM v3) - Client-side rendered rosters
2. **Table with roster class** - `<table class="roster|sidearm-table">`
3. **Generic table detection** - Any table with name/player/no. headers and 6+ rows
4. **Card-based layout** - SIDEARM player card divs/lis
5. **JSON-LD Schema.org** - Person objects in `<script type="application/ld+json">`
6. **Generic roster scoring** (new) - Scores all tables by roster-likeness (+3 for Name column, +2 for Position, etc.) and falls back to repeating div/li element patterns

### URL Patterns

The scraper tries 10 URL paths each for rosters and stats (in order):
- SIDEARM: `/sports/baseball/roster`, `/sports/baseball/roster/2026`
- PrestoSports: `/sport/m-basebl/roster`, `/sports/bsb/roster`
- Other: `/sports/mens-baseball/roster`, `/teams/baseball/roster`, `/roster.aspx?path=baseball`, `/athletics/baseball/roster`, `/baseball/roster/`

Homepage redirects (301 → base URL) are detected and skipped.

### Recovery Strategies

When standard URL paths fail, the scraper has a multi-layer recovery pipeline:
1. **URL discovery** - When all paths return 404/405, crawls the athletics homepage to find correct baseball URLs (homepage links → baseball landing page → sitemap.xml)
2. **Generic parsers** - Table-scoring algorithm for non-SIDEARM HTML (both roster and stats)
3. **SSL bypass** - Retries with `verify=False` when SSL errors occur (recovers expired certs)
4. **Browser fallback** - Playwright headless Chromium renders JS-heavy pages (requires `playwright` install)

### Diagnostic Results (Feb 17, 2026)

Tested 7 schools including previously-failing ones — all now succeed:

| School | Players | Batting | Pitching | Notes |
|--------|---------|---------|----------|-------|
| Louisville (D1) | 43 | 13 | 17 | Nuxt payload |
| Arizona St. (D1) | 41 | 0 | 0 | Nuxt roster (was failing with 0 players) |
| Cincinnati (D1) | 38 | 0 | 0 | Nuxt roster (was failing with 0 players) |
| Arkansas (D1) | 39 | 14 | 13 | Fixed via expanded URL patterns |
| Jackson St. (D1) | 37 | 14 | 11 | Fixed via expanded URL patterns |
| Clemson (D1) | 40 | 11 | 13 | Stats URL now found |
| Chapman (D3) | 30 | 15 | 8 | HTML table parser |

### Running the Scraper

```bash
cd scraper
pip install -r requirements.txt
# Optional: install Playwright for JS-rendered page fallback
pip install playwright && playwright install chromium

# Test 7 schools (mix of D1/D3, previously-failing included)
python main.py diagnostic

# Full scrape (requires DATABASE_URL, respects season start date)
python main.py run
python main.py run --force     # ignore season start date
python main.py run --dry-run   # show what would be scraped

# Retry all previously-failed schools with recovery strategies
python main.py recover
python main.py recover --dry-run  # show what would be retried

# Check progress
python main.py status
```

### GitHub Actions

Daily scrape runs via `.github/workflows/daily-scrape.yml`:
- Cron: 6 AM UTC daily
- Checks season start date (Feb 21, 2026) before running
- Manual trigger with `force` option
- Saves progress artifacts between runs

### Known Scraper Issues

- **~128 unreachable schools** - Dead domains (DNS failure, connection refused), sites returning 403 on all paths, or non-standard JS-rendered sites with 0 parseable players. Mostly D2/D3 schools that have folded or changed hosting. Conference URL discovery recovered 106 of the original ~254.
- **~23 corrected-but-still-failing** - URLs found via conference sites but roster pages return 0 players (JS-rendered content or non-standard URL paths). Would benefit from Playwright.
- **~14 JS-rendered sites** - Sites reachable but returning 0 players (content rendered client-side). Would be recovered by installing Playwright (`pip install playwright && playwright install chromium`) — the browser fallback is implemented but requires the dependency.
- **Vanderbilt / WMT Games sites** - Some schools use WordPress + WMT Games plugin where stats are JS iframes from `wmt.games`. Roster works, stats return 0.
- **Pitching on older SIDEARM** - HTML table parser gets pitching fine on D3 sites. D1 SIDEARM v3 only server-renders batting HTML, but the Nuxt parser handles pitching.

## Database Stats (as of Feb 23, 2026)

| Table | Count |
|-------|-------|
| Teams | ~977 |
| Players | ~20,000+ |
| Hitting Stats | ~7,000+ |
| Pitching Stats | ~5,000+ |

| Division | Teams (scraped/total) | Coverage |
|----------|----------------------|----------|
| D1 | ~131/268 | ~49% |
| D2 | ~230/282 | ~82% |
| D3 | ~316/421 | ~75% |
| **Total** | **~977/971** | **~100%** |

Note: Team count exceeds CSV total because some schools have multiple entries or were added via redirect domains. The ~128 remaining missing schools are dead domains not recoverable from conference sites. ~23 have corrected URLs but need Playwright for JS-rendered rosters.

## Recent Changes

### Session 5 (Feb 23, 2026) - Conference URL Discovery
1. **`validate_schools.py`** (new) - School classification + conference URL discovery tool:
   - `--classify`: Categorizes failed schools (DNS_DEAD, NO_BASEBALL, REDIRECT_DOMAIN, etc.)
   - `--discover-from-conferences`: Scrapes 56 conference websites to find correct athletics URLs
   - `--update-csv`: Applies discovered URLs to `schools_database.csv`
   - `--rescrape`: Re-scrapes schools with corrected URLs
2. **Conference scraping** - Extracted SIDEARM JSON data from conference sites (member directories with athletics URLs)
3. **Results** - Found correct URLs for 106 schools, 83 successfully scraped with roster data
4. **DB growth** - Teams: 894 → 977 (+83), bringing D2 coverage to ~82% and D3 to ~75%

### Session 4 (Feb 17, 2026) - Recovery Strategies & Full D2/D3 Scrape
1. **Scraper recovery system** - Added multi-layer recovery for failed schools:
   - `url_discovery.py` (new) - Homepage crawler discovers correct baseball URLs when standard paths 404
   - Generic table-scoring parsers in `sidearm_parser.py` - Scores tables for roster/stats-likeness on non-SIDEARM sites
   - `browser_scraper.py` (new) - Playwright headless Chromium fallback for JS-rendered pages
   - SSL `verify=False` retry in `request_handler.py` - Recovers sites with expired SSL certs
   - Expanded URL patterns (10 per resource) - PrestoSports, WordPress, .aspx patterns
   - `recover` CLI command - Retries all schools not in DB
2. **Fixed 5 previously-failing D1 schools** - Arizona St., Cincinnati (Nuxt roster), Arkansas, Jackson St. (URL patterns), Clemson (stats URL)
3. **Full D2/D3 scrape** - Ran 458 remaining schools in ~51 minutes: 203 saved, 8,790 players
4. **Recovery pass** - Attempted 254 failed schools; all confirmed as dead domains or truly unparseable
5. **Final DB stats** - ~586 teams, ~17,274 players across all three divisions

### Session 3 (Feb 14, 2026) - First Full Scrape
1. **Ran full scrape** - `python main.py run --force` across all D1 schools (pre-season)
2. **SSL error fix** - Dallas Baptist's expired SSL cert triggered circuit breaker (30-min cooldowns in a loop). Added `requests.exceptions.SSLError` catch in `request_handler.py` that returns None immediately without retries or circuit breaker increment
3. **Scrape completed in 2 runs** - First run: 38/100 schools before circuit breaker killed it. After SSL fix, second run: 90/100 successful (scheduler skipped already-scraped schools)
4. **Results** - 8,484 players, 2,629 hitting stats, 1,888 pitching stats loaded into production DB
5. **Failed schools (10/100):**
   - Arizona St., Auburn, Cincinnati, Grambling - 0 roster players found
   - Arkansas, Jackson St. - All URL paths returned 404
   - Dallas Baptist - SSL certificate error (skipped)
   - Colorado, Iowa St. - NoneType error when roster empty but stats response exists
   - Georgia Tech, Clemson - Roster works but all stats URLs 404

### Session 2 (Feb 14, 2026) - Scraper Testing & Fixes
1. **Ran first diagnostic** - Tested scraper on Vanderbilt (D1), Tampa (D2), Chapman (D3)
2. **Investigated Vanderbilt stats** - Discovered `/sports/baseball/stats` 301 redirects to homepage; stats are JS-rendered via WMT Games plugin
3. **Added SIDEARM v3 URL paths** - `/stats/2026` and `/stats/2025-26` for modern SIDEARM sites
4. **Homepage redirect detection** - Skip responses that redirect to base URL
5. **Parser improvements** - Column header fallback detection, "Last, First" name normalization, "GP-GS"/"SB-ATT" format handling, `slg%`/`ob%` aliases
6. **Nuxt payload parser** - New parser that extracts batting + pitching stats from SIDEARM v3's devalue-serialized Nuxt payload. Tested on 6 D1 schools, all returning both batting and pitching
7. **Updated diagnostic** - Swapped Vanderbilt for Louisville (working D1 SIDEARM v3 site)

### Session 1 - Web App Features
1. Added authentication requirement and email allowlist for registration
2. Comprehensive stat filters with conditional visibility (hitting/pitching)
3. Year filter, Min AB filter, Min IP filter

## Known Issues / Bugs

- None in the web app
- See "Known Scraper Issues" above for scraper limitations

## Next Steps / Ideas

1. **Install Playwright in GitHub Actions** - Would recover ~14 JS-rendered sites via browser fallback
2. **WMT Games integration** - Handle Vanderbilt/LSU-style sites (headless browser or API)
3. **Portal alerts** - Test and verify email notification system works
4. **Player comparison** - Add ability to compare multiple players side-by-side
5. **Export functionality** - Export filtered results to CSV
6. **Advanced search** - Search by hometown, high school
7. **Watchlist notifications** - Email when favorited player stats update
8. **Mobile optimization** - Review and improve mobile filter panel UX

## Git History (Recent)

```
29b9d25 Update 106 school URLs from conference website discovery
1b61243 Add scraper recovery for failed schools: URL discovery, generic parsers, browser fallback
7de822e Add force-dynamic to debug API route (fix cached GET response)
4ca5126 Remove hourly rate limit and circuit breaker sleep that caused 40+ min stalls
b8d23ab Fix 30-minute pauses: 403 from one school was pausing entire scraper
fa29357 Add JSON-LD roster parser and speed up empty-roster handling
365b09b Dramatically speed up initial scrape for 700+ schools
0cd5416 Fix SSL errors triggering circuit breaker cooldown
794bc8a Add Nuxt payload parser for SIDEARM v3 pitching stats
0d810fc Fix scraper for SIDEARM v3 stats pages (D1 support)
a136d28 Add CLAUDE.md with project status documentation
```

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Generate Prisma client
npx prisma generate

# Run migrations
npx prisma migrate deploy
```

## Environment Variables

Required in Vercel / `.env`:

```
DATABASE_URL=postgresql://...
NEXTAUTH_SECRET=...
NEXTAUTH_URL=https://college-baseball-tracker.vercel.app
ALLOWED_EMAILS=email1@example.com,email2@example.com
RESEND_API_KEY=... (for email notifications)
```
