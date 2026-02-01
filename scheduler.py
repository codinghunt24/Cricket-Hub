from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import atexit
import unicodedata
import re
import os

scheduler = BackgroundScheduler()
scheduler_started = False

def generate_slug(text, existing_slugs=None):
    """Generate SEO-friendly slug from text"""
    if not text:
        return None
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    text = text.strip('-')
    if existing_slugs and text in existing_slugs:
        counter = 1
        while f"{text}-{counter}" in existing_slugs:
            counter += 1
        text = f"{text}-{counter}"
    return text

def run_daily_scrape(app, db, TeamCategory, Team, ScrapeLog, ScrapeSetting, scraper):
    with app.app_context():
        try:
            setting = ScrapeSetting.query.first()
            if not setting or not setting.auto_scrape_enabled:
                return
            
            total_teams = 0
            categories = TeamCategory.query.all()
            existing_slugs = set(t.slug for t in Team.query.filter(Team.slug.isnot(None)).all())
            
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
                            if not existing.slug and existing.name:
                                existing.slug = generate_slug(existing.name, existing_slugs)
                                if existing.slug:
                                    existing_slugs.add(existing.slug)
                        else:
                            team_name = team_data.get('name', '')
                            new_slug = generate_slug(team_name, existing_slugs) if team_name else None
                            if new_slug:
                                existing_slugs.add(new_slug)
                            team = Team(
                                team_id=team_data.get('team_id'),
                                name=team_name,
                                slug=new_slug,
                                flag_url=team_data.get('flag_url'),
                                team_url=team_data.get('team_url'),
                                category_id=category.id
                            )
                            db.session.add(team)
                        total_teams += 1
            
            db.session.commit()
            
            setting.last_scrape = datetime.utcnow()
            db.session.commit()
            
            log = ScrapeLog(
                category='auto_daily',
                status='success',
                message=f'Auto scraped {total_teams} teams from all categories',
                teams_scraped=total_teams
            )
            db.session.add(log)
            db.session.commit()
            
            print(f"[SCHEDULER] Auto scrape completed: {total_teams} teams")
            
        except Exception as e:
            print(f"[SCHEDULER] Auto scrape error: {e}")
            log = ScrapeLog(
                category='auto_daily',
                status='error',
                message=str(e)
            )
            db.session.add(log)
            db.session.commit()

def run_daily_player_scrape(app, db, Team, Player, ScrapeLog, ScrapeSetting, scraper):
    with app.app_context():
        try:
            setting = ScrapeSetting.query.first()
            if not setting or not setting.player_auto_scrape_enabled:
                return
            
            total_players = 0
            teams = Team.query.filter(Team.team_url.isnot(None)).all()
            existing_player_slugs = set(p.slug for p in Player.query.filter(Player.slug.isnot(None)).all())
            
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
                            if not existing.slug and existing.name:
                                existing.slug = generate_slug(existing.name, existing_player_slugs)
                                if existing.slug:
                                    existing_player_slugs.add(existing.slug)
                        else:
                            player_name = player_data.get('name', '')
                            new_slug = generate_slug(player_name, existing_player_slugs) if player_name else None
                            if new_slug:
                                existing_player_slugs.add(new_slug)
                            player = Player(
                                player_id=player_data.get('player_id'),
                                name=player_name,
                                slug=new_slug,
                                photo_url=player_data.get('photo_url'),
                                player_url=player_data.get('player_url'),
                                role=player_data.get('role'),
                                team_id=team.id
                            )
                            db.session.add(player)
                        total_players += 1
                except Exception as e:
                    print(f"[SCHEDULER] Error scraping players for {team.name}: {e}")
                    continue
            
            db.session.commit()
            
            setting.last_player_scrape = datetime.utcnow()
            db.session.commit()
            
            log = ScrapeLog(
                category='auto_players',
                status='success',
                message=f'Auto scraped {total_players} players from all teams',
                players_scraped=total_players
            )
            db.session.add(log)
            db.session.commit()
            
            print(f"[SCHEDULER] Auto player scrape completed: {total_players} players")
            
        except Exception as e:
            print(f"[SCHEDULER] Auto player scrape error: {e}")
            log = ScrapeLog(
                category='auto_players',
                status='error',
                message=str(e)
            )
            db.session.add(log)
            db.session.commit()

