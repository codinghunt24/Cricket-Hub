# CricLive - Cricbuzz-inspired Cricket Website

## Overview
A Cricbuzz-inspired cricket website layout built with Python Flask. Features a responsive frontend with sticky navbar and dropdown submenus, plus an admin panel with sidebar navigation.

## Current State
- **Status**: Layout complete, ready for data integration
- **Last Updated**: January 25, 2026

## Project Structure
```
├── app.py                    # Main Flask application with routes
├── templates/
│   ├── base.html            # Base template with navbar
│   ├── index.html           # Homepage
│   └── admin/
│       ├── base.html        # Admin base template with sidebar
│       ├── dashboard.html   # Admin dashboard
│       ├── matches.html     # Matches management
│       ├── teams.html       # Teams management
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
### Frontend
- Full-width sticky navbar with dropdown submenus
- Centered container layout (max-width: 1200px)
- Menu items: Live Score, Teams, Series, News
- Responsive design for mobile, tablet, desktop
- Cricbuzz-inspired green color scheme

### Admin Panel
- Sidebar navigation
- Dashboard with overview cards
- Pages: Matches, Teams, Series, News, Settings
- Responsive sidebar (collapses on mobile)
- Back to site link

## Routes
### Frontend Routes
- `/` - Homepage
- `/live-scores` - Live scores page
- `/teams` - Teams page
- `/series` - Series page
- `/news` - News page

### Admin Routes
- `/admin` - Admin dashboard
- `/admin/matches` - Matches management
- `/admin/teams` - Teams management
- `/admin/series` - Series management
- `/admin/news` - News management
- `/admin/settings` - Settings

## Tech Stack
- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Templating**: Jinja2
- **Styling**: Custom CSS with CSS Grid and Flexbox

## Next Steps
- Add database integration for storing data
- Implement user authentication
- Add live cricket score API integration
- Create detailed match pages
- Add search functionality
