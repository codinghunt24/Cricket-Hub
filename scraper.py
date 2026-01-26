import requests
from bs4 import BeautifulSoup
import re
import time
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.cricbuzz.com"

def extract_json_from_page(html):
    """Extract embedded JSON data from Cricbuzz page (Next.js __next_f data)"""
    if not html:
        return None
    
    matches_data = []
    
    # Pattern 1: Find __next_f.push data containing matchesData
    next_f_pattern = r'self\.__next_f\.push\(\[1,"([^"]+)"\]\)'
    for match in re.finditer(next_f_pattern, html):
        try:
            encoded = match.group(1)
            # Unescape the string
            decoded = encoded.encode().decode('unicode_escape')
            
            # Find matchInfo objects
            match_info_pattern = r'"matchInfo"\s*:\s*\{[^}]+?"matchId"\s*:\s*(\d+)[^}]+?"seriesId"\s*:\s*(\d+)[^}]+?"seriesName"\s*:\s*"([^"]+)"[^}]+?"matchDesc"\s*:\s*"([^"]+)"[^}]+?"matchFormat"\s*:\s*"([^"]+)"'
            
            for info_match in re.finditer(match_info_pattern, decoded):
                match_data = {
                    'match_id': info_match.group(1),
                    'series_id': info_match.group(2),
                    'series_name': info_match.group(3),
                    'match_desc': info_match.group(4),
                    'match_format': info_match.group(5),
                }
                matches_data.append(match_data)
        except Exception as e:
            continue
    
    return matches_data


def extract_full_json_matches(html):
    """Extract complete match data from Cricbuzz JSON embedded in page"""
    if not html:
        return []
    
    all_matches = []
    
    # Find all JSON-like structures with matchInfo
    try:
        # Pattern for complete match object
        pattern = r'\{"matchInfo":\{[^}]*"matchId":(\d+).*?"matchFormat":"([^"]+)".*?\}.*?"matchScore":\{.*?\}\}'
        
        # Alternative: Extract from script tags
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string and 'matchInfo' in script.string:
                text = script.string
                
                # Find matchDetailsMap entries
                key_pattern = r'"key":"([^"]+)".*?"match":\[(.*?)\]'
                for key_match in re.finditer(key_pattern, text, re.DOTALL):
                    date_key = key_match.group(1)
                    matches_json = key_match.group(2)
                    
                    # Extract individual matches
                    match_pattern = r'"matchId":(\d+).*?"matchDesc":"([^"]+)".*?"matchFormat":"([^"]+)"'
                    for m in re.finditer(match_pattern, matches_json):
                        all_matches.append({
                            'date': date_key,
                            'match_id': m.group(1),
                            'match_desc': m.group(2),
                            'match_format': m.group(3)
                        })
    except Exception as e:
        logger.error(f"JSON extraction error: {e}")
    
    return all_matches


def scrape_matches_from_json(series_url):
    """Scrape all matches from series page using JSON extraction - POWERFUL VERSION"""
    logger.info(f"Scraping matches from JSON: {series_url}")
    
    try:
        response = requests.get(series_url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            return []
        
        html = response.text
        matches = []
        seen_ids = set()
        
        # Unescape the JSON (Cricbuzz uses \\" format)
        html_unescaped = html.replace('\\"', '"').replace('\\\\', '\\')
        
        # POWERFUL REGEX: Find all matchInfo positions and extract complete data
        # Find all matchId occurrences in matchInfo context
        match_positions = [(m.start(), m.group(1)) for m in re.finditer(r'"matchInfo"\s*:\s*\{[^}]*"matchId"\s*:\s*(\d+)', html_unescaped)]
        
        for pos, mid in match_positions:
            try:
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
                
                # Get context - but find the END of this match's block to avoid contamination
                # Look for next "matchInfo" or end of data to bound the context
                next_match = html_unescaped.find('"matchInfo"', pos + 50)
                if next_match == -1 or next_match > pos + 2500:
                    context_end = pos + 2000
                else:
                    context_end = next_match
                context = html_unescaped[pos:context_end]
                
                # Parse fields from context
                series_id = re.search(r'"seriesId"\s*:\s*(\d+)', context)
                series_name = re.search(r'"seriesName"\s*:\s*"([^"]*)"', context)
                match_desc = re.search(r'"matchDesc"\s*:\s*"([^"]*)"', context)
                match_format = re.search(r'"matchFormat"\s*:\s*"([^"]*)"', context)
                state = re.search(r'"state"\s*:\s*"([^"]*)"', context)
                status = re.search(r'"status"\s*:\s*"([^"]*)"', context)
                start_date = re.search(r'"startDate"\s*:\s*(\d+)', context)
                
                # Team info - improved patterns
                team1_name = re.search(r'"team1"\s*:\s*\{[^}]*"teamName"\s*:\s*"([^"]*)"', context)
                team1_short = re.search(r'"team1"\s*:\s*\{[^}]*"teamSName"\s*:\s*"([^"]*)"', context)
                team2_name = re.search(r'"team2"\s*:\s*\{[^}]*"teamName"\s*:\s*"([^"]*)"', context)
                team2_short = re.search(r'"team2"\s*:\s*\{[^}]*"teamSName"\s*:\s*"([^"]*)"', context)
                
                # Venue info
                venue_ground = re.search(r'"venueInfo"\s*:\s*\{[^}]*"ground"\s*:\s*"([^"]*)"', context)
                venue_city = re.search(r'"venueInfo"\s*:\s*\{[^}]*"city"\s*:\s*"([^"]*)"', context)
                
                # Check match state - normalize to our states
                raw_state = state.group(1) if state else ''
                # Normalize states: Cricbuzz uses Preview/Scheduled for upcoming
                state_map = {
                    'Live': 'Live',
                    'In Progress': 'Live',
                    'Innings Break': 'Innings Break',
                    'Stumps': 'Innings Break',
                    'Lunch': 'Innings Break',
                    'Tea': 'Innings Break',
                    'Drinks': 'Innings Break',
                    'Complete': 'Complete',
                    'Preview': 'Upcoming',
                    'Scheduled': 'Upcoming',
                    'Upcoming': 'Upcoming',
                    '': 'Upcoming'
                }
                match_state = state_map.get(raw_state, raw_state)
                team1_score = ''
                team2_score = ''
                
                # Only extract scores if match has started (Live, Innings Break, Complete)
                if match_state in ['Live', 'Innings Break', 'Complete']:
                    t1_score_block = re.search(r'"team1Score"\s*:\s*\{[^{]*"inngs1"\s*:\s*\{([^}]+)\}', context)
                    t2_score_block = re.search(r'"team2Score"\s*:\s*\{[^{]*"inngs1"\s*:\s*\{([^}]+)\}', context)
                    
                    if t1_score_block:
                        sb = t1_score_block.group(1)
                        t1_runs = re.search(r'"runs"\s*:\s*(\d+)', sb)
                        t1_wkts = re.search(r'"wickets"\s*:\s*(\d+)', sb)
                        t1_overs = re.search(r'"overs"\s*:\s*([\d.]+)', sb)
                        if t1_runs:
                            team1_score = f"{t1_runs.group(1)}/{t1_wkts.group(1) if t1_wkts else '?'}"
                            if t1_overs:
                                team1_score += f" ({t1_overs.group(1)})"
                    
                    if t2_score_block:
                        sb = t2_score_block.group(1)
                        t2_runs = re.search(r'"runs"\s*:\s*(\d+)', sb)
                        t2_wkts = re.search(r'"wickets"\s*:\s*(\d+)', sb)
                        t2_overs = re.search(r'"overs"\s*:\s*([\d.]+)', sb)
                        if t2_runs:
                            team2_score = f"{t2_runs.group(1)}/{t2_wkts.group(1) if t2_wkts else '?'}"
                            if t2_overs:
                                team2_score += f" ({t2_overs.group(1)})"
                
                # Convert timestamp to date
                match_date = ''
                if start_date:
                    try:
                        from datetime import datetime
                        ts = int(start_date.group(1)) / 1000
                        dt = datetime.fromtimestamp(ts)
                        match_date = dt.strftime('%a, %b %d, %Y')
                    except:
                        pass
                
                venue = ''
                if venue_ground and venue_city:
                    venue = f"{venue_ground.group(1)}, {venue_city.group(1)}"
                elif venue_ground:
                    venue = venue_ground.group(1)
                
                match_data = {
                    'match_id': mid,
                    'series_id': series_id.group(1) if series_id else '',
                    'series_name': series_name.group(1) if series_name else '',
                    'match_format': match_desc.group(1) if match_desc else '',
                    'format_type': match_format.group(1) if match_format else '',
                    'match_date': match_date,
                    'team1_name': team1_name.group(1) if team1_name else '',
                    'team1_short': team1_short.group(1) if team1_short else '',
                    'team1_score': team1_score,
                    'team2_name': team2_name.group(1) if team2_name else '',
                    'team2_short': team2_short.group(1) if team2_short else '',
                    'team2_score': team2_score,
                    'venue': venue,
                    'result': status.group(1) if status else '',
                    'state': match_state,
                    'match_url': f"/live-cricket-scores/{mid}"
                }
                
                matches.append(match_data)
                logger.info(f"JSON: {match_data['match_format']} | {match_data['team1_name']} vs {match_data['team2_name']} | {match_data['result']}")
            
            except Exception as e:
                continue
        
        logger.info(f"Total matches extracted from JSON: {len(matches)}")
        return matches
        
    except Exception as e:
        logger.error(f"Error scraping JSON matches: {e}")
        return []


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

TEAM_FULL_NAMES = {
    'ind': 'India', 'nz': 'New Zealand', 'aus': 'Australia',
    'eng': 'England', 'pak': 'Pakistan', 'sa': 'South Africa',
    'wi': 'West Indies', 'sl': 'Sri Lanka', 'ban': 'Bangladesh',
    'zim': 'Zimbabwe', 'afg': 'Afghanistan', 'ire': 'Ireland',
    'sco': 'Scotland', 'ned': 'Netherlands', 'uae': 'UAE',
    'oman': 'Oman', 'usa': 'USA', 'nep': 'Nepal', 'ken': 'Kenya',
    'hk': 'Hong Kong', 'nam': 'Namibia', 'can': 'Canada',
    'india': 'India', 'new zealand': 'New Zealand', 'australia': 'Australia',
    'england': 'England', 'pakistan': 'Pakistan', 'south africa': 'South Africa',
    'west indies': 'West Indies', 'sri lanka': 'Sri Lanka', 'bangladesh': 'Bangladesh',
}

TEAM_ABBREVS = {v.lower(): k for k, v in TEAM_FULL_NAMES.items() if len(k) <= 3}

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
    'all': {
        'name': 'All',
        'url': 'https://www.cricbuzz.com/cricket-schedule/series/all'
    },
    'international': {
        'name': 'International',
        'url': 'https://www.cricbuzz.com/cricket-schedule/series/international'
    },
    'domestic': {
        'name': 'Domestic',
        'url': 'https://www.cricbuzz.com/cricket-schedule/series/domestic'
    },
    'league': {
        'name': 'T20 Leagues',
        'url': 'https://www.cricbuzz.com/cricket-schedule/series/league'
    },
    'women': {
        'name': 'Women',
        'url': 'https://www.cricbuzz.com/cricket-schedule/series/women'
    }
}

