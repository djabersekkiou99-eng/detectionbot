import logging
import json
import os
from flask import Flask
import threading
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)


app_flask = Flask(name)

@app_flask.route('/')
def home():
    return "Bot is running"

def run_web():
    app_flask.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web).start()
# ========== الإعدادات ==========
TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "data.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== تحميل وحفظ البيانات ==========
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"banned_words": [], "mute_duration": 10}  # مدة الميوت بالدقائق

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ========== أمر /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبا! أنا بوت الحماية\n\n"
        "📌 الأوامر المتاحة:\n"
        "/addword [كلمة] - إضافة كلمة محظورة\n"
        "/delword [كلمة] - حذف كلمة محظورة\n"
        "/listwords - عرض الكلمات المحظورة\n"
        "/setmute [دقائق] - تحديد مدة الميوت\n"
        "/help - المساعدة"
    )

# ========== أمر /help ==========
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *بوت الحماية من الكلمات المحظورة*\n\n"
        "🔇 عند اكتشاف كلمة محظورة:\n"
        "  - يتم حذف الرسالة تلقائياً\n"
        "  - يتم ميوت الشخص للمدة المحددة\n\n"
        "⚙️ *الأوامر* (للمشرفين فقط):\n"
        "`/addword كلمة` - إضافة كلمة محظورة\n"
        "`/delword كلمة` - حذف كلمة محظورة\n"
        "`/listwords` - عرض قائمة الكلمات\n"
        "`/setmute 10` - تحديد مدة الميوت بالدقائق",
        parse_mode="Markdown"
    )

# ========== التحقق من المشرف ==========
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# ========== إضافة كلمة محظورة ==========
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ استخدم: /addword [الكلمة]")
        return

    word = " ".join(context.args).lower().strip()
    
    if word in data["banned_words"]:
        await update.message.reply_text(f"⚠️ الكلمة `{word}` موجودة مسبقاً!", parse_mode="Markdown")
        return

    data["banned_words"].append(word)
    save_data(data)
    await update.message.reply_text(f"✅ تمت إضافة الكلمة المحظورة: `{word}`", parse_mode="Markdown")

# ========== حذف كلمة محظورة ==========
async def del_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ استخدم: /delword [الكلمة]")
        return

    word = " ".join(context.args).lower().strip()

    if word not in data["banned_words"]:
        await update.message.reply_text(f"⚠️ الكلمة `{word}` غير موجودة في القائمة!", parse_mode="Markdown")
        return

    data["banned_words"].remove(word)
    save_data(data)
    await update.message.reply_text(f"🗑️ تم حذف الكلمة: `{word}`", parse_mode="Markdown")

# ========== عرض الكلمات المحظورة ==========
async def list_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return

    if not data["banned_words"]:
        await update.message.reply_text("📋 قائمة الكلمات المحظورة فارغة!")
        return

    words_list = "\n".join([f"• `{w}`" for w in data["banned_words"]])
    await update.message.reply_text(
        f"📋 *الكلمات المحظورة ({len(data['banned_words'])})：*\n\n{words_list}",
        parse_mode="Markdown"
    )

# ========== تحديد مدة الميوت ==========
async def set_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ استخدم: /setmute [عدد الدقائق]\nمثال: /setmute 10")
        return

    minutes = int(context.args[0])
    if minutes < 1:
        await update.message.reply_text("⚠️ يجب أن تكون المدة دقيقة واحدة على الأقل!")
        return

    data["mute_duration"] = minutes
    save_data(data)
    await update.message.reply_text(f"✅ تم تحديد مدة الميوت: *{minutes} دقيقة*", parse_mode="Markdown")

# ========== فحص الرسائل ==========
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    # تجاهل رسائل المشرفين
    if await is_admin(update, context):
        return

    message_text = update.message.text.lower()
    chat_id = update.effective_chat.id
    user = update.effective_user
    message_id = update.message.message_id

    # البحث عن كلمة محظورة
    found_word = None
    for word in data["banned_words"]:
        if word in message_text:
            found_word = word
            break

    if not found_word:
        return

    # حذف الرسالة
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"فشل حذف الرسالة: {e}")

    # ميوت الشخص
    mute_until = datetime.now() + timedelta(minutes=data["mute_duration"])
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
            ),
            until_date=mute_until
        )

        username = f"@{user.username}" if user.username else user.first_name
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🔇 تم كتم {username}\n"
                f"⚠️ السبب: استخدام كلمة محظورة\n"
                f"⏱️ المدة: {data['mute_duration']} دقيقة"
            )
        )
        logger.info(f"تم ميوت {user.first_name} ({user.id}) بسبب: {found_word}")

    except Exception as e:
        logger.error(f"فشل الميوت: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ تم حذف رسالة تحتوي كلمة محظورة، لكن لم أتمكن من الميوت. تأكد أن البوت مشرف!"
        )

# ========== تشغيل البوت ==========
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addword", add_word))
    app.add_handler(CommandHandler("delword", del_word))
    app.add_handler(CommandHandler("listwords", list_words))
    app.add_handler(CommandHandler("setmute", set_mute))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))

    logger.info("البوت شغال! 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