def init_scheduler(app, db, TeamCategory, Team, ScrapeLog, ScrapeSetting, scraper, Player=None, Match=None, LiveScoreScrapeSetting=None, ProfileScrapeSetting=None, SeriesCategory=None, Series=None, SeriesScrapeSetting=None, MatchScrapeSetting=None):
    global scheduler_started
    
    if scheduler_started:
        return
    
    with app.app_context():
        setting = ScrapeSetting.query.first()
        if setting and setting.auto_scrape_enabled:
            scrape_time = setting.scrape_time or '02:00'
            hour, minute = map(int, scrape_time.split(':'))
            
            scheduler.add_job(
                func=lambda: run_daily_scrape(app, db, TeamCategory, Team, ScrapeLog, ScrapeSetting, scraper),
                trigger=CronTrigger(hour=hour, minute=minute),
                id='daily_scrape',
                replace_existing=True
            )
            
            print(f"[SCHEDULER] Daily scrape scheduled at {scrape_time}")
        
        if setting and setting.player_auto_scrape_enabled and Player:
            player_time = setting.player_scrape_time or '03:00'
            hour, minute = map(int, player_time.split(':'))
            
            scheduler.add_job(
                func=lambda: run_daily_player_scrape(app, db, Team, Player, ScrapeLog, ScrapeSetting, scraper),
                trigger=CronTrigger(hour=hour, minute=minute),
                id='daily_player_scrape',
                replace_existing=True
            )
            
            print(f"[SCHEDULER] Daily player scrape scheduled at {player_time}")
        
        if LiveScoreScrapeSetting and Match:
            live_setting = LiveScoreScrapeSetting.query.first()
            if live_setting and live_setting.auto_scrape_enabled:
                from apscheduler.triggers.interval import IntervalTrigger
                interval_seconds = live_setting.interval_seconds or 60
                
                scheduler.add_job(
                    func=lambda: run_live_score_scrape(app, db, Match, ScrapeLog, LiveScoreScrapeSetting, scraper),
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id='live_score_auto_scrape',
                    replace_existing=True
                )
                
                print(f"[SCHEDULER] Live score auto-scrape scheduled (every {interval_seconds}s)")
        
        if ProfileScrapeSetting and Player:
            profile_settings = ProfileScrapeSetting.query.filter_by(auto_scrape_enabled=True).all()
            for ps in profile_settings:
                try:
                    hour, minute = map(int, ps.scrape_time.split(':'))
                    job_id = f'{ps.category_slug}_profile_scrape'
                    
                    scheduler.add_job(
                        func=lambda cat=ps.category_slug: run_category_profile_scrape(app, db, TeamCategory, Team, Player, ScrapeLog, ProfileScrapeSetting, scraper, cat),
                        trigger=CronTrigger(hour=hour, minute=minute),
                        id=job_id,
                        replace_existing=True
                    )
                    
                    print(f"[SCHEDULER] {ps.category_slug.title()} profile scrape scheduled at {ps.scrape_time}")
                except Exception as e:
                    print(f"[SCHEDULER] Error scheduling {ps.category_slug} profile scrape: {e}")
        
        if SeriesScrapeSetting and Series and SeriesCategory:
            series_settings = SeriesScrapeSetting.query.filter_by(auto_scrape_enabled=True).all()
            for ss in series_settings:
                try:
                    hour, minute = map(int, ss.scrape_time.split(':'))
                    job_id = f'{ss.category_slug}_series_scrape'
                    
                    scheduler.add_job(
                        func=lambda cat=ss.category_slug: run_category_series_scrape(app, db, SeriesCategory, Series, ScrapeLog, SeriesScrapeSetting, scraper, cat),
                        trigger=CronTrigger(hour=hour, minute=minute),
                        id=job_id,
                        replace_existing=True
                    )
                    
                    print(f"[SCHEDULER] {ss.category_slug.title()} series scrape scheduled at {ss.scrape_time}")
                except Exception as e:
                    print(f"[SCHEDULER] Error scheduling {ss.category_slug} series scrape: {e}")
        
        if MatchScrapeSetting and Match and Series and SeriesCategory:
            match_setting = MatchScrapeSetting.query.first()
            if match_setting and match_setting.auto_scrape_enabled:
                from apscheduler.triggers.interval import IntervalTrigger
                interval_hours = match_setting.interval_hours or 4
                interval_seconds = interval_hours * 3600
                
                scheduler.add_job(
                    func=lambda: run_category_matches_scrape(app, db, SeriesCategory, Series, Match, ScrapeLog, MatchScrapeSetting, scraper, 'all'),
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id='match_interval_scrape',
                    replace_existing=True
                )
                
                print(f"[SCHEDULER] Match auto-scrape scheduled (every {interval_hours}h)")
    
    scheduler.start()
    scheduler_started = True
    
    atexit.register(lambda: scheduler.shutdown())