def fetch_page(url, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(1)
    return None


def scrape_live_scores():
    """
    Scrape all matches from Cricbuzz live-scores page with ID verification.
    Returns matches categorized by status: Live, Innings Break, Complete, Upcoming
    """
    url = "https://www.cricbuzz.com/cricket-match/live-scores"
    html = fetch_page(url)
    if not html:
        return {'success': False, 'matches': [], 'message': 'Failed to fetch page'}
    
    soup = BeautifulSoup(html, 'html.parser')
    all_matches = []
    
    # Find all match links
    match_links = soup.find_all('a', href=re.compile(r'/live-cricket-scores/(\d+)/'))
    
    seen_ids = set()
    for link in match_links:
        href = link.get('href', '')
        title = link.get('title', '')
        
        # Extract match_id from URL - ID VERIFICATION
        match_id_match = re.search(r'/live-cricket-scores/(\d+)/', href)
        if not match_id_match:
            continue
        match_id = match_id_match.group(1)
        
        # Skip duplicates
        if match_id in seen_ids:
            continue
        seen_ids.add(match_id)
        
        # Extract series_id from URL if present
        series_id = None
        series_match = re.search(r'/cricket-series/(\d+)/', href)
        if series_match:
            series_id = series_match.group(1)
        
        # Determine match status from title attribute
        status = 'Upcoming'
        title_lower = title.lower()
        
        # Check for live indicators in title
        if ' - live' in title_lower or title_lower.endswith(' live') or '- live ' in title_lower:
            status = 'Live'
        elif 'innings break' in title_lower or 'ings break' in title_lower:
            status = 'Innings Break'
        elif 'stumps' in title_lower or 'lunch' in title_lower or 'tea' in title_lower or 'drinks' in title_lower:
            status = 'Innings Break'
        elif ' won' in title_lower or 'complete' in title_lower or ' tied' in title_lower or 'drawn' in title_lower:
            status = 'Complete'
        elif 'preview' in title_lower or 'upcoming' in title_lower or 'scheduled' in title_lower:
            status = 'Upcoming'
        elif 'need' in title_lower or 'trail' in title_lower or 'lead' in title_lower:
            # Match is in progress if there's a "need X runs" or "trail by" or "lead by"
            status = 'Live'
        
        # Also check for live tag in HTML
        has_live_tag = link.find('span', class_=re.compile(r'cbPlusLiveTag|live', re.IGNORECASE)) is not None
        if has_live_tag:
            status = 'Live'
        
        # Extract team names and match format from title
        teams = ''
        match_format = ''
        if ' - ' in title:
            parts = title.split(' - ')
            teams = parts[0].strip()
            if len(parts) > 1:
                # Status might be in the second part
                pass
        else:
            teams = title.strip()
        
        # Try to get teams from div text
        team_div = link.find('div', class_='text-white')
        if team_div:
            teams = team_div.get_text(strip=True)
        
        # Try to get match format from format div
        format_div = link.find('div', class_=re.compile(r'text-xs'))
        if format_div:
            match_format = format_div.get_text(strip=True)
        
        # Split teams
        team1 = ''
        team2 = ''
        if ' vs ' in teams:
            team_parts = teams.split(' vs ')
            team1 = team_parts[0].strip()
            team2 = team_parts[1].strip() if len(team_parts) > 1 else ''
            
            # Clean team2 - remove match format like ", 3rd T20I", ", 1st ODI", etc.
            # Pattern: team name followed by comma and match format
            format_patterns = [
                r',\s*\d+(?:st|nd|rd|th)\s+(?:T20I?|ODI|Test|T10).*$',  # ", 3rd T20I", ", 1st ODI"
                r',\s*(?:Final|Semi[- ]?[Ff]inal|Quarter[- ]?[Ff]inal).*$',  # ", Final", ", Semi-final"
                r',\s*(?:Group\s+[A-Z]|Qualifier|Play[- ]?off).*$',  # ", Group A", ", Qualifier"
                r',\s*\d+(?:st|nd|rd|th)\s+Match.*$',  # ", 16th Match"
            ]
            for pattern in format_patterns:
                team2 = re.sub(pattern, '', team2, flags=re.IGNORECASE).strip()
        
        match_data = {
            'match_id': match_id,
            'team1': team1,
            'team2': team2,
            'teams': teams,
            'match_format': match_format,
            'status': status,
            'match_url': BASE_URL + href,
            'series_id': series_id
        }
        
        all_matches.append(match_data)
    
    # Categorize matches
    live_matches = [m for m in all_matches if m['status'] == 'Live']
    innings_break = [m for m in all_matches if m['status'] == 'Innings Break']
    complete_matches = [m for m in all_matches if m['status'] == 'Complete']
    upcoming_matches = [m for m in all_matches if m['status'] == 'Upcoming']
    
    return {
        'success': True,
        'matches': all_matches,
        'live': live_matches,
        'innings_break': innings_break,
        'complete': complete_matches,
        'upcoming': upcoming_matches,
        'counts': {
            'total': len(all_matches),
            'live': len(live_matches),
            'innings_break': len(innings_break),
            'complete': len(complete_matches),
            'upcoming': len(upcoming_matches)
        }
    }


def fetch_match_detail_accurate(match_id):
    """
    Fetch accurate match details using multiple sources and techniques.
    Returns complete match data with venue, date, scores, format, result.
    """
    match_data = {
        'match_id': match_id,
        'match_format': '',
        'venue': '',
        'match_date': '',
        'team1_name': '',
        'team1_score': '',
        'team2_name': '',
        'team2_score': '',
        'result': '',
        'match_url': f"{BASE_URL}/live-cricket-scores/{match_id}",
        'status': ''
    }
    
    urls_to_try = [
        f"{BASE_URL}/live-cricket-scores/{match_id}",
        f"{BASE_URL}/live-cricket-scorecard/{match_id}",
        f"{BASE_URL}/cricket-match-live-commentary/{match_id}",
    ]
    
    html = None
    soup = None
    
    for url in urls_to_try:
        html = fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            break
    
    if not html or not soup:
        logger.error(f"Could not fetch any page for match {match_id}")
        return match_data
    
    page_text = soup.get_text(' ', strip=True)
    
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else ''
    
    title_patterns = [
        r'^([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+),\s*(\d+(?:st|nd|rd|th)\s+(?:ODI|T20I?|Test|Match))',
        r'^([A-Z]+)\s+vs\s+([A-Z]+),?\s*(\d+(?:st|nd|rd|th)\s+\w+)?',
        r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+)',
    ]
    
    for pattern in title_patterns:
        title_match = re.search(pattern, title, re.IGNORECASE)
        if title_match:
            t1 = title_match.group(1).strip()
            t2 = title_match.group(2).strip()
            match_data['team1_name'] = TEAM_FULL_NAMES.get(t1.lower(), t1)
            match_data['team2_name'] = TEAM_FULL_NAMES.get(t2.lower(), t2)
            if len(title_match.groups()) >= 3 and title_match.group(3):
                match_data['match_format'] = title_match.group(3).strip()
            break
    
    format_patterns = [
        r'(\d+(?:st|nd|rd|th))\s+(ODI|T20I?|Test|T20|Match)',
        r'(ODI|T20I|Test|T20)\s+Match',
        r'\b(Test|ODI|T20I|T20)\b',
    ]
    
    if not match_data['match_format']:
        for pattern in format_patterns:
            fmt_match = re.search(pattern, title + ' ' + page_text[:500], re.IGNORECASE)
            if fmt_match:
                if len(fmt_match.groups()) >= 2:
                    ordinal = fmt_match.group(1)
                    fmt_type = fmt_match.group(2).upper()
                    if fmt_type == 'T20':
                        fmt_type = 'T20I'
                    match_data['match_format'] = f"{ordinal} {fmt_type}"
                else:
                    match_data['match_format'] = fmt_match.group(1).upper()
                break
    
    venue_selectors = [
        ('a', {'href': lambda h: h and '/cricket-stadium/' in h}),
        ('a', {'href': lambda h: h and 'venue' in h.lower() if h else False}),
        ('div', {'class_': lambda c: c and 'venue' in ' '.join(c).lower() if c else False}),
        ('span', {'class_': lambda c: c and 'venue' in ' '.join(c).lower() if c else False}),
    ]
    
    for tag, attrs in venue_selectors:
        venue_elem = soup.find(tag, **attrs)
        if venue_elem:
            venue_text = venue_elem.get_text(strip=True)
            venue_text = re.sub(r'^at\s+', '', venue_text, flags=re.IGNORECASE)
            if venue_text and len(venue_text) > 3:
                match_data['venue'] = venue_text
                break
    
    if not match_data['venue']:
        venue_patterns = [
            r'(?:at|venue[:\s]+)\s*([A-Z][A-Za-z\s,]+(?:Stadium|Ground|Oval|Park|Arena)[A-Za-z\s,]*)',
            r'([A-Z][A-Za-z\s]+(?:International|Cricket)\s+Stadium)',
            r'([A-Z][A-Za-z\s]+,\s+[A-Z][A-Za-z]+(?:,\s+[A-Z][A-Za-z]+)?)',
        ]
        for pattern in venue_patterns:
            venue_match = re.search(pattern, page_text[:2000])
            if venue_match:
                venue = venue_match.group(1).strip()
                if len(venue) > 5 and len(venue) < 100:
                    match_data['venue'] = venue
                    break
    
    date_selectors = [
        ('span', {'class_': lambda c: c and any('date' in x.lower() for x in c) if c else False}),
        ('div', {'class_': lambda c: c and any('schedule' in x.lower() for x in c) if c else False}),
        ('time', {}),
    ]
    
    for tag, attrs in date_selectors:
        date_elem = soup.find(tag, **attrs)
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            if date_text and re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', date_text, re.IGNORECASE):
                match_data['match_date'] = date_text
                break
    
    if not match_data['match_date']:
        date_patterns = [
            r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}(?:\s+\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?(?:\s+(?:IST|GMT|LOCAL))?)?',
            r'\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?\s+\d{4}(?:\s+\d{1,2}:\d{2})?',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, page_text[:3000], re.IGNORECASE)
            if date_match:
                match_data['match_date'] = date_match.group(0).strip()
                break
    
    score_divs = soup.find_all('div', class_=lambda c: c and any(x in ' '.join(c) for x in ['cb-col-scores', 'score', 'batting-team']) if c else False)
    
    team_scores = []
    for div in score_divs:
        text = div.get_text(' ', strip=True)
        score_match = re.search(r'(\d{1,3})[-/](\d{1,2})\s*(?:\((\d+(?:\.\d+)?)\s*(?:Ov|ov)s?\))?', text)
        if score_match:
            runs = score_match.group(1)
            wickets = score_match.group(2)
            overs = score_match.group(3) or ''
            if overs:
                team_scores.append(f"{runs}/{wickets} ({overs})")
            else:
                team_scores.append(f"{runs}/{wickets}")
    
    if len(team_scores) >= 2:
        match_data['team1_score'] = team_scores[0]
        match_data['team2_score'] = team_scores[1]
    elif len(team_scores) == 1:
        match_data['team1_score'] = team_scores[0]
    
    if not match_data['team1_score']:
        score_pattern = r'(India|New Zealand|Australia|England|Pakistan|South Africa|West Indies|Sri Lanka|Bangladesh|Afghanistan|Ireland|Zimbabwe)\s*(\d{1,3})[-/](\d{1,2})\s*\((\d+(?:\.\d+)?)\s*(?:Ov|ov)s?\)'
        score_matches = re.findall(score_pattern, page_text, re.IGNORECASE)
        
        if score_matches:
            for i, (team, runs, wickets, overs) in enumerate(score_matches[:2]):
                score = f"{runs}/{wickets} ({overs})"
                team_name = TEAM_FULL_NAMES.get(team.lower(), team)
                if i == 0:
                    if not match_data['team1_name']:
                        match_data['team1_name'] = team_name
                    match_data['team1_score'] = score
                elif i == 1:
                    if not match_data['team2_name']:
                        match_data['team2_name'] = team_name
                    match_data['team2_score'] = score
    
    result_selectors = [
        ('div', {'class_': lambda c: c and any('complete' in x.lower() or 'result' in x.lower() for x in c) if c else False}),
        ('span', {'class_': lambda c: c and 'status' in ' '.join(c).lower() if c else False}),
    ]
    
    for tag, attrs in result_selectors:
        result_elem = soup.find(tag, **attrs)
        if result_elem:
            result_text = result_elem.get_text(strip=True)
            if result_text and ('won' in result_text.lower() or 'draw' in result_text.lower() or 'tie' in result_text.lower() or 'no result' in result_text.lower()):
                match_data['result'] = result_text
                break
    
    if not match_data['result']:
        result_patterns = [
            r'((?:India|New Zealand|Australia|England|Pakistan|South Africa|West Indies|Sri Lanka|Bangladesh|Afghanistan|Ireland|Zimbabwe)\s+won\s+by\s+\d+\s*(?:runs?|wkts?|wickets?))',
            r'(Match\s+(?:tied|drawn|abandoned))',
            r'(No\s+Result)',
            r'(Match\s+yet\s+to\s+begin)',
        ]
        for pattern in result_patterns:
            result_match = re.search(pattern, page_text, re.IGNORECASE)
            if result_match:
                match_data['result'] = result_match.group(1).strip()
                break
    
    if 'yet to begin' in page_text.lower() or 'match starts' in page_text.lower():
        match_data['status'] = 'Upcoming'
        if not match_data['result']:
            match_data['result'] = 'Upcoming'
    elif 'live' in page_text.lower()[:500]:
        match_data['status'] = 'Live'
    elif match_data['result']:
        match_data['status'] = 'Completed'
    
    logger.info(f"Match {match_id}: {match_data['team1_name']} vs {match_data['team2_name']} at {match_data['venue']}")
    
    return match_data


