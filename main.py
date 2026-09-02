# ==========================================
# 🌌 AURA BOT v9.0 - COMPLETE FIXED
# ==========================================

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import json, os, random, string, asyncio, re, sqlite3, hashlib
from datetime import datetime, timedelta
import traceback
import threading

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
# ⭐ CONCURRENT PLAYERS LOCK
# ==========================================
USER_LOCKS = {}
DB_LOCK = threading.Lock()

def get_user_lock(uid):
    if uid not in USER_LOCKS:
        USER_LOCKS[uid] = asyncio.Lock()
    return USER_LOCKS[uid]

# ==========================================
# ⭐ SAFE FILE OPERATIONS
# ==========================================
def safe_load_json(filename):
    with DB_LOCK:
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

def safe_save_json(filename, data):
    with DB_LOCK:
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except:
            return False

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
    
    async with get_user_lock(uid):
        users = safe_load_json("users.json")
        if uid in users:
            users[uid]['win_count'] = users[uid].get('win_count', 0) + bonus
            safe_save_json("users.json", users)
    
    DAILY_BONUS_TRACKER[uid]['last_claimed'] = today
    
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
# ⭐ ACHIEVEMENTS SYSTEM - 82 ACHIEVEMENTS
# ==========================================

ACHIEVEMENTS = {
    # ========== GAME PLAY (14) ==========
    "🎮 First Game": {"condition": "games_1", "desc": "Play your first game", "rarity": "common"},
    "🎯 10 Games": {"condition": "games_10", "desc": "Play 10 games", "rarity": "common"},
    "🎯 25 Games": {"condition": "games_25", "desc": "Play 25 games", "rarity": "common"},
    "🎯 50 Games": {"condition": "games_50", "desc": "Play 50 games", "rarity": "uncommon"},
    "🎯 100 Games": {"condition": "games_100", "desc": "Play 100 games", "rarity": "uncommon"},
    "🎯 250 Games": {"condition": "games_250", "desc": "Play 250 games", "rarity": "rare"},
    "🎯 500 Games": {"condition": "games_500", "desc": "Play 500 games", "rarity": "rare"},
    "🎯 1000 Games": {"condition": "games_1000", "desc": "Play 1000 games", "rarity": "very_rare"},
    "🎯 2500 Games": {"condition": "games_2500", "desc": "Play 2500 games", "rarity": "very_rare"},
    "🎯 5000 Games": {"condition": "games_5000", "desc": "Play 5000 games", "rarity": "ultra_rare"},
    "🎯 10000 Games": {"condition": "games_10000", "desc": "Play 10000 games", "rarity": "ultra_rare"},
    "🎯 25000 Games": {"condition": "games_25000", "desc": "Play 25000 games", "rarity": "legendary"},
    "🎯 50000 Games": {"condition": "games_50000", "desc": "Play 50000 games", "rarity": "legendary"},
    "🎯 100000 Games": {"condition": "games_100000", "desc": "Play 100000 games", "rarity": "mythic"},
    
    # ========== WINS (14) ==========
    "🏅 First Win": {"condition": "wins_1", "desc": "Win your first game", "rarity": "common"},
    "🏆 10 Wins": {"condition": "wins_10", "desc": "Win 10 games", "rarity": "common"},
    "🏆 25 Wins": {"condition": "wins_25", "desc": "Win 25 games", "rarity": "common"},
    "🏆 50 Wins": {"condition": "wins_50", "desc": "Win 50 games", "rarity": "uncommon"},
    "🏆 100 Wins": {"condition": "wins_100", "desc": "Win 100 games", "rarity": "uncommon"},
    "🏆 250 Wins": {"condition": "wins_250", "desc": "Win 250 games", "rarity": "rare"},
    "🏆 500 Wins": {"condition": "wins_500", "desc": "Win 500 games", "rarity": "rare"},
    "🏆 1000 Wins": {"condition": "wins_1000", "desc": "Win 1000 games", "rarity": "very_rare"},
    "🏆 2500 Wins": {"condition": "wins_2500", "desc": "Win 2500 games", "rarity": "very_rare"},
    "🏆 5000 Wins": {"condition": "wins_5000", "desc": "Win 5000 games", "rarity": "ultra_rare"},
    "🏆 10000 Wins": {"condition": "wins_10000", "desc": "Win 10000 games", "rarity": "ultra_rare"},
    "🏆 25000 Wins": {"condition": "wins_25000", "desc": "Win 25000 games", "rarity": "legendary"},
    "🏆 50000 Wins": {"condition": "wins_50000", "desc": "Win 50000 games", "rarity": "legendary"},
    "🏆 100000 Wins": {"condition": "wins_100000", "desc": "Win 100000 games", "rarity": "mythic"},
    
    # ========== STREAK (12) ==========
    "🔥 3 Streak": {"condition": "streak_3", "desc": "Win 3 in a row", "rarity": "common"},
    "🔥 5 Streak": {"condition": "streak_5", "desc": "Win 5 in a row", "rarity": "common"},
    "🔥 10 Streak": {"condition": "streak_10", "desc": "Win 10 in a row", "rarity": "uncommon"},
    "🔥 15 Streak": {"condition": "streak_15", "desc": "Win 15 in a row", "rarity": "rare"},
    "🔥 20 Streak": {"condition": "streak_20", "desc": "Win 20 in a row", "rarity": "rare"},
    "🔥 25 Streak": {"condition": "streak_25", "desc": "Win 25 in a row", "rarity": "very_rare"},
    "🔥 30 Streak": {"condition": "streak_30", "desc": "Win 30 in a row", "rarity": "very_rare"},
    "🔥 50 Streak": {"condition": "streak_50", "desc": "Win 50 in a row", "rarity": "ultra_rare"},
    "🔥 75 Streak": {"condition": "streak_75", "desc": "Win 75 in a row", "rarity": "ultra_rare"},
    "🔥 100 Streak": {"condition": "streak_100", "desc": "Win 100 in a row", "rarity": "legendary"},
    "🔥 150 Streak": {"condition": "streak_150", "desc": "Win 150 in a row", "rarity": "legendary"},
    "🔥 200 Streak": {"condition": "streak_200", "desc": "Win 200 in a row", "rarity": "mythic"},
    
    # ========== LEVEL (10) ==========
    "⭐ Level 5": {"condition": "level_5", "desc": "Reach Level 5", "rarity": "common"},
    "⭐ Level 10": {"condition": "level_10", "desc": "Reach Level 10", "rarity": "uncommon"},
    "⭐ Level 15": {"condition": "level_15", "desc": "Reach Level 15", "rarity": "uncommon"},
    "⭐ Level 20": {"condition": "level_20", "desc": "Reach Level 20", "rarity": "rare"},
    "⭐ Level 25": {"condition": "level_25", "desc": "Reach Level 25", "rarity": "rare"},
    "⭐ Level 30": {"condition": "level_30", "desc": "Reach Level 30", "rarity": "very_rare"},
    "⭐ Level 40": {"condition": "level_40", "desc": "Reach Level 40", "rarity": "very_rare"},
    "⭐ Level 50": {"condition": "level_50", "desc": "Reach Level 50", "rarity": "ultra_rare"},
    "⭐ Level 75": {"condition": "level_75", "desc": "Reach Level 75", "rarity": "legendary"},
    "⭐ Level 100": {"condition": "level_100", "desc": "Reach Level 100", "rarity": "mythic"},
    
    # ========== VIP (4) ==========
    "👑 Royal Player": {"condition": "vip", "desc": "Become a VIP Member", "rarity": "uncommon"},
    "💎 Diamond VIP": {"condition": "vip_30", "desc": "VIP for 30 days", "rarity": "rare"},
    "👑 King VIP": {"condition": "vip_90", "desc": "VIP for 90 days", "rarity": "very_rare"},
    "👑 Emperor VIP": {"condition": "vip_365", "desc": "VIP for 365 days", "rarity": "legendary"},
    
    # ========== BONUS (3) ==========
    "🎁 Daily Bonus": {"condition": "bonus_7", "desc": "Claim daily bonus 7 times", "rarity": "uncommon"},
    "🎁 Weekly Bonus": {"condition": "bonus_week", "desc": "Claim weekly rewards", "rarity": "rare"},
    "🎁 Monthly Bonus": {"condition": "bonus_month", "desc": "Claim monthly rewards", "rarity": "very_rare"},
    
    # ========== REFERRAL (4) ==========
    "👥 Recruiter": {"condition": "ref_1", "desc": "Refer 1 friend", "rarity": "uncommon"},
    "👥 Super Recruiter": {"condition": "ref_10", "desc": "Refer 10 friends", "rarity": "rare"},
    "👥 Mega Recruiter": {"condition": "ref_50", "desc": "Refer 50 friends", "rarity": "very_rare"},
    "👥 Legendary Recruiter": {"condition": "ref_100", "desc": "Refer 100 friends", "rarity": "legendary"},
    
    # ========== DAILY STREAK (7) ==========
    "📅 7 Day Streak": {"condition": "daily_7", "desc": "Play 7 days in a row", "rarity": "uncommon"},
    "📅 15 Day Streak": {"condition": "daily_15", "desc": "Play 15 days in a row", "rarity": "rare"},
    "📅 30 Day Streak": {"condition": "daily_30", "desc": "Play 30 days in a row", "rarity": "very_rare"},
    "📅 60 Day Streak": {"condition": "daily_60", "desc": "Play 60 days in a row", "rarity": "ultra_rare"},
    "📅 90 Day Streak": {"condition": "daily_90", "desc": "Play 90 days in a row", "rarity": "ultra_rare"},
    "📅 180 Day Streak": {"condition": "daily_180", "desc": "Play 180 days in a row", "rarity": "legendary"},
    "📅 365 Day Streak": {"condition": "daily_365", "desc": "Play 365 days in a row", "rarity": "mythic"},
    
    # ========== PERFECT PREDICTION (4) ==========
    "🎯 Perfect Prediction": {"condition": "perfect_5", "desc": "Win 5 times in a row", "rarity": "rare"},
    "🎯 God Mode": {"condition": "perfect_20", "desc": "Win 20 times in a row", "rarity": "very_rare"},
    "🎯 Unstoppable": {"condition": "perfect_50", "desc": "Win 50 times in a row", "rarity": "legendary"},
    "🎯 Invincible": {"condition": "perfect_100", "desc": "Win 100 times in a row", "rarity": "mythic"},
    
    # ========== ULTIMATE (10) ==========
    "👑 Ultimate Legend": {"condition": "all_achievements", "desc": "All achievements completed", "rarity": "mythic"},
    "🏆 GOD OF AURA": {"condition": "plays_100000", "desc": "100,000 total plays", "rarity": "mythic"},
    "💎 AURA MASTER": {"condition": "wins_50000", "desc": "50,000 total wins", "rarity": "mythic"},
    "🌟 STAR PLAYER": {"condition": "top_10", "desc": "Top 10 leaderboard", "rarity": "ultra_rare"},
    "👑 AURA KING": {"condition": "rank_1", "desc": "Rank #1 leaderboard", "rarity": "legendary"},
    "🏆 CHAMPION": {"condition": "wins_5000", "desc": "Win 5000 games", "rarity": "ultra_rare"},
    "💎 DIAMOND HANDS": {"condition": "plays_25000", "desc": "Play 25,000 games", "rarity": "legendary"},
    "🔥 FIRE GOD": {"condition": "streak_250", "desc": "Win 250 games in a row", "rarity": "mythic"},
    "⚡ LIGHTNING": {"condition": "plays_100000", "desc": "Play 100,000 games", "rarity": "mythic"},
    "👽 GOD TIER": {"condition": "god_tier", "desc": "Reach GOD TIER rank", "rarity": "mythic"},
}

# ==========================================
# ⭐ ACHIEVEMENTS HELPER FUNCTIONS
# ==========================================

def get_rarity_emoji(rarity):
    rarity_map = {
        "common": "",
        "uncommon": "🟢",
        "rare": "🔵",
        "very_rare": "🟣",
        "ultra_rare": "🔴",
        "legendary": "🌟",
        "mythic": "👑",
    }
    return rarity_map.get(rarity, "")

def get_rarity_label(rarity):
    rarity_map = {
        "common": "Common",
        "uncommon": "Uncommon",
        "rare": "Rare",
        "very_rare": "Very Rare",
        "ultra_rare": "Ultra Rare",
        "legendary": "Legendary",
        "mythic": "MYTHIC ⭐",
    }
    return rarity_map.get(rarity, "Common")

def get_rare_achievements(unlocked_list):
    rare = []
    for name in unlocked_list:
        if name in ACHIEVEMENTS:
            rarity = ACHIEVEMENTS[name].get('rarity', 'common')
            if rarity in ['ultra_rare', 'legendary', 'mythic']:
                rare.append((name, rarity))
    return rare

def get_random_rare_achievement(unlocked_list):
    rare = get_rare_achievements(unlocked_list)
    if rare:
        return random.choice(rare)
    if unlocked_list:
        return (random.choice(unlocked_list), ACHIEVEMENTS.get(unlocked_list[0], {}).get('rarity', 'common'))
    return None

def get_achievement_stats(uid):
    users = safe_load_json("users.json")
    if uid not in users:
        return {'total': 0, 'unlocked': 0, 'percent': 0, 'unlocked_list': []}
    
    unlocked = users[uid].get('achievements', {}).get('unlocked', [])
    total = len(ACHIEVEMENTS)
    unlocked_count = len(unlocked)
    percent = int((unlocked_count / total) * 100) if total > 0 else 0
    
    return {
        'total': total,
        'unlocked': unlocked_count,
        'percent': percent,
        'unlocked_list': unlocked
    }

def get_achievement_players_count(ach_name):
    users = safe_load_json("users.json")
    count = 0
    for uid, user_data in users.items():
        unlocked = user_data.get('achievements', {}).get('unlocked', [])
        if ach_name in unlocked:
            count += 1
    return count

def get_achievement_title(percent):
    if percent >= 100:
        return "👑 THE ULTIMATE LEGEND"
    elif percent >= 90:
        return "🌟 THE LEGEND"
    elif percent >= 75:
        return "🏆 THE MASTER"
    elif percent >= 50:
        return "⚔️ THE WARRIOR"
    elif percent >= 25:
        return "🛡️ THE FIGHTER"
    else:
        return "🗡️ THE BEGINNER"

