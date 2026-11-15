import os
import io
import base64
import requests
import json
import streamlit as st
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

def save_settings(thresholds):
    """Saves the slider values (including Mo Lei Tou) to a JSON file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(thresholds, f, indent=4)

# In utils.py: Update default_vals dictionary handling in load_settings
def load_settings(defaults):
    """Loads settings if they exist, otherwise returns defaults."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            try:
                data = json.load(f)
                # Ensure last_folder fallback exists
                if 'last_folder' not in data:
                    data['last_folder'] = defaults.get('last_folder', r"C:\Users\aloha\TestPhotos")
                return data
            except Exception as e:
                print(f"Error loading settings.json: {e}")
                return defaults
    return defaults

def send_telegram_ping(message):
    try:
        bot_token = st.secrets["TELEGRAM_BOT_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=8)
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def get_camera_settings(path):
    focal_length = "Unknown"
    aperture = "Unknown"
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif: return focal_length, aperture
            
            # The Scout: Accessing the standard Exif IFD (0x8769)
            exif_dict = exif.get_ifd(0x8769) if hasattr(exif, 'get_ifd') else exif
            
            # 37386 = FocalLength, 33437 = FNumber
            foc_val = exif_dict.get(37386) or exif.get(37386)
            ap_val = exif_dict.get(33437) or exif.get(33437)
            
            # --- FOCAL LENGTH DECODER ---
            if foc_val:
                try:
                    if isinstance(foc_val, tuple) and len(foc_val) == 2:
                        f_len = (foc_val[0] / foc_val[1]) if foc_val[1] != 0 else float(foc_val[0])
                    else:
                        f_len = float(foc_val) # Handles IFDRational and int/float
                    focal_length = f"{int(f_len)}mm"
                except: pass
                
            # --- APERTURE DECODER ---
            if ap_val:
                try:
                    if isinstance(ap_val, tuple):
                        f_num = ap_val[0] / ap_val[1]
                    else:
                        f_num = float(ap_val) # Handles IFDRational and int/float
                    aperture = f"f/{f_num:.1f}"
                except: pass
                
    except Exception:
        pass # The Empty Boat: Let the scan continue even if metadata fails
        
    return focal_length, aperture

def get_jpeg_files(folder_path):
    # Sorting keeps your journey through Greece in chronological order
    return sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg'))])

def encode_image(image_path, max_size=1080):
    """
    The Smart Scout: Auto-orientates and resizes the clone to 1080px to keep the AI fast 
    without losing the 'Spark' needed for aesthetic & Mo Lei Tou judging.
    """
    try:
        with Image.open(image_path) as img:
            # Correct orientation for portrait shots so llava-phi3 doesn't analyze sideways
            img = ImageOps.exif_transpose(img)
            
            # Shrink while keeping aspect ratio
            img.thumbnail((max_size, max_size))
            
            buffer = io.BytesIO()
            # Quality 85 is the 'Hippo Sweet Spot' for speed vs. detail
            img.save(buffer, format="JPEG", quality=85)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def send_telegram_photo(image_path, caption_html):
    """
    Downscales a copy in-memory and dispatches to Telegram via sendPhoto.
    Uses HTML formatting to avoid parse crashes on filenames with underscores.
    """
    try:
        bot_token = st.secrets["TELEGRAM_BOT_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

        # 1. Truncate caption to Telegram's 1024-character limit
        if len(caption_html) > 1020:
            caption_html = caption_html[:1015] + "..."

        # 2. In-memory light compression (fast upload, zero disk bloat)
        with Image.open(image_path) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1280, 1280))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            buf.seek(0)

            payload = {
                'chat_id': chat_id,
                'caption': caption_html,
                'parse_mode': 'HTML'
            }
            files = {'photo': ('champion.jpg', buf, 'image/jpeg')}
            res = requests.post(url, data=payload, files=files, timeout=20)
            return res.status_code == 200
    except Exception as e:
        print(f"Telegram photo error: {e}")
        return False