# CricLive - Cricbuzz-inspired Cricket Website

## Overview
A Cricbuzz-inspired cricket website built with Python Flask featuring web scraping for team and player data from Cricbuzz. Includes a responsive frontend with sticky navbar and dropdown submenus, plus an admin panel with sidebar navigation and scraping controls.

## Current State
- **Status**: Professional-grade match scraping with accurate data extraction
- **Last Updated**: January 26, 2026
- **Note**: Enhanced scraping with multiple fallback methods for robust data extraction

## Recent Improvements
- Professional-level scraping accuracy with multiple URL sources (scorecard, live-scores, commentary)
- Full team name normalization (IND → India, NZ → New Zealand)
- Accurate venue extraction from multiple page elements
- Complete scorecard data with batting/bowling stats
- Match format extraction (1st ODI, 2nd Test, etc.)
- Result extraction with fallback patterns

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
