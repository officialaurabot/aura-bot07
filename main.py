# ==========================================
# 🌌 AURA BOT v7.0 - FULLY FIXED
# ==========================================

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import json, os, random, string, asyncio, re, sqlite3
from datetime import datetime, timedelta
import traceback

# ==========================================
# HEALTH CHECK - Simple HTTP Server (No Flask)
# ==========================================
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        pass  # Silence logs

def run_health_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

# ==========================================
# SETUP
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN environment variable is not set!")

SUPER_ADMIN_IDS = [5901835425]
ADMIN_IDS = [5901835425, 6467765686, 7295714098]

BROADCAST_HISTORY = []
FEEDBACK_LIST = []

# ==========================================
# GLOBAL RESULT STORAGE
# ==========================================
GLOBAL_PERIOD_RESULTS = {}
USER_PRESS_TRACKER = {}

# ==========================================
# BIG/SMALL ANALYSIS ALGORITHM
# ==========================================

def get_size(number):
    try:
        number = int(number)
    except (ValueError, TypeError):
        return None
    if 0 <= number <= 4:
        return "SMALL"
    elif 5 <= number <= 9:
        return "BIG"
    return None

HISTORICAL_RESULTS = [
    5, 9, 6, 2, 4, 6, 0, 2, 0, 2,
    1, 3, 7, 3, 3, 8, 2, 7, 1, 1,
    4, 0, 2, 2, 7, 0, 9, 2, 0, 1,
    1, 7, 4, 5, 2, 3, 3, 6, 8, 5,
    3, 5, 0, 6, 9, 0, 1, 7, 6, 2
]

CLASSIFIED_RESULTS = [
    {"number": num, "size": get_size(num)}
    for num in HISTORICAL_RESULTS
]

def get_statistics():
    big_count = sum(1 for r in CLASSIFIED_RESULTS if r["size"] == "BIG")
    small_count = sum(1 for r in CLASSIFIED_RESULTS if r["size"] == "SMALL")
    return {"BIG": big_count, "SMALL": small_count}

def predict_next():
    last_10 = CLASSIFIED_RESULTS[-10:]
    big = sum(1 for r in last_10 if r["size"] == "BIG")
    small = sum(1 for r in last_10 if r["size"] == "SMALL")
    if big > small:
        return {"prediction": "BIG", "confidence": f"{big*10}%"}
    elif small > big:
        return {"prediction": "SMALL", "confidence": f"{small*10}%"}
    else:
        return {"prediction": "BALANCED", "confidence": "50%"}

def add_result_to_algorithm(number):
    try:
        num = int(number)
        if 0 <= num <= 9:
            HISTORICAL_RESULTS.append(num)
            CLASSIFIED_RESULTS.append({"number": num, "size": get_size(num)})
            if len(HISTORICAL_RESULTS) > 100:
                HISTORICAL_RESULTS.pop(0)
                CLASSIFIED_RESULTS.pop(0)
            return True
    except:
        pass
    return False

def get_analysis_report():
    stats = get_statistics()
    total = len(HISTORICAL_RESULTS)
    report = f"""
📊 BIG/SMALL ANALYSIS REPORT
━━━━━━━━━━━━━━━━━━━━━━
📈 Total Results: {total}
🔴 BIG: {stats['BIG']} ({stats['BIG']/total*100:.1f}%)
🔵 SMALL: {stats['SMALL']} ({stats['SMALL']/total*100:.1f}%)
━━━━━━━━━━━━━━━━━━━━━━
📊 Last 10 Results:
"""
    for i, r in enumerate(CLASSIFIED_RESULTS[-10:], 1):
        emoji = "🟥" if r["size"] == "BIG" else "🟦"
        report += f"{i}. {r['number']} → {emoji} {r['size']}\n"
    pred = predict_next()
    report += f"""
━━━━━━━━━━━━━━━━━━━━━━
🔮 Next Prediction: {pred['prediction']}
🎯 Confidence: {pred['confidence']}
━━━━━━━━━━━━━━━━━━━━━━
"""
    return report

# ==========================================
# FUNCTIONS
# ==========================================
def get_opposite_result(user_id, user_choice):
    uid = str(user_id)
    if uid not in USER_PRESS_TRACKER:
        USER_PRESS_TRACKER[uid] = {"BIG": 0, "SMALL": 0}
    current_count = USER_PRESS_TRACKER[uid].get(user_choice, 0)
    if current_count >= 3:
        USER_PRESS_TRACKER[uid] = {"BIG": 0, "SMALL": 0}
        opposite = "SMALL" if user_choice == "BIG" else "BIG"
        logger.info(f"⚠️ 3 press rule triggered! {user_choice} → {opposite} for user {uid}")
        return opposite
    USER_PRESS_TRACKER[uid][user_choice] = current_count + 1
    return user_choice

