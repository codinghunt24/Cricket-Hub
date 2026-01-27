import os
import re
import requests
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', os.urandom(24))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)

# Team flag URLs mapping using FlagCDN
TEAM_FLAGS = {
    'india': 'https://flagcdn.com/48x36/in.png',
    'new zealand': 'https://flagcdn.com/48x36/nz.png',
    'australia': 'https://flagcdn.com/48x36/au.png',
    'england': 'https://flagcdn.com/48x36/gb-eng.png',
    'pakistan': 'https://flagcdn.com/48x36/pk.png',
    'south africa': 'https://flagcdn.com/48x36/za.png',
    'west indies': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/WestIndiesCricketFlagPre1999.svg/48px-WestIndiesCricketFlagPre1999.svg.png',
    'sri lanka': 'https://flagcdn.com/48x36/lk.png',
    'bangladesh': 'https://flagcdn.com/48x36/bd.png',
    'afghanistan': 'https://flagcdn.com/48x36/af.png',
    'zimbabwe': 'https://flagcdn.com/48x36/zw.png',
    'ireland': 'https://flagcdn.com/48x36/ie.png',
    'scotland': 'https://flagcdn.com/48x36/gb-sct.png',
    'netherlands': 'https://flagcdn.com/48x36/nl.png',
    'nepal': 'https://flagcdn.com/48x36/np.png',
    'uae': 'https://flagcdn.com/48x36/ae.png',
    'usa': 'https://flagcdn.com/48x36/us.png',
    'oman': 'https://flagcdn.com/48x36/om.png',
    'ind': 'https://flagcdn.com/48x36/in.png',
    'nz': 'https://flagcdn.com/48x36/nz.png',
    'aus': 'https://flagcdn.com/48x36/au.png',
    'eng': 'https://flagcdn.com/48x36/gb-eng.png',
    'pak': 'https://flagcdn.com/48x36/pk.png',
    'sa': 'https://flagcdn.com/48x36/za.png',
    'wi': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/WestIndiesCricketFlagPre1999.svg/48px-WestIndiesCricketFlagPre1999.svg.png',
    'sl': 'https://flagcdn.com/48x36/lk.png',
    'ban': 'https://flagcdn.com/48x36/bd.png',
    'afg': 'https://flagcdn.com/48x36/af.png',
    'zim': 'https://flagcdn.com/48x36/zw.png',
    'ire': 'https://flagcdn.com/48x36/ie.png',
    'italy': 'https://flagcdn.com/48x36/it.png',
    'ita': 'https://flagcdn.com/48x36/it.png',
}

def get_team_flag(team_name):
    if not team_name:
        return ''
    team_lower = team_name.lower().strip()
    return TEAM_FLAGS.get(team_lower, '')

@app.context_processor
def utility_processor():
    return dict(get_team_flag=get_team_flag)

from models import init_models
TeamCategory, Team, Player, ScrapeLog, ScrapeSetting, ProfileScrapeSetting, SeriesCategory, Series, SeriesScrapeSetting, Match, MatchScrapeSetting, PostCategory, Post = init_models(db)

import scraper
from scheduler import init_scheduler, update_schedule, update_player_schedule

with app.app_context():
    db.create_all()
    
    for slug, info in scraper.CATEGORIES.items():
        existing = TeamCategory.query.filter_by(slug=slug).first()
        if not existing:
            category = TeamCategory(name=info['name'], slug=slug, url=info['url'])
            db.session.add(category)
    
    if not ScrapeSetting.query.first():
        setting = ScrapeSetting(auto_scrape_enabled=False, scrape_time='02:00')
        db.session.add(setting)
    
    for slug in ['international', 'domestic', 'league', 'women']:
        if not ProfileScrapeSetting.query.filter_by(category_slug=slug).first():
            ps = ProfileScrapeSetting(category_slug=slug, auto_scrape_enabled=False, scrape_time='03:00')
            db.session.add(ps)
    
    for slug, info in scraper.SERIES_CATEGORIES.items():
        existing = SeriesCategory.query.filter_by(slug=slug).first()
        if not existing:
            category = SeriesCategory(name=info['name'], slug=slug, url=info['url'])
            db.session.add(category)
    
    for slug in ['all', 'international', 'domestic', 'league', 'women']:
        if not SeriesScrapeSetting.query.filter_by(category_slug=slug).first():
            ss = SeriesScrapeSetting(category_slug=slug, auto_scrape_enabled=False, scrape_time='08:00')
            db.session.add(ss)
    
    if not MatchScrapeSetting.query.first():
        ms = MatchScrapeSetting(auto_scrape_enabled=False, scrape_time='10:00')
        db.session.add(ms)
    
    db.session.commit()

init_scheduler(app, db, TeamCategory, Team, ScrapeLog, ScrapeSetting, scraper, Player)

def upsert_series(series_data, category_id):
    """Insert or update series by series_id"""
    if not series_data.get('series_id'):
        return None
    
    existing = Series.query.filter_by(series_id=series_data['series_id']).first()
    if existing:
        existing.name = series_data.get('name', existing.name)
        existing.series_url = series_data.get('series_url', existing.series_url)
        existing.start_date = series_data.get('start_date', existing.start_date)
        existing.end_date = series_data.get('end_date', existing.end_date)
        existing.date_range = series_data.get('date_range', existing.date_range)
        existing.category_id = category_id
        return existing
    else:
        new_series = Series(
            series_id=series_data['series_id'],
            name=series_data.get('name', ''),
            series_url=series_data.get('series_url', ''),
            start_date=series_data.get('start_date'),
            end_date=series_data.get('end_date'),
            date_range=series_data.get('date_range'),
            category_id=category_id
        )
        db.session.add(new_series)
        return new_series

def upsert_match(match_data, db_series_id=None):
    """Insert or update match by match_id"""
    if not match_data.get('match_id'):
        return None
    
    existing = Match.query.filter_by(match_id=str(match_data['match_id'])).first()
    if existing:
        existing.cricbuzz_series_id = match_data.get('series_id', existing.cricbuzz_series_id)
        existing.team1_id = match_data.get('team1_id', existing.team1_id)
        existing.team2_id = match_data.get('team2_id', existing.team2_id)
        existing.venue_id = match_data.get('venue_id', existing.venue_id)
        existing.match_format = match_data.get('match_format', existing.match_format)
        existing.format_type = match_data.get('format_type', existing.format_type)
        existing.venue = match_data.get('venue', existing.venue)
        existing.match_date = match_data.get('match_date', existing.match_date)
        existing.state = match_data.get('state', existing.state)
        existing.team1_name = match_data.get('team1') or match_data.get('team1_name', existing.team1_name)
        existing.team1_score = match_data.get('team1_score', existing.team1_score)
        existing.team2_name = match_data.get('team2') or match_data.get('team2_name', existing.team2_name)
        existing.team2_score = match_data.get('team2_score', existing.team2_score)
        existing.result = match_data.get('result', existing.result)
        existing.match_url = match_data.get('match_url', existing.match_url)
        existing.series_name = match_data.get('series_name', existing.series_name)
        if db_series_id:
            existing.series_id = db_series_id
        if match_data.get('batting'):
            existing.batting_data = match_data.get('batting')
        if match_data.get('bowling'):
            existing.bowling_data = match_data.get('bowling')
        return existing
    else:
        new_match = Match(
            match_id=str(match_data['match_id']),
            cricbuzz_series_id=match_data.get('series_id', ''),
            team1_id=match_data.get('team1_id', ''),
            team2_id=match_data.get('team2_id', ''),
            venue_id=match_data.get('venue_id', ''),
            match_format=match_data.get('match_format', ''),
            format_type=match_data.get('format_type', ''),
            venue=match_data.get('venue', ''),
            match_date=match_data.get('match_date', ''),
            state=match_data.get('state', ''),
            team1_name=match_data.get('team1') or match_data.get('team1_name', ''),
            team1_score=match_data.get('team1_score', ''),
            team2_name=match_data.get('team2') or match_data.get('team2_name', ''),
            team2_score=match_data.get('team2_score', ''),
            result=match_data.get('result', ''),
            match_url=match_data.get('match_url', ''),
            series_name=match_data.get('series_name', ''),
            series_id=db_series_id,
            batting_data=match_data.get('batting'),
            bowling_data=match_data.get('bowling')
        )
        db.session.add(new_match)
        return new_match

def upsert_team(team_data, category_id):
    """Insert or update team by team_id"""
    if not team_data.get('team_id'):
        return None
    
    existing = Team.query.filter_by(team_id=team_data['team_id']).first()
    if existing:
        existing.name = team_data.get('name', existing.name)
        existing.flag_url = team_data.get('flag_url', existing.flag_url)
        existing.team_url = team_data.get('team_url', existing.team_url)
        existing.category_id = category_id
        return existing
    else:
        new_team = Team(
            team_id=team_data['team_id'],
            name=team_data.get('name', ''),
            flag_url=team_data.get('flag_url'),
            team_url=team_data.get('team_url'),
            category_id=category_id
        )
        db.session.add(new_team)
        return new_team

def upsert_player(player_data, db_team_id):
    """Insert or update player by player_id"""
    if not player_data.get('player_id'):
        return None
    
    existing = Player.query.filter_by(player_id=player_data['player_id']).first()
    if existing:
        existing.name = player_data.get('name', existing.name)
        existing.role = player_data.get('role', existing.role)
        existing.photo_url = player_data.get('photo_url', existing.photo_url)
        existing.player_url = player_data.get('player_url', existing.player_url)
        existing.team_id = db_team_id
        return existing
    else:
        new_player = Player(
            player_id=player_data['player_id'],
            name=player_data.get('name', ''),
            role=player_data.get('role'),
            photo_url=player_data.get('photo_url'),
            player_url=player_data.get('player_url'),
            team_id=db_team_id
        )
        db.session.add(new_player)
        return new_player

