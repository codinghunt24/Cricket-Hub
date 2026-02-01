from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os

THUMBNAIL_WIDTH = 1200
THUMBNAIL_HEIGHT = 630
BACKGROUND_COLOR = "#1a1a2e"
ACCENT_COLOR = "#16213e"

def download_flag(flag_url):
    """Download flag image from URL"""
    try:
        if not flag_url:
            return None
        response = requests.get(flag_url, timeout=5)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except:
        pass
    return None

def create_circle_mask(size):
    """Create circular mask for flag"""
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    return mask

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

def generate_thumbnail(team1_name, team2_name, match_title, team1_flag_url=None, team2_flag_url=None, output_path=None, team1_captain_url=None, team2_captain_url=None):
    """Generate match thumbnail with captain images"""
    
    img = Image.new('RGB', (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([0, 0, THUMBNAIL_WIDTH, 80], fill="#0f3460")
    draw.rectangle([0, THUMBNAIL_HEIGHT - 100, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT], fill="#0f3460")
    
    gradient_height = 150
    for i in range(gradient_height):
        alpha = int(255 * (1 - i / gradient_height))
        color = f"#{alpha:02x}{alpha//4:02x}{alpha//2:02x}"
        draw.line([(0, 80 + i), (THUMBNAIL_WIDTH, 80 + i)], fill=ACCENT_COLOR)
    
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        team_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
        vs_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        live_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except:
        title_font = ImageFont.load_default()
        team_font = ImageFont.load_default()
        vs_font = ImageFont.load_default()
        live_font = ImageFont.load_default()
    
    flag_size = 120
    center_y = THUMBNAIL_HEIGHT // 2
    
    team1_x = 200
    team1_flag = download_flag(team1_flag_url)
    if team1_flag:
        team1_flag = team1_flag.resize((flag_size, flag_size), Image.Resampling.LANCZOS)
        if team1_flag.mode != 'RGBA':
            team1_flag = team1_flag.convert('RGBA')
        mask = create_circle_mask(flag_size)
        img.paste(team1_flag, (team1_x - flag_size//2, center_y - 80), mask)
    else:
        draw.ellipse([team1_x - flag_size//2, center_y - 80, 
                     team1_x + flag_size//2, center_y - 80 + flag_size], 
                     fill="#2d4059", outline="#3282b8", width=3)
    
    captain_size = 100
    captain1 = download_image(team1_captain_url)
    if captain1:
        captain1 = captain1.resize((captain_size, captain_size), Image.Resampling.LANCZOS)
        if captain1.mode != 'RGBA':
            captain1 = captain1.convert('RGBA')
        cap_mask = create_circle_mask(captain_size)
        cap1_x = team1_x + flag_size//2 + 20
        cap1_y = center_y - 50
        draw.ellipse([cap1_x - 3, cap1_y - 3, cap1_x + captain_size + 3, cap1_y + captain_size + 3], fill="#e94560")
        img.paste(captain1, (cap1_x, cap1_y), cap_mask)
    
    team1_short = team1_name[:15] if len(team1_name) > 15 else team1_name
    bbox = draw.textbbox((0, 0), team1_short, font=team_font)
    text_width = bbox[2] - bbox[0]
    draw.text((team1_x - text_width//2, center_y + 60), team1_short, fill="#ffffff", font=team_font)
    
    vs_x = THUMBNAIL_WIDTH // 2
    draw.ellipse([vs_x - 40, center_y - 40, vs_x + 40, center_y + 40], fill="#e94560")
    bbox = draw.textbbox((0, 0), "VS", font=vs_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw.text((vs_x - text_width//2, center_y - text_height//2 - 5), "VS", fill="#ffffff", font=vs_font)
    
    team2_x = THUMBNAIL_WIDTH - 200
    team2_flag = download_flag(team2_flag_url)
    if team2_flag:
        team2_flag = team2_flag.resize((flag_size, flag_size), Image.Resampling.LANCZOS)
        if team2_flag.mode != 'RGBA':
            team2_flag = team2_flag.convert('RGBA')
        mask = create_circle_mask(flag_size)
        img.paste(team2_flag, (team2_x - flag_size//2, center_y - 80), mask)
    else:
        draw.ellipse([team2_x - flag_size//2, center_y - 80, 
                     team2_x + flag_size//2, center_y - 80 + flag_size], 
                     fill="#2d4059", outline="#3282b8", width=3)
    
    captain2 = download_image(team2_captain_url)
    if captain2:
        captain2 = captain2.resize((captain_size, captain_size), Image.Resampling.LANCZOS)
        if captain2.mode != 'RGBA':
            captain2 = captain2.convert('RGBA')
        cap_mask2 = create_circle_mask(captain_size)
        cap2_x = team2_x - flag_size//2 - captain_size - 20
        cap2_y = center_y - 50
        draw.ellipse([cap2_x - 3, cap2_y - 3, cap2_x + captain_size + 3, cap2_y + captain_size + 3], fill="#e94560")
        img.paste(captain2, (cap2_x, cap2_y), cap_mask2)
    
    team2_short = team2_name[:15] if len(team2_name) > 15 else team2_name
    bbox = draw.textbbox((0, 0), team2_short, font=team_font)
    text_width = bbox[2] - bbox[0]
    draw.text((team2_x - text_width//2, center_y + 60), team2_short, fill="#ffffff", font=team_font)
    
    title_short = match_title[:50] + "..." if len(match_title) > 50 else match_title
    bbox = draw.textbbox((0, 0), title_short, font=title_font)
    text_width = bbox[2] - bbox[0]
    draw.text((THUMBNAIL_WIDTH//2 - text_width//2, THUMBNAIL_HEIGHT - 70), title_short, fill="#ffffff", font=title_font)
    
    live_text = "LIVE"
    live_padding = 15
    bbox = draw.textbbox((0, 0), live_text, font=live_font)
    live_width = bbox[2] - bbox[0] + live_padding * 2
    live_height = bbox[3] - bbox[1] + live_padding * 2
    
    live_x = THUMBNAIL_WIDTH - live_width - 20
    live_y = 20
    
    draw.rectangle([live_x, live_y, live_x + live_width, live_y + live_height], fill="#dc2626")
    draw.text((live_x + live_padding, live_y + live_padding - 5), live_text, fill="#ffffff", font=live_font)
    
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
    
    title = f"{match_format}"
    if series:
        title = f"{match_format} | {series[:30]}"
    
    filename = f"{match.match_id or 'match'}.png"
    output_path = os.path.join(output_dir, filename)
    
    team1_flag_url = None
    team2_flag_url = None
    
    if hasattr(match, 'team1_flag'):
        team1_flag_url = match.team1_flag
    if hasattr(match, 'team2_flag'):
        team2_flag_url = match.team2_flag
    
    generate_thumbnail(team1_name, team2_name, title, team1_flag_url, team2_flag_url, output_path, team1_captain_url, team2_captain_url)
    
    return f"/static/thumbnails/{filename}"
