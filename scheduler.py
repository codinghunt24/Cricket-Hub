from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import atexit

scheduler = BackgroundScheduler()
scheduler_started = False

def run_daily_scrape(app, db, TeamCategory, Team, ScrapeLog, ScrapeSetting, scraper):
    with app.app_context():
        try:
            setting = ScrapeSetting.query.first()
            if not setting or not setting.auto_scrape_enabled:
                return
            
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

def init_scheduler(app, db, TeamCategory, Team, ScrapeLog, ScrapeSetting, scraper, Player=None, Match=None, LiveScoreScrapeSetting=None, ProfileScrapeSetting=None):
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
                    # Update team names if provided
                    if match_data.get('team1'):
                        existing.team1_name = match_data.get('team1')
                    if match_data.get('team2'):
                        existing.team2_name = match_data.get('team2')
                    # Only update scores if new value is not empty (preserve existing scores)
                    if match_data.get('team1_score'):
                        existing.team1_score = match_data.get('team1_score')
                    if match_data.get('team2_score'):
                        existing.team2_score = match_data.get('team2_score')
                    # Update result only if not empty
                    if match_data.get('result'):
                        existing.result = match_data.get('result')
                    if match_data.get('status'):
                        existing.state = match_data.get('status')
                    if match_data.get('match_format'):
                        existing.match_format = match_data.get('match_format')
                    if match_data.get('match_url'):
                        existing.match_url = match_data.get('match_url')
                    if match_data.get('series_id'):
                        existing.cricbuzz_series_id = match_data.get('series_id')
                    existing.updated_at = datetime.utcnow()
                else:
                    new_match = Match(
                        match_id=match_id,
                        team1_name=match_data.get('team1', ''),
                        team1_score=match_data.get('team1_score', ''),
                        team2_name=match_data.get('team2', ''),
                        team2_score=match_data.get('team2_score', ''),
                        result=match_data.get('result', ''),
                        state=match_data.get('status', ''),
                        match_format=match_data.get('match_format', ''),
                        match_url=match_data.get('match_url', ''),
                        cricbuzz_series_id=match_data.get('series_id', '')
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
