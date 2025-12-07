import os
import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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

# --------------------
# بدء البوت
# --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا!\n"
        "لديك 3 تحليلات مجانية ✅\n"
        "استخدم الأمر:\n/analyze USERNAME COUNTRY\n"
        "مثال:\n/analyze koki67110 Yemen"
    )

# --------------------
# تحليل الحساب
# --------------------
async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()
    use_count = users.get(user_id, 0)

    # التحقق من الحد المجاني أو VIP
    if user_id not in VIP_USERS and use_count >= FREE_LIMIT:
        await update.message.reply_text(
            "🚫 لقد انتهت محاولاتك المجانية.\n"
            "✅ للاشتراك واستخدام البوت بدون حدود تواصل معنا:\n"
            "@YOUR_USERNAME\n"
            "💰 سعر الاشتراك: ضع السعر هنا"
        )
        return

    # زيادة العداد للمستخدمين غير VIP
    if user_id not in VIP_USERS:
        users[user_id] = use_count + 1
        save_users(users)
        remaining = FREE_LIMIT - users[user_id]
        # رسالة تنبيه للمستخدم بالمحاولات المتبقية
        await update.message.reply_text(
            f"⚠️ تنبيه: هذه محاولتك رقم {users[user_id]} من {FREE_LIMIT} محاولات مجانية.\n"
            f"المتبقي لك: {remaining} محاولات."
        )
    else:
        remaining = "∞ (VIP)"

    # التحقق من المدخلات
    if len(context.args) < 2:
        await update.message.reply_text("❗ استخدم:\n/analyze USERNAME COUNTRY")
        return

    username = context.args[0].replace("@","")
    country = context.args[1].title()

    if country not in BEST_POSTING_HOURS:
        await update.message.reply_text(
            f"❌ الدولة غير مدعومة.\n"
            f"الدول المتاحة:\n{', '.join(BEST_POSTING_HOURS.keys())}"
        )
        return

    # جلب البيانات من TikTok
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

        msg = (
            f"📊 تحليل حساب @{username}\n\n"
            f"👥 المتابعون: {followers}\n"
            f"🔁 يتابع: {following}\n"
            f"🎬 عدد الفيديوهات: {videos}\n"
            f"❤️ الإعجابات: {likes}\n"
            f"🔥 معدل التفاعل: {engagement}%\n\n"
            f"💡 أفضل أوقات النشر في {country}: "
            f"{', '.join(BEST_POSTING_HOURS[country])}\n"
            f"💡 هاشتاغات مقترحة: "
            f"{', '.join(TRENDING_HASHTAGS[country])}\n\n"
            f"🎁 المحاولات المجانية المتبقية: {remaining}"
        )

        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء التحليل: {e}")

# --------------------
# تشغيل البوت
# --------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyze", analyze))
    print("✅ BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
