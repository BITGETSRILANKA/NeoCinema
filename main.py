import telebot
import firebase_admin
from firebase_admin import credentials, db
import re

# --- CONFIG ---
BOT_TOKEN = "8513298523:AAEx9spShVRX3N_qpynoQU99zkmlAYE8nGg"
BOT_USERNAME = "Teledrivelk_bot" # Without the @
FIREBASE_URL = "https://neocinema-6809b-default-rtdb.firebaseio.com/"
CHANNEL_ID = -1003675498085 # Your private storage channel

# --- INIT ---
cred = credentials.Certificate("secret.json")
firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
bot = telebot.TeleBot(BOT_TOKEN)
ref = db.reference('catalog')

# 1. ADMIN MODE: This watches the CHANNEL
@bot.channel_post_handler(content_types=['video', 'document'])
def index_from_channel(message):
    file = message.video if message.video else message.document
    raw_name = getattr(file, 'file_name', "Unknown Movie")
    
    # Clean name for TMDB AI
    clean_name = raw_name.split('.')[0].replace('_', ' ').replace('.', ' ')
    clean_name = re.sub(r'(720p|1080p|480p|4k|HDR|WEB|BluRay).*', '', clean_name, flags=re.IGNORECASE).strip()

    # Calculate Size
    size_mb = round(file.file_size / (1024 * 1024), 2)
    size_str = f"{size_mb} MB" if size_mb < 1000 else f"{round(size_mb/1024, 2)} GB"

    movie_data = {
        "title": clean_name,
        "size": size_str,
        "quality": "HD/1080p",
        "file_id": file.file_id,
        "message_id": message.message_id # This is the unique key
    }
    
    # Store in Firebase
    ref.push().set(movie_data)
    print(f"🚀 Indexed: {clean_name}")

# 2. USER MODE: When user clicks the link in your Android App
@bot.message_handler(commands=['start'])
def send_file_to_user(message):
    if len(message.text.split()) > 1:
        msg_id = message.text.split()[1] # Gets the ID from the ?start=... link
        try:
            # The bot forwards the file from the hidden channel to the user
            bot.copy_message(message.chat.id, CHANNEL_ID, int(msg_id))
        except Exception:
            bot.reply_to(message, "❌ File not found in my database.")
    else:
        bot.reply_to(message, "Welcome! Please use our App to browse movies.")

print("🤖 Movie Bot is running...")
bot.polling()