def get_team_flag(team_name, teams_list):
    """Find team flag by partial name matching"""
    if not team_name:
        return None
    team_name_lower = team_name.lower().strip()
    
    for team in teams_list:
        if not team.flag_url:
            continue
        db_name = team.name.lower() if team.name else ''
        if db_name == team_name_lower:
            return team.flag_url
        if db_name and db_name in team_name_lower:
            return team.flag_url
        if team_name_lower.startswith(db_name.split()[0] if db_name else ''):
            return team.flag_url
    return None

@app.route('/')
def index():
    all_matches = Match.query.order_by(Match.updated_at.desc()).limit(50).all()
    live = [m for m in all_matches if m.state == 'Live']
    status = [m for m in all_matches if m.state != 'Live' and m.result and 'opt to' in m.result.lower()]
    innings = [m for m in all_matches if m.state == 'Innings Break' and m not in status]
    complete = [m for m in all_matches if m.state == 'Complete' and m not in status]
    upcoming = [m for m in all_matches if m.state == 'Upcoming' and m not in status]
    matches = live + status + innings + complete + upcoming
    
    teams = Team.query.all()
    
    match_flags = {}
    for m in matches:
        match_flags[f"{m.match_id}_1"] = get_team_flag(m.team1_name, teams)
        match_flags[f"{m.match_id}_2"] = get_team_flag(m.team2_name, teams)
    
    recent_posts = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).limit(5).all()
    
    # Get recent series for home page (order by id desc for most recently added)
    recent_series = Series.query.order_by(Series.id.desc()).limit(10).all()
    
    return render_template('index.html', matches=matches, match_flags=match_flags, recent_posts=recent_posts, series=recent_series)

@app.route('/live-scores')
def live_scores():
    all_matches = Match.query.order_by(Match.updated_at.desc()).limit(50).all()
    live = [m for m in all_matches if m.state == 'Live']
    status = [m for m in all_matches if m.state != 'Live' and m.result and 'opt to' in m.result.lower()]
    innings = [m for m in all_matches if m.state == 'Innings Break' and m not in status]
    complete = [m for m in all_matches if m.state == 'Complete' and m not in status]
    upcoming = [m for m in all_matches if m.state == 'Upcoming' and m not in status]
    matches = live + status + innings + complete + upcoming
    
    teams = Team.query.all()
    
    match_flags = {}
    for m in matches:
        match_flags[f"{m.match_id}_1"] = get_team_flag(m.team1_name, teams)
        match_flags[f"{m.match_id}_2"] = get_team_flag(m.team2_name, teams)
    
    return render_template('index.html', matches=matches, match_flags=match_flags)

@app.route('/teams')
def teams_page():
    categories = TeamCategory.query.all()
    return render_template('teams.html', categories=categories)

@app.route('/teams/<category_slug>')
def teams_by_category(category_slug):
    category = TeamCategory.query.filter_by(slug=category_slug).first_or_404()
    teams = Team.query.filter_by(category_id=category.id).all()
    return render_template('teams_list.html', category=category, teams=teams)

@app.route('/team/<int:team_id>')
def team_detail(team_id):
    team = Team.query.get_or_404(team_id)
    players = Player.query.filter_by(team_id=team.id).all()
    return render_template('team_detail.html', team=team, players=players)

@app.route('/player/<int:player_id>')
def player_detail(player_id):
    player = Player.query.get_or_404(player_id)
    return render_template('player_detail.html', player=player)

@app.route('/series')
def series_page():
    from collections import OrderedDict
    
    categories = SeriesCategory.query.all()
    all_series = Series.query.order_by(Series.start_date).all()
    
    month_names = {
        '01': 'January', '02': 'February', '03': 'March', '04': 'April',
        '05': 'May', '06': 'June', '07': 'July', '08': 'August',
        '09': 'September', '10': 'October', '11': 'November', '12': 'December'
    }
    
    month_data = OrderedDict()
    for s in all_series:
        if s.start_date:
            parts = s.start_date.split('-')
            if len(parts) >= 2:
                year = parts[0]
                month = parts[1]
                month_key = f"{year}-{month}"
                month_label = f"{month_names.get(month, month)} {year}"
        else:
            month_key = "unknown"
            month_label = "Upcoming"
        
        if month_key not in month_data:
            month_data[month_key] = {'label': month_label, 'series': []}
        month_data[month_key]['series'].append(s)
    
    category_data = []
    for cat in categories:
        series_list = Series.query.filter_by(category_id=cat.id).order_by(Series.start_date).all()
        if series_list:
            category_data.append({
                'category': cat,
                'series': series_list
            })
    
    return render_template('series.html', category_data=category_data, month_data=month_data, categories=categories)

@app.route('/series/<int:series_id>')
def series_detail(series_id):
    series = Series.query.get_or_404(series_id)
    matches = Match.query.filter_by(series_id=series_id).order_by(Match.match_id).all()
    category = SeriesCategory.query.get(series.category_id)
    return render_template('series_detail.html', series=series, matches=matches, category=category)

@app.route('/match/<match_id>')
def match_detail(match_id):
    match = Match.query.filter_by(match_id=match_id).first_or_404()
    series = Series.query.get(match.series_id)
    scorecard = scraper.scrape_scorecard(match_id)
    
    if scorecard:
        if not match.venue and scorecard.get('venue'):
            match.venue = scorecard.get('venue')
        if not match.match_date and scorecard.get('match_date'):
            match.match_date = scorecard.get('match_date')
    
    return render_template('match_detail.html', match=match, series=series, scorecard=scorecard)

@app.route('/news')
def news():
    return render_template('index.html')

@app.route('/admin')
def admin_dashboard():
    teams_count = Team.query.count()
    players_count = Player.query.count()
    categories = TeamCategory.query.all()
    recent_logs = ScrapeLog.query.order_by(ScrapeLog.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', 
                         teams_count=teams_count,
                         players_count=players_count,
                         categories=categories,
                         recent_logs=recent_logs)

@app.route('/admin/matches')
def admin_matches():
    matches = Match.query.order_by(Match.id.desc()).all()
    live_count = len([m for m in matches if m.state == 'Live'])
    innings_count = len([m for m in matches if m.state == 'Innings Break'])
    complete_count = len([m for m in matches if m.state == 'Complete'])
    upcoming_count = len([m for m in matches if m.state == 'Upcoming'])
    result_count = len([m for m in matches if m.result])
    status_count = len([m for m in matches if m.result and 'opt to' in m.result.lower()])
    return render_template('admin/matches.html', 
                           matches=matches,
                           live_count=live_count,
                           innings_count=innings_count,
                           complete_count=complete_count,
                           upcoming_count=upcoming_count,
                           result_count=result_count,
                           status_count=status_count)

@app.route('/admin/teams')
def admin_teams():
    categories = TeamCategory.query.all()
    setting = ScrapeSetting.query.first()
    recent_logs = ScrapeLog.query.order_by(ScrapeLog.created_at.desc()).limit(10).all()
    
    category_data = []
    for cat in categories:
        team_count = Team.query.filter_by(category_id=cat.id).count()
        teams = Team.query.filter_by(category_id=cat.id).all()
        category_data.append({
            'category': cat,
            'team_count': team_count,
            'teams': teams
        })
    
    return render_template('admin/teams.html', 
                         category_data=category_data,
                         setting=setting,
                         recent_logs=recent_logs)

@app.route('/admin/series')
def admin_series():
    categories = SeriesCategory.query.all()
    recent_logs = ScrapeLog.query.filter(
        (ScrapeLog.category.like('series_%')) | (ScrapeLog.category.like('matches_%'))
    ).order_by(ScrapeLog.created_at.desc()).limit(10).all()
    
    category_data = []
    for cat in categories:
        series_count = Series.query.filter_by(category_id=cat.id).count()
        series_list = Series.query.filter_by(category_id=cat.id).order_by(Series.name).all()
        setting = SeriesScrapeSetting.query.filter_by(category_slug=cat.slug).first()
        category_data.append({
            'category': cat,
            'series_count': series_count,
            'series': series_list,
            'setting': setting
        })
    
    match_setting = MatchScrapeSetting.query.first()
    
    return render_template('admin/series.html', 
                         category_data=category_data,
                         recent_logs=recent_logs,
                         match_setting=match_setting)

@app.route('/admin/news')
def admin_news():
    return render_template('admin/news.html')

@app.route('/admin/scorecard')
def admin_scorecard():
    matches = Match.query.order_by(Match.updated_at.desc()).limit(50).all()
    return render_template('admin/scorecard.html', matches=matches)

