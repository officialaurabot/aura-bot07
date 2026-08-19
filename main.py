# ==========================================
# 🌌 AURA BOT v8.0 - FINAL COMPLETE
# ==========================================

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import json, os, random, string, asyncio, re, sqlite3, hashlib
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
        pass

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
ADMIN_IDS = [5901835425, 6467765686, 7295714098, 7495428732]

BROADCAST_HISTORY = []
FEEDBACK_LIST = []

# ==========================================
# GLOBAL RESULT STORAGE
# ==========================================
GLOBAL_PERIOD_RESULTS = {}
USER_PRESS_TRACKER = {}

# ==========================================
# ⭐ DAILY BONUS SYSTEM
# ==========================================
DAILY_BONUS_TRACKER = {}

async def daily_bonus(update, context):
    uid = str(update.effective_user.id)
    today = datetime.now().date().isoformat()
    
    if uid not in DAILY_BONUS_TRACKER:
        DAILY_BONUS_TRACKER[uid] = {}
    
    if DAILY_BONUS_TRACKER[uid].get('last_claimed') == today:
        await update.message.reply_text(
            "⏰ *DAILY BONUS ALREADY CLAIMED!*\n━━━━━━━━━━━━━━━━━━━━━━\nCome back tomorrow for more! 🎁\n━━━━━━━━━━━━━━━━━━━━━━\n💪 Keep playing!",
            parse_mode='Markdown'
        )
        return
    
    bonus = random.randint(5, 15)
    users[uid]['win_count'] = users[uid].get('win_count', 0) + bonus
    DAILY_BONUS_TRACKER[uid]['last_claimed'] = today
    save("users.json", users)
    
    await update.message.reply_text(
        f"🎁 *DAILY BONUS CLAIMED!* 🎁\n━━━━━━━━━━━━━━━━━━━━━━\n✅ +{bonus} Free Wins!\n📊 Total Wins: {users[uid]['win_count']}\n━━━━━━━━━━━━━━━━━━━━━━\n🔥 Come back tomorrow for more!",
        parse_mode='Markdown'
    )

# ==========================================
# ⭐ STREAK SYSTEM
# ==========================================
STREAK_TRACKER = {}

def update_streak(uid, win):
    if uid not in STREAK_TRACKER:
        STREAK_TRACKER[uid] = {'streak': 0, 'max_streak': 0}
    
    if win:
        STREAK_TRACKER[uid]['streak'] += 1
        if STREAK_TRACKER[uid]['streak'] > STREAK_TRACKER[uid]['max_streak']:
            STREAK_TRACKER[uid]['max_streak'] = STREAK_TRACKER[uid]['streak']
    else:
        STREAK_TRACKER[uid]['streak'] = 0
    
    return STREAK_TRACKER[uid]['streak']

def get_streak_bonus(streak):
    if streak >= 10:
        return 15, "🔥 10 WIN STREAK! +15 BONUS! 🔥"
    elif streak >= 7:
        return 10, "⚡ 7 WIN STREAK! +10 BONUS! ⚡"
    elif streak >= 5:
        return 5, "🔥 5 WIN STREAK! +5 BONUS! 🔥"
    elif streak >= 3:
        return 3, "💪 3 WIN STREAK! +3 BONUS! 💪"
    return 0, None

# ==========================================
# ⭐ CHALLENGE MODE
# ==========================================
CHALLENGES = [
    {"name": "Win 3 in a row", "reward": 10, "type": "streak", "target": 3},
    {"name": "Win 5 in a row", "reward": 20, "type": "streak", "target": 5},
    {"name": "Win 10 in a row", "reward": 50, "type": "streak", "target": 10},
    {"name": "Get 10 wins", "reward": 15, "type": "wins", "target": 10},
    {"name": "Get 25 wins", "reward": 30, "type": "wins", "target": 25},
    {"name": "Get 50 wins", "reward": 75, "type": "wins", "target": 50},
    {"name": "Play 25 games", "reward": 20, "type": "games", "target": 25},
    {"name": "Play 50 games", "reward": 40, "type": "games", "target": 50},
    {"name": "Play 100 games", "reward": 100, "type": "games", "target": 100},
]

CHALLENGE_TRACKER = {}

def check_challenges(uid, win, total_plays):
    if uid not in CHALLENGE_TRACKER:
        CHALLENGE_TRACKER[uid] = {'streak': 0, 'wins': 0, 'games': 0}
    
    CHALLENGE_TRACKER[uid]['games'] += 1
    if win:
        CHALLENGE_TRACKER[uid]['streak'] += 1
        CHALLENGE_TRACKER[uid]['wins'] += 1
    else:
        CHALLENGE_TRACKER[uid]['streak'] = 0
    
    completed = []
    for challenge in CHALLENGES:
        key = f"{challenge['name']}_{uid}"
        if challenge['type'] == 'streak' and CHALLENGE_TRACKER[uid]['streak'] >= challenge['target']:
            if not CHALLENGE_TRACKER[uid].get(f'completed_{challenge["name"]}', False):
                CHALLENGE_TRACKER[uid][f'completed_{challenge["name"]}'] = True
                completed.append(challenge)
        elif challenge['type'] == 'wins' and CHALLENGE_TRACKER[uid]['wins'] >= challenge['target']:
            if not CHALLENGE_TRACKER[uid].get(f'completed_{challenge["name"]}', False):
                CHALLENGE_TRACKER[uid][f'completed_{challenge["name"]}'] = True
                completed.append(challenge)
        elif challenge['type'] == 'games' and CHALLENGE_TRACKER[uid]['games'] >= challenge['target']:
            if not CHALLENGE_TRACKER[uid].get(f'completed_{challenge["name"]}', False):
                CHALLENGE_TRACKER[uid][f'completed_{challenge["name"]}'] = True
                completed.append(challenge)
    
    return completed

# ==========================================
# ⭐ ACHIEVEMENT BADGES
# ==========================================
BADGES = {
    "🏅 First Win": {"condition": "win_first", "description": "Win your first game"},
    "🏆 10 Wins": {"condition": "win_10", "description": "Win 10 games"},
    "👑 50 Wins": {"condition": "win_50", "description": "Win 50 games"},
    "💎 100 Wins": {"condition": "win_100", "description": "Win 100 games"},
    "🔥 3 Streak": {"condition": "streak_3", "description": "Win 3 in a row"},
    "⚡ 5 Streak": {"condition": "streak_5", "description": "Win 5 in a row"},
    "🌟 10 Streak": {"condition": "streak_10", "description": "Win 10 in a row"},
    "🎯 25 Games": {"condition": "games_25", "description": "Play 25 games"},
    "🚀 50 Games": {"condition": "games_50", "description": "Play 50 games"},
    "🏅 100 Games": {"condition": "games_100", "description": "Play 100 games"},
}

BADGE_TRACKER = {}

def check_badges(uid, win, total_plays):
    if uid not in BADGE_TRACKER:
        BADGE_TRACKER[uid] = {'earned': []}
    
    earned = []
    wins = users[uid].get('win_count', 0)
    streak = STREAK_TRACKER.get(uid, {}).get('streak', 0)
    
    badge_map = {
        "win_first": wins >= 1,
        "win_10": wins >= 10,
        "win_50": wins >= 50,
        "win_100": wins >= 100,
        "streak_3": streak >= 3,
        "streak_5": streak >= 5,
        "streak_10": streak >= 10,
        "games_25": total_plays >= 25,
        "games_50": total_plays >= 50,
        "games_100": total_plays >= 100,
    }
    
    for badge_name, badge_data in BADGES.items():
        condition = badge_data['condition']
        if badge_map.get(condition, False) and condition not in BADGE_TRACKER[uid]['earned']:
            BADGE_TRACKER[uid]['earned'].append(condition)
            earned.append(badge_name)
    
    return earned

# ==========================================
# ⭐ WEEKLY REWARDS
# ==========================================
WEEKLY_REWARDS_TRACKER = {}

async def weekly_rewards(update, context):
    uid = str(update.effective_user.id)
    week_start = datetime.now().date() - timedelta(days=datetime.now().weekday())
    week_key = week_start.isoformat()
    
    if uid not in WEEKLY_REWARDS_TRACKER:
        WEEKLY_REWARDS_TRACKER[uid] = {}
    
    if WEEKLY_REWARDS_TRACKER[uid].get('week_claimed') == week_key:
        await update.message.reply_text(
            "⏰ *WEEKLY REWARDS ALREADY CLAIMED!*\n━━━━━━━━━━━━━━━━━━━━━━\nCome back next week! 🏆",
            parse_mode='Markdown'
        )
        return
    
    # Get top players for weekly rewards
    all_users = get_leaderboard_users()
    top_10 = all_users[:10]
    
    msg = f"""
🏆 *WEEKLY REWARDS*
━━━━━━━━━━━━━━━━━━━━━━
📅 Week: {week_start.strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}

👑 *TOP 10 PLAYERS*
"""
    medals = ["🥇", "🥈", "🥉", "04", "05", "06", "07", "08", "09", "10"]
    for i, user in enumerate(top_10):
        medal = medals[i] if i < len(medals) else f"{i+1:02d}"
        msg += f"\n{medal} {user['rank_emoji']} {user['username']} - {user['total']} plays"
    
    msg += """
━━━━━━━━━━━━━━━━━━━━━━
🎁 *Your Reward Status:*
"""
    
    # Check if user is in top 10
    user_pos = None
    for i, user in enumerate(top_10):
        if user['id'] == uid:
            user_pos = i + 1
            break
    
    if user_pos:
        if user_pos == 1:
            msg += "🏆 *RANK 1: +50 Bonus Wins!*"
            users[uid]['win_count'] = users[uid].get('win_count', 0) + 50
        elif user_pos == 2:
            msg += "🥈 *RANK 2: +30 Bonus Wins!*"
            users[uid]['win_count'] = users[uid].get('win_count', 0) + 30
        elif user_pos == 3:
            msg += "🥉 *RANK 3: +20 Bonus Wins!*"
            users[uid]['win_count'] = users[uid].get('win_count', 0) + 20
        else:
            msg += "👏 *Good Effort! Keep it up!*"
    else:
        msg += "💪 *Keep playing to reach Top 10!*"
    
    WEEKLY_REWARDS_TRACKER[uid]['week_claimed'] = week_key
    save("users.json", users)
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==========================================
# ⭐ PREDICTION HISTORY
# ==========================================
HISTORY_TRACKER = {}