def update_schedule(app, db, ScrapeSetting, TeamCategory, Team, ScrapeLog, scraper, enabled, scrape_time):
    global scheduler_started
    
    if 'daily_scrape' in [job.id for job in scheduler.get_jobs()]:
        scheduler.remove_job('daily_scrape')
    
    if enabled:
        hour, minute = map(int, scrape_time.split(':'))
        
        scheduler.add_job(
            func=lambda: run_daily_scrape(app, db, TeamCategory, Team, ScrapeLog, ScrapeSetting, scraper),
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_scrape',
            replace_existing=True
        )
        
        print(f"[SCHEDULER] Daily scrape rescheduled at {scrape_time}")
    else:
        print("[SCHEDULER] Daily scrape disabled")

def update_player_schedule(app, db, ScrapeSetting, Team, Player, ScrapeLog, scraper, enabled, scrape_time):
    global scheduler_started
    
    if 'daily_player_scrape' in [job.id for job in scheduler.get_jobs()]:
        scheduler.remove_job('daily_player_scrape')
    
    if enabled:
        hour, minute = map(int, scrape_time.split(':'))
        
        scheduler.add_job(
            func=lambda: run_daily_player_scrape(app, db, Team, Player, ScrapeLog, ScrapeSetting, scraper),
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_player_scrape',
            replace_existing=True
        )
        
        print(f"[SCHEDULER] Daily player scrape rescheduled at {scrape_time}")
    else:
        print("[SCHEDULER] Daily player scrape disabled")

def run_category_player_scrape(app, db, TeamCategory, Team, Player, ScrapeLog, ScrapeSetting, scraper, category_slug):
    with app.app_context():
        try:
            category = TeamCategory.query.filter_by(slug=category_slug).first()
            if not category:
                return
            
            total_players = 0
            teams = Team.query.filter_by(category_id=category.id).filter(Team.team_url.isnot(None)).all()
            existing_player_slugs = set(p.slug for p in Player.query.filter(Player.slug.isnot(None)).all())
            
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
                            if not existing.slug and existing.name:
                                existing.slug = generate_slug(existing.name, existing_player_slugs)
                                if existing.slug:
                                    existing_player_slugs.add(existing.slug)
                        else:
                            player_name = player_data.get('name', '')
                            new_slug = generate_slug(player_name, existing_player_slugs) if player_name else None
                            if new_slug:
                                existing_player_slugs.add(new_slug)
                            player = Player(
                                player_id=player_data.get('player_id'),
                                name=player_name,
                                slug=new_slug,
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
                category=f'auto_{category_slug}_players',
                status='success',
                message=f'Auto scraped {total_players} players from {category.name}',
                players_scraped=total_players
            )
            db.session.add(log)
            db.session.commit()
            
            print(f"[SCHEDULER] Auto {category_slug} players scrape completed: {total_players} players")
            
        except Exception as e:
            print(f"[SCHEDULER] Auto {category_slug} players scrape error: {e}")

def update_category_player_schedule(app, db, ScrapeSetting, TeamCategory, Team, Player, ScrapeLog, scraper, category, enabled, scrape_time):
    job_id = f'{category}_player_scrape'
    
    if job_id in [job.id for job in scheduler.get_jobs()]:
        scheduler.remove_job(job_id)
    
    if enabled:
        hour, minute = map(int, scrape_time.split(':'))
        
        scheduler.add_job(
            func=lambda cat=category: run_category_player_scrape(app, db, TeamCategory, Team, Player, ScrapeLog, ScrapeSetting, scraper, cat),
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True
        )
        
        print(f"[SCHEDULER] {category.title()} player scrape scheduled at {scrape_time}")
    else:
        print(f"[SCHEDULER] {category.title()} player scrape disabled")