def get_global_result_for_period(period, generate_if_missing=True):
    if period in GLOBAL_PERIOD_RESULTS:
        logger.info(f"✅ PERIOD {period} ALREADY EXISTS! Returning existing result")
        return GLOBAL_PERIOD_RESULTS[period]
    if not generate_if_missing:
        return None
    num1 = random.randint(0, 9)
    num2 = random.randint(0, 9)
    if num1 >= 5 and num2 >= 5:
        trend = "BIG"
        category = "🔴 BIG"
    elif num1 <= 4 and num2 <= 4:
        trend = "SMALL"
        category = "🔵 SMALL"
    else:
        trend = random.choice(["BIG", "SMALL"])
        category = "🔴 BIG" if trend == "BIG" else "🔵 SMALL"
    result = {"num1": num1, "num2": num2, "trend": trend, "category": category}
    GLOBAL_PERIOD_RESULTS[period] = result
    logger.info(f"✅ Created NEW GLOBAL result for period {period}: {num1}, {num2} ({trend})")
    return result

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
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO results (user_id, period, number, size, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (user_id, period, number, size, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database error: {e}")

def get_user_history(user_id, limit=10):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT number, size FROM results WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return rows
    except:
        return []

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

# ⭐ RANK SYSTEM
def get_rank(level):
    if level >= 20:
        return "👑 LEGEND", "👑"
    elif level >= 10:
        return "🔥 PRO", "🔥"
    elif level >= 5:
        return "📈 INTERMEDIATE", "📈"
    else:
        return "🌱 BEGINNER", "🌱"

def get_achievements(win_count, loss_count, level):
    achievements = []
    if win_count >= 10:
        achievements.append("🏆 10 WINS")
    if win_count >= 25:
        achievements.append("👑 25 WINS")
    if win_count >= 50:
        achievements.append("💎 50 WINS")
    if win_count > loss_count and win_count >= 5:
        achievements.append("📊 POSITIVE RATIO")
    if not achievements:
        achievements.append("🌱 KEEP PLAYING")
    return achievements

async def show_loading(update, context, steps=None):
    if steps is None:
        steps = [
            "🔍 ANALYZING...\n├─ █░░░░░░░░░ 10%\n└─ Scanning patterns...",
            "🔍 ANALYZING...\n├─ ████░░░░░░ 40%\n└─ Processing data...",
            "🔍 ANALYZING...\n├─ ████████░░ 80%\n└─ Generating results...",
            "🔍 ANALYZING...\n├─ ██████████ 100% ✅\n└─ Complete!"
        ]
    
    msg = await update.message.reply_text(steps[0])
    for i in range(1, len(steps)):
        await asyncio.sleep(0.3)
        await msg.edit_text(steps[i])
    await asyncio.sleep(0.2)
    await msg.delete()

# ==========================================
# KEYBOARDS
# ==========================================
start_btn = ReplyKeyboardMarkup([["🚀 START"]], resize_keyboard=True)

main_menu = ReplyKeyboardMarkup([
    ["💳 MEMBERSHIP", "▶️ PLAY"],
    ["👤 PROFILE", "📞 SUPPORT"],
    ["📝 FEEDBACK", "🏠 HOME"]
], resize_keyboard=True)

admin_menu = ReplyKeyboardMarkup([
    ["📊 STATS", "💰 PAYMENTS"],
    ["📢 BROADCAST", "📅 PAYMENT HISTORY"],
    ["🔙 BACK"]
], resize_keyboard=True)

super_admin_menu = ReplyKeyboardMarkup([
    ["📊 STATS", "💰 PAYMENTS"],
    ["📢 BROADCAST", "📅 PAYMENT HISTORY"],
    ["📋 APPROVAL LOG", "👑 ADMIN ACTIVITY"],
    ["📝 FEEDBACK LOG", "🔙 BACK"]
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
profile_menu = ReplyKeyboardMarkup([
    ["▶️ START ANALYSIS"],
    ["🏠 HOME"]
], resize_keyboard=True)
membership_menu = ReplyKeyboardMarkup([["👑 BUY ₹299"], ["❌ CANCEL VIP"], ["🔙 BACK"]], resize_keyboard=True)

# ==========================================
# START FUNCTION
# ==========================================
async def start(update, context):
    try:
        uid = str(update.effective_user.id)
        if uid not in users:
            users[uid] = {"id": uid, "name": update.effective_user.username or "Unknown", "joined": str(datetime.now()), "win_count": 0, "loss_count": 0, "level": 0}
            save("users.json", users)
        await send_typing(context, update.effective_chat.id)
        await asyncio.sleep(0.3)
        await update.message.reply_text("🌟 Welcome to AURA BOT!\n\nClick START to begin! 🚀", reply_markup=start_btn)
    except Exception as e:
        logger.error(f"Start error: {e}")

async def start_button(update, context):
    try:
        uid = str(update.effective_user.id)
        is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
        is_verified = context.user_data.get('verified', False)
        await send_typing(context, update.effective_chat.id)
        await asyncio.sleep(0.3)
        banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
        
        user_id_int = int(uid)
        if user_id_int in SUPER_ADMIN_IDS:
            kb = super_admin_menu
        elif user_id_int in ADMIN_IDS:
            kb = admin_menu
        else:
            kb = main_menu
        
        await update.message.reply_text(banner, reply_markup=kb)
    except Exception as e:
        logger.error(f"Start button error: {e}")

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

# ⭐ STATS BANNER
def get_stats_banner(win, loss, level, period, category, num1, num2, player_result=None, next_prediction=None):
    rank, rank_emoji = get_rank(level)
    banner = f"""
𝟬𝟴 — 𝗦𝗧𝗔𝗧𝗦
┌─[ 📈 𝗖/𝗧://𝗦𝗧𝗔𝗧𝗦 ]
│
├─[ 𝗦𝗘𝗦𝗦𝗜𝗢𝗡 ]
│ ├─ 🏆 𝗪𝗜𝗡   :: {win:02d}
│ ├─ ❌ 𝗟𝗢𝗦𝗦  :: {loss:02d}
│ └─ 📊 𝗟𝗘𝗩𝗘𝗟 :: {level:02d} {rank_emoji}
│
├─[ 𝗥𝗔𝗡𝗞 ]
│ └─ 🎖️ {rank}
│
├─[ 𝗡𝗘𝗫𝗧 ]
│ ├─ 🔢 𝗣𝗘𝗥𝗜𝗢𝗗   :: {period}
│ ├─ 📈 𝗖𝗔𝗧𝗘𝗚𝗢𝗥𝗬 :: {category}
│ └─ 📊 𝗡𝗨𝗠𝗕𝗘𝗥   :: {num1} , {num2}
│
├─[ 📤 𝗦𝗘𝗡𝗗 𝗡𝗘𝗫𝗧 𝗡𝗨𝗠𝗕𝗘𝗥 ]
│ └─ 🎯 𝗣𝗟𝗔𝗬𝗘𝗥 𝗥𝗘𝗦𝗨𝗟𝗧 :: {player_result if player_result else "⏳ WAITING"}
│
└─[ 𝗖/𝗧://𝗟𝗜𝗩𝗘 ]
"""
    return banner

# ==========================================
# BUY MEMBERSHIP
# ==========================================
async def buy_membership(update, context):
    try:
        uid = str(update.effective_user.id)
        if uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now():
            banner = get_vip_banner(update.effective_user.username, vip[uid]['expiry'], vip[uid]['key'])
            await update.message.reply_text(f"""{banner}\n┌─[ 🔐 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦 ]\n│\n├─[ 👑 𝗠𝗔𝗡𝗔𝗚𝗘 𝗬𝗢𝗨𝗥 𝗩𝗜𝗣 ]\n│\n│ ├─ 👑 𝗕𝗨𝗬 𝗡𝗢𝗪 :: ₹299\n│ │     └─ 𝗘𝗫𝗧𝗘𝗡𝗗 𝗩𝗜𝗣\n│ │\n│ ├─ ❌ 𝗖𝗔𝗡𝗖𝗘𝗟 𝗩𝗜𝗣\n│ │     └─ 𝗖𝗔𝗡𝗖𝗘𝗟 𝗩𝗜𝗣\n│ │\n│ └─ 🔙 𝗕𝗔𝗖𝗞\n│       └─ 𝗚𝗢 𝗕𝗔𝗖𝗞\n│\n└─[ 🔐 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦_𝗚𝗥𝗔𝗡𝗧𝗘𝗗 ]""", reply_markup=membership_menu)
            return
        msg = await update.message.reply_text("⏳ Loading membership...")
        await asyncio.sleep(0.5)
        await msg.delete()
        qr_path = find_qr()
        if qr_path:
            try:
                with open(qr_path, 'rb') as f:
                    await update.message.reply_photo(InputFile(f), caption="""💳 VIP MEMBERSHIP\n━━━━━━━━━━━━━━━━━━━━━━\n👑 VIP Plan: ₹299 / 3 Days\n✅ Full Access\n✅ Premium Content\n━━━━━━━━━━━━━━━━━━━━━━\nPay via UPI: aura@pay""")
            except:
                await update.message.reply_text("""💳 VIP MEMBERSHIP\n━━━━━━━━━━━━━━━━━━━━━━\n👑 VIP Plan: ₹299 / 3 Days\n✅ Full Access\n✅ Premium Content\n━━━━━━━━━━━━━━━━━━━━━━\nPay via UPI: aura@pay""")
        else:
            await update.message.reply_text("""💳 VIP MEMBERSHIP\n━━━━━━━━━━━━━━━━━━━━━━\n👑 VIP Plan: ₹299 / 3 Days\n✅ Full Access\n✅ Premium Content\n━━━━━━━━━━━━━━━━━━━━━━\nPay via UPI: aura@pay""")
        await asyncio.sleep(0.5)
        await update.message.reply_text("👆 PAY AND SEND SCREENSHOT 👆", reply_markup=ReplyKeyboardRemove())
        context.user_data['waiting_payment'] = True
    except Exception as e:
        logger.error(f"Buy membership error: {e}")
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=main_menu)

async def cancel_vip(update, context):
    try:
        uid = str(update.effective_user.id)
        if uid not in vip:
            await update.message.reply_text("❌ No Active VIP!", reply_markup=main_menu)
            return
        exp = datetime.fromisoformat(vip[uid]['expiry'])
        if exp <= datetime.now():
            await update.message.reply_text("❌ Already Expired!", reply_markup=main_menu)
            return
        await update.message.reply_text(f"""⚠️ CANCEL VIP\n━━━━━━━━━━━━━━━━━━━━━━\n🔑 {vip[uid]['key']}\n📅 {exp.strftime('%Y-%m-%d %H:%M')}\n━━━━━━━━━━━━━━━━━━━━━━""", reply_markup=ReplyKeyboardMarkup([["✅ YES, CANCEL VIP"], ["❌ NO, GO BACK"]], resize_keyboard=True))
        context.user_data['waiting_cancel'] = True
    except Exception as e:
        logger.error(f"Cancel VIP error: {e}")

async def confirm_cancel(update, context):
    try:
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
    except Exception as e:
        logger.error(f"Confirm cancel error: {e}")

async def upload(update, context):
    try:
        uid = str(update.effective_user.id)
        if 'plan' not in context.user_data:
            await update.message.reply_text("❌ Use /buy first!", reply_markup=main_menu)
            return
        await update.message.reply_text("📤 Send payment screenshot now:")
        context.user_data['waiting'] = True
    except Exception as e:
        logger.error(f"Upload error: {e}")

async def handle_photo(update, context):
    try:
        uid = str(update.effective_user.id)
        if not context.user_data.get('waiting_payment') and not context.user_data.get('waiting'):
            await update.message.reply_text("❌ Use MEMBERSHIP first!", reply_markup=main_menu)
            return
        
        steps = [
            "📤 UPLOADING...\n├─ █░░░░░░░░░ 10%\n└─ Connecting to server...",
            "📤 UPLOADING...\n├─ ████░░░░░░ 40%\n└─ Processing image...",
            "📤 UPLOADING...\n├─ ████████░░ 80%\n└─ Verifying payment...",
            "📤 UPLOADING...\n├─ ██████████ 100% ✅\n└─ Upload complete!"
        ]
        msg = await update.message.reply_text(steps[0])
        for i in range(1, len(steps)):
            await asyncio.sleep(0.2)
            await msg.edit_text(steps[i])
        await asyncio.sleep(0.2)
        await msg.delete()
        
        photo = update.message.photo[-1].file_id
        req = f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        user_name = update.effective_user.username or "Unknown"
        pay[req] = {"id": req, "uid": uid, "name": user_name, "photo": photo, "time": str(datetime.now()), "status": "pending"}
        save("pay.json", pay)
        
        admin_sent = False
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo,
                    caption=f"""🔔 NEW PAYMENT REQUEST!\n━━━━━━━━━━━━━━━━━━━━━━\n📋 ID: {req}\n👤 User: @{user_name}\n🆔 UID: {uid}\n💰 Amount: ₹299\n🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}""",
                    reply_markup=get_admin_buttons(req)
                )
                admin_sent = True
            except Exception as e:
                logger.error(f"Error sending to admin: {e}")
        
        await update.message.reply_text(f"""📤 SCREENSHOT SENT!\n━━━━━━━━━━━━━━━━━━━━━━\n📋 ID: {req}\n⏳ Status: PENDING\n━━━━━━━━━━━━━━━━━━━━━━\n⏳ Waiting for admin approval...""", reply_markup=main_menu)
        context.user_data['waiting_payment'] = False
        context.user_data['waiting'] = False
    except Exception as e:
        logger.error(f"Handle photo error: {e}")
        await update.message.reply_text("❌ Error uploading! Please try again.", reply_markup=main_menu)

async def callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        admin_id = int(query.from_user.id)
        if admin_id not in ADMIN_IDS:
            await context.bot.send_message(admin_id, "❌ You are not admin!")
            return
        
        if data.startswith("broadcast_"):
            await broadcast_callback(update, context)
            return
        
        if data.startswith("app_"):
            req_id = data.replace("app_", "")
            await approve_payment(query, context, req_id)
        elif data.startswith("rej_"):
            req_id = data.replace("rej_", "")
            await reject_payment(query, context, req_id)
    except Exception as e:
        logger.error(f"Callback error: {e}")

# ==========================================
# APPROVE PAYMENT
# ==========================================
async def approve_payment(query, context, req_id):
    try:
        if req_id not in pay:
            await context.bot.send_message(query.from_user.id, "❌ Request not found!")
            return
        p = pay[req_id]
        if p['status'] != 'pending':
            await context.bot.send_message(query.from_user.id, "❌ Already processed!")
            return
        
        admin_id = query.from_user.id
        admin_name = query.from_user.username or str(admin_id)
        is_super_admin = admin_id in SUPER_ADMIN_IDS
        
        steps = [
            "⚡ PROCESSING PAYMENT...\n├─ █░░░░░░░░░ 10%\n└─ Verifying details...",
            "⚡ PROCESSING PAYMENT...\n├─ ████░░░░░░ 40%\n└─ Generating passkey...",
            "⚡ PROCESSING PAYMENT...\n├─ ████████░░ 80%\n└─ Activating VIP...",
            "⚡ PROCESSING PAYMENT...\n├─ ██████████ 100% ✅\n└─ Approved!"
        ]
        msg = await query.message.reply_text(steps[0])
        for i in range(1, len(steps)):
            await asyncio.sleep(0.3)
            await msg.edit_text(steps[i])
        await asyncio.sleep(0.2)
        await msg.delete()
        
        key = gen_key()
        uid = p['uid']
        expiry = datetime.now() + timedelta(days=3)
        vip[uid] = {"user_id": uid, "key": key, "expiry": expiry.isoformat()}
        save("vip.json", vip)
        p['status'] = 'approved'
        p['passkey'] = key
        p['approved_by'] = admin_id
        p['approved_by_name'] = admin_name
        p['approved_time'] = datetime.now().isoformat()
        p['is_super_admin'] = is_super_admin
        save("pay.json", pay)
        
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"""✅ VIP ACTIVATED!
━━━━━━━━━━━━━━━━━━━━━━
👑 Plan: VIP 3 Days
⏰ Duration: 72 Hours
🔑 Passkey: {key}
📅 Expiry: {expiry.strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━
▶️ Use /play to start playing""",
                reply_markup=main_menu
            )
            logger.info(f"✅ Passkey sent to user: {uid}")
        except Exception as e:
            logger.error(f"Error sending to user: {e}")
        
        star = '⭐ ' if is_super_admin else ''
        role = 'SUPER ADMIN' if is_super_admin else 'ADMIN'
        
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"""✅ APPROVED!
━━━━━━━━━━━━━━━━━━━━━━
📋 ID: {req_id}
👤 User: @{p['name']}
🔑 Passkey: {key}
👑 Approved By: {star}@{admin_name} ({role})
🕐 Time: {datetime.now().strftime('%I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━━
📸 Screenshot saved in history."""
        )
        
        for other_admin in ADMIN_IDS:
            if other_admin != admin_id:
                try:
                    await context.bot.send_photo(
                        chat_id=other_admin,
                        photo=p['photo'],
                        caption=f"""✅ PAYMENT APPROVED!
━━━━━━━━━━━━━━━━━━━━━━
📋 ID: {req_id}
👤 User: @{p['name']}
👑 Approved By: {star}@{admin_name} ({role})
🕐 Time: {datetime.now().strftime('%I:%M %p')}
📅 Date: {datetime.now().strftime('%Y-%m-%d')}
━━━━━━━━━━━━━━━━━━━━━━
🔑 Passkey: {key}
💰 Amount: ₹299
━━━━━━━━━━━━━━━━━━━━━━
📸 Screenshot saved in history"""
                    )
                except:
                    pass
        
        try:
            await query.message.edit_caption(
                caption=f"""✅ APPROVED!
━━━━━━━━━━━━━━━━━━━━━━
📋 ID: {req_id}
👤 User: @{p['name']}
🔑 Passkey: {key}
👑 Approved By: {star}@{admin_name} ({role})
💰 Amount: ₹299
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━
📸 Screenshot saved in history"""
            )
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Approve payment error: {e}")