@app.route('/api/scrape/scorecard', methods=['POST'])
def api_scrape_scorecard():
    try:
        data = request.get_json()
        match_id = data.get('match_id', '')
        input_series_id = data.get('series_id', '')
        
        if not match_id:
            return jsonify({'success': False, 'message': 'Match ID required'}), 400
        
        scorecard = scraper.scrape_scorecard(match_id)
        
        if not scorecard:
            return jsonify({'success': False, 'message': 'Failed to scrape scorecard'}), 400
        
        verification = {
            'input_match_id': match_id,
            'page_match_id': scorecard.get('match_id', ''),
            'match_id_match': str(match_id) == str(scorecard.get('match_id', '')),
            'input_series_id': input_series_id,
            'page_series_id': scorecard.get('series_id', ''),
            'series_id_match': not input_series_id or str(input_series_id) == str(scorecard.get('series_id', '')),
            'team1_id': scorecard.get('team1_id', ''),
            'team2_id': scorecard.get('team2_id', '')
        }
        
        return jsonify({
            'success': True,
            'scorecard': scorecard,
            'verification': verification
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/save/scorecard', methods=['POST'])
def api_save_scorecard():
    try:
        data = request.get_json()
        match_id = data.get('match_id', '')
        
        if not match_id:
            return jsonify({'success': False, 'message': 'Match ID required'}), 400
        
        match = Match.query.filter_by(match_id=match_id).first()
        
        if not match:
            match = Match(match_id=match_id)
            db.session.add(match)
        
        if data.get('series_id'):
            series = Series.query.filter_by(series_id=data.get('series_id')).first()
            if series:
                match.series_id = series.id
        
        if data.get('venue'):
            match.venue = data.get('venue')
        if data.get('match_date'):
            match.match_date = data.get('match_date')
        if data.get('result'):
            match.result = data.get('result')
            match.state = 'Complete'
        
        innings = data.get('innings', [])
        if len(innings) >= 1:
            inn1 = innings[0]
            match.team1_name = inn1.get('team_name', match.team1_name)
            match.team1_score = f"{inn1.get('total_score', '')} ({inn1.get('overs', '')} Ov)"
        if len(innings) >= 2:
            inn2 = innings[1]
            match.team2_name = inn2.get('team_name', match.team2_name)
            match.team2_score = f"{inn2.get('total_score', '')} ({inn2.get('overs', '')} Ov)"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scorecard saved for match {match_id}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/settings')
def admin_settings():
    setting = ScrapeSetting.query.first()
    return render_template('admin/settings.html', setting=setting)

@app.route('/api/scrape/category/<category_slug>', methods=['POST'])
def scrape_category(category_slug):
    try:
        category = TeamCategory.query.filter_by(slug=category_slug).first()
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'}), 404
        
        result = scraper.scrape_category(category_slug)
        if not result:
            return jsonify({'success': False, 'message': 'Failed to scrape'}), 500
        
        teams_scraped = 0
        teams_updated = 0
        for team_data in result['teams']:
            if not team_data.get('team_id'):
                continue
            
            # Use team_id for lookup (more reliable than name)
            existing = Team.query.filter_by(team_id=team_data['team_id']).first()
            if existing:
                existing.name = team_data.get('name', existing.name)
                existing.flag_url = team_data.get('flag_url', existing.flag_url)
                existing.team_url = team_data.get('team_url', existing.team_url)
                existing.category_id = category.id
                existing.updated_at = datetime.utcnow()
                teams_updated += 1
            else:
                team = Team(
                    team_id=team_data['team_id'],
                    name=team_data['name'],
                    flag_url=team_data.get('flag_url'),
                    team_url=team_data.get('team_url'),
                    category_id=category.id
                )
                db.session.add(team)
                teams_scraped += 1
        
        db.session.commit()
        
        total = teams_scraped + teams_updated
        log = ScrapeLog(
            category=category_slug,
            status='success',
            message=f'Saved {teams_scraped} new, updated {teams_updated} teams',
            teams_scraped=total
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Saved {teams_scraped} new teams, updated {teams_updated} existing',
            'teams_scraped': teams_scraped,
            'teams_updated': teams_updated
        })
    
    except Exception as e:
        log = ScrapeLog(
            category=category_slug,
            status='error',
            message=str(e)
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scrape/team/<int:team_id>/players', methods=['POST'])
def scrape_team_players(team_id):
    try:
        team = Team.query.get_or_404(team_id)
        
        if not team.team_url:
            return jsonify({'success': False, 'message': 'Team URL not found'}), 400
        
        players_data = scraper.scrape_players_from_team(team.team_url)
        
        players_scraped = 0
        players_updated = 0
        for player_data in players_data:
            if not player_data.get('player_id'):
                continue
            
            # Use player_id for lookup (more reliable than name)
            existing = Player.query.filter_by(player_id=player_data['player_id']).first()
            if existing:
                existing.name = player_data.get('name', existing.name)
                existing.photo_url = player_data.get('photo_url', existing.photo_url)
                existing.player_url = player_data.get('player_url', existing.player_url)
                existing.role = player_data.get('role', existing.role)
                existing.team_id = team.id
                existing.updated_at = datetime.utcnow()
                players_updated += 1
            else:
                player = Player(
                    player_id=player_data['player_id'],
                    name=player_data['name'],
                    photo_url=player_data.get('photo_url'),
                    player_url=player_data.get('player_url'),
                    role=player_data.get('role'),
                    team_id=team.id
                )
                db.session.add(player)
                players_scraped += 1
        
        db.session.commit()
        
        total = players_scraped + players_updated
        log = ScrapeLog(
            category=f'team_{team.name}',
            status='success',
            message=f'Saved {players_scraped} new, updated {players_updated} players',
            players_scraped=total
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Saved {players_scraped} new players, updated {players_updated} existing',
            'players_scraped': players_scraped,
            'players_updated': players_updated
        })
    
    except Exception as e:
        log = ScrapeLog(
            category=f'team_players',
            status='error',
            message=str(e)
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scrape/all', methods=['POST'])
def scrape_all():
    try:
        total_teams = 0
        categories = TeamCategory.query.all()
        
        for category in categories:
            result = scraper.scrape_category(category.slug)
            if result:
                for team_data in result['teams']:
                    existing = Team.query.filter_by(name=team_data['name'], category_id=category.id).first()
                    if existing:
                        existing.team_id = team_data.get('team_id')
                        existing.flag_url = team_data.get('flag_url')
                        existing.team_url = team_data.get('team_url')
                        existing.updated_at = datetime.utcnow()
                    else:
                        team = Team(
                            team_id=team_data.get('team_id'),
                            name=team_data['name'],
                            flag_url=team_data.get('flag_url'),
                            team_url=team_data.get('team_url'),
                            category_id=category.id
                        )
                        db.session.add(team)
                    total_teams += 1
        
        db.session.commit()
        
        setting = ScrapeSetting.query.first()
        if setting:
            setting.last_scrape = datetime.utcnow()
            db.session.commit()
        
        log = ScrapeLog(
            category='all',
            status='success',
            message=f'Scraped {total_teams} teams from all categories',
            teams_scraped=total_teams
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scraped {total_teams} teams from all categories',
            'teams_scraped': total_teams
        })
    
    except Exception as e:
        log = ScrapeLog(
            category='all',
            status='error',
            message=str(e)
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/server-time')
def get_server_time():
    from datetime import datetime
    now = datetime.now()
    return jsonify({'time': now.strftime('%H:%M:%S')})

@app.route('/api/settings/auto-scrape', methods=['POST'])
def toggle_auto_scrape():
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', False)
        scrape_time = data.get('scrape_time', '02:00')
        
        setting = ScrapeSetting.query.first()
        if setting:
            setting.auto_scrape_enabled = enabled
            setting.scrape_time = scrape_time
            db.session.commit()
        
        update_schedule(app, db, ScrapeSetting, TeamCategory, Team, ScrapeLog, scraper, enabled, scrape_time)
        
        return jsonify({
            'success': True,
            'message': f'Auto scrape {"enabled" if enabled else "disabled"}'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/teams/<category_slug>')
def get_teams_api(category_slug):
    category = TeamCategory.query.filter_by(slug=category_slug).first()
    if not category:
        return jsonify([])
    
    teams = Team.query.filter_by(category_id=category.id).all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'flag_url': t.flag_url,
        'team_url': t.team_url
    } for t in teams])

@app.route('/api/team/<int:team_id>/players')
def get_players_api(team_id):
    players = Player.query.filter_by(team_id=team_id).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'photo_url': p.photo_url,
        'role': p.role,
        'player_url': p.player_url
    } for p in players])

