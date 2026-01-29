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

CATEGORIES = {
    'international': {
        'name': 'International',
        'url': 'https://www.cricbuzz.com/cricket-team'
    },
    'domestic': {
        'name': 'Domestic',
        'url': 'https://www.cricbuzz.com/cricket-team/domestic'
    },
    'league': {
        'name': 'League',
        'url': 'https://www.cricbuzz.com/cricket-team/league'
    },
    'women': {
        'name': 'Women',
        'url': 'https://www.cricbuzz.com/cricket-team/women'
    }
}

SERIES_CATEGORIES = {
    'international': {
        'name': 'International',
        'url': 'https://www.cricbuzz.com/cricket-schedule/series/international'
    },
    'domestic': {
        'name': 'Domestic',
        'url': 'https://www.cricbuzz.com/cricket-schedule/series/domestic'
    },
    'league': {
        'name': 'League',
        'url': 'https://www.cricbuzz.com/cricket-schedule/series/league'
    },
    'women': {
        'name': 'Women',
        'url': 'https://www.cricbuzz.com/cricket-schedule/series/women'
    }
}


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
    """
    Scrape all matches from Cricbuzz live-scores page.
    Gets ALL matches from the first 'div.flex.flex-col.gap-3' container.
    Returns dynamically - whatever matches are in that container.
    """
    url = "https://www.cricbuzz.com/cricket-match/live-scores"
    html = fetch_page(url)
    
    if not html:
        return {'success': False, 'matches': [], 'message': 'Failed to fetch page'}
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the FIRST main container with match links
    main_container = None
    containers = soup.select('div.flex.flex-col.gap-3')
    for container in containers:
        if container.find('a', href=re.compile(r'/live-cricket-scores/\d+/')):
            main_container = container
            break
    
    if not main_container:
        return {'success': False, 'matches': [], 'message': 'No match container found'}
    
    # Build status map from CSS classes
    status_map = {}
    result_map = {}
    
    # Find status from text-cbLive, text-cbComplete, text-cbPreview classes
    for span in main_container.find_all('span', class_=re.compile(r'text-cb')):
        classes = span.get('class', [])
        class_str = ' '.join(classes)
        text = span.get_text(strip=True)
        
        # Skip navigation links
        if text in ['Live Score', 'Scorecard', 'Full Commentary', 'News', 'Highlights']:
            continue
        
        # Determine status
        if 'cbLive' in class_str:
            status = 'Live'
        elif 'cbComplete' in class_str:
            status = 'Complete'
        elif 'cbPreview' in class_str:
            status = 'Preview'
        else:
            continue
        
        # Find match_id from nearby link
        parent = span.parent
        for _ in range(8):
            if parent:
                link = parent.find('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
                if link:
                    m = re.search(r'/live-cricket-scores/(\d+)/', link.get('href', ''))
                    if m:
                        mid = m.group(1)
                        if mid not in status_map:
                            status_map[mid] = status
                            result_map[mid] = text
                        break
                parent = parent.parent
    
    # Extract scores
    score_map = {}
    score_pattern = re.compile(r'\d{1,3}(?:[-/]\d{1,2})?\s*\(\d+\.?\d*\)')
    score_elements = main_container.find_all(string=score_pattern)
    
    for elem in score_elements:
        parent = elem.parent
        if parent:
            score_text = elem.strip()
            classes = parent.get('class', [])
            class_str = ' '.join(classes) if classes else ''
            
            grandparent = parent.parent
            for _ in range(6):
                if grandparent:
                    link = grandparent.find('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
                    if link:
                        m = re.search(r'/live-cricket-scores/(\d+)/', link.get('href', ''))
                        if m:
                            mid = m.group(1)
                            if mid not in score_map:
                                score_map[mid] = {'team1_score': None, 'team2_score': None}
                            
                            if 'cbTxtPrim' in class_str and not score_map[mid]['team1_score']:
                                score_map[mid]['team1_score'] = score_text
                            elif 'cbTxtSec' in class_str and not score_map[mid]['team2_score']:
                                score_map[mid]['team2_score'] = score_text
                            break
                    grandparent = grandparent.parent
    
    # Extract team flags and names
    flag_map = {}
    for img in main_container.find_all('img'):
        src = img.get('src', '')
        alt = img.get('alt', '')
        if 'static.cricbuzz.com' in src and '.jpg' in src:
            team_name = alt.replace('-', ' ').title() if alt else ''
            
            parent = img.parent
            for _ in range(8):
                if parent:
                    link = parent.find('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
                    if link:
                        m = re.search(r'/live-cricket-scores/(\d+)/', link.get('href', ''))
                        if m:
                            mid = m.group(1)
                            if mid not in flag_map:
                                flag_map[mid] = {'team1_flag': None, 'team2_flag': None, 'team1_name': None, 'team2_name': None}
                            
                            if not flag_map[mid]['team1_flag']:
                                flag_map[mid]['team1_flag'] = src
                                flag_map[mid]['team1_name'] = team_name
                            elif not flag_map[mid]['team2_flag']:
                                flag_map[mid]['team2_flag'] = src
                                flag_map[mid]['team2_name'] = team_name
                            break
                    parent = parent.parent
    
    # Extract series info for each match
    series_map = {}
    for s_link in main_container.find_all('a', href=re.compile(r'/cricket-series/(\d+)/')):
        href = s_link.get('href', '')
        match = re.search(r'/cricket-series/(\d+)/([^/\?"]+)', href)
        if match:
            series_id = match.group(1)
            series_name = s_link.get_text(strip=True)
            if series_name and series_name not in ['Matches', 'Points Table', 'Venues']:
                # Find match links near this series link
                parent = s_link.parent
                for _ in range(5):
                    if parent:
                        match_links = parent.find_all('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
                        for m_link in match_links:
                            m_match = re.search(r'/live-cricket-scores/(\d+)/', m_link.get('href', ''))
                            if m_match:
                                mid = m_match.group(1)
                                if mid not in series_map:
                                    series_map[mid] = {'series_id': series_id, 'series_name': series_name}
                        if match_links:
                            break
                        parent = parent.parent
    
    # Get ALL unique match IDs from first container
    all_match_links = main_container.find_all('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
    seen_match_ids = set()
    matches = []
    
    for link in all_match_links:
        href = link.get('href', '')
        m = re.search(r'/live-cricket-scores/(\d+)/', href)
        if m:
            mid = m.group(1)
            if mid not in seen_match_ids:
                seen_match_ids.add(mid)
                
                # Get status (default to 'Upcoming' if not found)
                status = status_map.get(mid, 'Upcoming')
                result = result_map.get(mid, '')
                
                # Get scores
                scores = score_map.get(mid, {})
                team1_score = scores.get('team1_score', '-')
                team2_score = scores.get('team2_score', '-')
                
                # Get flags and team names
                flags = flag_map.get(mid, {})
                team1_flag = flags.get('team1_flag', '')
                team2_flag = flags.get('team2_flag', '')
                team1_name = flags.get('team1_name', '')
                team2_name = flags.get('team2_name', '')
                
                # Get series info
                series_info = series_map.get(mid, {})
                series_id = series_info.get('series_id', '')
                series_name = series_info.get('series_name', '')
                
                # Get match title from link text
                match_title = link.get_text(strip=True) or ''
                
                matches.append({
                    'match_id': mid,
                    'match_title': match_title,
                    'state': status,
                    'result': result,
                    'team1_name': team1_name,
                    'team2_name': team2_name,
                    'team1_score': team1_score,
                    'team2_score': team2_score,
                    'team1_flag': team1_flag,
                    'team2_flag': team2_flag,
                    'series_id': series_id,
                    'series_name': series_name
                })
    
    logger.info(f"Live Scores: Found {len(matches)} matches in first container")
    return {'success': True, 'matches': matches, 'count': len(matches), 'message': f'Found {len(matches)} matches'}


def scrape_series_from_live_page():
    """
    Scrape unique series from Cricbuzz live-scores page.
    Each series includes its match IDs found on the page.
    Returns list of series with series_id, series_name, series_url, and match_ids
    Uses CSS classes (text-cbLive, text-cbComplete) for accurate status detection.
    """
    url = "https://www.cricbuzz.com/cricket-match/live-scores"
    html = fetch_page(url)
    
    if not html:
        return {'success': False, 'series': [], 'message': 'Failed to fetch page'}
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the main match container (flex flex-col gap-3 with match links)
    main_container = None
    containers = soup.select('div.flex.flex-col.gap-3')
    for container in containers:
        if container.find('a', href=re.compile(r'/live-cricket-scores/\d+/')):
            main_container = container
            break
    
    # If no container found, use full soup
    search_scope = main_container if main_container else soup
    
    # Build status map from CSS classes (text-cbLive, text-cbComplete)
    status_map = {}
    result_map = {}
    score_map = {}  # Store team scores
    
    # Find all spans with status classes within the container
    status_spans = search_scope.find_all('span', class_=re.compile(r'text-cb(Live|Complete)'))
    for span in status_spans:
        classes = span.get('class', [])
        class_str = ' '.join(classes)
        result_text = span.get_text(strip=True)
        
        # Skip navigation links like "Live Score", "Scorecard", etc.
        if result_text in ['Live Score', 'Scorecard', 'Full Commentary', 'News', 'Highlights']:
            continue
        
        # Determine status from CSS class
        if 'cbLive' in class_str:
            status = 'Live'
        elif 'cbComplete' in class_str:
            status = 'Completed'
        else:
            continue
        
        # Find match_id from nearby link
        parent = span.parent
        for _ in range(8):
            if parent:
                link = parent.find('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
                if link:
                    m = re.search(r'/live-cricket-scores/(\d+)/', link.get('href', ''))
                    if m:
                        mid = m.group(1)
                        if mid not in status_map:
                            status_map[mid] = status
                            result_map[mid] = result_text
                        break
                parent = parent.parent
    
    # Extract scores (format: 215-7 (20) OR 165 (18.4) for all-out) from the container
    score_pattern = re.compile(r'\d{1,3}(?:[-/]\d{1,2})?\s*\(\d+\.?\d*\)')
    score_elements = search_scope.find_all(string=score_pattern)
    
    for elem in score_elements:
        parent = elem.parent
        if parent:
            score_text = elem.strip()
            classes = parent.get('class', [])
            class_str = ' '.join(classes) if classes else ''
            
            # Find match_id
            grandparent = parent.parent
            for _ in range(6):
                if grandparent:
                    link = grandparent.find('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
                    if link:
                        m = re.search(r'/live-cricket-scores/(\d+)/', link.get('href', ''))
                        if m:
                            mid = m.group(1)
                            if mid not in score_map:
                                score_map[mid] = {'team1_score': None, 'team2_score': None}
                            
                            # text-cbTxtPrim = Team 1, text-cbTxtSec = Team 2
                            if 'cbTxtPrim' in class_str and not score_map[mid]['team1_score']:
                                score_map[mid]['team1_score'] = score_text
                            elif 'cbTxtSec' in class_str and not score_map[mid]['team2_score']:
                                score_map[mid]['team2_score'] = score_text
                            break
                    grandparent = grandparent.parent
    
    # Extract team flag URLs and team names
    flag_map = {}  # match_id -> {team1_flag, team2_flag, team1_name, team2_name}
    all_imgs = search_scope.find_all('img')
    for img in all_imgs:
        src = img.get('src', '')
        alt = img.get('alt', '')
        if 'static.cricbuzz.com' in src and '.jpg' in src:
            # Extract team name from alt attribute (e.g., "new-zealand" -> "New Zealand")
            team_name = alt.replace('-', ' ').title() if alt else ''
            
            # Find match_id from nearby link
            parent = img.parent
            for _ in range(8):
                if parent:
                    link = parent.find('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
                    if link:
                        m = re.search(r'/live-cricket-scores/(\d+)/', link.get('href', ''))
                        if m:
                            mid = m.group(1)
                            if mid not in flag_map:
                                flag_map[mid] = {'team1_flag': None, 'team2_flag': None, 'team1_name': None, 'team2_name': None}
                            
                            # First flag = Team 1, Second flag = Team 2
                            if not flag_map[mid]['team1_flag']:
                                flag_map[mid]['team1_flag'] = src
                                flag_map[mid]['team1_name'] = team_name
                            elif not flag_map[mid]['team2_flag']:
                                flag_map[mid]['team2_flag'] = src
                                flag_map[mid]['team2_name'] = team_name
                            break
                    parent = parent.parent
    
    # Also check title attributes for Upcoming matches (Preview)
    preview_links = search_scope.find_all('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
    for link in preview_links:
        title_attr = link.get('title', '').lower()
        href = link.get('href', '')
        m = re.search(r'/live-cricket-scores/(\d+)/', href)
        if m:
            mid = m.group(1)
            if mid not in status_map:
                if 'preview' in title_attr or 'upcoming' in title_attr:
                    status_map[mid] = 'Upcoming'
                    result_map[mid] = 'Preview'
    
    series_list = []
    seen_series_ids = set()
    
    # Find all series links first, then find their correct parent containers
    series_links = search_scope.find_all('a', href=re.compile(r'/cricket-series/(\d+)/'))
    
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
                    # Only include matches that have Live or Completed status (not Upcoming)
                    if mid in status_map and status_map[mid] in ['Live', 'Completed']:
                        seen_match_ids.add(mid)
                        match_title = m_link.get_text(strip=True)
                        match_status = status_map.get(mid)
                        match_result = result_map.get(mid, '')
                        
                        # Get scores
                        scores = score_map.get(mid, {})
                        team1_score = scores.get('team1_score', '-')
                        team2_score = scores.get('team2_score', '-')
                        
                        # Get flags and team names
                        flags = flag_map.get(mid, {})
                        team1_flag = flags.get('team1_flag', '')
                        team2_flag = flags.get('team2_flag', '')
                        team1_name = flags.get('team1_name', '')
                        team2_name = flags.get('team2_name', '')
                        
                        matches.append({
                            'match_id': mid,
                            'match_title': match_title if match_title else '-',
                            'match_status': match_status,
                            'match_result': match_result,
                            'team1_score': team1_score,
                            'team2_score': team2_score,
                            'team1_flag': team1_flag,
                            'team2_flag': team2_flag,
                            'team1_name': team1_name,
                            'team2_name': team2_name
                        })
        
        # Only add series if it has matches with status
        if matches:
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
        'live_status': None,  # e.g., "West Indies U19 need 115 runs in 86 balls"
        'match_time': None,
        'start_date': None,
        'end_date': None,
        'team1': None,
        'team2': None,
        'team1_score': None,
        'team2_score': None,
        'venue': None,
        'match_format': None,
        'series_name': None,
        'result': None,
        'toss': None,  # e.g., "West Indies U19 won the toss and opt to Bowl"
        'match_short': None,  # e.g., "7th Match" or "4th T20I"
        'innings': []
    }
    
    # Extract live match status (e.g., "need X runs in Y balls")
    live_status_div = soup.find('div', class_='text-cbLive')
    if live_status_div:
        result['live_status'] = live_status_div.get_text(strip=True)
    
    # Extract Date & Time (e.g., "Today, 9:30 AM LOCAL")
    for span in soup.find_all('span', class_='font-bold'):
        if 'Date' in span.get_text():
            parent = span.parent
            if parent:
                full_text = parent.get_text(strip=True)
                date_match = re.search(r'Date.*?Time:\s*(.+)', full_text)
                if date_match:
                    # Clean up the text (fix spacing issues)
                    date_time = date_match.group(1).strip()
                    date_time = re.sub(r',(\S)', r', \1', date_time)  # Add space after comma
                    date_time = re.sub(r'(\d)(AM|PM)', r'\1 \2', date_time)  # Add space before AM/PM
                    date_time = re.sub(r'(AM|PM)LOCAL', r'\1 LOCAL', date_time)  # Add space before LOCAL
                    result['match_datetime'] = date_time
            break
    
    # Extract toss result (e.g., "West Indies U19 won the toss and opt to Bowl")
    for div in soup.find_all('div'):
        text = div.get_text(strip=True)
        if ('opt to bat' in text.lower() or 'opt to bowl' in text.lower()) and 'won the toss' in text.lower():
            if len(text) < 100:
                # Remove "Toss" prefix if present
                toss_text = re.sub(r'^Toss', '', text).strip()
                result['toss'] = toss_text
                break
    
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
                # Extract start and end dates (ISO format)
                if data.get('startDate'):
                    result['start_date'] = data['startDate']
                if data.get('endDate'):
                    result['end_date'] = data['endDate']
                break
        except:
            continue
    
    # Extract short match description from title (e.g., "7th Match", "4th T20I", "2nd Test")
    if result.get('match_title'):
        match_desc = re.search(r'(\d+(?:st|nd|rd|th)\s+(?:Match|T20I?|ODI|Test|One-Day))', result['match_title'], re.IGNORECASE)
        if match_desc:
            result['match_short'] = match_desc.group(1)
    
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
        
        # Extract series name from match title (e.g., "Australia tour of Pakistan, 2026")
        series_match = re.search(r',\s*([^,]+tour[^,]+,?\s*\d{4})', result['match_title'], re.IGNORECASE)
        if series_match:
            result['series_name'] = series_match.group(1).strip()
        else:
            # Try alternate pattern for other series types
            series_match2 = re.search(r',\s*(\d+(?:st|nd|rd|th)?\s+\w+),\s*(.+)$', result['match_title'])
            if series_match2:
                result['series_name'] = series_match2.group(2).strip()
    
    # Fallback: Get series name from breadcrumb/link if not found in title
    if not result['series_name']:
        series_link = soup.find('a', href=re.compile(r'/cricket-series/\d+/'))
        if series_link:
            result['series_name'] = series_link.get_text(strip=True)
    
    # Extract innings data from new Cricbuzz structure (id="team-XXX-innings-X")
    innings_divs = soup.find_all('div', id=re.compile(r'^team-\d+-innings-\d+$'))
    seen_innings = set()
    for inn_div in innings_divs:
        inn_id = inn_div.get('id')
        if inn_id in seen_innings:
            continue
        seen_innings.add(inn_id)
        
        # Parse innings number from id
        inn_match = re.search(r'innings-(\d+)', inn_id)
        innings_num = int(inn_match.group(1)) if inn_match else len(result['innings']) + 1
        
        # Get team name and score from the div text
        inn_text = inn_div.get_text(strip=True)
        # Pattern: "AUSU19Australia U19314-7(50 Ov)" or "WIU19West Indies U19185-3(30.5 Ov)"
        # Extract score first: runs-wickets(overs Ov)
        score_match = re.search(r'(\d{1,3})-(\d{1,2})\((\d+(?:\.\d+)?)\s*Ov\)', inn_text)
        
        if score_match:
            runs = score_match.group(1)
            wickets = score_match.group(2)
            overs = score_match.group(3)
            
            # Extract team name from text before score
            text_before_score = inn_text[:score_match.start()].strip()
            # Remove abbreviation prefix (usually uppercase letters at start)
            # Pattern: AUSU19Australia U19 -> Australia U19, WIU19West Indies U19 -> West Indies U19
            # Find where lowercase letter starts (that's where full team name begins)
            lower_match = re.search(r'[a-z]', text_before_score)
            if lower_match:
                # Abbreviation is from start to just before first lowercase
                first_lower_idx = lower_match.start()
                team_abbr = text_before_score[:first_lower_idx]
                # Include the uppercase letter before the lowercase
                if first_lower_idx > 0:
                    team_name = text_before_score[first_lower_idx - 1:]
                else:
                    team_name = text_before_score
            else:
                # All uppercase, use as is
                team_abbr = text_before_score[:5]
                team_name = text_before_score
            
            innings_data = {
                'innings_num': innings_num,
                'team_name': team_name,
                'team_abbr': team_abbr,
                'total_score': f"{runs}/{wickets}",
                'overs': overs,
                'batting': [],
                'bowling': [],
                'fall_of_wickets': []
            }
            
            # Extract batting data from scard-team-XXX-innings-X div
            # The id pattern: scard-team-129-innings-1
            team_match = re.search(r'team-(\d+)-innings-(\d+)', inn_id)
            if team_match:
                team_id = team_match.group(1)
                inn_num = team_match.group(2)
                scard_id = f"scard-team-{team_id}-innings-{inn_num}"
                scard_div = soup.find('div', id=scard_id)
                
                if scard_div:
                    # Extract batting data from scorecard-bat-grid divs
                    bat_grids = scard_div.find_all('div', class_=re.compile(r'scorecard-bat-grid'))
                    for bat_row in bat_grids:
                        # Skip header row (has "Batter" text)
                        if bat_row.find('div', string=re.compile(r'^Batter$')):
                            continue
                        
                        # Find player name link
                        player_link = bat_row.find('a', href=re.compile(r'/profiles/'))
                        if not player_link:
                            continue
                        
                        player_name = player_link.get_text(strip=True)
                        
                        # Extract player_id from URL (e.g., /profiles/12345/player-name)
                        player_href = player_link.get('href', '')
                        player_id_match = re.search(r'/profiles/(\d+)/', player_href)
                        player_id = player_id_match.group(1) if player_id_match else None
                        
                        # Find dismissal text (in text-cbTxtSec div)
                        dismissal_div = bat_row.find('div', class_=re.compile(r'text-cbTxtSec'))
                        dismissal = dismissal_div.get_text(strip=True) if dismissal_div else 'not out'
                        
                        # Extract runs, balls, 4s, 6s, SR from divs with justify-center
                        stats_divs = bat_row.find_all('div', class_=re.compile(r'justify-center'))
                        stats = []
                        for sd in stats_divs:
                            text = sd.get_text(strip=True)
                            if text and text not in ['R', 'B', '4s', '6s', 'SR', '']:
                                stats.append(text)
                        
                        if len(stats) >= 5:
                            batting_entry = {
                                'player': player_name,
                                'player_id': player_id,
                                'dismissal': dismissal,
                                'runs': stats[0],
                                'balls': stats[1],
                                'fours': stats[2],
                                'sixes': stats[3],
                                'strike_rate': stats[4]
                            }
                            innings_data['batting'].append(batting_entry)
                    
                    # Extract bowling data from scorecard-bowl-grid divs
                    bowl_grids = scard_div.find_all('div', class_=re.compile(r'scorecard-bowl-grid'))
                    for bowl_row in bowl_grids:
                        # Skip header row
                        if bowl_row.find('div', string=re.compile(r'^Bowler$')):
                            continue
                        
                        # Find bowler name link
                        bowler_link = bowl_row.find('a', href=re.compile(r'/profiles/'))
                        if not bowler_link:
                            continue
                        
                        bowler_name = bowler_link.get_text(strip=True)
                        
                        # Extract player_id from URL
                        bowler_href = bowler_link.get('href', '')
                        bowler_id_match = re.search(r'/profiles/(\d+)/', bowler_href)
                        bowler_id = bowler_id_match.group(1) if bowler_id_match else None
                        
                        # Extract O, M, R, W, NB, WD, ECO - keep all values including empty for position alignment
                        stats_divs = bowl_row.find_all('div', class_=re.compile(r'justify-center'))
                        all_stats = []
                        for sd in stats_divs:
                            text = sd.get_text(strip=True)
                            # Skip header labels
                            if text in ['O', 'M', 'R', 'W', 'NB', 'WD', 'ECO']:
                                continue
                            all_stats.append(text)
                        
                        # Bowling columns: O, M, R, W, (NB, WD hidden on mobile), ECO
                        # Economy is always the last column before the highlight icon
                        if len(all_stats) >= 5:
                            bowling_entry = {
                                'bowler': bowler_name,
                                'player_id': bowler_id,
                                'overs': all_stats[0],
                                'maidens': all_stats[1],
                                'runs': all_stats[2],
                                'wickets': all_stats[3],
                                'economy': all_stats[-1]  # Economy is always last
                            }
                            innings_data['bowling'].append(bowling_entry)
                    
                    # Extract fall of wickets from parent container (FOW is outside scard_div)
                    parent_container = scard_div.parent
                    fow_grids = parent_container.find_all('div', class_=re.compile(r'scorecard-fow-grid')) if parent_container else []
                    for fow_row in fow_grids:
                        # Skip header row
                        if fow_row.find('div', string=re.compile(r'Fall of Wickets')):
                            continue
                        
                        # Find player name
                        player_link = fow_row.find('a', href=re.compile(r'/profiles/'))
                        if not player_link:
                            continue
                        
                        player_name = player_link.get_text(strip=True)
                        
                        # Extract player_id from URL
                        fow_player_href = player_link.get('href', '')
                        fow_player_id_match = re.search(r'/profiles/(\d+)/', fow_player_href)
                        fow_player_id = fow_player_id_match.group(1) if fow_player_id_match else None
                        
                        # Extract score and over
                        stats_divs = fow_row.find_all('div', class_=re.compile(r'justify-center'))
                        stats = []
                        for sd in stats_divs:
                            text = sd.get_text(strip=True)
                            if text and text not in ['Score', 'Over', 'Overs', 'Runs', '']:
                                stats.append(text)
                        
                        if len(stats) >= 2:
                            fow_entry = {
                                'player': player_name,
                                'player_id': fow_player_id,
                                'score': stats[0],  # e.g., "73-1"
                                'over': stats[1]    # e.g., "8.6"
                            }
                            innings_data['fall_of_wickets'].append(fow_entry)
            
            result['innings'].append(innings_data)
            
            # Set team scores based on team name match (not innings order)
            innings_score = f"{runs}/{wickets} ({overs} Ov)"
            team_name_lower = team_name.lower() if team_name else ''
            team1_lower = result.get('team1', '').lower() if result.get('team1') else ''
            team2_lower = result.get('team2', '').lower() if result.get('team2') else ''
            
            # Match by team name to assign correct score
            if team_name_lower and team1_lower and team_name_lower in team1_lower or team1_lower in team_name_lower:
                if not result['team1_score']:
                    result['team1_score'] = innings_score
            elif team_name_lower and team2_lower and team_name_lower in team2_lower or team2_lower in team_name_lower:
                if not result['team2_score']:
                    result['team2_score'] = innings_score
            else:
                # Fallback: assign by innings order if no match found
                if innings_num == 1 and not result['team1_score'] and not result['team2_score']:
                    # First innings - could be either team, set based on team name extracted
                    if not result['team1']:
                        result['team1'] = team_name
                        result['team1_score'] = innings_score
                    elif not result['team2']:
                        result['team2'] = team_name  
                        result['team2_score'] = innings_score
                elif innings_num == 2:
                    if not result['team2_score']:
                        result['team2_score'] = innings_score
                        if not result['team2']:
                            result['team2'] = team_name
    
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
        
        # Extract match start time (e.g., "Match starts at Jan 29, 11:00 GMT")
        time_div = live_soup.find('div', class_='text-cbPreview')
        if time_div:
            time_text = time_div.get_text(strip=True)
            # Extract date and time from "Match starts at Jan 29, 11:00 GMT"
            time_match = re.search(r'Match starts at\s+(.+)', time_text, re.IGNORECASE)
            if time_match:
                result['match_time'] = time_match.group(1).strip()
        
        # Also look for date in other elements if not found
        if not result['match_time']:
            for div in live_soup.find_all('div'):
                text = div.get_text(strip=True)
                if 'Match starts at' in text and len(text) < 60:
                    time_match = re.search(r'Match starts at\s+(.+?)(?:$|Match)', text)
                    if time_match:
                        result['match_time'] = time_match.group(1).strip()
                        break
        
        # First check if match is upcoming (no innings data)
        has_innings = len(result.get('innings', [])) > 0
        
        # Check for upcoming match indicators
        upcoming_patterns = ['yet to begin', 'match starts', 'preview', 'tomorrow,', 'starts at']
        is_upcoming = any(p in page_text.lower() for p in upcoming_patterns)
        
        if not has_innings and is_upcoming:
            result['match_status'] = 'Upcoming'
        elif not has_innings and result.get('match_datetime') and 'tomorrow' in result.get('match_datetime', '').lower():
            result['match_status'] = 'Upcoming'
        else:
            # First try to find result in specific element
            result_el = live_soup.find('div', class_='text-cbTextLink')
            if result_el:
                result_text = result_el.get_text(strip=True)
                if 'won by' in result_text.lower() or 'match drawn' in result_text.lower() or 'match tied' in result_text.lower():
                    result['match_status'] = result_text
                    result['result'] = result_text
            
            # If no result element, check patterns in page text
            if not result['match_status']:
                # Determine if this is a Test match (multi-day) based on match format
                match_title = result.get('match_title', '').lower()
                is_test_match = 'test' in match_title or 'day ' in match_title
                
                # Base patterns for all match types
                status_patterns = [
                    (r'Match\s+drawn', 'Completed'),
                    (r'Match\s+tied', 'Completed'),
                    (r'No\s+result', 'No Result'),
                    (r'Innings\s+Break', 'Break'),
                ]
                
                # Test-specific breaks (only for multi-day matches)
                if is_test_match:
                    status_patterns.extend([
                        (r'Stumps', 'Stumps'),
                        (r'Tea', 'Tea'),
                        (r'Lunch', 'Lunch'),
                    ])
                
                for pattern, status in status_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        result['match_status'] = status
                        break
            
            # If has innings but no specific status, it's Live
            if not result['match_status'] and has_innings:
                result['match_status'] = 'Live'
            elif not result['match_status']:
                result['match_status'] = 'Upcoming'
    
    logger.info(f"Scraped match {match_id}: {result['match_title']} - Status: {result['match_status']}")
    return {'success': True, **result}


def scrape_category(category_slug):
    """Scrape teams from a category (international, domestic, league, women)."""
    category_urls = {
        'international': 'https://www.cricbuzz.com/cricket-team',
        'domestic': 'https://www.cricbuzz.com/cricket-team/domestic',
        'league': 'https://www.cricbuzz.com/cricket-team/league',
        'women': 'https://www.cricbuzz.com/cricket-team/women'
    }
    
    url = category_urls.get(category_slug)
    if not url:
        return {'success': False, 'teams': [], 'message': f'Unknown category: {category_slug}'}
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        teams = []
        
        team_links = soup.select('a.cb-teams-lft-ancr, a[href*="/cricket-team/"]')
        
        for link in team_links:
            href = link.get('href', '')
            if '/cricket-team/' not in href or href.endswith('/cricket-team') or href.endswith('/cricket-team/'):
                continue
            if '/domestic' in href or '/league' in href or '/women' in href:
                if not any(x in href for x in ['/profiles/', '/players/']):
                    continue
            
            team_name = link.get_text(strip=True)
            if not team_name or len(team_name) < 2:
                continue
            
            team_id = None
            team_id_match = re.search(r'/cricket-team/[^/]+/(\d+)', href)
            if team_id_match:
                team_id = team_id_match.group(1)
            
            flag_url = None
            flag_img = link.find('img')
            if flag_img:
                flag_url = flag_img.get('src', '')
                if flag_url and not flag_url.startswith('http'):
                    flag_url = 'https://www.cricbuzz.com' + flag_url
            
            team_url = href if href.startswith('http') else 'https://www.cricbuzz.com' + href
            
            if team_name and team_id:
                teams.append({
                    'name': team_name,
                    'team_id': team_id,
                    'flag_url': flag_url,
                    'team_url': team_url
                })
        
        seen = set()
        unique_teams = []
        for t in teams:
            if t['team_id'] not in seen:
                seen.add(t['team_id'])
                unique_teams.append(t)
        
        logger.info(f"Scraped {len(unique_teams)} teams from {category_slug}")
        return {'success': True, 'teams': unique_teams, 'message': f'Scraped {len(unique_teams)} teams'}
        
    except Exception as e:
        logger.error(f"Error scraping category {category_slug}: {e}")
        return {'success': False, 'teams': [], 'message': str(e)}


def scrape_players_from_team(team_url):
    """Scrape players from a team page."""
    try:
        if not team_url:
            return []
        
        if not team_url.startswith('http'):
            team_url = 'https://www.cricbuzz.com' + team_url
        
        players_url = team_url.rstrip('/') + '/players'
        
        response = requests.get(players_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        players = []
        
        player_links = soup.select('a[href*="/profiles/"]')
        
        for link in player_links:
            href = link.get('href', '')
            if '/profiles/' not in href:
                continue
            
            player_name = link.get_text(strip=True)
            if not player_name or len(player_name) < 2:
                continue
            
            player_id = None
            player_id_match = re.search(r'/profiles/(\d+)/', href)
            if player_id_match:
                player_id = player_id_match.group(1)
            
            photo_url = None
            photo_img = link.find('img')
            if photo_img:
                photo_url = photo_img.get('src', '')
                if photo_url and not photo_url.startswith('http'):
                    photo_url = 'https://www.cricbuzz.com' + photo_url
            
            player_url = href if href.startswith('http') else 'https://www.cricbuzz.com' + href
            
            role_elem = link.find_next('div', class_='cb-font-12')
            role = role_elem.get_text(strip=True) if role_elem else None
            
            if player_name and player_id:
                players.append({
                    'name': player_name,
                    'player_id': player_id,
                    'photo_url': photo_url,
                    'player_url': player_url,
                    'role': role
                })
        
        seen = set()
        unique_players = []
        for p in players:
            if p['player_id'] not in seen:
                seen.add(p['player_id'])
                unique_players.append(p)
        
        logger.info(f"Scraped {len(unique_players)} players from {team_url}")
        return unique_players
        
    except Exception as e:
        logger.error(f"Error scraping players from {team_url}: {e}")
        return []


def scrape_series_from_category(category_url):
    """Scrape series from a category URL like /cricket-schedule/series/international."""
    try:
        if not category_url:
            return {'success': False, 'series': []}
        
        if not category_url.startswith('http'):
            category_url = 'https://www.cricbuzz.com' + category_url
        
        response = requests.get(category_url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            return {'success': False, 'series': []}
        
        html = response.text.replace('\\"', '"')
        series_data = []
        seen = set()
        
        schedule_match = re.search(r'"seriesScheduleData"\s*:\s*(\[.*?\])\s*,\s*"', html, re.DOTALL)
        
        if schedule_match:
            try:
                import json
                schedule_json = schedule_match.group(1)
                schedule_json = schedule_json.replace('\\"', '"')
                schedule = json.loads(schedule_json)
                
                for month_group in schedule:
                    month_year = month_group.get('date', '')
                    for series in month_group.get('series', []):
                        sid = str(series.get('id', ''))
                        name = series.get('name', '')
                        
                        if sid and sid not in seen:
                            seen.add(sid)
                            slug = name.lower().replace(' ', '-').replace(',', '').replace("'", '').replace('/', '-')
                            series_url = f"https://www.cricbuzz.com/cricket-series/{sid}/{slug}/matches"
                            series_data.append({
                                'id': sid,
                                'name': name,
                                'url': series_url,
                                'date_range': month_year.title() if month_year else ''
                            })
            except Exception as e:
                logger.error(f"Error parsing series schedule: {e}")
        
        if not series_data:
            match_positions = [(m.start(), m.group(1)) for m in re.finditer(r'"matchInfo"\s*:\s*\{[^}]*"seriesId"\s*:\s*(\d+)', html)]
            
            for pos, sid in match_positions:
                if sid in seen:
                    continue
                
                context = html[pos:pos+2000]
                series_name_match = re.search(r'"seriesName"\s*:\s*"([^"]+)"', context)
                
                if series_name_match:
                    name = series_name_match.group(1)
                    seen.add(sid)
                    slug = name.lower().replace(' ', '-').replace(',', '').replace("'", '')
                    series_url = f"https://www.cricbuzz.com/cricket-series/{sid}/{slug}/matches"
                    series_data.append({'id': sid, 'name': name, 'url': series_url, 'date_range': ''})
        
        logger.info(f"Scraped {len(series_data)} series from {category_url}")
        return {'success': True, 'series': series_data}
        
    except Exception as e:
        logger.error(f"Error scraping series from category: {e}")
        return {'success': False, 'series': []}


def scrape_matches_from_series(series_url):
    """Scrape matches from a series URL."""
    try:
        if not series_url:
            return []
        
        if not series_url.startswith('http'):
            series_url = 'https://www.cricbuzz.com' + series_url
        
        if '/matches' not in series_url:
            series_url = series_url.rstrip('/') + '/matches'
        
        response = requests.get(series_url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            return []
        
        html = response.text.replace('\\"', '"')
        matches_data = []
        seen_ids = set()
        
        series_id_from_url = None
        url_match = re.search(r'/cricket-series/(\d+)/', series_url)
        if url_match:
            series_id_from_url = url_match.group(1)
        
        match_positions = [(m.start(), m.group(1)) for m in re.finditer(r'"matchInfo"\s*:\s*\{[^}]*"matchId"\s*:\s*(\d+)', html)]
        
        for pos, mid in match_positions:
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            
            next_match = html.find('"matchInfo"', pos + 50)
            if next_match == -1 or next_match > pos + 2000:
                context_end = pos + 1500
            else:
                context_end = next_match
            context = html[pos:context_end]
            
            match_sid = re.search(r'"seriesId"\s*:\s*(\d+)', context)
            if series_id_from_url and match_sid:
                if match_sid.group(1) != series_id_from_url:
                    continue
            
            series_name = re.search(r'"seriesName"\s*:\s*"([^"]*)"', context)
            match_desc = re.search(r'"matchDesc"\s*:\s*"([^"]*)"', context)
            match_format = re.search(r'"matchFormat"\s*:\s*"([^"]*)"', context)
            status = re.search(r'"status"\s*:\s*"([^"]*)"', context)
            state = re.search(r'"state"\s*:\s*"([^"]*)"', context)
            start_date = re.search(r'"startDate"\s*:\s*"?(\d+)"?', context)
            
            team1_name = re.search(r'"team1"\s*:\s*\{[^}]*"teamName"\s*:\s*"([^"]*)"', context)
            team2_name = re.search(r'"team2"\s*:\s*\{[^}]*"teamName"\s*:\s*"([^"]*)"', context)
            team1_id = re.search(r'"team1"\s*:\s*\{[^}]*"teamId"\s*:\s*(\d+)', context)
            team2_id = re.search(r'"team2"\s*:\s*\{[^}]*"teamId"\s*:\s*(\d+)', context)
            
            team1_score_match = re.search(r'"team1Score"\s*:\s*\{[^}]*"inngs1"\s*:\s*\{[^}]*"runs"\s*:\s*(\d+)[^}]*"wickets"\s*:\s*(\d+)[^}]*"overs"\s*:\s*([\d.]+)', context)
            team2_score_match = re.search(r'"team2Score"\s*:\s*\{[^}]*"inngs1"\s*:\s*\{[^}]*"runs"\s*:\s*(\d+)[^}]*"wickets"\s*:\s*(\d+)[^}]*"overs"\s*:\s*([\d.]+)', context)
            
            team1_score = ''
            team2_score = ''
            if team1_score_match:
                runs, wickets, overs = team1_score_match.groups()
                team1_score = f"{runs}/{wickets} ({overs})"
            if team2_score_match:
                runs, wickets, overs = team2_score_match.groups()
                team2_score = f"{runs}/{wickets} ({overs})"
            
            venue_ground = re.search(r'"venueInfo"\s*:\s*\{[^}]*"ground"\s*:\s*"([^"]*)"', context)
            venue_city = re.search(r'"venueInfo"\s*:\s*\{[^}]*"city"\s*:\s*"([^"]*)"', context)
            
            match_date = ''
            if start_date:
                try:
                    from datetime import datetime as dt
                    ts = int(start_date.group(1)) / 1000
                    match_date = dt.fromtimestamp(ts).strftime('%a, %d %b %Y')
                except:
                    pass
            
            venue = ''
            if venue_ground and venue_city:
                venue = f"{venue_ground.group(1)}, {venue_city.group(1)}"
            elif venue_ground:
                venue = venue_ground.group(1)
            
            team1_short = team1_name.group(1) if team1_name else ''
            team2_short = team2_name.group(1) if team2_name else ''
            
            matches_data.append({
                'match_id': mid,
                'series_id': match_sid.group(1) if match_sid else series_id_from_url or '',
                'team1_id': team1_id.group(1) if team1_id else '',
                'team2_id': team2_id.group(1) if team2_id else '',
                'match_format': match_desc.group(1) if match_desc else '',
                'format_type': match_format.group(1) if match_format else '',
                'series_name': series_name.group(1) if series_name else '',
                'match_date': match_date,
                'state': state.group(1) if state else '',
                'team1': team1_short,
                'team2': team2_short,
                'team1_score': team1_score,
                'team2_score': team2_score,
                'venue': venue,
                'result': status.group(1) if status else ''
            })
        
        logger.info(f"Scraped {len(matches_data)} matches from {series_url}")
        return matches_data
        
    except Exception as e:
        logger.error(f"Error scraping matches from series: {e}")
        return []


def scrape_player_profile(player_url):
    """Scrape player profile details from Cricbuzz."""
    try:
        if not player_url:
            return None
        
        if not player_url.startswith('http'):
            player_url = 'https://www.cricbuzz.com' + player_url
        
        response = requests.get(player_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        profile = {
            'born': None,
            'birth_place': None,
            'nickname': None,
            'batting_style': None,
            'bowling_style': None,
            'role': None,
            'photo_url': None,
            'batting_stats': {},
            'bowling_stats': {},
            'career_timeline': []
        }
        
        # Extract player photo
        photo_img = soup.select_one('img[src*="static.cricbuzz.com/a/img/v1/"]')
        if photo_img:
            src = photo_img.get('src', '')
            if src and 'static.cricbuzz.com' in src:
                profile['photo_url'] = src
        
        # Get all text from the page for regex extraction
        page_text = soup.get_text()
        
        # Extract Born date using regex - pattern: BornDATE (YEARS)
        born_match = re.search(r'Born\s*([A-Za-z]+ \d{1,2}, \d{4})', page_text)
        if born_match:
            profile['born'] = born_match.group(1)
        
        # Extract Birth Place - pattern: Birth PlaceCITY
        birth_place_match = re.search(r'Birth\s*Place\s*([A-Za-z][A-Za-z\s]+?)(?:Nickname|Height|Role|Batting)', page_text)
        if birth_place_match:
            profile['birth_place'] = birth_place_match.group(1).strip()
        
        # Extract Nickname - pattern: NicknameNAME
        nickname_match = re.search(r'Nickname\s*([A-Za-z][A-Za-z\s]+?)(?:Height|Role|Batting|Born)', page_text)
        if nickname_match:
            profile['nickname'] = nickname_match.group(1).strip()
        
        # Extract Role - pattern: RoleTYPE
        role_match = re.search(r'Role\s*([A-Za-z][A-Za-z\-\s]+?)(?:Batting|Bowling|Teams|$)', page_text)
        if role_match:
            profile['role'] = role_match.group(1).strip()
        
        # Extract Batting Style - pattern: Batting StyleTYPE
        batting_match = re.search(r'Batting\s*Style\s*([A-Za-z][A-Za-z\s\-]+?)(?:Bowling|Teams|$)', page_text)
        if batting_match:
            profile['batting_style'] = batting_match.group(1).strip()
        
        # Extract Bowling Style - pattern: Bowling StyleTYPE
        bowling_match = re.search(r'Bowling\s*Style\s*([A-Za-z][A-Za-z\s\-]+?)(?:Teams|$)', page_text)
        if bowling_match:
            profile['bowling_style'] = bowling_match.group(1).strip()
        
        # Extract Career Timeline (Debut and Last Match for each format)
        career_timeline = []
        format_map = {'t20': 'T20', 'test': 'Test', 'odi': 'ODI', 'ipl': 'IPL'}
        
        # Two patterns exist on Cricbuzz:
        # Pattern 1: t20vs opponent, date, venuevs opponent2, date2, venue2
        # Pattern 2: t20Debutvs opponent, date, venueLast Playedvs opponent2, date2, venue2
        
        for fmt in ['t20', 'test', 'odi', 'ipl']:
            # Try Pattern 2 first (with Debut/Last Played)
            pattern2 = fmt + r'(?:Debut)?vs\s*([^,]+),\s*(\d{4}-\d{2}-\d{2}),\s*(.+?)(?:Last Played|Last Match)?vs\s*([^,]+),\s*(\d{4}-\d{2}-\d{2}),\s*(.+?)(?=t20|test|odi|ipl|clt|Career Info|$)'
            match = re.search(pattern2, page_text, re.IGNORECASE)
            if match:
                # Clean up venue text
                def clean_venue(v):
                    v = v.strip()
                    for suffix in ['Last Played', 'Last Match', 'Career Information', 'Career Info']:
                        if v.endswith(suffix):
                            v = v[:-len(suffix)].strip()
                    return v
                
                career_timeline.append({
                    'format': format_map.get(fmt, fmt.upper()),
                    'debut': {
                        'opponent': match.group(1).strip(),
                        'date': match.group(2).strip(),
                        'venue': clean_venue(match.group(3))
                    },
                    'last_match': {
                        'opponent': match.group(4).strip(),
                        'date': match.group(5).strip(),
                        'venue': clean_venue(match.group(6))
                    }
                })
        
        profile['career_timeline'] = career_timeline
        
        # Extract batting and bowling career summary stats
        batting_stats = {}
        bowling_stats = {}
        
        # Find all stats tables
        stats_tables = soup.select('table')
        batting_table_found = False
        
        for table in stats_tables:
            # Get headers from first row
            header_row = table.select_one('tr')
            if not header_row:
                continue
            
            headers = [th.get_text(strip=True) for th in header_row.select('th, td')]
            
            # Check if this is a career stats table (has Test, ODI, T20, IPL columns)
            if not any(fmt in headers for fmt in ['Test', 'ODI', 'T20', 'IPL']):
                continue
            
            # Get all data rows
            rows = table.select('tr')[1:]  # Skip header row
            
            # Build stats dictionary per format
            format_indices = {}
            for i, h in enumerate(headers):
                if h in ['Test', 'ODI', 'T20', 'IPL']:
                    format_indices[h] = i
            
            # Initialize format dicts
            for fmt in format_indices:
                if not batting_table_found:
                    batting_stats[fmt] = {}
                else:
                    bowling_stats[fmt] = {}
            
            for row in rows:
                cells = [td.get_text(strip=True) for td in row.select('td')]
                if len(cells) < 2:
                    continue
                
                stat_name = cells[0]
                if not stat_name:
                    continue
                
                # Map stat names to keys
                stat_key = stat_name.lower().replace(' ', '_').replace('/', '_')
                
                for fmt, idx in format_indices.items():
                    if idx < len(cells):
                        value = cells[idx]
                        if not batting_table_found:
                            batting_stats[fmt][stat_key] = value
                        else:
                            bowling_stats[fmt][stat_key] = value
            
            batting_table_found = True
        
        profile['batting_stats'] = batting_stats if batting_stats else None
        profile['bowling_stats'] = bowling_stats if bowling_stats else None
        
        # Also set flat stats for database columns (use Test stats as primary, fallback to ODI/T20/IPL)
        for fmt in ['Test', 'ODI', 'T20', 'IPL']:
            if fmt in batting_stats and batting_stats[fmt]:
                stats = batting_stats[fmt]
                if not profile.get('bat_matches'):
                    profile['bat_matches'] = stats.get('matches')
                    profile['bat_innings'] = stats.get('innings')
                    profile['bat_runs'] = stats.get('runs')
                    profile['bat_balls'] = stats.get('balls')
                    profile['bat_highest'] = stats.get('highest')
                    profile['bat_average'] = stats.get('average')
                    profile['bat_strike_rate'] = stats.get('sr')
                    profile['bat_not_outs'] = stats.get('not_out')
                    profile['bat_fours'] = stats.get('fours')
                    profile['bat_sixes'] = stats.get('sixes')
                    profile['bat_ducks'] = stats.get('ducks')
                    profile['bat_fifties'] = stats.get('50s')
                    profile['bat_hundreds'] = stats.get('100s')
                    profile['bat_two_hundreds'] = stats.get('200s')
                break
        
        for fmt in ['Test', 'ODI', 'T20', 'IPL']:
            if fmt in bowling_stats and bowling_stats[fmt]:
                stats = bowling_stats[fmt]
                if not profile.get('bowl_matches'):
                    profile['bowl_matches'] = stats.get('matches')
                    profile['bowl_innings'] = stats.get('innings')
                    profile['bowl_balls'] = stats.get('balls')
                    profile['bowl_runs'] = stats.get('runs')
                    profile['bowl_maidens'] = stats.get('maidens')
                    profile['bowl_wickets'] = stats.get('wickets')
                    profile['bowl_average'] = stats.get('avg')
                    profile['bowl_economy'] = stats.get('eco')
                    profile['bowl_strike_rate'] = stats.get('sr')
                    profile['bowl_best_innings'] = stats.get('bbi')
                    profile['bowl_best_match'] = stats.get('bbm')
                    profile['bowl_four_wickets'] = stats.get('4w')
                    profile['bowl_five_wickets'] = stats.get('5w')
                    profile['bowl_ten_wickets'] = stats.get('10w')
                break
        
        logger.info(f"Scraped player profile from {player_url}: Born={profile['born']}, Role={profile['role']}")
        return profile
        
    except Exception as e:
        logger.error(f"Error scraping player profile from {player_url}: {e}")
        return None


def update_match_with_accurate_data(match_id):
    """Update match with accurate data."""
    return None


def update_match_scores(match_id):
    """Update match scores."""
    return None
