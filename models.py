from datetime import datetime

def init_models(db):
    class TeamCategory(db.Model):
        __tablename__ = 'team_categories'
        
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(50), unique=True, nullable=False)
        slug = db.Column(db.String(50), unique=True, nullable=False)
        url = db.Column(db.String(255), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        teams = db.relationship('Team', backref='category', lazy=True)

    class Team(db.Model):
        __tablename__ = 'teams'
        
        id = db.Column(db.Integer, primary_key=True)
        team_id = db.Column(db.String(50), nullable=True)
        name = db.Column(db.String(100), nullable=False)
        short_name = db.Column(db.String(20), nullable=True)
        flag_url = db.Column(db.String(500), nullable=True)
        team_url = db.Column(db.String(500), nullable=True)
        category_id = db.Column(db.Integer, db.ForeignKey('team_categories.id'), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        players = db.relationship('Player', backref='team', lazy=True, cascade='all, delete-orphan')

    class Player(db.Model):
        __tablename__ = 'players'
        
        id = db.Column(db.Integer, primary_key=True)
        player_id = db.Column(db.String(50), nullable=True)
        name = db.Column(db.String(100), nullable=False)
        role = db.Column(db.String(50), nullable=True)
        photo_url = db.Column(db.String(500), nullable=True)
        player_url = db.Column(db.String(500), nullable=True)
        team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
        
        born = db.Column(db.String(100), nullable=True)
        birth_place = db.Column(db.String(200), nullable=True)
        nickname = db.Column(db.String(100), nullable=True)
        batting_style = db.Column(db.String(100), nullable=True)
        bowling_style = db.Column(db.String(100), nullable=True)
        
        bat_matches = db.Column(db.String(50), nullable=True)
        bat_innings = db.Column(db.String(50), nullable=True)
        bat_runs = db.Column(db.String(50), nullable=True)
        bat_balls = db.Column(db.String(50), nullable=True)
        bat_highest = db.Column(db.String(50), nullable=True)
        bat_average = db.Column(db.String(50), nullable=True)
        bat_strike_rate = db.Column(db.String(50), nullable=True)
        bat_not_outs = db.Column(db.String(50), nullable=True)
        bat_fours = db.Column(db.String(50), nullable=True)
        bat_sixes = db.Column(db.String(50), nullable=True)
        bat_ducks = db.Column(db.String(50), nullable=True)
        bat_fifties = db.Column(db.String(50), nullable=True)
        bat_hundreds = db.Column(db.String(50), nullable=True)
        bat_two_hundreds = db.Column(db.String(50), nullable=True)
        
        bowl_matches = db.Column(db.String(50), nullable=True)
        bowl_innings = db.Column(db.String(50), nullable=True)
        bowl_balls = db.Column(db.String(50), nullable=True)
        bowl_runs = db.Column(db.String(50), nullable=True)
        bowl_maidens = db.Column(db.String(50), nullable=True)
        bowl_wickets = db.Column(db.String(50), nullable=True)
        bowl_average = db.Column(db.String(50), nullable=True)
        bowl_economy = db.Column(db.String(50), nullable=True)
        bowl_strike_rate = db.Column(db.String(50), nullable=True)
        bowl_best_innings = db.Column(db.String(50), nullable=True)
        bowl_best_match = db.Column(db.String(50), nullable=True)
        bowl_four_wickets = db.Column(db.String(50), nullable=True)
        bowl_five_wickets = db.Column(db.String(50), nullable=True)
        bowl_ten_wickets = db.Column(db.String(50), nullable=True)
        
        batting_stats = db.Column(db.JSON, nullable=True)
        bowling_stats = db.Column(db.JSON, nullable=True)
        career_timeline = db.Column(db.JSON, nullable=True)
        
        profile_scraped = db.Column(db.Boolean, default=False)
        profile_scraped_at = db.Column(db.DateTime, nullable=True)
        
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class ScrapeLog(db.Model):
        __tablename__ = 'scrape_logs'
        
        id = db.Column(db.Integer, primary_key=True)
        category = db.Column(db.String(50), nullable=True)
        status = db.Column(db.String(20), nullable=False)
        message = db.Column(db.Text, nullable=True)
        teams_scraped = db.Column(db.Integer, default=0)
        players_scraped = db.Column(db.Integer, default=0)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class ScrapeSetting(db.Model):
        __tablename__ = 'scrape_settings'
        
        id = db.Column(db.Integer, primary_key=True)
        auto_scrape_enabled = db.Column(db.Boolean, default=False)
        scrape_time = db.Column(db.String(10), default='02:00')
        last_scrape = db.Column(db.DateTime, nullable=True)
        player_auto_scrape_enabled = db.Column(db.Boolean, default=False)
        player_scrape_time = db.Column(db.String(10), default='03:00')
        last_player_scrape = db.Column(db.DateTime, nullable=True)
        intl_auto = db.Column(db.Boolean, default=False)
        intl_time = db.Column(db.String(10), default='04:00')
        domestic_auto = db.Column(db.Boolean, default=False)
        domestic_time = db.Column(db.String(10), default='05:00')
        league_auto = db.Column(db.Boolean, default=False)
        league_time = db.Column(db.String(10), default='06:00')
        women_auto = db.Column(db.Boolean, default=False)
        women_time = db.Column(db.String(10), default='07:00')
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class ProfileScrapeSetting(db.Model):
        __tablename__ = 'profile_scrape_settings'
        
        id = db.Column(db.Integer, primary_key=True)
        category_slug = db.Column(db.String(50), unique=True, nullable=False)
        auto_scrape_enabled = db.Column(db.Boolean, default=False)
        scrape_time = db.Column(db.String(10), default='03:00')
        last_scrape = db.Column(db.DateTime, nullable=True)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    return TeamCategory, Team, Player, ScrapeLog, ScrapeSetting, ProfileScrapeSetting