# ==========================================
# REJECT PAYMENT
# ==========================================
async def reject_payment(query, context, req_id):
    try:
        if req_id not in pay:
            await context.bot.send_message(query.from_user.id, "❌ Request not found!")
            return
        p = pay[req_id]
        if p['status'] != 'pending':
            await context.bot.send_message(query.from_user.id, "❌ Already processed!")
            return
        
        admin_id = query.from_user.id
        admin_name = query.from_user.username or str(admin_id)
        is_super_admin = admin_id in SUPER_ADMIN_IDS
        
        p['status'] = 'rejected'
        p['rejected_by'] = admin_id
        p['rejected_by_name'] = admin_name
        p['rejected_time'] = datetime.now().isoformat()
        p['is_super_admin'] = is_super_admin
        save("pay.json", pay)
        
        try:
            await context.bot.send_message(
                chat_id=p['uid'],
                text=f"""❌ PAYMENT REJECTED!
━━━━━━━━━━━━━━━━━━━━━━
😔 Payment verification failed!
━━━━━━━━━━━━━━━━━━━━━━
Please upload again: /upload""",
                reply_markup=main_menu
            )
        except Exception as e:
            logger.error(f"Error sending to user: {e}")
        
        star = '⭐ ' if is_super_admin else ''
        role = 'SUPER ADMIN' if is_super_admin else 'ADMIN'
        
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"""❌ REJECTED!
━━━━━━━━━━━━━━━━━━━━━━
📋 ID: {req_id}
👤 User: @{p['name']}
👑 Rejected By: {star}@{admin_name} ({role})
🕐 Time: {datetime.now().strftime('%I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━━
📸 Screenshot saved in history."""
        )
        
        for other_admin in ADMIN_IDS:
            if other_admin != admin_id:
                try:
                    await context.bot.send_photo(
                        chat_id=other_admin,
                        photo=p['photo'],
                        caption=f"""❌ PAYMENT REJECTED!
━━━━━━━━━━━━━━━━━━━━━━
📋 ID: {req_id}
👤 User: @{p['name']}
👑 Rejected By: {star}@{admin_name} ({role})
🕐 Time: {datetime.now().strftime('%I:%M %p')}
📅 Date: {datetime.now().strftime('%Y-%m-%d')}
━━━━━━━━━━━━━━━━━━━━━━
💰 Amount: ₹299
━━━━━━━━━━━━━━━━━━━━━━
📸 Screenshot saved in history"""
                    )
                except:
                    pass
        
        try:
            await query.message.edit_caption(
                caption=f"""❌ REJECTED!
━━━━━━━━━━━━━━━━━━━━━━
📋 ID: {req_id}
👤 User: @{p['name']}
👑 Rejected By: {star}@{admin_name} ({role})
💰 Amount: ₹299
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━
📸 Screenshot saved in history"""
            )
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Reject payment error: {e}")