def fetch_match_from_scorecard(match_id):
    """
    Fetch match details from scorecard page - most accurate for completed matches.
    """
    match_data = {
        'match_id': match_id,
        'match_format': '',
        'venue': '',
        'match_date': '',
        'team1_name': '',
        'team1_score': '',
        'team2_name': '',
        'team2_score': '',
        'result': '',
        'match_url': f"{BASE_URL}/live-cricket-scorecard/{match_id}",
    }
    
    scorecard_url = f"{BASE_URL}/live-cricket-scorecard/{match_id}"
    html = fetch_page(scorecard_url)
    
    if not html:
        return fetch_match_detail_accurate(match_id)
    
    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text(' ', strip=True)
    
    title = soup.find('title')
    if title:
        title_text = title.get_text(strip=True)
        match = re.search(r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+),\s*(\d+(?:st|nd|rd|th)\s+\w+)', title_text)
        if match:
            match_data['team1_name'] = match.group(1).strip()
            match_data['team2_name'] = match.group(2).strip()
            match_data['match_format'] = match.group(3).strip()
    
    venue_link = soup.find('a', href=lambda h: h and '/cricket-stadium/' in h if h else False)
    if venue_link:
        match_data['venue'] = venue_link.get_text(strip=True)
    
    if not match_data['venue']:
        venue_pattern = r'at\s+([A-Za-z\s,]+(?:Stadium|Ground|Oval|Park|Arena))'
        venue_match = re.search(venue_pattern, page_text[:2000])
        if venue_match:
            match_data['venue'] = venue_match.group(1).strip()
    
    date_patterns = [
        r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}',
    ]
    for pattern in date_patterns:
        date_match = re.search(pattern, page_text[:2000], re.IGNORECASE)
        if date_match:
            match_data['match_date'] = date_match.group(0).strip()
            break
    
    innings_headers = soup.find_all('div', id=lambda x: x and x.startswith('team-') and '-innings-' in x if x else False)
    
    innings_data = []
    for header in innings_headers:
        team_div = header.find('div', class_=lambda c: c and 'font-bold' in c if c else False)
        if not team_div:
            continue
        
        team_name_raw = team_div.get_text(strip=True)
        team_name = TEAM_FULL_NAMES.get(team_name_raw.lower(), team_name_raw)
        
        score_span = header.find('span', class_=lambda c: c and 'font-bold' in c if c else False)
        total_score = score_span.get_text(strip=True).replace('-', '/') if score_span else ''
        
        overs = ''
        for span in header.find_all('span'):
            text = span.get_text(strip=True)
            if 'Ov' in text:
                overs_match = re.search(r'(\d+(?:\.\d+)?)', text)
                if overs_match:
                    overs = overs_match.group(1)
                break
        
        if team_name and team_name not in [d['team'] for d in innings_data]:
            score = f"{total_score} ({overs})" if overs else total_score
            innings_data.append({'team': team_name, 'score': score})
    
    if innings_data:
        if len(innings_data) >= 1:
            match_data['team1_name'] = innings_data[0]['team']
            match_data['team1_score'] = innings_data[0]['score']
        if len(innings_data) >= 2:
            match_data['team2_name'] = innings_data[1]['team']
            match_data['team2_score'] = innings_data[1]['score']
    
    result_patterns = [
        r'((?:India|New Zealand|Australia|England|Pakistan|South Africa|West Indies|Sri Lanka|Bangladesh|Afghanistan|Ireland|Zimbabwe)\s+won\s+by\s+\d+\s*(?:runs?|wkts?|wickets?))',
        r'(Match\s+(?:tied|drawn|abandoned))',
    ]
    for pattern in result_patterns:
        result_match = re.search(pattern, page_text, re.IGNORECASE)
        if result_match:
            match_data['result'] = result_match.group(1).strip()
            break
    
    return match_data


def update_match_with_accurate_data(match_id, existing_data=None):
    """
    Update match data with accurate information from multiple sources.
    Merges existing data with newly scraped data, preferring non-empty values.
    """
    scorecard_data = fetch_match_from_scorecard(match_id)
    live_data = fetch_match_detail_accurate(match_id)
    
    merged = {
        'match_id': match_id,
        'match_format': '',
        'venue': '',
        'match_date': '',
        'team1_name': '',
        'team1_score': '',
        'team2_name': '',
        'team2_score': '',
        'result': '',
        'match_url': f"{BASE_URL}/live-cricket-scores/{match_id}",
    }
    
    for key in merged.keys():
        for source in [scorecard_data, live_data, existing_data or {}]:
            if source and source.get(key):
                merged[key] = source[key]
                break
    
    return merged

def extract_team_id(url):
    # Match number at end of URL (with or without trailing slash)
    match = re.search(r'/(\d+)/?$', url)
    if match:
        return match.group(1)
    return None