def add_to_history(uid, period, number, trend, result):
    if uid not in HISTORY_TRACKER:
        HISTORY_TRACKER[uid] = []
    
    HISTORY_TRACKER[uid].append({
        'period': period,
        'number': number,
        'trend': trend,
        'result': 'WIN' if result else 'LOSS',
        'time': datetime.now().isoformat()
    })
    
    if len(HISTORY_TRACKER[uid]) > 50:
        HISTORY_TRACKER[uid].pop(0)

async def show_history(update, context):
    uid = str(update.effective_user.id)
    
    if uid not in HISTORY_TRACKER or not HISTORY_TRACKER[uid]:
        await update.message.reply_text(
            "📜 *NO PREDICTION HISTORY*\n━━━━━━━━━━━━━━━━━━━━━━\nStart playing to build your history! 🎯",
            parse_mode='Markdown'
        )
        return
    
    history = HISTORY_TRACKER[uid][-20:]  # Last 20 predictions
    
    msg = f"""
📜 *PREDICTION HISTORY*
━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, entry in enumerate(history, 1):
        status = "✅ WIN" if entry['result'] == 'WIN' else "❌ LOSS"
        msg += f"{i}. Period: {entry['period']} | {entry['number']} | {entry['trend']} | {status}\n"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
📊 *Total Predictions:* {len(history)}
💪 Keep going!"""
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==========================================
# ⭐ REFERRAL SYSTEM
# ==========================================
REFERRAL_TRACKER = {}
REFERRAL_CODE_TRACKER = {}

def generate_referral_code(uid):
    return hashlib.md5(f"{uid}_{datetime.now().isoformat()}".encode()).hexdigest()[:8].upper()

async def referral_system(update, context):
    uid = str(update.effective_user.id)
    
    if uid not in REFERRAL_CODE_TRACKER:
        REFERRAL_CODE_TRACKER[uid] = generate_referral_code(uid)
    
    ref_code = REFERRAL_CODE_TRACKER[uid]
    ref_link = f"https://t.me/YourBot?start=ref_{ref_code}"
    
    msg = f"""
👥 *REFERRAL SYSTEM*
━━━━━━━━━━━━━━━━━━━━━━

🔗 *Your Referral Link:*
`{ref_link}`

🎁 *Rewards:*
├─ Refer 1 friend: +5 Wins
├─ Refer 3 friends: +15 Wins
└─ Refer 5 friends: +30 Wins + VIP 24H

👥 *Total Referrals:* {REFERRAL_TRACKER.get(uid, {}).get('count', 0)}

━━━━━━━━━━━━━━━━━━━━━━
💡 Share your link and earn rewards!
"""
    await update.message.reply_text(msg, parse_mode='Markdown')

async def handle_referral(update, context):
    uid = str(update.effective_user.id)
    text = update.message.text
    
    if text.startswith('/start ref_'):
        ref_code = text.replace('/start ref_', '').strip()
        
        # Find who referred
        referrer = None
        for user_id, code in REFERRAL_CODE_TRACKER.items():
            if code == ref_code:
                referrer = user_id
                break
        
        if referrer and referrer != uid:
            if referrer not in REFERRAL_TRACKER:
                REFERRAL_TRACKER[referrer] = {'count': 0, 'rewards': 0}
            
            REFERRAL_TRACKER[referrer]['count'] += 1
            count = REFERRAL_TRACKER[referrer]['count']
            
            # Give rewards based on referrals
            if count >= 5:
                users[referrer]['win_count'] = users[referrer].get('win_count', 0) + 30
                # Give VIP 24H
                expiry = datetime.now() + timedelta(days=1)
                key = gen_key()
                vip[referrer] = {
                    "user_id": referrer,
                    "key": key,
                    "expiry": expiry.isoformat(),
                    "is_referral": True
                }
                save("vip.json", vip)
                reward_msg = "🎉 +30 Wins + VIP 24H!"
            elif count >= 3:
                users[referrer]['win_count'] = users[referrer].get('win_count', 0) + 15
                reward_msg = "🎉 +15 Wins!"
            elif count >= 1:
                users[referrer]['win_count'] = users[referrer].get('win_count', 0) + 5
                reward_msg = "🎉 +5 Wins!"
            else:
                reward_msg = ""
            
            save("users.json", users)
            
            try:
                await context.bot.send_message(
                    chat_id=referrer,
                    text=f"👥 *NEW REFERRAL!*\n━━━━━━━━━━━━━━━━━━━━━━\nSomeone used your referral code!\n\n📊 Total Referrals: {count}\n🎁 {reward_msg}",
                    parse_mode='Markdown'
                )
            except:
                pass
            
            await update.message.reply_text(
                f"✅ *REFERRAL SUCCESSFUL!*\n━━━━━━━━━━━━━━━━━━━━━━\nYou were referred by someone!\n🎁 You also get +2 Bonus Wins!\n━━━━━━━━━━━━━━━━━━━━━━\n🎯 Start playing now!",
                parse_mode='Markdown'
            )
            users[uid]['win_count'] = users[uid].get('win_count', 0) + 2
            save("users.json", users)

# ==========================================
# ⭐ BOT STATS DASHBOARD
# ==========================================
async def bot_stats_dashboard(update, context):
    try:
        uid = int(update.effective_user.id)
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Admin only!")
            return
        
        global users, vip, pay
        
        total_users = len(users)
        active_vip = sum(1 for v in vip.values() if datetime.fromisoformat(v['expiry']) > datetime.now())
        total_payments = len(pay)
        pending_payments = sum(1 for p in pay.values() if p.get('status') == 'pending')
        
        # Calculate daily active users
        daily_active = 0
        today = datetime.now().date().isoformat()
        for uid, user_data in users.items():
            if user_data.get('last_active', '').startswith(today):
                daily_active += 1
        
        total_wins = sum(u.get('win_count', 0) for u in users.values())
        total_losses = sum(u.get('loss_count', 0) for u in users.values())
        total_games = total_wins + total_losses
        
        msg = f"""
📊 *BOT STATISTICS DASHBOARD*
━━━━━━━━━━━━━━━━━━━━━━

👥 *USERS*
├─ Total Users: {total_users}
├─ Daily Active: {daily_active}
└─ Active VIP: {active_vip}

💳 *PAYMENTS*
├─ Total: {total_payments}
└─ Pending: {pending_payments}

🎮 *GAMES*
├─ Total Games: {total_games}
├─ Total Wins: {total_wins}
└─ Total Losses: {total_losses}

━━━━━━━━━━━━━━━━━━━━━━
📈 *WIN RATE*
{total_wins/total_games*100:.1f}% if total_games > 0 else 'N/A'
"""
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Bot stats error: {e}")

# ==========================================
# ⭐ BOT VOICE COMMANDS (Text-based for now)
# ==========================================
async def voice_handler(update, context):
    try:
        if update.message.voice:
            await update.message.reply_text(
                "🎤 *VOICE COMMAND RECEIVED!*\n━━━━━━━━━━━━━━━━━━━━━━\nVoice commands are currently in text mode.\n\n💡 Please type your command instead.\n\n📝 Available commands:\n/play - Start playing\n/profile - View profile\n/leaderboard - View rankings",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Voice handler error: {e}")

# ==========================================
# ⭐ AUTO-BACKUP SYSTEM
# ==========================================
async def auto_backup():
    while True:
        try:
            await asyncio.sleep(86400)  # 24 hours
            
            # Create backup
            backup_data = {
                'users': users,
                'vip': vip,
                'pay': pay,
                'history': history,
                'timestamp': datetime.now().isoformat()
            }
            
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=4)
            
            # Keep only last 7 backups
            backups = sorted([f for f in os.listdir() if f.startswith('backup_')])
            while len(backups) > 7:
                os.remove(backups[0])
                backups.pop(0)
            
            logger.info(f"✅ Auto-backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Auto-backup error: {e}")

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

# ============================================================
# ⭐ CHAIN PATTERN ALGORITHM - HIDDEN (Player ko nahi dikhega)
# ============================================================

# SESSION DATA
DAY_RESULTS = [
    5,9,6,2,4,6,0,2,0,2,
    1,3,7,3,3,8,2,7,1,1,
    4,0,2,2,7,0,9,2,0,1,
    1,7,4,5,2,3,3,6,8,5,
    3,5,0,6,9,0,1,7,6,2,
    4,6,0,0,9,7,1,9,1,9,
    4,1,6,6,6,4,6,3,4,4,
    5,2,3,1,7,9,7,2,3,4,
    5,4,5,2,6,7,2,6,5,5,
    8,9,1,6,9,9,7,9,6
]

EVENING_RESULTS = [
    2,0,8,5,9,0,9,0,5,9,
    8,1,3,8,8,5,4,7,2,2,
    7,8,1,7,5,3,4,1,2,7,
    0,8,6,3,6,7,4,2,0,3,
    4
]

NIGHT_RESULTS = [
    7,7,2,2,1,4,4,8,8,9,
    1,9,4,3,4,9,6,0,6,2,
    7,4,7,6,9,1,8,2,2,5,
    6,8,5
]

def classify_chain(number):
    try:
        number = int(number)
    except (ValueError, TypeError):
        return "INVALID"
    if 0 <= number <= 4:
        return "SMALL"
    if 5 <= number <= 9:
        return "BIG"
    return "INVALID"

def find_patterns(results, current, depth=4):
    current = int(current)
    patterns = []
    for i in range(len(results)):
        if results[i] != current:
            continue
        end = i + depth
        if end <= len(results):
            chain = results[i:end]
            patterns.append(chain)
    return patterns

def get_next_numbers(results, current):
    current = int(current)
    next_numbers = []
    for i in range(len(results) - 1):
        if results[i] == current:
            next_numbers.append(results[i + 1])
    return next_numbers

