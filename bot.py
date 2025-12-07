import os
import json
import requests
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, ContextTypes
import pandas as pd
import matplotlib.pyplot as plt

# --------------------
# إعداد Flask والبوت
# --------------------
TOKEN = os.environ.get("TG_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير محدد في Environment")

APP_URL = os.environ.get("APP_URL")  # رابط تطبيقك على Render
if not APP_URL:
    raise RuntimeError("❌ APP_URL غير محدد في Environment")

FREE_LIMIT = 3
USERS_FILE = "users.json"
VIP_USERS = ["123456789"]  # ضع User ID للمشتركين الدائمين

bot = Bot(TOKEN)
app = Flask(__name__)
dp = Dispatcher(bot, None, workers=0)

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
# تحميل أوقات النشر والهاشتاغات
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
    "📌 **كيفية استخدام البوت:**\n"
    "1️⃣ أرسل اسم الحساب:\n"
    "`/analyze USERNAME`\n"
    "2️⃣ اختر الدولة من الأزرار.\n"
    "3️⃣ بعد الاختيار، سيظهر لك:\n"
    "   - عدد المتابعين\n"
    "   - عدد الفيديوهات\n"
    "   - عدد الإعجابات\n"
    "   - معدل التفاعل\n"
    "   - أفضل أوقات النشر حسب الدولة\n"
    "   - هاشتاغات مقترحة\n\n"
    "⚠️ لديك 3 محاولات مجانية، بعدها الاشتراك مطلوب.\n"
    "VIP: استخدام غير محدود.\n\n"
    "💡 للاستفسار أو الاشتراك:\n"
    "@YOUR_USERNAME"
)

# --------------------
# دوال البوت
# --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [[InlineKeyboardButton("ℹ️ مساعدة", callback_data="HELP")]]
    markup = InlineKeyboardMarkup(buttons)
    text = (
        "👋 مرحبًا بك في بوت تحليل TikTok!\n\n"
        f"✅ لديك {FREE_LIMIT} محاولات مجانية.\n"
        "💡 لتحليل حساب استخدم:\n"
        "`/analyze USERNAME`\n"
        "ثم اختر الدولة من الأزرار.\n\n"
        "📌 اضغط على زر المساعدة إذا أردت تعليمات مفصلة."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

async def analyze_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = ' '.join(context.args).replace("@", "")
    if not username:
        await update.message.reply_text("❗ استخدم:\n/analyze USERNAME")
        return
    buttons = [[InlineKeyboardButton(c, callback_data=f"{username}|{c}")] for c in COUNTRIES]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("اختر الدولة:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "HELP":
        await query.message.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    username, country = query.data.split("|")
    user_id = str(query.from_user.id)

    users = load_users()
    use_count = users.get(user_id, 0)

    if user_id not in VIP_USERS and use_count >= FREE_LIMIT:
        await query.edit_message_text(
            "🚫 انتهت محاولاتك المجانية.\n"
            "✅ للاشتراك واستخدام البوت بدون حدود:\n"
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
            start = i + len(key)
            end = txt.find(",", start)
            return txt[start:end]

        followers = extract('"followerCount":')
        following = extract('"followingCount":')
        likes = extract('"heartCount":')
        videos = extract('"videoCount":')
        engagement = round((int(likes)/int(followers))*100,2) if int(followers)>0 else 0

        # زيادة العداد بعد نجاح التحليل
        if user_id not in VIP_USERS:
            users[user_id] = use_count + 1
            save_users(users)
            remaining = FREE_LIMIT - users[user_id]
        else:
            remaining = "∞ (VIP)"

        msg = (
            f"📊 تحليل حساب @{username}\n\n"
            f"👥 المتابعون: {followers}\n"
            f"🔁 يتابع: {following}\n"
            f"🎬 عدد الفيديوهات: {videos}\n"
            f"❤️ الإعجابات: {likes}\n"
            f"🔥 معدل التفاعل: {engagement}%\n\n"
            f"💡 أفضل أوقات النشر في {country}: {', '.join(BEST_POSTING_HOURS[country])}\n"
            f"💡 هاشتاغات مقترحة: {', '.join(TRENDING_HASHTAGS[country])}\n\n"
            f"🎁 المحاولات المتبقية: {remaining}"
        )
        await query.message.reply_text(msg)

    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحليل: {e}")

# --------------------
# تسجيل الأوامر
# --------------------
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(CommandHandler("analyze", analyze_start))
dp.add_handler(CallbackQueryHandler(button_handler))

# --------------------
# Webhook Route
# --------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.run_update(update)
    return "OK"

# --------------------
# تشغيل السيرفر
# --------------------
if __name__ == "__main__":
    bot.set_webhook(f"{APP_URL}/{TOKEN}")
    print("✅ Webhook مفعل، البوت يعمل على Render")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