def scrape_teams_from_category(category_url):
    teams = []
    html = fetch_page(category_url)
    if not html:
        return teams
    
    soup = BeautifulSoup(html, 'html.parser')
    
    team_links = soup.find_all('a', href=re.compile(r'/cricket-team/[^/]+/\d+'))
    
    for link in team_links:
        href = link.get('href', '')
        team_name = link.get_text(strip=True)
        
        if not team_name or len(team_name) < 2:
            continue
        
        team_url = BASE_URL + href if href.startswith('/') else href
        team_id = extract_team_id(href)
        
        img = link.find('img')
        flag_url = None
        if img and img.get('src'):
            flag_url = img['src']
            if flag_url.startswith('//'):
                flag_url = 'https:' + flag_url
            elif flag_url.startswith('/'):
                flag_url = BASE_URL + flag_url
        
        if not flag_url:
            parent = link.find_parent()
            if parent:
                img = parent.find('img')
                if img and img.get('src'):
                    flag_url = img['src']
                    if flag_url.startswith('//'):
                        flag_url = 'https:' + flag_url
        
        # ID VERIFICATION: Only add teams with valid team_id
        if not team_id:
            continue
        
        teams.append({
            'team_id': team_id,  # PRIMARY ID - Required for verification
            'name': team_name,
            'team_url': team_url,
            'flag_url': flag_url
        })
    
    # Use team_id for deduplication (more reliable than name)
    seen_ids = set()
    unique_teams = []
    for team in teams:
        if team['team_id'] not in seen_ids:
            seen_ids.add(team['team_id'])
            unique_teams.append(team)
    
    return unique_teams

def scrape_players_from_team(team_url):
    players = []
    
    players_url = team_url.rstrip('/') + '/players'
    
    html = fetch_page(players_url)
    if not html:
        html = fetch_page(team_url)
        if not html:
            return players
    
    soup = BeautifulSoup(html, 'html.parser')
    
    player_links = soup.find_all('a', href=re.compile(r'/profiles/\d+/|/cricket-player/\d+/'))
    
    for link in player_links:
        href = link.get('href', '')
        player_name = link.get_text(strip=True)
        
        if not player_name or len(player_name) < 2:
            continue
        
        player_url = BASE_URL + href if href.startswith('/') else href
        
        player_id_match = re.search(r'/profiles/(\d+)/', href)
        player_id = player_id_match.group(1) if player_id_match else None
        
        img = link.find('img')
        photo_url = None
        if img and img.get('src'):
            photo_url = img['src']
            if photo_url.startswith('//'):
                photo_url = 'https:' + photo_url
            elif photo_url.startswith('/'):
                photo_url = BASE_URL + photo_url
        
        if not photo_url:
            parent = link.find_parent()
            if parent:
                img = parent.find('img')
                if img and img.get('src'):
                    photo_url = img['src']
                    if photo_url.startswith('//'):
                        photo_url = 'https:' + photo_url
        
        role = None
        parent_div = link.find_parent('div')
        if parent_div:
            role_elem = parent_div.find(string=re.compile(r'(Batsman|Batter|Bowler|All-rounder|Allrounder|Wicketkeeper|Batting Allrounder|Bowling Allrounder|WK-Batter|Pace Bowler|Spin Bowler)', re.I))
            if role_elem:
                role = role_elem.strip()
        
        if not role:
            container = link.find_parent(['div', 'li', 'article'])
            if container:
                for elem in container.find_all(['span', 'div', 'p']):
                    text = elem.get_text(strip=True)
                    if re.match(r'^(Batsman|Batter|Bowler|All-rounder|Allrounder|Wicketkeeper|WK-Batter|Pace Bowler|Spin Bowler)$', text, re.I):
                        role = text
                        break
        
        # ID VERIFICATION: Only add players with valid player_id
        if not player_id:
            continue
        
        players.append({
            'player_id': player_id,  # PRIMARY ID - Required for verification
            'name': player_name,
            'player_url': player_url,
            'photo_url': photo_url,
            'role': role
        })
    
    # Use player_id for deduplication (more reliable than name)
    seen_ids = set()
    unique_players = []
    for player in players:
        if player['player_id'] not in seen_ids:
            seen_ids.add(player['player_id'])
            unique_players.append(player)
    
    return unique_players

def scrape_all_categories():
    results = {}
    for slug, info in CATEGORIES.items():
        print(f"Scraping {info['name']} teams...")
        teams = scrape_teams_from_category(info['url'])
        results[slug] = {
            'name': info['name'],
            'url': info['url'],
            'teams': teams
        }
        time.sleep(1)
    return results

def scrape_category(category_slug):
    if category_slug not in CATEGORIES:
        return None
    
    info = CATEGORIES[category_slug]
    teams = scrape_teams_from_category(info['url'])
    return {
        'name': info['name'],
        'url': info['url'],
        'teams': teams
    }

def scrape_player_profile(player_url):
    if not player_url:
        return None
    
    # ID VERIFICATION: Extract player_id from URL
    player_id_match = re.search(r'/profiles/(\d+)/', player_url)
    player_id = player_id_match.group(1) if player_id_match else None
    
    if not player_id:
        return None  # Reject if no valid ID
    
    full_url = player_url if player_url.startswith('http') else BASE_URL + player_url
    html = fetch_page(full_url)
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    profile = {
        'player_id': player_id  # PRIMARY ID - Required for verification
    }
    
    personal_labels = {
        'born': ['born', 'date of birth'],
        'birth_place': ['birth place', 'birthplace'],
        'nickname': ['nickname', 'also known'],
        'role': ['role'],
        'batting_style': ['batting style'],
        'bowling_style': ['bowling style']
    }
    
    for field, keywords in personal_labels.items():
        for kw in keywords:
            label_elem = soup.find('div', string=lambda t: t and kw.lower() in t.lower() if t else False)
            if label_elem:
                parent = label_elem.parent
                if parent:
                    divs = parent.find_all('div')
                    if len(divs) > 1:
                        profile[field] = divs[-1].get_text(strip=True)
                        break
    
    tables = soup.find_all('table', class_='w-full')
    
    bat_stat_aliases = {
        'matches': 'matches', 'innings': 'innings', 'runs': 'runs', 'balls': 'balls',
        'highest': 'highest', 'average': 'average', 'avg': 'average',
        'strike rate': 'strike rate', 'sr': 'strike rate',
        'not outs': 'not outs', 'not out': 'not outs',
        '4s': '4s', 'fours': '4s', '6s': '6s', 'sixes': '6s',
        'ducks': 'ducks', '50s': '50s', '100s': '100s', '200s': '200s'
    }
    bowl_stat_aliases = {
        'matches': 'matches', 'innings': 'innings', 'balls': 'balls', 'runs': 'runs',
        'maidens': 'maidens', 'wickets': 'wickets',
        'average': 'average', 'avg': 'average',
        'economy': 'economy', 'eco': 'economy',
        'strike rate': 'strike rate', 'sr': 'strike rate',
        'bbi': 'bbi', 'bbm': 'bbm', '4w': '4w', '5w': '5w', '10w': '10w'
    }
    
    bat_stats_map = {
        'matches': 'bat_matches',
        'innings': 'bat_innings',
        'runs': 'bat_runs',
        'balls': 'bat_balls',
        'highest': 'bat_highest',
        'average': 'bat_average',
        'strike rate': 'bat_strike_rate',
        'not outs': 'bat_not_outs',
        '4s': 'bat_fours',
        '6s': 'bat_sixes',
        'ducks': 'bat_ducks',
        '50s': 'bat_fifties',
        '100s': 'bat_hundreds',
        '200s': 'bat_two_hundreds'
    }
    
    bowl_stats_map = {
        'matches': 'bowl_matches',
        'innings': 'bowl_innings',
        'balls': 'bowl_balls',
        'runs': 'bowl_runs',
        'maidens': 'bowl_maidens',
        'wickets': 'bowl_wickets',
        'average': 'bowl_average',
        'economy': 'bowl_economy',
        'strike rate': 'bowl_strike_rate',
        'bbi': 'bowl_best_innings',
        'bbm': 'bowl_best_match',
        '4w': 'bowl_four_wickets',
        '5w': 'bowl_five_wickets',
        '10w': 'bowl_ten_wickets'
    }
    
    batting_stats = {'test': {}, 'odi': {}, 't20': {}, 'ipl': {}}
    bowling_stats = {'test': {}, 'odi': {}, 't20': {}, 'ipl': {}}
    
    format_map = {'test': 'test', 'odi': 'odi', 't20': 't20', 'ipl': 'ipl', 't20i': 't20'}
    
    for table_idx, table in enumerate(tables):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
        
        if not headers or ('test' not in headers and 'odi' not in headers and 't20' not in headers):
            continue
        
        format_indices = {}
        for i, h in enumerate(headers):
            for fmt_key, fmt_name in format_map.items():
                if fmt_key == h:
                    format_indices[fmt_name] = i
        
        is_batting = table_idx == 2 or (len(tables) > 2 and table == tables[2])
        is_bowling = table_idx == 3 or (len(tables) > 3 and table == tables[3])
        
        if is_batting:
            stats_map = bat_stats_map
            stats_dict = batting_stats
            stat_aliases = bat_stat_aliases
        elif is_bowling:
            stats_map = bowl_stats_map
            stats_dict = bowling_stats
            stat_aliases = bowl_stat_aliases
        else:
            continue
        
        odi_idx = format_indices.get('odi', format_indices.get('t20', 1))
        
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            
            stat_name = cells[0].get_text(strip=True).lower()
            
            normalized_key = stat_aliases.get(stat_name)
            if normalized_key:
                for fmt, idx in format_indices.items():
                    if idx < len(cells):
                        value = cells[idx].get_text(strip=True)
                        if value and value != '-':
                            stats_dict[fmt][normalized_key] = value
                
                if normalized_key in stats_map:
                    if odi_idx < len(cells):
                        profile[stats_map[normalized_key]] = cells[odi_idx].get_text(strip=True)
    
    profile['batting_stats'] = batting_stats
    profile['bowling_stats'] = bowling_stats
    
    career_timeline = {}
    timeline_heading = soup.find(string=lambda t: t and 'Career Timeline' in t if t else False)
    if timeline_heading:
        section = timeline_heading.find_parent('div')
        if section:
            parent = section.find_parent('div')
            if parent:
                grandparent = parent.find_parent('div')
                if grandparent:
                    for child in grandparent.find_all('div', recursive=False):
                        divs = child.find_all('div', recursive=False)
                        for div in divs:
                            text = div.get_text(separator=' | ', strip=True)
                            if 'vs' in text and ' | ' in text:
                                parts = text.split(' | ')
                                if len(parts) >= 3:
                                    format_name = parts[0].strip().lower()
                                    debut = parts[1].strip()
                                    last_match = parts[2].strip()
                                    career_timeline[format_name] = {
                                        'debut': debut,
                                        'last_match': last_match
                                    }
    
    profile['career_timeline'] = career_timeline
    
    return profile