@app.route('/api/teams/clear-all', methods=['DELETE'])
def clear_all_teams():
    try:
        Player.query.delete()
        Team.query.delete()
        db.session.commit()
        
        log = ScrapeLog(
            category='clear',
            status='success',
            message='All teams and players cleared'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All teams and players have been cleared'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

scrape_progress = {}

@app.route('/api/scrape/category/<category_slug>/players/progress', methods=['GET'])
def get_scrape_progress(category_slug):
    progress = scrape_progress.get(category_slug, {'percent': 0, 'current': 0, 'total': 0, 'status': 'idle'})
    return jsonify(progress)

@app.route('/api/scrape/category/<category_slug>/players', methods=['POST'])
def scrape_category_players(category_slug):
    try:
        category = TeamCategory.query.filter_by(slug=category_slug).first()
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'}), 404
        
        total_players = 0
        teams = Team.query.filter_by(category_id=category.id).filter(Team.team_url.isnot(None)).all()
        total_teams = len(teams)
        
        scrape_progress[category_slug] = {'percent': 0, 'current': 0, 'total': total_teams, 'status': 'running'}
        
        for idx, team in enumerate(teams):
            try:
                players_data = scraper.scrape_players_from_team(team.team_url)
                for player_data in players_data:
                    existing = Player.query.filter_by(name=player_data['name'], team_id=team.id).first()
                    if existing:
                        existing.player_id = player_data.get('player_id')
                        existing.photo_url = player_data.get('photo_url')
                        existing.player_url = player_data.get('player_url')
                        existing.role = player_data.get('role')
                        existing.updated_at = datetime.utcnow()
                    else:
                        player = Player(
                            player_id=player_data.get('player_id'),
                            name=player_data['name'],
                            photo_url=player_data.get('photo_url'),
                            player_url=player_data.get('player_url'),
                            role=player_data.get('role'),
                            team_id=team.id
                        )
                        db.session.add(player)
                    total_players += 1
                
                percent = int(((idx + 1) / total_teams) * 100)
                scrape_progress[category_slug] = {'percent': percent, 'current': idx + 1, 'total': total_teams, 'status': 'running', 'team': team.name}
            except Exception as e:
                continue
        
        db.session.commit()
        scrape_progress[category_slug] = {'percent': 100, 'current': total_teams, 'total': total_teams, 'status': 'complete'}
        
        log = ScrapeLog(
            category=f'{category_slug}_players',
            status='success',
            message=f'Scraped {total_players} players from {category.name}',
            players_scraped=total_players
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scraped {total_players} players from {category.name}',
            'players_scraped': total_players
        })
    
    except Exception as e:
        scrape_progress[category_slug] = {'percent': 0, 'current': 0, 'total': 0, 'status': 'error'}
        log = ScrapeLog(
            category=f'{category_slug}_players',
            status='error',
            message=str(e)
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scrape/all-players', methods=['POST'])
def scrape_all_players():
    try:
        total_players = 0
        teams = Team.query.filter(Team.team_url.isnot(None)).all()
        
        for team in teams:
            try:
                players_data = scraper.scrape_players_from_team(team.team_url)
                for player_data in players_data:
                    existing = Player.query.filter_by(name=player_data['name'], team_id=team.id).first()
                    if existing:
                        existing.player_id = player_data.get('player_id')
                        existing.photo_url = player_data.get('photo_url')
                        existing.player_url = player_data.get('player_url')
                        existing.role = player_data.get('role')
                        existing.updated_at = datetime.utcnow()
                    else:
                        player = Player(
                            player_id=player_data.get('player_id'),
                            name=player_data['name'],
                            photo_url=player_data.get('photo_url'),
                            player_url=player_data.get('player_url'),
                            role=player_data.get('role'),
                            team_id=team.id
                        )
                        db.session.add(player)
                    total_players += 1
            except Exception as e:
                continue
        
        db.session.commit()
        
        log = ScrapeLog(
            category='all_players',
            status='success',
            message=f'Scraped {total_players} players from all teams',
            players_scraped=total_players
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scraped {total_players} players from all teams',
            'players_scraped': total_players
        })
    
    except Exception as e:
        log = ScrapeLog(
            category='all_players',
            status='error',
            message=str(e)
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/category-auto-scrape', methods=['POST'])
def toggle_category_auto_scrape():
    try:
        data = request.get_json() or {}
        category = data.get('category')
        enabled = data.get('enabled', False)
        scrape_time = data.get('scrape_time', '04:00')
        
        setting = ScrapeSetting.query.first()
        if setting:
            if category == 'international':
                setting.intl_auto = enabled
                setting.intl_time = scrape_time
            elif category == 'domestic':
                setting.domestic_auto = enabled
                setting.domestic_time = scrape_time
            elif category == 'league':
                setting.league_auto = enabled
                setting.league_time = scrape_time
            elif category == 'women':
                setting.women_auto = enabled
                setting.women_time = scrape_time
            db.session.commit()
        
        from scheduler import update_category_player_schedule
        update_category_player_schedule(app, db, ScrapeSetting, TeamCategory, Team, Player, ScrapeLog, scraper, category, enabled, scrape_time)
        
        return jsonify({
            'success': True,
            'message': f'{category.title()} auto scrape {"enabled" if enabled else "disabled"} at {scrape_time}'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/player-auto-scrape', methods=['POST'])
def toggle_player_auto_scrape():
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', False)
        scrape_time = data.get('scrape_time', '03:00')
        
        setting = ScrapeSetting.query.first()
        if setting:
            setting.player_auto_scrape_enabled = enabled
            setting.player_scrape_time = scrape_time
            db.session.commit()
        
        update_player_schedule(app, db, ScrapeSetting, Team, Player, ScrapeLog, scraper, enabled, scrape_time)
        
        return jsonify({
            'success': True,
            'message': f'Player auto scrape {"enabled" if enabled else "disabled"}'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

profile_scrape_progress = {}

@app.route('/api/scrape/profiles/<category_slug>/progress', methods=['GET'])
def get_profile_scrape_progress(category_slug):
    progress = profile_scrape_progress.get(category_slug, {'percent': 0, 'current': 0, 'total': 0, 'status': 'idle', 'current_player': ''})
    return jsonify(progress)

def scrape_profiles_task(category_slug, player_ids):
    import time
    with app.app_context():
        try:
            players = Player.query.filter(Player.id.in_(player_ids)).all()
            scraped_count = 0
            
            for i, player in enumerate(players):
                profile_scrape_progress[category_slug] = {
                    'percent': int(((i + 1) / len(players)) * 100),
                    'current': i + 1,
                    'total': len(players),
                    'status': 'running',
                    'current_player': player.name
                }
                
                if player.player_url:
                    time.sleep(0.3)
                    profile_data = scraper.scrape_player_profile(player.player_url)
                    
                    if profile_data:
                        if profile_data.get('born'):
                            player.born = profile_data['born']
                        if profile_data.get('birth_place'):
                            player.birth_place = profile_data['birth_place']
                        if profile_data.get('nickname'):
                            player.nickname = profile_data['nickname']
                        if profile_data.get('role'):
                            player.role = profile_data['role']
                        if profile_data.get('batting_style'):
                            player.batting_style = profile_data['batting_style']
                        if profile_data.get('bowling_style'):
                            player.bowling_style = profile_data['bowling_style']
                        
                        player.bat_matches = profile_data.get('bat_matches')
                        player.bat_innings = profile_data.get('bat_innings')
                        player.bat_runs = profile_data.get('bat_runs')
                        player.bat_balls = profile_data.get('bat_balls')
                        player.bat_highest = profile_data.get('bat_highest')
                        player.bat_average = profile_data.get('bat_average')
                        player.bat_strike_rate = profile_data.get('bat_strike_rate')
                        player.bat_not_outs = profile_data.get('bat_not_outs')
                        player.bat_fours = profile_data.get('bat_fours')
                        player.bat_sixes = profile_data.get('bat_sixes')
                        player.bat_ducks = profile_data.get('bat_ducks')
                        player.bat_fifties = profile_data.get('bat_fifties')
                        player.bat_hundreds = profile_data.get('bat_hundreds')
                        player.bat_two_hundreds = profile_data.get('bat_two_hundreds')
                        
                        player.bowl_matches = profile_data.get('bowl_matches')
                        player.bowl_innings = profile_data.get('bowl_innings')
                        player.bowl_balls = profile_data.get('bowl_balls')
                        player.bowl_runs = profile_data.get('bowl_runs')
                        player.bowl_maidens = profile_data.get('bowl_maidens')
                        player.bowl_wickets = profile_data.get('bowl_wickets')
                        player.bowl_average = profile_data.get('bowl_average')
                        player.bowl_economy = profile_data.get('bowl_economy')
                        player.bowl_strike_rate = profile_data.get('bowl_strike_rate')
                        player.bowl_best_innings = profile_data.get('bowl_best_innings')
                        player.bowl_best_match = profile_data.get('bowl_best_match')
                        player.bowl_four_wickets = profile_data.get('bowl_four_wickets')
                        player.bowl_five_wickets = profile_data.get('bowl_five_wickets')
                        player.bowl_ten_wickets = profile_data.get('bowl_ten_wickets')
                        
                        player.batting_stats = profile_data.get('batting_stats')
                        player.bowling_stats = profile_data.get('bowling_stats')
                        player.career_timeline = profile_data.get('career_timeline')
                        
                        player.profile_scraped = True
                        player.profile_scraped_at = datetime.utcnow()
                        scraped_count += 1
                        db.session.commit()
            
            profile_scrape_progress[category_slug] = {
                'percent': 100,
                'current': len(players),
                'total': len(players),
                'status': 'complete',
                'current_player': '',
                'scraped': scraped_count
            }
            
            log = ScrapeLog(
                category=f'{category_slug}_profiles',
                status='success',
                message=f'Scraped {scraped_count} player profiles',
                players_scraped=scraped_count
            )
            db.session.add(log)
            db.session.commit()
            
        except Exception as e:
            profile_scrape_progress[category_slug] = {
                'percent': 0, 'current': 0, 'total': 0, 
                'status': 'error', 'current_player': '', 'error': str(e)
            }

@app.route('/api/scrape/profiles/<category_slug>', methods=['POST'])
def scrape_category_profiles(category_slug):
    try:
        if profile_scrape_progress.get(category_slug, {}).get('status') == 'running':
            return jsonify({'success': False, 'message': 'Profile scraping already in progress'}), 400
        
        category = TeamCategory.query.filter_by(slug=category_slug).first()
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'}), 404
        
        teams = Team.query.filter_by(category_id=category.id).all()
        team_ids = [t.id for t in teams]
        
        players = Player.query.filter(Player.team_id.in_(team_ids)).filter(Player.player_url.isnot(None)).all()
        
        if not players:
            return jsonify({'success': False, 'message': 'No players to scrape'}), 400
        
        player_ids = [p.id for p in players]
        
        profile_scrape_progress[category_slug] = {
            'percent': 0,
            'current': 0,
            'total': len(players),
            'status': 'running',
            'current_player': 'Starting...'
        }
        
        thread = threading.Thread(target=scrape_profiles_task, args=(category_slug, player_ids))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Started scraping {len(players)} player profiles in background',
            'total': len(players)
        })
    
    except Exception as e:
        profile_scrape_progress[category_slug] = {'percent': 0, 'current': 0, 'total': 0, 'status': 'error', 'current_player': ''}
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/profile-auto-scrape', methods=['POST'])
def toggle_profile_auto_scrape():
    try:
        data = request.get_json() or {}
        category = data.get('category', '')
        enabled = data.get('enabled', False)
        scrape_time = data.get('scrape_time', '03:00')
        
        if category not in ['international', 'domestic', 'league', 'women']:
            return jsonify({'success': False, 'message': 'Invalid category'}), 400
        
        setting = ProfileScrapeSetting.query.filter_by(category_slug=category).first()
        if setting:
            setting.auto_scrape_enabled = enabled
            setting.scrape_time = scrape_time
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{category.title()} profile auto scrape {"enabled" if enabled else "disabled"} at {scrape_time}'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/profile-scrape')
def get_profile_scrape_settings():
    settings = ProfileScrapeSetting.query.all()
    return jsonify({s.category_slug: {'enabled': s.auto_scrape_enabled, 'time': s.scrape_time} for s in settings})

series_scrape_progress = {}

@app.route('/api/scrape/series-json', methods=['POST'])
def scrape_series_json():
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if not url:
            return jsonify({'success': False, 'message': 'URL required'}), 400
        
        series_id_from_url = None
        series_name_from_url = None
        url_match = re.search(r'/cricket-series/(\d+)/([^/]+)', url)
        if url_match:
            series_id_from_url = url_match.group(1)
            series_name_from_url = url_match.group(2).replace('-', ' ').lower()
        
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        }, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'success': False, 'message': 'Failed to fetch URL'}), 400
        
        html = response.text.replace('\\"', '"')
        
        is_matches_url = '/matches' in url
        
        if is_matches_url:
            matches_data = []
            seen_ids = set()
            
            match_blocks = re.finditer(r'"matchDetailsMap"\s*:\s*\{\s*"key"\s*:\s*"([^"]+)"[^}]*"match"\s*:\s*\[', html)
            date_map = {}
            for mb in match_blocks:
                date_key = mb.group(1)
                block_start = mb.start()
                block_context = html[block_start:block_start+5000]
                match_ids = re.findall(r'"matchId"\s*:\s*(\d+)', block_context)
                for mid in match_ids:
                    date_map[mid] = date_key
            
            match_positions = [(m.start(), m.group(1)) for m in re.finditer(r'"matchInfo"\s*:\s*\{[^}]*"matchId"\s*:\s*(\d+)', html)]
            
            for pos, mid in match_positions:
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
                
                # Bound context by next matchInfo to prevent data contamination
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
                
                # Extract team info with IDs - ID verification is important
                team1_name = re.search(r'"team1"\s*:\s*\{[^}]*"teamName"\s*:\s*"([^"]*)"', context)
                team2_name = re.search(r'"team2"\s*:\s*\{[^}]*"teamName"\s*:\s*"([^"]*)"', context)
                team1_id = re.search(r'"team1"\s*:\s*\{[^}]*"teamId"\s*:\s*(\d+)', context)
                team2_id = re.search(r'"team2"\s*:\s*\{[^}]*"teamId"\s*:\s*(\d+)', context)
                
                venue_ground = re.search(r'"venueInfo"\s*:\s*\{[^}]*"ground"\s*:\s*"([^"]*)"', context)
                venue_city = re.search(r'"venueInfo"\s*:\s*\{[^}]*"city"\s*:\s*"([^"]*)"', context)
                venue_id = re.search(r'"venueInfo"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', context)
                
                team1_score = ''
                team2_score = ''
                match_state = state.group(1) if state else ''
                
                if match_state not in ['Preview', 'Upcoming', 'Scheduled', '']:
                    # ACCURATE METHOD: Search for matchScoreMap with specific matchId
                    # This ensures we get scores only for THIS match
                    score_pattern = rf'"matchScoreMap"\s*:\s*\{{\s*"{mid}"\s*:\s*\{{[^}}]*"team1Score"\s*:\s*\{{[^}}]*"inngs1"\s*:\s*\{{([^}}]+)\}}'
                    t1_verified = re.search(score_pattern, html)
                    
                    if t1_verified:
                        sb = t1_verified.group(1)
                        runs = re.search(r'"runs"\s*:\s*(\d+)', sb)
                        wkts = re.search(r'"wickets"\s*:\s*(\d+)', sb)
                        overs = re.search(r'"overs"\s*:\s*([\d.]+)', sb)
                        if runs:
                            team1_score = f"{runs.group(1)}/{wkts.group(1) if wkts else '?'}"
                            if overs:
                                team1_score += f" ({overs.group(1)})"
                    else:
                        # Fallback to context-based extraction for T1 only
                        t1_score_block = re.search(r'"team1Score"\s*:\s*\{[^{]*"inngs1"\s*:\s*\{([^}]+)\}', context)
                        if t1_score_block:
                            sb = t1_score_block.group(1)
                            runs = re.search(r'"runs"\s*:\s*(\d+)', sb)
                            wkts = re.search(r'"wickets"\s*:\s*(\d+)', sb)
                            overs = re.search(r'"overs"\s*:\s*([\d.]+)', sb)
                            if runs:
                                team1_score = f"{runs.group(1)}/{wkts.group(1) if wkts else '?'}"
                                if overs:
                                    team1_score += f" ({overs.group(1)})"
                    
                    # T2 Score - search with matchId verification
                    score_pattern2 = rf'"matchScoreMap"\s*:\s*\{{\s*"{mid}"\s*:\s*\{{[^}}]*"team2Score"\s*:\s*\{{[^}}]*"inngs1"\s*:\s*\{{([^}}]+)\}}'
                    t2_verified = re.search(score_pattern2, html)
                    
                    if t2_verified:
                        sb = t2_verified.group(1)
                        runs = re.search(r'"runs"\s*:\s*(\d+)', sb)
                        wkts = re.search(r'"wickets"\s*:\s*(\d+)', sb)
                        overs = re.search(r'"overs"\s*:\s*([\d.]+)', sb)
                        if runs:
                            team2_score = f"{runs.group(1)}/{wkts.group(1) if wkts else '?'}"
                            if overs:
                                team2_score += f" ({overs.group(1)})"
                    else:
                        # For T2, only use context if it appears BEFORE any other matchInfo
                        # This prevents picking up scores from related matches
                        if context.count('"team2Score"') == 1:
                            t2_score_block = re.search(r'"team2Score"\s*:\s*\{[^{]*"inngs1"\s*:\s*\{([^}]+)\}', context)
                            if t2_score_block:
                                sb = t2_score_block.group(1)
                                runs = re.search(r'"runs"\s*:\s*(\d+)', sb)
                                wkts = re.search(r'"wickets"\s*:\s*(\d+)', sb)
                                overs = re.search(r'"overs"\s*:\s*([\d.]+)', sb)
                                if runs:
                                    team2_score = f"{runs.group(1)}/{wkts.group(1) if wkts else '?'}"
                                    if overs:
                                        team2_score += f" ({overs.group(1)})"
                
                match_date = date_map.get(mid, '')
                date_timestamp = 0
                if start_date:
                    try:
                        from datetime import datetime as dt
                        ts = int(start_date.group(1)) / 1000
                        date_timestamp = ts
                        if not match_date:
                            match_date = dt.fromtimestamp(ts).strftime('%a, %d %b %Y')
                    except:
                        pass
                
                venue = ''
                if venue_ground and venue_city:
                    venue = f"{venue_ground.group(1)}, {venue_city.group(1)}"
                elif venue_ground:
                    venue = venue_ground.group(1)
                
                match_series_name = series_name.group(1) if series_name else ''
                
                if series_name_from_url:
                    match_series_lower = match_series_name.lower().replace(',', '').replace("'", '')
                    if series_name_from_url not in match_series_lower and match_series_lower not in series_name_from_url:
                        continue
                
                team1_short = team1_name.group(1) if team1_name else ''
                team2_short = team2_name.group(1) if team2_name else ''
                match_slug = f"{team1_short.lower().replace(' ', '-')}-vs-{team2_short.lower().replace(' ', '-')}"
                match_url = f"https://www.cricbuzz.com/live-cricket-scorecard/{mid}/{match_slug}"
                
                # Get series_id from context for verification
                match_series_id = match_sid.group(1) if match_sid else series_id_from_url or ''
                
                matches_data.append({
                    # PRIMARY IDs - Most important for verification
                    'match_id': mid,
                    'series_id': match_series_id,
                    'team1_id': team1_id.group(1) if team1_id else '',
                    'team2_id': team2_id.group(1) if team2_id else '',
                    'venue_id': venue_id.group(1) if venue_id else '',
                    # Match info
                    'match_format': match_desc.group(1) if match_desc else '',
                    'format_type': match_format.group(1) if match_format else '',
                    'series_name': match_series_name,
                    'match_date': match_date,
                    'date_timestamp': date_timestamp,
                    'state': match_state,
                    # Team names
                    'team1': team1_short,
                    'team2': team2_short,
                    # Scores
                    'team1_score': team1_score,
                    'team2_score': team2_score,
                    # Other info
                    'venue': venue,
                    'result': status.group(1) if status else '',
                    'match_url': match_url
                })
            
            matches_data.sort(key=lambda x: x.get('date_timestamp', 0))
            
            # AUTO-SAVE: Dynamically save all matches to database
            saved_count = 0
            updated_count = 0
            for match in matches_data:
                if match.get('match_id'):
                    existing = Match.query.filter_by(match_id=str(match['match_id'])).first()
                    upsert_match(match)
                    if existing:
                        updated_count += 1
                    else:
                        saved_count += 1
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error saving matches: {e}")
            
            return jsonify({
                'success': True,
                'type': 'matches',
                'matches': matches_data,
                'count': len(matches_data),
                'saved': saved_count,
                'updated': updated_count
            })
        
        else:
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
                                    'month_year': month_year.title() if month_year else ''
                                })
                except Exception as e:
                    pass
            
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
                        series_data.append({'id': sid, 'name': name, 'url': series_url, 'month_year': ''})
            
            return jsonify({
                'success': True,
                'type': 'series',
                'series': series_data,
                'count': len(series_data)
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scrape/match-json', methods=['POST'])
def scrape_match_json():
    try:
        data = request.get_json()
        url = data.get('url', '')
        match_id = data.get('match_id', '')
        
        if match_id:
            url = f"https://www.cricbuzz.com/live-cricket-scorecard/{match_id}"
        
        if not url:
            return jsonify({'success': False, 'message': 'URL or match_id required'}), 400
        
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        }, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'success': False, 'message': 'Failed to fetch URL'}), 400
        
        html = response.text.replace('\\"', '"')
        
        match_data = {}
        
        header_match = re.search(r'"matchHeader"\s*:\s*\{([^{]*(?:\{[^}]*\}[^{]*)*)\}', html)
        match_state = ''
        if header_match:
            header = header_match.group(1)
            
            # Extract all IDs from matchHeader
            mid = re.search(r'"matchId"\s*:\s*(\d+)', header)
            series_id = re.search(r'"seriesId"\s*:\s*(\d+)', header)
            match_desc = re.search(r'"matchDescription"\s*:\s*"([^"]*)"', header)
            match_format = re.search(r'"matchFormat"\s*:\s*"([^"]*)"', header)
            status = re.search(r'"status"\s*:\s*"([^"]*)"', header)
            state = re.search(r'"state"\s*:\s*"([^"]*)"', header)
            toss_winner = re.search(r'"tossWinnerName"\s*:\s*"([^"]*)"', header)
            toss_decision = re.search(r'"decision"\s*:\s*"([^"]*)"', header)
            
            # Team IDs from header
            team1_id = re.search(r'"team1"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', header)
            team2_id = re.search(r'"team2"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', header)
            
            # PRIMARY IDs - Most important
            match_data['match_id'] = mid.group(1) if mid else match_id
            match_data['series_id'] = series_id.group(1) if series_id else ''
            match_data['team1_id'] = team1_id.group(1) if team1_id else ''
            match_data['team2_id'] = team2_id.group(1) if team2_id else ''
            
            # Match info
            match_data['match'] = match_desc.group(1) if match_desc else ''
            match_data['format'] = match_format.group(1) if match_format else ''
            match_data['status'] = status.group(1) if status else ''
            match_state = state.group(1) if state else ''
            match_data['state'] = match_state
            match_data['toss'] = f"{toss_winner.group(1)} won toss, chose to {toss_decision.group(1)}" if toss_winner and toss_decision else ''
        
        series_match = re.search(r'"seriesDesc"\s*:\s*"([^"]*)"', html)
        match_data['series'] = series_match.group(1) if series_match else ''
        
        venue_ground = re.search(r'"ground"\s*:\s*"([^"]*)"', html)
        venue_city = re.search(r'"city"\s*:\s*"([^"]*)"', html)
        venue_id = re.search(r'"venueInfo"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', html)
        match_data['venue'] = f"{venue_ground.group(1)}, {venue_city.group(1)}" if venue_ground and venue_city else ''
        match_data['venue_id'] = venue_id.group(1) if venue_id else ''
        
        if match_state in ['Preview', 'Upcoming', 'Scheduled']:
            match_data['team1'] = ''
            match_data['team2'] = ''
            match_data['team1_score'] = 'Match not started'
            match_data['team2_score'] = 'Match not started'
            match_data['batting'] = []
            match_data['bowling'] = []
            return jsonify({'success': True, 'data': match_data})
        
        target_match_id = match_data.get('match_id', match_id)
        scorecard_pattern = rf'"scoreCard"\s*:\s*\[\s*\{{\s*"matchId"\s*:\s*{target_match_id}'
        scorecard_match = re.search(scorecard_pattern, html)
        
        if not scorecard_match:
            match_data['team1'] = ''
            match_data['team2'] = ''
            match_data['team1_score'] = 'No scorecard available'
            match_data['team2_score'] = 'No scorecard available'
            match_data['batting'] = []
            match_data['bowling'] = []
            return jsonify({'success': True, 'data': match_data})
        
        scorecard_start = scorecard_match.start()
        if scorecard_start != -1:
            scorecard_section = html[scorecard_start:scorecard_start+80000]
            
            innings_data = []
            innings_pattern = r'"inningsId"\s*:\s*(\d+)[^{]*"batTeamDetails"\s*:\s*\{[^}]*"batTeamName"\s*:\s*"([^"]*)"'
            for m in re.finditer(innings_pattern, scorecard_section):
                innings_data.append({'id': m.group(1), 'team': m.group(2), 'pos': m.start()})
            
            if len(innings_data) >= 1:
                match_data['team1'] = innings_data[0]['team']
                inn1_start = innings_data[0]['pos']
                inn1_end = innings_data[1]['pos'] if len(innings_data) > 1 else inn1_start + 20000
                inn1_section = scorecard_section[inn1_start:inn1_end]
                
                score_match = re.search(r'"scoreDetails"\s*:\s*\{[^}]*"overs"\s*:\s*([\d.]+)[^}]*"runs"\s*:\s*(\d+)[^}]*"wickets"\s*:\s*(\d+)', inn1_section)
                if score_match:
                    match_data['team1_score'] = f"{score_match.group(2)}/{score_match.group(3)} ({score_match.group(1)})"
            
            if len(innings_data) >= 2:
                match_data['team2'] = innings_data[1]['team']
                inn2_start = innings_data[1]['pos']
                inn2_end = innings_data[2]['pos'] if len(innings_data) > 2 else inn2_start + 20000
                inn2_section = scorecard_section[inn2_start:inn2_end]
                
                score_match = re.search(r'"scoreDetails"\s*:\s*\{[^}]*"overs"\s*:\s*([\d.]+)[^}]*"runs"\s*:\s*(\d+)[^}]*"wickets"\s*:\s*(\d+)', inn2_section)
                if score_match:
                    match_data['team2_score'] = f"{score_match.group(2)}/{score_match.group(3)} ({score_match.group(1)})"
            
            batting = []
            bat_pattern = r'"batId":(\d+),"batName":"([^"]*)"[^}]*?"runs":(\d+),"balls":(\d+),"dots":(\d+),"fours":(\d+),"sixes":(\d+)[^}]*?"strikeRate":([\d.]+),"outDesc":"([^"]*)"'
            bat_matches = re.finditer(bat_pattern, scorecard_section)
            seen_batters = set()
            for m in bat_matches:
                bat_id = m.group(1)
                if bat_id not in seen_batters:
                    seen_batters.add(bat_id)
                    batting.append({
                        'player_id': bat_id,  # Primary ID for verification
                        'name': m.group(2),
                        'runs': m.group(3),
                        'balls': m.group(4),
                        'dots': m.group(5),
                        'fours': m.group(6),
                        'sixes': m.group(7),
                        'sr': m.group(8),
                        'status': m.group(9)
                    })
            match_data['batting'] = batting
            
            bowling = []
            bowl_pattern = r'"bowlerId":(\d+),"bowlName":"([^"]*)"[^}]*?"overs":([\d.]+),"maidens":(\d+),"runs":(\d+),"wickets":(\d+),"economy":([\d.]+)'
            bowl_matches = re.finditer(bowl_pattern, scorecard_section)
            seen_bowlers = set()
            for m in bowl_matches:
                bowl_id = m.group(1)
                if bowl_id not in seen_bowlers:
                    seen_bowlers.add(bowl_id)
                    bowling.append({
                        'player_id': bowl_id,  # Primary ID for verification
                        'name': m.group(2),
                        'overs': m.group(3),
                        'maidens': m.group(4),
                        'runs': m.group(5),
                        'wickets': m.group(6),
                        'economy': m.group(7)
                    })
            match_data['bowling'] = bowling
        else:
            match_data['batting'] = []
            match_data['bowling'] = []
        
        # AUTO-SAVE: Dynamically save match to database
        is_new = False
        if match_data.get('match_id'):
            existing = Match.query.filter_by(match_id=str(match_data['match_id'])).first()
            is_new = existing is None
            upsert_match(match_data)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error saving match: {e}")
        
        return jsonify({
            'success': True,
            'data': match_data,
            'saved': is_new,
            'updated': not is_new
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/save/series-matches', methods=['POST'])
def save_series_matches():
    """Save scraped series and matches to database"""
    try:
        data = request.get_json()
        series_list = data.get('series', [])
        matches_list = data.get('matches', [])
        series_url = data.get('series_url', '')
        
        saved_series = 0
        saved_matches = 0
        
        if series_list:
            for s in series_list:
                series_id = s.get('id', '')
                if not series_id:
                    continue
                
                category = SeriesCategory.query.filter_by(slug='international').first()
                if not category:
                    category = SeriesCategory.query.first()
                
                existing = Series.query.filter_by(series_id=series_id).first()
                if existing:
                    existing.name = s.get('name', '')
                    existing.series_url = s.get('url', '')
                    existing.date_range = s.get('month_year', '')
                else:
                    new_series = Series(
                        series_id=series_id,
                        name=s.get('name', ''),
                        series_url=s.get('url', ''),
                        date_range=s.get('month_year', ''),
                        category_id=category.id if category else 1
                    )
                    db.session.add(new_series)
                saved_series += 1
            
            db.session.commit()
        
        if matches_list:
            series_id_from_url = None
            if series_url:
                m = re.search(r'/cricket-series/(\d+)/', series_url)
                if m:
                    series_id_from_url = m.group(1)
            
            series = None
            if series_id_from_url:
                series = Series.query.filter_by(series_id=series_id_from_url).first()
            
            for match in matches_list:
                match_id = match.get('match_id', '')
                if not match_id:
                    continue
                
                existing = Match.query.filter_by(match_id=match_id).first()
                if existing:
                    existing.match_format = match.get('match_format', '')
                    existing.venue = match.get('venue', '')
                    existing.match_date = match.get('match_date', '')
                    existing.team1_name = match.get('team1', '')
                    existing.team1_score = match.get('team1_score', '')
                    existing.team2_name = match.get('team2', '')
                    existing.team2_score = match.get('team2_score', '')
                    existing.result = match.get('result', '')
                else:
                    new_match = Match(
                        match_id=match_id,
                        match_format=match.get('match_format', ''),
                        venue=match.get('venue', ''),
                        match_date=match.get('match_date', ''),
                        team1_name=match.get('team1', ''),
                        team1_score=match.get('team1_score', ''),
                        team2_name=match.get('team2', ''),
                        team2_score=match.get('team2_score', ''),
                        result=match.get('result', ''),
                        match_url=match.get('match_url', ''),
                        series_id=series.id if series else None
                    )
                    db.session.add(new_match)
                saved_matches += 1
            
            db.session.commit()
        
        return jsonify({
            'success': True,
            'saved_series': saved_series,
            'saved_matches': saved_matches
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/save/series-bulk', methods=['POST'])
def save_series_bulk():
    """Auto-save scraped series to database"""
    try:
        data = request.get_json()
        series_list = data.get('series', [])
        url = data.get('url', '')
        
        # Determine category from URL
        category_slug = 'international'
        if '/domestic' in url:
            category_slug = 'domestic'
        elif '/league' in url:
            category_slug = 'league'
        elif '/women' in url:
            category_slug = 'women'
        elif '/all' in url:
            category_slug = 'all'
        
        category = SeriesCategory.query.filter_by(slug=category_slug).first()
        if not category:
            category = SeriesCategory.query.first()
        
        saved = 0
        updated = 0
        
        for s in series_list:
            series_id = s.get('id', '')
            if not series_id:
                continue
            
            existing = Series.query.filter_by(series_id=series_id).first()
            if existing:
                existing.name = s.get('name', existing.name)
                existing.series_url = s.get('url', existing.series_url)
                existing.date_range = s.get('month_year', existing.date_range)
                updated += 1
            else:
                new_series = Series(
                    series_id=series_id,
                    name=s.get('name', ''),
                    series_url=s.get('url', ''),
                    date_range=s.get('month_year', ''),
                    category_id=category.id if category else 1
                )
                db.session.add(new_series)
                saved += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'saved': saved,
            'updated': updated,
            'message': f'Saved {saved} new, updated {updated} series'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scrape/series/<category_slug>', methods=['POST'])
def scrape_series(category_slug):
    try:
        if category_slug not in scraper.SERIES_CATEGORIES:
            return jsonify({'success': False, 'message': 'Invalid category'}), 400
        
        category = SeriesCategory.query.filter_by(slug=category_slug).first()
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'}), 404
        
        category_url = scraper.SERIES_CATEGORIES[category_slug]['url']
        series_list = scraper.scrape_series_from_category(category_url)
        
        if not series_list:
            return jsonify({'success': False, 'message': 'No series found'}), 404
        
        series_scraped = 0
        series_updated = 0
        for series_data in series_list:
            if not series_data.get('series_id'):
                continue
            
            existing = Series.query.filter_by(series_id=series_data['series_id']).first()
            if existing:
                existing.name = series_data.get('name', existing.name)
                existing.series_url = series_data.get('series_url', existing.series_url)
                existing.start_date = series_data.get('start_date', existing.start_date)
                existing.end_date = series_data.get('end_date', existing.end_date)
                existing.date_range = series_data.get('date_range', existing.date_range)
                existing.category_id = category.id
                existing.updated_at = datetime.utcnow()
                series_updated += 1
            else:
                series = Series(
                    series_id=series_data['series_id'],
                    name=series_data['name'],
                    series_url=series_data['series_url'],
                    start_date=series_data.get('start_date'),
                    end_date=series_data.get('end_date'),
                    date_range=series_data.get('date_range'),
                    category_id=category.id
                )
                db.session.add(series)
                series_scraped += 1
        
        db.session.commit()
        
        total = series_scraped + series_updated
        log = ScrapeLog(
            category=f'series_{category_slug}',
            status='success',
            message=f'Saved {series_scraped} new, updated {series_updated} series',
            teams_scraped=total
        )
        db.session.add(log)
        db.session.commit()
        
        setting = SeriesScrapeSetting.query.filter_by(category_slug=category_slug).first()
        if setting:
            setting.last_scrape = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Saved {series_scraped} new series, updated {series_updated} existing',
            'series_scraped': series_scraped,
            'series_updated': series_updated
        })
    
    except Exception as e:
        log = ScrapeLog(
            category=f'series_{category_slug}',
            status='error',
            message=str(e)
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': False, 'message': str(e)}), 500

match_update_progress = {}

@app.route('/api/matches/update-accurate', methods=['POST'])
def update_all_matches_accurate():
    """Update all matches with accurate data from individual match pages"""
    try:
        data = request.get_json() or {}
        series_id = data.get('series_id')
        
        if series_id:
            matches = Match.query.filter_by(series_id=series_id).all()
        else:
            matches = Match.query.all()
        
        if not matches:
            return jsonify({'success': False, 'message': 'No matches found'}), 404
        
        updated_count = 0
        for match in matches:
            try:
                accurate_data = scraper.update_match_with_accurate_data(match.match_id)
                
                if accurate_data:
                    if accurate_data.get('match_format'):
                        match.match_format = accurate_data['match_format']
                    if accurate_data.get('venue'):
                        match.venue = accurate_data['venue']
                    if accurate_data.get('match_date'):
                        match.match_date = accurate_data['match_date']
                    if accurate_data.get('team1_name'):
                        match.team1_name = accurate_data['team1_name']
                    if accurate_data.get('team1_score'):
                        match.team1_score = accurate_data['team1_score']
                    if accurate_data.get('team2_name'):
                        match.team2_name = accurate_data['team2_name']
                    if accurate_data.get('team2_score'):
                        match.team2_score = accurate_data['team2_score']
                    if accurate_data.get('result'):
                        match.result = accurate_data['result']
                    
                    match.updated_at = datetime.utcnow()
                    updated_count += 1
                
                import time
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error updating match {match.match_id}: {e}")
                continue
        
        db.session.commit()
        
        log = ScrapeLog(
            category='matches_update_accurate',
            status='success',
            message=f'Updated {updated_count} matches with accurate data',
            teams_scraped=updated_count
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} matches with accurate data',
            'updated': updated_count
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/match/<match_id>/update-accurate', methods=['POST'])
def update_single_match_accurate(match_id):
    """Update a single match with accurate data"""
    try:
        match = Match.query.filter_by(match_id=match_id).first()
        if not match:
            return jsonify({'success': False, 'message': 'Match not found'}), 404
        
        accurate_data = scraper.update_match_with_accurate_data(match_id)
        
        if accurate_data:
            if accurate_data.get('match_format'):
                match.match_format = accurate_data['match_format']
            if accurate_data.get('venue'):
                match.venue = accurate_data['venue']
            if accurate_data.get('match_date'):
                match.match_date = accurate_data['match_date']
            if accurate_data.get('team1_name'):
                match.team1_name = accurate_data['team1_name']
            if accurate_data.get('team1_score'):
                match.team1_score = accurate_data['team1_score']
            if accurate_data.get('team2_name'):
                match.team2_name = accurate_data['team2_name']
            if accurate_data.get('team2_score'):
                match.team2_score = accurate_data['team2_score']
            if accurate_data.get('result'):
                match.result = accurate_data['result']
            
            match.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Match updated with accurate data',
                'data': accurate_data
            })
        
        return jsonify({'success': False, 'message': 'Could not fetch accurate data'}), 500
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

match_scrape_progress = {}

@app.route('/api/series/<int:series_id>/matches')
def get_series_matches(series_id):
    try:
        matches = Match.query.filter_by(series_id=series_id).order_by(Match.id).all()
        return jsonify({
            'matches': [{
                'id': m.id,
                'match_id': m.match_id,
                'match_format': m.match_format,
                'match_date': m.match_date,
                'team1_name': m.team1_name,
                'team2_name': m.team2_name,
                'team1_score': m.team1_score,
                'team2_score': m.team2_score,
                'venue': m.venue,
                'result': m.result
            } for m in matches]
        })
    except Exception as e:
        return jsonify({'matches': [], 'error': str(e)})

@app.route('/api/scrape/matches/<int:series_id>', methods=['POST'])
def scrape_matches(series_id):
    try:
        series = Series.query.get(series_id)
        if not series:
            return jsonify({'success': False, 'message': 'Series not found'}), 404
        
        matches_list = scraper.scrape_matches_from_series(series.series_url)
        
        if not matches_list:
            return jsonify({'success': False, 'message': 'No matches found'}), 404
        
        matches_scraped = 0
        
        # Generate dates based on match format order
        from datetime import datetime as dt, timedelta
        base_date = dt(2026, 1, 15)  # Default start date
        if series.start_date:
            try:
                base_date = dt.strptime(series.start_date, '%Y-%m-%d')
            except:
                pass
        
        # Sort matches by format for proper date assignment
        format_order = {'1st ODI': 0, '2nd ODI': 1, '3rd ODI': 2, '1st T20I': 3, '2nd T20I': 4, '3rd T20I': 5, '4th T20I': 6, '5th T20I': 7, '1st Test': 0, '2nd Test': 1, '3rd Test': 2}
        
        for idx, match_data in enumerate(matches_list):
            match_id = match_data['match_id']
            match_format = match_data.get('match_format', '')
            
            # Generate date if not provided
            match_date = match_data.get('match_date', '')
            if not match_date:
                format_idx = format_order.get(match_format, idx)
                match_dt = base_date + timedelta(days=format_idx * 3)
                match_date = match_dt.strftime('%b %d, %Y')
            
            existing = Match.query.filter_by(match_id=match_id).first()
            if existing:
                existing.match_format = match_format
                existing.venue = match_data.get('venue')
                if match_date:
                    existing.match_date = match_date
                existing.team1_name = match_data.get('team1_name')
                existing.team1_score = match_data.get('team1_score')
                existing.team2_name = match_data.get('team2_name')
                existing.team2_score = match_data.get('team2_score')
                existing.result = match_data.get('result')
                existing.match_url = match_data.get('match_url')
                existing.updated_at = datetime.utcnow()
            else:
                match = Match(
                    match_id=match_id,
                    match_format=match_format,
                    venue=match_data.get('venue'),
                    match_date=match_date,
                    team1_name=match_data.get('team1_name'),
                    team1_score=match_data.get('team1_score'),
                    team2_name=match_data.get('team2_name'),
                    team2_score=match_data.get('team2_score'),
                    result=match_data.get('result'),
                    match_url=match_data.get('match_url'),
                    series_id=series_id
                )
                db.session.add(match)
            matches_scraped += 1
        
        db.session.commit()
        
        log = ScrapeLog(
            category=f'matches_{series.name[:30]}',
            status='success',
            message=f'Scraped {matches_scraped} matches',
            teams_scraped=matches_scraped
        )
        db.session.add(log)
        db.session.commit()
        
        setting = MatchScrapeSetting.query.first()
        if setting:
            setting.last_scrape = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scraped {matches_scraped} matches successfully',
            'matches_scraped': matches_scraped
        })
    
    except Exception as e:
        log = ScrapeLog(
            category=f'matches_error',
            status='error',
            message=str(e)
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scrape/update-all-scores', methods=['POST'])
def update_all_match_scores():
    """Update scores for all matches in database from scorecards"""
    try:
        matches = Match.query.filter(
            (Match.team1_score == None) | (Match.team1_score == '') |
            (Match.team2_score == None) | (Match.team2_score == '')
        ).all()
        
        updated_count = 0
        for match in matches:
            if not match.match_id:
                continue
            
            scores = scraper.update_match_scores(match.match_id)
            if scores:
                if scores.get('team1_name'):
                    match.team1_name = scores['team1_name']
                if scores.get('team2_name'):
                    match.team2_name = scores['team2_name']
                if scores.get('team1_score'):
                    match.team1_score = scores['team1_score']
                if scores.get('team2_score'):
                    match.team2_score = scores['team2_score']
                if scores.get('result'):
                    match.result = scores['result']
                match.updated_at = datetime.utcnow()
                updated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} matches with scores',
            'updated_count': updated_count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/match-auto-scrape', methods=['POST'])
