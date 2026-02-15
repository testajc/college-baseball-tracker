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
| `main.py` | Entry point - `run`, `diagnostic`, `status` commands |
| `config.py` | Rate limiting, season start date (`2026-02-21`), error thresholds |
| `scheduler.py` | Smart scheduling - tracks which schools need scraping |
| `request_handler.py` | HTTP client with rate limiting, retries, circuit breaker, UA rotation |
| `database.py` | PostgreSQL writer - saves scraped data to Prisma-compatible tables |
| `parsers/sidearm_parser.py` | HTML + Nuxt payload parser for SIDEARM athletics sites |
| `build_schools_db.py` | Builds `schools_database.csv` (971 schools across D1/D2/D3) |

### How Stats Parsing Works

Two parsing strategies, tried in order:

1. **Nuxt payload parser** (SIDEARM v3, most D1 schools) - Extracts the devalue-serialized JSON payload embedded in `<script>` tags. Gets batting AND pitching stats in one pass. Path: `statsSeason → cumulativeStats → overallIndividualStats → individualStats`
2. **HTML table parser** (older SIDEARM, D3/some D2) - Finds stats tables by id/class, heading text, or column header detection. Parses `<table>` elements directly.

### URL Patterns

The scraper tries multiple URL paths for rosters and stats (in order):
- `/sports/baseball/roster/2026`, `/roster/2025-26`, `/roster`
- `/sports/baseball/stats/2026`, `/stats/2025-26`, `/stats`
- `/sports/bsb/2025-26/roster|stats`, `/sports/bsb/roster|stats`
- `/sports/mens-baseball/roster|stats`

Homepage redirects (301 → base URL) are detected and skipped.

### Diagnostic Results (Feb 14, 2026)

Tested across D1 schools after opening weekend:

| School | Batting | Pitching | Method |
|--------|---------|----------|--------|
| Louisville | 10 | 4 | nuxt |
| Texas | 10 | 2 | nuxt |
| Alabama | 11 | 4 | nuxt |
| Florida | 11 | 6 | nuxt |
| Oregon State | 10 | 4 | nuxt |
| Wake Forest | 10 | 5 | nuxt |
| Chapman (D3) | 8 | 5 | html |

### Running the Scraper

```bash
cd scraper
pip install -r requirements.txt

# Test 3 schools (Louisville D1, Tampa D2, Chapman D3)
python main.py diagnostic

# Full scrape (requires DATABASE_URL, respects season start date)
python main.py run
python main.py run --force     # ignore season start date
python main.py run --dry-run   # show what would be scraped

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

- **Vanderbilt / WMT Games sites** - Some schools (Vanderbilt, LSU) use a WordPress + WMT Games plugin where stats are loaded via JS iframes from `wmt.games`. These don't have SIDEARM v3 Nuxt payloads. Roster scraping works, but stats return 0. Would need either a headless browser or WMT API integration.
- **Tampa (D2)** - All stats URL paths 404. Uses non-standard SIDEARM paths.
- **Pitching on older SIDEARM** - HTML table parser gets pitching fine on D3 sites. D1 SIDEARM v3 only server-renders batting HTML, but the Nuxt parser handles pitching.
- **Season start date** - Config hardcodes `2026-02-21` but some D1 teams play earlier (mid-Feb). Use `--force` to override.
- **NoneType error on empty rosters** - Colorado, Iowa St. crash with `'NoneType' object has no attribute 'get'` when roster returns 0 players but stats response exists. Non-fatal (caught by try/except), schools just skipped.
- **Schools with 0 roster players** - Arizona St., Auburn, Cincinnati, Grambling return roster pages but parser finds 0 players. May need parser updates for their specific HTML layouts.

## Database Stats (as of Feb 14, 2026)

| Table | Count |
|-------|-------|
| Teams | 797 |
| Players | 8,484 |
| Hitting Stats | 2,629 |
| Pitching Stats | 1,888 |

| Division | Teams | Players |
|----------|-------|---------|
| D1 | 424 | 7,014 |
| D2 | 99 | 858 |
| D3 | 274 | 612 |

## Recent Changes

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

1. **Fix failed schools** - Investigate the 10 D1 schools that failed (0 roster, 404s, NoneType bug)
2. **Run D2/D3 scrape** - Full scrape so far only covered D1; need to run D2 and D3
3. **Fix Tampa (D2)** - Find correct stats URL pattern for their site
4. **WMT Games integration** - Handle Vanderbilt/LSU-style sites (headless browser or API)
5. **Portal alerts** - Test and verify email notification system works
6. **Player comparison** - Add ability to compare multiple players side-by-side
7. **Export functionality** - Export filtered results to CSV
8. **Advanced search** - Search by hometown, high school
9. **Watchlist notifications** - Email when favorited player stats update
10. **Mobile optimization** - Review and improve mobile filter panel UX

## Git History (Recent)

```
0cd5416 Fix SSL errors triggering circuit breaker cooldown
794bc8a Add Nuxt payload parser for SIDEARM v3 pitching stats
0d810fc Fix scraper for SIDEARM v3 stats pages (D1 support)
a136d28 Add CLAUDE.md with project status documentation
2a9c82b Add Min AB filter for hitters
7ee4d51 Add Min IP filter for pitchers
5087723 Add comprehensive stat filters with conditional visibility
5ae543c Allow /register page through auth middleware
4ed40cb Add authentication requirement and email allowlist for registration
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