def rank_candidates(results, current):
    next_numbers = get_next_numbers(results, current)
    frequency = {}
    for number in next_numbers:
        frequency[number] = frequency.get(number, 0) + 1
    ranked = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
    return ranked

def format_chain(chain):
    return "-".join(str(number) for number in chain)

def analyze_current(results, current, depth=4):
    current = int(current)
    patterns = find_patterns(results, current, depth)
    ranked = rank_candidates(results, current)
    candidates = []
    for number, frequency in ranked:
        candidates.append({
            "number": number,
            "frequency": frequency,
            "size": classify_chain(number)
        })
    return {
        "current": current,
        "current_size": classify_chain(current),
        "patterns": [format_chain(pattern) for pattern in patterns],
        "candidates": candidates
    }

SESSIONS = {
    "DAY": DAY_RESULTS,
    "EVENING": EVENING_RESULTS,
    "NIGHT": NIGHT_RESULTS
}

def get_session(session):
    session = session.upper()
    if session not in SESSIONS:
        raise ValueError("Session must be DAY, EVENING or NIGHT")
    return SESSIONS[session]

def run_algorithm(session, current):
    results = get_session(session)
    return analyze_current(results, current, depth=4)

def get_algorithm_prediction(current_number):
    """Background mein run hota hai - Player ko nahi dikhta - Sirf Admin"""
    try:
        session = "DAY"
        result = run_algorithm(session, current_number)
        if result["candidates"]:
            top = result["candidates"][0]
            return {
                "prediction": top["size"],
                "number": top["number"],
                "frequency": top["frequency"],
                "confidence": f"{min(top['frequency'] * 20, 95)}%",
                "patterns": result["patterns"][:5],
                "candidates": result["candidates"][:5]
            }
    except Exception as e:
        logger.error(f"Algorithm error: {e}")
    return {
        "prediction": "BALANCED",
        "number": "N/A",
        "frequency": 0,
        "confidence": "50%",
        "patterns": [],
        "candidates": []
    }

# ==========================================
# ⭐ AURA EVOLUTION RANK SYSTEM - SIRF TOTAL PLAYS KE HISAB SE
# ==========================================

AURA_RANKS = [
    {"level": 0, "emoji": "😅", "rank": "BEGINNER", "tagline": "🔰 First Step", "required": 5},
    {"level": 1, "emoji": "🙂", "rank": "STARTER", "tagline": "🌱 Getting Started", "required": 15},
    {"level": 2, "emoji": "😎", "rank": "PLAYER", "tagline": "⚡ Active Mode", "required": 30},
    {"level": 3, "emoji": "😏", "rank": "RISING", "tagline": "📈 Level Up", "required": 50},
    {"level": 4, "emoji": "🧐", "rank": "PRO", "tagline": "🎯 Focus Mode", "required": 75},
    {"level": 5, "emoji": "🥶", "rank": "ELITE", "tagline": "💎 Cold Skill", "required": 120},
    {"level": 6, "emoji": "😈", "rank": "MASTER", "tagline": "🔥 Dominance", "required": 180},
    {"level": 7, "emoji": "👿", "rank": "APEX PRO", "tagline": "⚡ High Power", "required": 250},
    {"level": 8, "emoji": "🤬", "rank": "ELITE FORCE", "tagline": "💥 Unstoppable", "required": 350},
    {"level": 9, "emoji": "🌀", "rank": "AURA RISING", "tagline": "🌌 Aura Awakening", "required": 500},
    {"level": 10, "emoji": "👁️", "rank": "AURA PRO", "tagline": "⚡ Aura Control", "required": 700},
    {"level": 11, "emoji": "🐲", "rank": "AURA ELITE", "tagline": "💎 Elite Aura", "required": 1000},
    {"level": 12, "emoji": "☠️", "rank": "AURA MASTER", "tagline": "💀 Dark Power", "required": 1500},
    {"level": 13, "emoji": "👹", "rank": "AURA X", "tagline": "🌑 Extreme Aura", "required": 2500},
    {"level": 14, "emoji": "👑☠️", "rank": "AURA ASCENDANT", "tagline": "🚀 BEYOND LEVEL", "required": 5000},
]

def get_aura_rank(total_plays):
    """Rank based on total plays only"""
    for rank_data in reversed(AURA_RANKS):
        if total_plays >= rank_data["required"]:
            return rank_data
    return AURA_RANKS[0]

def get_next_rank(total_plays):
    """Next rank based on total plays"""
    for rank_data in AURA_RANKS:
        if total_plays < rank_data["required"]:
            return rank_data
    return None

def get_rank_progress(total_plays):
    """Calculate progress to next rank based on total plays only"""
    current = get_aura_rank(total_plays)
    next_rank = get_next_rank(total_plays)
    
    if not next_rank:
        return {
            "current": current,
            "next": None,
            "done": total_plays,
            "required": current["required"],
            "percent": 100,
            "remaining": 0,
            "is_max": True
        }
    
    required = next_rank["required"]
    done = min(total_plays, required)
    percent = min(int((done / required) * 100), 100)
    remaining = max(required - done, 0)
    
    return {
        "current": current,
        "next": next_rank,
        "done": done,
        "required": required,
        "percent": percent,
        "remaining": remaining,
        "is_max": False
    }

def format_progress_bar(percent, length=12):
    filled = int((percent / 100) * length)
    empty = length - filled
    return "█" * filled + "░" * empty

# ==========================================
# ⭐ FAKE USERS DATA (Player ko nahi pata chalega)
# ==========================================

FAKE_USERS = [
    {"name": "Rajesh Kumar", "username": "rajesh_kumar", "win": 145, "loss": 92},
    {"name": "Priya Sharma", "username": "priya_sharma", "win": 138, "loss": 85},
    {"name": "Amit Singh", "username": "amit_singh", "win": 152, "loss": 90},
    {"name": "Sneha Patel", "username": "sneha_patel", "win": 130, "loss": 82},
    {"name": "Vikram Reddy", "username": "vikram_reddy", "win": 128, "loss": 78},
    {"name": "Ananya Gupta", "username": "ananya_gupta", "win": 122, "loss": 75},
    {"name": "Deepak Verma", "username": "deepak_verma", "win": 160, "loss": 95},
    {"name": "Kavya Nair", "username": "kavya_nair", "win": 118, "loss": 72},
    {"name": "Arjun Mehta", "username": "arjun_mehta", "win": 142, "loss": 88},
    {"name": "Meera Iyer", "username": "meera_iyer", "win": 135, "loss": 80},
    {"name": "Rahul Joshi", "username": "rahul_joshi", "win": 115, "loss": 70},
    {"name": "Pooja Desai", "username": "pooja_desai", "win": 125, "loss": 78},
    {"name": "Suresh Rao", "username": "suresh_rao", "win": 148, "loss": 92},
    {"name": "Divya Kaur", "username": "divya_kaur", "win": 120, "loss": 74},
    {"name": "Manoj Tiwari", "username": "manoj_tiwari", "win": 155, "loss": 98},
]

FAKE_TIMESTAMPS = [
    "2026-08-19 00:15:23", "2026-08-19 00:32:45", "2026-08-18 23:45:12",
    "2026-08-18 23:12:34", "2026-08-18 22:30:56", "2026-08-18 22:05:18",
    "2026-08-18 21:40:42", "2026-08-18 21:15:30", "2026-08-18 20:50:15",
    "2026-08-18 20:25:08", "2026-08-18 20:00:00", "2026-08-18 19:35:22",
    "2026-08-18 19:10:45", "2026-08-18 18:45:33", "2026-08-18 18:20:14",
]

def initialize_fake_users():
    """Add fake users - Player ko pata nahi chalega"""
    global users
    users = load("users.json")
    
    fake_added = 0
    for fake in FAKE_USERS:
        username = fake["username"]
        exists = False
        for uid, user_data in users.items():
            if user_data.get("username") == username:
                exists = True
                break
        
        if not exists:
            total_plays = fake["win"] + fake["loss"]
            rank_data = get_aura_rank(total_plays)
            
            fake_id = f"user_{username}"
            users[fake_id] = {
                "id": fake_id,
                "name": fake["name"],
                "username": fake["username"],
                "joined": str(datetime.now() - timedelta(days=random.randint(1, 30))),
                "win_count": fake["win"],
                "loss_count": fake["loss"],
                "level": rank_data["level"],
                "device_id": f"dev_{random.randint(1000,9999)}",
                "ip_address": f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
                "free_trial_used": False,
                "free_trial_expiry": None,
                "is_fake": True,
                "last_active": random.choice(FAKE_TIMESTAMPS)
            }
            fake_added += 1
    
    if fake_added > 0:
        save("users.json", users)
        logger.info(f"✅ Added {fake_added} users")

def get_real_users_count():
    """Get count of real users (non-fake)"""
    global users
    users = load("users.json")
    
    real_count = 0
    for uid, user_data in users.items():
        if not user_data.get("is_fake", False):
            real_count += 1
    return real_count

def should_show_fake_users():
    """Check if fake users should still be shown"""
    real_count = get_real_users_count()
    return real_count < 15

def get_leaderboard_users():
    """Get users for leaderboard - Fake users completely hidden"""
    global users
    users = load("users.json")
    
    all_users = []
    show_fake = should_show_fake_users()
    
    for user_id, user_data in users.items():
        is_fake = user_data.get("is_fake", False)
        
        if is_fake and not show_fake:
            continue
        
        total_plays = user_data.get('win_count', 0) + user_data.get('loss_count', 0)
        if total_plays > 0:
            rank_data = get_aura_rank(total_plays)
            
            username = user_data.get('username', 'Unknown')
            if username.startswith('fake_'):
                username = user_data.get('name', 'Player')
            
            all_users.append({
                "id": user_id,
                "name": user_data.get('name', 'Unknown'),
                "username": username,
                "win": user_data.get('win_count', 0),
                "loss": user_data.get('loss_count', 0),
                "total": total_plays,
                "rank_emoji": rank_data["emoji"],
                "rank_name": rank_data["rank"],
                "is_fake": is_fake,
                "last_active": user_data.get('last_active', '')
            })
    
    all_users.sort(key=lambda x: x["total"], reverse=True)
    return all_users

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
    available = [i for i in range(0, 10) if i != num1]
    num2 = random.choice(available)
    
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
# DEVICE TRACKING FUNCTIONS
# ==========================================
def get_device_id(update):
    try:
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "unknown"
        first_name = update.effective_user.first_name or "user"
        last_name = update.effective_user.last_name or ""
        raw = f"{user_id}_{username}_{first_name}_{last_name}"
        device_id = hashlib.md5(raw.encode()).hexdigest()
        return device_id
    except:
        return "unknown_device"

