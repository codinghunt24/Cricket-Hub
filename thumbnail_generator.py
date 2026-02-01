from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os

THUMBNAIL_WIDTH = 1200
THUMBNAIL_HEIGHT = 630
BACKGROUND_COLOR = "#0a1628"

def download_image(url):
    """Download image from URL"""
    try:
        if not url:
            return None
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except:
        pass
    return None

def create_circle_mask(size):
    """Create circular mask for images"""
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    return mask

def generate_thumbnail(team1_name, team2_name, match_title, team1_flag_url=None, team2_flag_url=None, output_path=None, team1_captain_url=None, team2_captain_url=None, venue=None, series_name=None):
    """Generate match thumbnail with captain images, venue and series"""
    
    img = Image.new('RGB', (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    try:
        match_title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        team_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        vs_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        series_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        venue_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        live_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        match_title_font = ImageFont.load_default()
        team_font = ImageFont.load_default()
        vs_font = ImageFont.load_default()
        series_font = ImageFont.load_default()
        venue_font = ImageFont.load_default()
        live_font = ImageFont.load_default()
    
    if series_name:
        series_short = series_name[:60] + "..." if len(series_name) > 60 else series_name
        bbox = draw.textbbox((0, 0), series_short, font=series_font)
        text_width = bbox[2] - bbox[0]
        draw.text((THUMBNAIL_WIDTH//2 - text_width//2, 25), series_short, fill="#888888", font=series_font)
    
    match_display = f"{team1_name} vs {team2_name}"
    bbox = draw.textbbox((0, 0), match_display, font=match_title_font)
    text_width = bbox[2] - bbox[0]
    draw.text((THUMBNAIL_WIDTH//2 - text_width//2, 70), match_display, fill="#ffffff", font=match_title_font)
    
    center_y = 280
    captain_size = 140
    flag_size = 80
    
    team1_x = 250
    captain1 = download_image(team1_captain_url)
    if captain1:
        captain1 = captain1.resize((captain_size, captain_size), Image.Resampling.LANCZOS)
        if captain1.mode != 'RGBA':
            captain1 = captain1.convert('RGBA')
        cap_mask = create_circle_mask(captain_size)
        cap1_x = team1_x - captain_size//2
        cap1_y = center_y - captain_size//2
        draw.ellipse([cap1_x - 4, cap1_y - 4, cap1_x + captain_size + 4, cap1_y + captain_size + 4], fill="#e94560")
        img.paste(captain1, (cap1_x, cap1_y), cap_mask)
    else:
        draw.ellipse([team1_x - captain_size//2, center_y - captain_size//2, 
                     team1_x + captain_size//2, center_y + captain_size//2], 
                     fill="#1e3a5f", outline="#3282b8", width=3)
    
    team1_flag = download_image(team1_flag_url)
    if team1_flag:
        team1_flag = team1_flag.resize((flag_size, flag_size), Image.Resampling.LANCZOS)
        if team1_flag.mode != 'RGBA':
            team1_flag = team1_flag.convert('RGBA')
        flag_mask = create_circle_mask(flag_size)
        flag1_x = team1_x + captain_size//2 - 20
        flag1_y = center_y + captain_size//2 - flag_size + 10
        draw.ellipse([flag1_x - 3, flag1_y - 3, flag1_x + flag_size + 3, flag1_y + flag_size + 3], fill="#ffffff")
        img.paste(team1_flag, (flag1_x, flag1_y), flag_mask)
    
    team1_short = team1_name[:12] if len(team1_name) > 12 else team1_name
    bbox = draw.textbbox((0, 0), team1_short, font=team_font)
    text_width = bbox[2] - bbox[0]
    draw.text((team1_x - text_width//2, center_y + captain_size//2 + 25), team1_short, fill="#ffffff", font=team_font)
    
    vs_x = THUMBNAIL_WIDTH // 2
    draw.ellipse([vs_x - 35, center_y - 35, vs_x + 35, center_y + 35], fill="#e94560")
    bbox = draw.textbbox((0, 0), "VS", font=vs_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw.text((vs_x - text_width//2, center_y - text_height//2 - 5), "VS", fill="#ffffff", font=vs_font)
    
    team2_x = THUMBNAIL_WIDTH - 250
    captain2 = download_image(team2_captain_url)
    if captain2:
        captain2 = captain2.resize((captain_size, captain_size), Image.Resampling.LANCZOS)
        if captain2.mode != 'RGBA':
            captain2 = captain2.convert('RGBA')
        cap_mask2 = create_circle_mask(captain_size)
        cap2_x = team2_x - captain_size//2
        cap2_y = center_y - captain_size//2
        draw.ellipse([cap2_x - 4, cap2_y - 4, cap2_x + captain_size + 4, cap2_y + captain_size + 4], fill="#e94560")
        img.paste(captain2, (cap2_x, cap2_y), cap_mask2)
    else:
        draw.ellipse([team2_x - captain_size//2, center_y - captain_size//2, 
                     team2_x + captain_size//2, center_y + captain_size//2], 
                     fill="#1e3a5f", outline="#3282b8", width=3)
    
    team2_flag = download_image(team2_flag_url)
    if team2_flag:
        team2_flag = team2_flag.resize((flag_size, flag_size), Image.Resampling.LANCZOS)
        if team2_flag.mode != 'RGBA':
            team2_flag = team2_flag.convert('RGBA')
        flag_mask2 = create_circle_mask(flag_size)
        flag2_x = team2_x - captain_size//2 - flag_size + 20
        flag2_y = center_y + captain_size//2 - flag_size + 10
        draw.ellipse([flag2_x - 3, flag2_y - 3, flag2_x + flag_size + 3, flag2_y + flag_size + 3], fill="#ffffff")
        img.paste(team2_flag, (flag2_x, flag2_y), flag_mask2)
    
    team2_short = team2_name[:12] if len(team2_name) > 12 else team2_name
    bbox = draw.textbbox((0, 0), team2_short, font=team_font)
    text_width = bbox[2] - bbox[0]
    draw.text((team2_x - text_width//2, center_y + captain_size//2 + 25), team2_short, fill="#ffffff", font=team_font)
    
    if match_title:
        title_short = match_title[:40] + "..." if len(match_title) > 40 else match_title
        bbox = draw.textbbox((0, 0), title_short, font=series_font)
        text_width = bbox[2] - bbox[0]
        draw.text((THUMBNAIL_WIDTH//2 - text_width//2, center_y + captain_size//2 + 90), title_short, fill="#ffd700", font=series_font)
    
    if venue:
        venue_short = venue[:50] + "..." if len(venue) > 50 else venue
        venue_icon = "📍 " + venue_short
        bbox = draw.textbbox((0, 0), venue_short, font=venue_font)
        text_width = bbox[2] - bbox[0]
        draw.text((THUMBNAIL_WIDTH//2 - text_width//2, THUMBNAIL_HEIGHT - 55), venue_short, fill="#aaaaaa", font=venue_font)
    
    live_text = "LIVE"
    live_padding = 12
    bbox = draw.textbbox((0, 0), live_text, font=live_font)
    live_width = bbox[2] - bbox[0] + live_padding * 2
    live_height = bbox[3] - bbox[1] + live_padding * 2
    
    live_x = THUMBNAIL_WIDTH - live_width - 20
    live_y = 20
    
    draw.rectangle([live_x, live_y, live_x + live_width, live_y + live_height], fill="#dc2626")
    draw.text((live_x + live_padding, live_y + live_padding - 3), live_text, fill="#ffffff", font=live_font)
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, 'PNG', quality=95)
        return output_path
    else:
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

def generate_thumbnail_for_match(match, output_dir="static/thumbnails", team1_captain_url=None, team2_captain_url=None):
    """Generate thumbnail for a match object with captain images"""
    team1_name = match.team1_name or "Team 1"
    team2_name = match.team2_name or "Team 2"
    match_format = match.match_format or "Match"
    series = match.series_name or ""
    venue = getattr(match, 'venue', None) or ""
    
    title = f"{match_format}"
    
    filename = f"{match.match_id or 'match'}.png"
    output_path = os.path.join(output_dir, filename)
    
    team1_flag_url = None
    team2_flag_url = None
    
    if hasattr(match, 'team1_flag'):
        team1_flag_url = match.team1_flag
    if hasattr(match, 'team2_flag'):
        team2_flag_url = match.team2_flag
    
    generate_thumbnail(team1_name, team2_name, title, team1_flag_url, team2_flag_url, output_path, team1_captain_url, team2_captain_url, venue, series)
    
    return f"/static/thumbnails/{filename}"
