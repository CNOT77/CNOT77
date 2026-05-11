import os
import uuid
import requests
import yt_dlp
import telebot
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

# =====================================
# CONFIG
# =====================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@naaafs"
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

user_links = {} # لحفظ الروابط وتجنب مشكلة الـ 64 حرف مال تليكرام

# =====================================
# FLASK SERVER
# =====================================
app = Flask(__name__)
@app.route("/")
def home():
    return "I'm alive", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# =====================================
# CHECK SUBSCRIPTION
# =====================================
def check_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print("Membership Error:", e)
        return False

def subscription_markup():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("اشترك بالقناة أولاً ❤️", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    )
    return markup

# =====================================
# START
# =====================================
@bot.message_handler(commands=["start"])
def start(message):
    if not check_membership(message.from_user.id):
        bot.send_message(message.chat.id, "اشترك بالقناة أولاً ❤️", reply_markup=subscription_markup())
        return
    text = (
        "هلا بيك ❤️\n\n"
        "يدعم التحميل من:\n"
        "- TikTok\n"
        "- Instagram/Reels\n"
        "- YouTube\n"
        "- Shorts\n"
        "- Twitter/X\n\n"
        "دز الرابط وخلي الباقي علينا 🔥"
    )
    bot.reply_to(message, text)

# =====================================
# URL HANDLER
# =====================================
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_url(message):
    if not check_membership(message.from_user.id):
        bot.send_message(message.chat.id, "اشترك بالقناة أولاً ❤️", reply_markup=subscription_markup())
        return
        
    url = message.text.strip()
    user_links[message.from_user.id] = url # حفظ الرابط بالذاكرة
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("فيديو HD 🎥", callback_data="download_video"),
        InlineKeyboardButton("صوت MP3 🎵", callback_data="download_audio")
    )
    bot.reply_to(message, "اختار نوع التحميل:", reply_markup=markup)

# =====================================
# DOWNLOAD VIDEO
# =====================================
def download_video(url):
    uid = str(uuid.uuid4())
    output = f"{DOWNLOAD_DIR}/{uid}.%(ext)s"
    ydl_opts = {
        "outtmpl": output,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        requested = info.get("requested_downloads")
        if requested:
            return requested[0]["filepath"]
        file_path = ydl.prepare_filename(info)
        if not file_path.endswith(".mp4"):
            file_path = file_path.rsplit(".", 1)[0] + ".mp4"
        return file_path

# =====================================
# DOWNLOAD AUDIO
# =====================================
def download_audio(url):
    uid = str(uuid.uuid4())
    output = f"{DOWNLOAD_DIR}/{uid}.%(ext)s"
    ydl_opts = {
        "outtmpl": output,
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320"
        }]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        file_path = file_path.rsplit(".", 1)[0] + ".mp3"
        return file_path

# =====================================
# TIKTOK SLIDESHOW
# =====================================
def handle_tiktok_slideshow(chat_id, url):
    api = f"https://www.tikwm.com/api/?url={url}"
    response = requests.get(api, timeout=30).json()
    data = response.get("data")
    if not data:
        return False
    images = data.get("images")
    music = data.get("music")
    if not images:
        return False
    media = []
    for img in images[:10]:
        media.append(InputMediaPhoto(img))
    
    sent = bot.send_media_group(chat_id, media)
    
    if music:
        audio_content = requests.get(music, timeout=30).content
        bot.send_voice(chat_id, audio_content, reply_to_message_id=sent[0].message_id)
    return True

# =====================================
# CALLBACKS
# =====================================
@bot.callback_query_handler(func=lambda call: call.data in ["download_video", "download_audio"])
def callback(call):
    url = user_links.get(call.from_user.id)
    if not url:
        bot.answer_callback_query(call.id, "انتهت صلاحية الرابط، دز الرابط من جديد 🌹", show_alert=True)
        return

    action = call.data
    msg = bot.edit_message_text("جاري التحميل... ⏳", call.message.chat.id, call.message.message_id)
    
    try:
        if action == "download_audio":
            audio_path = download_audio(url)
            with open(audio_path, "rb") as audio:
                bot.send_audio(call.message.chat.id, audio)
            os.remove(audio_path)
        else:
            if "tiktok.com" in url:
                slideshow = handle_tiktok_slideshow(call.message.chat.id, url)
                if slideshow:
                    bot.delete_message(call.message.chat.id, msg.message_id)
                    return
            
            video_path = download_video(url)
            with open(video_path, "rb") as video:
                bot.send_document(call.message.chat.id, video, caption="تم التحميل بأعلى جودة ❤️")
            os.remove(video_path)
            
        bot.delete_message(call.message.chat.id, msg.message_id)
    except Exception as e:
        print("Download Error:", e)
        bot.edit_message_text("صار خطأ أثناء التحميل.\nتأكد إن الرابط صحيح ومو خاص.", call.message.chat.id, msg.message_id)

# =====================================
# RUN
# =====================================
def run_bot():
    print("BOT STARTED")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)

if __name__ == "__main__":
    Thread(target=run_web).start()
    run_bot()
