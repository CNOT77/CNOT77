import os
import requests
import telebot
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
import yt_dlp

# =========================
# CONFIG
# =========================
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@naaafs"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =========================
# FLASK SERVER (Keep Alive)
# =========================
app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# =========================
# CHECK SUBSCRIPTION
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
        bot.send_message(
            message.chat.id,
            "لازم تشترك بالقناة أولاً ❤️",
            reply_markup=subscription_markup()
        )
        return

    text = (
        "هلا بيك ❤️\n\n"
        "دزلي رابط تيك توك (فيديو أو صور)\n"
        "وأنـي أحمله إلك بأعلى جودة."
    )
    bot.reply_to(message, text)

# =========================
# yt-dlp: استخراج معلومات الرابط
# =========================
def get_tiktok_info(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

# =========================
# TIKTOK DOWNLOADER
# =========================
@bot.message_handler(func=lambda m: m.text and "tiktok.com" in m.text)
def handle_tiktok(message):
    if not check_membership(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "اشترك بالقناة أولاً ❤️",
            reply_markup=subscription_markup()
        )
        return

    url = message.text.strip()
    msg = bot.reply_to(message, "جاري التحميل المباشر... ⏳")

    try:
        info = get_tiktok_info(url)

        # ————————————————————————————
        # 1. نظام الصور (Slideshow)
        # ————————————————————————————
        entries = info.get("entries") or []
        if entries:
            media_group = []
            for entry in entries[:10]:
                thumb = entry.get("thumbnail") or entry.get("url")
                if thumb:
                    media_group.append(InputMediaPhoto(thumb))

            if media_group:
                sent = bot.send_media_group(message.chat.id, media_group)

                # جلب الصوت الخاص بالالبوم
                music_url = info.get("music_url") or info.get("audio_url")
                if music_url:
                    audio_bytes = requests.get(music_url, timeout=20).content
                    bot.send_voice(
                        message.chat.id,
                        audio_bytes,
                        reply_to_message_id=sent[0].message_id
                    )

        # ————————————————————————————
        # 2. نظام الفيديو الطبيعي
        # ————————————————————————————
        else:
            formats = info.get("formats") or []
            best_url = None
            
            # الفلترة الذكية: البحث عن الرابط المكتوب بيه هندسة الـ nowatermark أولاً
            for f in formats:
                if 'nowatermark' in f.get('format_id', '').lower():
                    best_url = f.get('url')
                    break
            
            # إذا ما لقى المسار النظيف، ياخذ أعلى جودة مشتغلة فيديو وصوت
            if not best_url:
                for f in reversed(formats):
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        best_url = f.get('url')
                        break
            
            # الاحتياط الأخير
            if not best_url:
                best_url = info.get("url")

            if not best_url:
                bot.edit_message_text(
                    "عذراً، ما گدرت أحمل هذا الرابط.",
                    message.chat.id, msg.message_id
                )
                return

            bot.send_video(
                message.chat.id,
                best_url,
                caption="تم التحميل بأعلى جودة مباشر 100% ❤️",
                supports_streaming=True
            )

        bot.delete_message(message.chat.id, msg.message_id)

    except yt_dlp.utils.DownloadError as e:
        print("yt-dlp Error:", e)
        bot.edit_message_text(
            "ما گدرت أحمل الرابط المباشر، جرب رابط ثاني أو تأكد إن الحساب عام.",
            message.chat.id, msg.message_id
        )
    except Exception as e:
        print("Unexpected Error:", e)
        bot.edit_message_text(
            "صار خطأ أثناء التحميل. جرب بعد شوية.",
            message.chat.id, msg.message_id
        )

# =========================
# RUN
# =========================
def run_bot():
    print("Bot Started ✅")
    # تنظيف تليكرام وضمان عدم حدوث تضارب 409
    bot.remove_webhook()
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)

if __name__ == "__main__":
    Thread(target=run_web).start()
    run_bot()
