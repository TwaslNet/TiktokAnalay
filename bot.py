import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --------------------
# إعداد البوت
# --------------------
TOKEN = os.environ.get("TG_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT TOKEN not found")

FREE_LIMIT = 3
USERS_FILE = "users.json"
VIP_USERS = ["123456789"]  # ضع User ID للمشتركين الدائمين

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
# تحميل أوقات النشر والهاشتاغات من ملف خارجي
# --------------------
with open("posting_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
BEST_POSTING_HOURS = data["BEST_POSTING_HOURS"]
TRENDING_HASHTAGS = data["TRENDING_HASHTAGS"]
COUNTRIES = list(BEST_POSTING_HOURS.keys())

# --------------------
# دالة /start
# --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 مرحبًا بك في بوت تحليل TikTok!\n\n"
        "✅ لديك 3 محاولات مجانية.\n"
        "💡 لتحليل حساب استخدم:\n"
        "`/analyze USERNAME`\n"
        "ثم اختر الدولة من الأزرار.\n\n"
        "📌 لمعرفة جميع التعليمات استخدم:\n"
        "`/help`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# --------------------
# دالة /help
# --------------------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "👋 مرحبًا بك في بوت تحليل TikTok!\n\n"
        "📌 **كيفية استخدام البوت:**\n"
        "1️⃣ أرسل اسم الحساب الذي تريد تحليله:\n"
        "`/analyze USERNAME`\n"
        "مثال:\n"
        "`/analyze koki67110`\n\n"
        "2️⃣ بعد ذلك ستظهر لك قائمة بالدول المتاحة، اختر الدولة.\n\n"
        "3️⃣ بعد اختيار الدولة، سيعرض البوت:\n"
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
    await update.message.reply_text(help_text, parse_mode="Markdown")

# --------------------
# دالة /analyze البداية
# --------------------
async def analyze_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = ' '.join(context.args).replace("@","")
    if not username:
        await update.message.reply_text("❗ استخدم:\n/analyze USERNAME")
        return

    buttons = [[InlineKeyboardButton(country, callback_data=f"{username}|{country}")] for country in COUNTRIES]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("اختر الدولة:", reply_markup=reply_markup)

# --------------------
# التعامل مع اختيار الدولة
# --------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    username, country = query.data.split("|")
    user_id = str(query.from_user.id)

    users = load_users()
    use_count = users.get(user_id, 0)

    if user_id not in VIP_USERS and use_count >= FREE_LIMIT:
        await query.edit_message_text(
            "🚫 انتهت محاولاتك المجانية.\n"
            "✅ للاشتراك واستخدام البوت بدون حدود تواصل معنا:\n"
            "@YOUR_USERNAME\n💰 سعر الاشتراك: ضع السعر هنا"
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

        # زيادة العداد بعد النجاح
        if user_id not in VIP_USERS:
            users[user_id] = use_count + 1
            save_users(users)
            remaining = FREE_LIMIT - users[user_id]
            await query.edit_message_text(
                f"⚠️ هذه محاولتك رقم {users[user_id]} من {FREE_LIMIT} محاولات مجانية.\n"
                f"المتبقي لك: {remaining} محاولات."
            )
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
            f"🎁 المحاولات المجانية المتبقية: {remaining}"
        )
        await query.message.reply_text(msg)

    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحليل: {e}")

# --------------------
# تشغيل البوت
# --------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("analyze", analyze_start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