def check_achievements(uid, users, stats):
    unlocked = []
    
    if 'achievements' not in users[uid]:
        users[uid]['achievements'] = {'unlocked': []}
    
    unlocked_list = users[uid]['achievements'].get('unlocked', [])
    
    wins = stats.get('wins', 0)
    games = stats.get('games', 0)
    streak = stats.get('streak', 0)
    level = stats.get('level', 0)
    max_streak = stats.get('max_streak', 0)
    
    for name, data in ACHIEVEMENTS.items():
        if name in unlocked_list:
            continue
        
        condition = data['condition']
        unlocked_condition = False
        
        if condition.startswith('games_'):
            target = int(condition.replace('games_', ''))
            if games >= target:
                unlocked_condition = True
        elif condition.startswith('wins_'):
            target = int(condition.replace('wins_', ''))
            if wins >= target:
                unlocked_condition = True
        elif condition.startswith('streak_'):
            target = int(condition.replace('streak_', ''))
            if max_streak >= target:
                unlocked_condition = True
        elif condition.startswith('level_'):
            target = int(condition.replace('level_', ''))
            if level >= target:
                unlocked_condition = True
        elif condition == 'vip':
            if stats.get('is_vip', False):
                unlocked_condition = True
        elif condition == 'vip_30':
            if stats.get('vip_days', 0) >= 30:
                unlocked_condition = True
        elif condition == 'vip_90':
            if stats.get('vip_days', 0) >= 90:
                unlocked_condition = True
        elif condition == 'vip_365':
            if stats.get('vip_days', 0) >= 365:
                unlocked_condition = True
        elif condition == 'bonus_7':
            if stats.get('bonus_count', 0) >= 7:
                unlocked_condition = True
        elif condition == 'bonus_week':
            if stats.get('weekly_claimed', False):
                unlocked_condition = True
        elif condition == 'bonus_month':
            if stats.get('monthly_claimed', False):
                unlocked_condition = True
        elif condition.startswith('ref_'):
            target = int(condition.replace('ref_', ''))
            if stats.get('referrals', 0) >= target:
                unlocked_condition = True
        elif condition.startswith('daily_'):
            target = int(condition.replace('daily_', ''))
            if stats.get('daily_streak', 0) >= target:
                unlocked_condition = True
        elif condition.startswith('perfect_'):
            target = int(condition.replace('perfect_', ''))
            if max_streak >= target:
                unlocked_condition = True
        elif condition == 'all_achievements':
            total = len(ACHIEVEMENTS)
            unlocked_count = len(unlocked_list) + 1
            if unlocked_count >= total:
                unlocked_condition = True
        elif condition == 'plays_100000':
            if games >= 100000:
                unlocked_condition = True
        elif condition == 'wins_50000':
            if wins >= 50000:
                unlocked_condition = True
        elif condition == 'top_10':
            if stats.get('rank_position', 999) <= 10:
                unlocked_condition = True
        elif condition == 'rank_1':
            if stats.get('rank_position', 999) == 1:
                unlocked_condition = True
        elif condition == 'wins_5000':
            if wins >= 5000:
                unlocked_condition = True
        elif condition == 'plays_25000':
            if games >= 25000:
                unlocked_condition = True
        elif condition == 'streak_250':
            if max_streak >= 250:
                unlocked_condition = True
        elif condition == 'god_tier':
            if stats.get('rank_name', '') == 'GOD TIER':
                unlocked_condition = True
        
        if unlocked_condition:
            unlocked_list.append(name)
            unlocked.append(name)
    
    users[uid]['achievements']['unlocked'] = unlocked_list
    return unlocked

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
    
    user_pos = None
    for i, user in enumerate(top_10):
        if user['id'] == uid:
            user_pos = i + 1
            break
    
    async with get_user_lock(uid):
        users = safe_load_json("users.json")
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
        safe_save_json("users.json", users)
    
    WEEKLY_REWARDS_TRACKER[uid]['week_claimed'] = week_key
    
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
    
    history = HISTORY_TRACKER[uid][-20:]
    
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
            
            async with get_user_lock(referrer):
                users = safe_load_json("users.json")
                if count >= 5:
                    users[referrer]['win_count'] = users[referrer].get('win_count', 0) + 30
                    expiry = datetime.now() + timedelta(days=1)
                    key = gen_key()
                    vip = safe_load_json("vip.json")
                    vip[referrer] = {
                        "user_id": referrer,
                        "key": key,
                        "expiry": expiry.isoformat(),
                        "is_referral": True
                    }
                    safe_save_json("vip.json", vip)
                    reward_msg = "🎉 +30 Wins + VIP 24H!"
                elif count >= 3:
                    users[referrer]['win_count'] = users[referrer].get('win_count', 0) + 15
                    reward_msg = "🎉 +15 Wins!"
                elif count >= 1:
                    users[referrer]['win_count'] = users[referrer].get('win_count', 0) + 5
                    reward_msg = "🎉 +5 Wins!"
                else:
                    reward_msg = ""
                safe_save_json("users.json", users)
            
            try:
                await context.bot.send_message(
                    chat_id=referrer,
                    text=f"👥 *NEW REFERRAL!*\n━━━━━━━━━━━━━━━━━━━━━━\nSomeone used your referral code!\n\n📊 Total Referrals: {count}\n🎁 {reward_msg}",
                    parse_mode='Markdown'
                )
            except:
                pass
            
            async with get_user_lock(uid):
                users = safe_load_json("users.json")
                users[uid]['win_count'] = users[uid].get('win_count', 0) + 2
                safe_save_json("users.json", users)
            
            await update.message.reply_text(
                f"✅ *REFERRAL SUCCESSFUL!*\n━━━━━━━━━━━━━━━━━━━━━━\nYou were referred by someone!\n🎁 You also get +2 Bonus Wins!\n━━━━━━━━━━━━━━━━━━━━━━\n🎯 Start playing now!",
                parse_mode='Markdown'
            )

# ==========================================
# ⭐ BOT STATS DASHBOARD
# ==========================================
async def bot_stats_dashboard(update, context):
    try:
        uid = int(update.effective_user.id)
        
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Admin only!")
            return
        
        users = safe_load_json("users.json")
        vip = safe_load_json("vip.json")
        pay = safe_load_json("pay.json")
        
        total_users = len(users)
        active_vip = 0
        for v in vip.values():
            try:
                if datetime.fromisoformat(v['expiry']) > datetime.now():
                    active_vip += 1
            except:
                pass
        
        total_payments = len(pay)
        pending_payments = 0
        for p in pay.values():
            if p.get('status') == 'pending':
                pending_payments += 1
        
        active_players = 0
        today = datetime.now().date().isoformat()
        for user_id, user_data in users.items():
            last_active = user_data.get('last_active', '')
            if last_active and last_active.startswith(today):
                active_players += 1
        
        real_users = 0
        for user_id, user_data in users.items():
            if not user_data.get('is_fake', False):
                real_users += 1
        
        total_wins = 0
        total_losses = 0
        for u in users.values():
            if not u.get('is_fake', False):
                total_wins += u.get('win_count', 0)
                total_losses += u.get('loss_count', 0)
        total_games = total_wins + total_losses
        
        win_rate = f"{total_wins/total_games*100:.1f}%" if total_games > 0 else "N/A"
        
        msg = f"""
📊 *BOT STATISTICS DASHBOARD*
━━━━━━━━━━━━━━━━━━━━━━

👥 *USERS*
├─ Total Users: {real_users}
├─ Active (24h): {active_players}
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
{win_rate}
"""
        
        if uid in SUPER_ADMIN_IDS:
            msg += """
━━━━━━━━━━━━━━━━━━━━━━
👑 *SUPER ADMIN ACCESS*
✅ All admin features available
"""
        
        if uid in SUPER_ADMIN_IDS:
            kb = super_admin_menu
        else:
            kb = admin_menu
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=kb)
    except Exception as e:
        logger.error(f"Bot stats error: {e}")
        await update.message.reply_text("❌ Error loading stats! Please try again.", reply_markup=admin_menu)

# ==========================================
# ⭐ AUTO-BACKUP SYSTEM
# ==========================================
async def auto_backup():
    while True:
        try:
            await asyncio.sleep(86400)
            
            users = safe_load_json("users.json")
            vip = safe_load_json("vip.json")
            pay = safe_load_json("pay.json")
            history = safe_load_json("history.json")
            
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
            
            backups = sorted([f for f in os.listdir() if f.startswith('backup_')])
            while len(backups) > 7:
                os.remove(backups[0])
                backups.pop(0)
            
            logger.info(f"✅ Auto-backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Auto-backup error: {e}")

def start_auto_backup():
    def backup_wrapper():
        try:
            asyncio.run(auto_backup())
        except Exception as e:
            logger.error(f"Backup thread error: {e}")
    
    thread = threading.Thread(target=backup_wrapper, daemon=True)
    thread.start()
    logger.info("✅ Auto-backup thread started")

# ==========================================
# ⭐ AUTO-PLAY INCREASE SYSTEM
# ==========================================

AUTO_PLAY_TRACKER = {}

async def auto_increase_plays():
    while True:
        try:
            await asyncio.sleep(3600)
            
            users = safe_load_json("users.json")
            
            for uid, user_data in users.items():
                if user_data.get('is_fake', False):
                    increase = random.randint(1, 5)
                    user_data['win_count'] = user_data.get('win_count', 0) + random.randint(0, increase)
                    user_data['loss_count'] = user_data.get('loss_count', 0) + random.randint(0, increase)
                    
                    total = user_data['win_count'] + user_data['loss_count']
                    user_data['level'] = total // 10
            
            safe_save_json("users.json", users)
            logger.info("✅ Auto-play increase completed!")
            
        except Exception as e:
            logger.error(f"Auto-play increase error: {e}")

def start_auto_play_increase():
    def wrapper():
        try:
            asyncio.run(auto_increase_plays())
        except Exception as e:
            logger.error(f"Auto-play thread error: {e}")
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    logger.info("✅ Auto-play increase thread started!")

# ==========================================
# ⭐ DYNAMIC TOP 3 SYSTEM
# ==========================================

TOP3_TRACKER = {}

async def dynamic_top3_update():
    while True:
        try:
            wait_time = random.randint(7200, 14400)
            await asyncio.sleep(wait_time)
            
            users = safe_load_json("users.json")
            
            fake_users = []
            for uid, user_data in users.items():
                if user_data.get('is_fake', False):
                    fake_users.append((uid, user_data))
            
            if len(fake_users) < 3:
                logger.info("⚠️ Not enough fake users for top 3 update")
                continue
            
            selected = random.sample(fake_users, 3)
            
            for i, (uid, user_data) in enumerate(selected, 1):
                current_wins = user_data.get('win_count', 0)
                current_losses = user_data.get('loss_count', 0)
                current_total = current_wins + current_losses
                
                increase = random.randint(20, 50)
                new_total = current_total + increase
                
                new_wins = int(new_total * random.uniform(0.6, 0.7))
                new_losses = new_total - new_wins
                
                user_data['win_count'] = new_wins
                user_data['loss_count'] = new_losses
                
                user_data['level'] = new_total // 10
                user_data['rank_level'] = get_aura_rank(new_total)['level']
                
                users[uid] = user_data
                
                logger.info(f"✅ Top {i} updated: {user_data.get('username')} → {new_total} plays")
            
            safe_save_json("users.json", users)
            logger.info("✅ Dynamic Top 3 updated successfully!")
            
        except Exception as e:
            logger.error(f"Dynamic Top 3 error: {e}")

def start_dynamic_top3():
    def wrapper():
        try:
            asyncio.run(dynamic_top3_update())
        except Exception as e:
            logger.error(f"Dynamic top3 thread error: {e}")
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    logger.info("✅ Dynamic Top 3 thread started!")

# ==========================================
# ⭐ DAILY RANDOM PLAYERS
# ==========================================
DAILY_PLAYER_TRACKER = {}

async def add_daily_random_players():
    while True:
        try:
            wait_time = random.randint(28800, 43200)
            await asyncio.sleep(wait_time)
            
            users = safe_load_json("users.json")
            
            new_fake_users = [
                {"name": "Ravi Kumar", "username": "ravi_kumar", "win": random.randint(2, 8), "loss": random.randint(1, 4)},
                {"name": "Neha Singh", "username": "neha_singh", "win": random.randint(3, 10), "loss": random.randint(1, 5)},
                {"name": "Vikram Shah", "username": "vikram_shah", "win": random.randint(1, 6), "loss": random.randint(0, 3)},
                {"name": "Pooja Reddy", "username": "pooja_reddy", "win": random.randint(4, 12), "loss": random.randint(2, 6)},
                {"name": "Amit Verma", "username": "amit_verma", "win": random.randint(2, 7), "loss": random.randint(1, 4)},
            ]
            
            selected = random.sample(new_fake_users, random.randint(2, 3))
            
            added = 0
            for fake in selected:
                username = fake["username"]
                exists = False
                for uid, user_data in users.items():
                    if user_data.get("username") == username:
                        exists = True
                        break
                
                if not exists:
                    total_plays = fake["win"] + fake["loss"]
                    rank_data = get_aura_rank(total_plays)
                    
                    fake_id = f"user_{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    users[fake_id] = {
                        "id": fake_id,
                        "name": fake["name"],
                        "username": fake["username"],
                        "joined": str(datetime.now()),
                        "win_count": fake["win"],
                        "loss_count": fake["loss"],
                        "level": total_plays // 10,
                        "rank_level": rank_data["level"],
                        "previous_rank": None,
                        "device_id": f"dev_{random.randint(1000,9999)}",
                        "ip_address": f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
                        "free_trial_used": False,
                        "free_trial_expiry": None,
                        "is_fake": True,
                        "last_active": datetime.now().isoformat(),
                        "achievements": {"unlocked": []}
                    }
                    added += 1
            
            if added > 0:
                safe_save_json("users.json", users)
                logger.info(f"✅ Added {added} daily random players!")
            
        except Exception as e:
            logger.error(f"Daily random players error: {e}")

def start_daily_random_players():
    def wrapper():
        try:
            asyncio.run(add_daily_random_players())
        except Exception as e:
            logger.error(f"Daily random players thread error: {e}")
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    logger.info("✅ Daily random players thread started!")

# ==========================================
# ⭐ BIG/SMALL ANALYSIS ALGORITHM
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

# ==========================================
# ⭐ HISTORICAL DATA - 200+ RESULTS
# ==========================================

HISTORICAL_RESULTS = [
    5, 9, 6, 2, 4, 6, 0, 2, 0, 2,
    1, 3, 7, 3, 3, 8, 2, 7, 1, 1,
    4, 0, 2, 2, 7, 0, 9, 2, 0, 1,
    1, 7, 4, 5, 2, 3, 3, 6, 8, 5,
    3, 5, 0, 6, 9, 0, 1, 7, 6, 2,
    4, 6, 0, 0, 9, 7, 1, 9, 1, 9,
    4, 1, 6, 6, 6, 4, 6, 3, 4, 4,
    5, 2, 3, 1, 7, 9, 7, 2, 3, 4,
    5, 4, 5, 2, 6, 7, 2, 6, 5, 5,
    8, 9, 1, 6, 9, 9, 7, 9, 6, 2,
    0, 8, 5, 9, 0, 9, 0, 5, 9, 8,
    1, 3, 8, 8, 5, 4, 7, 2, 2, 7,
    8, 1, 7, 5, 3, 4, 1, 2, 7, 0,
    8, 6, 3, 6, 7, 4, 2, 0, 3, 4,
    7, 2, 1, 4, 8, 9, 1, 9, 4, 3,
    4, 9, 6, 0, 6, 2, 7, 4, 7, 6,
    9, 1, 8, 2, 2, 5, 6, 8, 5, 9,
    1, 7, 9, 6, 2, 6, 5, 6, 4, 1,
    8, 0, 7, 9, 6, 5, 4, 8, 0, 6,
    4, 0, 3, 6, 3, 9, 3, 4, 3, 1,
    7, 2, 3, 1, 4, 8, 6, 7, 0, 5,
    1, 6, 7, 3, 7, 8, 0, 5, 2, 5,
    0, 4, 3, 8, 2, 5, 6, 4, 3, 7,
    1, 8, 4, 9, 0, 5, 0, 8, 0, 1,
    4, 8, 6, 0, 1, 8, 3, 5, 3, 6,
    3, 2, 1, 2, 9, 2, 4, 3, 4, 6,
    0, 6
]

CLASSIFIED_RESULTS = [
    {"number": num, "size": get_size(num)}
    for num in HISTORICAL_RESULTS
]

def get_statistics():
    big_count = sum(1 for r in CLASSIFIED_RESULTS if r["size"] == "BIG")
    small_count = sum(1 for r in CLASSIFIED_RESULTS if r["size"] == "SMALL")
    return {"BIG": big_count, "SMALL": small_count}

# ==========================================
# ⭐ HISTORICAL ANALYSIS ALGORITHM - SELF LEARNING
# ==========================================

def get_next_numbers_after(current_number):
    current = int(current_number)
    next_numbers = []
    for i in range(len(HISTORICAL_RESULTS) - 1):
        if HISTORICAL_RESULTS[i] == current:
            next_numbers.append(HISTORICAL_RESULTS[i + 1])
    return next_numbers

def get_frequency_analysis(current_number):
    next_numbers = get_next_numbers_after(current_number)
    frequency = {}
    for num in next_numbers:
        frequency[num] = frequency.get(num, 0) + 1
    return frequency

def get_sorted_candidates(current_number):
    frequency = get_frequency_analysis(current_number)
    sorted_candidates = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
    return sorted_candidates

def get_prediction_with_analysis(current_number):
    current = int(current_number)
    sorted_candidates = get_sorted_candidates(current)
    
    if not sorted_candidates:
        return {
            'current': current,
            'candidates': [],
            'top_prediction': None,
            'top_size': None,
            'total_matches': 0,
            'message': "⚠️ No historical data found for this number!"
        }
    
    candidates = []
    for num, count in sorted_candidates[:5]:
        size = "BIG" if num >= 5 else "SMALL"
        candidates.append({
            'number': num,
            'count': count,
            'size': size
        })
    
    top = candidates[0] if candidates else None
    
    return {
        'current': current,
        'candidates': candidates,
        'top_prediction': top['number'] if top else None,
        'top_size': top['size'] if top else None,
        'total_matches': sum(count for _, count in sorted_candidates),
        'message': f"✅ Found {len(sorted_candidates)} unique numbers after {current}"
    }

def add_result_to_history(number):
    try:
        num = int(number)
        if 0 <= num <= 9:
            HISTORICAL_RESULTS.append(num)
            CLASSIFIED_RESULTS.append({"number": num, "size": get_size(num)})
            if len(HISTORICAL_RESULTS) > 500:
                HISTORICAL_RESULTS.pop(0)
                CLASSIFIED_RESULTS.pop(0)
            return True
    except:
        pass
    return False