def get_client_ip(update):
    try:
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "unknown"
        raw = f"{user_id}_{username}"
        ip_hash = hashlib.md5(raw.encode()).hexdigest()[:12]
        return f"192.168.{ip_hash[:4]}.{ip_hash[4:8]}"
    except:
        return "unknown_ip"

def get_user_details(update):
    return {
        "user_id": str(update.effective_user.id),
        "username": update.effective_user.username or "Unknown",
        "first_name": update.effective_user.first_name or "User",
        "last_name": update.effective_user.last_name or "",
        "language_code": update.effective_user.language_code or "en",
        "ip_address": get_client_ip(update),
        "device_id": get_device_id(update)
    }

def calculate_remaining(expiry_str):
    if not expiry_str or expiry_str == 'N/A':
        return 'N/A'
    try:
        expiry = datetime.fromisoformat(expiry_str)
        remaining = (expiry - datetime.now()).total_seconds()
        if remaining > 0:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            return "Expired"
    except:
        return "N/A"

# ==========================================
# AUTO DELETE HELPER FUNCTION - 5 Seconds
# ==========================================
async def auto_delete_message(context, chat_id, message_id, delay=5):
    try:
        await asyncio.sleep(delay)
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Auto delete error: {e}")

async def send_and_auto_delete(update, context, text, delay=5, parse_mode=None, reply_markup=None):
    try:
        msg = await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        asyncio.create_task(auto_delete_message(context, update.effective_chat.id, msg.message_id, delay))
        return msg
    except Exception as e:
        logger.error(f"Send and auto delete error: {e}")
        return None

# ==========================================
# ⭐ DOPAMINE HIT - WIN/LOSS STICKERS (Simple Text)
# ==========================================

WIN_STICKERS = [
    """
🎉🎊🎉 *YOU'RE A LEGEND!* 🎉🎊🎉

🏆 MASTER WINNER! 🏆
""",
    """
🎉🎊🎉 *INCREDIBLE!* 🎉🎊🎉

👑 KING OF PREDICTIONS! 👑
""",
    """
🔥🔥🔥 *ON FIRE!* 🔥🔥🔥

⭐ EPIC WIN! ⭐
""",
    """
💎💎💎 *DIAMOND PLAYER!* 💎💎💎

🏆 CHAMPION! 🏆
""",
    """
🚀🚀🚀 *SKY HIGH!* 🚀🚀🚀

💎 LEGENDARY WIN! 💎
""",
    """
🎯🎯🎯 *BULLSEYE!* 🎯🎯🎯

🎯 PERFECT PREDICTION! 🎯
""",
    """
💪💪💪 *POWER PLAYER!* 💪💪💪

🏅 GOLD STANDARD! 🏅
""",
    """
🤩🤩🤩 *MINDBLOWING!* 🤩🤩🤩

⭐ AMAZING SKILLS! ⭐
""",
    """
🥇🥇🥇 *GOLD WINNER!* 🥇🥇🥇

💯 PERFECT SCORE! 💯
""",
    """
👑👑👑 *ROYAL VICTORY!* 👑👑👑

🎯 EXACT HIT! 🎯
""",
]

LOSS_STICKERS = [
    """
💪💪💪 *LEGEND IN MAKING!* 💪💪💪

😅 SO CLOSE! TRY AGAIN!
""",
    """
💪💪💪 *KEEP GOING!* 💪💪💪

💪 YOU GOT THIS!
""",
    """
🔄🔄🔄 *NEXT ROUND!* 🔄🔄🔄

💪 CHAMPION RISING!
""",
    """
🎯🎯🎯 *AIM HIGHER!* 🎯🎯🎯

📈 GET STRONGER!
""",
    """
📈📈📈 *GROWING!* 📈📈📈

💪 LEARNING DAILY!
""",
    """
⚡⚡⚡ *SHAKE IT OFF!* ⚡⚡⚡

🏆 COMEBACK KING!
""",
    """
🌟🌟🌟 *STILL A STAR!* 🌟🌟🌟

💪 KEEP SHINING!
""",
    """
💯💯💯 *STAY FOCUSED!* 💯💯💯

🎯 FOCUS = WIN!
""",
    """
🚀🚀🚀 *BOUNCE BACK!* 🚀🚀🚀

🔥 RISING AGAIN!
""",
    """
🏃🏃🏃 *KEEP MOVING!* 🏃🏃🏃

💪 NEVER STOP!
""",
]

def get_random_win_sticker():
    return random.choice(WIN_STICKERS)

def get_random_loss_sticker():
    return random.choice(LOSS_STICKERS)

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

# Initialize fake users on startup
initialize_fake_users()

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

async def send_typing(context, chat_id):
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except:
        pass

# ==========================================
# KEYBOARDS
# ==========================================
start_btn = ReplyKeyboardMarkup([["🚀 START"]], resize_keyboard=True)

# ⭐ MAIN MENU - Dashboard (With LEADERBOARD)
main_menu = ReplyKeyboardMarkup([
    ["💳 MEMBERSHIP", "📊 LEADERBOARD"],
    ["▶️ PLAY", "👤 PROFILE"],
    ["📞 SUPPORT", "📝 FEEDBACK"],
    ["🏠 HOME"]
], resize_keyboard=True)

admin_menu = ReplyKeyboardMarkup([
    ["📊 STATS", "💰 PAYMENTS"],
    ["📢 BROADCAST", "📅 PAYMENT HISTORY"],
    ["🛡️ DEVICE TRACKING"],
    ["🔙 BACK"]
], resize_keyboard=True)