def run_live_score_scrape(app, db, Match, ScrapeLog, LiveScoreScrapeSetting, scraper):
    with app.app_context():
        try:
            setting = LiveScoreScrapeSetting.query.first()
            if not setting or not setting.auto_scrape_enabled:
                return
            
            result = scraper.scrape_live_scores()
            
            if not result or not isinstance(result, dict):
                print("[SCHEDULER] Live score scrape returned invalid data")
                return
            
            all_matches = result.get('matches', [])
            
            updated_count = 0
            for match_data in all_matches:
                if not isinstance(match_data, dict):
                    continue
                    
                match_id = match_data.get('match_id')
                if not match_id:
                    continue
                
                existing = Match.query.filter_by(match_id=match_id).first()
                if existing:
                    # Update team names if provided (scraper uses team1_name/team2_name keys)
                    if match_data.get('team1_name'):
                        existing.team1_name = match_data.get('team1_name')
                    if match_data.get('team2_name'):
                        existing.team2_name = match_data.get('team2_name')
                    # Only update scores if new value is not empty (preserve existing scores)
                    if match_data.get('team1_score'):
                        existing.team1_score = match_data.get('team1_score')
                    if match_data.get('team2_score'):
                        existing.team2_score = match_data.get('team2_score')
                    # Update result only if not empty
                    if match_data.get('result'):
                        existing.result = match_data.get('result')
                    if match_data.get('state'):
                        state_val = match_data.get('state')
                        # Convert Preview to Upcoming for consistency
                        if state_val == 'Preview':
                            state_val = 'Upcoming'
                        existing.state = state_val
                    if match_data.get('match_format'):
                        existing.match_format = match_data.get('match_format')
                    if match_data.get('series_name'):
                        existing.series_name = match_data.get('series_name')
                    if match_data.get('match_url'):
                        existing.match_url = match_data.get('match_url')
                    if match_data.get('series_id'):
                        existing.cricbuzz_series_id = match_data.get('series_id')
                    # Update team flags if available
                    if match_data.get('team1_flag'):
                        existing.team1_flag = match_data.get('team1_flag')
                    if match_data.get('team2_flag'):
                        existing.team2_flag = match_data.get('team2_flag')
                    existing.updated_at = datetime.utcnow()
                else:
                    # Convert Preview to Upcoming for new matches
                    new_state = match_data.get('state', '')
                    if new_state == 'Preview':
                        new_state = 'Upcoming'
                    
                    # Generate slug for new match
                    team1 = match_data.get('team1_name', '')
                    team2 = match_data.get('team2_name', '')
                    match_format = match_data.get('match_format', '')
                    match_slug = None
                    if team1 and team2:
                        match_title = f"{team1} vs {team2}"
                        if match_format:
                            match_title += f" {match_format}"
                        match_slug = generate_slug(match_title)
                    
                    new_match = Match(
                        match_id=match_id,
                        slug=match_slug,
                        team1_name=team1,
                        team1_score=match_data.get('team1_score', ''),
                        team2_name=team2,
                        team2_score=match_data.get('team2_score', ''),
                        result=match_data.get('result', ''),
                        state=new_state,
                        match_format=match_format,
                        series_name=match_data.get('series_name', ''),
                        match_url=match_data.get('match_url', ''),
                        cricbuzz_series_id=match_data.get('series_id', ''),
                        team1_flag=match_data.get('team1_flag', ''),
                        team2_flag=match_data.get('team2_flag', '')
                    )
                    db.session.add(new_match)
                updated_count += 1
            
            db.session.commit()
            
            setting.last_scrape = datetime.utcnow()
            db.session.commit()
            
            print(f"[SCHEDULER] Live score auto-scrape: {updated_count} matches updated")
            
        except Exception as e:
            print(f"[SCHEDULER] Live score auto-scrape error: {e}")
            db.session.rollback()

def update_live_score_schedule(app, db, Match, ScrapeLog, LiveScoreScrapeSetting, scraper, enabled, interval_seconds):
    global scheduler
    
    job_id = 'live_score_auto_scrape'
    
    if job_id in [job.id for job in scheduler.get_jobs()]:
        scheduler.remove_job(job_id)
    
    if enabled:
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler.add_job(
            func=lambda: run_live_score_scrape(app, db, Match, ScrapeLog, LiveScoreScrapeSetting, scraper),
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=job_id,
            replace_existing=True
        )
        
        print(f"[SCHEDULER] Live score auto-scrape enabled (every {interval_seconds}s)")
    else:
        print(f"[SCHEDULER] Live score auto-scrape disabled")