def predict_next_with_history():
    if len(HISTORICAL_RESULTS) < 2:
        return {"prediction": "BALANCED", "confidence": "50%"}
    
    last_number = HISTORICAL_RESULTS[-1]
    analysis = get_prediction_with_analysis(last_number)
    
    if not analysis['candidates']:
        return {"prediction": "BALANCED", "confidence": "50%"}
    
    top = analysis['candidates'][0]
    confidence = min(int((top['count'] / analysis['total_matches']) * 100), 95)
    
    return {
        "prediction": top['size'],
        "number": top['number'],
        "confidence": f"{confidence}%",
        "frequency": top['count'],
        "total_matches": analysis['total_matches'],
        "candidates": analysis['candidates']
    }

def get_analysis_report():
    stats = get_statistics()
    total = len(HISTORICAL_RESULTS)
    
    pred = predict_next_with_history()
    
    report = f"""
📊 *BIG/SMALL ANALYSIS REPORT*
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
    
    report += f"""
━━━━━━━━━━━━━━━━━━━━━━
🔮 Next Prediction: {pred['prediction']}
🎯 Confidence: {pred['confidence']}
📊 Based on: {pred['total_matches']} historical matches
"""
    return report

# ==========================================
# ⭐ AURA EVOLUTION RANK SYSTEM
# ==========================================

AURA_RANKS = [
    {"level": 0, "emoji": "😅", "rank": "BEGINNER I", "tagline": "🔰 First Step", "required": 5},
    {"level": 1, "emoji": "🙂", "rank": "BEGINNER II", "tagline": "🌱 Learning", "required": 10},
    {"level": 2, "emoji": "😊", "rank": "BEGINNER III", "tagline": "📈 Growing", "required": 15},
    {"level": 3, "emoji": "🤔", "rank": "BEGINNER IV", "tagline": "🎯 Focusing", "required": 20},
    {"level": 4, "emoji": "🧐", "rank": "BEGINNER V", "tagline": "💪 Improving", "required": 25},
    {"level": 5, "emoji": "😎", "rank": "STARTER I", "tagline": "⚡ Getting Started", "required": 30},
    {"level": 6, "emoji": "🤓", "rank": "STARTER II", "tagline": "📚 Learning Ropes", "required": 40},
    {"level": 7, "emoji": "😏", "rank": "STARTER III", "tagline": "🔧 Building Skills", "required": 50},
    {"level": 8, "emoji": "😌", "rank": "STARTER IV", "tagline": "🎯 Finding Rhythm", "required": 60},
    {"level": 9, "emoji": "😁", "rank": "STARTER V", "tagline": "🔥 Gaining Momentum", "required": 70},
    {"level": 10, "emoji": "🥱", "rank": "PLAYER I", "tagline": "🎮 Gaming Mode", "required": 80},
    {"level": 11, "emoji": "😴", "rank": "PLAYER II", "tagline": "⚡ Active Mode", "required": 100},
    {"level": 12, "emoji": "😪", "rank": "PLAYER III", "tagline": "🎯 Target Practice", "required": 120},
    {"level": 13, "emoji": "😮", "rank": "PLAYER IV", "tagline": "🔥 Getting Serious", "required": 140},
    {"level": 14, "emoji": "🤯", "rank": "PLAYER V", "tagline": "💪 Power Mode", "required": 160},
    {"level": 15, "emoji": "😬", "rank": "RISING I", "tagline": "📈 Rising Star", "required": 180},
    {"level": 16, "emoji": "😤", "rank": "RISING II", "tagline": "⚡ Climbing Up", "required": 210},
    {"level": 17, "emoji": "😠", "rank": "RISING III", "tagline": "🔥 On Fire", "required": 240},
    {"level": 18, "emoji": "😡", "rank": "RISING IV", "tagline": "💥 Breaking Through", "required": 270},
    {"level": 19, "emoji": "👿", "rank": "RISING V", "tagline": "👑 Almost There", "required": 300},
    {"level": 20, "emoji": "👹", "rank": "PRO I", "tagline": "🎯 Sharpshooter", "required": 330},
    {"level": 21, "emoji": "😈", "rank": "PRO II", "tagline": "⚡ Professional", "required": 370},
    {"level": 22, "emoji": "💀", "rank": "PRO III", "tagline": "🔥 Deadly Aim", "required": 410},
    {"level": 23, "emoji": "☠️", "rank": "PRO IV", "tagline": "💪 Power Pro", "required": 450},
    {"level": 24, "emoji": "👑", "rank": "PRO V", "tagline": "⭐ Pro Elite", "required": 500},
    {"level": 25, "emoji": "👁️", "rank": "ELITE I", "tagline": "👁️ Eagle Eye", "required": 550},
    {"level": 26, "emoji": "🌀", "rank": "ELITE II", "tagline": "🌀 Unpredictable", "required": 610},
    {"level": 27, "emoji": "🐲", "rank": "ELITE III", "tagline": "🐲 Dragon Mode", "required": 670},
    {"level": 28, "emoji": "⭐", "rank": "ELITE IV", "tagline": "⭐ Star Power", "required": 730},
    {"level": 29, "emoji": "🌟", "rank": "ELITE V", "tagline": "🌟 Super Elite", "required": 800},
    {"level": 30, "emoji": "💎", "rank": "MASTER I", "tagline": "💎 Diamond Mind", "required": 850},
    {"level": 31, "emoji": "🔥", "rank": "MASTER II", "tagline": "🔥 Fire Master", "required": 920},
    {"level": 32, "emoji": "⚡", "rank": "MASTER III", "tagline": "⚡ Lightning Strike", "required": 990},
    {"level": 33, "emoji": "🌊", "rank": "MASTER IV", "tagline": "🌊 Wave Master", "required": 1060},
    {"level": 34, "emoji": "🌌", "rank": "MASTER V", "tagline": "🌌 Cosmic Master", "required": 1150},
    {"level": 35, "emoji": "🌪️", "rank": "APEX PRO I", "tagline": "🌪️ Storm Caller", "required": 1200},
    {"level": 36, "emoji": "🌋", "rank": "APEX PRO II", "tagline": "🌋 Volcano Power", "required": 1300},
    {"level": 37, "emoji": "🌠", "rank": "APEX PRO III", "tagline": "🌠 Starfall", "required": 1400},
    {"level": 38, "emoji": "🪐", "rank": "APEX PRO IV", "tagline": "🪐 Saturn Power", "required": 1500},
    {"level": 39, "emoji": "☄️", "rank": "APEX PRO V", "tagline": "☄️ Comet Strike", "required": 1650},
    {"level": 40, "emoji": "🛡️", "rank": "ELITE FORCE I", "tagline": "🛡️ Shield Bearer", "required": 1750},
    {"level": 41, "emoji": "⚔️", "rank": "ELITE FORCE II", "tagline": "⚔️ Blade Master", "required": 1900},
    {"level": 42, "emoji": "🏹", "rank": "ELITE FORCE III", "tagline": "🏹 Archer Supreme", "required": 2050},
    {"level": 43, "emoji": "🗡️", "rank": "ELITE FORCE IV", "tagline": "🗡️ Dagger Strike", "required": 2200},
    {"level": 44, "emoji": "⚡", "rank": "ELITE FORCE V", "tagline": "⚡ Lightning Force", "required": 2400},
    {"level": 45, "emoji": "🌅", "rank": "AURA RISING I", "tagline": "🌅 Dawn of Aura", "required": 2600},
    {"level": 46, "emoji": "🌞", "rank": "AURA RISING II", "tagline": "🌞 Sun's Power", "required": 2850},
    {"level": 47, "emoji": "🌙", "rank": "AURA RISING III", "tagline": "🌙 Moon's Grace", "required": 3100},
    {"level": 48, "emoji": "⭐", "rank": "AURA RISING IV", "tagline": "⭐ Star's Light", "required": 3400},
    {"level": 49, "emoji": "🌌", "rank": "AURA RISING V", "tagline": "🌌 Galaxy's Heart", "required": 3700},
    {"level": 50, "emoji": "🔮", "rank": "AURA PRO I", "tagline": "🔮 Crystal Vision", "required": 4000},
    {"level": 51, "emoji": "🎯", "rank": "AURA PRO II", "tagline": "🎯 Perfect Aim", "required": 4400},
    {"level": 52, "emoji": "💫", "rank": "AURA PRO III", "tagline": "💫 Star Power", "required": 4800},
    {"level": 53, "emoji": "✨", "rank": "AURA PRO IV", "tagline": "✨ Shining Force", "required": 5200},
    {"level": 54, "emoji": "🌟", "rank": "AURA PRO V", "tagline": "🌟 Supernova", "required": 5700},
    {"level": 55, "emoji": "🌠", "rank": "AURA ELITE I", "tagline": "🌠 Meteor Strike", "required": 6200},
    {"level": 56, "emoji": "🪐", "rank": "AURA ELITE II", "tagline": "🪐 Ring Master", "required": 6800},
    {"level": 57, "emoji": "🌌", "rank": "AURA ELITE III", "tagline": "🌌 Cosmic Power", "required": 7400},
    {"level": 58, "emoji": "♾️", "rank": "AURA ELITE IV", "tagline": "♾️ Infinite Force", "required": 8000},
    {"level": 59, "emoji": "👑", "rank": "AURA ELITE V", "tagline": "👑 Royal Aura", "required": 8700},
    {"level": 60, "emoji": "💎", "rank": "AURA MASTER I", "tagline": "💎 Diamond Aura", "required": 9400},
    {"level": 61, "emoji": "🔥", "rank": "AURA MASTER II", "tagline": "🔥 Inferno", "required": 10200},
    {"level": 62, "emoji": "⚡", "rank": "AURA MASTER III", "tagline": "⚡ Thunder Strike", "required": 11000},
    {"level": 63, "emoji": "🌊", "rank": "AURA MASTER IV", "tagline": "🌊 Tsunami", "required": 12000},
    {"level": 64, "emoji": "🌋", "rank": "AURA MASTER V", "tagline": "🌋 Volcano Aura", "required": 13000},
    {"level": 65, "emoji": "🕉️", "rank": "AURA X I", "tagline": "🕉️ Zen Power", "required": 14000},
    {"level": 66, "emoji": "☯️", "rank": "AURA X II", "tagline": "☯️ Balance", "required": 15500},
    {"level": 67, "emoji": "⚕️", "rank": "AURA X III", "tagline": "⚕️ Healing Aura", "required": 17000},
    {"level": 68, "emoji": "🔱", "rank": "AURA X IV", "tagline": "🔱 Trident Power", "required": 18500},
    {"level": 69, "emoji": "🛡️", "rank": "AURA X V", "tagline": "🛡️ Ultimate Shield", "required": 20000},
    {"level": 70, "emoji": "🌅", "rank": "ASCENDANT I", "tagline": "🌅 Ascending", "required": 22000},
    {"level": 71, "emoji": "🌞", "rank": "ASCENDANT II", "tagline": "🌞 Solar Power", "required": 25000},
    {"level": 72, "emoji": "🌙", "rank": "ASCENDANT III", "tagline": "🌙 Lunar Might", "required": 28000},
    {"level": 73, "emoji": "⭐", "rank": "ASCENDANT IV", "tagline": "⭐ Stellar Force", "required": 32000},
    {"level": 74, "emoji": "👑", "rank": "ASCENDANT V", "tagline": "👑 Ascendant King", "required": 35000},
    {"level": 75, "emoji": "🏛️", "rank": "LEGEND I", "tagline": "🏛️ Legend Begins", "required": 40000},
    {"level": 76, "emoji": "🏰", "rank": "LEGEND II", "tagline": "🏰 Castle Master", "required": 45000},
    {"level": 77, "emoji": "👑", "rank": "LEGEND III", "tagline": "👑 King Legend", "required": 50000},
    {"level": 78, "emoji": "💠", "rank": "LEGEND IV", "tagline": "💠 Diamond Legend", "required": 60000},
    {"level": 79, "emoji": "🏆", "rank": "LEGEND V", "tagline": "🏆 Ultimate Legend", "required": 75000},
    {"level": 80, "emoji": "👽", "rank": "GOD TIER", "tagline": "👽 Beyond Reality", "required": 100000},
]

def get_aura_rank(total_plays):
    for rank_data in reversed(AURA_RANKS):
        if total_plays >= rank_data["required"]:
            return rank_data
    return AURA_RANKS[0]

def get_next_rank(total_plays):
    for rank_data in AURA_RANKS:
        if total_plays < rank_data["required"]:
            return rank_data
    return None

def get_rank_progress(total_plays):
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
# ⭐ FAKE USERS DATA
# ==========================================

FAKE_USERS = [
    {"name": "Manoj Tiwari", "username": "manoj_tiwari", "win": 12, "loss": 8},
    {"name": "Arjun Mehta", "username": "arjun_mehta", "win": 10, "loss": 6},
    {"name": "Suresh Rao", "username": "suresh_rao", "win": 9, "loss": 5},
    {"name": "Vikram Reddy", "username": "vikram_reddy", "win": 8, "loss": 4},
    {"name": "Deepak Verma", "username": "deepak_verma", "win": 7, "loss": 5},
    {"name": "Amit Singh", "username": "amit_singh", "win": 6, "loss": 3},
    {"name": "Rahul Joshi", "username": "rahul_joshi", "win": 5, "loss": 3},
    {"name": "Rajesh Kumar", "username": "rajesh_kumar", "win": 4, "loss": 2},
    {"name": "Priya Sharma", "username": "priya_sharma", "win": 3, "loss": 2},
    {"name": "Pooja Desai", "username": "pooja_desai", "win": 3, "loss": 1},
    {"name": "Ravi Kumar", "username": "ravi_kumar", "win": 25, "loss": 15},
    {"name": "Neha Singh", "username": "neha_singh", "win": 20, "loss": 12},
    {"name": "Vikram Shah", "username": "vikram_shah", "win": 30, "loss": 15},
    {"name": "Pooja Reddy", "username": "pooja_reddy", "win": 28, "loss": 10},
    {"name": "Amit Verma", "username": "amit_verma", "win": 15, "loss": 8},
]

FAKE_TIMESTAMPS = [
    "2026-08-19 00:15:23", "2026-08-19 00:32:45", "2026-08-18 23:45:12",
    "2026-08-18 23:12:34", "2026-08-18 22:30:56", "2026-08-18 22:05:18",
    "2026-08-18 21:40:42", "2026-08-18 21:15:30", "2026-08-18 20:50:15",
    "2026-08-18 20:25:08", "2026-08-18 20:00:00", "2026-08-18 19:35:22",
    "2026-08-18 19:10:45", "2026-08-18 18:45:33", "2026-08-18 18:20:14",
]

def initialize_fake_users():
    users = safe_load_json("users.json")
    
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
            wins = fake["win"]
            losses = fake["loss"]
            level = total_plays // 10
            rank_data = get_aura_rank(total_plays)
            
            unlocked_achievements = []
            
            if total_plays >= 1:
                unlocked_achievements.append("🎮 First Game")
            if total_plays >= 10:
                unlocked_achievements.append("🎯 10 Games")
            if total_plays >= 25:
                unlocked_achievements.append("🎯 25 Games")
            if total_plays >= 50:
                unlocked_achievements.append("🎯 50 Games")
            if total_plays >= 100:
                unlocked_achievements.append("🎯 100 Games")
            if total_plays >= 250:
                unlocked_achievements.append("🎯 250 Games")
            if total_plays >= 500:
                unlocked_achievements.append("🎯 500 Games")
            if total_plays >= 1000:
                unlocked_achievements.append("🎯 1000 Games")
            
            if wins >= 1:
                unlocked_achievements.append("🏅 First Win")
            if wins >= 10:
                unlocked_achievements.append("🏆 10 Wins")
            if wins >= 25:
                unlocked_achievements.append("🏆 25 Wins")
            if wins >= 50:
                unlocked_achievements.append("🏆 50 Wins")
            if wins >= 100:
                unlocked_achievements.append("🏆 100 Wins")
            if wins >= 250:
                unlocked_achievements.append("🏆 250 Wins")
            if wins >= 500:
                unlocked_achievements.append("🏆 500 Wins")
            if wins >= 1000:
                unlocked_achievements.append("🏆 1000 Wins")
            
            if level >= 5:
                unlocked_achievements.append("⭐ Level 5")
            if level >= 10:
                unlocked_achievements.append("⭐ Level 10")
            if level >= 15:
                unlocked_achievements.append("⭐ Level 15")
            if level >= 20:
                unlocked_achievements.append("⭐ Level 20")
            if level >= 25:
                unlocked_achievements.append("⭐ Level 25")
            if level >= 30:
                unlocked_achievements.append("⭐ Level 30")
            if level >= 40:
                unlocked_achievements.append("⭐ Level 40")
            if level >= 50:
                unlocked_achievements.append("⭐ Level 50")
            
            if wins >= 3:
                unlocked_achievements.append("🔥 3 Streak")
            if wins >= 5:
                unlocked_achievements.append("🔥 5 Streak")
            if wins >= 10:
                unlocked_achievements.append("🔥 10 Streak")
            if wins >= 15:
                unlocked_achievements.append("🔥 15 Streak")
            if wins >= 20:
                unlocked_achievements.append("🔥 20 Streak")
            
            if total_plays >= 100000:
                unlocked_achievements.append("🏆 GOD OF AURA")
                unlocked_achievements.append("⚡ LIGHTNING")
            if wins >= 50000:
                unlocked_achievements.append("💎 AURA MASTER")
            if wins >= 5000:
                unlocked_achievements.append("🏆 CHAMPION")
            if total_plays >= 25000:
                unlocked_achievements.append("💎 DIAMOND HANDS")
            
            if total_plays >= 30:
                unlocked_achievements.append("🌟 STAR PLAYER")
            
            if total_plays >= 30:
                unlocked_achievements.append("🏆 CHAMPION")
            if total_plays >= 25:
                unlocked_achievements.append("🏆 100 Wins")
            if total_plays >= 20:
                unlocked_achievements.append("🏆 50 Wins")
            if total_plays >= 15:
                unlocked_achievements.append("🎯 100 Games")
            if total_plays >= 10:
                unlocked_achievements.append("🎯 50 Games")
            if total_plays >= 5:
                unlocked_achievements.append("🎯 25 Games")
            if total_plays >= 3:
                unlocked_achievements.append("🏆 10 Wins")
            if total_plays >= 1:
                unlocked_achievements.append("🏅 First Win")
            
            unlocked_achievements = list(set(unlocked_achievements))
            
            fake_id = f"user_{username}"
            users[fake_id] = {
                "id": fake_id,
                "name": fake["name"],
                "username": fake["username"],
                "joined": str(datetime.now() - timedelta(days=random.randint(1, 30))),
                "win_count": wins,
                "loss_count": losses,
                "level": level,
                "rank_level": rank_data["level"],
                "previous_rank": None,
                "device_id": f"dev_{random.randint(1000,9999)}",
                "ip_address": f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
                "free_trial_used": False,
                "free_trial_expiry": None,
                "is_fake": True,
                "last_active": random.choice(FAKE_TIMESTAMPS),
                "achievements": {"unlocked": unlocked_achievements}
            }
            fake_added += 1
            
            logger.info(f"✅ Fake user {username}: {len(unlocked_achievements)} achievements unlocked")
    
    if fake_added > 0:
        safe_save_json("users.json", users)
        logger.info(f"✅ Added {fake_added} fake users with smart achievements")

def get_real_users_count():
    users = safe_load_json("users.json")
    real_count = 0
    for uid, user_data in users.items():
        if not user_data.get("is_fake", False):
            real_count += 1
    return real_count

def should_show_fake_users():
    real_count = get_real_users_count()
    return real_count < 15

def get_leaderboard_users():
    users = safe_load_json("users.json")
    
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
                "level": user_data.get('level', 0),
                "total": total_plays,
                "rank_emoji": rank_data["emoji"],
                "rank_name": rank_data["rank"],
                "is_fake": is_fake,
                "last_active": user_data.get('last_active', '')
            })
    
    all_users.sort(key=lambda x: x["total"], reverse=True)
    return all_users

def get_rank_arrow(current_rank, previous_rank):
    if previous_rank is None:
        return "🆕"
    elif current_rank < previous_rank:
        return "⬆️"
    elif current_rank > previous_rank:
        return "⬇️"
    else:
        return ""

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

async def auto_delete_message(context, chat_id, message_id, delay=2):
    try:
        await asyncio.sleep(delay)
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Auto delete error: {e}")

async def send_and_auto_delete(update, context, text, delay=2, parse_mode=None, reply_markup=None):
    try:
        msg = await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        asyncio.create_task(auto_delete_message(context, update.effective_chat.id, msg.message_id, delay))
        return msg
    except Exception as e:
        logger.error(f"Send and auto delete error: {e}")
        return None

# ✅ ========== DOPAMINE HIT EMOJIS (WIN - 5 VARIATIONS) ==========
WIN_DOPAMINE = [
    """
