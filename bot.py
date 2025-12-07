# -*- coding: utf-8 -*-
import os
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# قراءة التوكن من متغير البيئة
TOKEN = os.environ.get("BOT_TOKEN")

# بدء البوت
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 مرحبًا! أرسل اسم حساب TikTok بدون @ لتحليل الحساب."
    )

# تحليل الحساب
async def analyze(update: Update, context):
    username = update.message.text.strip()
    url = f"https://www.tiktok.com/@{username}"
    headers = {"User-Agent": "Mozilla/5.0"}

    # جلب صفحة الحساب
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        await update.message.reply_text("❌ لم أتمكن من الوصول للحساب.")
        return

    # تحليل الصفحة
    soup = BeautifulSoup(r.text, "html.parser")
    try:
        script_tag = soup.find("script", id="SIGI_STATE")
        data_text = script_tag.string
        data_json = json.loads(data_text)

        user_info = data_json["UserModule"]["users"][username]
        stats = data_json["UserModule"]["stats"][username]

        followers = stats.get("followerCount", 0)
        following = stats.get("followingCount", 0)
        likes = stats.get("heartCount", 0)
        videos = stats.get("videoCount", 0)

        engagement = round((likes / followers) * 100, 2) if followers != 0 else 0

        # بيانات الفيديوهات
        video_list = data_json.get("ItemModule", {})
        video_data = []
        for vid in video_list.values():
            video_data.append({
                "title": vid.get("desc", ""),
                "views": vid.get("stats", {}).get("playCount", 0),
                "likes": vid.get("stats", {}).get("diggCount", 0),
                "comments": vid.get("stats", {}).get("commentCount", 0),
                "shares": vid.get("stats", {}).get("shareCount", 0)
            })
        df = pd.DataFrame(video_data)
        top_videos = df.sort_values(by="views", ascending=False).head(3)

    except Exception as e:
        await update.message.reply_text("❌ لم أتمكن من استخراج تفاصيل الحساب.")
        return

    # إعداد التقرير النصي
    report = f"""
✅ تحليل حساب TikTok

👤 المستخدم: @{username}
📊 المتابعون: {followers}
🎬 عدد الفيديوهات: {videos}
❤️ إجمالي الإعجابات: {likes}
📈 معدل التفاعل: {engagement}%

💡 أوقات النشر المقترحة: صباحًا، مساءً
💡 هاشتاغات مقترحة: #foryou #trending #viral

📌 أفضل 3 فيديوهات حسب المشاهدات:
"""
    for idx, row in top_videos.iterrows():
        report += f"- {row['title'][:30]}... | المشاهدات: {row['views']}\n"

    await update.message.reply_text(report)

    # رسم بياني للـ top 3 videos
    plt.figure(figsize=(6,4))
    plt.bar(top_videos['title'].str[:10], top_videos['views'])
    plt.title("أفضل 3 فيديوهات حسب المشاهدات")
    plt.ylabel("عدد المشاهدات")
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig("top_videos.png")
    plt.close()

    # إرسال الرسم البياني في تيليجرام
    await update.message.reply_photo(photo=open("top_videos.png", "rb"))

# إعداد التطبيق
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, analyze))

# تشغيل البوت
app.run_polling()