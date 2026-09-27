# -*- coding: utf-8 -*-
import os, json, threading, random, string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from flask import Flask

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7145036494"))
DATA_FILE = "database.json"

if not TOKEN:
    print("BOT_TOKEN ناقص")

USERS = {}
FILES = {}

def load_data():
    global USERS, FILES
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                USERS = data.get("users", {})
                FILES = data.get("files", {})
        except:
            USERS, FILES = {}, {}

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"users": USERS, "files": FILES}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Save error {e}")

load_data()

def get_user(uid):
    uid = str(uid)
    if uid not in USERS:
        USERS[uid] = {"balance": 0.50, "vip": False, "expire": None, "refs": 0, "daily": None, "earned": 0, "uploads": 0, "vault": []}
        save_data()
    return USERS[uid]

async def handle_start_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].startswith("file_"):
        code = context.args[0].replace("file_", "")
        if code in FILES:
            f = FILES[code]
            f["downloads"] = f.get("downloads", 0) + 1
            save_data()
            await update.message.reply_text(f"تحميل: {f['name']} - التحميلات: {f['downloads']}")
            try:
                await context.bot.send_document(update.effective_user.id, f["file_id"], caption=f["name"])
            except:
                await context.bot.send_photo(update.effective_user.id, f["file_id"])
            return
    await start(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    args = context.args
    if args and not args[0].startswith("file_") and args[0] in USERS and args[0]!= uid:
        if uid not in USERS:
            USERS[args[0]]["balance"] += 1.0
            USERS[args[0]]["refs"] += 1
            USERS[args[0]]["earned"] += 1.0
            save_data()
    u = get_user(update.effective_user.id)
    txt = f"اهلا {update.effective_user.first_name}!\n\nرصيدك: ${u['balance']:.2f} | هديتك 0.50$\nدعواتك: {u['refs']} | ملفاتك: {u['uploads']}\n\nاختر الخدمة:"
    kb = [
        [InlineKeyboardButton("رفع ملف", callback_data="upload")],
        [InlineKeyboardButton("المتجر", callback_data="shop"), InlineKeyboardButton("خزنتي", callback_data="vault")],
        [InlineKeyboardButton("بونص يومي", callback_data="daily"), InlineKeyboardButton("رابط دعوتي", callback_data="ref")],
        [InlineKeyboardButton("ترقية VIP", callback_data="vip"), InlineKeyboardButton("محفظتي", callback_data="wallet")],
        [InlineKeyboardButton("حسابي", callback_data="profile")],
    ]
    if update.message:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb))

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    u = get_user(uid)
    cost = 0 if u['vip'] else 0.10
    if u['uploads'] >= 3 and not u['vip']:
        await update.message.reply_text("وصلت الحد المجاني 3 ملفات - اشترك VIP")
        return
    doc = update.message.document or update.message.video or update.message.audio
    photo = update.message.photo[-1] if update.message.photo else None
    file_obj = doc or photo
    if not file_obj: return
    code = ''.join(random.choices(string.ascii_letters+string.digits, k=8))
    fname = getattr(file_obj, 'file_name', 'photo.jpg') if doc else 'photo.jpg'
    FILES[code] = {"owner": uid, "file_id": file_obj.file_id, "name": fname, "date": datetime.now().isoformat(), "downloads": 0}
    u['balance'] -= cost
    u['uploads'] += 1
    save_data()
    botname = (await context.bot.get_me()).username
    link = f"https://t.me/{botname}?start=file_{code}"
    await update.message.reply_text(f"تم الرفع!\n{fname}\nالرابط: {link}\nرصيدك: ${u['balance']:.2f}")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    u = get_user(uid)
    if q.data == "upload":
        await q.message.edit_text("ارسل اي ملف الان - السعر 0.10$ مجانا لل VIP", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back")]])); return
    if q.data == "daily":
        today = datetime.now().strftime("%Y-%m-%d")
        if u["daily"] == today:
            await q.answer("اخذته اليوم", show_alert=True); return
        u["balance"] += 0.25; u["daily"] = today; save_data()
        await q.answer("ربحت 0.25$", show_alert=True); await start(update, context); return
    if q.data == "ref":
        bot = (await context.bot.get_me()).username
        link = f"https://t.me/{bot}?start={uid}"
        await q.message.edit_text(f"رابطك:\n{link}\nكل شخص = 1$", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back")]])); return
    if q.data == "back":
        await start(update, context); return
    await q.message.edit_text("قريبا", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back")]]))

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot Running"

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

def run_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", handle_start_file))
    application.add_handler(CallbackQueryHandler(buttons))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, handle_file))
    print("Bot Started...")
    application.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()