# ==========================================
# BROADCAST CALLBACK
# ==========================================
async def broadcast_callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if int(query.from_user.id) not in ADMIN_IDS:
            await query.edit_message_text("❌ Admin only!")
            return
        
        if data == "broadcast_new":
            context.user_data['broadcast_mode'] = True
            await query.edit_message_text(
                "📝 *Write Your Message:*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "✏️ Type your message below\n"
                "📤 Then press the **Send** button (➤)\n"
                "🏠 Type 'CANCEL' to cancel",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Broadcast callback error: {e}")
        await query.edit_message_text("❌ Error! Please try again.")

# ==========================================
# BROADCAST
# ==========================================
async def broadcast(update, context):
    try:
        if int(update.effective_user.id) not in ADMIN_IDS:
            await update.message.reply_text("❌ Admin only!")
            return
        
        admin_id = int(update.effective_user.id)
        admin_name = update.effective_user.username or str(admin_id)
        is_super_admin = admin_id in SUPER_ADMIN_IDS
        
        if context.user_data.get('broadcast_mode'):
            msg = update.message.text
            
            count = 0
            loading_msg = await update.message.reply_text("📢 *Broadcasting...*", parse_mode='Markdown')
            
            for uid in users:
                try:
                    await context.bot.send_message(uid, f"📢 {msg}")
                    count += 1
                    await asyncio.sleep(0.05)
                except:
                    pass
            
            await loading_msg.delete()
            context.user_data['broadcast_mode'] = False
            
            broadcast_entry = {
                "admin_id": admin_id,
                "admin_name": admin_name,
                "is_super_admin": is_super_admin,
                "message": msg[:100],
                "count": count,
                "time": datetime.now().isoformat()
            }
            BROADCAST_HISTORY.append(broadcast_entry)
            if len(BROADCAST_HISTORY) > 50:
                BROADCAST_HISTORY.pop(0)
            
            current_time = datetime.now().strftime('%I:%M %p')
            
            success_msg = f"""
✅ *BROADCAST SUCCESSFUL!*
━━━━━━━━━━━━━━━━━━━━━━

📊 *Statistics:*
├─ 👥 Sent to :: {count} users
├─ 📤 Message :: {msg[:50]}{'...' if len(msg) > 50 else ''}
├─ 👑 Admin    :: @{admin_name} {'⭐' if is_super_admin else ''}
└─ 🕐 Time    :: {current_time}

━━━━━━━━━━━━━━━━━━━━━━
📢 Click below to send another broadcast
"""
            inline_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 New Broadcast", callback_data="broadcast_new")]
            ])
            
            await update.message.reply_text(
                success_msg,
                parse_mode='Markdown',
                reply_markup=inline_keyboard
            )
            return
        
        context.user_data['broadcast_mode'] = True
        await update.message.reply_text(
            "📝 *Write Your Message:*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✏️ Type your message below\n"
            "📤 Then press the **Send** button (➤)\n"
            "🏠 Type 'CANCEL' to cancel",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        context.user_data['broadcast_mode'] = False
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=admin_menu)

# ==========================================
# APPROVAL LOG - FIXED
# ==========================================
async def approval_log(update, context):
    try:
        uid = int(update.effective_user.id)
        if uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Only Super Admin can view this!")
            return
        
        # Reload pay data
        global pay
        pay = load("pay.json")
        
        approved_list = []
        rejected_list = []
        
        for req_id, p in pay.items():
            if p.get('status') == 'approved':
                approved_list.append(p)
            elif p.get('status') == 'rejected':
                rejected_list.append(p)
        
        msg = f"""
👑 *SUPER ADMIN - APPROVAL LOG*
━━━━━━━━━━━━━━━━━━━━━━

✅ *APPROVED ({len(approved_list)})*
"""
        if approved_list:
            for p in approved_list[-10:]:
                approved_by = p.get('approved_by_name', 'Unknown')
                approved_by_id = p.get('approved_by', 'N/A')
                is_super = p.get('is_super_admin', False)
                star = '⭐ ' if is_super else ''
                role = 'SUPER ADMIN' if is_super else 'ADMIN'
                time = p.get('approved_time', '')
                if time:
                    time = time[:16]
                msg += f"├─ 📋 {p['id']}\n│  👑 {star}@{approved_by} ({role})\n│  🆔 {approved_by_id}\n│  🕐 {time}\n\n"
        else:
            msg += "├─ No approvals yet\n"
        
        msg += f"""
❌ *REJECTED ({len(rejected_list)})*
"""
        if rejected_list:
            for p in rejected_list[-10:]:
                rejected_by = p.get('rejected_by_name', 'Unknown')
                rejected_by_id = p.get('rejected_by', 'N/A')
                is_super = p.get('is_super_admin', False)
                star = '⭐ ' if is_super else ''
                role = 'SUPER ADMIN' if is_super else 'ADMIN'
                time = p.get('rejected_time', '')
                if time:
                    time = time[:16]
                msg += f"├─ 📋 {p['id']}\n│  👑 {star}@{rejected_by} ({role})\n│  🆔 {rejected_by_id}\n│  🕐 {time}\n\n"
        else:
            msg += "├─ No rejections yet\n"
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
👑 *Super Admin:* @{update.effective_user.username}
🕐 *Last 10 entries shown*
"""
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=super_admin_menu)
        
    except Exception as e:
        logger.error(f"Approval log error: {e}")
        await update.message.reply_text("❌ Error loading approval log!", reply_markup=super_admin_menu)

# ==========================================
# ADMIN ACTIVITY
# ==========================================
async def admin_activity(update, context):
    try:
        uid = int(update.effective_user.id)
        if uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Only Super Admin can view this!")
            return
        
        msg = f"""
👑 *SUPER ADMIN - ADMIN ACTIVITY*
━━━━━━━━━━━━━━━━━━━━━━

