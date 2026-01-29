# Cricbuzz Live Score - Cricket Website

## Overview
Cricbuzz Live Score is a professional cricket website built with Python Flask, designed to provide live scores, team and player statistics, and comprehensive cricket news. It leverages web scraping to gather data from Cricbuzz, offering a rich user experience with a responsive frontend and a robust admin panel for content and SEO management. The project aims to deliver a high-quality platform for cricket enthusiasts, featuring detailed player profiles, match scorecards, and a blog/CMS system, all optimized for search engines.

## User Preferences
I prefer detailed explanations.
I want an iterative development process.
Ask before making major changes to the codebase.
Ensure all new features are SEO-friendly by default.
Focus on replicating the core functionalities and design aesthetics of professional sports websites like Cricbuzz.

## System Architecture

### UI/UX Decisions
The frontend features a full-width sticky navbar with dropdown submenus, a centered container layout (max-width: 1200px), and a Cricbuzz-inspired green color scheme. The design is fully responsive, adapting to mobile, tablet, and desktop views. The admin panel includes a sidebar navigation, collapsing on mobile, and a consistent theme.

### Technical Implementations
The core application is built with Python Flask, utilizing Flask-SQLAlchemy for database interactions with PostgreSQL. Web scraping is handled by Requests and BeautifulSoup4. Background tasks and scheduled scraping operations are managed by APScheduler. The frontend is developed using HTML5, CSS3, and vanilla JavaScript with Jinja2 for templating.

### Feature Specifications
- **Web Scraping**: Scrapes teams, detailed player profiles (personal info, batting/bowling career stats), series, and match data from Cricbuzz. Includes manual and category-wise auto-scrape timers with real-time progress tracking. All scraping functions incorporate ID verification to prevent data contamination.
- **Frontend**: Displays live scores, team categories, team lists with flags, detailed team pages with player cards, comprehensive player profiles, series lists, and match scorecards. Includes a blog system with recent news.
- **Admin Panel**: Provides comprehensive management for:
    - **SEO & Sitemap**: View sitemaps, copy URLs for Google Search Console, manage `robots.txt`.
    - **Google Analytics & AdSense**: Configuration for GA4 and AdSense, including ad slot management.
    - **Theme Customization**: Site identity, 11 customizable color options with reset functionality.
    - **301 Redirects**: Add/edit/delete 301/302 redirects, toggle status, track hits, bulk import, URL normalization.
    - **Content Management**: Full blog/CMS system with categories, posts, rich text editor (Quill.js), image uploads, and static page management (About Us, Privacy Policy, etc.).
    - **Scraping Controls**: Initiate manual scrapes, configure auto-scrape settings for teams, players, series, and matches.

### System Design Choices
- **SEO-First Approach**: Comprehensive SEO implementation including meta tags, high-volume keywords, Schema.org structured data (WebSite, SportsEvent, Person, CollectionPage, WebPage), Open Graph, and Twitter Cards. Dynamic sitemap generation, canonical URLs, cache-control headers, and SEO-friendly URLs are standard. Unique "About" sections on player pages dynamically generate content to avoid thin content issues.
- **Database Models**: Structured models for `TeamCategory`, `Team`, `Player` (with extensive career stats), `ScrapeLog`, `ScrapeSetting`, `ProfileScrapeSetting`, `SeriesCategory`, `Series`, `SeriesScrapeSetting`, `Match`, `MatchScrapeSetting`, `PostCategory`, `Post`, `Page`, and `Redirect`.
- **API Endpoints**: Dedicated APIs for triggering scraping processes (category, team players, player profiles, series, matches) and managing auto-scrape settings, alongside data retrieval APIs for teams and players.
- **Project Structure**: Organized into `app.py`, `models.py`, `scraper.py`, `scheduler.py`, `templates/`, and `static/` directories for clear separation of concerns.

## External Dependencies
- **PostgreSQL**: Primary database for storing all website data.
- **Requests**: Python library for making HTTP requests for web scraping.
- **BeautifulSoup4**: Python library for parsing HTML and XML documents during scraping.
- **APScheduler**: Python library for scheduling background jobs.
- **Quill.js**: Rich text editor used in the admin panel for content creation.