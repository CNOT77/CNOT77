import os
import random
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
# TikWM API
# =========================
def fetch_tiktok_data(url):
    spoofed_ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tikwm.com/",
        "Accept": "application/json, text/plain, */*",
        "X-Forwarded-For": spoofed_ip
    }
    api_url = f"https://www.tikwm.com/api/?url={url}&hd=1"
    response = requests.get(api_url, headers=headers, timeout=20)
    print("TikWM Status:", response.status_code)
    print("TikWM Response:", response.text[:400])
    response.raise_for_status()
    data = response.json()
    return data.get("data", {})

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
        # 1. صور (Slideshow)
        # ————————————————————————————
        if data.get("images"):
            media_group = []
            for img in data["images"][:10]:
                img_url = img if isinstance(img, str) else img.get("url", "")
                if img_url:
                    media_group.append(InputMediaPhoto(img_url))

            if media_group:
                sent = bot.send_media_group(message.chat.id, media_group)

                # الصوت — نحمله كـ bytes حتى يجي كبصمة صوتية (Voice)
                music_url = data.get("music")
                if music_url:
                    try:
                        audio_bytes = requests.get(music_url, timeout=20).content
                        bot.send_voice(
                            message.chat.id,
                            audio_bytes,
                            reply_to_message_id=sent[0].message_id
                        )
                    except Exception as ve:
                        print("Voice Error:", ve)

        # ————————————————————————————
        # 2. فيديو
        # ————————————————————————————
        elif data.get("play"):
            video_url = (
                data.get("hdplay")
                or data.get("play")
                or data.get("wmplay")
            )
            print("Video URL:", video_url[:80] if video_url else "None")

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

        else:
            bot.edit_message_text(
                "عذراً، ما گدرت أحصل البيانات من هذا الرابط.",
                message.chat.id, msg.message_id
            )
            return

        bot.delete_message(message.chat.id, msg.message_id)

    except requests.exceptions.Timeout:
        bot.edit_message_text(
            "السيرفر ما رد، جرب مرة ثانية ⏳",
            message.chat.id, msg.message_id
        )
    except requests.exceptions.RequestException as e:
        print("Request Error:", e)
        bot.edit_message_text(
            "صار خطأ بالاتصال بالسيرفر. جرب بعدين.",
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
    bot.remove_webhook()
    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60
    )

if __name__ == "__main__":
    Thread(target=run_web).start()
    run_bot()
