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
        "دزلي رابط تيك توك (فيديو أو صور)\n"
        "وأنـي أحمله إلك بأعلى جودة."
    )
    bot.reply_to(message, text)

# =========================
# TIKTOK DOWNLOADER
# =========================
@bot.message_handler(func=lambda m: m.text and "tiktok.com" in m.text)
def handle_tiktok(message):
    if not check_membership(message.from_user.id):
        bot.send_message(message.chat.id, "اشترك بالقناة أولاً ❤️", reply_markup=subscription_markup())
        return

    url = message.text.strip()
    msg = bot.reply_to(message, "جاري التحميل... ⏳")
    
    try:
        # جلب البيانات من API
        api = f"https://www.tikwm.com/api/?url={url}"
        res = requests.get(api, timeout=20).json()
        data = res.get("data", {})
        
        if not data:
            bot.edit_message_text("صار خطأ، تأكد إن الرابط صحيح ومو خاص.", message.chat.id, msg.message_id)
            return

        # 1. إذا الرابط صور (Slideshow)
        if data.get("images"):
            media = []
            for img in data["images"][:10]: # أقصى حد 10 صور للترتيب
                media.append(InputMediaPhoto(img))
            
            sent = bot.send_media_group(message.chat.id, media)
            
            # إرسال الصوت كبصمة
            if data.get("music"):
                audio_content = requests.get(data["music"], timeout=20).content
                bot.send_voice(message.chat.id, audio_content, reply_to_message_id=sent[0].message_id)
        
        # 2. إذا الرابط فيديو
        elif data.get("play"):
            # نختار أعلى جودة متوفرة (HD)
            video_url = data.get("hdplay") or data.get("play")
            
            # نرسله كـ فيديو يشتغل مباشرة مو كملف (Document)
            bot.send_video(
                message.chat.id,
                video_url,
                caption="تم التحميل بأعلى جودة ❤️"
            )
        else:
            bot.edit_message_text("عذراً، ما گدرت أحمل هذا الرابط.", message.chat.id, msg.message_id)
            return
            
        bot.delete_message(message.chat.id, msg.message_id)
        
    except Exception as e:
        print("Error:", e)
        bot.edit_message_text("صار خطأ أثناء التحميل. السيرفر عليه ضغط، جرب بعدين.", message.chat.id, msg.message_id)

# =========================
# RUN
# =========================
def run_bot():
    print("Bot Started (TikTok Only)")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)

if __name__ == "__main__":
    Thread(target=run_web).start()
    run_bot()