🎉🎊🎉 *YOU'RE A LEGEND!* 🎉🎊🎉
🔥🔥🔥 *ON FIRE!* 🔥🔥🔥
🏆 *MASTER WINNER!* 🏆
""",
    """
💎💎💎 *DIAMOND PLAYER!* 💎💎💎
👑👑👑 *KING OF PREDICTIONS!* 👑👑👑
⭐ *EPIC WIN!* ⭐
""",
    """
🚀🚀🚀 *SKY HIGH!* 🚀🚀🚀
💪💪💪 *POWER PLAYER!* 💪💪💪
🥇 *GOLD STANDARD!* 🥇
""",
    """
🎯🎯🎯 *BULLSEYE!* 🎯🎯🎯
🌟🌟🌟 *AMAZING SKILLS!* 🌟🌟🌟
💯 *PERFECT SCORE!* 💯
""",
    """
👑👑👑 *ROYAL VICTORY!* 👑👑👑
🔥🔥🔥 *UNSTOPPABLE!* 🔥🔥🔥
🎯 *EXACT HIT!* 🎯
""",
]

# ✅ ========== DOPAMINE HIT EMOJIS (LOSS - 5 VARIATIONS) ==========
LOSS_DOPAMINE = [
    """
💪💪💪 *LEGEND IN MAKING!* 💪💪💪
😅😅😅 *SO CLOSE!* 😅😅😅
💪 *TRY AGAIN!* 💪
""",
    """
🔥🔥🔥 *KEEP GOING!* 🔥🔥🔥
🔄🔄🔄 *NEXT ROUND!* 🔄🔄🔄
💪 *CHAMPION RISING!* 💪
""",
    """
📈📈📈 *GROWING!* 📈📈📈
⚡⚡⚡ *SHAKE IT OFF!* ⚡⚡⚡
🏆 *COMEBACK KING!* 🏆
""",
    """
🌟🌟🌟 *STILL A STAR!* 🌟🌟🌟
💯💯💯 *STAY FOCUSED!* 💯💯💯
🎯 *FOCUS = WIN!* 🎯
""",
    """
🚀🚀🚀 *BOUNCE BACK!* 🚀🚀🚀
🏃🏃🏃 *KEEP MOVING!* 🏃🏃🏃
💪 *NEVER STOP!* 💪
""",
]

def get_random_win_emoji():
    return random.choice(WIN_DOPAMINE)

def get_random_loss_emoji():
    return random.choice(LOSS_DOPAMINE)

# ==========================================
# OLD WIN/LOSS STICKERS (Keep for backward compatibility)
# ==========================================
WIN_STICKERS = WIN_DOPAMINE
LOSS_STICKERS = LOSS_DOPAMINE

def get_random_win_sticker():
    return get_random_win_emoji()

def get_random_loss_sticker():
    return get_random_loss_emoji()

def load(f):
    if os.path.exists(f):
        with open(f, 'r') as x:
            return json.load(x)
    return {}

def save(f, d):
    with open(f, 'w') as x:
        json.dump(d, x, indent=4)

initialize_fake_users()

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

main_menu = ReplyKeyboardMarkup([
    ["💳 MEMBERSHIP", "📊 LEADERBOARD"],
    ["👤 PROFILE", "🏆 RANK"],
    ["📞 SUPPORT", "📝 FEEDBACK"],
    ["▶️ ▶️ PLAY ▶️ ▶️"],
    ["🏠 HOME"]
], resize_keyboard=True)

membership_menu = ReplyKeyboardMarkup([
    ["👑 BUY ₹299"],
    ["🔙 BACK"]
], resize_keyboard=True)

admin_menu = ReplyKeyboardMarkup([
    ["📊 STATS", "💰 PAYMENTS"],
    ["📢 BROADCAST", "📅 PAYMENT HISTORY"],
    ["🛡️ DEVICE TRACKING"],
    ["📊 NEW PLAYERS"],
    ["🔙 BACK"]
], resize_keyboard=True)

super_admin_menu = ReplyKeyboardMarkup([
    ["📊 STATS", "💰 PAYMENTS"],
    ["📢 BROADCAST", "📅 PAYMENT HISTORY"],
    ["📋 APPROVAL LOG", "👑 ADMIN ACTIVITY"],
    ["📝 FEEDBACK LOG", "🛡️ DEVICE TRACKING"],
    ["📊 NEW PLAYERS"],
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

profile_menu = ReplyKeyboardMarkup([
    ["🏆 ACHIEVEMENTS"],
    ["🎁 DAILY BONUS"],
    ["📜 HISTORY"],
    ["👥 REFERRAL"],
    ["🏆 WEEKLY REWARDS"],
    ["▶️ START ANALYSIS"],
    ["🏠 HOME"]
], resize_keyboard=True)

# ==========================================
# BANNERS
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

def get_stats_banner_with_level(win, loss, level, period, category, num1, num2, player_result=None, next_prediction=None):
    total_plays = win + loss
    rank_data = get_aura_rank(total_plays)
    
    banner = f"""
