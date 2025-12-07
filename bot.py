import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# قراءة توكن البوت من Environment Variables
TOKEN = os.environ.get("TG_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT TOKEN not found in environment variables")

# قاعدة بيانات لأفضل أوقات النشر حسب الدولة
BEST_POSTING_HOURS = {
    "Yemen": ["10:00 - 12:00", "19:00 - 21:00"],
    "Egypt": ["09:00 - 11:00", "18:00 - 20:00"],
    "Saudi Arabia": ["10:00 - 12:00", "20:00 - 22:00"],
    "USA": ["12:00 - 14:00", "19:00 - 21:00"],
    "UK": ["11:00 - 13:00", "18:00 - 20:00"]
}

# --- دالة بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا!\n\nاستخدم الأمر:\n/analyze USERNAME COUNTRY\nمثال:\n/analyze koki67110 Yemen"
    )

# --- دالة تحليل الحساب
async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❗ استخدم:\n/analyze USERNAME COUNTRY")
        return

    username = context.args[0].replace("@", "")
    country = context.args[1]

    url = f"https://www.tiktok.com/@{username}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            raise Exception("الحساب غير موجود أو محمي")

        txt = r.text

        # استخراج البيانات من JSON داخل صفحة TikTok
        def extract(key):
            idx = txt.find(key)
            if idx == -1:
                return "0"
            start = idx + len(key)
            end = txt.find(",", start)
            return txt[start:end]

        followers = extract('"followerCount":')
        following = extract('"followingCount":')
        likes = extract('"heartCount":')
        videos = extract('"videoCount":')

        engagement = round((int(likes)/int(followers))*100,2) if int(followers)!=0 else 0

        # اقتراح أوقات النشر حسب الدولة
        best_hours = BEST_POSTING_HOURS.get(country, ["غير معروف"])

        # رسالة التقرير
        msg = f"""
📊 تحليل حساب تيك توك @{username}

👥 المتابعون: {followers}
🔁 يتابع: {following}
🎬 عدد الفيديوهات: {videos}
❤️ الإعجابات: {likes}
🔥 معدل التفاعل: {engagement}%

💡 أفضل أوقات النشر في {country}: {', '.join(best_hours)}
"""
        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"❌ فشل التحليل: {e}")

# --- تشغيل البوت
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyze", analyze))

    print("✅ BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
