import os
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
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

# اقتراح هاشتاغات trending لكل دولة
TRENDING_HASHTAGS = {
    "Yemen": ["#foryou", "#yemen", "#viral", "#trending"],
    "Egypt": ["#foryou", "#egypt", "#trending", "#viral"],
    "Saudi Arabia": ["#foryou", "#saudi", "#trending", "#viral"],
    "USA": ["#foryou", "#usa", "#trending", "#viral"],
    "UK": ["#foryou", "#uk", "#trending", "#viral"]
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

        # استخراج البيانات الأساسية من JSON داخل الصفحة
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

        # --- أفضل 3 فيديوهات
        video_list = []
        try:
            data_json = json.loads(txt.split('{"props"')[1].split("</script>")[0].split("</script>")[0]+"}")
            item_module = data_json.get("ItemModule", {})
            for vid in item_module.values():
                video_list.append({
                    "title": vid.get("desc", ""),
                    "views": vid.get("stats", {}).get("playCount", 0)
                })
        except:
            pass

        top_videos = sorted(video_list, key=lambda x: x["views"], reverse=True)[:3]

        # رسالة التقرير
        msg = f"📊 تحليل حساب تيك توك @{username}\n\n"
        msg += f"👥 المتابعون: {followers}\n"
        msg += f"🔁 يتابع: {following}\n"
        msg += f"🎬 عدد الفيديوهات: {videos}\n"
        msg += f"❤️ الإعجابات: {likes}\n"
        msg += f"🔥 معدل التفاعل: {engagement}%\n\n"
        msg += f"💡 أفضل أوقات النشر في {country}: {', '.join(BEST_POSTING_HOURS.get(country, ['غير معروف']))}\n"
        msg += f"💡 هاشتاغات مقترحة: {', '.join(TRENDING_HASHTAGS.get(country, ['#foryou']))}\n\n"

        if top_videos:
            msg += "📌 أفضل 3 فيديوهات حسب المشاهدات:\n"
            for vid in top_videos:
                msg += f"- {vid['title'][:30]}... | المشاهدات: {vid['views']}\n"

        await update.message.reply_text(msg)

        # رسم بياني لأعلى 3 فيديوهات
        if top_videos:
            plt.figure(figsize=(6,4))
            plt.bar([v["title"][:10] for v in top_videos], [v["views"] for v in top_videos])
            plt.title("أفضل 3 فيديوهات حسب المشاهدات")
            plt.ylabel("عدد المشاهدات")
            plt.xticks(rotation=15)
            plt.tight_layout()
            plt.savefig("top_videos.png")
            plt.close()
            await update.message.reply_photo(photo=open("top_videos.png", "rb"))

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
