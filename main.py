import os
import telebot
import yt_dlp
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# =========================
# CONFIG
# =========================
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@naaafs"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

user_links = {}

# =========================
# FLASK SERVER
# =========================
app = Flask(__name__)
@app.route('/')
def home():
    return "I'm alive", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

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
        InlineKeyboardButton("اشترك بالقناة أولاً 🌹", url=f"https://t.me/{CHANNEL_ID[1:]}")
    )
    return markup

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    if not check_membership(message.from_user.id):
        bot.send_message(message.chat.id, "لازم تشترك بالقناة أولاً ❤️", reply_markup=subscription_markup())
        return
        
    text = (
        "هلا بيك ❤️\n\n"
        "دز رابط:\n"
        "- TikTok\n"
        "- Instagram/Reels\n"
        "- YouTube\n"
        "- Shorts\n\n"
        "وأنـي أحمله بأعلى جودة."
    )
    bot.reply_to(message, text)

# =========================
# HANDLE LINKS
# =========================
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):
    if not check_membership(message.from_user.id):
        bot.send_message(message.chat.id, "اشترك بالقناة أولاً ❤️", reply_markup=subscription_markup())
        return

    url = message.text.strip()
    user_links[message.from_user.id] = url

    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("تحميل فيديو HD 🎥", callback_data="download_video")
    btn2 = InlineKeyboardButton("تحميل صوت MP3 🎵", callback_data="download_audio")
    markup.add(btn1, btn2)
    
    bot.reply_to(message, "اختار نوع التحميل:", reply_markup=markup)

# =========================
# DOWNLOAD FUNCTION (yt-dlp)
# =========================
def download_media(url, audio_only=False):
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
        'quiet': True,
        'noplaylist': True,
    }
    
    if audio_only:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        })
    else:
        ydl_opts.update({
            'format': 'best',
            'merge_output_format': 'mp4'
        })
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
        if audio_only:
            file_path = ydl.prepare_filename(info)
            file_path = file_path.rsplit(".", 1)[0] + ".mp3"
        else:
            requested = info.get("requested_downloads")
            if requested:
                file_path = requested[0]["filepath"]
            else:
                file_path = ydl.prepare_filename(info)
                if not file_path.endswith(".mp4"):
                    file_path = file_path.rsplit(".", 1)[0] + ".mp4"
        return file_path

# =========================
# BUTTONS HANDLER
# =========================
@bot.callback_query_handler(func=lambda call: call.data in ["download_video", "download_audio"])
def callback_handler(call):
    url = user_links.get(call.from_user.id)
    if not url:
        bot.answer_callback_query(call.id, "انتهت صلاحية الرابط، دز الرابط من جديد 🌹", show_alert=True)
        return

    action = call.data
    msg = bot.edit_message_text("جاري التحميل بأعلى جودة... ⏳", call.message.chat.id, call.message.message_id)
    
    try:
        if action == "download_audio":
            file_path = download_media(url, audio_only=True)
            with open(file_path, "rb") as audio:
                bot.send_audio(call.message.chat.id, audio, title="Audio")
        else:
            file_path = download_media(url, audio_only=False)
            
            # فحص نوع الملف حتى ندزه كملف او صوره
            if file_path.endswith((".mp4", ".mkv", ".webm")):
                with open(file_path, "rb") as video:
                    bot.send_document(call.message.chat.id, video, caption="تم التحميل بأعلى جودة ❤️")
            elif file_path.endswith((".jpg", ".jpeg", ".png", ".webp")):
                with open(file_path, "rb") as photo:
                    bot.send_photo(call.message.chat.id, photo, caption="تم التحميل ❤️")
            else:
                with open(file_path, "rb") as doc:
                    bot.send_document(call.message.chat.id, doc, caption="تم التحميل ❤️")

        os.remove(file_path)
        bot.delete_message(call.message.chat.id, msg.message_id)
        
    except Exception as e:
        print("Download Error:", e)
        bot.edit_message_text("صار خطأ أثناء التحميل.\nتأكد إن الرابط صحيح ومو خاص.", call.message.chat.id, msg.message_id)

# =========================
# RUN
# =========================
def run_bot():
    print("Bot Started")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)

if __name__ == "__main__":
    Thread(target=run_web).start()
    run_bot()