def extract_series_id(url):
    match = re.search(r'/cricket-series/(\d+)/', url)
    if match:
        return match.group(1)
    return None

def parse_series_date(name):
    months = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }
    
    date_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{1,2})'
    year_pattern = r'(\d{4})'
    
    year_match = re.search(year_pattern, name)
    year = year_match.group(1) if year_match else '2026'
    
    date_match = re.search(date_pattern, name)
    if date_match:
        month = months.get(date_match.group(1), '01')
        day = date_match.group(2).zfill(2)
        return f"{year}-{month}-{day}"
    
    return None

def parse_dates_from_title(title):
    months = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
        'Sep': '09', 'Sept': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }
    
    date_pattern = r'(\d{1,2})\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s*(\d{4})'
    matches = re.findall(date_pattern, title)
    
    start_date = None
    end_date = None
    
    if len(matches) >= 1:
        day, month, year = matches[0]
        start_date = f"{year}-{months.get(month, '01')}-{day.zfill(2)}"
    
    if len(matches) >= 2:
        day, month, year = matches[1]
        end_date = f"{year}-{months.get(month, '01')}-{day.zfill(2)}"
    
    return start_date, end_date

def extract_date_range(link):
    date_div = link.find('div', class_='text-cbTxtSec')
    if date_div:
        text = date_div.get_text(strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text
    return None

def scrape_series_from_category(category_url):
    series_list = []
    html = fetch_page(category_url)
    
    if not html:
        return series_list
    
    soup = BeautifulSoup(html, 'html.parser')
    
    series_links = soup.find_all('a', class_='flex justify-between items-center', href=lambda h: h and '/cricket-series/' in h and '/matches' in h)
    
    seen_ids = set()
    for link in series_links:
        href = link.get('href', '')
        series_id = extract_series_id(href)
        
        if not series_id or series_id in seen_ids:
            continue
        
        seen_ids.add(series_id)
        
        name_div = link.find('div', class_='text-ellipsis')
        name = name_div.get_text(strip=True) if name_div else ''
        
        if not name or len(name) < 3:
            continue
        
        title = link.get('title', '')
        start_date, end_date = parse_dates_from_title(title)
        date_range = extract_date_range(link)
        
        clean_href = href.replace('/matches', '')
        series_url = BASE_URL + clean_href if clean_href.startswith('/') else clean_href
        
        series_list.append({
            'series_id': series_id,
            'name': name,
            'series_url': series_url,
            'start_date': start_date,
            'end_date': end_date,
            'date_range': date_range
        })
    
    return series_list

def fetch_accurate_match_data(match_id, match_url_hint=None):
    """
    Fetch accurate match data from Cricbuzz match page.
    Uses multiple page sources for complete data extraction.
    All IDs are extracted for verification.
    """
    match_data = {
        # PRIMARY IDs - Required for verification
        'match_id': match_id,
        'series_id': '',
        'team1_id': '',
        'team2_id': '',
        'venue_id': '',
        # Match info
        'match_format': '',
        'venue': '',
        'match_date': '',
        'state': '',
        # Team data
        'team1_name': '',
        'team1_score': '',
        'team2_name': '',
        'team2_score': '',
        # Result
        'result': '',
        'match_url': match_url_hint or f"{BASE_URL}/live-cricket-scores/{match_id}",
    }
    
    team_abbrevs = {
        'ind': 'India', 'nz': 'New Zealand', 'aus': 'Australia',
        'eng': 'England', 'pak': 'Pakistan', 'sa': 'South Africa',
        'wi': 'West Indies', 'sl': 'Sri Lanka', 'ban': 'Bangladesh',
        'zim': 'Zimbabwe', 'afg': 'Afghanistan', 'ire': 'Ireland',
        'sco': 'Scotland', 'ned': 'Netherlands', 'uae': 'UAE',
        'oman': 'Oman', 'usa': 'USA', 'nep': 'Nepal'
    }
    
    if match_url_hint:
        team_match = re.search(r'/(\w+)-vs-(\w+)-(\d+(?:st|nd|rd|th)-(?:odi|t20i?|test))', match_url_hint, re.IGNORECASE)
        if team_match:
            t1 = team_match.group(1).lower()
            t2 = team_match.group(2).lower()
            fmt = team_match.group(3)
            match_data['team1_name'] = team_abbrevs.get(t1, t1.title())
            match_data['team2_name'] = team_abbrevs.get(t2, t2.title())
            match_data['match_format'] = fmt.replace('-', ' ').title()
    
    urls_to_try = [
        f"{BASE_URL}/live-cricket-scorecard/{match_id}",
        f"{BASE_URL}/live-cricket-scores/{match_id}",
    ]
    
    html = None
    soup = None
    
    for url in urls_to_try:
        html = fetch_page(url)
        if html and len(html) > 5000:
            soup = BeautifulSoup(html, 'html.parser')
            break
    
    if not html or not soup:
        logger.warning(f"Could not fetch match {match_id}")
        return match_data
    
    # ID EXTRACTION from embedded JSON data
    # Extract series_id
    series_id_match = re.search(r'"seriesId"\s*:\s*(\d+)', html)
    if series_id_match:
        match_data['series_id'] = series_id_match.group(1)
    
    # Extract team IDs from matchHeader
    team1_id_match = re.search(r'"team1"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', html)
    team2_id_match = re.search(r'"team2"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', html)
    if team1_id_match:
        match_data['team1_id'] = team1_id_match.group(1)
    if team2_id_match:
        match_data['team2_id'] = team2_id_match.group(1)
    
    # Extract venue_id
    venue_id_match = re.search(r'"venueInfo"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', html)
    if venue_id_match:
        match_data['venue_id'] = venue_id_match.group(1)
    
    # Extract match state
    state_match = re.search(r'"state"\s*:\s*"([^"]*)"', html)
    if state_match:
        match_data['state'] = state_match.group(1)
    
    # ID VERIFICATION: Verify match_id matches page content
    page_match_id = re.search(r'"matchId"\s*:\s*(\d+)', html)
    if page_match_id and page_match_id.group(1) != str(match_id):
        logger.warning(f"Match ID mismatch: requested {match_id}, page has {page_match_id.group(1)}")
        # Update to correct match_id from page
        match_data['match_id'] = page_match_id.group(1)
    
    page_text = soup.get_text(' ', strip=True)
    
    og_title = soup.find('meta', {'property': 'og:title'})
    og_content = og_title.get('content', '') if og_title else ''
    
    if og_content:
        meta_score = re.search(r'([A-Z]+)\s+(\d+/\d+)\s*\((\d+(?:\.\d+)?)\)\s*vs\s*([A-Z]+)\s+(\d+/\d+)', og_content, re.IGNORECASE)
        if meta_score:
            t1_abbr = meta_score.group(1).lower()
            t1_score = meta_score.group(2)
            t1_overs = meta_score.group(3)
            t2_abbr = meta_score.group(4).lower()
            t2_score = meta_score.group(5)
            
            match_data['team1_name'] = team_abbrevs.get(t1_abbr, t1_abbr.upper())
            match_data['team1_score'] = f"{t1_score} ({t1_overs})"
            match_data['team2_name'] = team_abbrevs.get(t2_abbr, t2_abbr.upper())
            
            t2_overs_match = re.search(rf'{t2_abbr}\s+{re.escape(t2_score)}\s*\((\d+(?:\.\d+)?)\)', og_content, re.IGNORECASE)
            if t2_overs_match:
                match_data['team2_score'] = f"{t2_score} ({t2_overs_match.group(1)})"
            else:
                match_data['team2_score'] = t2_score
        
        date_in_meta = re.search(r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2})', og_content)
        if date_in_meta:
            match_data['match_date'] = date_in_meta.group(1) + ', 2026'
        
        format_in_meta = re.search(r'(\d+(?:st|nd|rd|th)\s+(?:ODI|T20I?|Test))', og_content, re.IGNORECASE)
        if format_in_meta:
            match_data['match_format'] = format_in_meta.group(1)
    
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else ''
    
    title_match = re.search(r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+),\s*(\d+(?:st|nd|rd|th)\s+(?:ODI|T20I?|Test))', title, re.IGNORECASE)
    if title_match:
        if not match_data['team1_name']:
            t1 = title_match.group(1).strip()
            match_data['team1_name'] = TEAM_FULL_NAMES.get(t1.lower(), t1)
        if not match_data['team2_name']:
            t2 = title_match.group(2).strip()
            match_data['team2_name'] = TEAM_FULL_NAMES.get(t2.lower(), t2)
        if not match_data['match_format']:
            match_data['match_format'] = title_match.group(3).strip()
    
    venue_link = soup.find('a', href=lambda h: h and '/cricket-stadium/' in h if h else False)
    if venue_link:
        venue_text = venue_link.get_text(strip=True)
        parent = venue_link.find_parent()
        if parent:
            full_venue = parent.get_text(strip=True)
            if ',' in full_venue and len(full_venue) < 100:
                match_data['venue'] = full_venue
            else:
                match_data['venue'] = venue_text
        else:
            match_data['venue'] = venue_text
    
    if not match_data['venue']:
        venue_patterns = [
            r'(?:at\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z][A-Za-z\s]+(?:Stadium|Ground|Oval|Park|Arena))',
            r'([A-Z][A-Za-z\s]+(?:Stadium|Ground|Oval|Park|Arena)),\s*([A-Z][a-z]+)',
        ]
        for pattern in venue_patterns:
            venue_match = re.search(pattern, page_text[:3000])
            if venue_match:
                match_data['venue'] = f"{venue_match.group(1)}, {venue_match.group(2)}"
                break
    
    if not match_data['match_date']:
        date_patterns = [
            r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4})',
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4})',
            r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2})',
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, page_text[:5000], re.IGNORECASE)
            if date_match:
                date_str = date_match.group(1).strip()
                if not re.search(r'\d{4}', date_str):
                    date_str = date_str + ', 2026'
                match_data['match_date'] = date_str
                break
    
    innings_headers = soup.find_all('div', id=lambda x: x and x.startswith('team-') and '-innings-' in x if x else False)
    
    innings_data = []
    seen_teams = set()
    
    for header in innings_headers:
        team_div = header.find('div', class_=lambda c: c and ('font-bold' in c or 'cb-font-bold' in c) if c else False)
        if not team_div:
            continue
        
        team_name_raw = team_div.get_text(strip=True)
        if not team_name_raw or team_name_raw in seen_teams:
            continue
        seen_teams.add(team_name_raw)
        
        team_name = TEAM_FULL_NAMES.get(team_name_raw.lower(), team_name_raw)
        
        score_span = header.find('span', class_=lambda c: c and ('font-bold' in c or 'cb-font-bold' in c) if c else False)
        total_score = ''
        if score_span:
            score_text = score_span.get_text(strip=True)
            total_score = score_text.replace('-', '/')
        
        overs = ''
        for span in header.find_all('span'):
            text = span.get_text(strip=True)
            if 'Ov' in text:
                overs_match = re.search(r'(\d+(?:\.\d+)?)', text)
                if overs_match:
                    overs = overs_match.group(1)
                break
        
        if total_score:
            score_with_overs = f"{total_score} ({overs})" if overs else total_score
            innings_data.append({'team': team_name, 'score': score_with_overs, 'overs': overs})
    
    if innings_data:
        if len(innings_data) >= 1:
            match_data['team1_name'] = innings_data[0]['team']
            match_data['team1_score'] = innings_data[0]['score']
        if len(innings_data) >= 2:
            match_data['team2_name'] = innings_data[1]['team']
            match_data['team2_score'] = innings_data[1]['score']
    
    if not match_data['team1_score']:
        score_pattern = r'(New Zealand|India|Australia|England|Pakistan|South Africa|West Indies|Sri Lanka|Bangladesh|Afghanistan|Ireland|Zimbabwe|NZ|IND|AUS|ENG|PAK|SA|WI|SL|BAN|AFG)\s*(\d{1,3})[-/](\d{1,2})\s*\((\d+(?:\.\d+)?)\s*(?:Ov|ov)s?\)'
        score_matches = re.findall(score_pattern, page_text, re.IGNORECASE)
        
        for i, (team, runs, wickets, overs) in enumerate(score_matches[:2]):
            score = f"{runs}/{wickets} ({overs})"
            team_name = TEAM_FULL_NAMES.get(team.lower(), team)
            if i == 0:
                if not match_data['team1_name']:
                    match_data['team1_name'] = team_name
                match_data['team1_score'] = score
            elif i == 1:
                if not match_data['team2_name']:
                    match_data['team2_name'] = team_name
                match_data['team2_score'] = score
    
    result_patterns = [
        r'((?:India|New Zealand|Australia|England|Pakistan|South Africa|West Indies|Sri Lanka|Bangladesh|Afghanistan|Ireland|Zimbabwe)\s+won\s+by\s+\d+\s*(?:runs?|wkts?|wickets?))',
        r'(Match\s+(?:tied|drawn|abandoned))',
        r'(No\s+Result)',
    ]
    for pattern in result_patterns:
        result_match = re.search(pattern, page_text, re.IGNORECASE)
        if result_match:
            match_data['result'] = result_match.group(1).strip()
            break
    
    if not match_data['result']:
        result_div = soup.find('div', class_=lambda c: c and ('cb-text-complete' in c or 'cb-text-live' in c) if c else False)
        if result_div:
            match_data['result'] = result_div.get_text(strip=True)
    
    if 'yet to begin' in page_text.lower() or 'starts at' in page_text.lower():
        if not match_data['result']:
            match_data['result'] = 'Upcoming'
    
    logger.info(f"Match {match_id}: {match_data['team1_name']} {match_data['team1_score']} vs {match_data['team2_name']} {match_data['team2_score']} | {match_data['result']}")
    
    return match_data


