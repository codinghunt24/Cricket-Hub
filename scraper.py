import requests
from bs4 import BeautifulSoup
import re
import time

BASE_URL = "https://www.cricbuzz.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
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

def fetch_page(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_team_id(url):
    match = re.search(r'/(\d+)/', url)
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
        
        teams.append({
            'team_id': team_id,
            'name': team_name,
            'team_url': team_url,
            'flag_url': flag_url
        })
    
    seen = set()
    unique_teams = []
    for team in teams:
        if team['name'] not in seen:
            seen.add(team['name'])
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
        
        players.append({
            'player_id': player_id,
            'name': player_name,
            'player_url': player_url,
            'photo_url': photo_url,
            'role': role
        })
    
    seen = set()
    unique_players = []
    for player in players:
        if player['name'] not in seen:
            seen.add(player['name'])
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
    
    full_url = player_url if player_url.startswith('http') else BASE_URL + player_url
    html = fetch_page(full_url)
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    profile = {}
    
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

def scrape_matches_from_series(series_url):
    matches_list = []
    matches_url = series_url.rstrip('/') + '/matches'
    
    series_slug_match = re.search(r'/cricket-series/\d+/([^/]+)', series_url)
    series_slug = series_slug_match.group(1) if series_slug_match else ''
    
    # Try /matches page first, then main series page as fallback
    urls_to_try = [matches_url, series_url.rstrip('/')]
    html = None
    
    for url in urls_to_try:
        html = fetch_page(url)
        if html:
            # Check if this page has series-specific match links
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
    
    # First, find all match IDs directly in the page source (includes JS-embedded IDs)
    all_match_ids = set(re.findall(r'/live-cricket-scores/(\d+)/', html))
    
    # Also find bare 6-digit match IDs that might be in JavaScript data
    # Look for IDs that start with 121 (common pattern for 2026 matches)
    series_id_match = re.search(r'/cricket-series/(\d+)/', series_url)
    if series_id_match:
        series_num = series_id_match.group(1)
        # Find IDs that are numerically close to IDs we've already found
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
        
        # Extract format from URL (most reliable)
        url_format = re.search(r'/(\d+(?:st|nd|rd|th))-(\w+)', href, re.IGNORECASE)
        if url_format:
            ordinal = url_format.group(1).lower()  # 1st, 2nd, 3rd, etc.
            format_type = url_format.group(2).upper()  # ODI, T20I, etc.
            if format_type == 'T20':
                format_type = 'T20I'
            match_format = f"{ordinal} {format_type}"
        
        # Extract team names from URL (e.g., sl-vs-eng or eng-vs-sl)
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
    
    soup = BeautifulSoup(html, 'html.parser')
    scorecard = {
        'match_id': match_id,
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
