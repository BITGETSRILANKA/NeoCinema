import os
import json
import re
import threading
import telebot
import firebase_admin
from flask import Flask
from firebase_admin import credentials, db

# --- 1. KOYEB HEALTH CHECK SERVER ---
# This opens Port 8000 so Koyeb doesn't crash the bot
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is Healthy!", 200

def run_web_server():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

# --- 2. CONFIGURATION ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', -1001234567890))
FIREBASE_URL = "https://neocinema-6809b-default-rtdb.firebaseio.com/"

# --- 3. FIREBASE SETUP ---
def init_firebase():
    config_env = os.environ.get('FIREBASE_CONFIG_JSON')
    if config_env:
        cred_dict = json.loads(config_env)
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate("secret.json")
    
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

init_firebase()
bot = telebot.TeleBot(BOT_TOKEN)
firebase_ref = db.reference('catalog')

# --- 4. TITLE CLEANER (For TMDB AI) ---
def clean_title(raw_name):
    name = re.sub(r'\.(mp4|mkv|avi|mov)$', '', raw_name, flags=re.IGNORECASE)
    name = name.replace('.', ' ').replace('_', ' ')
    name = re.sub(r'(720p|1080p|2160p|4k|HDR|WEB|BluRay|PSA|YTS|WEBRip).*', '', name, flags=re.IGNORECASE)
    return name.strip()

# --- 5. INDEXER (Watch Channel) ---
@bot.channel_post_handler(content_types=['video', 'document'])
def index_files(message):
    file = message.video if message.video else message.document
    raw_name = getattr(file, 'file_name', 'Unknown_Movie')
    pure_title = clean_title(raw_name)
    
    size_mb = round(file.file_size / (1024 * 1024), 2)
    size_str = f"{size_mb} MB" if size_mb < 1000 else f"{round(size_mb/1024, 2)} GB"

    movie_entry = {
        "title": pure_title,
        "size": size_str,
        "quality": "HD/BlueRay",
        "message_id": message.message_id 
    }
    
    firebase_ref.push().set(movie_entry)
    print(f"✅ Indexed: {pure_title}")

# --- 6. DELIVERY (Bot Start Command) ---
@bot.message_handler(commands=['start'])
def deliver_file(message):
    text_parts = message.text.split()
    if len(text_parts) > 1:
        msg_id = text_parts[1]
        try:
            bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=int(msg_id)
            )
        except Exception as e:
            bot.reply_to(message, "❌ Link Expired.")
    else:
        bot.reply_to(message, "Welcome to Teledrivelk! Use the app to find movies.")

# --- 7. START BOTH (Web Server + Bot) ---
if __name__ == "__main__":
    # Start Flask in a background thread
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    print("🚀 Web server started on port 8000")
    print("🤖 Bot is polling for Telegram messages...")
    
    # Run the bot in the main thread
    bot.infinity_polling()
