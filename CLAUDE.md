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

## Recent Changes (Latest Session)

1. **Added authentication requirement** - All routes now require login except `/login`, `/register`, and `/api/auth/*`
2. **Email allowlist for registration** - Only emails in `ALLOWED_EMAILS` can register
3. **Comprehensive stat filters** - Added all hitting/pitching stat filters
4. **Conditional filter visibility** - Hitting filters only show when hitting selected, pitching filters only show when pitching selected
5. **Year filter** - Added class year filter
6. **Min AB filter** - For filtering hitters by at-bats
7. **Min IP filter** - For filtering pitchers by innings pitched

## Known Issues / Bugs

- None currently identified

## Next Steps / Ideas

1. **Data population** - Need to scrape/import actual player and team data
2. **Portal alerts** - Test and verify email notification system works
3. **Player comparison** - Add ability to compare multiple players side-by-side
4. **Export functionality** - Export filtered results to CSV
5. **Advanced search** - Search by hometown, high school
6. **Watchlist notifications** - Email when favorited player stats update
7. **Mobile optimization** - Review and improve mobile filter panel UX
8. **Dark mode** - Add theme toggle

## Git History (Recent)

```
2a9c82b Add Min AB filter for hitters
7ee4d51 Add Min IP filter for pitchers
5087723 Add comprehensive stat filters with conditional visibility
5ae543c Allow /register page through auth middleware
4ed40cb Add authentication requirement and email allowlist for registration
445f8a0 Track Prisma migrations in git for production deploys
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
