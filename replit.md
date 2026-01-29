# Cricbuzz Live Score - Cricket Website

## Overview
A professional cricket website (Cricbuzz Live Score) built with Python Flask featuring web scraping for team and player data from Cricbuzz. Includes a responsive frontend with sticky navbar and dropdown submenus, plus an admin panel with sidebar navigation and scraping controls.

**Website**: https://cricbuzz-live-score.com

## Current State
- **Status**: Complete SEO optimization with Schema.org, Open Graph, and high-volume keywords
- **Last Updated**: January 29, 2026
- **Note**: All scraping functions now include mandatory ID verification to prevent data contamination

## Recent SEO Enhancements (January 29, 2026)
- **Team Detail Page**: Added meta description, keywords, Open Graph tags, SportsTeam Schema.org markup
- **Teams List Page**: Added meta description, keywords, CollectionPage Schema.org markup
- **Teams Main Page**: Added complete SEO with meta tags and CollectionPage schema
- **Series List Page**: Enhanced with meta description, keywords and CollectionPage schema
- **Player Detail Page**: Added unique "About" section with dynamic content generation to avoid thin content issues
  - Auto-generates unique paragraphs based on player stats (batting average, centuries, wickets, etc.)
  - Each player page now has 200+ words of unique descriptive content
  - Prevents Google thin content penalty for similar player profiles

## Sitemap Index Structure (January 29, 2026)
- **Sitemap Index**: /sitemap.xml links to all category sitemaps
- **Category Sitemaps**:
  - /sitemap-main.xml: Homepage, live scores, teams page, series page, post categories
  - /sitemap-teams.xml: All team pages
  - /sitemap-players.xml: All player profile pages
  - /sitemap-series.xml: All series pages
  - /sitemap-posts.xml: All published blog posts
  - /sitemap-pages.xml: All static pages (About, Privacy, etc.)
- **Benefits**: Better crawling, faster indexing, avoids 50k URL limit per file

## 301 Redirect Management (January 29, 2026)
- **Admin Panel Feature**: Full redirect management at /admin/redirects
- **Features**:
  - Add/Edit/Delete 301 and 302 redirects
  - Toggle redirects on/off
  - Hit count tracking for each redirect
  - Bulk import via CSV (old_url,new_url format)
  - URL normalization (handles trailing slashes)
- **Database Model**: Redirect table with old_url, new_url, redirect_type, is_active, hit_count
- **Middleware**: @app.before_request checks all incoming requests against redirect rules
- **Use Case**: Preserve SEO rankings when migrating URLs (e.g., /team/123 → /team/india-1871)

## SEO Implementation (Cricbuzz-Inspired)
Based on Cricbuzz's SEO strategy (335M monthly traffic, 432K keywords):

### Meta Tags & Keywords
- High-volume keywords: live cricket score, today match live score, ball by ball commentary
- Match-specific keywords: ind vs aus, ind vs eng, ipl 2026 live score, t20 world cup
- Dream11 keywords: dream11 prediction, pitch report, playing 11
- All pages have unique meta titles, descriptions, and keywords

### Schema.org Structured Data (JSON-LD)
- WebSite schema on base template
- SportsEvent schema on match pages
- Person schema on player profiles
- CollectionPage schema on listing pages

### Open Graph & Twitter Cards
- og:title, og:description, og:image on all pages
- Twitter card support for social sharing
- Dynamic content based on page type

### Technical SEO
- robots.txt at /robots.txt
- Dynamic sitemap.xml at /sitemap.xml (includes all pages, posts, teams, players, series with SEO-friendly slugs)
- Canonical URLs on all pages
- Cache-control headers
- SEO-friendly URLs: /team/india-1871, /player/virat-kohli-123, /series/ipl-2026-5

### Page-Specific SEO
- Homepage: Live cricket score, today match keywords
- Match pages: Team vs Team live score, scorecard, ball by ball
- Player pages: Player name stats, profile, batting, bowling
- Series pages: Series name schedule, results, points table
- Live scores: Today match live, IPL live, all matches

## Recent Improvements
- **Static Pages for AdSense**: Complete static pages system for Google AdSense approval
  - Page model with title, slug, rich text content, SEO fields
  - 5 default pages: About Us, Contact Us, Privacy Policy, Terms & Conditions, Disclaimer
  - Admin pages management with Quill.js editor and quick templates
  - Footer integration showing pages with ordering control
  - Frontend route: /page/<slug> with Schema.org WebPage markup
  - Admin route: /admin/pages for managing all static pages