📢 *BROADCAST HISTORY ({len(BROADCAST_HISTORY)})*
"""
        if BROADCAST_HISTORY:
            for entry in BROADCAST_HISTORY[-10:]:
                admin = entry.get('admin_name', 'Unknown')
                is_super = entry.get('is_super_admin', False)
                star = '⭐ ' if is_super else ''
                role = 'SUPER ADMIN' if is_super else 'ADMIN'
                count = entry.get('count', 0)
                time = entry.get('time', '')
                if time:
                    time = time[:16]
                msg += f"├─ 👑 {star}@{admin} ({role})\n│  📤 {count} users\n│  🕐 {time}\n\n"
        else:
            msg += "├─ No broadcasts yet\n"
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
👑 *Super Admin:* @{update.effective_user.username}
🕐 *Last 10 entries shown*
"""
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=super_admin_menu)
        
    except Exception as e:
        logger.error(f"Admin activity error: {e}")
        await update.message.reply_text("❌ Error loading admin activity!", reply_markup=super_admin_menu)

# ==========================================
# FEEDBACK SYSTEM
# ==========================================
async def feedback(update, context):
    try:
        uid = str(update.effective_user.id)
        
        msg = """
📝 *SEND YOUR FEEDBACK*
━━━━━━━━━━━━━━━━━━━━━━

✏️ *Type your feedback below*

💡 *Suggestions:*
├─ New features you want
├─ Improvements you suggest
├─ Bugs you found
└─ Any other thoughts

⭐ *Your feedback helps us improve!*

━━━━━━━━━━━━━━━━━━━━━━
🏠 Type 'HOME' to cancel
"""
        context.user_data['waiting_feedback'] = True
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Feedback error: {e}")

async def handle_feedback(update, context):
    try:
        if not context.user_data.get('waiting_feedback'):
            return
        
        text = update.message.text
        if text.upper() == "HOME":
            context.user_data['waiting_feedback'] = False
            await start_button(update, context)
            return
        
        uid = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"
        
        feedback_entry = {
            "user_id": uid,
            "username": username,
            "feedback": text,
            "time": datetime.now().isoformat()
        }
        FEEDBACK_LIST.append(feedback_entry)
        if len(FEEDBACK_LIST) > 100:
            FEEDBACK_LIST.pop(0)
        
        context.user_data['waiting_feedback'] = False
        
        await update.message.reply_text(
            f"""✅ *FEEDBACK SENT!*
━━━━━━━━━━━━━━━━━━━━━━
📝 *Your Feedback:* {text}

🙏 *Thank you for your feedback!*
⭐ *We will review it soon.*
━━━━━━━━━━━━━━━━━━━━━━
🏠 Click HOME to continue""",
            parse_mode='Markdown'
        )
        
        for admin_id in SUPER_ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"""📝 *NEW FEEDBACK!*
━━━━━━━━━━━━━━━━━━━━━━
👤 User: @{username}
🆔 ID: {uid}
📝 Feedback: {text}
🕐 Time: {datetime.now().strftime('%I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━━"""
                )
            except:
                pass
                
    except Exception as e:
        logger.error(f"Handle feedback error: {e}")

