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
TeamCategory, Team, Player, ScrapeLog, ScrapeSetting, ProfileScrapeSetting, SeriesCategory, Series, SeriesScrapeSetting, Match, MatchScrapeSetting = init_models(db)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/live-scores')
def live_scores():
    return render_template('index.html')

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
    return render_template('admin/matches.html', matches=matches)

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
            teams_scraped += 1
        
        db.session.commit()
        
        log = ScrapeLog(
            category=category_slug,
            status='success',
            message=f'Scraped {teams_scraped} teams',
            teams_scraped=teams_scraped
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Scraped {teams_scraped} teams successfully',
            'teams_scraped': teams_scraped
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
            players_scraped += 1
        
        db.session.commit()
        
        log = ScrapeLog(
            category=f'team_{team.name}',
            status='success',
            message=f'Scraped {players_scraped} players',
            players_scraped=players_scraped
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scraped {players_scraped} players successfully',
            'players_scraped': players_scraped
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
            
            match_positions = [(m.start(), m.group(1)) for m in re.finditer(r'"matchInfo"\s*:\s*\{[^}]*"matchId"\s*:\s*(\d+)', html)]
            
            for pos, mid in match_positions:
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
                
                context = html[pos:pos+3000]
                
                series_name = re.search(r'"seriesName"\s*:\s*"([^"]*)"', context)
                match_desc = re.search(r'"matchDesc"\s*:\s*"([^"]*)"', context)
                match_format = re.search(r'"matchFormat"\s*:\s*"([^"]*)"', context)
                status = re.search(r'"status"\s*:\s*"([^"]*)"', context)
                start_date = re.search(r'"startDate"\s*:\s*(\d+)', context)
                
                team1_name = re.search(r'"team1"\s*:\s*\{[^}]*"teamName"\s*:\s*"([^"]*)"', context)
                team2_name = re.search(r'"team2"\s*:\s*\{[^}]*"teamName"\s*:\s*"([^"]*)"', context)
                
                venue_ground = re.search(r'"venueInfo"\s*:\s*\{[^}]*"ground"\s*:\s*"([^"]*)"', context)
                venue_city = re.search(r'"venueInfo"\s*:\s*\{[^}]*"city"\s*:\s*"([^"]*)"', context)
                
                t1_score_block = re.search(r'"team1Score"\s*:\s*\{.*?"inngs1"\s*:\s*\{([^}]+)\}', context, re.DOTALL)
                t2_score_block = re.search(r'"team2Score"\s*:\s*\{.*?"inngs1"\s*:\s*\{([^}]+)\}', context, re.DOTALL)
                
                team1_score = ''
                team2_score = ''
                
                if t1_score_block:
                    sb = t1_score_block.group(1)
                    runs = re.search(r'"runs"\s*:\s*(\d+)', sb)
                    wkts = re.search(r'"wickets"\s*:\s*(\d+)', sb)
                    overs = re.search(r'"overs"\s*:\s*([\d.]+)', sb)
                    if runs:
                        team1_score = f"{runs.group(1)}/{wkts.group(1) if wkts else '?'}"
                        if overs:
                            team1_score += f" ({overs.group(1)})"
                
                if t2_score_block:
                    sb = t2_score_block.group(1)
                    runs = re.search(r'"runs"\s*:\s*(\d+)', sb)
                    wkts = re.search(r'"wickets"\s*:\s*(\d+)', sb)
                    overs = re.search(r'"overs"\s*:\s*([\d.]+)', sb)
                    if runs:
                        team2_score = f"{runs.group(1)}/{wkts.group(1) if wkts else '?'}"
                        if overs:
                            team2_score += f" ({overs.group(1)})"
                
                match_date = ''
                if start_date:
                    try:
                        from datetime import datetime as dt
                        ts = int(start_date.group(1)) / 1000
                        match_date = dt.fromtimestamp(ts).strftime('%a, %b %d, %Y')
                    except:
                        pass
                
                venue = ''
                if venue_ground and venue_city:
                    venue = f"{venue_ground.group(1)}, {venue_city.group(1)}"
                elif venue_ground:
                    venue = venue_ground.group(1)
                
                matches_data.append({
                    'match_id': mid,
                    'match_format': match_desc.group(1) if match_desc else '',
                    'format_type': match_format.group(1) if match_format else '',
                    'series_name': series_name.group(1) if series_name else '',
                    'match_date': match_date,
                    'team1': team1_name.group(1) if team1_name else '',
                    'team2': team2_name.group(1) if team2_name else '',
                    'team1_score': team1_score,
                    'team2_score': team2_score,
                    'venue': venue,
                    'result': status.group(1) if status else ''
                })
            
            return jsonify({
                'success': True,
                'type': 'matches',
                'matches': matches_data,
                'count': len(matches_data)
            })
        
        else:
            series_data = []
            seen = set()
            
            pattern = r'"matchInfo"\s*:\s*\{[^}]*"seriesId"\s*:\s*(\d+)[^}]*"seriesName"\s*:\s*"([^"]+)"'
            for m in re.finditer(pattern, html):
                sid = m.group(1)
                name = m.group(2)
                if sid not in seen:
                    seen.add(sid)
                    slug = name.lower().replace(' ', '-').replace(',', '').replace("'", '')
                    series_url = f"https://www.cricbuzz.com/cricket-series/{sid}/{slug}/matches"
                    series_data.append({'id': sid, 'name': name, 'url': series_url})
            
            return jsonify({
                'success': True,
                'type': 'series',
                'series': series_data,
                'count': len(series_data)
            })
        
    except Exception as e:
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
        for series_data in series_list:
            existing = Series.query.filter_by(series_id=series_data['series_id']).first()
            if existing:
                existing.name = series_data['name']
                existing.series_url = series_data['series_url']
                existing.start_date = series_data.get('start_date')
                existing.end_date = series_data.get('end_date')
                existing.date_range = series_data.get('date_range')
                existing.category_id = category.id
                existing.updated_at = datetime.utcnow()
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
        
        log = ScrapeLog(
            category=f'series_{category_slug}',
            status='success',
            message=f'Scraped {series_scraped} series',
            teams_scraped=series_scraped
        )
        db.session.add(log)
        db.session.commit()
        
        setting = SeriesScrapeSetting.query.filter_by(category_slug=category_slug).first()
        if setting:
            setting.last_scrape = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scraped {series_scraped} series successfully',
            'series_scraped': series_scraped
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

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
