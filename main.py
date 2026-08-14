# ==========================================
# 🌌 AURA BOT v7.0 - PART 1
# ==========================================

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import json, os, random, string, asyncio, re, sqlite3
from datetime import datetime, timedelta

# ==========================================
# SETUP
# ==========================================
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN environment variable is not set!")

ADMIN_IDS = [5901835425]

# ==========================================
# JSON DATABASE
# ==========================================
def load(f):
    if os.path.exists(f):
        with open(f, 'r') as x:
            return json.load(x)
    return {}

def save(f, d):
    with open(f, 'w') as x:
        json.dump(d, x, indent=4)

users = load("users.json")
vip = load("vip.json")
pay = load("pay.json")
history = load("history.json")

# ==========================================
# SQLITE DATABASE
# ==========================================
DB_PATH = "aura.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, period TEXT, number INTEGER, size TEXT, timestamp TEXT
    )''')
    conn.commit()
    conn.close()
    print("✅ Database initialized!")

init_db()

def save_result(user_id, period, number, size):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO results (user_id, period, number, size, timestamp) VALUES (?, ?, ?, ?, ?)",
              (user_id, period, number, size, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT number, size FROM results WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

# ==========================================
# QR FINDER
# ==========================================
def find_qr():
    paths = ["qr.jpg", "assets/qr.jpg", "VidMate/assets/qr.jpg", "/storage/emulated/0/qr.jpg"]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def gen_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def get_admin_buttons(req_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ APPROVE", callback_data=f"app_{req_id}"),
         InlineKeyboardButton("❌ REJECT", callback_data=f"rej_{req_id}")]
    ])

def get_emoji():
    return random.choice(["🎯", "🔥", "⭐", "💎", "🏆", "👑", "🚀"])

def get_loss_emoji():
    return random.choice(["😅", "🥲", "😊", "🙂", "😌"])

async def send_typing(context, chat_id):
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except:
        pass

# ==========================================
# KEYBOARDS
# ==========================================
start_btn = ReplyKeyboardMarkup([["🚀 START"]], resize_keyboard=True)

main_menu = ReplyKeyboardMarkup([
    ["💳 MEMBERSHIP", "▶️ PLAY"],
    ["👤 PROFILE", "📞 SUPPORT"],
    ["🏠 HOME"]
], resize_keyboard=True)

admin_menu = ReplyKeyboardMarkup([
    ["📊 STATS", "💰 PAYMENTS"],
    ["📢 BROADCAST", "🔙 BACK"]
], resize_keyboard=True)

timer_menu = ReplyKeyboardMarkup([
    ["⏱ 30s", "⏱ 1m"],
    ["⏱ 2m", "⏱ 5m"],
    ["🏠 HOME"]
], resize_keyboard=True)

result_number_menu = ReplyKeyboardMarkup([
    ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣"],
    ["5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"],
    ["⏱ TIMER", "🏠 HOME"]
], resize_keyboard=True)

result_keyboard = ReplyKeyboardMarkup([
    ["🔴 BIG", "🔵 SMALL"],
    ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣"],
    ["5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"],
    ["⏱ TIMER", "🏠 HOME"]
], resize_keyboard=True)

start_button_menu = ReplyKeyboardMarkup([["🚀 START 🚀"]], resize_keyboard=True)
profile_menu = ReplyKeyboardMarkup([["▶️ START ANALYSIS"], ["🏠 HOME"]], resize_keyboard=True)
membership_menu = ReplyKeyboardMarkup([["👑 BUY ₹299"], ["❌ CANCEL VIP"], ["🔙 BACK"]], resize_keyboard=True)

# ==========================================
# START FUNCTION
# ==========================================
async def start(update, context):
    uid = str(update.effective_user.id)
    if uid not in users:
        users[uid] = {"id": uid, "name": update.effective_user.username or "Unknown", "joined": str(datetime.now()), "win_count": 0, "loss_count": 0, "level": 0}
        save("users.json", users)
    await send_typing(context, update.effective_chat.id)
    await asyncio.sleep(0.3)
    await update.message.reply_text("🌟 Welcome to AURA BOT!\n\nClick START to begin! 🚀", reply_markup=start_btn)

async def start_button(update, context):
    uid = str(update.effective_user.id)
    is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
    is_verified = context.user_data.get('verified', False)
    await send_typing(context, update.effective_chat.id)
    await asyncio.sleep(0.3)
    banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
    kb = admin_menu if int(uid) in ADMIN_IDS else main_menu
    await update.message.reply_text(banner, reply_markup=kb)
    
    
    
    
    
    # ==========================================
# 🌌 AURA BOT v7.0 - PART 2
# ==========================================

def get_home_banner(username, is_vip, is_verified=False):
    status = "★ VIP" if is_vip else "FREE"
    verify = "🔐 VERIFIED" if is_verified else "🔓 UNVERIFIED"
    online = "🟢 ONLINE" if is_verified else "🟡 AWAITING"
    return f"""
𝟬𝟭 — 𝗛𝗢𝗠𝗘 / 𝗪𝗘𝗟𝗖𝗢𝗠𝗘
┌─[ 🌌 𝗖/𝗧 𝗪𝗜𝗡 𝗛𝗔𝗖𝗞 ]
│
├─┬─[ 𝗦𝗬𝗦𝗧𝗘𝗠 𝗜𝗡𝗙𝗢 ]
│ ├─ 𝗨𝗦𝗘𝗥    :: @{username}
│ ├─ 𝗔𝗖𝗖𝗘𝗦𝗦  :: {status}
│ ├─ 𝗦𝗧𝗔𝗧𝗨𝗦  :: {online}
│ └─ 𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬 :: {verify}
│
└─[ 🔐 𝗖/𝗧://𝗦𝗘𝗖𝗨𝗥𝗘_𝗖𝗢𝗡𝗡𝗘𝗖𝗧𝗜𝗢𝗡 ]
"""

def get_vip_banner(username, expiry, passkey):
    remain = int((datetime.fromisoformat(expiry) - datetime.now()).total_seconds() / 3600)
    return f"""
𝟬𝟮 — 𝗩𝗜𝗣 𝗔𝗖𝗧𝗜𝗩𝗘
┌─[ 🔐 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦 ]
│
├─[ 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 ]
│ ├─ 𝗦𝗧𝗔𝗧𝗨𝗦 :: 🟢 𝗩𝗜𝗣 𝗔𝗖𝗧𝗜𝗩𝗘
│ ├─ 𝗥𝗘𝗠𝗔𝗜𝗡 :: ⏰ {remain}𝗛
│ └─ 𝗣𝗔𝗦𝗦𝗞𝗘𝗬 :: 🔑 {passkey}
│
└─[ 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦_𝗚𝗥𝗔𝗡𝗧𝗘𝗗 ]
"""

def get_passkey_banner():
    return """
𝟬𝟯 — 𝗣𝗔𝗦𝗦𝗞𝗘𝗬 𝗩𝗘𝗥𝗜𝗙𝗬
┌─[ 🔑 𝗖/𝗧 𝗪𝗜𝗡 𝗛𝗔𝗖𝗞 ]
│
├─[ 𝗣𝗔𝗦𝗦𝗞𝗘𝗬 𝗣𝗥𝗢𝗧𝗢𝗖𝗢𝗟 ]
│
│  > 𝗘𝗡𝗧𝗘𝗥 𝗬𝗢𝗨𝗥 𝗞𝗘𝗬 🔑
│
└─[ 𝗖/𝗧://𝗪𝗔𝗜𝗧𝗜𝗡𝗚 ]
"""

def get_verified_banner():
    return """
┌─[ 🔑 𝗖/𝗧 𝗪𝗜𝗡 𝗛𝗔𝗖𝗞 ]
│
├─[ 𝗞𝗘𝗬 𝗩𝗘𝗥𝗜𝗙𝗜𝗘𝗗 ✅ ]
│
│   🔑 𝗬𝗢𝗨𝗥 𝗞𝗘𝗬 𝗛𝗔𝗦 𝗕𝗘𝗘𝗡
│      𝗩𝗘𝗥𝗜𝗙𝗜𝗘𝗗 ✅
│
│   🟢 𝗛𝗔𝗖𝗞 𝗔𝗖𝗧𝗜𝗩𝗘
│
└─[ 🔓 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦_𝗚𝗥𝗔𝗡𝗧𝗘𝗗 ]
"""

def get_period_banner():
    return """
𝟬𝟱 — 𝗣𝗘𝗥𝗜𝗢𝗗 𝗘𝗡𝗧𝗥𝗬
┌─[ 📊 𝗖/𝗧://𝗔𝗡𝗔𝗟𝗬𝗦𝗜𝗦 ]
│
├─[ 🔢 𝗘𝗡𝗧𝗘𝗥 𝗣𝗘𝗥𝗜𝗢𝗗 ]
│
│  > 𝗪𝗔𝗜𝗧𝗜𝗡𝗚 𝗙𝗢𝗥 𝗜𝗡𝗣𝗨𝗧...
│
└─[ 𝗖/𝗧://𝗗𝗔𝗧𝗔_𝗜𝗡𝗧𝗔𝗞𝗘 ]
"""

def get_result_banner():
    return """
𝟬𝟲 — 𝗥𝗘𝗦𝗨𝗟𝗧 𝗘𝗡𝗧𝗥𝗬
┌─[ 📊 𝗖/𝗧://𝗥𝗘𝗦𝗨𝗟𝗧 ]
│
├─[ 🔢 𝗘𝗡𝗧𝗘𝗥 𝗥𝗘𝗦𝗨𝗟𝗧 ]
│
│  > 𝗪𝗔𝗜𝗧𝗜𝗡𝗚 𝗙𝗢𝗥 𝗜𝗡𝗣𝗨𝗧...
│
└─[ 𝗖/𝗧://𝗗𝗔𝗧𝗔_𝗜𝗡𝗧𝗔𝗞𝗘 ]
"""

def get_analysis_banner(period, category, num1, num2):
    return f"""
𝟬𝟳 — 𝗔𝗡𝗔𝗟𝗬𝗦𝗜𝗦 𝗥𝗘𝗦𝗨𝗟𝗧
┌─[ 📊 𝗖/𝗧://𝗔𝗡𝗔𝗟𝗬𝗦𝗜𝗦 ]
│
├─ 𝗣𝗘𝗥𝗜𝗢𝗗   :: {period}
├─ 𝗖𝗔𝗧𝗘𝗚𝗢𝗥𝗬 :: {category}
├─ 𝗡𝗨𝗠𝗕𝗘𝗥   :: {num1} , {num2}
│
└─[ ⚠ 𝗘𝗗𝗨𝗖𝗔𝗧𝗜𝗢𝗡𝗔𝗟 𝗣𝗨𝗥𝗣𝗢𝗦𝗘 ]
"""

def get_stats_banner(win, loss, level, period, category, num1, num2):
    return f"""
𝟬𝟴 — 𝗦𝗧𝗔𝗧𝗦
┌─[ 📈 𝗖/𝗧://𝗦𝗧𝗔𝗧𝗦 ]
│
├─[ 𝗦𝗘𝗦𝗦𝗜𝗢𝗡 ]
│ ├─ 🏆 𝗪𝗜𝗡   :: {win:02d}
│ ├─ ❌ 𝗟𝗢𝗦𝗦  :: {loss:02d}
│ └─ 📊 𝗟𝗘𝗩𝗘𝗟 :: {level:02d}
│
├─[ 𝗡𝗘𝗫𝗧 ]
│ ├─ 🔢 𝗣𝗘𝗥𝗜𝗢𝗗   :: {period}
│ ├─ 📈 𝗖𝗔𝗧𝗘𝗚𝗢𝗥𝗬 :: {category}
│ └─ 📊 𝗡𝗨𝗠𝗕𝗘𝗥   :: {num1} , {num2}
│
└─[ 𝗖/𝗧://𝗟𝗜𝗩𝗘 ]
"""




# ==========================================
# 🌌 AURA BOT v7.0 - PART 3
# ==========================================

async def buy_membership(update, context):
    uid = str(update.effective_user.id)
    
    if uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now():
        banner = get_vip_banner(update.effective_user.username, vip[uid]['expiry'], vip[uid]['key'])
        await update.message.reply_text(f"""{banner}\n┌─[ 🔐 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦 ]\n│\n├─[ 👑 𝗠𝗔𝗡𝗔𝗚𝗘 𝗬𝗢𝗨𝗥 𝗩𝗜𝗣 ]\n│\n│ ├─ 👑 𝗕𝗨𝗬 𝗡𝗢𝗪 :: ₹299\n│ │     └─ 𝗘𝗫𝗧𝗘𝗡𝗗 𝗩𝗜𝗣\n│ │\n│ ├─ ❌ 𝗖𝗔𝗡𝗖𝗘𝗟 𝗩𝗜𝗣\n│ │     └─ 𝗖𝗔𝗡𝗖𝗘𝗟 𝗩𝗜𝗣\n│ │\n│ └─ 🔙 𝗕𝗔𝗖𝗞\n│       └─ 𝗚𝗢 𝗕𝗔𝗖𝗞\n│\n└─[ 🔐 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦_𝗚𝗥𝗔𝗡𝗧𝗘𝗗 ]""", reply_markup=membership_menu)
        return
    
    # LOADING
    msg = await update.message.reply_text("""
┌─[ ⏳ 𝗖/𝗧://𝗟𝗢𝗔𝗗𝗜𝗡𝗚 ]
│
├─[ 🔄 𝗙𝗘𝗧𝗖𝗛𝗜𝗡𝗚 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 ]
│
│  █░░░░░░░░░  10%
│
└─[ 𝗖/𝗧://𝗪𝗔𝗜𝗧𝗜𝗡𝗚 ]""")
    await asyncio.sleep(0.4)
    await msg.edit_text("""
┌─[ ⏳ 𝗖/𝗧://𝗟𝗢𝗔𝗗𝗜𝗡𝗚 ]
│
├─[ 🔄 𝗙𝗘𝗧𝗖𝗛𝗜𝗡𝗚 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 ]
│
│  ████░░░░░░  40%
│
└─[ 𝗖/𝗧://𝗪𝗔𝗜𝗧𝗜𝗡𝗚 ]""")
    await asyncio.sleep(0.4)
    await msg.edit_text("""
┌─[ ⏳ 𝗖/𝗧://𝗟𝗢𝗔𝗗𝗜𝗡𝗚 ]
│
├─[ 🔄 𝗙𝗘𝗧𝗖𝗛𝗜𝗡𝗚 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 ]
│
│  ████████░░  80%
│
└─[ 𝗖/𝗧://𝗪𝗔𝗜𝗧𝗜𝗡𝗚 ]""")
    await asyncio.sleep(0.4)
    await msg.edit_text("""
┌─[ ✅ 𝗖/𝗧://𝗥𝗘𝗔𝗗𝗬 ]
│
├─[ ✅ 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 𝗟𝗢𝗔𝗗𝗘𝗗 ]
│
│  ██████████  100%
│
└─[ 🔐 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦_𝗚𝗥𝗔𝗡𝗧𝗘𝗗 ]""")
    await asyncio.sleep(0.3)
    await msg.delete()
    
    # QR
    qr_path = find_qr()
    if qr_path:
        try:
            with open(qr_path, 'rb') as f:
                await update.message.reply_photo(InputFile(f), caption="""┌─[ 💳 𝗖/𝗧://𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 ]\n│\n├─[ 💳 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 𝗣𝗟𝗔𝗡𝗦 ]\n│\n├─ 👑 𝗩𝗜𝗣 𝗣𝗟𝗔𝗡 :: ₹299 / 3 𝗗𝗔𝗬𝗦\n│\n│  ├─ ✅ 𝗙𝗨𝗟𝗟 𝗔𝗖𝗖𝗘𝗦𝗦\n│  └─ ✅ 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗖𝗢𝗡𝗧𝗘𝗡𝗧\n│\n└─[ ⏰ 3 𝗗𝗔𝗬𝗦 / 72 𝗛𝗢𝗨𝗥𝗦 ]""")
        except:
            await update.message.reply_text("""┌─[ 💳 𝗖/𝗧://𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 ]\n│\n├─[ 💳 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 𝗣𝗟𝗔𝗡𝗦 ]\n│\n├─ 👑 𝗩𝗜𝗣 𝗣𝗟𝗔𝗡 :: ₹299 / 3 𝗗𝗔𝗬𝗦\n│\n│  ├─ ✅ 𝗙𝗨𝗟𝗟 𝗔𝗖𝗖𝗘𝗦𝗦\n│  └─ ✅ 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗖𝗢𝗡𝗧𝗘𝗡𝗧\n│\n└─[ ⏰ 3 𝗗𝗔𝗬𝗦 / 72 𝗛𝗢𝗨𝗥𝗦 ]\n\n💳 Pay via UPI: aura@pay""")
    else:
        await update.message.reply_text("""┌─[ 💳 𝗖/𝗧://𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 ]\n│\n├─[ 💳 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 𝗣𝗟𝗔𝗡𝗦 ]\n│\n├─ 👑 𝗩𝗜𝗣 𝗣𝗟𝗔𝗡 :: ₹299 / 3 𝗗𝗔𝗬𝗦\n│\n│  ├─ ✅ 𝗙𝗨𝗟𝗟 𝗔𝗖𝗖𝗘𝗦𝗦\n│  └─ ✅ 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗖𝗢𝗡𝗧𝗘𝗡𝗧\n│\n└─[ ⏰ 3 𝗗𝗔𝗬𝗦 / 72 𝗛𝗢𝗨𝗥𝗦 ]\n\n💳 Pay via UPI: aura@pay""")
    
    await asyncio.sleep(0.5)
    await update.message.reply_text("👆𝗣𝗔𝗬 𝗔𝗡𝗗 𝗦𝗘𝗡𝗗 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧 👆", reply_markup=ReplyKeyboardRemove())
    context.user_data['waiting_payment'] = True

async def cancel_vip(update, context):
    uid = str(update.effective_user.id)
    if uid not in vip:
        await update.message.reply_text("❌ No Active VIP!", reply_markup=main_menu)
        return
    exp = datetime.fromisoformat(vip[uid]['expiry'])
    if exp <= datetime.now():
        await update.message.reply_text("❌ Already Expired!", reply_markup=main_menu)
        return
    await update.message.reply_text(f"""⚠️ CANCEL VIP\n━━━━━━━━━━━━━━━━━━━━━━\n🔑 {vip[uid]['key']}\n📅 {exp.strftime('%Y-%m-%d %H:%M')}\n━━━━━━━━━━━━━━━━━━━━━━\n[ ✅ YES ]  [ ❌ NO ]""", reply_markup=ReplyKeyboardMarkup([["✅ YES, CANCEL VIP"], ["❌ NO, GO BACK"]], resize_keyboard=True))
    context.user_data['waiting_cancel'] = True

async def confirm_cancel(update, context):
    uid = str(update.effective_user.id)
    text = update.message.text
    if not context.user_data.get('waiting_cancel'):
        return
    if text == "✅ YES, CANCEL VIP":
        if uid in vip:
            del vip[uid]
            save("vip.json", vip)
            context.user_data['verified'] = False
            await update.message.reply_text("❌ VIP CANCELLED!", reply_markup=main_menu)
        context.user_data['waiting_cancel'] = False
    elif text == "❌ NO, GO BACK":
        await update.message.reply_text("✅ Cancelled!", reply_markup=main_menu)
        context.user_data['waiting_cancel'] = False
        
        
        
        
        
        # ==========================================
# 🌌 AURA BOT v7.0 - PART 4
# ==========================================

async def upload(update, context):
    uid = str(update.effective_user.id)
    if 'plan' not in context.user_data:
        await update.message.reply_text("❌ Use /buy first!", reply_markup=main_menu)
        return
    await update.message.reply_text("📤 Send payment screenshot now:")
    context.user_data['waiting'] = True

async def handle_photo(update, context):
    uid = str(update.effective_user.id)
    
    if not context.user_data.get('waiting_payment') and not context.user_data.get('waiting'):
        await update.message.reply_text("❌ Use MEMBERSHIP first!", reply_markup=main_menu)
        return
    
    # Upload Loading
    msg = await update.message.reply_text("⏳ UPLOADING...\n█░░░░░░░░░ 10%")
    await asyncio.sleep(0.2)
    await msg.edit_text("⏳ UPLOADING...\n█████░░░░░ 50%")
    await asyncio.sleep(0.2)
    await msg.edit_text("⏳ UPLOADING...\n██████████ 100% ✅")
    await asyncio.sleep(0.2)
    await msg.delete()
    
    photo = update.message.photo[-1].file_id
    req = f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    user_name = update.effective_user.username or "Unknown"
    
    # ✅ SAVE PAYMENT
    pay[req] = {"id": req, "uid": uid, "name": user_name, "photo": photo, "time": str(datetime.now()), "status": "pending"}
    save("pay.json", pay)
    print(f"✅ Payment saved: {req}")
    
    # ✅ SEND TO ADMIN (IMMEDIATE)
    admin_sent = False
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo,
                caption=f"""🔔 NEW PAYMENT REQUEST!
━━━━━━━━━━━━━━━━━━━━━━
📋 ID: {req}
👤 User: @{user_name}
🆔 UID: {uid}
💰 Amount: ₹299
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━
Click button below:""",
                reply_markup=get_admin_buttons(req)
            )
            print(f"✅ Sent to admin: {admin_id}")
            admin_sent = True
        except Exception as e:
            print(f"❌ Error sending to admin {admin_id}: {e}")
    
    # ✅ SHOW WAITING ANIMATION TO USER
    wait_msg = await update.message.reply_text(
        f"""𝗪𝗔𝗜𝗧 𝗙𝗢𝗥 𝗖𝗛𝗘𝗖𝗞𝗜𝗡𝗚 ‼️
━━━━━━━━━━━━━━━━━━━━━━
📋 ID: {req}
⏳ Status: PENDING
━━━━━━━━━━━━━━━━━━━━━━""",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # ✅ START ANIMATION
    context.user_data['waiting_animation'] = True
    context.user_data['waiting_message'] = wait_msg
    context.user_data['pending_req_id'] = req
    
    asyncio.create_task(animated_wait_replace(update, context))
    
    if admin_sent:
        await update.message.reply_text("✅ Screenshot sent to admin!\n⏳ Waiting for approval...", reply_markup=main_menu)
    else:
        await update.message.reply_text("⚠️ Could not send to admin. Please try again.", reply_markup=main_menu)
    
    context.user_data['waiting_payment'] = False
    context.user_data['waiting'] = False

# ✅ DOT ANIMATION
async def animated_wait_replace(update, context):
    msg = context.user_data.get('waiting_message')
    if not msg:
        msg = await update.message.reply_text("𝗪𝗔𝗜𝗧 𝟮 𝗠𝗜𝗡𝗨𝗧𝗘𝗦")
        context.user_data['waiting_message'] = msg
    
    await asyncio.sleep(0.5)
    
    dot_index = 0
    while context.user_data.get('waiting_animation', False):
        dot_index += 1
        if dot_index > 7:
            dot_index = 1
        dots_text = "." * dot_index
        try:
            await msg.edit_text(f"𝗪𝗔𝗜𝗧 𝟮 𝗠𝗜𝗡𝗨𝗧𝗘𝗦\n{dots_text}")
        except:
            pass
        await asyncio.sleep(1.2)
    
    # Animation stopped - delete message
    try:
        if context.user_data.get('waiting_message'):
            await context.user_data['waiting_message'].delete()
            context.user_data['waiting_message'] = None
    except:
        pass

# ✅ STOP ANIMATION FOR USER
async def stop_user_animation(context, user_id):
    try:
        user_data = context.application.user_data.get(user_id, {})
        user_data['waiting_animation'] = False
        if user_data.get('waiting_message'):
            try:
                await user_data['waiting_message'].delete()
            except:
                pass
            user_data['waiting_message'] = None
        context.application.user_data[user_id] = user_data
        print(f"✅ Animation stopped for user: {user_id}")
    except Exception as e:
        print(f"❌ Error stopping animation: {e}")

# ✅ CALLBACK
async def callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    admin_id = int(query.from_user.id)
    
    print(f"🔔 Callback: {data} from admin {admin_id}")
    
    if admin_id not in ADMIN_IDS:
        await context.bot.send_message(admin_id, "❌ You are not admin!")
        return
    
    if data.startswith("app_"):
        req_id = data.replace("app_", "")
        await approve_payment(query, context, req_id)
    elif data.startswith("rej_"):
        req_id = data.replace("rej_", "")
        await reject_payment(query, context, req_id)

# ✅ APPROVE PAYMENT
async def approve_payment(query, context, req_id):
    print(f"✅ Approving: {req_id}")
    
    if req_id not in pay:
        await context.bot.send_message(query.from_user.id, "❌ Request not found!")
        return
    
    p = pay[req_id]
    if p['status'] != 'pending':
        await context.bot.send_message(query.from_user.id, "❌ Already processed!")
        return
    
    key = gen_key()
    uid = p['uid']
    expiry = datetime.now() + timedelta(days=3)
    
    vip[uid] = {"user_id": uid, "key": key, "expiry": expiry.isoformat()}
    save("vip.json", vip)
    print(f"✅ VIP activated for: {uid}")
    
    p['status'] = 'approved'
    p['passkey'] = key
    save("pay.json", pay)
    print(f"✅ Payment approved: {req_id}")
    
    # ✅ STOP ANIMATION
    await stop_user_animation(context, uid)
    
    # ✅ SEND PASSKEY TO USER
    try:
        await context.bot.send_message(
            chat_id=uid,
            text=f"""╔══════════════════════════════════════╗
║              ✅ APPROVED!              ║
╠══════════════════════════════════════╣
║                                        ║
║    🎉 Your VIP has been activated!    ║
║                                        ║
║    ──────── MEMBERSHIP ────────       ║
║    👑 Plan      : VIP 3 Days          ║
║    ⏰ Duration  : 72 Hours            ║
║    🔑 Passkey  : {key}                ║
║    📅 Expiry   : {expiry.strftime('%Y-%m-%d %H:%M')}║
║                                        ║
║    ⚠️ Passkey linked to your account! ║
║    ▶️ Use /play to start playing      ║
║                                        ║
╚══════════════════════════════════════╝""",
            reply_markup=main_menu
        )
        print(f"✅ Passkey sent to user: {uid}")
    except Exception as e:
        print(f"❌ Error sending to user: {e}")
    
    # ✅ SEND CONFIRMATION TO ADMIN
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=f"""╔══════════════════════════════════════╗
║              ✅ APPROVED!              ║
╠══════════════════════════════════════╣
║                                        ║
║    ✅ Payment verified successfully!  ║
║                                        ║
║    ──────── DETAILS ────────          ║
║    📋 Request : {req_id}              ║
║    👤 User    : @{p['name']}          ║
║    🔑 Passkey : {key}                 ║
║    💰 Amount  : ₹299                  ║
║    ⏰ Duration: 3 Days (72 Hours)     ║
║                                        ║
║    ✅ Passkey sent to user!           ║
║                                        ║
╚══════════════════════════════════════╝"""
    )
    
    try:
        await query.message.delete()
    except:
        pass

# ✅ REJECT PAYMENT
async def reject_payment(query, context, req_id):
    print(f"❌ Rejecting: {req_id}")
    
    if req_id not in pay:
        await context.bot.send_message(query.from_user.id, "❌ Request not found!")
        return
    
    p = pay[req_id]
    if p['status'] != 'pending':
        await context.bot.send_message(query.from_user.id, "❌ Already processed!")
        return
    
    p['status'] = 'rejected'
    save("pay.json", pay)
    print(f"❌ Payment rejected: {req_id}")
    
    # ✅ STOP ANIMATION
    await stop_user_animation(context, p['uid'])
    
    # ✅ SEND REJECTION TO USER
    try:
        await context.bot.send_message(
            chat_id=p['uid'],
            text=f"""╔══════════════════════════════════════╗║              ❌ REJECTED!              ║
╠══════════════════════════════════════╣
║                                        ║
║    😔 Payment verification failed!    ║
║                                        ║
║    ──── POSSIBLE REASONS ────         ║
║    ❌ Screenshot is unclear           ║
║    ❌ Invalid payment proof           ║
║    ❌ Incorrect amount (₹299)         ║
║    ❌ Missing transaction ID          ║
║                                        ║
║    ──────── NEXT STEP ────────        ║
║    📤 Please upload again: /upload    ║
║                                        ║
║    📌 Make sure to show:              ║
║    ✅ ₹299 Payment                    ║
║    ✅ Transaction ID                  ║
║    ✅ Date & Time                     ║
║                                        ║
╚══════════════════════════════════════╝""",
            reply_markup=main_menu
        )
        print(f"✅ Rejection sent to user: {p['uid']}")
    except Exception as e:
        print(f"❌ Error sending to user: {e}")
    
    # ✅ SEND CONFIRMATION TO ADMIN
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=f"""╔══════════════════════════════════════╗
║              ❌ REJECTED!              ║
╠══════════════════════════════════════╣
║                                        ║
║    ❌ Payment rejected!               ║
║                                        ║
║    ──────── DETAILS ────────          ║
║    📋 Request : {req_id}              ║
║    👤 User    : @{p['name']}          ║
║                                        ║
║    ✅ User notified to upload again!  ║
║                                        ║
╚══════════════════════════════════════╝"""
    )
    
    try:
        await query.message.delete()
    except:
        pass
        
        
        
        
       
       # ==========================================
# 🌌 AURA BOT v7.0 - PART 5
# ==========================================

async def play(update, context):
    uid = str(update.effective_user.id)
    
    if uid not in vip:
        await update.message.reply_text("❌ VIP REQUIRED!\nBuy: 💳 MEMBERSHIP", reply_markup=ReplyKeyboardMarkup([["💳 MEMBERSHIP"], ["🏠 HOME"]], resize_keyboard=True))
        return
    
    exp = datetime.fromisoformat(vip[uid]['expiry'])
    if exp <= datetime.now():
        await update.message.reply_text("❌ EXPIRED!\nRenew: /buy", reply_markup=main_menu)
        return
    
    banner = get_passkey_banner()
    await update.message.reply_text(banner, reply_markup=ReplyKeyboardRemove())
    
    loading = await update.message.reply_text("⏳ LOADING...\n█░░░░░░░░░ 10%")
    await asyncio.sleep(0.3)
    await loading.edit_text("⏳ LOADING...\n█████░░░░░ 50%")
    await asyncio.sleep(0.3)
    await loading.edit_text("⏳ LOADING...\n██████████ 100% ✅")
    await asyncio.sleep(0.3)
    await loading.delete()
    
    await update.message.reply_text("𝗬𝗢𝗨𝗥 𝗞𝗘𝗬 🔑👇👇")
    await asyncio.sleep(0.3)
    await update.message.reply_text(f"{vip[uid]['key']}")
    await asyncio.sleep(0.3)
    await update.message.reply_text("> 𝗧𝗬𝗣𝗘 𝗬𝗢𝗨𝗥 𝗞𝗘𝗬:", reply_markup=ReplyKeyboardRemove())
    context.user_data['waiting_passkey'] = True

async def verify_passkey(update, context):
    uid = str(update.effective_user.id)
    entered = update.message.text.strip()
    
    if not context.user_data.get('waiting_passkey'):
        return
    
    if uid not in vip:
        await update.message.reply_text("❌ No VIP!", reply_markup=main_menu)
        context.user_data['waiting_passkey'] = False
        return
    
    exp = datetime.fromisoformat(vip[uid]['expiry'])
    if exp <= datetime.now():
        await update.message.reply_text("❌ Expired!", reply_markup=main_menu)
        context.user_data['waiting_passkey'] = False
        return
    
    if entered == vip[uid]['key']:
        context.user_data['verified'] = True
        await hacker_loading(update, context)
        banner = get_verified_banner()
        await update.message.reply_text(banner, reply_markup=start_button_menu)
        context.user_data['waiting_start'] = True
    else:
        await update.message.reply_text(f"❌ INVALID!\n🔑 Your Key: {vip[uid]['key']}", reply_markup=ReplyKeyboardRemove())
    
    context.user_data['waiting_passkey'] = False

async def hacker_loading(update, context):
    msg = await update.message.reply_text("┌─[ 🔓 𝗗𝗘𝗖𝗥𝗬𝗣𝗧 ]\n│\n├─[ █░░░░░░░░░ 10% ]\n└─[ 𝗣𝗥𝗢𝗖𝗘𝗦𝗦𝗜𝗡𝗚 ]")
    await asyncio.sleep(0.2)
    await msg.edit_text("┌─[ 🔓 𝗗𝗘𝗖𝗥𝗬𝗣𝗧 ]\n│\n├─[ ████░░░░░░ 40% ]\n└─[ 𝗩𝗘𝗥𝗜𝗙𝗬𝗜𝗡𝗚 ]")
    await asyncio.sleep(0.2)
    await msg.edit_text("┌─[ 🔓 𝗗𝗘𝗖𝗥𝗬𝗣𝗧 ]\n│\n├─[ ████████░░ 80% ]\n└─[ 𝗔𝗖𝗖𝗘𝗦𝗦 𝗚𝗥𝗔𝗡𝗧𝗘𝗗 ]")
    await asyncio.sleep(0.2)
    await msg.edit_text("┌─[ 🔓 𝗗𝗘𝗖𝗥𝗬𝗣𝗧 ]\n│\n├─[ ██████████ 100% ✅ ]\n└─[ 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘 ]")
    await asyncio.sleep(0.2)
    await msg.delete()

async def start_game(update, context):
    if not context.user_data.get('waiting_start'):
        return
    if update.message.text == "🚀 START 🚀":
        context.user_data['waiting_start'] = False
        await update.message.reply_text("✅ VERIFIED!\n📌 SELECT TIME:", reply_markup=timer_menu)
        context.user_data['waiting_timer'] = True
        
        
        
        
        # ==========================================
# 🌌 AURA BOT v7.0 - PART 6
# ==========================================

async def timer_select(update, context):
    text = update.message.text
    uid = str(update.effective_user.id)
    
    if not context.user_data.get('waiting_timer'):
        return
    
    timer_map = {"⏱ 30s": "30", "⏱ 1m": "60", "⏱ 2m": "120", "⏱ 5m": "300"}
    if text in timer_map:
        users[uid]['selected_time'] = timer_map[text]
        save("users.json", users)
        context.user_data['waiting_timer'] = False
        banner = get_period_banner()
        await update.message.reply_text(f"✅ Timer: {text}\n\n{banner}", reply_markup=ReplyKeyboardRemove())
        context.user_data['waiting_period'] = True
    elif text == "🏠 HOME":
        context.user_data.clear()
        await start_button(update, context)

async def set_period(update, context):
    uid = str(update.effective_user.id)
    period = update.message.text.strip()
    
    if not context.user_data.get('waiting_period'):
        return
    
    if len(period) == 4 and period.isdigit():
        users[uid]['last_period'] = period
        save("users.json", users)
        banner = get_result_banner()
        await update.message.reply_text(f"✅ Period: {period}\n\n{banner}", reply_markup=result_number_menu)
        context.user_data['waiting_period'] = False
        context.user_data['waiting_result_number'] = True
    else:
        await update.message.reply_text("❌ Enter 4 digits!", reply_markup=ReplyKeyboardRemove())
        
        
        
        
        
        # ==========================================
# 🌌 AURA BOT v7.0 - PART 7
# ==========================================

async def handle_result_number(update, context):
    uid = str(update.effective_user.id)
    text = update.message.text
    
    if not context.user_data.get('waiting_result_number'):
        return
    
    if text in ["⏱ 30s", "⏱ 1m", "⏱ 2m", "⏱ 5m"]:
        await timer_select(update, context)
        return
    if text == "⏱ TIMER":
        await update.message.reply_text("⏱ SELECT TIME", reply_markup=timer_menu)
        return
    if text == "🏠 HOME":
        context.user_data.clear()
        await start_button(update, context)
        return
    
    number_map = {"0️⃣":0,"1️⃣":1,"2️⃣":2,"3️⃣":3,"4️⃣":4,"5️⃣":5,"6️⃣":6,"7️⃣":7,"8️⃣":8,"9️⃣":9}
    
    if text in number_map:
        user_num = number_map[text]
        result_trend = "BIG" if user_num >= 5 else "SMALL"
        result_category = "🔴 BIG" if user_num >= 5 else "🔵 SMALL"
        period = users[uid].get('last_period', '0000')
        
        save_result(uid, period, user_num, result_trend)
        
        await update.message.reply_text(f"✅ Result Saved!\n📊 {user_num}\n📈 {result_category}\n🔢 {period}", reply_markup=ReplyKeyboardRemove())
        context.user_data['waiting_result_number'] = False
        await process_analysis(update, context, uid, None, period)

async def process_analysis(update, context, uid, periods=None, last_period=None):
    msg = await update.message.reply_text("⏳ PROCESSING...\n█░░░░░░░░░ 10%")
    await asyncio.sleep(0.2)
    await msg.edit_text("⏳ PROCESSING...\n█████░░░░░ 50%")
    await asyncio.sleep(0.2)
    await msg.edit_text("⏳ PROCESSING...\n██████████ 100% ✅")
    await asyncio.sleep(0.2)
    await msg.delete()
    
    num1 = random.randint(0, 9)
    num2 = random.randint(0, 9)
    
    if num1 >= 5 and num2 >= 5:
        trend = "BIG"; category = "🔴 BIG"
    elif num1 <= 4 and num2 <= 4:
        trend = "SMALL"; category = "🔵 SMALL"
    else:
        trend = random.choice(["BIG", "SMALL"])
        category = "🔴 BIG" if trend == "BIG" else "🔵 SMALL"
    
    if last_period:
        current_period = str(int(last_period) + 1).zfill(4)
    else:
        current_period = ''.join(random.choices(string.digits, k=4))
    
    users[uid]['last_period'] = current_period
    save("users.json", users)
    
    context.user_data['last_analysis'] = {"trend": trend, "num1": num1, "num2": num2, "period": current_period}
    
    banner = get_analysis_banner(current_period, category, num1, num2)
    await update.message.reply_text(banner, reply_markup=result_keyboard)
    context.user_data['waiting_result'] = True
    
    
    
    
    
    
    # ==========================================
# 🌌 AURA BOT v7.0 - PART 8
# ==========================================

async def handle_result(update, context):
    uid = str(update.effective_user.id)
    text = update.message.text
    
    if not context.user_data.get('waiting_result'):
        return
    
    last = context.user_data.get('last_analysis', {})
    period = last.get('period', '0000')
    
    if text in ["⏱ 30s", "⏱ 1m", "⏱ 2m", "⏱ 5m"]:
        await timer_select(update, context)
        return
    if text == "⏱ TIMER":
        await update.message.reply_text("⏱ SELECT TIME", reply_markup=timer_menu)
        return
    
    if text in ["🔴 BIG", "🔵 SMALL"]:
        user_choice = "BIG" if text == "🔴 BIG" else "SMALL"
        win = user_choice == last.get('trend')
        
        if 'win_count' not in users[uid]:
            users[uid]['win_count'] = 0
            users[uid]['loss_count'] = 0
            users[uid]['level'] = 0
        
        if win:
            users[uid]['win_count'] += 1
            users[uid]['level'] = 0
            emoji = get_emoji()
            result_text = f"{emoji} WIN! {emoji}"
        else:
            users[uid]['loss_count'] += 1
            users[uid]['level'] += 1
            emoji = get_loss_emoji()
            result_text = f"{emoji} LOSS! {emoji}"
        
        save("users.json", users)
        
        next_num1 = random.randint(5, 9) if user_choice == "BIG" else random.randint(0, 4)
        next_num2 = random.randint(5, 9) if user_choice == "BIG" else random.randint(0, 4)
        next_trend = "BIG" if next_num1 >= 5 and next_num2 >= 5 else "SMALL"
        next_category = "🔴 BIG" if next_trend == "BIG" else "🔵 SMALL"
        next_period = str(int(period) + 1).zfill(4)
        
        banner = get_stats_banner(users[uid]['win_count'], users[uid]['loss_count'], users[uid]['level'], next_period, next_category, next_num1, next_num2)
        await update.message.reply_text(f"{result_text}\n{banner}", reply_markup=result_keyboard)
        context.user_data['last_analysis'] = {"trend": next_trend, "num1": next_num1, "num2": next_num2, "period": next_period}
        return
    
    if text in ["0️⃣","1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]:
        user_num = int(text[0])
        result_trend = "BIG" if user_num >= 5 else "SMALL"
        win = result_trend == last.get('trend')
        
        if 'win_count' not in users[uid]:
            users[uid]['win_count'] = 0
            users[uid]['loss_count'] = 0
            users[uid]['level'] = 0
        
        if win:
            users[uid]['win_count'] += 1
            users[uid]['level'] = 0
            emoji = get_emoji()
            result_text = f"{emoji} WIN! {emoji}"
        else:
            users[uid]['loss_count'] += 1
            users[uid]['level'] += 1
            emoji = get_loss_emoji()
            result_text = f"{emoji} LOSS! {emoji}"
        
        save("users.json", users)
        
        next_num1 = random.randint(5, 9) if result_trend == "BIG" else random.randint(0, 4)
        next_num2 = random.randint(5, 9) if result_trend == "BIG" else random.randint(0, 4)
        next_trend = "BIG" if next_num1 >= 5 and next_num2 >= 5 else "SMALL"
        next_category = "🔴 BIG" if next_trend == "BIG" else "🔵 SMALL"
        next_period = str(int(period) + 1).zfill(4)
        
        banner = get_stats_banner(users[uid]['win_count'], users[uid]['loss_count'], users[uid]['level'], next_period, next_category, next_num1, next_num2)
        await update.message.reply_text(f"{result_text}\n{banner}", reply_markup=result_keyboard)
        context.user_data['last_analysis'] = {"trend": next_trend, "num1": next_num1, "num2": next_num2, "period": next_period}
        return
    
    if text in ["🏠 HOME", "🔙 BACK"]:
        context.user_data.clear()
        await start_button(update, context)
        return
    
    await update.message.reply_text("❓ Use buttons!", reply_markup=result_keyboard)
   
   
   
   
   # ==========================================
# 🌌 AURA BOT v7.0 - PART 9
# ==========================================

async def profile(update, context):
    uid = str(update.effective_user.id)
    user = users.get(uid, {})
    
    is_vip = False
    is_verified = context.user_data.get('verified', False)
    exp_text = "No Membership"
    key_text = "N/A"
    
    if uid in vip:
        exp = datetime.fromisoformat(vip[uid]['expiry'])
        if exp > datetime.now():
            is_vip = True
            exp_text = exp.strftime('%Y-%m-%d %H:%M')
            key_text = vip[uid]['key']
    
    banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
    
    await update.message.reply_text(f"""{banner}\n┌─[ 📊 𝗣𝗥𝗢𝗙𝗜𝗟𝗘 ]\n│\n├─ 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣\n│ ├─ 𝗦𝗧𝗔𝗧𝗨𝗦 :: {'🟢 ACTIVE' if is_vip else '🔴 INACTIVE'}\n│ ├─ 𝗘𝗫𝗣𝗜𝗥𝗬 :: {exp_text}\n│ └─ 𝗣𝗔𝗦𝗦𝗞𝗘𝗬 :: {key_text}\n│\n└─[ 𝗖/𝗧://𝗣𝗥𝗢𝗙𝗜𝗟𝗘 ]""", reply_markup=profile_menu)

async def start_analysis(update, context):
    uid = str(update.effective_user.id)
    if uid not in vip:
        await update.message.reply_text("❌ No VIP!", reply_markup=main_menu)
        return
    exp = datetime.fromisoformat(vip[uid]['expiry'])
    if exp <= datetime.now():
        await update.message.reply_text("❌ Expired!", reply_markup=main_menu)
        return
    if not context.user_data.get('verified'):
        await update.message.reply_text("🔑 Verify first!", reply_markup=main_menu)
        return
    await update.message.reply_text("📊 ANALYSIS STARTED!\n[1] Scanning...\n[2] Processing...\n[3] Complete!", reply_markup=profile_menu)

async def support(update, context):
    await update.message.reply_text("📞 SUPPORT\nContact: @BDGmin 24 hours", reply_markup=main_menu)

async def home(update, context):
    context.user_data.clear()
    await start_button(update, context)
    
    
    
    
    # ==========================================
# 🌌 AURA BOT v7.0 - PART 10
# ==========================================

async def stats(update, context):
    if int(update.effective_user.id) not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    
    pending = len([p for p in pay.values() if p['status'] == 'pending'])
    active_vip = len([v for v in vip.values() if datetime.fromisoformat(v['expiry']) > datetime.now()])
    
    await update.message.reply_text(f"""📊 STATS\n━━━━━━━━━━━━━━━━━━━━━━\n👥 Users: {len(users)}\n⭐ Active VIP: {active_vip}\n💰 Total VIP: {len(vip)}\n⏳ Pending: {pending}\n━━━━━━━━━━━━━━━━━━━━━━""")

async def payments_list(update, context):
    if int(update.effective_user.id) not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    
    pending = [p for p in pay.values() if p['status'] == 'pending']
    if not pending:
        await update.message.reply_text("📭 No pending payments")
        return
    
    msg = "📋 PENDING PAYMENTS:\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for i, p in enumerate(pending[:10], 1):
        msg += f"{i}. {p['id']}\n   👤 @{p['name']}\n   🕐 {p['time'][:16]}\n\n"
    
    await update.message.reply_text(msg)

async def broadcast(update, context):
    if int(update.effective_user.id) not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("📢 /broadcast Your message")
        return
    
    count = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, f"📢 {msg}")
            count += 1
        except:
            pass
    
    await update.message.reply_text(f"✅ Sent to {count} users")

async def payment_status(update, context):
    if int(update.effective_user.id) not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    
    pending = [p for p in pay.values() if p['status'] == 'pending']
    approved = [p for p in pay.values() if p['status'] == 'approved']
    rejected = [p for p in pay.values() if p['status'] == 'rejected']
    
    msg = f"""┌─[ 💳 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗧𝗔𝗧𝗨𝗦 ]\n│\n├─[ 📊 𝗦𝗨𝗠𝗠𝗔𝗥𝗬 ]\n│ ├─ ⏳ 𝗣𝗘𝗡𝗗𝗜𝗡𝗚  :: {len(pending)}\n│ ├─ ✅ 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 :: {len(approved)}\n│ └─ ❌ 𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗 :: {len(rejected)}\n│\n├─[ 📋 𝗣𝗘𝗡𝗗𝗜𝗡𝗚 ]"""
    if pending:
        for p in pending[:5]:
            msg += f"\n│ 👤 @{p['name']}\n│ 🕐 {p['time'][:16]}"
    else:
        msg += "\n│ 📭 No pending"
    msg += "\n└─[ 🔐 𝗖/𝗧://𝗦𝗧𝗔𝗧𝗨𝗦 ]"
    await update.message.reply_text(msg)
    
    
    
    
    # ==========================================
# 🌌 AURA BOT v7.0 - PART 11
# ==========================================

async def handle_buttons(update, context):
    text = update.message.text
    uid = str(update.effective_user.id)
    
    if context.user_data.get('waiting_passkey'):
        await verify_passkey(update, context)
        return
    if context.user_data.get('waiting_start'):
        await start_game(update, context)
        return
    if context.user_data.get('waiting_timer'):
        await timer_select(update, context)
        return
    if context.user_data.get('waiting_period'):
        await set_period(update, context)
        return
    if context.user_data.get('waiting_result_number'):
        await handle_result_number(update, context)
        return
    if context.user_data.get('waiting_result'):
        await handle_result(update, context)
        return
    if context.user_data.get('waiting_cancel'):
        await confirm_cancel(update, context)
        return
    
    if text == "🚀 START":
        await start_button(update, context)
    elif text in ["💳 MEMBERSHIP", "💳 Buy Membership"]:
        await buy_membership(update, context)
    elif text == "❌ CANCEL VIP":
        await cancel_vip(update, context)
    elif text in ["▶️ PLAY", "▶️ Play"]:
        await play(update, context)
    elif text in ["👤 PROFILE", "👤 Profile"]:
        await profile(update, context)
    elif text in ["📞 SUPPORT", "📞 Support"]:
        await support(update, context)
    elif text in ["📊 STATS", "📊 Stats"]:
        await stats(update, context)
    elif text in ["💰 PAYMENTS", "💰 Payments"]:
        await payment_status(update, context)
    elif text in ["📢 BROADCAST", "📢 Broadcast"]:
        await update.message.reply_text("📢 /broadcast Your message")
    elif text == "⏱ TIMER":
        await update.message.reply_text("⏱ SELECT TIME", reply_markup=timer_menu)
    elif text in ["⏱ 30s", "⏱ 1m", "⏱ 2m", "⏱ 5m"]:
        await timer_select(update, context)
    elif text == "▶️ START ANALYSIS":
        await start_analysis(update, context)
    elif text in ["🏠 HOME", "🔙 BACK"]:
        context.user_data.clear()
        await start_button(update, context)
    else:
        await update.message.reply_text("❓ Use buttons!", reply_markup=main_menu)
        
        
        
        
        # ==========================================
# 🌌 AURA BOT v7.0 - PART 12
# ==========================================

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy_membership))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("payments", payment_status))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("play", play))
    
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    
    print("=" * 50)
    print("🌟 AURA BOT v7.0 STARTED!")
    print("=" * 50)
    print("✅ Bot is running!")
    print(f"📌 Admins: {ADMIN_IDS}")
    
    qr = find_qr()
    if qr:
        print(f"✅ QR: {qr}")
    else:
        print("❌ QR Not Found!")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
    
    
    
    