def run_category_profile_scrape(app, db, TeamCategory, Team, Player, ScrapeLog, ProfileScrapeSetting, scraper, category_slug):
    with app.app_context():
        try:
            category = TeamCategory.query.filter_by(slug=category_slug).first()
            if not category:
                print(f"[SCHEDULER] Category {category_slug} not found")
                return
            
            players = Player.query.join(Team).filter(
                Team.category_id == category.id,
                Player.player_url.isnot(None)
            ).all()
            
            scraped_count = 0
            for player in players:
                try:
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
                        
                        player.batting_stats = profile_data.get('batting_stats')
                        player.bowling_stats = profile_data.get('bowling_stats')
                        player.career_timeline = profile_data.get('career_timeline')
                        
                        player.profile_scraped = True
                        player.profile_scraped_at = datetime.utcnow()
                        scraped_count += 1
                        
                        if scraped_count % 10 == 0:
                            db.session.commit()
                            
                except Exception as e:
                    print(f"[SCHEDULER] Error scraping profile for {player.name}: {e}")
                    continue
            
            db.session.commit()
            
            log = ScrapeLog(
                category=f'{category_slug}_profiles',
                status='success',
                message=f'Auto scraped {scraped_count} player profiles',
                players_scraped=scraped_count
            )
            db.session.add(log)
            db.session.commit()
            
            print(f"[SCHEDULER] Auto {category_slug} profiles scrape completed: {scraped_count} profiles")
            
        except Exception as e:
            print(f"[SCHEDULER] Auto {category_slug} profiles scrape error: {e}")

def update_category_profile_schedule(app, db, TeamCategory, Team, Player, ScrapeLog, ProfileScrapeSetting, scraper, category, enabled, scrape_time):
    job_id = f'{category}_profile_scrape'
    
    if job_id in [job.id for job in scheduler.get_jobs()]:
        scheduler.remove_job(job_id)
    
    if enabled:
        hour, minute = map(int, scrape_time.split(':'))
        
        scheduler.add_job(
            func=lambda cat=category: run_category_profile_scrape(app, db, TeamCategory, Team, Player, ScrapeLog, ProfileScrapeSetting, scraper, cat),
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True
        )
        
        print(f"[SCHEDULER] {category.title()} profile scrape scheduled at {scrape_time}")
    else:
        print(f"[SCHEDULER] {category.title()} profile scrape disabled")

def run_category_series_scrape(app, db, SeriesCategory, Series, ScrapeLog, SeriesScrapeSetting, scraper, category_slug):
    with app.app_context():
        try:
            if category_slug == 'all':
                categories = SeriesCategory.query.all()
            else:
                cat = SeriesCategory.query.filter_by(slug=category_slug).first()
                categories = [cat] if cat else []
            
            total_series = 0
            for category in categories:
                try:
                    result = scraper.scrape_series_from_category(category.url)
                    if result and result.get('series'):
                        for series_data in result['series']:
                            existing = Series.query.filter_by(series_id=series_data.get('id')).first()
                            if existing:
                                existing.name = series_data.get('name', existing.name)
                                existing.series_url = series_data.get('url', existing.series_url)
                                existing.date_range = series_data.get('date_range', existing.date_range)
                                existing.updated_at = datetime.utcnow()
                            else:
                                new_series = Series(
                                    series_id=series_data.get('id'),
                                    name=series_data.get('name', ''),
                                    series_url=series_data.get('url', ''),
                                    date_range=series_data.get('date_range'),
                                    category_id=category.id
                                )
                                db.session.add(new_series)
                            total_series += 1
                except Exception as e:
                    print(f"[SCHEDULER] Error scraping series for {category.name}: {e}")
                    continue
            
            db.session.commit()
            
            setting = SeriesScrapeSetting.query.filter_by(category_slug=category_slug).first()
            if setting:
                setting.last_scrape = datetime.utcnow()
                db.session.commit()
            
            log = ScrapeLog(
                category=f'auto_{category_slug}_series',
                status='success',
                message=f'Auto scraped {total_series} series'
            )
            db.session.add(log)
            db.session.commit()
            
            print(f"[SCHEDULER] Auto {category_slug} series scrape completed: {total_series} series")
            
        except Exception as e:
            print(f"[SCHEDULER] Auto {category_slug} series scrape error: {e}")