# ==========================================
# FEEDBACK LOG
# ==========================================
async def feedback_log(update, context):
    try:
        uid = int(update.effective_user.id)
        if uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Only Super Admin can view this!")
            return
        
        if not FEEDBACK_LIST:
            await update.message.reply_text("📭 No feedback yet!", reply_markup=super_admin_menu)
            return
        
        msg = f"""
📝 *FEEDBACK LOG ({len(FEEDBACK_LIST)})*
━━━━━━━━━━━━━━━━━━━━━━
"""
        for entry in FEEDBACK_LIST[-10:]:
            username = entry.get('username', 'Unknown')
            feedback = entry.get('feedback', '')
            time = entry.get('time', '')
            if time:
                time = time[:16]
            msg += f"""
👤 @{username}
📝 {feedback}
🕐 {time}
━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=super_admin_menu)
    except Exception as e:
        logger.error(f"Feedback log error: {e}")

# ==========================================
# PLAY
# ==========================================
async def play(update, context):
    try:
        uid = str(update.effective_user.id)
        if uid not in vip:
            await update.message.reply_text("❌ VIP REQUIRED!\nBuy: 💳 MEMBERSHIP", reply_markup=ReplyKeyboardMarkup([["💳 MEMBERSHIP"], ["🏠 HOME"]], resize_keyboard=True))
            return
        exp = datetime.fromisoformat(vip[uid]['expiry'])
        if exp <= datetime.now():
            await update.message.reply_text("❌ EXPIRED!\nRenew: /buy", reply_markup=main_menu)
            return
        context.user_data.clear()
        
        steps = [
            "🚀 LOADING...\n├─ █░░░░░░░░░ 10%\n└─ Initializing system...",
            "🚀 LOADING...\n├─ ████░░░░░░ 40%\n└─ Connecting to server...",
            "🚀 LOADING...\n├─ ████████░░ 80%\n└─ Preparing your key...",
            "🚀 LOADING...\n├─ ██████████ 100% ✅\n└─ Ready!"
        ]
        msg = await update.message.reply_text(steps[0])
        for i in range(1, len(steps)):
            await asyncio.sleep(0.2)
            await msg.edit_text(steps[i])
        await asyncio.sleep(0.2)
        await msg.delete()
        
        banner = get_passkey_banner()
        await update.message.reply_text(banner, reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("𝗬𝗢𝗨𝗥 𝗞𝗘𝗬 🔑👇👇")
        await asyncio.sleep(0.2)
        await update.message.reply_text(f"`{vip[uid]['key']}`", parse_mode='Markdown')
        await asyncio.sleep(0.2)
        await update.message.reply_text("> 𝗧𝗬𝗣𝗘 𝗬𝗢𝗨𝗥 𝗞𝗘𝗬:", reply_markup=ReplyKeyboardRemove())
        context.user_data['waiting_passkey'] = True
    except Exception as e:
        logger.error(f"Play error: {e}")
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=main_menu)

async def verify_passkey(update, context):
    try:
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
            context.user_data['waiting_passkey'] = False
        else:
            await update.message.reply_text(f"❌ INVALID KEY!\n🔑 Your Key: `{vip[uid]['key']}`", reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
            context.user_data['waiting_passkey'] = False
    except Exception as e:
        logger.error(f"Verify passkey error: {e}")

async def hacker_loading(update, context):
    try:
        steps = [
            "🔓 DECRYPT...\n├─ █░░░░░░░░░ 10%\n└─ Verifying key...",
            "🔓 DECRYPT...\n├─ ████░░░░░░ 40%\n└─ Access granted...",
            "🔓 DECRYPT...\n├─ ████████░░ 80%\n└─ Loading system...",
            "🔓 DECRYPT...\n├─ ██████████ 100% ✅\n└─ Complete!"
        ]
        msg = await update.message.reply_text(steps[0])
        for i in range(1, len(steps)):
            await asyncio.sleep(0.2)
            await msg.edit_text(steps[i])
        await asyncio.sleep(0.2)
        await msg.delete()
    except Exception as e:
        logger.error(f"Hacker loading error: {e}")

# ==========================================
# START GAME
# ==========================================
async def start_game(update, context):
    try:
        if not context.user_data.get('waiting_start'):
            return
        if update.message.text == "🚀 START 🚀":
            context.user_data['waiting_start'] = False
            await update.message.reply_text("✅ VERIFIED!\n📌 SELECT TIME:", reply_markup=timer_menu)
            context.user_data['waiting_timer'] = True
    except Exception as e:
        logger.error(f"Start game error: {e}")

# ==========================================
# TIMER SELECT
# ==========================================
async def timer_select(update, context):
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        if uid not in users:
            users[uid] = {"id": uid, "name": update.effective_user.username or "Unknown", "joined": str(datetime.now()), "win_count": 0, "loss_count": 0, "level": 0}
            save("users.json", users)
            logger.info(f"✅ New user created in timer: {uid}")
        timer_map = {"⏱ 30s": "30", "⏱ 1m": "60", "⏱ 2m": "120", "⏱ 5m": "300"}
        if text in timer_map:
            users[uid]['selected_time'] = timer_map[text]
            save("users.json", users)
            context.user_data['waiting_timer'] = False
            context.user_data['waiting_period'] = True
            banner = get_period_banner()
            await update.message.reply_text(f"✅ Timer: {text}\n\n{banner}", reply_markup=ReplyKeyboardRemove())
            return
        elif text == "🏠 HOME":
            context.user_data.clear()
            await start_button(update, context)
            return
    except Exception as e:
        logger.error(f"Timer error: {e}")
        context.user_data['waiting_timer'] = False
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=timer_menu)

# ==========================================
# SET PERIOD
# ==========================================
async def set_period(update, context):
    try:
        uid = str(update.effective_user.id)
        period = update.message.text.strip()
        if not context.user_data.get('waiting_period'):
            return
        if len(period) == 4 and period.isdigit():
            users[uid]['last_period'] = period
            save("users.json", users)
            context.user_data['waiting_period'] = False
            context.user_data['waiting_result_number'] = True
            banner = get_result_banner()
            await update.message.reply_text(f"✅ Period: {period}\n\n{banner}", reply_markup=result_number_menu)
        else:
            await update.message.reply_text("❌ Enter 4 digits only!\nExample: 1234", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logger.error(f"Set period error: {e}")

# ==========================================
# HANDLE RESULT NUMBER
# ==========================================
async def handle_result_number(update, context):
    try:
        uid = str(update.effective_user.id)
        text = update.message.text
        if not context.user_data.get('waiting_result_number'):
            return
        if text in ["⏱ 30s", "⏱ 1m", "⏱ 2m", "⏱ 5m"]:
            context.user_data['waiting_timer'] = True
            await timer_select(update, context)
            return
        if text == "⏱ TIMER":
            context.user_data['waiting_timer'] = True
            await update.message.reply_text("⏱ SELECT TIME", reply_markup=timer_menu)
            return
        if text == "🏠 HOME":
            context.user_data.clear()
            await start_button(update, context)
            return
        number_map = {"0️⃣":0,"1️⃣":1,"2️⃣":2,"3️⃣":3,"4️⃣":4,"5️⃣":5,"6️⃣":6,"7️⃣":7,"8️⃣":8,"9️⃣":9}
        if text in number_map:
            loading_msg = await update.message.reply_text("⏳ Processing...")
            await asyncio.sleep(0.3)
            await loading_msg.delete()
            user_num = number_map[text]
            result_trend = "BIG" if user_num >= 5 else "SMALL"
            result_category = "🔴 BIG" if user_num >= 5 else "🔵 SMALL"
            period = users[uid].get('last_period', '0000')
            save_result(uid, period, user_num, result_trend)
            add_result_to_algorithm(user_num)
            logger.info(f"✅ Added {user_num} to algorithm! Total: {len(HISTORICAL_RESULTS)}")
            if period not in GLOBAL_PERIOD_RESULTS:
                GLOBAL_PERIOD_RESULTS[period] = {"num1": user_num, "num2": random.randint(0, 9), "trend": result_trend, "category": result_category}
                logger.info(f"✅ Stored GLOBAL result for period {period}: {user_num} ({result_trend})")
            else:
                logger.info(f"⚠️ Period {period} ALREADY exists in GLOBAL! Using existing: {GLOBAL_PERIOD_RESULTS[period]['num1']}")
            context.user_data['waiting_result_number'] = False
            await update.message.reply_text(f"✅ Result Saved!\n📊 {user_num}\n📈 {result_category}\n🔢 {period}", reply_markup=ReplyKeyboardRemove())
            await process_analysis(update, context, uid, None, period)
    except Exception as e:
        logger.error(f"Handle result number error: {e}")
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=result_number_menu)

# ==========================================
# PROCESS ANALYSIS
# ==========================================
async def process_analysis(update, context, uid, periods=None, last_period=None):
    try:
        steps = [
            "📊 ANALYZING...\n├─ █░░░░░░░░░ 10%\n└─ Scanning patterns...",
            "📊 ANALYZING...\n├─ ████░░░░░░ 40%\n└─ Processing data...",
            "📊 ANALYZING...\n├─ ████████░░ 80%\n└─ Generating results...",
            "📊 ANALYZING...\n├─ ██████████ 100% ✅\n└─ Complete!"
        ]
        msg = await update.message.reply_text(steps[0])
        for i in range(1, len(steps)):
            await asyncio.sleep(0.2)
            await msg.edit_text(steps[i])
        await asyncio.sleep(0.2)
        await msg.delete()
        
        if last_period:
            current_period = str(int(last_period) + 1).zfill(4)
        else:
            current_period = ''.join(random.choices(string.digits, k=4))
        global_result = get_global_result_for_period(current_period, generate_if_missing=True)
        num1 = global_result["num1"]
        num2 = global_result["num2"]
        trend = global_result["trend"]
        category = global_result["category"]
        logger.info(f"✅ Using GLOBAL result for period {current_period}: {num1}, {num2} ({trend})")
        users[uid]['last_period'] = current_period
        save("users.json", users)
        context.user_data['last_analysis'] = {"trend": trend, "num1": num1, "num2": num2, "period": current_period}
        pred = predict_next()
        next_prediction = f"{pred['prediction']} ({pred['confidence']})"
        banner = get_analysis_banner(current_period, category, num1, num2)
        await update.message.reply_text(banner, reply_markup=result_keyboard)
        context.user_data['waiting_result'] = True
    except Exception as e:
        logger.error(f"Process analysis error: {e}")
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=result_keyboard)

# ==========================================
# HANDLE RESULT - Level System: Loss = Level Up, Win = Reset to 0
# ==========================================
async def handle_result(update, context):
    try:
        uid = str(update.effective_user.id)
        text = update.message.text
        if not context.user_data.get('waiting_result'):
            return
        last = context.user_data.get('last_analysis', {})
        period = last.get('period', '0000')
        
        if text in ["⏱ 30s", "⏱ 1m", "⏱ 2m", "⏱ 5m"]:
            context.user_data['waiting_timer'] = True
            await timer_select(update, context)
            return
        if text == "⏱ TIMER":
            context.user_data['waiting_timer'] = True
            await update.message.reply_text("⏱ SELECT TIME", reply_markup=timer_menu)
            return
        
        if text in ["🔴 BIG", "🔵 SMALL"]:
            loading_msg = await update.message.reply_text("⏳ Processing...")
            await asyncio.sleep(0.2)
            await loading_msg.delete()
            user_choice = "BIG" if text == "🔴 BIG" else "SMALL"
            final_choice = get_opposite_result(uid, user_choice)
            win = final_choice == last.get('trend')
            
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
            
            next_num1 = random.randint(5, 9) if final_choice == "BIG" else random.randint(0, 4)
            next_num2 = random.randint(5, 9) if final_choice == "BIG" else random.randint(0, 4)
            next_trend = "BIG" if next_num1 >= 5 and next_num2 >= 5 else "SMALL"
            next_category = "🔴 BIG" if next_trend == "BIG" else "🔵 SMALL"
            next_period = str(int(period) + 1).zfill(4)
            if next_period not in GLOBAL_PERIOD_RESULTS:
                GLOBAL_PERIOD_RESULTS[next_period] = {"num1": next_num1, "num2": next_num2, "trend": next_trend, "category": next_category}
            else:
                logger.info(f"⚠️ Period {next_period} ALREADY exists! Using existing result.")
            pred = predict_next()
            next_prediction = f"{pred['prediction']} ({pred['confidence']})"
            
            banner = get_stats_banner(
                users[uid]['win_count'],
                users[uid]['loss_count'],
                users[uid]['level'],
                next_period,
                next_category,
                next_num1,
                next_num2,
                player_result=final_choice,
                next_prediction=next_prediction
            )
            await update.message.reply_text(f"{result_text}\n{banner}", reply_markup=result_keyboard)
            context.user_data['last_analysis'] = {"trend": next_trend, "num1": next_num1, "num2": next_num2, "period": next_period}
            return
        
        if text in ["0️⃣","1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]:
            loading_msg = await update.message.reply_text("⏳ Processing...")
            await asyncio.sleep(0.2)
            await loading_msg.delete()
            user_num = int(text[0])
            result_trend = "BIG" if user_num >= 5 else "SMALL"
            final_trend = get_opposite_result(uid, result_trend)
            win = final_trend == last.get('trend')
            
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
            
            next_num1 = random.randint(5, 9) if final_trend == "BIG" else random.randint(0, 4)
            next_num2 = random.randint(5, 9) if final_trend == "BIG" else random.randint(0, 4)
            next_trend = "BIG" if next_num1 >= 5 and next_num2 >= 5 else "SMALL"
            next_category = "🔴 BIG" if next_trend == "BIG" else "🔵 SMALL"
            next_period = str(int(period) + 1).zfill(4)
            if next_period not in GLOBAL_PERIOD_RESULTS:
                GLOBAL_PERIOD_RESULTS[next_period] = {"num1": next_num1, "num2": next_num2, "trend": next_trend, "category": next_category}
            else:
                logger.info(f"⚠️ Period {next_period} ALREADY exists! Using existing result.")
            pred = predict_next()
            next_prediction = f"{pred['prediction']} ({pred['confidence']})"
            
            banner = get_stats_banner(
                users[uid]['win_count'],
                users[uid]['loss_count'],
                users[uid]['level'],
                next_period,
                next_category,
                next_num1,
                next_num2,
                player_result=final_trend,
                next_prediction=next_prediction
            )
            await update.message.reply_text(f"{result_text}\n{banner}", reply_markup=result_keyboard)
            context.user_data['last_analysis'] = {"trend": next_trend, "num1": next_num1, "num2": next_num2, "period": next_period}
            return
        
        if text in ["🏠 HOME", "🔙 BACK"]:
            context.user_data.clear()
            await start_button(update, context)
            return
        
        await update.message.reply_text("❓ Use buttons!", reply_markup=result_keyboard)
    except Exception as e:
        logger.error(f"Handle result error: {e}")
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=result_keyboard)

# ==========================================
# ANALYSIS COMMAND
# ==========================================
async def analysis(update, context):
    report = get_analysis_report()
    await update.message.reply_text(report, reply_markup=main_menu)

async def profile(update, context):
    try:
        uid = str(update.effective_user.id)
        user = users.get(uid, {})
        is_vip = False
        is_verified = context.user_data.get('verified', False)
        exp_text = "No Membership"
        key_text = "N/A"
        remaining = "N/A"
        joined_date = user.get('joined', datetime.now().strftime('%Y-%m-%d %H:%M'))
        
        if uid in vip:
            exp = datetime.fromisoformat(vip[uid]['expiry'])
            if exp > datetime.now():
                is_vip = True
                exp_text = exp.strftime('%Y-%m-%d %H:%M')
                key_text = vip[uid]['key']
                remaining_seconds = (exp - datetime.now()).total_seconds()
                if remaining_seconds > 3600:
                    remaining = f"{int(remaining_seconds // 3600)}h {int((remaining_seconds % 3600) // 60)}m"
                else:
                    remaining = f"{int(remaining_seconds // 60)}m"
        
        rank, rank_emoji = get_rank(user.get('level', 0))
        achievements_list = get_achievements(
            user.get('win_count', 0),
            user.get('loss_count', 0),
            user.get('level', 0)
        )
        
        username = update.effective_user.username or "Unknown"
        first_name = update.effective_user.first_name or "User"
        banner = f"""