- **Team Flags on Homepage**: Live score cards now display team flags
  - Flags extracted from Cricbuzz static images (static.cricbuzz.com)
  - Team names extracted from img alt attributes
  - Flags stored in Match model (team1_flag, team2_flag columns)
  - Admin panel "Save All" button to bulk save matches with flags
  - Homepage shows circular flag images with team names and scores
- **Complete Scorecard Extraction**: Full scorecard data from Cricbuzz HTML structure
  - Batting: Player name, dismissal, runs, balls, 4s, 6s, strike rate
  - Bowling: Bowler name, overs, maidens, runs, wickets, economy
  - Fall of Wickets: Player, score, over
  - Team name extraction with abbreviation removal (AUSU19Australia U19 → Australia U19)
  - Admin UI with complete innings display
- **Auto Post with Advanced SEO**: Complete auto-posting system for live match coverage
  - Advanced SEO settings (Meta Title, Meta Description, Focus Keyword)
  - Multiple keywords support with tag-based UI
  - Suggested keywords for cricket SEO (live score, dream11, pitch report, etc.)
  - Live/Upcoming match selection with real-time scorecard embedding
  - Server-side scorecard rendering for SEO optimization
  - Category selection with "Today Live Match" default
  - Open Graph settings for social media sharing
  - Character counters with SEO meters
- **Blog/CMS System**: Complete content management with categories and posts
  - PostCategory model with navbar visibility and ordering
  - Post model with full SEO fields (meta_title, meta_description, meta_keywords, Open Graph)
  - Rich text editor (Quill.js) for content creation
  - Image upload functionality for thumbnails
  - Frontend post page with JSON-LD schema markup
  - Dynamic navbar showing categories from database
  - Recent News section on homepage with published posts
- **Complete ID Extraction**: All entities now have primary IDs for verification
  - match_id, series_id, team1_id, team2_id, venue_id in match data
  - player_id in batting/bowling stats
- Professional-level scraping accuracy with multiple URL sources (scorecard, live-scores, commentary)
- Full team name normalization (IND → India, NZ → New Zealand)
- Accurate venue extraction from multiple page elements
- Complete scorecard data with batting/bowling stats
- Match format extraction (1st ODI, 2nd Test, etc.)
- Result extraction with fallback patterns
- ID-verified scraping prevents data contamination from "Related Matches"

## Project Structure
```
├── app.py                    # Main Flask application with routes & API
├── models.py                 # Database models (Teams, Players, etc.)
├── scraper.py                # Cricbuzz web scraper module
├── scheduler.py              # APScheduler for daily auto-scraping
├── templates/
│   ├── base.html            # Base template with navbar
│   ├── index.html           # Homepage
│   ├── teams.html           # Teams categories page
│   ├── teams_list.html      # Teams list by category
│   ├── team_detail.html     # Team detail with players
│   ├── player_detail.html   # Player profile with stats
│   └── admin/
│       ├── base.html        # Admin base template with sidebar
│       ├── dashboard.html   # Admin dashboard
│       ├── matches.html     # Matches management
│       ├── teams.html       # Teams management with scrape controls
│       ├── series.html      # Series management
│       ├── news.html        # News management
│       └── settings.html    # Settings page
├── static/
│   ├── css/
│   │   ├── style.css        # Main frontend styles
│   │   └── admin.css        # Admin panel styles
│   └── js/
│       ├── main.js          # Frontend JavaScript
│       └── admin.js         # Admin panel JavaScript
└── replit.md                # Project documentation
```

## Features

### Web Scraping
- Scrape teams from 4 Cricbuzz categories:
  - International
  - Domestic
  - League
  - Women
- Scrape player data (name, photo, role) for each team
- **NEW: Scrape detailed player profiles with:**
  - Personal Info: Born, Birth Place, Nickname, Role, Batting Style, Bowling Style
  - Batting Career: Matches, Innings, Runs, Balls, Highest Score, Average, Strike Rate, Not Outs, 4s, 6s, Ducks, 50s, 100s, 200s
  - Bowling Career: Matches, Innings, Balls, Runs, Maidens, Wickets, Average, Economy, Strike Rate, Best Bowling (Inn/Match), 4/5/10 Wickets
- Manual scraping from admin panel
- Category-wise auto-scrape timers for players and profiles
- Real-time progress tracking with percentage display

### Frontend
- Full-width sticky navbar with dropdown submenus
- Centered container layout (max-width: 1200px)
- Menu items: Live Score, Teams, Series, News
- Teams page showing 4 categories with icons
- Team list page with flags
- Team detail page with clickable player cards
- **NEW: Player profile page with detailed stats cards**
- Responsive design for mobile, tablet, desktop
- Cricbuzz-inspired green color scheme