super_admin_menu = ReplyKeyboardMarkup([
    ["📊 STATS", "💰 PAYMENTS"],
    ["📢 BROADCAST", "📅 PAYMENT HISTORY"],
    ["📋 APPROVAL LOG", "👑 ADMIN ACTIVITY"],
    ["📝 FEEDBACK LOG", "🛡️ DEVICE TRACKING"],
    ["🔙 BACK"]
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

# ⭐ PROFILE MENU - With ACHIEVEMENTS Button
profile_menu = ReplyKeyboardMarkup([
    ["🏆 ACHIEVEMENTS"],
    ["🎁 DAILY BONUS"],
    ["📜 HISTORY"],
    ["👥 REFERRAL"],
    ["🏆 WEEKLY REWARDS"],
    ["▶️ START ANALYSIS"],
    ["🏠 HOME"]
], resize_keyboard=True)

membership_menu = ReplyKeyboardMarkup([["👑 BUY ₹299"], ["❌ CANCEL VIP"], ["🔙 BACK"]], resize_keyboard=True)

# ==========================================
# BANNERS - SIMPLE TEXT (No Box/Border)
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

def get_stats_banner(win, loss, period, category, num1, num2, player_result=None, next_prediction=None):
    total_plays = win + loss
    rank_data = get_aura_rank(total_plays)
    
    banner = f"""
𝟬𝟴 — 𝗦𝗧𝗔𝗧𝗦
┌─[ 📈 𝗖/𝗧://𝗦𝗧𝗔𝗧𝗦 ]
│
├─[ 𝗦𝗘𝗦𝗦𝗜𝗢𝗡 ]
│ ├─ 🏆 𝗪𝗜𝗡   :: {win:02d}
│ ├─ ❌ 𝗟𝗢𝗦𝗦  :: {loss:02d}
│ └─ 📊 𝗧𝗢𝗧𝗔𝗟 :: {total_plays:02d}
│
├─[ 𝗥𝗔𝗡𝗞 ]
│ └─ {rank_data['emoji']} {rank_data['rank']}
│
├─[ 𝗡𝗘𝗫𝗧 ]
│ ├─ 🔢 𝗣𝗘𝗥𝗜𝗢𝗗   :: {period}
│ ├─ 📈 𝗖𝗔𝗧𝗘𝗚𝗢𝗥𝗬 :: {category}
│ └─ 📊 𝗡𝗨𝗠𝗕𝗘𝗥   :: {num1} , {num2}
│
├─[ 📤 𝗦𝗘𝗡𝗗 𝗡𝗘𝗫𝗧 𝗡𝗨𝗠𝗕𝗘𝗥 ]
│ └─ 🎯
│
└─[ 𝗖/𝗧://𝗟𝗜𝗩𝗘 ]
"""
    return banner

# ==========================================
# START FUNCTION
# ==========================================
async def start(update, context):
    try:
        uid = str(update.effective_user.id)
        if uid not in users:
            device_info = get_user_details(update)
            users[uid] = {
                "id": uid, 
                "name": update.effective_user.username or "Unknown", 
                "joined": str(datetime.now()), 
                "win_count": 0, 
                "loss_count": 0, 
                "level": 0,
                "device_id": device_info["device_id"],
                "ip_address": device_info["ip_address"],
                "free_trial_used": False,
                "free_trial_expiry": None,
                "username": device_info["username"],
                "first_name": device_info["first_name"],
                "last_name": device_info["last_name"],
                "language_code": device_info["language_code"]
            }
            save("users.json", users)
            logger.info(f"✅ New user created with device tracking: {uid}")
        
        # Check for referral
        if context.args and context.args[0].startswith('ref_'):
            await handle_referral(update, context)
            return
        
        await send_typing(context, update.effective_chat.id)
        await asyncio.sleep(0.3)
        
        await update.message.reply_text(
            "🌟 Welcome to AURA BOT!\n\nClick START to begin! 🚀",
            reply_markup=start_btn
        )
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
        await update.message.reply_text(banner, reply_markup=main_menu)
        
    except Exception as e:
        logger.error(f"Start button error: {e}")

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
        elif data.startswith("track_"):
            await device_tracking_callback(update, context)
            
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
# APPROVAL LOG
# ==========================================
async def approval_log(update, context):
    try:
        uid = int(update.effective_user.id)
        if uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Only Super Admin can view this!")
            return
        
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
# ⭐ LEADERBOARD FUNCTION
# ==========================================
async def leaderboard(update, context):
    try:
        uid = str(update.effective_user.id)
        
        all_users = get_leaderboard_users()
        
        current_user_pos = None
        current_user = None
        
        for i, user in enumerate(all_users):
            if user["id"] == uid:
                current_user_pos = i + 1
                current_user = user
                break
        
        if not current_user and uid in users:
            user_data = users[uid]
            total_plays = user_data.get('win_count', 0) + user_data.get('loss_count', 0)
            rank_data = get_aura_rank(total_plays)
            current_user = {
                "id": uid,
                "username": user_data.get('username', 'Unknown'),
                "name": user_data.get('name', 'Unknown'),
                "total": total_plays,
                "rank_emoji": rank_data["emoji"],
                "rank_name": rank_data["rank"]
            }
            current_user_pos = len(all_users) + 1
        
        msg = f"""
🏆 *AURA LEADERBOARD*
━━━━━━━━━━━━━━━━━━━━━━
"""
        
        top_10 = all_users[:10]
        medals = ["🥇", "🥈", "🥉", "04", "05", "06", "07", "08", "09", "10"]
        
        for i, user in enumerate(top_10):
            medal = medals[i] if i < len(medals) else f"{i+1:02d}"
            name = user["username"] if user["username"] != "Unknown" else user["name"]
            msg += f"""
{medal} {user['rank_emoji']} *{user['rank_name']}*
   {name} • {user['total']:,} Plays
"""
        
        msg += """
━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if current_user:
            name = current_user["username"] if current_user["username"] != "Unknown" else current_user["name"]
            rank_emoji = current_user["rank_emoji"]
            rank_name = current_user["rank_name"]
            total = current_user["total"] if current_user["total"] else 0
            
            msg += f"""
👤 *YOUR RANK*

#{current_user_pos}  {rank_emoji} *{rank_name}*
{name} • {total:,} Plays
"""
            
            if current_user_pos <= 10:
                msg += """
> 👑 *You're in the Top 10!* 🏆
> 🔥 Keep it up!
"""
            elif current_user_pos <= 25:
                msg += """
> ⚡ *You're close to the Top 10!*
> 💪 Keep pushing!
"""
            else:
                if total == 0:
                    msg += """
> 🎯 *Play your first game!*
> 💪 Start your journey today!
"""
                else:
                    remaining = current_user_pos - 10
                    msg += f"""
> ⚡ *Play {remaining} more to reach Top 10!*
> 🎯 Keep grinding!
"""
        else:
            msg += """
👤 *YOUR RANK*
> ℹ️ Play your first game to appear on the leaderboard!
"""
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
👥 *Total Players:* {len(all_users)}
💡 Click HOME to go back
"""
        
        leaderboard_menu = ReplyKeyboardMarkup([
            ["🏠 HOME"]
        ], resize_keyboard=True)
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=leaderboard_menu)
        
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        await update.message.reply_text("❌ Error loading leaderboard!", reply_markup=main_menu)

# ==========================================
# ⭐ ACHIEVEMENTS FUNCTION
# ==========================================
async def achievements(update, context):
    try:
        uid = str(update.effective_user.id)
        user = users.get(uid, {})
        
        win = user.get('win_count', 0)
        loss = user.get('loss_count', 0)
        total_plays = win + loss
        
        progress = get_rank_progress(total_plays)
        
        is_vip = False
        if uid in vip:
            exp = datetime.fromisoformat(vip[uid]['expiry'])
            if exp > datetime.now():
                is_vip = True
        
        # Get earned badges
        earned_badges = BADGE_TRACKER.get(uid, {}).get('earned', [])
        
        msg = f"""
🏆 *ACHIEVEMENTS & PROGRESSION*
━━━━━━━━━━━━━━━━━━━━━━

📍 *CURRENT RANK*
{progress['current']['emoji']} {progress['current']['rank']}
{progress['current']['tagline']}

━━━━━━━━━━━━━━━━━━━━━━
🎯 *NEXT RANK*"""

        if progress["is_max"]:
            msg += f"""
👑 *MAX LEVEL REACHED!*
🏆 YOU'RE A LEGEND!"""
        else:
            msg += f"""
{progress['next']['emoji']} {progress['next']['rank']}
{progress['next']['tagline']}

━━━━━━━━━━━━━━━━━━━━━━
📊 *PROGRESS*
{format_progress_bar(progress['percent'])}
{progress['done']} / {progress['required']} plays
⏳ {progress['remaining']} more plays needed

━━━━━━━━━━━━━━━━━━━━━━
📈 *STATS*
├─ 🏆 Wins: {win}
├─ ❌ Losses: {loss}
└─ 📊 Total: {total_plays}

━━━━━━━━━━━━━━━━━━━━━━
🏅 *BADGES UNLOCKED*
"""
        if earned_badges:
            for badge_condition in earned_badges:
                for badge_name, badge_data in BADGES.items():
                    if badge_data['condition'] == badge_condition:
                        msg += f"├─ {badge_name} - {badge_data['description']}\n"
        else:
            msg += "├─ No badges yet. Keep playing!\n"
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
💎 *VIP Status:* {'✅ ACTIVE' if is_vip else '❌ INACTIVE'}
"""
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=profile_menu)
        
    except Exception as e:
        logger.error(f"Achievements error: {e}")
        await update.message.reply_text("❌ Error loading achievements!", reply_markup=profile_menu)

# ==========================================
# DEVICE TRACKING PANEL
# ==========================================
async def device_tracking(update, context):
    try:
        uid = int(update.effective_user.id)
        
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Access Denied! Admin only.")
            return
        
        global users
        users = load("users.json")
        
        total_users = len(users)
        free_trial_users = sum(1 for u in users.values() if u.get('free_trial_used', False))
        unique_devices = len(set(u.get('device_id', '') for u in users.values() if u.get('device_id')))
        
        msg = f"""
🛡️ *DEVICE TRACKING PANEL*
━━━━━━━━━━━━━━━━━━━━━━

📊 *STATISTICS*
├─ 👥 Total Users    :: {total_users}
├─ 📱 Unique Devices :: {unique_devices}
└─ 🔒 Multi-Device   :: {total_users - unique_devices}

━━━━━━━━━━━━━━━━━━━━━━
📋 *RECENT USERS*
"""
        count = 0
        for user_id, user_data in list(users.items())[-10:]:
            username = user_data.get('username', 'Unknown')
            device_id = user_data.get('device_id', 'N/A')[:8]
            ip = user_data.get('ip_address', 'N/A')
            
            msg += f"""
👤 @{username}
├─ 🆔 {user_id}
├─ 📱 {device_id}...
└─ 🌐 {ip}
━━━━━━━━━━━━━━━━━━━━━━
"""
            count += 1
            if count >= 10:
                break
        
        if count == 0:
            msg += "📭 No users found.\n"
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
👑 *Admin:* @{update.effective_user.username}
🕐 *Last 10 users shown*

💡 *Options:*
├─ /track [user_id] - Track specific user
└─ /devices - Show all unique devices
"""
        
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 All Users", callback_data="track_all")],
            [InlineKeyboardButton("📱 Unique Devices", callback_data="track_devices")]
        ])
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=inline_keyboard)
        
    except Exception as e:
        logger.error(f"Device tracking error: {e}")
        await update.message.reply_text("❌ Error loading device tracking!", reply_markup=admin_menu)