𝟬𝟭 — 𝗛𝗢𝗠𝗘 / 𝗪𝗘𝗟𝗖𝗢𝗠𝗘
┌─[ 🌌 𝗖/𝗧 𝗪𝗜𝗡 𝗛𝗔𝗖𝗞 ]
│
├─┬─[ 𝗦𝗬𝗦𝗧𝗘𝗠 𝗜𝗡𝗙𝗢 ]
│ ├─ 𝗨𝗦𝗘𝗥    :: @{username}
│ ├─ 𝗔𝗖𝗖𝗘𝗦𝗦  :: {'★ VIP' if is_vip else 'FREE'}
│ ├─ 𝗦𝗧𝗔𝗧𝗨𝗦  :: {'🟢 ONLINE' if is_verified else '🟡 AWAITING'}
│ └─ 𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬 :: {'🔐 VERIFIED' if is_verified else '🔓 UNVERIFIED'}
│
└─[ 🔐 𝗖/𝗧://𝗦𝗘𝗖𝗨𝗥𝗘_𝗖𝗢𝗡𝗡𝗘𝗖𝗧𝗜𝗢𝗡 ]

┌─[ 📊 𝗣𝗥𝗢𝗙𝗜𝗟𝗘 ]
│
├─ 𝗨𝗦𝗘𝗥 𝗣𝗥𝗢𝗙𝗜𝗟𝗘
│ ├─ 👤 𝗡𝗔𝗠𝗘     :: {first_name}
│ ├─ 🆔 𝗜𝗗       :: {uid}
│ ├─ 💎 𝗩𝗜𝗣      :: {'✅ ACTIVE' if is_vip else '❌ INACTIVE'}
│ └─ ✅ 𝗩𝗘𝗥𝗜𝗙𝗜𝗘𝗗 :: {'✅ YES' if is_verified else '❌ NO'}
│
├─ 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣
│ ├─ 𝗦𝗧𝗔𝗧𝗨𝗦     :: {'🟢 VIP' if is_vip else '🔴 FREE'}
│ ├─ 𝗝𝗢𝗜𝗡𝗘𝗗     :: {joined_date}
│ ├─ 𝗘𝗫𝗣𝗜𝗥𝗬     :: {exp_text}
│ └─ ⏰ 𝗥𝗘𝗠𝗔𝗜𝗡𝗜𝗡𝗚 :: {remaining}
│
├─ 𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗛𝗜𝗦𝗧𝗢𝗥𝗬
│ ├─ 🏆 𝗪𝗜𝗡   :: {user.get('win_count', 0):02d}
│ ├─ ❌ 𝗟𝗢𝗦𝗦  :: {user.get('loss_count', 0):02d}
│ ├─ 📊 𝗟𝗘𝗩𝗘𝗟 :: {user.get('level', 0):02d} {rank_emoji}
│ └─ 🎖️ 𝗥𝗔𝗡𝗞 :: {rank}
│
├─ 𝗔𝗖𝗛𝗜𝗘𝗩𝗘𝗠𝗘𝗡𝗧𝗦
"""
        for ach in achievements_list[:3]:
            banner += f"│ ├─ ✅ {ach}\n"
        if len(achievements_list) > 3:
            banner += f"│ └─ ... +{len(achievements_list)-3} more\n"
        
        banner += f"""
├─ 𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬
│ └─ 🔑 𝗣𝗔𝗦𝗦𝗞𝗘𝗬 :: {key_text}
│
└─[ 𝗖/𝗧://𝗣𝗥𝗢𝗙𝗜𝗟𝗘 ]
"""
        await update.message.reply_text(banner, reply_markup=profile_menu)
    except Exception as e:
        logger.error(f"Profile error: {e}")
        await update.message.reply_text("❌ Error loading profile!", reply_markup=main_menu)

async def start_analysis(update, context):
    try:
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
    except Exception as e:
        logger.error(f"Start analysis error: {e}")

async def support(update, context):
    msg = """
📞 SUPPORT
━━━━━━━━━━━━━━━━━━━━━━
👤 Admin: @BDGmin

📱 Contact: @BDGmin
⏰ Response: 24/7

For any issues, contact admin directly.
━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(msg, reply_markup=main_menu)

async def home(update, context):
    context.user_data.clear()
    await start_button(update, context)

async def stats(update, context):
    try:
        if int(update.effective_user.id) not in ADMIN_IDS:
            await update.message.reply_text("❌ Admin only!")
            return
        pending = len([p for p in pay.values() if p['status'] == 'pending'])
        active_vip = len([v for v in vip.values() if datetime.fromisoformat(v['expiry']) > datetime.now()])
        await update.message.reply_text(f"""📊 STATS\n━━━━━━━━━━━━━━━━━━━━━━\n👥 Users: {len(users)}\n⭐ Active VIP: {active_vip}\n💰 Total VIP: {len(vip)}\n⏳ Pending: {pending}\n━━━━━━━━━━━━━━━━━━━━━━""")
    except Exception as e:
        logger.error(f"Stats error: {e}")

async def payments_list(update, context):
    try:
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
    except Exception as e:
        logger.error(f"Payments list error: {e}")

async def payment_history(update, context):
    try:
        if int(update.effective_user.id) not in ADMIN_IDS:
            await update.message.reply_text("❌ Admin only!")
            return
        today = datetime.now().strftime('%Y-%m-%d')
        today_pending = 0
        today_approved = 0
        today_rejected = 0
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_pending = 0
        yesterday_approved = 0
        yesterday_rejected = 0
        for p in pay.values():
            p_date = p.get('time', '')[:10]
            status = p.get('status', 'pending')
            if p_date == today:
                if status == 'pending':
                    today_pending += 1
                elif status == 'approved':
                    today_approved += 1
                elif status == 'rejected':
                    today_rejected += 1
            elif p_date == yesterday:
                if status == 'pending':
                    yesterday_pending += 1
                elif status == 'approved':
                    yesterday_approved += 1
                elif status == 'rejected':
                    yesterday_rejected += 1
        msg = f"""
📅 PAYMENT HISTORY
━━━━━━━━━━━━━━━━━━━━━━

📊 TODAY ({today})
├─ ⏳ Pending  :: {today_pending}
├─ ✅ Approved :: {today_approved}
└─ ❌ Rejected :: {today_rejected}

📊 YESTERDAY ({yesterday})
├─ ⏳ Pending  :: {yesterday_pending}
├─ ✅ Approved :: {yesterday_approved}
└─ ❌ Rejected :: {yesterday_rejected}

━━━━━━━━━━━━━━━━━━━━━━
💰 Total Payments: {len(pay)}
"""
        await update.message.reply_text(msg, reply_markup=admin_menu)
    except Exception as e:
        logger.error(f"Payment history error: {e}")
        await update.message.reply_text("❌ Error loading payment history!", reply_markup=admin_menu)

async def payment_status(update, context):
    try:
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
    except Exception as e:
        logger.error(f"Payment status error: {e}")

# ==========================================
# HANDLE BUTTONS - FIXED (BACK & HOME Working)
# ==========================================
async def handle_buttons(update, context):
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        
        # Handle feedback mode
        if context.user_data.get('waiting_feedback'):
            await handle_feedback(update, context)
            return
        
        if uid not in users:
            users[uid] = {"id": uid, "name": update.effective_user.username or "Unknown", "joined": str(datetime.now()), "win_count": 0, "loss_count": 0, "level": 0}
            save("users.json", users)
            logger.info(f"✅ New user created in handle_buttons: {uid}")
        
        # Broadcast mode check
        if context.user_data.get('broadcast_mode'):
            if text.upper() == "CANCEL":
                context.user_data['broadcast_mode'] = False
                await update.message.reply_text("🏠 *Broadcast cancelled.*", parse_mode='Markdown')
                await start_button(update, context)
                return
            
            if text in ["🚀 START", "💳 MEMBERSHIP", "▶️ PLAY", "👤 PROFILE", "📞 SUPPORT", "📊 STATS", "💰 PAYMENTS", "📢 BROADCAST", "📅 PAYMENT HISTORY", "📋 APPROVAL LOG", "👑 ADMIN ACTIVITY", "🔙 BACK", "🏠 HOME", "📝 FEEDBACK", "📝 FEEDBACK LOG"]:
                context.user_data['broadcast_mode'] = False
                await update.message.reply_text("🏠 *Broadcast cancelled.*", parse_mode='Markdown')
            
            msg = text
            count = 0
            loading_msg = await update.message.reply_text("📢 *Broadcasting...*", parse_mode='Markdown')
            
            for uid in users:
                try:
                    await context.bot.send_message(uid, f"📢 {msg}")
                    count += 1
                    await asyncio.sleep(0.05)
                except:
                    pass
            
            await loading_msg.delete()
            context.user_data['broadcast_mode'] = False
            
            admin_id = int(update.effective_user.id)
            admin_name = update.effective_user.username or str(admin_id)
            is_super_admin = admin_id in SUPER_ADMIN_IDS
            
            broadcast_entry = {
                "admin_id": admin_id,
                "admin_name": admin_name,
                "is_super_admin": is_super_admin,
                "message": msg[:100],
                "count": count,
                "time": datetime.now().isoformat()
            }
            BROADCAST_HISTORY.append(broadcast_entry)
            if len(BROADCAST_HISTORY) > 50:
                BROADCAST_HISTORY.pop(0)
            
            current_time = datetime.now().strftime('%I:%M %p')
            
            success_msg = f"""
✅ *BROADCAST SUCCESSFUL!*
━━━━━━━━━━━━━━━━━━━━━━

📊 *Statistics:*
├─ 👥 Sent to :: {count} users
├─ 📤 Message :: {msg[:50]}{'...' if len(msg) > 50 else ''}
├─ 👑 Admin    :: @{admin_name} {'⭐' if is_super_admin else ''}
└─ 🕐 Time    :: {current_time}

━━━━━━━━━━━━━━━━━━━━━━
📢 Click below to send another broadcast
"""
            inline_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 New Broadcast", callback_data="broadcast_new")]
            ])
            
            await update.message.reply_text(
                success_msg,
                parse_mode='Markdown',
                reply_markup=inline_keyboard
            )
            return
        
        # Check other states - IMPORTANT: BACK and HOME handled here
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
        
        # Main menu buttons
        user_id_int = int(uid)
        is_super_admin = user_id_int in SUPER_ADMIN_IDS
        
        # ⭐ BACK and HOME buttons - ALWAYS work
        if text in ["🏠 HOME", "🔙 BACK"]:
            context.user_data.clear()
            await start_button(update, context)
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
            await broadcast(update, context)
        elif text == "📅 PAYMENT HISTORY":
            await payment_history(update, context)
        elif text == "📋 APPROVAL LOG":
            if is_super_admin:
                await approval_log(update, context)
            else:
                await update.message.reply_text("❌ Only Super Admin can view this!", reply_markup=admin_menu)
        elif text == "👑 ADMIN ACTIVITY":
            if is_super_admin:
                await admin_activity(update, context)
            else:
                await update.message.reply_text("❌ Only Super Admin can view this!", reply_markup=admin_menu)
        elif text == "📝 FEEDBACK":
            await feedback(update, context)
        elif text == "📝 FEEDBACK LOG":
            if is_super_admin:
                await feedback_log(update, context)
            else:
                await update.message.reply_text("❌ Only Super Admin can view this!", reply_markup=admin_menu)
        elif text == "📊 ANALYSIS":
            await analysis(update, context)
        elif text == "⏱ TIMER":
            context.user_data['waiting_timer'] = True
            await update.message.reply_text("⏱ SELECT TIME", reply_markup=timer_menu)
        elif text in ["⏱ 30s", "⏱ 1m", "⏱ 2m", "⏱ 5m"]:
            context.user_data['waiting_timer'] = True
            await timer_select(update, context)
        elif text == "▶️ START ANALYSIS":
            await start_analysis(update, context)
        else:
            await update.message.reply_text("❓ Use buttons!", reply_markup=main_menu)
    except Exception as e:
        logger.error(f"Handle buttons error: {e}")
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=main_menu)

# ==========================================
# ERROR HANDLER
# ==========================================
async def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")
    try:
        await update.message.reply_text("❌ Something went wrong! Please try again.", reply_markup=main_menu)
    except:
        pass

# ==========================================
# MAIN
# ==========================================
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy_membership))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("payments", payment_status))
    app.add_handler(CommandHandler("payment_history", payment_history))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("analysis", analysis))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    app.add_error_handler(error_handler)
    
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    print("✅ Health check server running on port 10000!")
    print("=" * 50)
    print("🌟 AURA BOT v7.0 STARTED!")
    print("=" * 50)
    print("✅ Bot is running!")
    print(f"👑 Super Admin: {SUPER_ADMIN_IDS}")
    print(f"📌 All Admins: {ADMIN_IDS}")
    print("=" * 50)
    app.run_polling()

if __name__ == "__main__":
    main()