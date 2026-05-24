import os
import requests
import telebot
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

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
# FETCH FROM TIKLYDOWN API
# =========================
def fetch_tiktok_data(url):
    api_url = f"https://api.tiklydown.eu.org/api/download?url={url}"
    response = requests.get(api_url, timeout=20)
    response.raise_for_status()
    return response.json()

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
    msg = bot.reply_to(message, "جاري التحميل... ⏳")

    try:
        data = fetch_tiktok_data(url)

        if not data:
            bot.edit_message_text(
                "صار خطأ، تأكد إن الرابط صحيح ومو خاص.",
                message.chat.id, msg.message_id
            )
            return

        # ————————————————————————————
        # 1. رابط صور (Slideshow)
        # ————————————————————————————
        images = data.get("images")
        if images:
            # تصليح المسار: الدخول للمفتاح ['url'] بداخل كل صورة بـ tiklydown
            media_group = []
            for img in images[:10]:
                img_url = img.get("url")
                if img_url:
                    media_group.append(InputMediaPhoto(img_url))

            sent = bot.send_media_group(message.chat.id, media_group)

            # تصليح مسار الصوت الخاص بـ tiklydown API
            music = data.get("music") or {}
            music_url = music.get("play_url") or music.get("playUrl")
            
            if music_url:
                audio_bytes = requests.get(music_url, timeout=20).content
                bot.send_voice(
                    message.chat.id,
                    audio_bytes,
                    reply_to_message_id=sent[0].message_id
                )

        # ————————————————————————————
        # 2. رابط فيديو
        # ————————————————————————————
        else:
            video = data.get("video") or {}
            # تقديم جودة الـ HD أولاً للحصول على أفضل دقة
            video_url = (
                video.get("noWatermarkHD") or 
                video.get("noWatermark") or 
                video.get("originDownloadAddr") or 
                data.get("play")
            )

            if not video_url:
                bot.edit_message_text(
                    "عذراً، ما گدرت أحمل هذا الرابط.",
                    message.chat.id, msg.message_id
                )
                return

            bot.send_video(
                message.chat.id,
                video_url,
                caption="تم التحميل بأعلى جودة ❤️",
                supports_streaming=True
            )

        bot.delete_message(message.chat.id, msg.message_id)

    except requests.exceptions.Timeout:
        bot.edit_message_text(
            "السيرفر ما رد بوقته، جرب مرة ثانية بعد شوية ⏳",
            message.chat.id, msg.message_id
        )
    except requests.exceptions.RequestException as e:
        print("API Request Error:", e)
        bot.edit_message_text(
            "صار خطأ بالاتصال بالسيرفر. جرب بعدين.",
            message.chat.id, msg.message_id
        )
    except Exception as e:
        print("Unexpected Error:", e)
        bot.edit_message_text(
            "صار خطأ أثناء التحميل. تأكد من الرابط أو جرب لاحقاً.",
            message.chat.id, msg.message_id
        )

# =========================
# RUN
# =========================
def run_bot():
    print("Bot Started ✅")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)

if __name__ == "__main__":
    Thread(target=run_web).start()
    run_bot()
