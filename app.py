import os
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

from models import init_models
TeamCategory, Team, Player, ScrapeLog, ScrapeSetting = init_models(db)

import scraper
from scheduler import init_scheduler, update_schedule

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
    
    db.session.commit()

init_scheduler(app, db, TeamCategory, Team, ScrapeLog, ScrapeSetting, scraper)

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

@app.route('/series')
def series():
    return render_template('index.html')

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
    return render_template('admin/matches.html')

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
    return render_template('admin/series.html')

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

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