def toggle_match_auto_scrape():
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', False)
        time = data.get('time', '10:00')
        
        setting = MatchScrapeSetting.query.first()
        if not setting:
            setting = MatchScrapeSetting(auto_scrape_enabled=enabled, scrape_time=time)
            db.session.add(setting)
        else:
            setting.auto_scrape_enabled = enabled
            setting.scrape_time = time
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Match auto-scrape {"enabled" if enabled else "disabled"}',
            'enabled': enabled,
            'time': time
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/match-scrape', methods=['GET'])
def get_match_scrape_settings():
    setting = MatchScrapeSetting.query.first()
    if setting:
        return jsonify({
            'enabled': setting.auto_scrape_enabled,
            'time': setting.scrape_time,
            'last_scrape': setting.last_scrape.isoformat() if setting.last_scrape else None
        })
    return jsonify({'enabled': False, 'time': '10:00', 'last_scrape': None})

@app.route('/api/settings/series-auto-scrape', methods=['POST'])
def toggle_series_auto_scrape():
    try:
        data = request.get_json() or {}
        category = data.get('category', '')
        enabled = data.get('enabled', False)
        scrape_time = data.get('scrape_time', '08:00')
        
        if category not in ['all', 'international', 'domestic', 'league', 'women']:
            return jsonify({'success': False, 'message': 'Invalid category'}), 400
        
        setting = SeriesScrapeSetting.query.filter_by(category_slug=category).first()
        if setting:
            setting.auto_scrape_enabled = enabled
            setting.scrape_time = scrape_time
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{category.title()} series auto scrape {"enabled" if enabled else "disabled"} at {scrape_time}'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/series-scrape')
def get_series_scrape_settings():
    settings = SeriesScrapeSetting.query.all()
    return jsonify({s.category_slug: {'enabled': s.auto_scrape_enabled, 'time': s.scrape_time, 'last_scrape': s.last_scrape.isoformat() if s.last_scrape else None} for s in settings})

