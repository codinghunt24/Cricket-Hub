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
                                'overs': all_stats[0],
                                'maidens': all_stats[1],
                                'runs': all_stats[2],
                                'wickets': all_stats[3],
                                'economy': all_stats[-1]  # Economy is always last
                            }
                            innings_data['bowling'].append(bowling_entry)
                    
                    # Extract fall of wickets from scorecard-fow-grid divs
                    fow_grids = scard_div.find_all('div', class_=re.compile(r'scorecard-fow-grid'))
                    for fow_row in fow_grids:
                        # Skip header row
                        if fow_row.find('div', string=re.compile(r'Fall of Wickets')):
                            continue
                        
                        # Find player name
                        player_link = fow_row.find('a', href=re.compile(r'/profiles/'))
                        if not player_link:
                            continue
                        
                        player_name = player_link.get_text(strip=True)
                        
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
                                'score': stats[0],  # e.g., "73-1"
                                'over': stats[1]    # e.g., "8.6"
                            }
                            innings_data['fall_of_wickets'].append(fow_entry)
            
            result['innings'].append(innings_data)
            
            # Set team scores
            if innings_num == 1 and not result['team1_score']:
                result['team1_score'] = f"{runs}/{wickets} ({overs} Ov)"
                if not result['team1']:
                    result['team1'] = team_name
            elif innings_num == 2 and not result['team2_score']:
                result['team2_score'] = f"{runs}/{wickets} ({overs} Ov)"
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
            # Check for common status patterns
            status_patterns = [
                (r'(\w+)\s+won\s+by\s+\d+\s+(runs?|wickets?)', 'Completed'),
                (r'Match\s+drawn', 'Completed'),
                (r'Match\s+tied', 'Completed'),
                (r'No\s+result', 'No Result'),
                (r'Innings\s+Break', 'Break'),
                (r'Stumps', 'Stumps'),
                (r'Tea', 'Tea'),
                (r'Lunch', 'Lunch'),
            ]
            
            for pattern, status in status_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    if status == 'Completed':
                        result['match_status'] = match.group()
                        result['result'] = match.group()
                    else:
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