def update_category_series_schedule(app, db, SeriesCategory, Series, ScrapeLog, SeriesScrapeSetting, scraper, category, enabled, scrape_time):
    job_id = f'{category}_series_scrape'
    
    if job_id in [job.id for job in scheduler.get_jobs()]:
        scheduler.remove_job(job_id)
    
    if enabled:
        hour, minute = map(int, scrape_time.split(':'))
        
        scheduler.add_job(
            func=lambda cat=category: run_category_series_scrape(app, db, SeriesCategory, Series, ScrapeLog, SeriesScrapeSetting, scraper, cat),
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True
        )
        
        print(f"[SCHEDULER] {category.title()} series scrape scheduled at {scrape_time}")
    else:
        print(f"[SCHEDULER] {category.title()} series scrape disabled")

def run_category_matches_scrape(app, db, SeriesCategory, Series, Match, ScrapeLog, MatchScrapeSetting, scraper, category_slug):
    with app.app_context():
        try:
            if category_slug == 'all':
                all_series = Series.query.all()
            else:
                category = SeriesCategory.query.filter_by(slug=category_slug).first()
                if category:
                    all_series = Series.query.filter_by(category_id=category.id).all()
                else:
                    all_series = []
            
            total_matches = 0
            for series in all_series:
                try:
                    matches_list = scraper.scrape_matches_from_series(series.series_url)
                    if matches_list:
                        for match_data in matches_list:
                            match_id = match_data.get('match_id')
                            if not match_id:
                                continue
                            
                            existing = Match.query.filter_by(match_id=match_id).first()
                            if existing:
                                existing.match_format = match_data.get('match_format', existing.match_format)
                                existing.venue = match_data.get('venue', existing.venue)
                                existing.match_date = match_data.get('match_date', existing.match_date)
                                existing.team1_name = match_data.get('team1', existing.team1_name)
                                existing.team2_name = match_data.get('team2', existing.team2_name)
                                if match_data.get('team1_score'):
                                    existing.team1_score = match_data.get('team1_score')
                                if match_data.get('team2_score'):
                                    existing.team2_score = match_data.get('team2_score')
                                existing.result = match_data.get('result', existing.result)
                                # Update team flags
                                if match_data.get('team1_flag'):
                                    existing.team1_flag = match_data.get('team1_flag')
                                if match_data.get('team2_flag'):
                                    existing.team2_flag = match_data.get('team2_flag')
                                # Update state - convert Preview to Upcoming
                                if match_data.get('state'):
                                    state_val = match_data.get('state')
                                    if state_val == 'Preview':
                                        state_val = 'Upcoming'
                                    existing.state = state_val
                                existing.series_id = series.id
                                existing.updated_at = datetime.utcnow()
                            else:
                                # Convert state for new matches
                                new_state = match_data.get('state', '')
                                if new_state == 'Preview':
                                    new_state = 'Upcoming'
                                
                                match = Match(
                                    match_id=match_id,
                                    match_format=match_data.get('match_format', ''),
                                    venue=match_data.get('venue', ''),
                                    match_date=match_data.get('match_date', ''),
                                    team1_name=match_data.get('team1', ''),
                                    team2_name=match_data.get('team2', ''),
                                    team1_score=match_data.get('team1_score', ''),
                                    team2_score=match_data.get('team2_score', ''),
                                    team1_flag=match_data.get('team1_flag', ''),
                                    team2_flag=match_data.get('team2_flag', ''),
                                    result=match_data.get('result', ''),
                                    state=new_state,
                                    series_id=series.id
                                )
                                db.session.add(match)
                            total_matches += 1
                except Exception as e:
                    print(f"[SCHEDULER] Error scraping matches for {series.name}: {e}")
                    continue
            
            db.session.commit()
            
            setting = MatchScrapeSetting.query.filter_by(category_slug=category_slug).first()
            if setting:
                setting.last_scrape = datetime.utcnow()
                db.session.commit()
            
            log = ScrapeLog(
                category=f'auto_{category_slug}_matches',
                status='success',
                message=f'Auto scraped {total_matches} matches'
            )
            db.session.add(log)
            db.session.commit()
            
            print(f"[SCHEDULER] Auto {category_slug} matches scrape completed: {total_matches} matches")
            
        except Exception as e:
            print(f"[SCHEDULER] Auto {category_slug} matches scrape error: {e}")

