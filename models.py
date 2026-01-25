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
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    return TeamCategory, Team, Player, ScrapeLog, ScrapeSetting