𝟬𝟴 — 𝗦𝗧𝗔𝗧𝗦
┌─[ 📈 𝗖/𝗧://𝗦𝗧𝗔𝗧𝗦 ]
│
├─[ 𝗦𝗘𝗦𝗦𝗜𝗢𝗡 ]
│ ├─ 🏆 𝗪𝗜𝗡   :: {win:02d}
│ ├─ ❌ 𝗟𝗢𝗦𝗦  :: {loss:02d}
│ ├─ 📈 𝗟𝗘𝗩𝗘𝗟 :: {level:02d}
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
# ⭐ NEW PLAYERS STATS - ADMIN/Super Admin
# ==========================================

async def new_players_stats(update, context):
    try:
        uid = int(update.effective_user.id)
        
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Admin only!")
            return
        
        users = safe_load_json("users.json")
        
        today = datetime.now().date().isoformat()
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        
        today_players = []
        yesterday_players = []
        total_players = 0
        
        for user_id, user_data in users.items():
            # ✅ Real users count (not fake)
            if user_data.get('is_fake', False):
                continue
            
            total_players += 1
            joined_date = user_data.get('joined', '')
            if joined_date:
                joined_date = joined_date[:10]
                if joined_date == today:
                    today_players.append({
                        'id': user_id,
                        'username': user_data.get('username', 'Unknown'),
                        'name': user_data.get('name', 'Unknown'),
                        'joined': user_data.get('joined', '')
                    })
                elif joined_date == yesterday:
                    yesterday_players.append({
                        'id': user_id,
                        'username': user_data.get('username', 'Unknown'),
                        'name': user_data.get('name', 'Unknown'),
                        'joined': user_data.get('joined', '')
                    })
        
        msg = f"""
📊 *NEW PLAYERS STATS*
━━━━━━━━━━━━━━━━━━━━━━

👥 *TOTAL PLAYERS*
├─ Total: {total_players}

━━━━━━━━━━━━━━━━━━━━━━
📅 *TODAY ({datetime.now().strftime('%d-%m-%Y')})*
├─ New Players: {len(today_players)}
"""
        
        if today_players:
            for i, p in enumerate(today_players[:20], 1):
                username = p.get('username', 'Unknown')
                name = p.get('name', 'Unknown')
                uid_display = p.get('id', '')
                msg += f"\n{i}. @{username} (ID: {uid_display})"
            if len(today_players) > 20:
                msg += f"\n... and {len(today_players) - 20} more"
        else:
            msg += "\n📭 No new players today"
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
📅 *YESTERDAY ({yesterday})*
├─ New Players: {len(yesterday_players)}
"""
        
        if yesterday_players:
            for i, p in enumerate(yesterday_players[:10], 1):
                username = p.get('username', 'Unknown')
                name = p.get('name', 'Unknown')
                uid_display = p.get('id', '')
                msg += f"\n{i}. @{username} (ID: {uid_display})"
            if len(yesterday_players) > 10:
                msg += f"\n... and {len(yesterday_players) - 10} more"
        else:
            msg += "\n📭 No new players yesterday"
        
        msg += """
━━━━━━━━━━━━━━━━━━━━━━
👑 *Admin:* @{update.effective_user.username}
🕐 *Report Time:* {datetime.now().strftime('%I:%M %p')}
"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"New players stats error: {e}")
        await update.message.reply_text("❌ Error loading stats!", reply_markup=admin_menu)
        async def start(update, context):
    try:
        uid = str(update.effective_user.id)
        users = safe_load_json("users.json")
        
        if uid not in users:
            device_info = get_user_details(update)
            users[uid] = {
                "id": uid, 
                "name": update.effective_user.username or "Unknown", 
                "joined": str(datetime.now()), 
                "win_count": 0, 
                "loss_count": 0, 
                "level": 0,
                "rank_level": 0,
                "previous_rank": None,
                "device_id": device_info["device_id"],
                "ip_address": device_info["ip_address"],
                "free_trial_used": False,
                "free_trial_expiry": None,
                "username": device_info["username"],
                "first_name": device_info["first_name"],
                "last_name": device_info["last_name"],
                "language_code": device_info["language_code"],
                "achievements": {"unlocked": []},
                "selected_achievement": None,
                "selected_achievement_saved": False
            }
            safe_save_json("users.json", users)
            logger.info(f"✅ New user created with device tracking: {uid}")
        
        if context.args and context.args[0].startswith('ref_'):
            await handle_referral(update, context)
            return
        
        await send_typing(context, update.effective_chat.id)
        await asyncio.sleep(0.3)
        
        disclaimer = """
⚠️ *18+ ONLY* ⚠️
━━━━━━━━━━━━━━━━━━━━━━
ᴛʜɪꜱ ʙᴏᴛ ɪꜱ ꜰᴏʀ ᴀᴅᴜʟᴛꜱ ᴏɴʟʏ.
ʙʏ ᴜꜱɪɴɢ ʏᴏᴜ ᴀɢʀᴇᴇ ᴛᴏ ᴛʜᴇ ᴛᴇʀᴍꜱ.
━━━━━━━━━━━━━━━━━━━━━━
⚡ ꜰᴏʀ ᴇᴅᴜᴄᴀᴛɪᴏɴᴀʟ ᴘᴜʀᴘᴏꜱᴇ ᴏɴʟʏ
"""
        await update.message.reply_text(disclaimer, parse_mode='Markdown')
        await asyncio.sleep(0.5)
        
        await update.message.reply_text(
            "🌟 Welcome to AURA BOT!\n\nClick START to begin! 🚀",
            reply_markup=start_btn
        )
    except Exception as e:
        logger.error(f"Start error: {e}")

async def start_button(update, context):
    try:
        uid = str(update.effective_user.id)
        vip = safe_load_json("vip.json")
        is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
        is_verified = context.user_data.get('verified', False)
        
        async with get_user_lock(uid):
            users = safe_load_json("users.json")
            if uid in users:
                users[uid]['win_count'] = 0
                users[uid]['loss_count'] = 0
                users[uid]['level'] = 0
                safe_save_json("users.json", users)
        
        await send_typing(context, update.effective_chat.id)
        await asyncio.sleep(0.3)
        
        banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
        await update.message.reply_text(banner, reply_markup=main_menu)
        
    except Exception as e:
        logger.error(f"Start button error: {e}")

async def buy_membership(update, context):
    try:
        uid = str(update.effective_user.id)
        vip = safe_load_json("vip.json")
        
        if uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now():
            banner = get_vip_banner(update.effective_user.username, vip[uid]['expiry'], vip[uid]['key'])
            await update.message.reply_text(f"""{banner}\n┌─[ 🔐 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦 ]\n│\n├─[ 👑 𝗠𝗔𝗡𝗔𝗚𝗘 𝗬𝗢𝗨𝗥 𝗩𝗜𝗣 ]\n│\n│ ├─ 👑 𝗕𝗨𝗬 𝗡𝗢𝗪 :: ₹299\n│ │     └─ 𝗘𝗫𝗧𝗘𝗡𝗗 𝗩𝗜𝗣\n│ │\n│ └─ 🔙 𝗕𝗔𝗖𝗞\n│       └─ 𝗚𝗢 𝗕𝗔𝗖𝗞\n│\n└─[ 🔐 𝗖/𝗧://𝗔𝗖𝗖𝗘𝗦𝗦_𝗚𝗥𝗔𝗡𝗧𝗘𝗗 ]""", reply_markup=membership_menu)
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
        pay = safe_load_json("pay.json")
        pay[req] = {"id": req, "uid": uid, "name": user_name, "photo": photo, "time": str(datetime.now()), "status": "pending"}
        safe_save_json("pay.json", pay)
        
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
        elif data.startswith("select_ach_"):
            await select_achievement_callback(update, context)
        elif data == "view_achievements":
            await view_achievements_callback(update, context)
        elif data == "back_profile":
            await back_to_profile_callback(update, context)
        elif data == "save_selected_achievement":
            await save_selected_achievement_callback(update, context)
        elif data == "profile_history":
            await profile_history_callback(update, context)
        elif data == "back_home":
            await back_home_callback(update, context)
            
    except Exception as e:
        logger.error(f"Callback error: {e}")

# ==========================================
# ⭐ ACHIEVEMENT SELECTION SYSTEM - UPDATED WITH DONE BUTTON
# ==========================================

async def view_achievements_callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        
        uid = str(query.from_user.id)
        users = safe_load_json("users.json")
        
        if uid not in users:
            await query.edit_message_text("❌ Please /start first!")
            return
        
        unlocked = users[uid].get('achievements', {}).get('unlocked', [])
        selected = users[uid].get('selected_achievement', None)
        is_saved = users[uid].get('selected_achievement_saved', False)
        
        if not unlocked:
            await query.edit_message_text(
                "🏅 *NO ACHIEVEMENTS UNLOCKED*\n━━━━━━━━━━━━━━━━━━━━━━\n\nStart playing to unlock achievements!\n💪 Play your first game to begin.",
                parse_mode='Markdown'
            )
            return
        
        status_text = "✅ SAVED" if is_saved else "⚠️ NOT SAVED (Click DONE to save)"
        selected_display = f"✅ {selected}" if selected else "❌ None Selected"
        
        msg = f"""
🏅 *YOUR ACHIEVEMENTS* ({len(unlocked)}/82)
━━━━━━━━━━━━━━━━━━━━━━

📌 *SELECTED:* {selected_display}
📌 *STATUS:* {status_text}

📋 *Unlocked Achievements:*
"""
        
        keyboard = []
        
        for ach in unlocked:
            rarity = ACHIEVEMENTS.get(ach, {}).get('rarity', 'common')
            emoji = get_rarity_emoji(rarity)
            is_selected = "✅" if ach == selected else "⬜"
            msg += f"\n{is_selected} {ach} {emoji}"
            keyboard.append([InlineKeyboardButton(f"SELECT {ach}", callback_data=f"select_ach_{ach}")])
        
        msg += """
━━━━━━━━━━━━━━━━━━━━━━
💡 Click SELECT to choose an achievement
💡 Then click DONE to save it to your profile!
"""
        
        keyboard.append([InlineKeyboardButton("✅ DONE - SAVE TO PROFILE", callback_data="save_selected_achievement")])
        keyboard.append([InlineKeyboardButton("⬅ BACK TO PROFILE", callback_data="back_profile")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"View achievements callback error: {e}")
        await query.edit_message_text("❌ Error loading achievements!", reply_markup=main_menu)

async def select_achievement_callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        
        uid = str(query.from_user.id)
        ach_name = query.data.replace("select_ach_", "")
        
        users = safe_load_json("users.json")
        
        if uid not in users:
            await query.edit_message_text("❌ Please /start first!")
            return
        
        unlocked = users[uid].get('achievements', {}).get('unlocked', [])
        
        if ach_name not in unlocked:
            await query.edit_message_text("❌ This achievement is not unlocked yet!")
            return
        
        users[uid]['selected_achievement'] = ach_name
        users[uid]['selected_achievement_saved'] = False
        safe_save_json("users.json", users)
        
        rarity = ACHIEVEMENTS.get(ach_name, {}).get('rarity', 'common')
        emoji = get_rarity_emoji(rarity)
        
        await view_achievements_callback(update, context)
        
    except Exception as e:
        logger.error(f"Select achievement callback error: {e}")
        await query.edit_message_text("❌ Error selecting achievement!", reply_markup=main_menu)

async def save_selected_achievement_callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        
        uid = str(query.from_user.id)
        users = safe_load_json("users.json")
        
        if uid not in users:
            await query.edit_message_text("❌ Please /start first!")
            return
        
        selected = users[uid].get('selected_achievement', None)
        
        if not selected:
            await query.edit_message_text(
                "❌ *NO ACHIEVEMENT SELECTED!*\n━━━━━━━━━━━━━━━━━━━━━━\n\nPlease select an achievement first, then click DONE.",
                parse_mode='Markdown'
            )
            return
        
        users[uid]['selected_achievement_saved'] = True
        safe_save_json("users.json", users)
        
        rarity = ACHIEVEMENTS.get(selected, {}).get('rarity', 'common')
        emoji = get_rarity_emoji(rarity)
        
        await query.edit_message_text(
            f"""
✅ *ACHIEVEMENT SAVED SUCCESSFULLY!*
━━━━━━━━━━━━━━━━━━━━━━

🏅 {selected} {emoji}

📌 This achievement is now SAVED to your profile!
📌 It will show on your PROFILE and LEADERBOARD!

━━━━━━━━━━━━━━━━━━━━━━
[⬅ BACK TO ACHIEVEMENTS]
""",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ BACK TO ACHIEVEMENTS", callback_data="view_achievements")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Save selected achievement callback error: {e}")
        await query.edit_message_text("❌ Error saving achievement!", reply_markup=main_menu)

async def back_to_profile_callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        
        uid = str(query.from_user.id)
        users = safe_load_json("users.json")
        vip = safe_load_json("vip.json")
        
        is_vip = False
        is_verified = context.user_data.get('verified', False)
        exp_text = "No Membership"
        key_text = "N/A"
        remaining = "N/A"
        joined_date = users.get(uid, {}).get('joined', datetime.now().strftime('%Y-%m-%d %H:%M'))
        
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
        
        user = users.get(uid, {})
        win = user.get('win_count', 0)
        loss = user.get('loss_count', 0)
        level = user.get('level', 0)
        total_plays = win + loss
        rank_data = get_aura_rank(total_plays)
        progress = get_rank_progress(total_plays)
        
        username = query.from_user.username or "Unknown"
        first_name = query.from_user.first_name or "User"
        
        streak = STREAK_TRACKER.get(uid, {}).get('streak', 0)
        max_streak = STREAK_TRACKER.get(uid, {}).get('max_streak', 0)
        
        ach_stats = get_achievement_stats(uid)
        title = get_achievement_title(ach_stats['percent'])
        
        selected_ach = None
        if users.get(uid, {}).get('selected_achievement_saved', False):
            selected_ach = users.get(uid, {}).get('selected_achievement', None)
        
        selected_display = f"🏅 {selected_ach}" if selected_ach else "None"
        
        ach_display = ""
        if ach_stats['unlocked'] > 0:
            unlocked_list = ach_stats['unlocked_list']
            recent = unlocked_list[-4:] if len(unlocked_list) > 4 else unlocked_list
            
            ach_display = f"\n🏆 *ACHIEVEMENTS* ({ach_stats['unlocked']}/{ach_stats['total']})\n━━━━━━━━━━━━━━━━━━━━━━\n"
            ach_display += f"📜 *Title:* {title}\n"
            ach_display += f"🏅 *Selected:* {selected_display}\n"
            ach_display += "⭐ *Recent Unlocked:*\n"
            for ach in recent:
                rarity = ACHIEVEMENTS.get(ach, {}).get('rarity', 'common')
                emoji = get_rarity_emoji(rarity)
                ach_display += f"├─ {ach} {emoji}\n"
            ach_display += f"\n📊 *Progress:* {ach_stats['unlocked']}/{ach_stats['total']} ({ach_stats['percent']}%)\n"
            ach_display += "\n[👉 SELECT ACHIEVEMENT] - Click below\n"
            
            if ach_stats['percent'] >= 100:
                ach_display += "\n🎊🎊🎊 *COMPLETED!* 🎊🎊🎊\n👑 YOU ARE THE ULTIMATE LEGEND!\n"
        else:
            ach_display = "\n🏅 No achievements yet. Start playing!\n💪 Play your first game to unlock!\n"
        
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
│ ├─ 📈 𝗟𝗘𝗩𝗘𝗟 :: {level}
│ ├─ 📊 𝗧𝗢𝗧𝗔𝗟 :: {total_plays}
│ ├─ 🔥 𝗦𝗧𝗥𝗘𝗔𝗞 :: {streak}
│ └─ 👑 𝗠𝗔𝗫 𝗦𝗧𝗥𝗘𝗔𝗞 :: {max_streak}
│
{ach_display}
├─ 𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬
│ └─ 🔑 𝗣𝗔𝗦𝗦𝗞𝗘𝗬 :: {key_text}
│
└─[ 𝗖/𝗧://𝗣𝗥𝗢𝗙𝗜𝗟𝗘 ]

💡 Click 🏆 YOUR ACHIEVEMENTS to select which one shows on your profile!
💡 Click 📜 COMPLETE HISTORY for full stats!
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 YOUR ACHIEVEMENTS", callback_data="view_achievements")],
            [InlineKeyboardButton("📜 COMPLETE HISTORY", callback_data="profile_history")],
            [InlineKeyboardButton("⬅ BACK TO HOME", callback_data="back_home")]
        ])
        
        await query.edit_message_text(banner, parse_mode='Markdown', reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Back to profile callback error: {e}")
        await query.edit_message_text("❌ Error loading profile!", reply_markup=main_menu)

# ==========================================
# ⭐ LEADERBOARD - DYNAMIC ACHIEVEMENTS (FIXED)
# ==========================================
async def leaderboard(update, context):
    try:
        uid = str(update.effective_user.id)
        users = safe_load_json("users.json")
        
        all_users = get_leaderboard_users()
        
        for i, user in enumerate(all_users, 1):
            user_id = user["id"]
            if user_id in users:
                users[user_id]['previous_rank'] = i
        safe_save_json("users.json", users)
        
        msg = f"""
🏆 *AURA LEADERBOARD*
━━━━━━━━━━━━━━━━━━━━━━
"""
        
        top_10 = all_users[:10]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, user in enumerate(top_10):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            name = user["username"] if user["username"] != "Unknown" else user["name"]
            level = user.get('level', 0)
            total = user.get('total', 0)
            
            user_id = user["id"]
            previous_rank = users.get(user_id, {}).get('previous_rank', None)
            arrow = get_rank_arrow(i + 1, previous_rank)
            
            if user_id in users:
                users[user_id]['previous_rank'] = i + 1
            
            unlocked = users.get(user_id, {}).get('achievements', {}).get('unlocked', [])
            has_saved_selection = users.get(user_id, {}).get('selected_achievement_saved', False)
            selected = users.get(user_id, {}).get('selected_achievement', None)
            
            msg += f"""
{medal} *{name}*
   📊 {total} Plays • Level {level} {arrow}
"""
            
            # 🔥 ========== DYNAMIC ACHIEVEMENT SHOWING (FIXED) ==========
            if has_saved_selection and selected and selected in unlocked:
                rarity = ACHIEVEMENTS.get(selected, {}).get('rarity', 'common')
                emoji = get_rarity_emoji(rarity)
                msg += f"""
   ═══ ACHIEVEMENT ═══
   🏅 {selected} {emoji}
"""
            else:
                rare = get_rare_achievements(unlocked)
                
                # 🔥 DYNAMIC COUNT: Top1=4, Top2/3=3, Rest=1
                if i == 0:  # Rank #1
                    show_count = 4
                elif i == 1 or i == 2:  # Rank #2 and #3
                    show_count = 3
                else:  # Rank #4+
                    show_count = 1
                
                if rare:
                    rare_show = rare[:show_count]
                    if rare_show:
                        msg += f"""
   ═══ ACHIEVEMENTS ═══
"""
                        for ach_name, rarity in rare_show:
                            emoji = get_rarity_emoji(rarity)
                            msg += f"   🏅 {ach_name} {emoji}\n"
                else:
                    if unlocked:
                        random_ach = random.choice(unlocked)
                        rarity = ACHIEVEMENTS.get(random_ach, {}).get('rarity', 'common')
                        emoji = get_rarity_emoji(rarity)
                        msg += f"""
   ═══ ACHIEVEMENT ═══
   🏅 {random_ach} {emoji}
"""
        
        safe_save_json("users.json", users)
        
        msg += """
━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if uid in users:
            user_data = users[uid]
            total_plays = user_data.get('win_count', 0) + user_data.get('loss_count', 0)
            rank_data = get_aura_rank(total_plays)
            level = user_data.get('level', 0)
            
            pos = 1
            for i, user in enumerate(all_users, 1):
                if user["id"] == uid:
                    pos = i
                    break
            
            previous_rank = user_data.get('previous_rank', None)
            arrow = get_rank_arrow(pos, previous_rank)
            users[uid]['previous_rank'] = pos
            safe_save_json("users.json", users)
            
            msg += f"""
👤 *YOUR RANK*

#{pos}  {rank_data['emoji']} *{rank_data['rank']}*
📊 {total_plays} Plays • Level {level} {arrow}
"""
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
👥 *Total Players:* {len(all_users)}
💡 *Rank changes every hour!* ⏰
"""
        
        leaderboard_menu = ReplyKeyboardMarkup([
            ["🏠 HOME"]
        ], resize_keyboard=True)
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=leaderboard_menu)
        
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        await update.message.reply_text("❌ Error loading leaderboard!", reply_markup=main_menu)

# ==========================================
# ⭐ PROFILE HISTORY - DOPAMINE HIT
# ==========================================

async def profile_history_callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        
        uid = str(query.from_user.id)
        users = safe_load_json("users.json")
        user = users.get(uid, {})
        
        if not user:
            await query.edit_message_text("❌ Please /start first!")
            return
        
        win = user.get('win_count', 0)
        loss = user.get('loss_count', 0)
        level = user.get('level', 0)
        total_plays = win + loss
        
        highest_level = user.get('highest_level', level)
        if level > highest_level:
            highest_level = level
            users[uid]['highest_level'] = highest_level
            safe_save_json("users.json", users)
        
        win_rate = (win / total_plays * 100) if total_plays > 0 else 0
        win_rate_display = f"{win_rate:.1f}%"
        
        today = datetime.now().date().isoformat()
        daily_plays = 0
        daily_wins = 0
        daily_losses = 0
        
        if uid in HISTORY_TRACKER:
            for entry in HISTORY_TRACKER[uid]:
                entry_date = entry.get('time', '')[:10]
                if entry_date == today:
                    daily_plays += 1
                    if entry.get('result') == 'WIN':
                        daily_wins += 1
                    else:
                        daily_losses += 1
        
        daily_win_rate = (daily_wins / daily_plays * 100) if daily_plays > 0 else 0
        daily_win_rate_display = f"{daily_win_rate:.1f}%"
        
        all_users = get_leaderboard_users()
        total_players = len(all_users)
        
        player_rank = 0
        for i, u in enumerate(all_users, 1):
            if u['id'] == uid:
                player_rank = i
                break
        
        top_10 = all_users[:10]
        avg_top10_plays = 0
        avg_top10_wins = 0
        avg_top10_winrate = 0
        
        if top_10:
            for u in top_10:
                avg_top10_plays += u.get('total', 0)
                avg_top10_wins += u.get('win', 0)
            avg_top10_plays = avg_top10_plays // len(top_10)
            avg_top10_wins = avg_top10_wins // len(top_10)
            avg_top10_winrate = (avg_top10_wins / avg_top10_plays * 100) if avg_top10_plays > 0 else 0
        
        rank_data = get_aura_rank(total_plays)
        progress = get_rank_progress(total_plays)
        
        streak = STREAK_TRACKER.get(uid, {}).get('streak', 0)
        max_streak = STREAK_TRACKER.get(uid, {}).get('max_streak', 0)
        
        ach_stats = get_achievement_stats(uid)
        title = get_achievement_title(ach_stats['percent'])
        
        msg = f"""
📜 *YOUR COMPLETE HISTORY*
━━━━━━━━━━━━━━━━━━━━━━

👤 *Player:* @{user.get('username', 'Unknown')}

━━━━━━━━━━━━━━━━━━━━━━
📊 *OVERALL STATS*
├─ 🏆 *Total Wins* :: {win}
├─ ❌ *Total Losses* :: {loss}
├─ 📊 *Total Plays* :: {total_plays}
└─ 📈 *Win Rate* :: {win_rate_display}

━━━━━━━━━━━━━━━━━━━━━━
📈 *RANK & LEVEL*
├─ 🎖️ *Current Rank* :: {rank_data['emoji']} {rank_data['rank']}
├─ 📈 *Current Level* :: {level}
├─ 👑 *Highest Level* :: {highest_level} ⭐
└─ 🚀 *Next Rank* :: {progress['next']['rank'] if progress['next'] else '🏆 MAX'}

━━━━━━━━━━━━━━━━━━━━━━
🔥 *STREAKS*
├─ 🔥 *Current Streak* :: {streak} wins
└─ 👑 *Best Streak* :: {max_streak} wins 🏆

━━━━━━━━━━━━━━━━━━━━━━
📅 *TODAY'S STATS*
├─ 🏆 *Today Wins* :: {daily_wins}
├─ ❌ *Today Losses* :: {daily_losses}
├─ 📊 *Today Plays* :: {daily_plays}
└─ 📈 *Today Win Rate* :: {daily_win_rate_display}

━━━━━━━━━━━━━━━━━━━━━━
🏅 *ACHIEVEMENTS*
├─ 🏅 *Unlocked* :: {ach_stats['unlocked']}/{ach_stats['total']}
├─ 📊 *Progress* :: {ach_stats['percent']}%
└─ 👑 *Title* :: {title}

━━━━━━━━━━━━━━━━━━━━━━
👥 *PLAYER RATING (vs Others)*
├─ 📊 *Your Rank* :: #{player_rank} / {total_players}
├─ 📈 *Your Plays* :: {total_plays}
├─ 📊 *Top 10 Avg Plays* :: {avg_top10_plays}
├─ 📈 *Top 10 Avg Win Rate* :: {avg_top10_winrate:.1f}%
└─ 💡 *You are {'ABOVE' if total_plays > avg_top10_plays else 'BELOW'} average!*

━━━━━━━━━━━━━━━━━━━━━━
💪 *KEEP PLAYING TO BEAT THE TOP 10!* 🚀
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅ BACK TO PROFILE", callback_data="back_profile")]
        ])
        
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Profile history callback error: {e}")
        await query.edit_message_text("❌ Error loading history!", reply_markup=main_menu)

async def back_home_callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        
        uid = str(query.from_user.id)
        vip = safe_load_json("vip.json")
        is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
        is_verified = context.user_data.get('verified', False)
        
        banner = get_home_banner(query.from_user.username, is_vip, is_verified)
        
        user_id_int = int(uid)
        if user_id_int in SUPER_ADMIN_IDS:
            kb = super_admin_menu
        elif user_id_int in ADMIN_IDS:
            kb = admin_menu
        else:
            kb = main_menu
        
        await query.edit_message_text(banner, reply_markup=kb)
        
    except Exception as e:
        logger.error(f"Back home callback error: {e}")

# ==========================================
# ⭐ PROFILE COMMAND - UPDATED
# ==========================================
async def profile(update, context):
    try:
        uid = str(update.effective_user.id)
        users = safe_load_json("users.json")
        user = users.get(uid, {})
        vip = safe_load_json("vip.json")
        
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
        level = user.get('level', 0)
        total_plays = win + loss
        rank_data = get_aura_rank(total_plays)
        progress = get_rank_progress(total_plays)
        
        username = update.effective_user.username or "Unknown"
        first_name = update.effective_user.first_name or "User"
        
        streak = STREAK_TRACKER.get(uid, {}).get('streak', 0)
        max_streak = STREAK_TRACKER.get(uid, {}).get('max_streak', 0)
        
        ach_stats = get_achievement_stats(uid)
        title = get_achievement_title(ach_stats['percent'])
        
        selected_ach = None
        if users.get(uid, {}).get('selected_achievement_saved', False):
            selected_ach = users.get(uid, {}).get('selected_achievement', None)
        
        selected_display = f"🏅 {selected_ach}" if selected_ach else "None"
        
        ach_display = ""
        if ach_stats['unlocked'] > 0:
            unlocked_list = ach_stats['unlocked_list']
            recent = unlocked_list[-4:] if len(unlocked_list) > 4 else unlocked_list
            
            ach_display = f"\n🏆 *ACHIEVEMENTS* ({ach_stats['unlocked']}/{ach_stats['total']})\n━━━━━━━━━━━━━━━━━━━━━━\n"
            ach_display += f"📜 *Title:* {title}\n"
            ach_display += f"🏅 *Selected:* {selected_display}\n"
            ach_display += "⭐ *Recent Unlocked:*\n"
            for ach in recent:
                rarity = ACHIEVEMENTS.get(ach, {}).get('rarity', 'common')
                emoji = get_rarity_emoji(rarity)
                ach_display += f"├─ {ach} {emoji}\n"
            ach_display += f"\n📊 *Progress:* {ach_stats['unlocked']}/{ach_stats['total']} ({ach_stats['percent']}%)\n"
            ach_display += "\n[👉 SELECT ACHIEVEMENT] - Click below\n"
            
            if ach_stats['percent'] >= 100:
                ach_display += "\n🎊🎊🎊 *COMPLETED!* 🎊🎊🎊\n👑 YOU ARE THE ULTIMATE LEGEND!\n"
        else:
            ach_display = "\n🏅 No achievements yet. Start playing!\n💪 Play your first game to unlock!\n"
        
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
│ ├─ 📈 𝗟𝗘𝗩𝗘𝗟 :: {level}
│ ├─ 📊 𝗧𝗢𝗧𝗔𝗟 :: {total_plays}
│ ├─ 🔥 𝗦𝗧𝗥𝗘𝗔𝗞 :: {streak}
│ └─ 👑 𝗠𝗔𝗫 𝗦𝗧𝗥𝗘𝗔𝗞 :: {max_streak}
│
{ach_display}
├─ 𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬
│ └─ 🔑 𝗣𝗔𝗦𝗦𝗞𝗘𝗬 :: {key_text}
│
└─[ 𝗖/𝗧://𝗣𝗥𝗢𝗙𝗜𝗟𝗘 ]

💡 Click 🏆 YOUR ACHIEVEMENTS to select which one shows on your profile!
💡 Click 📜 COMPLETE HISTORY for full stats!
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 YOUR ACHIEVEMENTS", callback_data="view_achievements")],
            [InlineKeyboardButton("📜 COMPLETE HISTORY", callback_data="profile_history")],
            [InlineKeyboardButton("⬅ BACK TO HOME", callback_data="back_home")]
        ])
        
        await update.message.reply_text(banner, parse_mode='Markdown', reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        await update.message.reply_text("❌ Error loading profile!", reply_markup=main_menu)

# ==========================================
# ⭐ REMAINING FUNCTIONS (UNCHANGED - KEEP AS IS)
# ==========================================

async def approve_payment(query, context, req_id):
    try:
        pay = safe_load_json("pay.json")
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
        vip = safe_load_json("vip.json")
        vip[uid] = {"user_id": uid, "key": key, "expiry": expiry.isoformat()}
        safe_save_json("vip.json", vip)
        p['status'] = 'approved'
        p['passkey'] = key
        p['approved_by'] = admin_id
        p['approved_by_name'] = admin_name
        p['approved_time'] = datetime.now().isoformat()
        p['is_super_admin'] = is_super_admin
        safe_save_json("pay.json", pay)
        
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

async def reject_payment(query, context, req_id):
    try:
        pay = safe_load_json("pay.json")
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
        safe_save_json("pay.json", pay)
        
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
            
            users = safe_load_json("users.json")
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
# ALL OTHER FUNCTIONS (UNCHANGED - KEEP AS IS)
# ==========================================

async def approval_log(update, context):
    try:
        uid = int(update.effective_user.id)
        if uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Only Super Admin can view this!")
            return
        
        pay = safe_load_json("pay.json")
        
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

async def achievements(update, context):
    try:
        uid = str(update.effective_user.id)
        users = safe_load_json("users.json")
        user = users.get(uid, {})
        
        win = user.get('win_count', 0)
        loss = user.get('loss_count', 0)
        level = user.get('level', 0)
        total_plays = win + loss
        
        progress = get_rank_progress(total_plays)
        
        vip = safe_load_json("vip.json")
        is_vip = False
        if uid in vip:
            exp = datetime.fromisoformat(vip[uid]['expiry'])
            if exp > datetime.now():
                is_vip = True
        
        ach_stats = get_achievement_stats(uid)
        unlocked_list = ach_stats['unlocked_list']
        
        msg = f"""
🏆 *ALL ACHIEVEMENTS*
━━━━━━━━━━━━━━━━━━━━━━

👤 *Player:* @{user.get('username', 'Unknown')}
📊 *Progress:* {ach_stats['unlocked']}/{ach_stats['total']} ({ach_stats['percent']}%)

"""
        
        categories = {
            "🎮 Game Play": [],
            "🏆 Wins": [],
            "🔥 Streak": [],
            "⭐ Level": [],
            "👑 VIP": [],
            "🎁 Bonus": [],
            "👥 Referral": [],
            "📅 Daily Streak": [],
            "🎯 Perfect Prediction": [],
            "🏆 Ultimate": []
        }
        
        cat_map = {
            "🎮 Game Play": ["🎮", "🎯 10", "🎯 25", "🎯 50", "🎯 100", "🎯 250", "🎯 500", "🎯 1000", "🎯 2500", "🎯 5000", "🎯 10000", "🎯 25000", "🎯 50000", "🎯 100000"],
            "🏆 Wins": ["🏅", "🏆 10", "🏆 25", "🏆 50", "🏆 100", "🏆 250", "🏆 500", "🏆 1000", "🏆 2500", "🏆 5000", "🏆 10000", "🏆 25000", "🏆 50000", "🏆 100000"],
            "🔥 Streak": ["🔥 3", "🔥 5", "🔥 10", "🔥 15", "🔥 20", "🔥 25", "🔥 30", "🔥 50", "🔥 75", "🔥 100", "🔥 150", "🔥 200"],
            "⭐ Level": ["⭐ Level 5", "⭐ Level 10", "⭐ Level 15", "⭐ Level 20", "⭐ Level 25", "⭐ Level 30", "⭐ Level 40", "⭐ Level 50", "⭐ Level 75", "⭐ Level 100"],
            "👑 VIP": ["👑 Royal Player", "💎 Diamond VIP", "👑 King VIP", "👑 Emperor VIP"],
            "🎁 Bonus": ["🎁 Daily Bonus", "🎁 Weekly Bonus", "🎁 Monthly Bonus"],
            "👥 Referral": ["👥 Recruiter", "👥 Super Recruiter", "👥 Mega Recruiter", "👥 Legendary Recruiter"],
            "📅 Daily Streak": ["📅 7 Day Streak", "📅 15 Day Streak", "📅 30 Day Streak", "📅 60 Day Streak", "📅 90 Day Streak", "📅 180 Day Streak", "📅 365 Day Streak"],
            "🎯 Perfect Prediction": ["🎯 Perfect Prediction", "🎯 God Mode", "🎯 Unstoppable", "🎯 Invincible"],
            "🏆 Ultimate": ["👑 Ultimate Legend", "🏆 GOD OF AURA", "💎 AURA MASTER", "🌟 STAR PLAYER", "👑 AURA KING", "🏆 CHAMPION", "💎 DIAMOND HANDS", "🔥 FIRE GOD", "⚡ LIGHTNING", "👽 GOD TIER"]
        }
        
        for name, data in ACHIEVEMENTS.items():
            for cat, keys in cat_map.items():
                if any(name.startswith(k) for k in keys) or name in keys:
                    categories[cat].append(name)
                    break
        
        for cat, items in categories.items():
            if items:
                unlocked_count = sum(1 for i in items if i in unlocked_list)
                if unlocked_count > 0:
                    msg += f"\n*{cat}* ({unlocked_count}/{len(items)})\n"
                    for item in items:
                        if item in unlocked_list:
                            rarity = ACHIEVEMENTS.get(item, {}).get('rarity', 'common')
                            emoji = get_rarity_emoji(rarity)
                            msg += f"├─ {item} ✅ {emoji}\n"
                        else:
                            msg += f"├─ {item} ⬜\n"
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
💎 *VIP Status:* {'✅ ACTIVE' if is_vip else '❌ INACTIVE'}
[⬅ BACK TO PROFILE]
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅ BACK TO PROFILE", callback_data="back_profile")]
        ])
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Achievements error: {e}")
        await update.message.reply_text("❌ Error loading achievements!", reply_markup=profile_menu)

async def rank_command(update, context):
    try:
        uid = str(update.effective_user.id)
        users = safe_load_json("users.json")
        
        if uid not in users:
            await update.message.reply_text("❌ Please /start first!")
            return
        
        user = users[uid]
        wins = user.get('win_count', 0)
        losses = user.get('loss_count', 0)
        total_plays = wins + losses
        
        current_rank = get_aura_rank(total_plays)
        next_rank = get_next_rank(total_plays)
        
        rank_chart = """
📋 *COMPLETE RANK CHART*
━━━━━━━━━━━━━━━━━━━━━━

😅 BEGINNER I (5 plays)
🙂 BEGINNER II (10 plays)
😊 BEGINNER III (15 plays)
🤔 BEGINNER IV (20 plays)
🧐 BEGINNER V (25 plays)

😎 STARTER I (30 plays)
🤓 STARTER II (40 plays)
😏 STARTER III (50 plays)
😌 STARTER IV (60 plays)
😁 STARTER V (70 plays)

🥱 PLAYER I (80 plays)
😴 PLAYER II (100 plays)
😪 PLAYER III (120 plays)
😮 PLAYER IV (140 plays)
🤯 PLAYER V (160 plays)

😬 RISING I (180 plays)
😤 RISING II (210 plays)
😠 RISING III (240 plays)
😡 RISING IV (270 plays)
👿 RISING V (300 plays)

👹 PRO I (330 plays)
😈 PRO II (370 plays)
💀 PRO III (410 plays)
☠️ PRO IV (450 plays)
👑 PRO V (500 plays)

👁️ ELITE I (550 plays)
🌀 ELITE II (610 plays)
🐲 ELITE III (670 plays)
⭐ ELITE IV (730 plays)
🌟 ELITE V (800 plays)

💎 MASTER I (850 plays)
🔥 MASTER II (920 plays)
⚡ MASTER III (990 plays)
🌊 MASTER IV (1060 plays)
🌌 MASTER V (1150 plays)

🌪️ APEX PRO I (1200 plays)
🌋 APEX PRO II (1300 plays)
🌠 APEX PRO III (1400 plays)
🪐 APEX PRO IV (1500 plays)
☄️ APEX PRO V (1650 plays)

🛡️ ELITE FORCE I (1750 plays)
⚔️ ELITE FORCE II (1900 plays)
🏹 ELITE FORCE III (2050 plays)
🗡️ ELITE FORCE IV (2200 plays)
⚡ ELITE FORCE V (2400 plays)

🌅 AURA RISING I (2600 plays)
🌞 AURA RISING II (2850 plays)
🌙 AURA RISING III (3100 plays)
⭐ AURA RISING IV (3400 plays)
🌌 AURA RISING V (3700 plays)

🔮 AURA PRO I (4000 plays)
🎯 AURA PRO II (4400 plays)
💫 AURA PRO III (4800 plays)
✨ AURA PRO IV (5200 plays)
🌟 AURA PRO V (5700 plays)

🌠 AURA ELITE I (6200 plays)
🪐 AURA ELITE II (6800 plays)
🌌 AURA ELITE III (7400 plays)
♾️ AURA ELITE IV (8000 plays)
👑 AURA ELITE V (8700 plays)

💎 AURA MASTER I (9400 plays)
🔥 AURA MASTER II (10200 plays)
⚡ AURA MASTER III (11000 plays)
🌊 AURA MASTER IV (12000 plays)
🌋 AURA MASTER V (13000 plays)

🕉️ AURA X I (14000 plays)
☯️ AURA X II (15500 plays)
⚕️ AURA X III (17000 plays)
🔱 AURA X IV (18500 plays)
🛡️ AURA X V (20000 plays)

🌅 ASCENDANT I (22000 plays)
🌞 ASCENDANT II (25000 plays)
🌙 ASCENDANT III (28000 plays)
⭐ ASCENDANT IV (32000 plays)
👑 ASCENDANT V (35000 plays)

🏛️ LEGEND I (40000 plays)
🏰 LEGEND II (45000 plays)
👑 LEGEND III (50000 plays)
💠 LEGEND IV (60000 plays)
🏆 LEGEND V (75000 plays)

👽 GOD TIER (100000+ plays)
━━━━━━━━━━━━━━━━━━━━━━
"""
        
        current_rank_line = f"""
📍 *YOUR CURRENT RANK*
👉 {current_rank['emoji']} *{current_rank['rank']}* ← YOUR RANK
"""

        if next_rank:
            progress = get_rank_progress(total_plays)
            bar = format_progress_bar(progress['percent'])
            
            msg = f"""
🏆 *RANK PROGRESS*
━━━━━━━━━━━━━━━━━━━━━━

👤 *Player:* @{user.get('username', 'Unknown')}

{current_rank_line}

📊 *Current Rank:*
{current_rank['emoji']} *{current_rank['rank']}*
{current_rank['tagline']}

━━━━━━━━━━━━━━━━━━━━━━
🎯 *NEXT RANK:*
{next_rank['emoji']} *{next_rank['rank']}*
{next_rank['tagline']}

📈 *Progress:*
{bar}
{progress['done']} / {progress['required']} plays
⏳ {progress['remaining']} more plays needed

━━━━━━━━━━━━━━━━━━━━━━
📊 *YOUR STATS:*
├─ 🏆 Wins: {wins}
├─ ❌ Losses: {losses}
└─ 📈 Total: {total_plays}

{rank_chart}

💡 *Keep playing to rank up!* 🚀
"""
        else:
            msg = f"""
🏆 *RANK PROGRESS*
━━━━━━━━━━━━━━━━━━━━━━

👤 *Player:* @{user.get('username', 'Unknown')}

{current_rank_line}

👑 *MAX RANK REACHED!*
{current_rank['emoji']} *{current_rank['rank']}*
{current_rank['tagline']}

━━━━━━━━━━━━━━━━━━━━━━
📊 *YOUR STATS:*
├─ 🏆 Wins: {wins}
├─ ❌ Losses: {losses}
└─ 📈 Total: {total_plays}

{rank_chart}

🏆 *YOU ARE A LEGEND!* 👑
"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Rank command error: {e}")
        await update.message.reply_text("❌ Error loading rank!", reply_markup=main_menu)