def update_category_matches_schedule(app, db, SeriesCategory, Series, Match, ScrapeLog, MatchScrapeSetting, scraper, category, enabled, scrape_time):
    job_id = f'{category}_matches_scrape'
    
    if job_id in [job.id for job in scheduler.get_jobs()]:
        scheduler.remove_job(job_id)
    
    if enabled:
        hour, minute = map(int, scrape_time.split(':'))
        
        scheduler.add_job(
            func=lambda cat=category: run_category_matches_scrape(app, db, SeriesCategory, Series, Match, ScrapeLog, MatchScrapeSetting, scraper, cat),
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True
        )
        
        print(f"[SCHEDULER] {category.title()} matches scrape scheduled at {scrape_time}")
    else:
        print(f"[SCHEDULER] {category.title()} matches scrape disabled")

def generate_auto_post_content(match):
    """Generate content for auto post"""
    team1 = match.team1_name or 'Team 1'
    team2 = match.team2_name or 'Team 2'
    match_format = match.match_format or 'Match'
    series = match.series_name or ''
    venue = match.venue or ''
    
    title = f"{team1} vs {team2} Today Live Match - {match_format}"
    if series:
        title += f" | {series}"
    
    meta_title = title[:60] if len(title) > 60 else title
    
    keywords = f"{team1}, {team2}, {team1} vs {team2}, live score, {match_format}"
    if series:
        keywords += f", {series}"
    
    slug = generate_slug(f"{team1}-vs-{team2}-{match_format}")
    
    content = f"""<h2>{team1} vs {team2} Live Score</h2>
<p>Get live updates for the exciting {match_format} match between {team1} and {team2}.</p>
"""
    if series:
        content += f"<p><strong>Series:</strong> {series}</p>\n"
    if venue:
        content += f"<p><strong>Venue:</strong> {venue}</p>\n"
    
    content += f"""
<h3>Match Details</h3>
<ul>
<li><strong>Teams:</strong> {team1} vs {team2}</li>
<li><strong>Format:</strong> {match_format}</li>
</ul>

<p>Stay tuned for ball-by-ball updates and live commentary!</p>
"""
    
    return {
        'title': title,
        'meta_title': meta_title,
        'keywords': keywords,
        'slug': slug,
        'content': content
    }