# ==========================================
# DEVICE TRACKING CALLBACK HANDLER
# ==========================================
async def device_tracking_callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        
        uid = int(query.from_user.id)
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await query.edit_message_text("❌ Access Denied! Admin only.")
            return
        
        data = query.data
        global users
        users = load("users.json")
        
        if data == "track_all":
            msg = f"""
📊 *ALL USERS ({len(users)})*
━━━━━━━━━━━━━━━━━━━━━━
"""
            count = 0
            for user_id, user_data in list(users.items())[-20:]:
                username = user_data.get('username', 'Unknown')
                device = user_data.get('device_id', 'N/A')[:8]
                msg += f"👤 @{username} | 📱{device}...\n"
                count += 1
                if count >= 20:
                    break
            await query.edit_message_text(msg, parse_mode='Markdown')
            
        elif data == "track_devices":
            devices = {}
            for user_data in users.values():
                device_id = user_data.get('device_id', '')
                if device_id:
                    if device_id not in devices:
                        devices[device_id] = []
                    devices[device_id].append(user_data.get('username', 'Unknown'))
            
            msg = f"""
📱 *UNIQUE DEVICES ({len(devices)})*
━━━━━━━━━━━━━━━━━━━━━━
"""
            for device_id, users_list in list(devices.items())[:20]:
                msg += f"📱 {device_id[:8]}... -> {len(users_list)} users\n"
            
            await query.edit_message_text(msg, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Device tracking callback error: {e}")
        await query.edit_message_text("❌ Error!", reply_markup=admin_menu)

# ==========================================
# TRACK SPECIFIC USER
# ==========================================
async def track_user(update, context):
    try:
        uid = int(update.effective_user.id)
        
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Access Denied! Admin only.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text("""
❌ *Usage:* `/track [user_id]`

Example:
/track 123456789

💡 Get user_id from:
├─ User profile
├─ Payment requests
└─ Device tracking panel
""", parse_mode='Markdown')
            return
        
        target_user_id = args[0]
        
        global users
        users = load("users.json")
        
        if target_user_id not in users:
            await update.message.reply_text(f"❌ User `{target_user_id}` not found!", parse_mode='Markdown')
            return
        
        user_data = users[target_user_id]
        
        msg = f"""
🛡️ *USER TRACKING REPORT*
━━━━━━━━━━━━━━━━━━━━━━

👤 *USER DETAILS*
├─ 🆔 ID        :: {target_user_id}
├─ 👤 Name      :: {user_data.get('name', 'Unknown')}
├─ 📛 Username  :: @{user_data.get('username', 'Unknown')}
├─ 📅 Joined    :: {user_data.get('joined', 'Unknown')}
└─ 🌐 Language  :: {user_data.get('language_code', 'Unknown')}

━━━━━━━━━━━━━━━━━━━━━━
📱 *DEVICE INFO*
├─ 📱 Device ID :: {user_data.get('device_id', 'N/A')}
├─ 🌐 IP        :: {user_data.get('ip_address', 'N/A')}
└─ 🔒 Status    :: {'🟢 Active' if not user_data.get('blocked', False) else '🔴 Blocked'}

━━━━━━━━━━━━━━━━━━━━━━
📊 *STATS*
├─ 🏆 Wins   :: {user_data.get('win_count', 0)}
├─ ❌ Losses :: {user_data.get('loss_count', 0)}
└─ 📈 Level  :: {user_data.get('level', 0)}

━━━━━━━━━━━━━━━━━━━━━━
👑 *Admin:* @{update.effective_user.username}
🕐 *Report Time:* {datetime.now().strftime('%I:%M %p')}
"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Track user error: {e}")
        await update.message.reply_text("❌ Error tracking user!", reply_markup=admin_menu)

# ==========================================
# SHOW UNIQUE DEVICES
# ==========================================
async def show_devices(update, context):
    try:
        uid = int(update.effective_user.id)
        
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Access Denied! Admin only.")
            return
        
        global users
        users = load("users.json")
        
        devices = {}
        for user_data in users.values():
            device_id = user_data.get('device_id', '')
            if device_id:
                if device_id not in devices:
                    devices[device_id] = []
                devices[device_id].append(user_data.get('username', 'Unknown'))
        
        if not devices:
            await update.message.reply_text("📭 No devices found!")
            return
        
        msg = f"""
📱 *UNIQUE DEVICES ({len(devices)})*
━━━━━━━━━━━━━━━━━━━━━━
"""
        for device_id, users_list in list(devices.items())[:30]:
            msg += f"📱 `{device_id[:12]}...` -> {len(users_list)} users\n"
            for username in users_list[:3]:
                msg += f"   👤 @{username}\n"
            if len(users_list) > 3:
                msg += f"   ... and {len(users_list)-3} more\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Show devices error: {e}")
        await update.message.reply_text("❌ Error loading devices!", reply_markup=admin_menu)

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
# PLAY - VIP ONLY (No Free Trial)
# ==========================================
async def play(update, context):
    try:
        uid = str(update.effective_user.id)
        
        # Check VIP only - NO FREE TRIAL
        if uid not in vip:
            await update.message.reply_text(
                "❌ *VIP REQUIRED!*\n━━━━━━━━━━━━━━━━━━━━━━\n💳 Buy MEMBERSHIP to continue\n━━━━━━━━━━━━━━━━━━━━━━\n\n👇 *BUY NOW*",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup([["💳 MEMBERSHIP"], ["🏠 HOME"]], resize_keyboard=True)
            )
            return
        
        exp = datetime.fromisoformat(vip[uid]['expiry'])
        if exp <= datetime.now():
            await update.message.reply_text(
                "❌ *VIP EXPIRED!*\n━━━━━━━━━━━━━━━━━━━━━━\n⏰ Your VIP has expired\n━━━━━━━━━━━━━━━━━━━━━━\n💳 Renew now: /buy",
                parse_mode='Markdown',
                reply_markup=main_menu
            )
            return
        
        context.user_data.clear()
        
        # SAME FLOW FOR ALL - Passkey screen
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
            # DIRECT TIMER
            await update.message.reply_text(
                "📌 SELECT TIME:",
                reply_markup=timer_menu
            )
            context.user_data['waiting_timer'] = True
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
            await update.message.reply_text(
                "📌 SELECT TIME:",
                reply_markup=timer_menu
            )
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
            device_info = get_user_details(update)
            users[uid] = {"id": uid, "name": update.effective_user.username or "Unknown", "joined": str(datetime.now()), "win_count": 0, "loss_count": 0, "level": 0, "device_id": device_info["device_id"], "ip_address": device_info["ip_address"], "free_trial_used": False, "free_trial_expiry": None, "username": device_info["username"], "first_name": device_info["first_name"], "last_name": device_info["last_name"], "language_code": device_info["language_code"]}
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
# SET PERIOD - FIXED
# ==========================================
async def set_period(update, context):
    try:
        uid = str(update.effective_user.id)
        period = update.message.text.strip()
        
        if not context.user_data.get('waiting_period'):
            logger.info(f"⚠️ waiting_period is False for {uid}, but continuing...")
            context.user_data['waiting_period'] = True
        
        if len(period) == 4 and period.isdigit():
            users[uid]['last_period'] = period
            save("users.json", users)
            
            context.user_data['waiting_period'] = False
            context.user_data['waiting_result_number'] = True
            
            banner = get_result_banner()
            await update.message.reply_text(
                f"✅ Period: {period}\n\n{banner}",
                reply_markup=result_number_menu
            )
        else:
            await update.message.reply_text(
                "❌ Enter 4 digits only!\nExample: 1234",
                reply_markup=ReplyKeyboardRemove()
            )
    except Exception as e:
        logger.error(f"Set period error: {e}")
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=result_number_menu)

# ==========================================
# HANDLE RESULT NUMBER - FIXED (WITH HIDDEN ALGORITHM)
# ==========================================
async def handle_result_number(update, context):
    try:
        uid = str(update.effective_user.id)
        text = update.message.text
        
        if not context.user_data.get('waiting_result_number'):
            logger.info(f"⚠️ waiting_result_number is False for {uid}, but continuing...")
            context.user_data['waiting_result_number'] = True
        
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
            
            # ⭐ HIDDEN ALGORITHM - Background mein run (Player ko nahi dikhega)
            algo_prediction = get_algorithm_prediction(user_num)
            
            # ⭐ SIRF ADMIN KE LIYE STORE (Hidden from player)
            context.user_data['algo_prediction'] = algo_prediction
            
            # ⭐ LOG MEIN SAVE (Admin dekh sake)
            logger.info(f"🔮 Algorithm: {user_num} → {algo_prediction['prediction']} ({algo_prediction['number']})")
            
            save_result(uid, period, user_num, result_trend)
            add_result_to_algorithm(user_num)
            
            logger.info(f"✅ Added {user_num} to algorithm! Total: {len(HISTORICAL_RESULTS)}")
            
            if period not in GLOBAL_PERIOD_RESULTS:
                GLOBAL_PERIOD_RESULTS[period] = {
                    "num1": user_num, 
                    "num2": random.randint(0, 9), 
                    "trend": result_trend, 
                    "category": result_category
                }
                logger.info(f"✅ Stored GLOBAL result for period {period}: {user_num} ({result_trend})")
            else:
                logger.info(f"⚠️ Period {period} ALREADY exists in GLOBAL! Using existing: {GLOBAL_PERIOD_RESULTS[period]['num1']}")
            
            context.user_data['waiting_result_number'] = False
            
            # ⭐ PLAYER KO NORMAL FLOW DIKHAO (Algorithm hidden)
            await update.message.reply_text(
                f"✅ Result Saved!\n📊 {user_num}\n📈 {result_category}\n🔢 {period}",
                reply_markup=ReplyKeyboardRemove()
            )
            
            await process_analysis(update, context, uid, None, period)
            return
        
        await update.message.reply_text("❌ Please use the number buttons!", reply_markup=result_number_menu)
        
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
        
        context.user_data['last_analysis'] = {
            "trend": trend, 
            "num1": num1, 
            "num2": num2, 
            "period": current_period
        }
        
        pred = predict_next()
        next_prediction = f"{pred['prediction']} ({pred['confidence']})"
        
        banner = get_analysis_banner(current_period, category, num1, num2)
        await update.message.reply_text(banner, reply_markup=result_keyboard)
        context.user_data['waiting_result'] = True
        
    except Exception as e:
        logger.error(f"Process analysis error: {e}")
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=result_keyboard)

# ==========================================
# HANDLE RESULT - WITH DOPAMINE HIT + RANK UP CHECK + STREAK + CHALLENGES + BADGES
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
            
            old_total = users[uid]['win_count'] + users[uid]['loss_count']
            old_rank = get_aura_rank(old_total)
            
            if win:
                users[uid]['win_count'] += 1
                result_text = "✅ 🏆 VICTORY!"
            else:
                users[uid]['loss_count'] += 1
                result_text = "💪 😅 KEEP GOING!"
            
            new_total = users[uid]['win_count'] + users[uid]['loss_count']
            new_rank = get_aura_rank(new_total)
            
            save("users.json", users)
            
            # ⭐ Update streak
            streak = update_streak(uid, win)
            streak_bonus, streak_msg = get_streak_bonus(streak)
            if streak_bonus > 0 and win:
                users[uid]['win_count'] += streak_bonus
                save("users.json", users)
                await send_and_auto_delete(update, context, streak_msg, delay=5, parse_mode='Markdown')
            
            # ⭐ Check challenges
            completed_challenges = check_challenges(uid, win, new_total)
            for challenge in completed_challenges:
                users[uid]['win_count'] += challenge['reward']
                save("users.json", users)
                await send_and_auto_delete(update, context, f"🎯 *CHALLENGE COMPLETED!*\n{challenge['name']}\n🎁 +{challenge['reward']} Wins!", delay=5, parse_mode='Markdown')
            
            # ⭐ Check badges
            earned_badges = check_badges(uid, win, new_total)
            for badge in earned_badges:
                await send_and_auto_delete(update, context, f"🏅 *BADGE UNLOCKED!*\n{badge}", delay=5, parse_mode='Markdown')
            
            # ⭐ RANK UP CHECK - SIRF TOTAL PLAYS KE HISAB SE
            if new_rank["level"] > old_rank["level"]:
                rank_up_msg = f"""
🎉🎊🎉 *CONGRATULATIONS!* 🎉🎊🎉

{old_rank['emoji']} {old_rank['rank']}
        ⬇️⬇️⬇️
{new_rank['emoji']} {new_rank['rank']}

🔥 *YOU RANKED UP!* 🔥
{new_rank['tagline']}

💪 Keep going! Next rank at {new_rank['required'] + 5} plays
"""
                await send_and_auto_delete(update, context, rank_up_msg, delay=5, parse_mode='Markdown')
            
            # 🎯 WIN/LOSS STICKER (Auto-delete 5s)
            if win:
                win_sticker = get_random_win_sticker()
                await send_and_auto_delete(update, context, win_sticker, delay=5, parse_mode='Markdown')
            else:
                loss_sticker = get_random_loss_sticker()
                await send_and_auto_delete(update, context, loss_sticker, delay=5, parse_mode='Markdown')
            
            # ⭐ Add to history
            add_to_history(uid, period, last.get('num1'), final_choice, win)
            
            # ⭐ FIX: Dono numbers alag
            if final_choice == "BIG":
                next_num1 = random.randint(5, 9)
                available = [i for i in range(5, 10) if i != next_num1]
                if available:
                    next_num2 = random.choice(available)
                else:
                    next_num2 = random.randint(5, 9)
            else:
                next_num1 = random.randint(0, 4)
                available = [i for i in range(0, 5) if i != next_num1]
                if available:
                    next_num2 = random.choice(available)
                else:
                    next_num2 = random.randint(0, 4)
            
            next_trend = "BIG" if next_num1 >= 5 and next_num2 >= 5 else "SMALL"
            next_category = "🔴 BIG" if next_trend == "BIG" else "🔵 SMALL"
            next_period = str(int(period) + 1).zfill(4)
            
            if next_period not in GLOBAL_PERIOD_RESULTS:
                GLOBAL_PERIOD_RESULTS[next_period] = {
                    "num1": next_num1, 
                    "num2": next_num2, 
                    "trend": next_trend, 
                    "category": next_category
                }
            else:
                logger.info(f"⚠️ Period {next_period} ALREADY exists! Using existing result.")
            
            pred = predict_next()
            next_prediction = f"{pred['prediction']} ({pred['confidence']})"
            
            banner = get_stats_banner(
                users[uid]['win_count'],
                users[uid]['loss_count'],
                next_period,
                next_category,
                next_num1,
                next_num2,
                player_result=final_choice,
                next_prediction=next_prediction
            )
            
            await update.message.reply_text(f"{result_text}\n{banner}", reply_markup=result_keyboard)
            context.user_data['last_analysis'] = {
                "trend": next_trend, 
                "num1": next_num1, 
                "num2": next_num2, 
                "period": next_period
            }
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
            
            old_total = users[uid]['win_count'] + users[uid]['loss_count']
            old_rank = get_aura_rank(old_total)
            
            if win:
                users[uid]['win_count'] += 1
                result_text = "✅ 🏆 VICTORY!"
            else:
                users[uid]['loss_count'] += 1
                result_text = "💪 😅 KEEP GOING!"
            
            new_total = users[uid]['win_count'] + users[uid]['loss_count']
            new_rank = get_aura_rank(new_total)
            
            save("users.json", users)
            
            # ⭐ Update streak
            streak = update_streak(uid, win)
            streak_bonus, streak_msg = get_streak_bonus(streak)
            if streak_bonus > 0 and win:
                users[uid]['win_count'] += streak_bonus
                save("users.json", users)
                await send_and_auto_delete(update, context, streak_msg, delay=5, parse_mode='Markdown')
            
            # ⭐ Check challenges
            completed_challenges = check_challenges(uid, win, new_total)
            for challenge in completed_challenges:
                users[uid]['win_count'] += challenge['reward']
                save("users.json", users)
                await send_and_auto_delete(update, context, f"🎯 *CHALLENGE COMPLETED!*\n{challenge['name']}\n🎁 +{challenge['reward']} Wins!", delay=5, parse_mode='Markdown')
            
            # ⭐ Check badges
            earned_badges = check_badges(uid, win, new_total)
            for badge in earned_badges:
                await send_and_auto_delete(update, context, f"🏅 *BADGE UNLOCKED!*\n{badge}", delay=5, parse_mode='Markdown')
            
            # ⭐ RANK UP CHECK - SIRF TOTAL PLAYS KE HISAB SE
            if new_rank["level"] > old_rank["level"]:
                rank_up_msg = f"""
🎉🎊🎉 *CONGRATULATIONS!* 🎉🎊🎉

{old_rank['emoji']} {old_rank['rank']}
        ⬇️⬇️⬇️
{new_rank['emoji']} {new_rank['rank']}

🔥 *YOU RANKED UP!* 🔥
{new_rank['tagline']}

💪 Keep going! Next rank at {new_rank['required'] + 5} plays
"""
                await send_and_auto_delete(update, context, rank_up_msg, delay=5, parse_mode='Markdown')
            
            # 🎯 WIN/LOSS STICKER (Auto-delete 5s)
            if win:
                win_sticker = get_random_win_sticker()
                await send_and_auto_delete(update, context, win_sticker, delay=5, parse_mode='Markdown')
            else:
                loss_sticker = get_random_loss_sticker()
                await send_and_auto_delete(update, context, loss_sticker, delay=5, parse_mode='Markdown')
            
            # ⭐ Add to history
            add_to_history(uid, period, user_num, final_trend, win)
            
            # ⭐ FIX: Dono numbers alag
            if final_trend == "BIG":
                next_num1 = random.randint(5, 9)
                available = [i for i in range(5, 10) if i != next_num1]
                if available:
                    next_num2 = random.choice(available)
                else:
                    next_num2 = random.randint(5, 9)
            else:
                next_num1 = random.randint(0, 4)
                available = [i for i in range(0, 5) if i != next_num1]
                if available:
                    next_num2 = random.choice(available)
                else:
                    next_num2 = random.randint(0, 4)
            
            next_trend = "BIG" if next_num1 >= 5 and next_num2 >= 5 else "SMALL"
            next_category = "🔴 BIG" if next_trend == "BIG" else "🔵 SMALL"
            next_period = str(int(period) + 1).zfill(4)
            
            if next_period not in GLOBAL_PERIOD_RESULTS:
                GLOBAL_PERIOD_RESULTS[next_period] = {
                    "num1": next_num1, 
                    "num2": next_num2, 
                    "trend": next_trend, 
                    "category": next_category
                }
            else:
                logger.info(f"⚠️ Period {next_period} ALREADY exists! Using existing result.")
            
            pred = predict_next()
            next_prediction = f"{pred['prediction']} ({pred['confidence']})"
            
            banner = get_stats_banner(
                users[uid]['win_count'],
                users[uid]['loss_count'],
                next_period,
                next_category,
                next_num1,
                next_num2,
                player_result=final_trend,
                next_prediction=next_prediction
            )
            
            await update.message.reply_text(f"{result_text}\n{banner}", reply_markup=result_keyboard)
            context.user_data['last_analysis'] = {
                "trend": next_trend, 
                "num1": next_num1, 
                "num2": next_num2, 
                "period": next_period
            }
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
# ADMIN ALGORITHM VIEW - SIRF ADMIN KE LIYE
# ==========================================
async def admin_algorithm_view(update, context):
    """Sirf Admin/Super Admin dekh sakte hain"""
    uid = int(update.effective_user.id)
    
    if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied! Admin only.")
        return
    
    pred = context.user_data.get('algo_prediction', {})
    
    msg = f"""
🔮 *CHAIN PATTERN ALGORITHM (ADMIN ONLY)*
━━━━━━━━━━━━━━━━━━━━━━

📊 *System Status*
├─ Session: DAY
├─ Depth: 4
└─ Status: 🟢 Active

━━━━━━━━━━━━━━━━━━━━━━
📈 *Last Prediction*
"""
    
    if pred and pred.get('number') != "N/A":
        msg += f"""
├─ Current Number: {pred.get('number', 'N/A')}
├─ Prediction: {pred.get('prediction', 'N/A')}
├─ Confidence: {pred.get('confidence', '50%')}
├─ Frequency: {pred.get('frequency', 0)}x
├─ Patterns Found: {len(pred.get('patterns', []))}
└─ Candidates: {len(pred.get('candidates', []))}
"""
    else:
        msg += "├─ No predictions yet\n"
    
    msg += """
━━━━━━━━━━━━━━━━━━━━━━
👑 *Admin:* @{update.effective_user.username}
🕐 *Live Analysis*
"""
    
    await update.message.reply_text(msg, parse_mode='Markdown')

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
        
        win = user.get('win_count', 0)
        loss = user.get('loss_count', 0)
        total_plays = win + loss
        rank_data = get_aura_rank(total_plays)
        progress = get_rank_progress(total_plays)
        
        username = update.effective_user.username or "Unknown"
        first_name = update.effective_user.first_name or "User"
        
        # Get streak info
        streak = STREAK_TRACKER.get(uid, {}).get('streak', 0)
        max_streak = STREAK_TRACKER.get(uid, {}).get('max_streak', 0)
        
        banner = f"""
𝟬𝟭 — 𝗛𝗢𝗠𝗘 / 𝗪𝗘𝗟𝗖𝗢𝗠𝗘
┌─[ 🌌 𝗖/𝗧 𝗪𝗜𝗡 𝗛𝗔𝗖𝗞 ]
│
├─┬─[ 𝗦𝗬𝗦𝗧𝗘𝗠 𝗜𝗡𝗙𝗢 ]
│ ├─ 𝗨𝗦𝗘𝗥    :: @{username}
│ ├─ 𝗔𝗖𝗖𝗘𝗦𝗦  :: {'★ VIP' if is_vip else 'FREE'}
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
├─ 𝗥𝗔𝗡𝗞
│ └─ {rank_data['emoji']} {rank_data['rank']} - {rank_data['tagline']}
│
├─ 𝗣𝗥𝗢𝗚𝗥𝗘𝗦𝗦
│ ├─ Next: {progress['next']['rank'] if progress['next'] else '🏆 MAX'}
│ ├─ {progress['done']} / {progress['required']} plays
│ └─ {format_progress_bar(progress['percent'])}
│
├─ 𝗦𝗧𝗔𝗧𝗦
│ ├─ 🏆 𝗪𝗜𝗡   :: {win}
│ ├─ ❌ 𝗟𝗢𝗦𝗦  :: {loss}
│ ├─ 📊 𝗧𝗢𝗧𝗔𝗟 :: {total_plays}
│ ├─ 🔥 𝗦𝗧𝗥𝗘𝗔𝗞 :: {streak}
│ └─ 👑 𝗠𝗔𝗫 𝗦𝗧𝗥𝗘𝗔𝗞 :: {max_streak}
│
├─ 𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬
│ └─ 🔑 𝗣𝗔𝗦𝗦𝗞𝗘𝗬 :: {key_text}
│
└─[ 𝗖/𝗧://𝗣𝗥𝗢𝗙𝗜𝗟𝗘 ]

💡 Click 🏆 ACHIEVEMENTS to see full progression!
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
# ⭐⭐⭐ HANDLE BUTTONS
# ==========================================
async def handle_buttons(update, context):
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        
        if uid not in users:
            device_info = get_user_details(update)
            users[uid] = {"id": uid, "name": update.effective_user.username or "Unknown", "joined": str(datetime.now()), "win_count": 0, "loss_count": 0, "level": 0, "device_id": device_info["device_id"], "ip_address": device_info["ip_address"], "free_trial_used": False, "free_trial_expiry": None, "username": device_info["username"], "first_name": device_info["first_name"], "last_name": device_info["last_name"], "language_code": device_info["language_code"]}
            save("users.json", users)
            logger.info(f"✅ New user created: {uid}")
        
        # BACK Button
        if text == "🔙 BACK":
            context.user_data.clear()
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                kb = super_admin_menu
            elif user_id_int in ADMIN_IDS:
                kb = admin_menu
            else:
                kb = main_menu
            is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
            is_verified = context.user_data.get('verified', False)
            banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
            await update.message.reply_text(banner, reply_markup=kb)
            return
        
        # HOME Button
        if text == "🏠 HOME":
            context.user_data.clear()
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                kb = super_admin_menu
            elif user_id_int in ADMIN_IDS:
                kb = admin_menu
            else:
                kb = main_menu
            is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
            is_verified = context.user_data.get('verified', False)
            banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
            await update.message.reply_text(banner, reply_markup=kb)
            return
        
        # START Button
        if text == "🚀 START":
            await start_button(update, context)
            return
        
        # MEMBERSHIP Button
        if text in ["💳 MEMBERSHIP", "💳 Buy Membership"]:
            await buy_membership(update, context)
            return
        
        # ⭐ LEADERBOARD Button
        if text in ["📊 LEADERBOARD", "📊 Leaderboard"]:
            await leaderboard(update, context)
            return
        
        # PLAY Button
        if text in ["▶️ PLAY", "▶️ Play"]:
            await play(update, context)
            return
        
        # ⭐ PROFILE Button
        if text in ["👤 PROFILE", "👤 Profile"]:
            await profile(update, context)
            return
        
        # ⭐ ACHIEVEMENTS Button
        if text == "🏆 ACHIEVEMENTS":
            await achievements(update, context)
            return
        
        # ⭐ DAILY BONUS Button
        if text == "🎁 DAILY BONUS":
            await daily_bonus(update, context)
            return
        
        # ⭐ HISTORY Button
        if text == "📜 HISTORY":
            await show_history(update, context)
            return
        
        # ⭐ REFERRAL Button
        if text == "👥 REFERRAL":
            await referral_system(update, context)
            return
        
        # ⭐ WEEKLY REWARDS Button
        if text == "🏆 WEEKLY REWARDS":
            await weekly_rewards(update, context)
            return
        
        # SUPPORT Button
        if text in ["📞 SUPPORT", "📞 Support"]:
            await support(update, context)
            return
        
        # FEEDBACK Button
        if text == "📝 FEEDBACK":
            await feedback(update, context)
            return
        
        # STATS Button (Admin)
        if text in ["📊 STATS", "📊 Stats"]:
            await bot_stats_dashboard(update, context)
            return
        
        # PAYMENTS Button (Admin)
        if text in ["💰 PAYMENTS", "💰 Payments"]:
            await payment_status(update, context)
            return
        
        # BROADCAST Button (Admin)
        if text in ["📢 BROADCAST", "📢 Broadcast"]:
            await broadcast(update, context)
            return
        
        # PAYMENT HISTORY Button (Admin)
        if text == "📅 PAYMENT HISTORY":
            await payment_history(update, context)
            return
        
        # DEVICE TRACKING Button
        if text == "🛡️ DEVICE TRACKING":
            user_id_int = int(uid)
            if user_id_int in ADMIN_IDS or user_id_int in SUPER_ADMIN_IDS:
                await device_tracking(update, context)
            else:
                await update.message.reply_text("❌ Access Denied! Admin only.")
            return
        
        # APPROVAL LOG Button
        if text == "📋 APPROVAL LOG":
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                await approval_log(update, context)
            else:
                await update.message.reply_text("❌ Only Super Admin can view this!", reply_markup=admin_menu)
            return
        
        # ADMIN ACTIVITY Button
        if text == "👑 ADMIN ACTIVITY":
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                await admin_activity(update, context)
            else:
                await update.message.reply_text("❌ Only Super Admin can view this!", reply_markup=admin_menu)
            return
        
        # FEEDBACK LOG Button
        if text == "📝 FEEDBACK LOG":
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                await feedback_log(update, context)
            else:
                await update.message.reply_text("❌ Only Super Admin can view this!", reply_markup=admin_menu)
            return
        
        # ⭐ ALGORITHM VIEW Button (Admin)
        if text == "🔮 ALGORITHM":
            await admin_algorithm_view(update, context)
            return
        
        # CANCEL VIP Button
        if text == "❌ CANCEL VIP":
            await cancel_vip(update, context)
            return
        
        # TIMER Buttons
        if text == "⏱ TIMER":
            context.user_data['waiting_timer'] = True
            await update.message.reply_text("⏱ SELECT TIME", reply_markup=timer_menu)
            return
        
        if text in ["⏱ 30s", "⏱ 1m", "⏱ 2m", "⏱ 5m"]:
            context.user_data['waiting_timer'] = True
            await timer_select(update, context)
            return
        
        # ANALYSIS Button
        if text == "📊 ANALYSIS":
            await analysis(update, context)
            return
        
        # START ANALYSIS Button
        if text == "▶️ START ANALYSIS":
            await start_analysis(update, context)
            return
        
        # BUY Button
        if text == "👑 BUY ₹299":
            await buy_membership(update, context)
            return
        
        # Check other waiting states
        if context.user_data.get('waiting_feedback'):
            await handle_feedback(update, context)
            return
        
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
        
        # Broadcast mode
        if context.user_data.get('broadcast_mode'):
            if text.upper() == "CANCEL":
                context.user_data['broadcast_mode'] = False
                await update.message.reply_text("🏠 *Broadcast cancelled.*", parse_mode='Markdown')
                user_id_int = int(uid)
                if user_id_int in SUPER_ADMIN_IDS:
                    kb = super_admin_menu
                elif user_id_int in ADMIN_IDS:
                    kb = admin_menu
                else:
                    kb = main_menu
                is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
                is_verified = context.user_data.get('verified', False)
                banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
                await update.message.reply_text(banner, reply_markup=kb)
                return
            
            msg = text
            count = 0
            loading_msg = await update.message.reply_text("📢 *Broadcasting...*", parse_mode='Markdown')
            
            for user_id in users:
                try:
                    await context.bot.send_message(user_id, f"📢 {msg}")
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
    app.add_handler(CommandHandler("track", track_user))
    app.add_handler(CommandHandler("devices", show_devices))
    app.add_handler(CommandHandler("algo", admin_algorithm_view))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("achievements", achievements))
    app.add_handler(CommandHandler("bonus", daily_bonus))
    app.add_handler(CommandHandler("history", show_history))
    app.add_handler(CommandHandler("referral", referral_system))
    app.add_handler(CommandHandler("weekly", weekly_rewards))
    app.add_handler(CommandHandler("stats", bot_stats_dashboard))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    app.add_error_handler(error_handler)
    
    # Start auto-backup in background
    asyncio.create_task(auto_backup())
    
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    print("✅ Health check server running on port 10000!")
    print("=" * 50)
    print("🌟 AURA BOT v8.0 STARTED!")
    print("=" * 50)
    print("✅ Bot is running!")
    print(f"👑 Super Admin: {SUPER_ADMIN_IDS}")
    print(f"📌 All Admins: {ADMIN_IDS}")
    print("🛡️ Device Tracking: ENABLED")
    print("🎯 Dopamine Hit: ENABLED (Win/Loss Stickers - 5s Auto-Delete)")
    print("🔮 Chain Pattern Algorithm: ENABLED (Hidden from Players)")
    print("⏰ Auto-Delete: 5 SECONDS (All Popup Messages)")
    print("✅ Numbers Fixed: Always Different")
    print("📝 Professional Style: Simple Text - No Box/Border")
    print("🏆 Aura Evolution Rank System: ENABLED (15 Tiers - Based on Total Plays)")
    print("📊 Achievements: ENABLED (Badges System)")
    print("👥 Leaderboard: ENABLED (Top 10 + Your Rank)")
    print("🎭 Fake Users: ENABLED (Hidden from Players)")
    print("🎁 Daily Bonus: ENABLED (5-15 Free Wins per day)")
    print("🔥 Streak System: ENABLED (3,5,7,10 Win Streaks)")
    print("🎯 Challenge Mode: ENABLED (9 Challenges)")
    print("🏅 Badge System: ENABLED (10 Badges)")
    print("📜 Prediction History: ENABLED (Last 20 predictions)")
    print("👥 Referral System: ENABLED")
    print("🏆 Weekly Rewards: ENABLED (Top 10 get bonuses)")
    print("📊 Bot Stats Dashboard: ENABLED (Admin only)")
    print("💾 Auto-Backup: ENABLED (Daily)")
    print("=" * 50)
    app.run_polling()

if __name__ == "__main__":
    main()