def scrape_matches_from_series(series_url):
    """
    Scrape all matches from a series with accurate data.
    Fetches each match page individually for complete accuracy.
    """
    matches_list = []
    matches_url = series_url.rstrip('/') + '/matches'
    
    series_slug_match = re.search(r'/cricket-series/\d+/([^/]+)', series_url)
    series_slug = series_slug_match.group(1) if series_slug_match else ''
    
    urls_to_try = [matches_url, series_url.rstrip('/')]
    html = None
    
    for url in urls_to_try:
        html = fetch_page(url)
        if html and '/live-cricket-scores/' in html:
            break
    
    if not html:
        return matches_list
    
    soup = BeautifulSoup(html, 'html.parser')
    
    all_links = soup.find_all('a', href=lambda h: h and '/live-cricket-scores/' in h)
    
    if series_slug:
        country_abbrevs = {
            'new-zealand': 'nz', 'india': 'ind', 'australia': 'aus', 
            'england': 'eng', 'pakistan': 'pak', 'south-africa': 'sa',
            'west-indies': 'wi', 'sri-lanka': 'sl', 'bangladesh': 'ban'
        }
        slug_lower = series_slug.lower()
        short_slugs = [series_slug]
        temp_slug = slug_lower
        for full, abbrev in country_abbrevs.items():
            temp_slug = temp_slug.replace(full, abbrev)
        short_slugs.append(temp_slug)
        short_slugs.append(slug_lower.replace('-2026', '').replace('-2025', ''))
        short_slugs.append(temp_slug.replace('-2026', '').replace('-2025', ''))
        
        match_links = [m for m in all_links if any(s in m.get('href', '').lower() for s in short_slugs if len(s) > 5)]
    else:
        match_links = all_links
    
    seen_ids = set()
    match_urls = []
    
    for link in match_links:
        href = link.get('href', '')
        match_id_match = re.search(r'/live-cricket-scores/(\d+)/', href)
        if not match_id_match:
            continue
        
        match_id = match_id_match.group(1)
        if match_id in seen_ids:
            continue
        seen_ids.add(match_id)
        
        match_url = BASE_URL + href if href.startswith('/') else href
        match_urls.append((match_id, match_url))
    
    logger.info(f"Found {len(match_urls)} matches in series")
    
    for match_id, match_url in match_urls:
        match_data = fetch_accurate_match_data(match_id, match_url)
        match_data['match_url'] = match_url
        matches_list.append(match_data)
        time.sleep(0.5)
    
    return matches_list


