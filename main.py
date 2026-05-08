import os
import telebot
import yt_dlp
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# =========================
# Flask Server (Keep Alive)
# =========================
app = Flask(__name__)
@app.route('/')
def home():
    return "I'm alive", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# =========================
# Telegram Bot
# =========================
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@naaafs"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# =========================
# Check Subscription
# =========================
def check_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print("Membership Error:", e)
        return False

def subscription_markup():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("اشترك بالقناة", url=f"https://t.me/{CHANNEL_ID[1:]}")
    )
    return markup

# =========================
# Start Command
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    if not check_membership(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "لازم تشترك بالقناة أولاً ❤️",
            reply_markup=subscription_markup()
        )
        return

    bot.reply_to(
        message,
        "هلا بيك 🌹\nدز رابط تيك توك واني احمله الك بأعلى جودة (HD)."
    )

# =========================
# TikTok Downloader (yt-dlp)
# =========================
@bot.message_handler(func=lambda m: m.text and "tiktok.com" in m.text)
def download_tiktok(message):
    if not check_membership(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "اشترك بالقناة أولاً ❤️",
            reply_markup=subscription_markup()
        )
        return

    url = message.text.strip()
    msg = bot.reply_to(message, "جاري التحميل بأعلى جودة... ⏳")
    
    try:
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
            'format': 'best',
            'quiet': True,
            'noplaylist': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
        with open(file_path, 'rb') as video:
            bot.send_video(
                message.chat.id,
                video,
                caption="تم التحميل بأعلى جودة ❤️"
            )
            
        os.remove(file_path) # مسح الفيديو من السيرفر بعد إرساله حتى لا يمتلئ
        bot.delete_message(message.chat.id, msg.message_id)
        
    except Exception as e:
        print("Error:", e)
        bot.edit_message_text(
            "صار خطأ أثناء التحميل، تأكد إن الرابط صحيح ومو خاص.",
            message.chat.id,
            msg.message_id
        )

# =========================
# Run Bot
# =========================
def run_bot():
    print("Bot Started with yt-dlp")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)

if __name__ == "__main__":
    Thread(target=run_web).start()
    run_bot()
