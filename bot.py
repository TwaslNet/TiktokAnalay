import os
import json
import requests
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# --------------------
# إعداد التوكن والـ App URL
# --------------------
TOKEN = os.environ.get("TG_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ TG_BOT_TOKEN غير موجود")

APP_URL = os.environ.get("APP_URL")
if not APP_URL:
    raise RuntimeError("❌ APP_URL غير موجود")

FREE_LIMIT = 3
USERS_FILE = "users.json"
VIP_USERS = ["123456789"]

# --------------------
# تحميل بيانات المستخدمين
# --------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# --------------------
# تحميل بيانات النشر
# --------------------
with open("posting_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

BEST_POSTING_HOURS = data["BEST_POSTING_HOURS"]
TRENDING_HASHTAGS = data["TRENDING_HASHTAGS"]
COUNTRIES = list(BEST_POSTING_HOURS.keys())

# --------------------
# نص المساعدة
# --------------------
HELP_TEXT = (
    "👋 مرحبًا بك في بوت تحليل TikTok!\n\n"
    "📌 الاستخدام:\n"
    "1️⃣ أرسل:\n"
    "`/analyze USERNAME`\n"
    "2️⃣ اختر الدولة من الأزرار.\n\n"
    "3️⃣ ستحصل على:\n"
    "- المتابعين\n"
    "- الفيديوهات\n"
    "- الإعجابات\n"
    "- معدل التفاعل\n"
    "- أفضل أوقات النشر\n"
    "- هاشتاغات مقترحة\n\n"
    "⚠️ 3 محاولات مجانية فقط.\n"
    "VIP استخدام غير محدود.\n\n"
    "💡 الدعم والاشتراك:\n"
    "@YOUR_USERNAME"
)

# --------------------
# إنشاء Application
# --------------------
app_bot = Application.builder().token(TOKEN).build()

# --------------------
# أوامر البوت
# --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("ℹ️ مساعدة", callback_data="HELP")]]
    text = (
        "👋 مرحبًا بك في بوت تحليل TikTok!\n\n"
        f"🎁 لديك {FREE_LIMIT} محاولات مجانية.\n"
        "🔎 لاستخدام البوت:\n"
        "`/analyze USERNAME`\n\n"
        "ثم اختر الدولة."
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

async def analyze_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = ' '.join(context.args).replace("@", "")
    if not username:
        await update.message.reply_text("❗ استخدم:\n/analyze USERNAME")
        return

    buttons = [
        [InlineKeyboardButton(c, callback_data=f"{username}|{c}")]
        for c in COUNTRIES
    ]

    await update.message.reply_text(
        "🌍 اختر الدولة:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "HELP":
        await query.message.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    username, country = query.data.split("|")
    user_id = str(query.from_user.id)

    users = load_users()
    used = users.get(user_id, 0)

    if user_id not in VIP_USERS and used >= FREE_LIMIT:
        await query.message.reply_text(
            "🚫 انتهت محاولاتك المجانية.\n"
            "✅ للاشتراك:\n"
            "@YOUR_USERNAME"
        )
        return

    url = f"https://www.tiktok.com/@{username}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            raise Exception("الحساب غير موجود")

        txt = r.text

        def extract(key):
            i = txt.find(key)
            if i == -1:
                return "0"
            s = i + len(key)
            e = txt.find(",", s)
            return txt[s:e]

        followers = extract('"followerCount":')
        following = extract('"followingCount":')
        likes = extract('"heartCount":')
        videos = extract('"videoCount":')

        engagement = round(
            (int(likes) / int(followers)) * 100, 2
        ) if int(followers) else 0

        if user_id not in VIP_USERS:
            users[user_id] = used + 1
            save_users(users)
            remaining = FREE_LIMIT - users[user_id]
        else:
            remaining = "∞ VIP"

        msg = (
            f"📊 تحليل @{username}\n\n"
            f"👥 المتابعون: {followers}\n"
            f"🔁 يتابع: {following}\n"
            f"🎬 الفيديوهات: {videos}\n"
            f"❤️ الإعجابات: {likes}\n"
            f"🔥 معدل التفاعل: {engagement}%\n\n"
            f"⏰ أفضل أوقات النشر في {country}: "
            f"{', '.join(BEST_POSTING_HOURS[country])}\n"
            f"#️⃣ هاشتاغات:\n"
            f"{', '.join(TRENDING_HASHTAGS[country])}\n\n"
            f"🎁 المتبقي: {remaining}"
        )

        await query.message.reply_text(msg)

    except Exception as e:
        await query.message.reply_text(f"❌ خطأ: {e}")

# --------------------
# تسجيل الأوامر
# --------------------
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("help", help_command))
app_bot.add_handler(CommandHandler("analyze", analyze_start))
app_bot.add_handler(CallbackQueryHandler(button_handler))

# --------------------
# Flask Webhook
# --------------------
web = Flask(__name__)

@web.route("/", methods=["GET"])
def home():
    return "Bot is running ✅"

@web.route("/webhook", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, app_bot.bot)
    await app_bot.process_update(update)
    return "OK"

# --------------------
# التشغيل
# --------------------
if __name__ == "__main__":
    app_bot.bot.set_webhook(f"{APP_URL}/webhook")
    print("✅ Webhook تم تفعيله")

    web.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
