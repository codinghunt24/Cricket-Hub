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
