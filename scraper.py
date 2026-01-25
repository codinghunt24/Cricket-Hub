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

def parse_date_from_title(title):
    months = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
        'Sep': '09', 'Sept': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }
    
    date_pattern = r'(\d{1,2})\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s*(\d{4})'
    match = re.search(date_pattern, title)
    if match:
        day = match.group(1).zfill(2)
        month = months.get(match.group(2), '01')
        year = match.group(3)
        return f"{year}-{month}-{day}"
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
        start_date = parse_date_from_title(title)
        
        clean_href = href.replace('/matches', '')
        series_url = BASE_URL + clean_href if clean_href.startswith('/') else clean_href
        
        series_list.append({
            'series_id': series_id,
            'name': name,
            'series_url': series_url,
            'start_date': start_date
        })
    
    return series_list
