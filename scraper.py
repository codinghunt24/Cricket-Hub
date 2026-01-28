import requests
from bs4 import BeautifulSoup
import re
import time
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.cricbuzz.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

CATEGORIES = {}
SERIES_CATEGORIES = {}


def fetch_page(url, retries=3):
    """Fetch a page with retries"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            if attempt < retries - 1:
                time.sleep(1)
    return None


def scrape_live_scores():
    """Scrape all matches from Cricbuzz live-scores page."""
    return {'success': False, 'matches': [], 'message': 'Scraping method not implemented yet'}


def scrape_series_from_live_page():
    """
    Scrape unique series from Cricbuzz live-scores page.
    Each series includes its match IDs found on the page.
    Returns list of series with series_id, series_name, series_url, and match_ids
    """
    url = "https://www.cricbuzz.com/cricket-match/live-scores"
    html = fetch_page(url)
    
    if not html:
        return {'success': False, 'series': [], 'message': 'Failed to fetch page'}
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    series_list = []
    seen_series_ids = set()
    
    # Find all parent divs with class 'mb-3' which contain series + matches
    parent_divs = soup.find_all('div', class_='mb-3')
    
    for parent in parent_divs:
        # Find series link in this parent
        series_link = parent.find('a', href=re.compile(r'/cricket-series/(\d+)/'))
        if not series_link:
            continue
        
        href = series_link.get('href', '')
        match = re.search(r'/cricket-series/(\d+)/([^/\?"]+)', href)
        if not match:
            continue
        
        series_id = match.group(1)
        series_slug = match.group(2)
        
        # Skip duplicates
        if series_id in seen_series_ids:
            continue
        seen_series_ids.add(series_id)
        
        series_name = series_link.get_text(strip=True)
        
        # Skip if no name or just navigation links
        if not series_name or series_name in ['Matches', 'Points Table', 'Venues']:
            continue
        
        # Find all match links under this series parent
        match_links = parent.find_all('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
        match_ids = []
        seen_match_ids = set()
        
        for m_link in match_links:
            m_href = m_link.get('href', '')
            m_match = re.search(r'/live-cricket-scores/(\d+)/', m_href)
            if m_match:
                mid = m_match.group(1)
                if mid not in seen_match_ids:
                    seen_match_ids.add(mid)
                    match_ids.append(mid)
        
        series_list.append({
            'series_id': series_id,
            'series_name': series_name,
            'series_slug': series_slug,
            'series_url': BASE_URL + href,
            'match_ids': match_ids,
            'match_count': len(match_ids)
        })
    
    total_matches = sum(s['match_count'] for s in series_list)
    logger.info(f"Found {len(series_list)} series with {total_matches} total matches")
    return {'success': True, 'series': series_list, 'message': f'Found {len(series_list)} series with {total_matches} matches'}


def scrape_scorecard(match_id):
    """Scrape scorecard for a match."""
    return None


def scrape_category(category_slug):
    """Scrape matches from a category."""
    return {'success': False, 'matches': [], 'message': 'Not implemented'}


def scrape_players_from_team(team_url):
    """Scrape players from a team page."""
    return []


def scrape_series_from_category(category_url):
    """Scrape series from a category."""
    return []


def scrape_matches_from_series(series_url):
    """Scrape matches from a series."""
    return []


def scrape_player_profile(player_url):
    """Scrape player profile."""
    return None


def update_match_with_accurate_data(match_id):
    """Update match with accurate data."""
    return None


def update_match_scores(match_id):
    """Update match scores."""
    return None
