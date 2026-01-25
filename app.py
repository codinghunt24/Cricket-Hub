import os
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', os.urandom(24))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/live-scores')
def live_scores():
    return render_template('index.html')

@app.route('/teams')
def teams():
    return render_template('index.html')

@app.route('/series')
def series():
    return render_template('index.html')

@app.route('/news')
def news():
    return render_template('index.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/matches')
def admin_matches():
    return render_template('admin/matches.html')

@app.route('/admin/teams')
def admin_teams():
    return render_template('admin/teams.html')

@app.route('/admin/series')
def admin_series():
    return render_template('admin/series.html')

@app.route('/admin/news')
def admin_news():
    return render_template('admin/news.html')

@app.route('/admin/settings')
def admin_settings():
    return render_template('admin/settings.html')

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
