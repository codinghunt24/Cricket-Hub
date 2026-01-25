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

def init_scheduler(app, db, TeamCategory, Team, ScrapeLog, ScrapeSetting, scraper):
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
