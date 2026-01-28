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
    
    # Find all series links first, then find their correct parent containers
    series_links = soup.find_all('a', href=re.compile(r'/cricket-series/(\d+)/'))
    
    for s_link in series_links:
        href = s_link.get('href', '')
        match = re.search(r'/cricket-series/(\d+)/([^/\?"]+)', href)
        if not match:
            continue
        
        series_id = match.group(1)
        series_slug = match.group(2)
        
        # Skip duplicates
        if series_id in seen_series_ids:
            continue
        
        series_name = s_link.get_text(strip=True)
        
        # Skip if no name or just navigation links
        if not series_name or series_name in ['Matches', 'Points Table', 'Venues']:
            continue
        
        # Find the correct parent container that has exactly this series
        parent = s_link.parent
        correct_parent = None
        
        for _ in range(5):
            if parent:
                # Check if this parent has exactly one instance of this series link
                series_in_parent = parent.find_all('a', href=re.compile(r'/cricket-series/' + series_id + '/'))
                match_links = parent.find_all('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
                
                if len(series_in_parent) == 1 and len(match_links) >= 1:
                    correct_parent = parent
                    break
                parent = parent.parent
        
        if not correct_parent:
            continue
        
        seen_series_ids.add(series_id)
        
        # Find all match links under this correct parent
        match_links = correct_parent.find_all('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
        matches = []
        seen_match_ids = set()
        
        for m_link in match_links:
            m_href = m_link.get('href', '')
            m_match = re.search(r'/live-cricket-scores/(\d+)/', m_href)
            if m_match:
                mid = m_match.group(1)
                if mid not in seen_match_ids:
                    seen_match_ids.add(mid)
                    match_title = m_link.get_text(strip=True)
                    matches.append({
                        'match_id': mid,
                        'match_title': match_title if match_title else '-'
                    })
        
        series_list.append({
            'series_id': series_id,
            'series_name': series_name,
            'series_slug': series_slug,
            'series_url': BASE_URL + href,
            'matches': matches,
            'match_ids': [m['match_id'] for m in matches],
            'match_count': len(matches)
        })
    
    total_matches = sum(s['match_count'] for s in series_list)
    logger.info(f"Found {len(series_list)} series with {total_matches} total matches")
    return {'success': True, 'series': series_list, 'count': len(series_list), 'message': f'Found {len(series_list)} series with {total_matches} matches'}


def scrape_scorecard(match_id):
    """
    Scrape scorecard/match info for a match.
    Returns basic match info available in HTML.
    """
    url = f"{BASE_URL}/live-cricket-scorecard/{match_id}"
    html = fetch_page(url)
    
    if not html:
        return {'success': False, 'match_id': match_id, 'message': 'Failed to fetch page'}
    
    from bs4 import BeautifulSoup
    import json
    
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'match_id': match_id,
        'match_title': None,
        'match_status': None,
        'team1': None,
        'team2': None,
        'team1_score': None,
        'team2_score': None,
        'venue': None,
        'match_format': None,
        'series_name': None,
        'result': None
    }
    
    # Get title from page
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        # Extract match title from "Cricket scorecard | India vs New Zealand, 4th T20I..."
        if '|' in title_text:
            result['match_title'] = title_text.split('|')[1].strip().split(' - ')[0].strip()
        else:
            result['match_title'] = title_text
    
    # Try to get SportsEvent JSON-LD data
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') == 'SportsEvent':
                if data.get('name'):
                    result['match_title'] = data['name'].split(' - ')[0].strip()
                if data.get('location'):
                    loc = data['location']
                    if isinstance(loc, dict):
                        result['venue'] = loc.get('name')
                    elif isinstance(loc, str):
                        result['venue'] = loc
                break
        except:
            continue
    
    # Parse team names from title
    if result['match_title']:
        vs_match = re.search(r'(.+?)\s+vs\s+(.+?),', result['match_title'])
        if vs_match:
            result['team1'] = vs_match.group(1).strip()
            result['team2'] = vs_match.group(2).strip()
        
        # Extract format (T20I, ODI, Test, etc.)
        format_match = re.search(r'\d+(?:st|nd|rd|th)?\s+(T20I?|ODI|Test|T20)', result['match_title'])
        if format_match:
            result['match_format'] = format_match.group(1)
    
    # Get series name from breadcrumb/link
    series_link = soup.find('a', href=re.compile(r'/cricket-series/\d+/'))
    if series_link:
        result['series_name'] = series_link.get_text(strip=True)
    
    # Try to get match status and scores from live-cricket-scores page
    live_url = f"{BASE_URL}/live-cricket-scores/{match_id}"
    live_html = fetch_page(live_url)
    if live_html:
        live_soup = BeautifulSoup(live_html, 'html.parser')
        page_text = live_soup.get_text()
        
        # Extract scores - look for patterns like "NZ14-0(1)" or "IND180/5(18.2)"
        # First look for team abbreviation + score patterns
        score_patterns = [
            r'([A-Z]{2,5})(\d{1,3})-(\d{1,2})\((\d+(?:\.\d)?)\)',  # NZ14-0(1)
            r'([A-Z]{2,5})(\d{1,3})/(\d{1,2})\((\d+(?:\.\d)?)\)',  # IND180/5(18.2)
            r'([A-Z]{2,5})\s*(\d{1,3})-(\d{1,2})',  # NZ 14-0
            r'([A-Z]{2,5})\s*(\d{1,3})/(\d{1,2})',  # IND 180/5
        ]
        
        scores_found = []
        for pattern in score_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                team = match[0]
                if len(match) >= 4:
                    score = f"{match[1]}/{match[2]} ({match[3]})"
                else:
                    score = f"{match[1]}/{match[2]}"
                scores_found.append({'team': team, 'score': score})
            if scores_found:
                break
        
        # Assign scores to teams
        team1_abbr = result['team1'][:3].upper() if result['team1'] else None
        team2_abbr = result['team2'][:3].upper() if result['team2'] else None
        
        for sf in scores_found[:2]:
            team_abbr = sf['team']
            if team1_abbr and team_abbr in ['IND', 'INDIA', team1_abbr]:
                if not result['team1_score']:
                    result['team1_score'] = sf['score']
            elif team2_abbr and team_abbr in ['NZ', 'PAK', 'AUS', 'ENG', 'SA', 'WI', 'SL', 'BAN', 'AFG', 'ZIM', team2_abbr]:
                if not result['team2_score']:
                    result['team2_score'] = sf['score']
            elif not result['team1_score']:
                result['team1_score'] = sf['score']
            elif not result['team2_score']:
                result['team2_score'] = sf['score']
        
        # Check for common status patterns
        status_patterns = [
            (r'(\w+)\s+won\s+by\s+\d+\s+(runs?|wickets?)', 'Completed'),
            (r'Match\s+drawn', 'Completed'),
            (r'Match\s+tied', 'Completed'),
            (r'No\s+result', 'No Result'),
            (r'opt\s+to\s+(bat|bowl)', 'Live'),
            (r'Need\s+\d+\s+to\s+win', 'Live'),
            (r'Day\s+\d+', 'Live'),
            (r'Innings\s+Break', 'Break'),
            (r'Stumps', 'Stumps'),
            (r'Tea', 'Tea'),
            (r'Lunch', 'Lunch'),
        ]
        
        for pattern, status in status_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                if status == 'Completed':
                    result['match_status'] = match.group()  # e.g., "India won by 5 wickets"
                    result['result'] = match.group()
                else:
                    result['match_status'] = status
                break
        
        # If no status found, check if match is upcoming
        if not result['match_status']:
            if 'yet to begin' in page_text.lower() or 'preview' in page_text.lower():
                result['match_status'] = 'Upcoming'
    
    logger.info(f"Scraped match {match_id}: {result['match_title']} - Status: {result['match_status']}")
    return {'success': True, **result}


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
