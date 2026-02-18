import os
import json
import re
import telebot
import firebase_admin
from firebase_admin import credentials, db

# --- 1. CONFIGURATION ---
# (On Koyeb, set these in Environment Variables)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8513298523:AAEx9spShVRX3N_qpynoQU99zkmlAYE8nGg')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', -1003675498085))
FIREBASE_URL = "https://neocinema-6809b-default-rtdb.firebaseio.com/"

# --- 2. FIREBASE INITIALIZATION ---
def init_firebase():
    config_env = os.environ.get('FIREBASE_CONFIG_JSON')
    if config_env:
        # For Koyeb/Production
        cred_dict = json.loads(config_env)
        cred = credentials.Certificate(cred_dict)
    else:
        # For Local testing
        cred = credentials.Certificate("secret.json")
    
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

init_firebase()
bot = telebot.TeleBot(BOT_TOKEN)
firebase_ref = db.reference('catalog')

# --- 3. HELPER: CLEAN FILENAMES FOR TMDB AI ---
def clean_movie_title(raw_name):
    # Removes extensions (.mp4, .mkv)
    name = re.sub(r'\.(mp4|mkv|avi|mov)$', '', raw_name, flags=re.IGNORECASE)
    # Replaces dots and underscores with spaces
    name = name.replace('.', ' ').replace('_', ' ')
    # Removes quality tags so TMDB can find it (1080p, HDR, etc)
    name = re.sub(r'(720p|1080p|2160p|4k|HDR|WEB-DL|BluRay|PSA|YTS|WEBRip).*', '', name, flags=re.IGNORECASE)
    return name.strip()

# --- 4. CHANNEL HANDLER (Indexing Mode) ---
@bot.channel_post_handler(content_types=['video', 'document'])
def index_channel_file(message):
    file = message.video if message.video else message.document
    
    # Extract Data
    raw_name = getattr(file, 'file_name', 'Unknown_Movie')
    pure_title = clean_movie_title(raw_name)
    
    # Calculate Size (MB or GB)
    size_mb = round(file.file_size / (1024 * 1024), 2)
    final_size = f"{size_mb} MB" if size_mb < 1000 else f"{round(size_mb/1024, 2)} GB"

    # Push to Firebase 'catalog' node
    movie_entry = {
        "title": pure_title,
        "size": final_size,
        "quality": "HD High-Speed",
        "message_id": message.message_id # This connects the App click to this specific post
    }
    
    firebase_ref.push().set(movie_entry)
    print(f"✅ Indexed in Firebase: {pure_title} ({final_size})")

# --- 5. PRIVATE BOT HANDLER (Delivery Mode) ---
@bot.message_handler(commands=['start'])
def handle_app_click(message):
    # This triggers when app opens link like t.me/bot?start=123
    text_parts = message.text.split()
    
    if len(text_parts) > 1:
        msg_id_from_app = text_parts[1]
        try:
            # Forwards the movie from the hidden channel directly to the user
            bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=int(msg_id_from_app)
            )
        except Exception as e:
            bot.reply_to(message, f"❌ Link expired or File moved. Error: {str(e)}")
    else:
        bot.reply_to(message, "📽️ Welcome to NeoCinema Cloud. Please use our Android App to request movies!")

# --- START ---
print("🚀 NeoCinema Indexer & Delivery Bot is Active...")
bot.infinity_polling()
