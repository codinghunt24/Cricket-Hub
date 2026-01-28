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
        slug = db.Column(db.String(150), unique=True, nullable=True, index=True)
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
        slug = db.Column(db.String(150), unique=True, nullable=True, index=True)
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
    
    class SeriesCategory(db.Model):
        __tablename__ = 'series_categories'
        
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(50), unique=True, nullable=False)
        slug = db.Column(db.String(50), unique=True, nullable=False)
        url = db.Column(db.String(255), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        series = db.relationship('Series', backref='category', lazy=True, cascade='all, delete-orphan')
    
    class Series(db.Model):
        __tablename__ = 'series'
        
        id = db.Column(db.Integer, primary_key=True)
        series_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
        name = db.Column(db.String(200), nullable=False)
        slug = db.Column(db.String(250), unique=True, nullable=True, index=True)
        series_url = db.Column(db.String(500), nullable=True)
        start_date = db.Column(db.String(100), nullable=True)
        end_date = db.Column(db.String(100), nullable=True)
        date_range = db.Column(db.String(100), nullable=True)
        category_id = db.Column(db.Integer, db.ForeignKey('series_categories.id'), nullable=False)
        matches = db.relationship('Match', backref='series', lazy=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class SeriesScrapeSetting(db.Model):
        __tablename__ = 'series_scrape_settings'
        
        id = db.Column(db.Integer, primary_key=True)
        category_slug = db.Column(db.String(50), unique=True, nullable=False)
        auto_scrape_enabled = db.Column(db.Boolean, default=False)
        scrape_time = db.Column(db.String(10), default='08:00')
        last_scrape = db.Column(db.DateTime, nullable=True)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class Match(db.Model):
        __tablename__ = 'matches'
        
        id = db.Column(db.Integer, primary_key=True)
        match_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
        cricbuzz_series_id = db.Column(db.String(50), nullable=True, index=True)
        team1_id = db.Column(db.String(50), nullable=True)
        team2_id = db.Column(db.String(50), nullable=True)
        venue_id = db.Column(db.String(50), nullable=True)
        match_format = db.Column(db.String(100), nullable=True)
        format_type = db.Column(db.String(50), nullable=True)
        venue = db.Column(db.String(200), nullable=True)
        match_date = db.Column(db.String(100), nullable=True)
        match_time = db.Column(db.String(100), nullable=True)
        start_date = db.Column(db.String(50), nullable=True)
        end_date = db.Column(db.String(50), nullable=True)
        state = db.Column(db.String(50), nullable=True)
        team1_name = db.Column(db.String(100), nullable=True)
        team1_score = db.Column(db.String(100), nullable=True)
        team1_flag = db.Column(db.String(500), nullable=True)
        team2_name = db.Column(db.String(100), nullable=True)
        team2_score = db.Column(db.String(100), nullable=True)
        team2_flag = db.Column(db.String(500), nullable=True)
        result = db.Column(db.String(300), nullable=True)
        match_url = db.Column(db.String(500), nullable=True)
        series_name = db.Column(db.String(300), nullable=True)
        series_id = db.Column(db.Integer, db.ForeignKey('series.id'), nullable=True)
        batting_data = db.Column(db.JSON, nullable=True)
        bowling_data = db.Column(db.JSON, nullable=True)
        innings_data = db.Column(db.JSON, nullable=True)
        toss = db.Column(db.String(300), nullable=True)
        live_status = db.Column(db.String(300), nullable=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class MatchScrapeSetting(db.Model):
        __tablename__ = 'match_scrape_settings'
        
        id = db.Column(db.Integer, primary_key=True)
        category_slug = db.Column(db.String(50), nullable=True)
        auto_scrape_enabled = db.Column(db.Boolean, default=False)
        scrape_time = db.Column(db.String(10), default='10:00')
        last_scrape = db.Column(db.DateTime, nullable=True)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class LiveScoreScrapeSetting(db.Model):
        __tablename__ = 'live_score_scrape_settings'
        
        id = db.Column(db.Integer, primary_key=True)
        auto_scrape_enabled = db.Column(db.Boolean, default=False)
        interval_seconds = db.Column(db.Integer, default=60)
        last_scrape = db.Column(db.DateTime, nullable=True)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class PostCategory(db.Model):
        __tablename__ = 'post_categories'
        
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), unique=True, nullable=False)
        slug = db.Column(db.String(100), unique=True, nullable=False)
        description = db.Column(db.Text, nullable=True)
        show_in_navbar = db.Column(db.Boolean, default=True)
        navbar_order = db.Column(db.Integer, default=0)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        posts = db.relationship('Post', backref='category', lazy=True)
    
    class Post(db.Model):
        __tablename__ = 'posts'
        
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(300), nullable=False)
        slug = db.Column(db.String(300), unique=True, nullable=False)
        content = db.Column(db.Text, nullable=True)
        excerpt = db.Column(db.Text, nullable=True)
        thumbnail = db.Column(db.String(500), nullable=True)
        
        meta_title = db.Column(db.String(200), nullable=True)
        meta_description = db.Column(db.Text, nullable=True)
        meta_keywords = db.Column(db.Text, nullable=True)
        canonical_url = db.Column(db.String(500), nullable=True)
        og_title = db.Column(db.String(200), nullable=True)
        og_description = db.Column(db.Text, nullable=True)
        og_image = db.Column(db.String(500), nullable=True)
        schema_markup = db.Column(db.Text, nullable=True)
        
        is_published = db.Column(db.Boolean, default=False)
        is_featured = db.Column(db.Boolean, default=False)
        views = db.Column(db.Integer, default=0)
        
        category_id = db.Column(db.Integer, db.ForeignKey('post_categories.id'), nullable=True)
        match_id = db.Column(db.String(50), nullable=True)
        author = db.Column(db.String(100), default='Admin')
        
        published_at = db.Column(db.DateTime, nullable=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class AdminUser(db.Model):
        __tablename__ = 'admin_users'
        
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(50), unique=True, nullable=False)
        password_hash = db.Column(db.String(256), nullable=False)
        name = db.Column(db.String(100), default='Admin')
        email = db.Column(db.String(100), nullable=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        last_login = db.Column(db.DateTime, nullable=True)
    
    class Page(db.Model):
        __tablename__ = 'pages'
        
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        slug = db.Column(db.String(200), unique=True, nullable=False)
        content = db.Column(db.Text, nullable=True)
        meta_title = db.Column(db.String(200), nullable=True)
        meta_description = db.Column(db.Text, nullable=True)
        meta_keywords = db.Column(db.String(500), nullable=True)
        is_published = db.Column(db.Boolean, default=True)
        show_in_footer = db.Column(db.Boolean, default=True)
        footer_order = db.Column(db.Integer, default=0)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    return TeamCategory, Team, Player, ScrapeLog, ScrapeSetting, ProfileScrapeSetting, SeriesCategory, Series, SeriesScrapeSetting, Match, MatchScrapeSetting, LiveScoreScrapeSetting, PostCategory, Post, AdminUser, Page