def scrape_matches_from_series_old(series_url):
    matches_list = []
    matches_url = series_url.rstrip('/') + '/matches'
    
    series_slug_match = re.search(r'/cricket-series/\d+/([^/]+)', series_url)
    series_slug = series_slug_match.group(1) if series_slug_match else ''
    
    urls_to_try = [matches_url, series_url.rstrip('/')]
    html = None
    
    for url in urls_to_try:
        html = fetch_page(url)
        if html:
            if series_slug:
                series_match_pattern = rf'/live-cricket-scores/\d+/[^"]*{re.escape(series_slug)}[^"]*'
                if re.search(series_match_pattern, html, re.IGNORECASE):
                    break
            else:
                if '/live-cricket-scores/' in html:
                    break
    
    if not html:
        return matches_list
    
    soup = BeautifulSoup(html, 'html.parser')
    
    current_date = None
    
    all_match_ids = set(re.findall(r'/live-cricket-scores/(\d+)/', html))
    
    series_id_match = re.search(r'/cricket-series/(\d+)/', series_url)
    if series_id_match:
        series_num = series_id_match.group(1)
        bare_ids = re.findall(r'\b(12\d{4})\b', html)
        for bid in bare_ids:
            all_match_ids.add(bid)
    
    all_links = soup.find_all('a', href=lambda h: h and '/live-cricket-scores/' in h)
    
    if series_slug:
        country_abbrevs = {
            'new-zealand': 'nz', 'india': 'ind', 'australia': 'aus', 
            'england': 'eng', 'pakistan': 'pak', 'south-africa': 'sa',
            'west-indies': 'wi', 'sri-lanka': 'sl', 'bangladesh': 'ban'
        }
        slug_lower = series_slug.lower()
        short_slugs = [series_slug]
        temp_slug = slug_lower
        for full, abbrev in country_abbrevs.items():
            temp_slug = temp_slug.replace(full, abbrev)
        short_slugs.append(temp_slug)
        short_slugs.append(slug_lower.replace('-2026', '').replace('-2025', ''))
        short_slugs.append(temp_slug.replace('-2026', '').replace('-2025', ''))
        parts = series_slug.split('-')
        if len(parts) >= 4:
            short_slugs.append('-'.join(parts[:4]))
        
        match_links = [m for m in all_links if any(s in m.get('href', '').lower() for s in short_slugs if len(s) > 5)]
    else:
        match_links = all_links
    
    seen_ids = set()
    for link in match_links:
        href = link.get('href', '')
        
        match_id_match = re.search(r'/live-cricket-scores/(\d+)/', href)
        if not match_id_match:
            continue
        
        match_id = match_id_match.group(1)
        
        if match_id in seen_ids:
            continue
        seen_ids.add(match_id)
        
        parent = link.find_parent('div', class_=lambda c: c and 'cb-col-100' in c)
        if not parent:
            parent = link.parent
        
        date_header = None
        prev = link.find_previous(['div', 'h3', 'span'], string=re.compile(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+\w+\s+\d+\s+\d{4}'))
        if prev:
            date_header = prev.get_text(strip=True)
        
        if date_header:
            current_date = date_header
        
        text = link.get_text(' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        
        match_format = ''
        venue = ''
        team1_name = ''
        team1_score = ''
        team2_name = ''
        team2_score = ''
        result = ''
        match_date = current_date
        
        url_format = re.search(r'/(\d+(?:st|nd|rd|th))-(\w+)', href, re.IGNORECASE)
        if url_format:
            ordinal = url_format.group(1).lower()
            format_type = url_format.group(2).upper()
            if format_type == 'T20':
                format_type = 'T20I'
            match_format = f"{ordinal} {format_type}"
        
        team_abbrevs = {
            'ind': 'India', 'nz': 'New Zealand', 'aus': 'Australia',
            'eng': 'England', 'pak': 'Pakistan', 'sa': 'South Africa',
            'wi': 'West Indies', 'sl': 'Sri Lanka', 'ban': 'Bangladesh',
            'zim': 'Zimbabwe', 'afg': 'Afghanistan', 'ire': 'Ireland'
        }
        team_match = re.search(r'/live-cricket-scores/\d+/([a-z]+)-vs-([a-z]+)', href, re.IGNORECASE)
        if team_match:
            t1_abbrev = team_match.group(1).lower()
            t2_abbrev = team_match.group(2).lower()
            team1_name = team_abbrevs.get(t1_abbrev, t1_abbrev.upper())
            team2_name = team_abbrevs.get(t2_abbrev, t2_abbrev.upper())
        else:
            # Extract from series slug (e.g., england-tour-of-sri-lanka-2026)
            tour_match = re.search(r'(england|india|australia|new-zealand|pakistan|south-africa|west-indies|sri-lanka|bangladesh)-tour-of-(england|india|australia|new-zealand|pakistan|south-africa|west-indies|sri-lanka|bangladesh)', href, re.IGNORECASE)
            if tour_match:
                touring = tour_match.group(1).replace('-', ' ').title()
                host = tour_match.group(2).replace('-', ' ').title()
                team1_name = host
                team2_name = touring
        
        # Extract scores from text (pattern: XXX/Y (overs))
        score_matches = re.findall(r'([A-Z]+)\s+(\d+(?:/\d+)?)\s*\((\d+(?:\.\d+)?)\)', text, re.IGNORECASE)
        if len(score_matches) >= 2:
            team1_score = f"{score_matches[0][1]} ({score_matches[0][2]})"
            team2_score = f"{score_matches[1][1]} ({score_matches[1][2]})"
        elif len(score_matches) == 1:
            team1_score = f"{score_matches[0][1]} ({score_matches[0][2]})"
        
        # Extract result
        result_match = re.search(r'((?:India|New Zealand|Australia|England|Pakistan|South Africa|Sri Lanka|Bangladesh|West Indies|Afghanistan|Zimbabwe|Ireland)\s+won\s+by\s+\d+\s*(?:runs?|wkts?|wickets?))', text, re.IGNORECASE)
        if result_match:
            result = result_match.group(1).strip()
        
        # Extract match date from text
        date_match = re.search(r'Match starts at\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+,?\s*\d*:?\d*\s*(?:GMT|IST)?)', text, re.IGNORECASE)
        if date_match:
            match_date = date_match.group(1).strip()
            result = 'Upcoming'  # Future match
        
        match_url = BASE_URL + href if href.startswith('/') else href
        
        matches_list.append({
            'match_id': match_id,
            'match_format': match_format,
            'venue': venue,
            'match_date': match_date,
            'team1_name': team1_name,
            'team1_score': team1_score,
            'team2_name': team2_name,
            'team2_score': team2_score,
            'result': result,
            'match_url': match_url
        })
    
    # Now fetch details for match IDs found in source but not in anchor tags
    # Only process IDs that look like they belong to this series (within a reasonable ID range)
    if seen_ids:
        min_id = min(int(m) for m in seen_ids)
        max_id = max(int(m) for m in seen_ids)
        id_range = max_id - min_id + 100  # Allow some buffer
    else:
        min_id = 0
        max_id = 999999999
        id_range = 100
    
    for match_id in all_match_ids:
        if match_id in seen_ids:
            continue
        
        # Only fetch if ID is within reasonable range of known series matches
        match_id_int = int(match_id)
        if seen_ids and (match_id_int < min_id - 100 or match_id_int > max_id + 100):
            continue
        
        # Fetch the match page to get details
        match_page_url = f"{BASE_URL}/live-cricket-scores/{match_id}/"
        match_html = fetch_page(match_page_url)
        if not match_html:
            continue
        
        match_soup = BeautifulSoup(match_html, 'html.parser')
        
        # Strict check: match page must contain exact series slug in a link
        series_link = match_soup.find('a', href=lambda h: h and series_slug in h.lower() if series_slug else False)
        if not series_link and series_slug:
            continue
        
        seen_ids.add(match_id)
        
        # Extract match info from page
        title_tag = match_soup.find('title')
        title = title_tag.get_text() if title_tag else ''
        
        team1_name = ''
        team2_name = ''
        match_format = ''
        venue = ''
        result = ''
        team1_score = ''
        team2_score = ''
        
        # Parse title: "India vs New Zealand, 1st ODI, New Zealand tour of India, 2026"
        title_match = re.search(r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+),\s*(\d+(?:st|nd|rd|th)\s+(?:ODI|T20I|Test|T20))', title)
        if title_match:
            team1_name = title_match.group(1).strip()
            team2_name = title_match.group(2).strip()
            match_format = title_match.group(3).strip()
        else:
            # Try alternate pattern
            alt_match = re.search(r'([A-Z]+)\s+vs\s+([A-Z]+)', title)
            if alt_match:
                team1_name = alt_match.group(1)
                team2_name = alt_match.group(2)
            format_match = re.search(r'(\d+(?:st|nd|rd|th)\s+(?:ODI|T20I|Test|T20|Match))', title)
            if format_match:
                match_format = format_match.group(1)
        
        # Get venue
        venue_div = match_soup.find('a', href=lambda h: h and '/cricket-stadium' in h if h else False)
        if venue_div:
            venue = venue_div.get_text(strip=True)
        
        # Get match date from page
        match_date = None
        date_patterns = [
            r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,?\s+\d{4})?(?:\s+\d{1,2}:\d{2}\s*(?:GMT|IST|Local)?)?',
        ]
        page_text = match_soup.get_text()
        for pattern in date_patterns:
            date_match = re.search(pattern, page_text)
            if date_match:
                match_date = date_match.group(0).strip()
                # Clean up the date
                match_date = re.sub(r',\s*New Zealand.*$', '', match_date)
                break
        
        # Get scores - try multiple patterns
        score_divs = match_soup.find_all('div', class_=lambda c: c and 'cb-col-scores' in c)
        for i, score_div in enumerate(score_divs[:2]):
            score_text = score_div.get_text(strip=True)
            if i == 0:
                team1_score = score_text
            else:
                team2_score = score_text
        
        # If no scores found, try extracting from page text
        if not team1_score or not team2_score:
            # Look for score pattern like "300-8 (50)" or "306/6 (49)"
            score_pattern = re.findall(r'(\d{1,3}(?:-|/)\d{1,2})\s*\((\d{1,2}(?:\.\d)?)\)', page_text)
            if len(score_pattern) >= 2:
                team1_score = f"{score_pattern[0][0]} ({score_pattern[0][1]})"
                team2_score = f"{score_pattern[1][0]} ({score_pattern[1][1]})"
            elif len(score_pattern) == 1:
                team1_score = f"{score_pattern[0][0]} ({score_pattern[0][1]})"
        
        # Try to find innings scores with team names
        if not team1_score or not team2_score:
            innings_pattern = re.findall(r'(India|New Zealand|Australia|England|Pakistan|South Africa|West Indies|Sri Lanka|Bangladesh)\s*(\d{1,3}(?:-|/)\d{1,2})\s*\((\d{1,2}(?:\.\d)?)\s*(?:Ovs?|overs?)?\)', page_text, re.IGNORECASE)
            for team, runs, overs in innings_pattern:
                score = f"{runs} ({overs})"
                if team.lower() == team1_name.lower():
                    team1_score = score
                elif team.lower() == team2_name.lower():
                    team2_score = score
        
        # Get result - try multiple patterns
        result_div = match_soup.find('div', class_=lambda c: c and 'cb-text-complete' in c)
        if result_div:
            result = result_div.get_text(strip=True)
        
        if not result:
            # Try to find result in page text
            result_patterns = [
                r'((?:India|New Zealand|Australia|England|Pakistan|South Africa|West Indies|Sri Lanka|Bangladesh|Afghanistan|Zimbabwe|Ireland)\s+won\s+by\s+\d+\s*(?:runs?|wkts?|wickets?))',
                r'(Match\s+(?:tied|drawn|abandoned))',
                r'(No\s+Result)',
            ]
            for pattern in result_patterns:
                result_match = re.search(pattern, page_text, re.IGNORECASE)
                if result_match:
                    result = result_match.group(1).strip()
                    break
        
        match_url = match_page_url
        
        matches_list.append({
            'match_id': match_id,
            'match_format': match_format,
            'venue': venue,
            'match_date': None,
            'team1_name': team1_name,
            'team1_score': team1_score,
            'team2_name': team2_name,
            'team2_score': team2_score,
            'result': result,
            'match_url': match_url
        })
    
    return matches_list


def scrape_scorecard(match_id):
    scorecard_url = f"https://www.cricbuzz.com/live-cricket-scorecard/{match_id}"
    html = fetch_page(scorecard_url)
    
    if not html:
        return None
    
    # ID VERIFICATION: Verify match_id from page content
    page_match_id = re.search(r'"matchId"\s*:\s*(\d+)', html)
    verified_match_id = page_match_id.group(1) if page_match_id else str(match_id)
    
    if page_match_id and page_match_id.group(1) != str(match_id):
        logger.warning(f"Scorecard ID mismatch: requested {match_id}, page has {page_match_id.group(1)}")
    
    # Extract all IDs from page
    series_id_match = re.search(r'"seriesId"\s*:\s*(\d+)', html)
    team1_id_match = re.search(r'"team1"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', html)
    team2_id_match = re.search(r'"team2"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', html)
    venue_id_match = re.search(r'"venueInfo"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', html)
    
    soup = BeautifulSoup(html, 'html.parser')
    scorecard = {
        # PRIMARY IDs - Required for verification
        'match_id': verified_match_id,
        'series_id': series_id_match.group(1) if series_id_match else '',
        'team1_id': team1_id_match.group(1) if team1_id_match else '',
        'team2_id': team2_id_match.group(1) if team2_id_match else '',
        'venue_id': venue_id_match.group(1) if venue_id_match else '',
        # Scorecard data
        'innings': [],
        'venue': '',
        'match_date': ''
    }
    
    venue_link = soup.find('a', href=lambda h: h and '/cricket-series/' in h and '/venues/' in h)
    if venue_link:
        scorecard['venue'] = venue_link.get_text(strip=True)
    else:
        at_span = soup.find('span', string=lambda s: s and 'at ' in s if s else False)
        if at_span:
            scorecard['venue'] = at_span.get_text(strip=True).replace('at ', '')
    
    date_span = soup.find('span', class_=lambda c: c and 'schedule-date' in c if c else False)
    if date_span:
        scorecard['match_date'] = date_span.get_text(strip=True)
    else:
        date_pattern = r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,?\s+\d{4})?,?\s+\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\s*(?:LOCAL|IST|GMT)?'
        date_match = re.search(date_pattern, str(soup))
        if date_match:
            scorecard['match_date'] = date_match.group(0)
    
    page_text = soup.get_text()
    html_content = str(soup)
    
    result_match = re.search(r'(India|New Zealand|Australia|England|South Africa|Pakistan|Sri Lanka|West Indies|Bangladesh|Afghanistan|Ireland|Zimbabwe|Scotland|Netherlands|Nepal|UAE|Oman|USA) won by (\d+ (?:runs?|wkts?))', html_content, re.IGNORECASE)
    if result_match:
        scorecard['result'] = f"{result_match.group(1)} won by {result_match.group(2)}"
    elif 'Match drawn' in html_content:
        scorecard['result'] = "Match drawn"
    elif 'Match tied' in html_content:
        scorecard['result'] = "Match tied"
    elif 'No result' in html_content:
        scorecard['result'] = "No result"
    
    innings_headers = soup.find_all('div', id=lambda x: x and x.startswith('team-') and '-innings-' in x and not x.startswith('scard-') and not x.startswith('caret-'))
    
    seen_innings = set()
    for header in innings_headers:
        header_id = header.get('id', '')
        
        if header_id in seen_innings:
            continue
        
        team_name_div = header.find('div', class_=lambda c: c and 'font-bold' in c if c else False)
        team_name = team_name_div.get_text(strip=True) if team_name_div else ''
        
        if not team_name:
            continue
        
        innings_key = f"{team_name}-{header_id}"
        if team_name in [inn['team_name'] for inn in scorecard['innings']]:
            continue
        
        seen_innings.add(header_id)
        
        score_span = header.find('span', class_=lambda c: c and 'font-bold' in c if c else False)
        total_score = score_span.get_text(strip=True).replace('-', '/') if score_span else ''
        
        overs_span = header.find_all('span')
        overs = ''
        for sp in overs_span:
            sp_text = sp.get_text(strip=True)
            if 'Ov' in sp_text:
                overs_match = re.search(r'(\d+(?:\.\d+)?)', sp_text)
                if overs_match:
                    overs = overs_match.group(1)
                break
        
        innings_data = {
            'innings_num': len(scorecard['innings']) + 1,
            'team_name': team_name,
            'total_score': total_score,
            'overs': overs,
            'batting': [],
            'bowling': [],
            'extras': 0,
            'fall_of_wickets': []
        }
        
        scard_id = f"scard-{header_id}"
        scard_div = soup.find('div', id=scard_id)
        
        if scard_div:
            bat_grids = scard_div.find_all('div', class_=lambda c: c and 'scorecard-bat-grid' in c if c else False)
            
            for grid in bat_grids:
                if 'Batter' in grid.get_text():
                    continue
                if grid.find('div', class_=lambda c: c and 'bg-cbBorderGrey' in c if c else False):
                    continue
                
                player_link = grid.find('a', href=lambda h: h and '/profiles/' in h if h else False)
                if not player_link:
                    continue
                
                batter_name = player_link.get_text(strip=True)
                
                dismissal_div = grid.find('div', class_=lambda c: c and 'text-cbTxtSec' in c if c else False)
                dismissal = dismissal_div.get_text(strip=True) if dismissal_div else 'not out'
                
                stat_cells = grid.find_all('div', class_=lambda c: c and 'flex' in c and 'justify-center' in c and 'items-center' in c if c else False)
                
                runs = stat_cells[0].get_text(strip=True) if len(stat_cells) > 0 else '0'
                balls = stat_cells[1].get_text(strip=True) if len(stat_cells) > 1 else '0'
                fours = stat_cells[2].get_text(strip=True) if len(stat_cells) > 2 else '0'
                sixes = stat_cells[3].get_text(strip=True) if len(stat_cells) > 3 else '0'
                sr = stat_cells[4].get_text(strip=True) if len(stat_cells) > 4 else '0.00'
                
                innings_data['batting'].append({
                    'name': batter_name,
                    'dismissal': dismissal,
                    'runs': runs,
                    'balls': balls,
                    'fours': fours,
                    'sixes': sixes,
                    'strike_rate': sr
                })
            
            for div in scard_div.find_all('div'):
                div_text = div.get_text()
                if 'Extras' in div_text:
                    extras_match = re.search(r'Extras\s*(\d+)', div_text)
                    if extras_match:
                        innings_data['extras'] = int(extras_match.group(1))
                    break
            
            bowl_grids = scard_div.find_all('div', class_=lambda c: c and 'scorecard-bowl-grid' in c if c else False)
            
            for grid in bowl_grids:
                if 'Bowler' in grid.get_text():
                    continue
                
                player_link = grid.find('a', href=lambda h: h and '/profiles/' in h if h else False)
                if not player_link:
                    continue
                
                bowler_name = player_link.get_text(strip=True)
                
                stat_cells = grid.find_all('div', class_=lambda c: c and 'flex' in c and 'justify-center' in c and 'items-center' in c if c else False)
                
                overs_bowled = stat_cells[0].get_text(strip=True) if len(stat_cells) > 0 else '0'
                maidens = stat_cells[1].get_text(strip=True) if len(stat_cells) > 1 else '0'
                runs_given = stat_cells[2].get_text(strip=True) if len(stat_cells) > 2 else '0'
                wickets = stat_cells[3].get_text(strip=True) if len(stat_cells) > 3 else '0'
                economy = stat_cells[5].get_text(strip=True) if len(stat_cells) > 5 else '0.00'
                
                innings_data['bowling'].append({
                    'name': bowler_name,
                    'overs': overs_bowled,
                    'maidens': maidens,
                    'runs': runs_given,
                    'wickets': wickets,
                    'economy': economy
                })
        
        scorecard['innings'].append(innings_data)
    
    if not scorecard['innings']:
        team_score_pattern = r'(New Zealand|India|Australia|England|Pakistan|South Africa|West Indies|Sri Lanka|Bangladesh|Afghanistan|NZ|IND|AUS|ENG|PAK|SA|WI|SL|BAN|AFG)\s*(\d+)[-/](\d+)\s*\((\d+(?:\.\d+)?)\s*Ov\)'
        team_matches = re.findall(team_score_pattern, page_text)
        
        for idx, (team, runs, wickets, overs) in enumerate(team_matches[:2]):
            full_team_name = {
                'NZ': 'New Zealand', 'IND': 'India', 'AUS': 'Australia', 
                'ENG': 'England', 'PAK': 'Pakistan', 'SA': 'South Africa',
                'WI': 'West Indies', 'SL': 'Sri Lanka', 'BAN': 'Bangladesh', 'AFG': 'Afghanistan'
            }.get(team.strip(), team.strip())
            
            innings_data = {
                'innings_num': idx + 1,
                'team_name': full_team_name,
                'total_score': f"{runs}/{wickets}",
                'overs': overs,
                'batting': [],
                'bowling': [],
                'extras': 0,
                'fall_of_wickets': []
            }
            scorecard['innings'].append(innings_data)
    
    return scorecard


def update_match_scores(match_id):
    """Update a single match with scores from scorecard"""
    scorecard = scrape_scorecard(match_id)
    if not scorecard or not scorecard.get('innings'):
        return None
    
    innings = scorecard.get('innings', [])
    result = scorecard.get('result', '')
    
    match_data = {
        'match_id': match_id,
        'result': result
    }
    
    if len(innings) >= 1:
        inn1 = innings[0]
        match_data['team1_name'] = inn1.get('team_name', '')
        overs1 = inn1.get('overs', '')
        score1 = inn1.get('total_score', '')
        match_data['team1_score'] = f"{score1} ({overs1})" if overs1 else score1
    
    if len(innings) >= 2:
        inn2 = innings[1]
        match_data['team2_name'] = inn2.get('team_name', '')
        overs2 = inn2.get('overs', '')
        score2 = inn2.get('total_score', '')
        match_data['team2_score'] = f"{score2} ({overs2})" if overs2 else score2
    
    return match_data


def scrape_all_series_matches(series_list):
    """
    Scrape matches for all series with scores
    series_list: list of dicts with 'id', 'series_id', 'series_url' keys
    Returns: list of all matches with scores
    """
    all_matches = []
    
    for series in series_list:
        series_url = series.get('series_url', '')
        series_db_id = series.get('id')
        
        if not series_url:
            continue
        
        print(f"Scraping matches for: {series_url}")
        
        # Get match IDs from series page
        matches = scrape_matches_from_series(series_url)
        
        for match in matches:
            match['series_db_id'] = series_db_id
            match_id = match.get('match_id')
            
            # If no scores, try to get from scorecard
            if match_id and (not match.get('team1_score') or not match.get('team2_score')):
                scores = update_match_scores(match_id)
                if scores:
                    if scores.get('team1_name'):
                        match['team1_name'] = scores['team1_name']
                    if scores.get('team2_name'):
                        match['team2_name'] = scores['team2_name']
                    if scores.get('team1_score'):
                        match['team1_score'] = scores['team1_score']
                    if scores.get('team2_score'):
                        match['team2_score'] = scores['team2_score']
                    if scores.get('result'):
                        match['result'] = scores['result']
                
                time.sleep(0.5)  # Rate limiting
            
            all_matches.append(match)
        
        time.sleep(1)  # Rate limiting between series
    
    return all_matches