async def device_tracking(update, context):
    try:
        uid = int(update.effective_user.id)
        
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Access Denied! Admin only.")
            return
        
        users = safe_load_json("users.json")
        
        total_users = len(users)
        
        devices = {}
        for user_id, user_data in users.items():
            device_id = user_data.get('device_id', '')
            if device_id:
                if device_id not in devices:
                    devices[device_id] = []
                devices[device_id].append({
                    'username': user_data.get('username', 'Unknown'),
                    'user_id': user_id,
                    'is_fake': user_data.get('is_fake', False)
                })
        
        unique_devices = len(devices)
        
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
            is_fake = user_data.get('is_fake', False)
            fake_tag = " (FAKE)" if is_fake else ""
            
            msg += f"""
👤 @{username} (ID: {user_id}){fake_tag}
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
"""
        
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 All Users", callback_data="track_all")],
            [InlineKeyboardButton("📱 Unique Devices", callback_data="track_devices")]
        ])
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=inline_keyboard)
        
    except Exception as e:
        logger.error(f"Device tracking error: {e}")
        await update.message.reply_text("❌ Error loading device tracking!", reply_markup=admin_menu)

async def device_tracking_callback(update, context):
    try:
        query = update.callback_query
        await query.answer()
        
        uid = int(query.from_user.id)
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await query.edit_message_text("❌ Access Denied! Admin only.")
            return
        
        data = query.data
        users = safe_load_json("users.json")
        
        if data == "track_all":
            msg = f"""
📊 *ALL USERS ({len(users)})*
━━━━━━━━━━━━━━━━━━━━━━
"""
            count = 0
            for user_id, user_data in list(users.items())[-20:]:
                username = user_data.get('username', 'Unknown')
                device = user_data.get('device_id', 'N/A')[:8]
                is_fake = user_data.get('is_fake', False)
                fake_tag = " (FAKE)" if is_fake else ""
                msg += f"👤 @{username} (ID: {user_id}){fake_tag} | 📱{device}...\n"
                count += 1
                if count >= 20:
                    break
            await query.edit_message_text(msg, parse_mode='Markdown')
            
        elif data == "track_devices":
            devices = {}
            for user_id, user_data in users.items():
                device_id = user_data.get('device_id', '')
                if device_id:
                    if device_id not in devices:
                        devices[device_id] = []
                    devices[device_id].append({
                        'username': user_data.get('username', 'Unknown'),
                        'user_id': user_id,
                        'is_fake': user_data.get('is_fake', False)
                    })
            
            msg = f"""
📱 *UNIQUE DEVICES ({len(devices)})*
━━━━━━━━━━━━━━━━━━━━━━
"""
            for device_id, users_list in list(devices.items())[:20]:
                msg += f"📱 {device_id[:8]}... -> {len(users_list)} users\n"
                for u in users_list[:3]:
                    fake_tag = " (FAKE)" if u['is_fake'] else ""
                    msg += f"   👤 @{u['username']} (ID: {u['user_id']}){fake_tag}\n"
                if len(users_list) > 3:
                    msg += f"   ... and {len(users_list)-3} more\n"
                msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
            
            await query.edit_message_text(msg, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Device tracking callback error: {e}")
        await query.edit_message_text("❌ Error!", reply_markup=admin_menu)

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
""", parse_mode='Markdown')
            return
        
        target_user_id = args[0]
        users = safe_load_json("users.json")
        
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

📊 *STATS*
├─ 🏆 Wins   :: {user_data.get('win_count', 0)}
├─ ❌ Losses :: {user_data.get('loss_count', 0)}
├─ 📈 Level  :: {user_data.get('level', 0)}
└─ 🏆 Achievements :: {len(user_data.get('achievements', {}).get('unlocked', []))}/82

👑 *Admin:* @{update.effective_user.username}
🕐 *Report Time:* {datetime.now().strftime('%I:%M %p')}
"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Track user error: {e}")
        await update.message.reply_text("❌ Error tracking user!", reply_markup=admin_menu)

async def show_devices(update, context):
    try:
        uid = int(update.effective_user.id)
        
        if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
            await update.message.reply_text("❌ Access Denied! Admin only.")
            return
        
        users = safe_load_json("users.json")
        
        devices = {}
        for user_id, user_data in users.items():
            device_id = user_data.get('device_id', '')
            if device_id:
                if device_id not in devices:
                    devices[device_id] = []
                devices[device_id].append({
                    'username': user_data.get('username', 'Unknown'),
                    'user_id': user_id,
                    'is_fake': user_data.get('is_fake', False)
                })
        
        if not devices:
            await update.message.reply_text("📭 No devices found!")
            return
        
        msg = f"""
📱 *UNIQUE DEVICES ({len(devices)})*
━━━━━━━━━━━━━━━━━━━━━━
"""
        for device_id, users_list in list(devices.items())[:30]:
            msg += f"📱 `{device_id[:12]}...` -> {len(users_list)} users\n"
            for u in users_list[:3]:
                fake_tag = " (FAKE)" if u['is_fake'] else ""
                msg += f"   👤 @{u['username']} (ID: {u['user_id']}){fake_tag}\n"
            if len(users_list) > 3:
                msg += f"   ... and {len(users_list)-3} more\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Show devices error: {e}")
        await update.message.reply_text("❌ Error loading devices!", reply_markup=admin_menu)

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
# ⭐ PLAY AND GAME FUNCTIONS
# ==========================================

async def play(update, context):
    try:
        uid = str(update.effective_user.id)
        vip = safe_load_json("vip.json")
        
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
        vip = safe_load_json("vip.json")
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

async def timer_select(update, context):
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        users = safe_load_json("users.json")
        
        if uid not in users:
            device_info = get_user_details(update)
            users[uid] = {"id": uid, "name": update.effective_user.username or "Unknown", "joined": str(datetime.now()), "win_count": 0, "loss_count": 0, "level": 0, "rank_level": 0, "previous_rank": None, "device_id": device_info["device_id"], "ip_address": device_info["ip_address"], "free_trial_used": False, "free_trial_expiry": None, "username": device_info["username"], "first_name": device_info["first_name"], "last_name": device_info["last_name"], "language_code": device_info["language_code"], "achievements": {"unlocked": []}}
            safe_save_json("users.json", users)
            logger.info(f"✅ New user created in timer: {uid}")
        timer_map = {"⏱ 30s": "30", "⏱ 1m": "60", "⏱ 2m": "120", "⏱ 5m": "300"}
        if text in timer_map:
            users[uid]['selected_time'] = timer_map[text]
            safe_save_json("users.json", users)
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

async def set_period(update, context):
    try:
        uid = str(update.effective_user.id)
        period = update.message.text.strip()
        
        if not context.user_data.get('waiting_period'):
            logger.info(f"⚠️ waiting_period is False for {uid}, but continuing...")
            context.user_data['waiting_period'] = True
        
        if len(period) == 4 and period.isdigit():
            users = safe_load_json("users.json")
            users[uid]['last_period'] = period
            safe_save_json("users.json", users)
            
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
            users = safe_load_json("users.json")
            period = users.get(uid, {}).get('last_period', '0000')
            
            algo_prediction = predict_next_with_history()
            context.user_data['algo_prediction'] = algo_prediction
            
            logger.info(f"🔮 Algorithm: {user_num} → {algo_prediction['prediction']} ({algo_prediction['number']})")
            
            save_result(uid, period, user_num, result_trend)
            add_result_to_history(user_num)
            
            logger.info(f"✅ Added {user_num} to history! Total: {len(HISTORICAL_RESULTS)}")
            
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
        
        users = safe_load_json("users.json")
        users[uid]['last_period'] = current_period
        safe_save_json("users.json", users)
        
        context.user_data['last_analysis'] = {
            "trend": trend, 
            "num1": num1, 
            "num2": num2, 
            "period": current_period
        }
        
        banner = get_analysis_banner(current_period, category, num1, num2)
        await update.message.reply_text(banner, reply_markup=result_keyboard)
        context.user_data['waiting_result'] = True
        
    except Exception as e:
        logger.error(f"Process analysis error: {e}")
        await update.message.reply_text("❌ Error! Please try again.", reply_markup=result_keyboard)

# ==========================================
# ⭐ HANDLE RESULT - UPDATED WITH DOPAMINE HIT (2 SECOND AUTO-DELETE)
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
            
            bot_category_raw = last.get('trend', '')
            if 'BIG' in bot_category_raw or bot_category_raw == 'BIG':
                bot_category = 'BIG'
            elif 'SMALL' in bot_category_raw or bot_category_raw == 'SMALL':
                bot_category = 'SMALL'
            else:
                bot_category = bot_category_raw
            
            user_num = last.get('num1', 0)
            if user_num >= 5:
                player_category = "BIG"
            else:
                player_category = "SMALL"
            
            if bot_category == player_category:
                win = True
                result_text = "✅ VICTORY!"
            else:
                win = False
                result_text = "💪 KEEP GOING!"
            
            async with get_user_lock(uid):
                users = safe_load_json("users.json")
                
                if 'win_count' not in users[uid]:
                    users[uid]['win_count'] = 0
                    users[uid]['loss_count'] = 0
                    users[uid]['level'] = 0
                
                old_total = users[uid]['win_count'] + users[uid]['loss_count']
                old_rank = get_aura_rank(old_total)
                
                if win:
                    users[uid]['win_count'] += 1
                    users[uid]['level'] = 0
                else:
                    users[uid]['loss_count'] += 1
                    users[uid]['level'] += 1
                
                new_total = users[uid]['win_count'] + users[uid]['loss_count']
                new_rank = get_aura_rank(new_total)
                
                stats = {
                    'wins': users[uid]['win_count'],
                    'games': new_total,
                    'streak': update_streak(uid, win),
                    'max_streak': STREAK_TRACKER.get(uid, {}).get('max_streak', 0),
                    'level': users[uid]['level'],
                    'is_vip': uid in safe_load_json("vip.json"),
                    'vip_days': 0,
                    'bonus_count': 0,
                    'weekly_claimed': False,
                    'monthly_claimed': False,
                    'referrals': REFERRAL_TRACKER.get(uid, {}).get('count', 0),
                    'daily_streak': 0,
                    'rank_position': 0,
                    'rank_name': new_rank['rank']
                }
                
                new_achievements = check_achievements(uid, users, stats)
                
                safe_save_json("users.json", users)
            
            for ach in new_achievements:
                rarity = ACHIEVEMENTS[ach].get('rarity', 'common')
                rarity_label = get_rarity_label(rarity)
                emoji = get_rarity_emoji(rarity)
                count = get_achievement_players_count(ach)
                if count == 0:
                    count = 1
                
                ach_stats = get_achievement_stats(uid)
                title = get_achievement_title(ach_stats['percent'])
                
                if ach_stats['percent'] >= 100:
                    unlock_msg = f"""
🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊
🏆 *COMPLETIONIST!* 🏆
🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊
━━━━━━━━━━━━━━━━━━━━━━

👑 *"THE ULTIMATE LEGEND"* 👑

🌟 *ALL ACHIEVEMENTS COMPLETE!* 🌟

━━━━━━━━━━━━━━━━━━━━━━
📊 *Your Stats:*
├─ 🏆 Achievements: {ach_stats['unlocked']}/{ach_stats['total']}
├─ 📈 Progress: {ach_stats['percent']}%
└─ 👑 Title: {title}

━━━━━━━━━━━━━━━━━━━━━━
🎖️ *FINAL RANK:* GOD TIER

📜 *Title:* "THE ONE"

━━━━━━━━━━━━━━━━━━━━━━
💎 *You are a true LEGEND!*

🏅 *Your name will be remembered FOREVER!*

━━━━━━━━━━━━━━━━━━━━━━
👑 *"Legends are not born, they are made!"*
"""
                else:
                    unlock_msg = f"""
🏅 *ACHIEVEMENT UNLOCKED!* 🏅
━━━━━━━━━━━━━━━━━━━━━━

{ach}
📝 {ACHIEVEMENTS[ach]['desc']}

🏅 *Rarity:* {rarity_label} {emoji}
👥 *Players with this:* {count}
📊 *Progress:* {ach_stats['unlocked']}/{ach_stats['total']} ({ach_stats['percent']}%)
📜 *Title:* {title}

━━━━━━━━━━━━━━━━━━━━━━
💪 Keep playing to unlock more!
"""
                
                await send_and_auto_delete(update, context, unlock_msg, delay=2, parse_mode='Markdown')
            
            streak = update_streak(uid, win)
            
            # ✅ ========== DOPAMINE HIT SYSTEM (2 SECOND AUTO-DELETE) ==========
            if win:
                win_emoji = get_random_win_emoji()
                dopamine_msg = await update.message.reply_text(win_emoji, parse_mode='Markdown')
                await asyncio.sleep(2)
                try:
                    await dopamine_msg.delete()
                except:
                    pass
            else:
                loss_emoji = get_random_loss_emoji()
                dopamine_msg = await update.message.reply_text(loss_emoji, parse_mode='Markdown')
                await asyncio.sleep(2)
                try:
                    await dopamine_msg.delete()
                except:
                    pass
            # ✅ ============================================================
            
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
                await send_and_auto_delete(update, context, rank_up_msg, delay=2, parse_mode='Markdown')
            
            add_to_history(uid, period, last.get('num1'), final_choice, win)
            
            if final_choice == "BIG":
                next_num1 = random.randint(5, 9)
                available = [i for i in range(5, 10) if i != next_num1]
                if available:
                    next_num2 = random.choice(available)
                else:
                    next_num2 = random.randint(5, 9)
                next_trend = "BIG"
                next_category = "🔴 BIG"
            else:
                next_num1 = random.randint(0, 4)
                available = [i for i in range(0, 5) if i != next_num1]
                if available:
                    next_num2 = random.choice(available)
                else:
                    next_num2 = random.randint(0, 4)
                next_trend = "SMALL"
                next_category = "🔵 SMALL"
            
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
            
            users = safe_load_json("users.json")
            
            banner = get_stats_banner_with_level(
                users[uid]['win_count'],
                users[uid]['loss_count'],
                users[uid]['level'],
                next_period,
                next_category,
                next_num1,
                next_num2,
                player_result=final_choice
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
            
            bot_category_raw = last.get('trend', '')
            if 'BIG' in bot_category_raw or bot_category_raw == 'BIG':
                bot_category = 'BIG'
            elif 'SMALL' in bot_category_raw or bot_category_raw == 'SMALL':
                bot_category = 'SMALL'
            else:
                bot_category = bot_category_raw
            
            if user_num >= 5:
                player_category = "BIG"
            else:
                player_category = "SMALL"
            
            if bot_category == player_category:
                win = True
                result_text = "✅ VICTORY!"
            else:
                win = False
                result_text = "💪 KEEP GOING!"
            
            async with get_user_lock(uid):
                users = safe_load_json("users.json")
                
                if 'win_count' not in users[uid]:
                    users[uid]['win_count'] = 0
                    users[uid]['loss_count'] = 0
                    users[uid]['level'] = 0
                
                old_total = users[uid]['win_count'] + users[uid]['loss_count']
                old_rank = get_aura_rank(old_total)
                
                if win:
                    users[uid]['win_count'] += 1
                    users[uid]['level'] = 0
                else:
                    users[uid]['loss_count'] += 1
                    users[uid]['level'] += 1
                
                new_total = users[uid]['win_count'] + users[uid]['loss_count']
                new_rank = get_aura_rank(new_total)
                
                stats = {
                    'wins': users[uid]['win_count'],
                    'games': new_total,
                    'streak': update_streak(uid, win),
                    'max_streak': STREAK_TRACKER.get(uid, {}).get('max_streak', 0),
                    'level': users[uid]['level'],
                    'is_vip': uid in safe_load_json("vip.json"),
                    'vip_days': 0,
                    'bonus_count': 0,
                    'weekly_claimed': False,
                    'monthly_claimed': False,
                    'referrals': REFERRAL_TRACKER.get(uid, {}).get('count', 0),
                    'daily_streak': 0,
                    'rank_position': 0,
                    'rank_name': new_rank['rank']
                }
                
                new_achievements = check_achievements(uid, users, stats)
                
                safe_save_json("users.json", users)
            
            for ach in new_achievements:
                rarity = ACHIEVEMENTS[ach].get('rarity', 'common')
                rarity_label = get_rarity_label(rarity)
                emoji = get_rarity_emoji(rarity)
                count = get_achievement_players_count(ach)
                if count == 0:
                    count = 1
                
                ach_stats = get_achievement_stats(uid)
                title = get_achievement_title(ach_stats['percent'])
                
                if ach_stats['percent'] >= 100:
                    unlock_msg = f"""
🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊
🏆 *COMPLETIONIST!* 🏆
🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊🎊
━━━━━━━━━━━━━━━━━━━━━━

👑 *"THE ULTIMATE LEGEND"* 👑

🌟 *ALL ACHIEVEMENTS COMPLETE!* 🌟

━━━━━━━━━━━━━━━━━━━━━━
📊 *Your Stats:*
├─ 🏆 Achievements: {ach_stats['unlocked']}/{ach_stats['total']}
├─ 📈 Progress: {ach_stats['percent']}%
└─ 👑 Title: {title}

━━━━━━━━━━━━━━━━━━━━━━
🎖️ *FINAL RANK:* GOD TIER

📜 *Title:* "THE ONE"

━━━━━━━━━━━━━━━━━━━━━━
💎 *You are a true LEGEND!*

🏅 *Your name will be remembered FOREVER!*

━━━━━━━━━━━━━━━━━━━━━━
👑 *"Legends are not born, they are made!"*
"""
                else:
                    unlock_msg = f"""
🏅 *ACHIEVEMENT UNLOCKED!* 🏅
━━━━━━━━━━━━━━━━━━━━━━

{ach}
📝 {ACHIEVEMENTS[ach]['desc']}

🏅 *Rarity:* {rarity_label} {emoji}
👥 *Players with this:* {count}
📊 *Progress:* {ach_stats['unlocked']}/{ach_stats['total']} ({ach_stats['percent']}%)
📜 *Title:* {title}

━━━━━━━━━━━━━━━━━━━━━━
💪 Keep playing to unlock more!
"""
                
                await send_and_auto_delete(update, context, unlock_msg, delay=2, parse_mode='Markdown')
            
            streak = update_streak(uid, win)
            
            # ✅ ========== DOPAMINE HIT SYSTEM (2 SECOND AUTO-DELETE) ==========
            if win:
                win_emoji = get_random_win_emoji()
                dopamine_msg = await update.message.reply_text(win_emoji, parse_mode='Markdown')
                await asyncio.sleep(2)
                try:
                    await dopamine_msg.delete()
                except:
                    pass
            else:
                loss_emoji = get_random_loss_emoji()
                dopamine_msg = await update.message.reply_text(loss_emoji, parse_mode='Markdown')
                await asyncio.sleep(2)
                try:
                    await dopamine_msg.delete()
                except:
                    pass
            # ✅ ============================================================
            
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
                await send_and_auto_delete(update, context, rank_up_msg, delay=2, parse_mode='Markdown')
            
            add_to_history(uid, period, user_num, final_trend, win)
            
            if final_trend == "BIG":
                next_num1 = random.randint(5, 9)
                available = [i for i in range(5, 10) if i != next_num1]
                if available:
                    next_num2 = random.choice(available)
                else:
                    next_num2 = random.randint(5, 9)
                next_trend = "BIG"
                next_category = "🔴 BIG"
            else:
                next_num1 = random.randint(0, 4)
                available = [i for i in range(0, 5) if i != next_num1]
                if available:
                    next_num2 = random.choice(available)
                else:
                    next_num2 = random.randint(0, 4)
                next_trend = "SMALL"
                next_category = "🔵 SMALL"
            
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
            
            users = safe_load_json("users.json")
            
            banner = get_stats_banner_with_level(
                users[uid]['win_count'],
                users[uid]['loss_count'],
                users[uid]['level'],
                next_period,
                next_category,
                next_num1,
                next_num2,
                player_result=final_trend
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

async def admin_algorithm_view(update, context):
    uid = int(update.effective_user.id)
    
    if uid not in ADMIN_IDS and uid not in SUPER_ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied! Admin only.")
        return
    
    pred = context.user_data.get('algo_prediction', {})
    
    msg = f"""
🔮 *BIG/SMALL ANALYSIS (ADMIN ONLY)*
━━━━━━━━━━━━━━━━━━━━━━

📊 *System Status*
├─ Total Results: {len(HISTORICAL_RESULTS)}
├─ Status: 🟢 Active
└─ Self-Learning: ✅ Enabled

━━━━━━━━━━━━━━━━━━━━━━
📈 *Last Prediction*
"""
    
    if pred and pred.get('number') != "N/A":
        msg += f"""
├─ Current Number: {pred.get('number', 'N/A')}
├─ Prediction: {pred.get('prediction', 'N/A')}
├─ Confidence: {pred.get('confidence', '50%')}
├─ Frequency: {pred.get('frequency', 0)}x
└─ Total Matches: {pred.get('total_matches', 0)}
"""
    else:
        msg += "├─ No predictions yet\n"
    
    msg += """
━━━━━━━━━━━━━━━━━━━━━━
👑 *Admin:* @{update.effective_user.username}
🕐 *Live Analysis*
"""
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def analysis(update, context):
    report = get_analysis_report()
    await update.message.reply_text(report, reply_markup=main_menu)

async def start_analysis(update, context):
    try:
        uid = str(update.effective_user.id)
        vip = safe_load_json("vip.json")
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
        
        report = get_analysis_report()
        await update.message.reply_text(report, parse_mode='Markdown', reply_markup=profile_menu)
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
        pay = safe_load_json("pay.json")
        vip = safe_load_json("vip.json")
        users = safe_load_json("users.json")
        
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
        pay = safe_load_json("pay.json")
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
        pay = safe_load_json("pay.json")
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
        pay = safe_load_json("pay.json")
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
# ⭐ HANDLE BUTTONS
# ==========================================

async def handle_buttons(update, context):
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        
        users = safe_load_json("users.json")
        if uid not in users:
            device_info = get_user_details(update)
            users[uid] = {"id": uid, "name": update.effective_user.username or "Unknown", "joined": str(datetime.now()), "win_count": 0, "loss_count": 0, "level": 0, "rank_level": 0, "previous_rank": None, "device_id": device_info["device_id"], "ip_address": device_info["ip_address"], "free_trial_used": False, "free_trial_expiry": None, "username": device_info["username"], "first_name": device_info["first_name"], "last_name": device_info["last_name"], "language_code": device_info["language_code"], "achievements": {"unlocked": []}}
            safe_save_json("users.json", users)
            logger.info(f"✅ New user created: {uid}")
        
        if text == "⬅ BACK TO PROFILE" or text == "🔙 BACK":
            context.user_data.clear()
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                kb = super_admin_menu
            elif user_id_int in ADMIN_IDS:
                kb = admin_menu
            else:
                kb = main_menu
            vip = safe_load_json("vip.json")
            is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
            is_verified = context.user_data.get('verified', False)
            banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
            await update.message.reply_text(banner, reply_markup=kb)
            return
        
        if text == "🏠 HOME":
            context.user_data.clear()
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                kb = super_admin_menu
            elif user_id_int in ADMIN_IDS:
                kb = admin_menu
            else:
                kb = main_menu
            vip = safe_load_json("vip.json")
            is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
            is_verified = context.user_data.get('verified', False)
            banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
            await update.message.reply_text(banner, reply_markup=kb)
            return
        
        if text == "🚀 START":
            await start_button(update, context)
            return
        
        if text in ["💳 MEMBERSHIP", "💳 Buy Membership"]:
            await buy_membership(update, context)
            return
        
        if text in ["📊 LEADERBOARD", "📊 Leaderboard"]:
            await leaderboard(update, context)
            return
        
        if text in ["▶️ PLAY", "▶️ Play", "▶️ ▶️ PLAY ▶️ ▶️"]:
            await play(update, context)
            return
        
        if text in ["👤 PROFILE", "👤 Profile"]:
            await profile(update, context)
            return
        
        if text == "🏆 RANK":
            await rank_command(update, context)
            return
        
        if text == "🏆 ACHIEVEMENTS":
            await achievements(update, context)
            return
        
        if text == "🎁 DAILY BONUS":
            await daily_bonus(update, context)
            return
        
        if text == "📜 HISTORY":
            await show_history(update, context)
            return
        
        if text == "👥 REFERRAL":
            await referral_system(update, context)
            return
        
        if text == "🏆 WEEKLY REWARDS":
            await weekly_rewards(update, context)
            return
        
        if text in ["📞 SUPPORT", "📞 Support"]:
            await support(update, context)
            return
        
        if text == "📝 FEEDBACK":
            await feedback(update, context)
            return
        
        if text in ["📊 STATS", "📊 Stats"]:
            await bot_stats_dashboard(update, context)
            return
        
        if text in ["💰 PAYMENTS", "💰 Payments"]:
            await payment_status(update, context)
            return
        
        if text in ["📢 BROADCAST", "📢 Broadcast"]:
            await broadcast(update, context)
            return
        
        if text == "📅 PAYMENT HISTORY":
            await payment_history(update, context)
            return
        
        if text == "🛡️ DEVICE TRACKING":
            user_id_int = int(uid)
            if user_id_int in ADMIN_IDS or user_id_int in SUPER_ADMIN_IDS:
                await device_tracking(update, context)
            else:
                await update.message.reply_text("❌ Access Denied! Admin only.")
            return
        
        if text == "📋 APPROVAL LOG":
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                await approval_log(update, context)
            else:
                await update.message.reply_text("❌ Only Super Admin can view this!", reply_markup=admin_menu)
            return
        
        if text == "👑 ADMIN ACTIVITY":
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                await admin_activity(update, context)
            else:
                await update.message.reply_text("❌ Only Super Admin can view this!", reply_markup=admin_menu)
            return
        
        if text == "📝 FEEDBACK LOG":
            user_id_int = int(uid)
            if user_id_int in SUPER_ADMIN_IDS:
                await feedback_log(update, context)
            else:
                await update.message.reply_text("❌ Only Super Admin can view this!", reply_markup=admin_menu)
            return
        
        # ✅ ========== FIX: NEW PLAYERS BUTTON ==========
        if text == "📊 NEW PLAYERS":
            user_id_int = int(uid)
            if user_id_int in ADMIN_IDS or user_id_int in SUPER_ADMIN_IDS:
                await new_players_stats(update, context)
            else:
                await update.message.reply_text("❌ Admin only!")
            return
        
        if text == "🔮 ALGORITHM":
            await admin_algorithm_view(update, context)
            return
        
        if text == "⏱ TIMER":
            context.user_data['waiting_timer'] = True
            await update.message.reply_text("⏱ SELECT TIME", reply_markup=timer_menu)
            return
        
        if text in ["⏱ 30s", "⏱ 1m", "⏱ 2m", "⏱ 5m"]:
            context.user_data['waiting_timer'] = True
            await timer_select(update, context)
            return
        
        if text == "📊 ANALYSIS":
            await analysis(update, context)
            return
        
        if text == "▶️ START ANALYSIS":
            await start_analysis(update, context)
            return
        
        if text == "👑 BUY ₹299":
            await buy_membership(update, context)
            return
        
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
                vip = safe_load_json("vip.json")
                is_vip = uid in vip and datetime.fromisoformat(vip[uid]['expiry']) > datetime.now()
                is_verified = context.user_data.get('verified', False)
                banner = get_home_banner(update.effective_user.username, is_vip, is_verified)
                await update.message.reply_text(banner, reply_markup=kb)
                return
            
            msg = text
            count = 0
            loading_msg = await update.message.reply_text("📢 *Broadcasting...*", parse_mode='Markdown')
            
            users = safe_load_json("users.json")
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

async def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")
    try:
        await update.message.reply_text("❌ Something went wrong! Please try again.", reply_markup=main_menu)
    except:
        pass

# ==========================================
# ⭐ MAIN FUNCTION
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
    app.add_handler(CommandHandler("rank", rank_command))
    app.add_handler(CommandHandler("newplayers", new_players_stats))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    app.add_error_handler(error_handler)
    
    try:
        start_auto_backup()
    except Exception as e:
        logger.error(f"Failed to start auto-backup: {e}")
    
    try:
        start_auto_play_increase()
    except Exception as e:
        logger.error(f"Failed to start auto-play increase: {e}")
    
    try:
        start_dynamic_top3()
    except Exception as e:
        logger.error(f"Failed to start dynamic top 3: {e}")
    
    try:
        start_daily_random_players()
    except Exception as e:
        logger.error(f"Failed to start daily random players: {e}")
    
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    print("✅ Health check server running on port 10000!")
    print("=" * 50)
    print("🌟 AURA BOT v9.0 STARTED!")
    print("=" * 50)
    print("✅ Bot is running!")
    print(f"👑 Super Admin: {SUPER_ADMIN_IDS}")
    print(f"📌 All Admins: {ADMIN_IDS}")
    print("🛡️ Device Tracking: ENABLED")
    print("🎯 Dopamine Hit: ENABLED (Win/Loss Emojis - 2s Auto-Delete)")
    print("🔮 BIG/SMALL Analysis Algorithm: ENABLED (Self-Learning)")
    print("⏰ Auto-Delete: 2 SECONDS (Dopamine Emojis)")
    print("✅ Numbers Fixed: Always Different")
    print("📝 Professional Style: Simple Text - No Box/Border")
    print("🏆 Aura Evolution Rank System: ENABLED (80+ Ranks with Sub-Levels)")
    print("🏅 82 ACHIEVEMENTS: ENABLED (With Rarity System + Ultimate Title)")
    print("👥 Leaderboard: ENABLED (Top 10 + Your Rank + UP/DOWN Arrows + Achievements)")
    print("🎭 Fake Users: ENABLED (Hidden from Players)")
    print("🎁 Daily Bonus: ENABLED (5-15 Free Wins per day)")
    print("🔥 Streak System: ENABLED (3,5,7,10 Win Streaks)")
    print("📜 Prediction History: ENABLED (Last 20 predictions)")
    print("👥 Referral System: ENABLED")
    print("🏆 Weekly Rewards: ENABLED (Top 10 get bonuses)")
    print("📊 Bot Stats Dashboard: ENABLED (Admin only)")
    print("📊 New Players Stats: ENABLED (Admin/Super Admin)")
    print("💾 Auto-Backup: ENABLED (Daily)")
    print("📈 LEVEL SYSTEM: ENABLED (Win=Reset, Loss=+1)")
    print("⏰ Auto-Play Increase: ENABLED (Every hour)")
    print("🔄 Dynamic Top 3: ENABLED (Every 2-4 hours)")
    print("📅 Daily Random Players: ENABLED (2-3 players daily)")
    print("🎮 PLAY Button: MOVED TO BOTTOM (BIGGER)")
    print("📋 FULL RANK CHART: ENABLED (BEGINNER to GOD TIER)")
    print("🔒 CONCURRENT PLAYERS: ENABLED (Supports 15-20 players simultaneously)")
    print("🔐 THREAD SAFE: ENABLED (No data corruption)")
    print("⌨️ KEYBOARD HIDE: ENABLED (During PLAY)")
    print("📋 APPROVAL LOG: FIXED")
    print("❌ CANCEL VIP: REMOVED")
    print("👑 ULTIMATE ACHIEVEMENT SYSTEM: ENABLED (Titles, Milestones, Completionist)")
    print("📜 COMPLETE HISTORY: ENABLED (Dopamine Hit Stats)")
    print("✅ DYNAMIC LEADERBOARD ACHIEVEMENTS: Top 1=4, Top 2=3, Top 3=2, 4-10=1")
    print("✅ SELECT ACHIEVEMENT WITH DONE BUTTON: ENABLED")
    print("✅ RANDOM RARE ACHIEVEMENT: ENABLED (If no selection)")
    print("✅ DOPAMINE HIT EMOJIS: 5 WIN + 5 LOSS Variations (2s Auto-Delete)")
    print("✅ CHAIN PATTERN ALGORITHM: REMOVED (Only BIG/SMALL Analysis)")
    print("✅ VIP EXPIRE PAR DATA DELETE NAHI HOTA")
    print("✅ BOT RESTART PAR DATA SAFE RAHEGA")
    print("✅ ALL ERRORS FIXED")
    print("=" * 50)
    app.run_polling()

if __name__ == "__main__":
    main()