def run_auto_post_job(app, db, Match, Post, PostCategory, AutoPostSetting, AutoPostLog, Player=None):
    """Run auto post job - create posts for tomorrow's matches"""
    with app.app_context():
        try:
            setting = AutoPostSetting.query.first()
            if not setting or not setting.is_enabled:
                return 0
            
            from datetime import timedelta
            import pytz
            
            ist = pytz.timezone('Asia/Kolkata')
            now_ist = datetime.now(ist)
            target_date = now_ist.date() + timedelta(days=setting.days_ahead)
            
            upcoming_matches = Match.query.filter(
                Match.state.in_(['upcoming', 'Upcoming', 'UPCOMING'])
            ).all()
            
            tomorrow_matches = []
            for m in upcoming_matches:
                if m.match_date:
                    try:
                        match_date = None
                        if isinstance(m.match_date, str):
                            date_formats = [
                                '%Y-%m-%d',
                                '%a, %d %b %Y',
                                '%d %b %Y',
                                '%d-%m-%Y',
                                '%d/%m/%Y'
                            ]
                            for fmt in date_formats:
                                try:
                                    match_date = datetime.strptime(m.match_date.strip(), fmt).date()
                                    break
                                except:
                                    continue
                        else:
                            match_date = m.match_date.date() if hasattr(m.match_date, 'date') else m.match_date
                        
                        if match_date and match_date == target_date:
                            tomorrow_matches.append(m)
                    except:
                        pass
            
            posts_created = 0
            existing_slugs = set(p.slug for p in Post.query.filter(Post.slug.isnot(None)).all())
            
            for match in tomorrow_matches:
                try:
                    post_data = generate_auto_post_content(match)
                    
                    slug = post_data['slug']
                    if slug in existing_slugs:
                        log = AutoPostLog(
                            match_id=match.match_id,
                            match_title=post_data['title'],
                            status='skipped',
                            message='Post with similar slug already exists'
                        )
                        db.session.add(log)
                        continue
                    
                    counter = 1
                    original_slug = slug
                    while slug in existing_slugs:
                        slug = f"{original_slug}-{counter}"
                        counter += 1
                    
                    thumbnail_url = None
                    try:
                        from thumbnail_generator import generate_thumbnail
                        from scraper import scrape_match_squads
                        import uuid
                        
                        team1_captain_url = None
                        team2_captain_url = None
                        
                        try:
                            squads = scrape_match_squads(match.match_id)
                            if squads and squads.get('success'):
                                from app import Player as PlayerModel
                                if squads.get('team1', {}).get('captain_id'):
                                    captain = PlayerModel.query.filter_by(player_id=squads['team1']['captain_id']).first()
                                    if captain and captain.photo_url:
                                        team1_captain_url = captain.photo_url
                                if squads.get('team2', {}).get('captain_id'):
                                    captain = PlayerModel.query.filter_by(player_id=squads['team2']['captain_id']).first()
                                    if captain and captain.photo_url:
                                        team2_captain_url = captain.photo_url
                        except Exception as cap_err:
                            print(f"[SCHEDULER] Captain fetch error: {cap_err}")
                        
                        filename = f"thumb_{uuid.uuid4().hex[:8]}.png"
                        output_path = os.path.join('static', 'thumbnails', filename)
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        
                        generate_thumbnail(
                            match.team1_name or "Team 1",
                            match.team2_name or "Team 2",
                            match.match_format or "Match",
                            getattr(match, 'team1_flag', None),
                            getattr(match, 'team2_flag', None),
                            output_path,
                            team1_captain_url,
                            team2_captain_url,
                            getattr(match, 'venue', None),
                            getattr(match, 'series_name', None)
                        )
                        thumbnail_url = f"/static/thumbnails/{filename}"
                    except Exception as thumb_err:
                        print(f"[SCHEDULER] Thumbnail error: {thumb_err}")
                    
                    post = Post(
                        title=post_data['title'],
                        slug=slug,
                        content=post_data['content'],
                        meta_title=post_data['meta_title'],
                        meta_keywords=post_data['keywords'],
                        category_id=setting.category_id,
                        is_published=setting.auto_publish,
                        thumbnail=thumbnail_url
                    )
                    db.session.add(post)
                    db.session.flush()
                    
                    existing_slugs.add(slug)
                    
                    log = AutoPostLog(
                        match_id=match.match_id,
                        post_id=post.id,
                        match_title=post_data['title'],
                        status='success',
                        message=f'Post created: {post.title}'
                    )
                    db.session.add(log)
                    posts_created += 1
                    
                except Exception as e:
                    log = AutoPostLog(
                        match_id=match.match_id,
                        match_title=f"{match.team1_name} vs {match.team2_name}",
                        status='error',
                        message=str(e)
                    )
                    db.session.add(log)
            
            setting.last_run = datetime.utcnow()
            setting.last_run_status = 'success'
            setting.posts_created_last_run = posts_created
            
            db.session.commit()
            print(f"[SCHEDULER] Auto Post: {posts_created} posts created for {target_date}")
            return posts_created
            
        except Exception as e:
            print(f"[SCHEDULER] Auto Post error: {e}")
            try:
                setting = AutoPostSetting.query.first()
                if setting:
                    setting.last_run = datetime.utcnow()
                    setting.last_run_status = f'error: {str(e)}'
                    db.session.commit()
            except:
                pass
            return 0

def run_auto_post_now(app, db, Match, Post, PostCategory, AutoPostSetting, AutoPostLog):
    """Manually run auto post"""
    return run_auto_post_job(app, db, Match, Post, PostCategory, AutoPostSetting, AutoPostLog)

def update_auto_post_schedule(app, db, Match, Post, PostCategory, AutoPostSetting, AutoPostLog):
    """Update auto post scheduler"""
    global scheduler
    job_id = 'auto_post_daily'
    
    try:
        scheduler.remove_job(job_id)
    except:
        pass
    
    with app.app_context():
        setting = AutoPostSetting.query.first()
        if setting and setting.is_enabled:
            utc_hour = (setting.schedule_hour - 5) % 24
            if setting.schedule_minute >= 30:
                utc_hour = (setting.schedule_hour - 6) % 24
            utc_minute = (setting.schedule_minute - 30) % 60
            
            scheduler.add_job(
                func=lambda: run_auto_post_job(app, db, Match, Post, PostCategory, AutoPostSetting, AutoPostLog),
                trigger=CronTrigger(hour=utc_hour, minute=utc_minute),
                id=job_id,
                replace_existing=True
            )
            
            print(f"[SCHEDULER] Auto Post scheduled at {setting.schedule_hour:02d}:{setting.schedule_minute:02d} IST")
        else:
            print("[SCHEDULER] Auto Post disabled")
