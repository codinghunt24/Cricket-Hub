# CricLive - Cricbuzz-inspired Cricket Website

## Overview
A Cricbuzz-inspired cricket website built with Python Flask featuring web scraping for team and player data from Cricbuzz. Includes a responsive frontend with sticky navbar and dropdown submenus, plus an admin panel with sidebar navigation and scraping controls.

## Current State
- **Status**: Teams scraping feature complete
- **Last Updated**: January 25, 2026

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
- Manual scraping from admin panel
- Automatic daily scraping with configurable time

### Frontend
- Full-width sticky navbar with dropdown submenus
- Centered container layout (max-width: 1200px)
- Menu items: Live Score, Teams, Series, News
- Teams page showing 4 categories with icons
- Team list page with flags
- Team detail page with player photos
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
  - Scrape logs table
- Responsive sidebar (collapses on mobile)

## Database Models
- **TeamCategory**: International, Domestic, League, Women
- **Team**: name, team_id, flag_url, team_url, category_id
- **Player**: name, player_id, photo_url, player_url, role, team_id
- **ScrapeLog**: category, status, message, timestamps
- **ScrapeSetting**: auto_scrape_enabled, scrape_time, last_scrape

## API Endpoints

### Scraping APIs
- `POST /api/scrape/category/<slug>` - Scrape teams from category
- `POST /api/scrape/team/<id>/players` - Scrape players from team
- `POST /api/scrape/all` - Scrape all categories
- `POST /api/settings/auto-scrape` - Toggle auto-scrape

### Data APIs
- `GET /api/teams/<category_slug>` - Get teams by category
- `GET /api/team/<id>/players` - Get players by team

## Routes

### Frontend Routes
- `/` - Homepage
- `/teams` - Teams categories
- `/teams/<category>` - Teams list by category
- `/team/<id>` - Team detail with players
- `/live-scores`, `/series`, `/news` - Other pages

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