### Admin Panel
- Sidebar navigation
- Dashboard with overview stats
- Teams Management with:
  - Scrape All Categories button
  - Individual category scrape buttons
  - Scrape Players for each team
  - Auto-scrape daily toggle with time picker
  - Category-wise player scraping with auto timers
  - **NEW: Player Profiles section with category-wise scraping**
  - Real-time progress bars during scraping
  - Scrape logs table
- Responsive sidebar (collapses on mobile)

## Database Models
- **TeamCategory**: International, Domestic, League, Women
- **Team**: name, team_id, flag_url, team_url, category_id
- **Player**: name, player_id, photo_url, player_url, role, team_id
  - Personal: born, birth_place, nickname, batting_style, bowling_style
  - Batting: bat_matches, bat_innings, bat_runs, bat_balls, bat_highest, bat_average, bat_strike_rate, bat_not_outs, bat_fours, bat_sixes, bat_ducks, bat_fifties, bat_hundreds, bat_two_hundreds
  - Bowling: bowl_matches, bowl_innings, bowl_balls, bowl_runs, bowl_maidens, bowl_wickets, bowl_average, bowl_economy, bowl_strike_rate, bowl_best_innings, bowl_best_match, bowl_four_wickets, bowl_five_wickets, bowl_ten_wickets
  - Career Timeline: career_timeline (JSON with format keys containing debut/last_match)
  - profile_scraped, profile_scraped_at
- **ScrapeLog**: category, status, message, timestamps
- **ScrapeSetting**: auto_scrape_enabled, scrape_time, category-wise settings
- **ProfileScrapeSetting**: category_slug, auto_scrape_enabled, scrape_time
- **SeriesCategory**: All, International, Domestic, T20 Leagues, Women
- **Series**: series_id, name, series_url, start_date, end_date, date_range, category_id
- **SeriesScrapeSetting**: category_slug, auto_scrape_enabled, scrape_time
- **Match**: match_id, match_format, venue, match_date, team1_name, team1_score, team2_name, team2_score, result, match_url, series_id
- **MatchScrapeSetting**: auto_scrape_enabled, scrape_time, last_scrape

## API Endpoints

### Scraping APIs
- `POST /api/scrape/category/<slug>` - Scrape teams from category
- `POST /api/scrape/team/<id>/players` - Scrape players from team
- `POST /api/scrape/category/<slug>/players` - Scrape all players in category
- `POST /api/scrape/profiles/<slug>` - Scrape player profiles in category
- `GET /api/scrape/profiles/<slug>/progress` - Get profile scraping progress
- `POST /api/scrape/all` - Scrape all categories
- `POST /api/settings/auto-scrape` - Toggle auto-scrape
- `POST /api/settings/profile-auto-scrape` - Toggle profile auto-scrape
- `GET /api/settings/profile-scrape` - Get profile scrape settings
- `POST /api/scrape/series/<slug>` - Scrape series from category
- `POST /api/settings/series-auto-scrape` - Toggle series auto-scrape
- `GET /api/settings/series-scrape` - Get series scrape settings
- `POST /api/scrape/matches/<series_id>` - Scrape matches from series
- `POST /api/settings/match-auto-scrape` - Toggle match auto-scrape
- `GET /api/settings/match-scrape` - Get match scrape settings

### Data APIs
- `GET /api/teams/<category_slug>` - Get teams by category
- `GET /api/team/<id>/players` - Get players by team

## Routes

### Frontend Routes
- `/` - Homepage
- `/teams` - Teams categories
- `/teams/<category>` - Teams list by category
- `/team/<id>` - Team detail with players
- `/player/<id>` - Player profile with stats
- `/series/<id>` - Series detail with matches list
- `/match/<id>` - Match scorecard with full batting/bowling stats (live scraped from Cricbuzz)
- `/live-scores`, `/news` - Other pages

### Admin Routes
- `/admin` - Dashboard
- `/admin/teams` - Teams management with scraping
- `/admin/matches`, `/admin/series`, `/admin/news`, `/admin/settings`

## Tech Stack
- **Backend**: Python Flask, Flask-SQLAlchemy
- **Database**: PostgreSQL
- **Scraping**: Requests, BeautifulSoup4
- **Scheduling**: APScheduler
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Templating**: Jinja2

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - Flask session secret
- `FLASK_DEBUG` - Debug mode toggle

## Next Steps
- Add live cricket score integration
- Implement user authentication
- Add search functionality
- Create detailed match pages
- Add news scraping feature
- Wire profile auto-scrape to scheduler for automatic execution
