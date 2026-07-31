import os
import random
import requests
import telebot
import subprocess
import tempfile
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
        "أو دزلي أي فيديو من جهازك حتى أحوله إلك بصمة دائرية."
    )
    bot.reply_to(message, text)

# =========================
# TikWM API (TIKTOK)
# =========================
def fetch_tiktok_data(url):
    spoofed_ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.tikwm.com/",
        "X-Forwarded-For": spoofed_ip
    }
    data = {"url": url, "hd": 1}
    
    response = requests.post("https://www.tikwm.com/api/", data=data, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json().get("data", {})

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
            bot.edit_message_text("صار خطأ، تأكد إن الرابط صحيح ومو خاص.", message.chat.id, msg.message_id)
            return

        if data.get("images"):
            media_group = []
            for img in data["images"][:10]:
                img_url = img if isinstance(img, str) else img.get("url", "")
                if img_url:
                    media_group.append(InputMediaPhoto(img_url))

            if media_group:
                sent = bot.send_media_group(message.chat.id, media_group)
                music_url = data.get("music")
                if music_url:
                    try:
                        audio_bytes = requests.get(music_url, timeout=20).content
                        bot.send_voice(message.chat.id, audio_bytes, reply_to_message_id=sent[0].message_id)
                    except Exception as ve:
                        print("Voice Error:", ve)
                
                bot.delete_message(message.chat.id, msg.message_id)

        elif data.get("play"):
            video_url = data.get("hdplay") or data.get("play") or data.get("wmplay")
            if not video_url:
                bot.edit_message_text("عذراً، ما گدرت أحمل هذا الرابط.", message.chat.id, msg.message_id)
                return

            bot.edit_message_text("جاري معالجة الفيديو... ⏳", message.chat.id, msg.message_id)
            video_bytes = requests.get(video_url, timeout=30).content
            
            bot.send_video(message.chat.id, video_bytes, caption="تم التحميل بأعلى جودة ❤️", supports_streaming=True)
            bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        print("Unexpected Error:", e)
        bot.edit_message_text("صار خطأ أثناء التحميل. جرب بعد شوية.", message.chat.id, msg.message_id)

# =========================
# VIDEO TO VIDEO NOTE (بصمة دائرية - معدلة لتوفير الرام)
# =========================
@bot.message_handler(content_types=['video'])
def handle_video_note(message):
    if not check_membership(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "اشترك بالقناة أولاً ❤️",
            reply_markup=subscription_markup()
        )
        return

    msg = bot.reply_to(message, "جاري تحويل الفيديو لبصمة دائرية... ⏳\n(قد يستغرق لحظات للفيديوهات عالية الجودة)")
    in_path = out_path = None

    try:
        file_info = bot.get_file(message.video.file_id)
        downloaded = bot.download_file(file_info.file_path)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(downloaded)
            in_path = f.name

        out_path = in_path.replace(".mp4", "_note.mp4")

        # تقليل الأبعاد لـ 480x480 واستخدام ultra-fast خفيف على الـ RAM
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-t", "60",
            "-vf", "scale=480:480:force_original_aspect_ratio=increase,crop=480:480",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-b:a", "96k",
            out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        with open(out_path, "rb") as note:
            bot.send_video_note(message.chat.id, note)

        bot.delete_message(message.chat.id, msg.message_id)

    except subprocess.CalledProcessError as e:
        print("FFmpeg Error:", e.stderr.decode('utf-8', errors='ignore'))
        bot.edit_message_text("صار خطأ بالتحويل، حجم أو دقة الفيديو عالية جداً.", message.chat.id, msg.message_id)
    except Exception as e:
        print("Video Note Error:", e)
        bot.edit_message_text("صار خطأ أثناء التحويل.", message.chat.id, msg.message_id)
    finally:
        for p in (in_path, out_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

# =========================
# RUN
# =========================
def run_bot():
    print("Bot Started ✅")
    bot.remove_webhook()
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    Thread(target=run_web).start()
    run_bot()