@app.route('/api/scrape/live-scores', methods=['POST'])
def scrape_live_scores_api():
    """Scrape all matches from Cricbuzz live-scores page and save to database"""
    try:
        result = scraper.scrape_live_scores()
        if not result.get('success'):
            return jsonify(result), 500
        
        saved = 0
        updated = 0
        
        for match_data in result.get('matches', []):
            if not match_data.get('match_id'):
                continue
            
            existing = Match.query.filter_by(match_id=match_data['match_id']).first()
            
            if existing:
                existing.team1_name = match_data.get('team1', existing.team1_name)
                existing.team2_name = match_data.get('team2', existing.team2_name)
                existing.match_format = match_data.get('match_format', existing.match_format)
                existing.state = match_data.get('status', existing.state)
                existing.match_url = match_data.get('match_url', existing.match_url)
                existing.cricbuzz_series_id = match_data.get('series_id', existing.cricbuzz_series_id)
                existing.team1_score = match_data.get('team1_score') or existing.team1_score
                existing.team2_score = match_data.get('team2_score') or existing.team2_score
                existing.result = match_data.get('result') or existing.result
                existing.updated_at = datetime.utcnow()
                updated += 1
            else:
                new_match = Match(
                    match_id=match_data['match_id'],
                    team1_name=match_data.get('team1', ''),
                    team2_name=match_data.get('team2', ''),
                    match_format=match_data.get('match_format', ''),
                    state=match_data.get('status', 'Upcoming'),
                    match_url=match_data.get('match_url', ''),
                    cricbuzz_series_id=match_data.get('series_id'),
                    team1_score=match_data.get('team1_score', ''),
                    team2_score=match_data.get('team2_score', ''),
                    result=match_data.get('result', '')
                )
                db.session.add(new_match)
                saved += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'saved': saved,
            'updated': updated,
            'counts': result.get('counts', {}),
            'matches': result.get('matches', [])
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/matches/clear', methods=['POST'])
def clear_all_matches():
    try:
        count = Match.query.count()
        Match.query.delete()
        db.session.commit()
        return jsonify({'success': True, 'message': f'{count} matches deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/categories')
def admin_categories():
    categories = PostCategory.query.order_by(PostCategory.navbar_order).all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/posts')
def admin_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    categories = PostCategory.query.order_by(PostCategory.name).all()
    return render_template('admin/posts.html', posts=posts, categories=categories)

@app.route('/admin/posts/new')
def admin_post_new():
    categories = PostCategory.query.order_by(PostCategory.name).all()
    return render_template('admin/post_edit.html', post=None, categories=categories)

@app.route('/admin/posts/<int:post_id>')
def admin_post_edit(post_id):
    post = Post.query.get_or_404(post_id)
    categories = PostCategory.query.order_by(PostCategory.name).all()
    return render_template('admin/post_edit.html', post=post, categories=categories)

@app.route('/api/categories', methods=['POST'])
def api_create_category():
    try:
        data = request.json
        if not data.get('name') or not data.get('slug'):
            return jsonify({'success': False, 'message': 'Name and slug are required'}), 400
        
        existing = PostCategory.query.filter_by(slug=data['slug']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Category with this slug already exists'}), 400
        
        category = PostCategory(
            name=data['name'],
            slug=data['slug'],
            description=data.get('description', ''),
            show_in_navbar=data.get('show_in_navbar', True),
            navbar_order=data.get('navbar_order', 0)
        )
        db.session.add(category)
        db.session.commit()
        return jsonify({'success': True, 'id': category.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/categories/<int:cat_id>', methods=['PUT'])
def api_update_category(cat_id):
    try:
        category = PostCategory.query.get_or_404(cat_id)
        data = request.json
        
        if data.get('slug') and data['slug'] != category.slug:
            existing = PostCategory.query.filter_by(slug=data['slug']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Slug already exists'}), 400
        
        category.name = data.get('name', category.name)
        category.slug = data.get('slug', category.slug)
        category.description = data.get('description', category.description)
        category.show_in_navbar = data.get('show_in_navbar', category.show_in_navbar)
        category.navbar_order = data.get('navbar_order', category.navbar_order)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
def api_delete_category(cat_id):
    try:
        category = PostCategory.query.get_or_404(cat_id)
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/posts', methods=['POST'])
def api_create_post():
    try:
        data = request.json
        if not data.get('title') or not data.get('slug'):
            return jsonify({'success': False, 'message': 'Title and slug are required'}), 400
        
        existing = Post.query.filter_by(slug=data['slug']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Post with this slug already exists'}), 400
        
        post = Post(
            title=data['title'],
            slug=data['slug'],
            content=data.get('content', ''),
            excerpt=data.get('excerpt', ''),
            thumbnail=data.get('thumbnail', ''),
            category_id=data.get('category_id') if data.get('category_id') else None,
            is_published=data.get('is_published', False),
            is_featured=data.get('is_featured', False),
            meta_title=data.get('meta_title', ''),
            meta_description=data.get('meta_description', ''),
            meta_keywords=data.get('meta_keywords', ''),
            canonical_url=data.get('canonical_url', ''),
            og_title=data.get('og_title', ''),
            og_description=data.get('og_description', ''),
            author=data.get('author', 'Admin'),
            published_at=datetime.utcnow() if data.get('is_published') else None
        )
        db.session.add(post)
        db.session.commit()
        return jsonify({'success': True, 'id': post.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def api_update_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        data = request.json
        
        if data.get('slug') and data['slug'] != post.slug:
            existing = Post.query.filter_by(slug=data['slug']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Slug already exists'}), 400
        
        post.title = data.get('title', post.title)
        post.slug = data.get('slug', post.slug)
        post.content = data.get('content', post.content)
        post.excerpt = data.get('excerpt', post.excerpt)
        post.thumbnail = data.get('thumbnail', post.thumbnail)
        post.category_id = data.get('category_id') if data.get('category_id') else None
        post.is_published = data.get('is_published', post.is_published)
        post.is_featured = data.get('is_featured', post.is_featured)
        post.meta_title = data.get('meta_title', post.meta_title)
        post.meta_description = data.get('meta_description', post.meta_description)
        post.meta_keywords = data.get('meta_keywords', post.meta_keywords)
        post.canonical_url = data.get('canonical_url', post.canonical_url)
        post.og_title = data.get('og_title', post.og_title)
        post.og_description = data.get('og_description', post.og_description)
        post.author = data.get('author', post.author)
        
        if data.get('is_published') and not post.published_at:
            post.published_at = datetime.utcnow()
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def api_delete_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        db.session.delete(post)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def api_upload_file():
    import uuid
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed:
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        upload_dir = os.path.join(app.static_folder, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        url = f"/static/uploads/{filename}"
        return jsonify({'success': True, 'url': url})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/post/<slug>')
def view_post(slug):
    post = Post.query.filter_by(slug=slug, is_published=True).first_or_404()
    post.views += 1
    db.session.commit()
    
    recent_posts = Post.query.filter(Post.is_published==True, Post.id!=post.id).order_by(Post.created_at.desc()).limit(5).all()
    categories = PostCategory.query.filter_by(show_in_navbar=True).order_by(PostCategory.navbar_order).all()
    
    return render_template('post.html', post=post, recent_posts=recent_posts, categories=categories)

@app.route('/category/<slug>')
def view_category(slug):
    category = PostCategory.query.filter_by(slug=slug).first_or_404()
    posts = Post.query.filter_by(category_id=category.id, is_published=True).order_by(Post.created_at.desc()).all()
    categories = PostCategory.query.filter_by(show_in_navbar=True).order_by(PostCategory.navbar_order).all()
    recent_posts = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).limit(5).all()
    
    return render_template('category.html', category=category, posts=posts, categories=categories, recent_posts=recent_posts)

@app.context_processor
def inject_navbar_categories():
    try:
        nav_categories = PostCategory.query.filter_by(show_in_navbar=True).order_by(PostCategory.navbar_order).all()
        return dict(nav_categories=nav_categories)
    except:
        return dict(nav_categories=[])

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
