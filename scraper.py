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
    
    info_items = soup.find_all('div', class_='cb-col cb-col-40 cb-plyr-rt')
    if not info_items:
        info_items = soup.find_all('div', class_='cb-col-40')
    
    personal_info_map = {
        'born': ['born', 'date of birth', 'dob'],
        'birth_place': ['birth place', 'birthplace', 'place of birth'],
        'nickname': ['nickname', 'nick name', 'also known as'],
        'role': ['role', 'playing role'],
        'batting_style': ['batting style', 'bat style', 'batting'],
        'bowling_style': ['bowling style', 'bowl style', 'bowling']
    }
    
    info_container = soup.find('div', class_='cb-plyr-inf')
    if info_container:
        items = info_container.find_all('div', class_='cb-col-100')
        for item in items:
            label_elem = item.find('div', class_='cb-col-40')
            value_elem = item.find('div', class_='cb-col-60')
            if label_elem and value_elem:
                label = label_elem.get_text(strip=True).lower()
                value = value_elem.get_text(strip=True)
                for field, keywords in personal_info_map.items():
                    if any(kw in label for kw in keywords):
                        profile[field] = value
                        break
    
    for table in soup.find_all('table', class_='cb-plyr-tbl'):
        header = table.find_previous(['h2', 'h3', 'div'])
        header_text = header.get_text(strip=True).lower() if header else ''
        
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
        
        for row in rows[1:]:
            cells = row.find_all('td')
            if not cells:
                continue
            
            if 'batting' in header_text or 'bat' in header_text:
                if profile.get('bat_matches'):
                    continue
                for i, cell in enumerate(cells[1:], 1):
                    val = cell.get_text(strip=True)
                    if i < len(headers):
                        h = headers[i] if i < len(headers) else ''
                        if 'match' in h:
                            profile['bat_matches'] = val
                        elif 'inn' in h:
                            profile['bat_innings'] = val
                        elif 'run' in h and 'rate' not in h:
                            profile['bat_runs'] = val
                        elif 'ball' in h:
                            profile['bat_balls'] = val
                        elif 'high' in h or 'hs' in h:
                            profile['bat_highest'] = val
                        elif 'avg' in h or 'average' in h:
                            profile['bat_average'] = val
                        elif 'sr' in h or 'strike' in h:
                            profile['bat_strike_rate'] = val
                        elif 'no' in h or 'not out' in h:
                            profile['bat_not_outs'] = val
                        elif '4s' in h or 'four' in h:
                            profile['bat_fours'] = val
                        elif '6s' in h or 'six' in h:
                            profile['bat_sixes'] = val
                        elif 'duck' in h:
                            profile['bat_ducks'] = val
                        elif '50' in h or 'fift' in h:
                            profile['bat_fifties'] = val
                        elif '100' in h or 'hundred' in h or 'cent' in h:
                            profile['bat_hundreds'] = val
                        elif '200' in h:
                            profile['bat_two_hundreds'] = val
            
            elif 'bowling' in header_text or 'bowl' in header_text:
                if profile.get('bowl_matches'):
                    continue
                for i, cell in enumerate(cells[1:], 1):
                    val = cell.get_text(strip=True)
                    if i < len(headers):
                        h = headers[i] if i < len(headers) else ''
                        if 'match' in h:
                            profile['bowl_matches'] = val
                        elif 'inn' in h:
                            profile['bowl_innings'] = val
                        elif 'ball' in h:
                            profile['bowl_balls'] = val
                        elif 'run' in h:
                            profile['bowl_runs'] = val
                        elif 'maid' in h:
                            profile['bowl_maidens'] = val
                        elif 'wkt' in h or 'wicket' in h:
                            profile['bowl_wickets'] = val
                        elif 'avg' in h or 'average' in h:
                            profile['bowl_average'] = val
                        elif 'eco' in h or 'economy' in h:
                            profile['bowl_economy'] = val
                        elif 'sr' in h or 'strike' in h:
                            profile['bowl_strike_rate'] = val
                        elif 'bbi' in h or 'best inn' in h:
                            profile['bowl_best_innings'] = val
                        elif 'bbm' in h or 'best match' in h:
                            profile['bowl_best_match'] = val
                        elif '4w' in h or '4 wkt' in h:
                            profile['bowl_four_wickets'] = val
                        elif '5w' in h or '5 wkt' in h:
                            profile['bowl_five_wickets'] = val
                        elif '10w' in h or '10 wkt' in h:
                            profile['bowl_ten_wickets'] = val
    
    return profile
