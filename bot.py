import os
import json
import asyncio
import requests
from flask import Flask, request

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

# ===========================
# إعداد المتغيرات
# ===========================
TOKEN = os.environ.get("TG_BOT_TOKEN")
APP_URL = os.environ.get("APP_URL")

if not TOKEN:
    raise RuntimeError("❌ TG_BOT_TOKEN غير موجود")
if not APP_URL:
    raise RuntimeError("❌ APP_URL غير موجود")

FREE_LIMIT = 3
USERS_FILE = "users.json"
VIP_USERS = ["123456789"]   # ضع هنا ID المشتركين الدائمين

# ===========================
# إعداد Flask
# ===========================
app = Flask(__name__)

# ===========================
# تحميل المستخدمين
# ===========================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# ===========================
# تحميل بيانات النشر
# ===========================
with open("posting_data.json", "r", encoding="utf-8") as f:
    posting_data = json.load(f)

BEST_POSTING_HOURS = posting_data["BEST_POSTING_HOURS"]
TRENDING_HASHTAGS = posting_data["TRENDING_HASHTAGS"]
COUNTRIES = list(BEST_POSTING_HOURS.keys())

# ===========================
# نص المساعدة
# ===========================
HELP_TEXT = (
    "👋 مرحبًا بك في بوت تحليل TikTok!\n\n"
    "📌 **طريقة الاستخدام:**\n"
    "1️⃣ اكتب الأمر التالي:\n"
    "`/analyze USERNAME`\n"
    "مثال:\n"
    "`/analyze koki67110`\n\n"
    "2️⃣ اختر الدولة من الأزرار التي تظهر.\n\n"
    "3️⃣ ستحصل على:\n"
    "👥 المتابعين • ❤️ الإعجابات • 🎬 الفيديوهات\n"
    "🔥 معدل التفاعل\n"
    "⏰ أفضل أوقات النشر\n"
    "📌 هاشتاغات مقترحة\n\n"
    f"⚠️ لديك {FREE_LIMIT} محاولات مجانية.\n"
    "VIP بدون حدود.\n\n"
    "💬 للاشتراك:\n"
    "@YOUR_USERNAME"
)

# ===========================
# أوامر البوت
# ===========================
async def start(update: Update, context):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ المساعدة", callback_data="HELP")]
    ])
    text = (
        "🚀 أهلاً بك في بوت تحليل TikTok\n\n"
        f"✅ لديك {FREE_LIMIT} محاولات مجانية\n"
        "استخدم:\n"
        "`/analyze USERNAME`\n\n"
        "ثم اختر الدولة من الأزرار\n"
        "📌 اضغط زر المساعدة للتعليمات"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def help_command(update: Update, context):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def analyze_start(update: Update, context):
    if not context.args:
        await update.message.reply_text("❌ استخدم:\n/analyze USERNAME")
        return

    username = context.args[0].replace("@", "")

    keyboard = [
        [InlineKeyboardButton(c, callback_data=f"{username}|{c}")]
        for c in COUNTRIES
    ]

    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"اختر الدولة لتحليل @{username}:",
        reply_markup=markup
    )

# ===========================
# التعامل مع ضغط الأزرار
# ===========================
async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()

    # زر المساعدة
    if query.data == "HELP":
        await query.message.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    username, country = query.data.split("|")
    user_id = str(query.from_user.id)

    users = load_users()
    count = users.get(user_id, 0)

    # فحص الحد المجاني
    if user_id not in VIP_USERS and count >= FREE_LIMIT:
        await query.message.reply_text(
            "🚫 انتهت محاولاتك المجانية\n\n"
            "✅ فعّل الاشتراك من خلال:\n"
            "@YOUR_USERNAME"
        )
        return

    # تحليل حساب TikTok
    url = f"https://www.tiktok.com/@{username}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            raise Exception("❌ الحساب غير موجود")

        txt = r.text

        def extract(key):
            pos = txt.find(key)
            if pos == -1:
                return "0"
            start = pos + len(key)
            end = txt.find(",", start)
            return txt[start:end]

        followers = extract('"followerCount":')
        following = extract('"followingCount":')
        likes = extract('"heartCount":')
        videos = extract('"videoCount":')

        engagement = round(
            (int(likes) / int(followers)) * 100, 2
        ) if int(followers) > 0 else 0

        # زيادة عداد المحاولات
        if user_id not in VIP_USERS:
            users[user_id] = count + 1
            save_users(users)
            remaining = FREE_LIMIT - users[user_id]
        else:
            remaining = "∞ (VIP)"

        msg = (
            f"📊 تحليل حساب @{username}\n\n"
            f"👥 المتابعون: {followers}\n"
            f"🔁 يتابع: {following}\n"
            f"🎬 الفيديوهات: {videos}\n"
            f"❤️ الإعجابات: {likes}\n"
            f"🔥 معدل التفاعل: {engagement}%\n\n"
            f"⏰ أفضل أوقات النشر في {country}:\n"
            f"{', '.join(BEST_POSTING_HOURS[country])}\n\n"
            f"📌 هاشتاغات مقترحة:\n"
            f"{', '.join(TRENDING_HASHTAGS[country])}\n\n"
            f"🎁 المحاولات المتبقية: {remaining}"
        )

        await query.message.reply_text(msg)

    except Exception as e:
        await query.message.reply_text(f"❌ خطأ: {e}")

# ===========================
# إعداد Application
# ===========================
telegram_app = Application.builder().token(TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("analyze", analyze_start))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# ===========================
# Webhook route
# ===========================
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK"

# ===========================
# الإقلاع النهائي
# ===========================
if __name__ == "__main__":

    async def main():
        await telegram_app.initialize()
        await telegram_app.bot.set_webhook(f"{APP_URL}/{TOKEN}")
        print("✅ Webhook تم تفعيله")

    asyncio.run(main())

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
