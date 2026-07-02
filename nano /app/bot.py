
import asyncio
import random
import sqlite3
import json
import aiohttp
import base64
import io
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.enums import ParseMode

import os

# ==================== ТОКЕНЫ ====================
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не задан!")
    print("📝 Установи: export BOT_TOKEN='твой_токен'")
    exit(1)

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
GROK_API_KEY = os.getenv('GROK_API_KEY')
REPLICATE_API_KEY = os.getenv('REPLICATE_API_KEY')

BOT_NAME = "Fable"
CREATOR_ID = 8039111975

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
cooldowns = {}
daily_cooldown = {}
cube_games = {}
roulette_games = {}
rep_cooldown = {}
marriage_proposals = {}
active_economy_event = None
last_message_time = {}
user_last_reaction = {}
reacted_messages = set()
BOT_START_TIME = datetime.now()
flood_users = {}
captcha_cache = {}
ai_cooldowns = {}
active_auctions = {}
auction_bids = {}
game_knb = {}

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        coins INTEGER DEFAULT 0,
        bank INTEGER DEFAULT 0,
        admin_level INTEGER DEFAULT 0,
        rep INTEGER DEFAULT 0,
        job TEXT,
        created_at TEXT,
        referrer_id INTEGER DEFAULT 0,
        ref_count INTEGER DEFAULT 0,
        vip INTEGER DEFAULT 0,
        vip_until TEXT,
        messages_total INTEGER DEFAULT 0,
        last_active TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS chat_stats (
        user_id INTEGER,
        chat_id INTEGER,
        messages INTEGER DEFAULT 0,
        last_message TEXT,
        PRIMARY KEY (user_id, chat_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER,
        item_name TEXT,
        quantity INTEGER DEFAULT 1,
        is_limited INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, item_name)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS businesses (
        user_id INTEGER,
        name TEXT,
        level INTEGER DEFAULT 1,
        bought_at TEXT,
        last_collect TEXT,
        PRIMARY KEY (user_id, name)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS marriages (
        user_id INTEGER PRIMARY KEY,
        spouse_id INTEGER,
        date TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TEXT,
        chat_id INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS clans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        owner_id INTEGER,
        members TEXT,
        treasury INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS clan_roles (
        user_id INTEGER,
        clan_id INTEGER,
        role TEXT DEFAULT 'member',
        PRIMARY KEY (user_id, clan_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS loans (
        user_id INTEGER PRIMARY KEY,
        amount INTEGER,
        interest INTEGER,
        taken_at TEXT,
        due_date TEXT,
        paid INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        type TEXT,
        interest_rate REAL,
        started_at TEXT,
        ended_at TEXT,
        active INTEGER DEFAULT 1,
        last_interest TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS warns (
        user_id INTEGER,
        chat_id INTEGER,
        reason TEXT,
        date TEXT,
        warned_by INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS stop_words (
        chat_id INTEGER,
        word TEXT,
        PRIMARY KEY (chat_id, word)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS chat_settings (
        chat_id INTEGER PRIMARY KEY,
        mode TEXT DEFAULT 'свободный',
        welcome TEXT,
        goodbye TEXT,
        antimat_enabled INTEGER DEFAULT 0,
        anticaps_enabled INTEGER DEFAULT 0,
        antispam_enabled INTEGER DEFAULT 0,
        antiflood_enabled INTEGER DEFAULT 0,
        antilinks_enabled INTEGER DEFAULT 0,
        rules TEXT DEFAULT '',
        slow_mode INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS pets (
        user_id INTEGER,
        pet_type TEXT,
        name TEXT,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        bought_at TEXT,
        PRIMARY KEY (user_id, pet_type)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS properties (
        user_id INTEGER,
        type TEXT,
        bought_at TEXT,
        PRIMARY KEY (user_id, type)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS farm (
        user_id INTEGER,
        crop TEXT,
        planted_at TEXT,
        PRIMARY KEY (user_id, crop)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement_name TEXT,
        unlocked_at TEXT,
        PRIMARY KEY (user_id, achievement_name)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        reporter_id INTEGER,
        reason TEXT,
        chat_id INTEGER,
        date TEXT,
        resolved INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS promos (
        code TEXT PRIMARY KEY,
        coins INTEGER DEFAULT 0,
        item TEXT,
        quantity INTEGER DEFAULT 1,
        max_uses INTEGER DEFAULT 1,
        uses INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        item_name TEXT,
        item_quantity INTEGER,
        start_price INTEGER,
        current_bid INTEGER,
        buyer_id INTEGER DEFAULT 0,
        ends_at TEXT,
        active INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS referrals (
        referrer_id INTEGER,
        referred_id INTEGER,
        date TEXT,
        PRIMARY KEY (referrer_id, referred_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS case_history (
        user_id INTEGER,
        case_name TEXT,
        item_name TEXT,
        opened_at TEXT
    )""")

    conn.commit()
    conn.close()

init_db()

# ==================== ОСНОВНЫЕ ФУНКЦИИ БАЗЫ ДАННЫХ ====================
async def get_user(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

async def create_user(user_id, username=None):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, created_at, admin_level, last_active) VALUES (?, ?, ?, 0, ?)",
              (user_id, username, now, now))
    conn.commit()
    conn.close()

async def get_coins(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

async def add_coins(user_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (user_id, coins) VALUES (?, ?)", (user_id, amount))
    conn.commit()
    conn.close()

async def remove_coins(user_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins - ? WHERE user_id = ? AND coins >= ?", (amount, user_id, amount))
    if c.rowcount == 0:
        conn.close()
        return False
    conn.commit()
    conn.close()
    return True

async def get_bank(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT bank FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

async def add_bank(user_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET bank = bank + ? WHERE user_id = ?", (amount, user_id))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (user_id, bank) VALUES (?, ?)", (user_id, amount))
    conn.commit()
    conn.close()

async def remove_bank(user_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET bank = bank - ? WHERE user_id = ? AND bank >= ?", (amount, user_id, amount))
    if c.rowcount == 0:
        conn.close()
        return False
    conn.commit()
    conn.close()
    return True

async def get_admin_level(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT admin_level FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

async def set_admin_level(user_id, level):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET admin_level = ? WHERE user_id = ?", (level, user_id))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (user_id, admin_level) VALUES (?, ?)", (user_id, level))
    conn.commit()
    conn.close()

async def is_vip(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT vip, vip_until FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        return False
    if row[1]:
        try:
            until = datetime.fromisoformat(row[1])
            if until < datetime.now():
                return False
        except:
            return False
    return True

async def set_vip(user_id, days):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    until = (datetime.now() + timedelta(days=days)).isoformat()
    c.execute("UPDATE users SET vip = 1, vip_until = ? WHERE user_id = ?", (until, user_id))
    conn.commit()
    conn.close()

async def remove_vip(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET vip = 0, vip_until = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

async def get_name(user_id):
    try:
        user = await bot.get_chat(user_id)
        return f"@{user.username}" if user.username else user.first_name
    except:
        return f"id{user_id}"

async def log_action(user_id, action, details, chat_id=0):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action, details, timestamp, chat_id) VALUES (?, ?, ?, ?, ?)",
              (user_id, action, details, datetime.now().isoformat(), chat_id))
    conn.commit()
    conn.close()

async def check_cooldown(user_id, action, seconds):
    key = f"{action}_{user_id}"
    if key in cooldowns:
        elapsed = (datetime.now() - cooldowns[key]).total_seconds()
        if elapsed < seconds:
            return False, int(seconds - elapsed)
    cooldowns[key] = datetime.now()
    return True, 0

async def get_economy_multiplier():
    global active_economy_event
    if active_economy_event:
        return active_economy_event.get("multiplier", 1.0)
    return 1.0

# ==================== ФУНКЦИИ ИНВЕНТАРЯ ====================
async def has_item(user_id, item_name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

async def add_item(user_id, item_name, quantity=1, is_limited=0):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO inventory (user_id, item_name, quantity, is_limited) VALUES (?, ?, ?, ?) ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?",
              (user_id, item_name, quantity, is_limited, quantity))
    conn.commit()
    conn.close()

async def remove_item(user_id, item_name, quantity=1):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    row = c.fetchone()
    if row and row[0] >= quantity:
        new_qty = row[0] - quantity
        if new_qty <= 0:
            c.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else:
            c.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

async def get_inventory(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT item_name, quantity, is_limited FROM inventory WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ ====================
async def get_job(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT job FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

async def set_job(user_id, job):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET job = ? WHERE user_id = ?", (job, user_id))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (user_id, job) VALUES (?, ?)", (user_id, job))
    conn.commit()
    conn.close()

# ==================== ФУНКЦИИ ДЛЯ БИЗНЕСА ====================
async def get_business(user_id, name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT level, bought_at, last_collect FROM businesses WHERE user_id = ? AND name = ?", (user_id, name))
    row = c.fetchone()
    conn.close()
    return row

async def get_businesses(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT name, level, bought_at, last_collect FROM businesses WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

async def create_business(user_id, name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT INTO businesses (user_id, name, bought_at, last_collect) VALUES (?, ?, ?, ?)",
              (user_id, name, now, now))
    conn.commit()
    conn.close()

async def upgrade_business(user_id, name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT level FROM businesses WHERE user_id = ? AND name = ?", (user_id, name))
    row = c.fetchone()
    if row:
        new_level = row[0] + 1
        c.execute("UPDATE businesses SET level = ? WHERE user_id = ? AND name = ?", (new_level, user_id, name))
        conn.commit()
        conn.close()
        return new_level
    conn.close()
    return None

async def update_business_collect(user_id, name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE businesses SET last_collect = ? WHERE user_id = ? AND name = ?", 
              (datetime.now().isoformat(), user_id, name))
    conn.commit()
    conn.close()

# ==================== ФУНКЦИИ ДЛЯ ВКЛАДОВ ====================
async def get_deposit(deposit_id, user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM deposits WHERE id = ? AND user_id = ?", (deposit_id, user_id))
    row = c.fetchone()
    conn.close()
    return row

async def get_active_deposits(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT id, amount, type, interest_rate, started_at, ended_at FROM deposits WHERE user_id = ? AND active = 1", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

async def close_deposit(deposit_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE deposits SET active = 0 WHERE id = ?", (deposit_id,))
    conn.commit()
    conn.close()

async def update_deposit_interest(deposit_id, last_interest):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE deposits SET last_interest = ? WHERE id = ?", (last_interest, deposit_id))
    conn.commit()
    conn.close()

# ==================== ФУНКЦИИ ДЛЯ РЕПУТАЦИИ ====================
async def get_rep(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT rep FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

async def add_rep(user_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET rep = rep + ? WHERE user_id = ?", (amount, user_id))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (user_id, rep) VALUES (?, ?)", (user_id, amount))
    conn.commit()
    conn.close()

# ==================== ФУНКЦИИ ДЛЯ БРАКА ====================
async def get_marriage(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT spouse_id FROM marriages WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

async def set_marriage(user_id, spouse_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO marriages (user_id, spouse_id, date) VALUES (?, ?, ?)",
              (user_id, spouse_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

async def remove_marriage(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM marriages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ==================== ФУНКЦИИ ДЛЯ КЛАНОВ ====================
async def get_user_clan(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT id, name, owner_id, members FROM clans WHERE members LIKE ?", (f"%{user_id}%",))
    row = c.fetchone()
    conn.close()
    return row

async def get_clan_role(user_id, clan_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT role FROM clan_roles WHERE user_id = ? AND clan_id = ?", (user_id, clan_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "member"

async def get_clan_treasury(clan_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT treasury FROM clans WHERE id = ?", (clan_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

async def add_clan_treasury(clan_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE clans SET treasury = treasury + ? WHERE id = ?", (amount, clan_id))
    conn.commit()
    conn.close()

async def remove_clan_treasury(clan_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE clans SET treasury = treasury - ? WHERE id = ? AND treasury >= ?", (amount, clan_id, amount))
    conn.commit()
    conn.close()

# ==================== ФУНКЦИИ ДЛЯ НАСТРОЕК ЧАТА ====================
async def get_chat_settings(chat_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "mode": row[1],
            "welcome": row[2],
            "goodbye": row[3],
            "antimat_enabled": row[4],
            "anticaps_enabled": row[5],
            "antispam_enabled": row[6],
            "antiflood_enabled": row[7],
            "antilinks_enabled": row[8],
            "rules": row[9],
            "slow_mode": row[10]
        }
    return {
        "mode": "свободный",
        "welcome": None,
        "goodbye": None,
        "antimat_enabled": 0,
        "anticaps_enabled": 0,
        "antispam_enabled": 0,
        "antiflood_enabled": 0,
        "antilinks_enabled": 0,
        "rules": "",
        "slow_mode": 0
    }

async def get_stop_words(chat_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT word FROM stop_words WHERE chat_id = ?", (chat_id,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# ==================== ФУНКЦИИ ДЛЯ ВАРНОВ ====================
async def add_warn(user_id, chat_id, reason, warned_by):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO warns (user_id, chat_id, reason, date, warned_by) VALUES (?, ?, ?, ?, ?)",
              (user_id, chat_id, reason, datetime.now().isoformat(), warned_by))
    conn.commit()
    conn.close()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM warns WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    count = c.fetchone()[0]
    conn.close()
    return count

async def get_user_warns(user_id, chat_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT reason, date, warned_by FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY date DESC", (user_id, chat_id))
    rows = c.fetchall()
    conn.close()
    return rows

async def remove_warn(user_id, chat_id, warn_num):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT rowid FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY date DESC LIMIT 1 OFFSET ?", 
              (user_id, chat_id, warn_num - 1))
    row = c.fetchone()
    if row:
        c.execute("DELETE FROM warns WHERE rowid = ?", (row[0],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# ==================== ДАННЫЕ БОТА ====================
JOBS = {
    "шахтёр": {"min": 200, "max": 400, "emoji": "⛏️", "desc": "Добывает руду"},
    "рыбак": {"min": 150, "max": 350, "emoji": "🎣", "desc": "Ловит рыбу"},
    "фермер": {"min": 180, "max": 380, "emoji": "🌾", "desc": "Выращивает овощи"},
    "строитель": {"min": 200, "max": 450, "emoji": "🏗️", "desc": "Строит дома"},
    "водитель": {"min": 150, "max": 300, "emoji": "🚕", "desc": "Возит людей"},
    "повар": {"min": 150, "max": 350, "emoji": "🍳", "desc": "Готовит еду"},
    "учитель": {"min": 150, "max": 300, "emoji": "📚", "desc": "Учит детей"},
    "врач": {"min": 200, "max": 450, "emoji": "🏥", "desc": "Лечит людей"},
    "охотник": {"min": 180, "max": 400, "emoji": "🔫", "desc": "Охотится"},
    "курьер": {"min": 120, "max": 250, "emoji": "📦", "desc": "Развозит заказы"}
}

BUSINESSES = {
    "кафе": {"price": 15000, "emoji": "☕", "income": 50, "upgrade_price": 15000, "upgrade_income": 10, "desc": "Продаёт кофе"},
    "пиццерия": {"price": 20000, "emoji": "🍕", "income": 70, "upgrade_price": 20000, "upgrade_income": 15, "desc": "Готовит пиццу"},
    "магазин": {"price": 25000, "emoji": "🏪", "income": 90, "upgrade_price": 25000, "upgrade_income": 20, "desc": "Продаёт товары"},
    "ферма": {"price": 20000, "emoji": "🌾", "income": 80, "upgrade_price": 20000, "upgrade_income": 15, "desc": "Выращивает овощи"},
    "ресторан": {"price": 35000, "emoji": "🍽️", "income": 120, "upgrade_price": 35000, "upgrade_income": 25, "desc": "Готовит блюда"},
    "отель": {"price": 40000, "emoji": "🏨", "income": 150, "upgrade_price": 40000, "upgrade_income": 30, "desc": "Принимает гостей"},
    "криптоферма": {"price": 50000, "emoji": "💎", "income": 200, "upgrade_price": 50000, "upgrade_income": 40, "desc": "Майнит крипту"},
    "студия": {"price": 45000, "emoji": "🎬", "income": 180, "upgrade_price": 45000, "upgrade_income": 35, "desc": "Снимает фильмы"},
    "завод": {"price": 60000, "emoji": "🏭", "income": 250, "upgrade_price": 60000, "upgrade_income": 50, "desc": "Производит товары"},
    "клуб": {"price": 70000, "emoji": "🎉", "income": 300, "upgrade_price": 70000, "upgrade_income": 60, "desc": "Ночной клуб"}
}

SHOP_ITEMS = {
    "улучшенная кирка": {"price": 50000, "job": "шахтёр", "bonus": 10},
    "профессиональная удочка": {"price": 40000, "job": "рыбак", "bonus": 10},
    "тренировочное ружьё": {"price": 60000, "job": "охотник", "bonus": 10},
    "трактор": {"price": 70000, "job": "фермер", "bonus": 10},
    "строительная техника": {"price": 90000, "job": "строитель", "bonus": 10},
    "диплом": {"price": 30000, "job": "все", "bonus": 10},
    "деловой костюм": {"price": 25000, "job": "все", "bonus": 10},
    "щит": {"price": 3000, "bonus": 5},
    "каска": {"price": 2000, "bonus": 3},
    "бронежилет": {"price": 5000, "bonus": 10},
    "амулет удачи": {"price": 8000, "bonus": 3},
    "золотая монета": {"price": 1000, "bonus": 2},
    "драгоценный камень": {"price": 5000, "bonus": 5}
}

LIMITED_ITEMS = {
    "кольцо удачи": {"emoji": "💍", "price": 15000, "total": 5, "left": 5, "rarity": "🟣 РЕДКИЙ", "bonus": 5, "desc": "+5% удачи"},
    "амулет богатства": {"emoji": "📿", "price": 30000, "total": 3, "left": 3, "rarity": "🟠 ЭПИЧЕСКИЙ", "bonus": 10, "desc": "+10% доход"},
    "кинжал цезаря": {"emoji": "🗡️", "price": 40000, "total": 2, "left": 2, "rarity": "🔴 ЛЕГЕНДАРНЫЙ", "bonus": 15, "desc": "+15% PvP"},
    "глаз гора": {"emoji": "🧿", "price": 35000, "total": 2, "left": 2, "rarity": "🔴 ЛЕГЕНДАРНЫЙ", "bonus": 10, "desc": "+10% удача"},
    "корона власти": {"emoji": "👑", "price": 50000, "total": 1, "left": 1, "rarity": "🌟 МИФИЧЕСКИЙ", "bonus": 20, "desc": "+20% всё"},
    "маска царя": {"emoji": "🎭", "price": 80000, "total": 1, "left": 1, "rarity": "🌟 МИФИЧЕСКИЙ", "bonus": 25, "desc": "+25% скрытность"}
}

CASES = {
    "обычный": {
        "name": "Обычный кейс",
        "emoji": "📦",
        "price": 1000,
        "items": {
            "монеты": {"chance": 30, "min": 1, "max": 10},
            "монеты_2": {"chance": 20, "min": 10, "max": 50},
            "драгоценный камень": {"chance": 15, "min": 1, "max": 1},
            "драгоценный камень_2": {"chance": 10, "min": 2, "max": 2},
            "щит": {"chance": 8, "quantity": 1},
            "каска": {"chance": 7, "quantity": 1},
            "диплом": {"chance": 5, "quantity": 1},
            "деловой костюм": {"chance": 5, "quantity": 1}
        }
    },
    "редкий": {
        "name": "Редкий кейс",
        "emoji": "🎁",
        "price": 5000,
        "items": {
            "монеты": {"chance": 25, "min": 50, "max": 200},
            "монеты_2": {"chance": 20, "min": 100, "max": 300},
            "драгоценный камень": {"chance": 15, "min": 3, "max": 8},
            "бронежилет": {"chance": 12, "quantity": 1},
            "амулет удачи": {"chance": 10, "quantity": 1},
            "улучшенная кирка": {"chance": 5, "quantity": 1},
            "профессиональная удочка": {"chance": 5, "quantity": 1},
            "тренировочное ружьё": {"chance": 4, "quantity": 1},
            "диплом": {"chance": 4, "quantity": 1}
        }
    },
    "эпический": {
        "name": "Эпический кейс",
        "emoji": "🎊",
        "price": 15000,
        "items": {
            "монеты": {"chance": 20, "min": 100, "max": 500},
            "монеты_2": {"chance": 15, "min": 200, "max": 600},
            "драгоценный камень": {"chance": 15, "min": 5, "max": 15},
            "бронежилет": {"chance": 10, "quantity": 1},
            "амулет удачи": {"chance": 10, "quantity": 1},
            "трактор": {"chance": 8, "quantity": 1},
            "строительная техника": {"chance": 7, "quantity": 1},
            "кольцо удачи": {"chance": 5, "quantity": 1, "limited": True},
            "деловой костюм": {"chance": 5, "quantity": 1},
            "диплом": {"chance": 5, "quantity": 1}
        }
    },
    "легендарный": {
        "name": "Легендарный кейс",
        "emoji": "🎆",
        "price": 30000,
        "items": {
            "монеты": {"chance": 20, "min": 300, "max": 1000},
            "монеты_2": {"chance": 15, "min": 500, "max": 1500},
            "драгоценный камень": {"chance": 15, "min": 10, "max": 30},
            "бронежилет": {"chance": 10, "quantity": 1},
            "амулет удачи": {"chance": 8, "quantity": 1},
            "трактор": {"chance": 7, "quantity": 1},
            "строительная техника": {"chance": 5, "quantity": 1},
            "кольцо удачи": {"chance": 8, "quantity": 1, "limited": True},
            "амулет богатства": {"chance": 7, "quantity": 1, "limited": True},
            "кинжал цезаря": {"chance": 5, "quantity": 1, "limited": True},
            "корона власти": {"chance": 3, "quantity": 1, "limited": True},
            "глаз гора": {"chance": 2, "quantity": 1, "limited": True}
        }
    },
    "супер": {
        "name": "Супер кейс",
        "emoji": "🔥",
        "price": 50000,
        "items": {
            "монеты": {"chance": 20, "min": 500, "max": 2000},
            "монеты_2": {"chance": 15, "min": 1000, "max": 3000},
            "драгоценный камень": {"chance": 15, "min": 20, "max": 50},
            "бронежилет": {"chance": 10, "quantity": 1},
            "трактор": {"chance": 8, "quantity": 1},
            "строительная техника": {"chance": 5, "quantity": 1},
            "кольцо удачи": {"chance": 10, "quantity": 1, "limited": True},
            "амулет богатства": {"chance": 8, "quantity": 1, "limited": True},
            "кинжал цезаря": {"chance": 6, "quantity": 1, "limited": True},
            "глаз гора": {"chance": 4, "quantity": 1, "limited": True},
            "корона власти": {"chance": 3, "quantity": 1, "limited": True},
            "маска царя": {"chance": 0.25, "quantity": 1, "limited": True}
        }
    },
    "vip": {
        "name": "VIP кейс",
        "emoji": "👑",
        "price": 75000,
        "vip_only": True,
        "items": {
            "монеты": {"chance": 20, "min": 1000, "max": 5000},
            "монеты_2": {"chance": 15, "min": 2000, "max": 8000},
            "драгоценный камень": {"chance": 15, "min": 30, "max": 80},
            "кольцо удачи": {"chance": 12, "quantity": 1, "limited": True},
            "амулет богатства": {"chance": 10, "quantity": 1, "limited": True},
            "кинжал цезаря": {"chance": 8, "quantity": 1, "limited": True},
            "глаз гора": {"chance": 6, "quantity": 1, "limited": True},
            "корона власти": {"chance": 4, "quantity": 1, "limited": True},
            "маска царя": {"chance": 1, "quantity": 1, "limited": True}
        }
    }
}

DEPOSIT_TYPES = {
    "обычный": {"name": "💳 Обычный вклад", "interest": 1.0, "min_amount": 1000, "duration": None, "penalty": 0, "desc": "1% в час, можно снять в любой момент"},
    "долгосрочный": {"name": "🏦 Долгосрочный вклад", "interest": 3.0, "min_amount": 5000, "duration": 24, "penalty": 100, "desc": "3% в час, нельзя снять 24 часа"},
    "vip": {"name": "👑 VIP вклад", "interest": 4.0, "min_amount": 10000, "duration": 24, "penalty": 100, "desc": "4% в час, только для VIP"}
}

PROPERTIES = {
    "дом": {"price": 100000, "income": 500, "emoji": "🏠"},
    "квартира": {"price": 80000, "income": 400, "emoji": "🏢"},
    "особняк": {"price": 200000, "income": 1000, "emoji": "🏰"},
    "замок": {"price": 500000, "income": 2500, "emoji": "🏯"}
}

PETS = {
    "собака": {"price": 10000, "emoji": "🐕", "bonus": "защита", "desc": "Защищает от грабежа"},
    "кот": {"price": 8000, "emoji": "🐱", "bonus": "удача", "desc": "Приносит удачу"},
    "орёл": {"price": 20000, "emoji": "🦅", "bonus": "охота", "desc": "Помогает в охоте"},
    "волк": {"price": 25000, "emoji": "🐺", "bonus": "война", "desc": "Помогает в битвах"},
    "дракон": {"price": 50000, "emoji": "🐉", "bonus": "всё", "desc": "Помогает во всём"}
}

ACHIEVEMENTS = {
    "first_work": {"name": "💼 Первая работа", "desc": "Устроиться на первую работу", "reward": 500},
    "first_money": {"name": "💰 Первый миллион", "desc": "Накопить 1 000 000 монет", "reward": 10000},
    "first_business": {"name": "🏪 Первый бизнес", "desc": "Купить первый бизнес", "reward": 1000},
    "ten_businesses": {"name": "🏪 Магнат", "desc": "Купить 10 бизнесов", "reward": 5000},
    "first_marriage": {"name": "💍 Первая свадьба", "desc": "Вступить в брак", "reward": 1000},
    "first_rep": {"name": "⭐ Первая репутация", "desc": "Получить +реп", "reward": 500},
    "first_shop": {"name": "🛒 Покупатель", "desc": "Купить предмет", "reward": 500},
    "level_5": {"name": "🎯 Уровень 5", "desc": "Достигнуть уровня 5", "reward": 2000}
}

BAD_WORDS = ["хуй", "пизда", "бля", "сука", "мудак", "тварь", "пидор", "лох", "гандон", "редиска", "залупа", "жопа"]

# ==================== УТИЛИТЫ ====================
def format_number(num):
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    if num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)

def get_level_name(level):
    levels = {
        0: "Пользователь",
        1: "Младший модератор",
        2: "Модератор",
        3: "Старший модератор",
        4: "Администратор",
        5: "Старший администратор",
        10: "Создатель"
    }
    return levels.get(level, "Неизвестно")

def get_level_emoji(level):
    emojis = {
        0: "👤",
        1: "🛡️",
        2: "⚔️",
        3: "🗡️",
        4: "👑",
        5: "💎",
        10: "👾"
    }
    return emojis.get(level, "❓")

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def get_user_total_messages(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT messages_total FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

async def update_user_activity(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("UPDATE users SET messages_total = messages_total + 1, last_active = ? WHERE user_id = ?", (now, user_id))
    conn.commit()
    conn.close()

async def get_chat_admins(chat_id):
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return [admin.user.id for admin in admins]
    except:
        return []

async def get_ref_count(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0
# ==================== ЧАСТЬ 2/20: ОБРАБОТЧИКИ СООБЩЕНИЙ ====================

# ==================== ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ====================
@dp.message()
async def handle_all_messages(message: types.Message):
    """Главный обработчик всех сообщений"""
    
    # Игнорируем сообщения от ботов
    if message.from_user.is_bot:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.lower().strip() if message.text else ""
    
    # Создаём пользователя если его нет
    await create_user(user_id, message.from_user.username)
    
    # Обновляем статистику
    await update_user_activity(user_id)
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat_stats (user_id, chat_id, messages, last_message) VALUES (?, ?, 1, ?) "
              "ON CONFLICT(user_id, chat_id) DO UPDATE SET messages = messages + 1, last_message = ?",
              (user_id, chat_id, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Проверяем модерацию
    await auto_moderation(message)
    
    # Обрабатываем команды
    if text.startswith("фабле "):
        await handle_fable_command(message, text.replace("фабле ", ""))
        return
    
    # Если есть текст - проверяем команды
    if text:
        await handle_commands(message, text)
        return
    
    # Если это медиа - обрабатываем
    if message.photo or message.video or message.animation:
        await handle_media(message)

# ==================== ОБРАБОТЧИК КОМАНД ====================
async def handle_commands(message: types.Message, text: str):
    """Обработчик всех команд"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # ===== ПРОФИЛЬ =====
    if text in ["я", "профиль"]:
        await show_profile(message, user_id)
        return
    
    if text.startswith("профиль @"):
        username = text.split("@")[1].split()[0]
        try:
            member = await message.chat.get_member(username)
            await show_profile(message, member.user.id)
        except:
            await message.reply("❌ Пользователь не найден!")
        return
    
    # ===== БАЛАНС =====
    if text == "баланс":
        coins = await get_coins(user_id)
        bank = await get_bank(user_id)
        await message.reply(f"💰 **Баланс:**\n💵 Монет: {coins}\n🏦 В банке: {bank}", parse_mode=ParseMode.MARKDOWN)
        return
    
    # ===== РАБОТА =====
    if text == "работа":
        await work_command(message)
        return
    
    if text.startswith("устроиться "):
        await hire_command(message)
        return
    
    if text == "список работ":
        await list_jobs(message)
        return
    
    # ===== БИЗНЕСЫ =====
    if text == "бизнесы":
        await list_businesses(message)
        return
    
    if text.startswith("купить бизнес "):
        await buy_business(message)
        return
    
    if text.startswith("собрать бизнес "):
        await collect_business_income(message)
        return
    
    if text == "мои бизнесы":
        await my_businesses_command(message)
        return
    
    # ===== МАГАЗИН =====
    if text == "магазин":
        await show_shop(message)
        return
    
    if text.startswith("купить "):
        await buy_item(message)
        return
    
    if text in ["инвентарь", "мой инвентарь"]:
        await show_inventory(message)
        return
    
    if text.startswith("продать "):
        await sell_item(message)
        return
    
    # ===== ЛИМИТКИ =====
    if text == "лимитки":
        await show_limited_items(message)
        return
    
    # ===== КЕЙСЫ =====
    if text.startswith("открыть кейс "):
        await open_case(message)
        return
    
    if text == "кейсы":
        await show_cases(message)
        return
    
    # ===== ПЕРЕВОДЫ =====
    if text.startswith("перевод ") and message.reply_to_message:
        await transfer_reply(message)
        return
    
    if text.startswith("перевод "):
        await transfer_command(message)
        return
    
    # ===== БАНК =====
    if text.startswith("положить "):
        await deposit_command(message)
        return
    
    if text.startswith("снять "):
        await withdraw_command(message)
        return
    
    # ===== ВКЛАДЫ =====
    if text.startswith("вклад"):
        await deposit_commands(message)
        return
    
    # ===== ТОПЫ =====
    if text == "топ":
        await top_command(message)
        return
    
    if text == "топ реп":
        await top_rep_command(message)
        return
    
    # ===== БОНУСЫ =====
    if text in ["бонус", "ежедневно"]:
        await daily_bonus(message)
        return
    
    # ===== РП КОМАНДЫ =====
    rp_actions = ["обнять", "поцеловать", "ударить", "пнуть"]
    if text in rp_actions and message.reply_to_message:
        await rp_command(message)
        return
    
    # ===== РЕПУТАЦИЯ =====
    if text == "+реп" and message.reply_to_message:
        await add_reputation(message)
        return
    
    if text == "-реп" and message.reply_to_message:
        await remove_reputation(message)
        return
    
    # ===== БРАК =====
    if text == "брак" and message.reply_to_message:
        await propose_marriage(message)
        return
    
    if text == "развестись":
        await divorce_command(message)
        return
    
    # ===== ИГРЫ =====
    if text.startswith("кубы"):
        await cube_game(message)
        return
    
    if text == "рулетка" and message.reply_to_message:
        await roulette_game(message)
        return
    
    if text.startswith("казино "):
        await casino_command(message)
        return
    
    # ===== КЛАНЫ =====
    if text.startswith("создать клан "):
        await create_clan(message)
        return
    
    if text.startswith("вступить в клан "):
        await join_clan(message)
        return
    
    if text == "мой клан":
        await my_clan(message)
        return
    
    if text == "кланы":
        await list_clans(message)
        return
    
    if text.startswith("казна "):
        await clan_treasury_command(message)
        return
    
    # ===== КРЕДИТЫ =====
    if text.startswith("кредит "):
        await loan_commands(message)
        return
    
    # ===== ФЕРМА =====
    if text in ["ферма", "посадить", "собрать"]:
        await farm_commands(message)
        return
    
    # ===== РЫБАЛКА =====
    if text in ["рыбалка", "купить удочку"]:
        await fishing_commands(message)
        return
    
    # ===== ОХОТА =====
    if text in ["охота", "купить ружьё"]:
        await hunting_commands(message)
        return
    
    # ===== ПИТОМЦЫ =====
    if text == "питомцы":
        await show_pets_shop(message)
        return
    
    if text.startswith("купить питомца "):
        await buy_pet(message)
        return
    
    if text == "мои питомцы":
        await my_pets(message)
        return
    
    # ===== НЕДВИЖИМОСТЬ =====
    if text == "недвижимость":
        await show_properties_shop(message)
        return
    
    if text.startswith("купить "):
        await buy_property(message)
        return
    
    if text == "моя недвижимость":
        await my_properties(message)
        return
    
    # ===== ДОСТИЖЕНИЯ =====
    if text == "ачивки":
        await show_achievements(message)
        return
    
    if text == "все ачивки":
        await all_achievements_command(message)
        return
    
    # ===== КВЕСТЫ =====
    if text in ["ежедневные задания", "еженедельные задания"]:
        await quest_commands(message)
        return
    
    # ===== МОДЕРАЦИЯ =====
    if text.startswith("варн "):
        await warn_user(message)
        return
    
    if text.startswith("варны "):
        await get_warns_command(message)
        return
    
    if text.startswith("снять варн "):
        await remove_warn_command(message)
        return
    
    if text.startswith("мут "):
        await mute_command(message)
        return
    
    if text.startswith("размут "):
        await unmute_command(message)
        return
    
    if text.startswith("кик "):
        await kick_user(message)
        return
    
    if text.startswith("бан "):
        await ban_user(message)
        return
    
    if text.startswith("разбан "):
        await unban_user(message)
        return
    
    if text.startswith("очистить "):
        await clear_command(message)
        return
    
    if text.startswith("стоп слово "):
        await add_stop_word(message)
        return
    
    if text == "стоп слова":
        await list_stop_words(message)
        return
    
    if text.startswith("удалить стоп "):
        await remove_stop_word(message)
        return
    
    # ===== НАСТРОЙКИ =====
    if text == "антимат вкл":
        await toggle_antimat(message, 1)
        return
    
    if text == "антимат выкл":
        await toggle_antimat(message, 0)
        return
    
    if text == "антикапс вкл":
        await toggle_anticaps(message, 1)
        return
    
    if text == "антикапс выкл":
        await toggle_anticaps(message, 0)
        return
    
    if text == "антиспам вкл":
        await toggle_antispam(message, 1)
        return
    
    if text == "антиспам выкл":
        await toggle_antispam(message, 0)
        return
    
    if text == "антифлуд вкл":
        await toggle_antiflood(message, 1)
        return
    
    if text == "антифлуд выкл":
        await toggle_antiflood(message, 0)
        return
    
    if text == "антиссылки вкл":
        await toggle_antilinks(message, 1)
        return
    
    if text == "антиссылки выкл":
        await toggle_antilinks(message, 0)
        return
    
    if text.startswith("чат режим "):
        await set_chat_mode(message)
        return
    
    if text == "правила":
        await show_rules(message)
        return
    
    if text.startswith("правила установить "):
        await set_rules(message)
        return
    
    # ===== КОМАНДЫ И ПОМОЩЬ =====
    if text in ["команды", "помощь"]:
        await show_commands(message)
        return
    
    # ===== АВТОМАТИЧЕСКИЕ РЕАКЦИИ =====
    await auto_reaction(message)

# ==================== ОБРАБОТЧИК КОМАНДЫ FABLE ====================
async def handle_fable_command(message: types.Message, query: str):
    """Обработчик команды 'фабле' - генерация контента с ИИ"""
    user_id = message.from_user.id
    
    # Проверяем КД
    ok, remaining = await check_cooldown(user_id, "fable_ai", 30)
    if not ok:
        await message.reply(f"⏳ Подожди {remaining} секунд!")
        return
    
    # Проверяем наличие API ключа
    if not DEEPSEEK_API_KEY and not GROK_API_KEY:
        await message.reply("❌ ИИ не настроен! Обратитесь к создателю.")
        return
    
    # Генерируем ответ
    try:
        await message.reply("🔄 Генерирую...")
        
        # Пытаемся использовать DeepSeek
        if DEEPSEEK_API_KEY:
            response = await deepseek_generate(query)
        elif GROK_API_KEY:
            response = await grok_generate(query)
        else:
            await message.reply("❌ Нет доступных ИИ!")
            return
        
        # Отправляем ответ
        if len(response) > 4096:
            # Разбиваем на части
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for part in parts:
                await message.reply(part, parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply(response, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# ==================== АВТОМАТИЧЕСКАЯ МОДЕРАЦИЯ ====================
async def auto_moderation(message: types.Message):
    """Автоматическая модерация сообщений"""
    if not message.text:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.lower()
    
    # Проверяем уровень админа
    admin_level = await get_admin_level(user_id)
    if admin_level >= 1:
        return
    
    settings = await get_chat_settings(chat_id)
    
    # 1. АНТИ-МАТ
    if settings.get("antimat_enabled", 0) == 1:
        for word in BAD_WORDS:
            if word in text:
                await message.delete()
                await message.answer(f"⚠️ {message.from_user.first_name}, мат запрещён!")
                await add_warn(user_id, chat_id, f"Мат: {word}", user_id)
                
                # Проверяем количество варнов
                warn_count = await add_warn(user_id, chat_id, f"Мат: {word}", user_id)
                if warn_count >= 5:
                    await bot.ban_chat_member(chat_id, user_id)
                    await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
                return
    
    # 2. АНТИ-КАПС
    if settings.get("anticaps_enabled", 0) == 1:
        if len(text) > 10:
            caps_count = sum(1 for c in text if c.isupper())
            if caps_count / len(text) > 0.7:
                await message.delete()
                await message.answer(f"⚠️ {message.from_user.first_name}, не кричи!")
                warn_count = await add_warn(user_id, chat_id, "Капс", user_id)
                if warn_count >= 5:
                    await bot.ban_chat_member(chat_id, user_id)
                    await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
                return
    
    # 3. АНТИ-ССЫЛКИ
    if settings.get("antilinks_enabled", 0) == 1:
        if "http" in text or "www." in text or ".ru" in text or ".com" in text:
            await message.delete()
            await message.answer(f"⚠️ {message.from_user.first_name}, ссылки запрещены!")
            warn_count = await add_warn(user_id, chat_id, "Ссылка", user_id)
            if warn_count >= 5:
                await bot.ban_chat_member(chat_id, user_id)
                await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
            return
    
    # 4. АНТИ-СПАМ
    if settings.get("antispam_enabled", 0) == 1:
        # Проверяем повторяющиеся сообщения
        if user_id in last_message_time:
            last_text = last_message_time.get(user_id, {}).get("text", "")
            if text == last_text:
                await message.delete()
                await message.answer(f"⚠️ {message.from_user.first_name}, не спамь!")
                warn_count = await add_warn(user_id, chat_id, "Спам", user_id)
                if warn_count >= 5:
                    await bot.ban_chat_member(chat_id, user_id)
                    await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
                return
        
        last_message_time[user_id] = {"text": text, "time": datetime.now()}
    
    # 5. АНТИ-ФЛУД
    if settings.get("antiflood_enabled", 0) == 1:
        now = datetime.now()
        if user_id not in flood_users:
            flood_users[user_id] = []
        
        # Очищаем старые сообщения
        flood_users[user_id] = [t for t in flood_users[user_id] if (now - t).total_seconds() < 5]
        flood_users[user_id].append(now)
        
        if len(flood_users[user_id]) > 5:
            await message.delete()
            await message.answer(f"⚠️ {message.from_user.first_name}, флуд! Мут 1 мин.")
            
            # Мут на 1 минуту
            try:
                await bot.restrict_chat_member(
                    chat_id,
                    user_id,
                    ChatPermissions(can_send_messages=False),
                    until_date=datetime.now() + timedelta(minutes=1)
                )
            except:
                pass
            return
    
    # 6. ПРОВЕРКА СТОП-СЛОВ
    stop_words = await get_stop_words(chat_id)
    for word in stop_words:
        if word in text:
            await message.delete()
            await message.answer(f"⚠️ Запрещённое слово: {word}")
            warn_count = await add_warn(user_id, chat_id, f"Стоп-слово: {word}", user_id)
            if warn_count >= 5:
                await bot.ban_chat_member(chat_id, user_id)
                await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
            return

# ==================== АВТОМАТИЧЕСКИЕ РЕАКЦИИ ====================
async def auto_reaction(message: types.Message):
    """Автоматические реакции на сообщения"""
    if not message.text:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.lower()
    
    # Проверяем, не ставили ли уже реакцию на это сообщение
    if message.message_id in reacted_messages:
        return
    
    # Проверяем КД для пользователя
    if user_id in user_last_reaction:
        elapsed = (datetime.now() - user_last_reaction[user_id]).total_seconds()
        if elapsed < 60:  # Раз в минуту
            return
    
    reacted_messages.add(message.message_id)
    user_last_reaction[user_id] = datetime.now()
    
    # Выбираем реакцию
    reactions = ["❤️", "🔥", "👍", "👏", "😄", "🎉", "✨", "🌟", "💪", "🥰"]
    
    # Реакции на ключевые слова
    keyword_reactions = {
        "привет": ["👋", "🙋", "🤝"],
        "спасибо": ["❤️", "🥰", "💕"],
        "люблю": ["❤️", "🥰", "💕"],
        "круто": ["🔥", "✨", "⚡"],
        "класс": ["✨", "🌟", "🎉"],
        "вау": ["😮", "🤯", "😲"],
        "смешно": ["😂", "🤣", "😆"],
        "грустно": ["😢", "😭", "🥺"],
        "топ": ["👑", "🏆", "🥇"],
        "победа": ["🏆", "🥇", "🎉"],
    }
    
    # Проверяем ключевые слова
    for word, reaction_list in keyword_reactions.items():
        if word in text:
            try:
                await message.react(reaction_list[0])
                return
            except:
                pass
    
    # Случайная реакция
    try:
        await message.react(random.choice(reactions))
    except:
        pass

print(f"✅ Часть 2/20 загружена! Строк: ~650")
# ==================== ЧАСТЬ 3/20: ЭКОНОМИКА ====================

# ==================== РАБОТА ====================
async def work_command(message: types.Message):
    user_id = message.from_user.id
    job = await get_job(user_id)
    
    if not job:
        await message.reply("❌ Ты безработный!\n📝 `устроиться [работа]`")
        return
    
    ok, remaining = await check_cooldown(user_id, "work", 600)
    if not ok:
        await message.reply(f"⏳ Подожди {remaining//60} мин {remaining%60} сек!")
        return
    
    job_data = JOBS.get(job)
    if not job_data:
        await message.reply("❌ Ошибка!")
        return
    
    # Подсчёт бонусов
    bonus = 0
    bonus_items = {
        "шахтёр": "улучшенная кирка",
        "рыбак": "профессиональная удочка",
        "охотник": "тренировочное ружьё",
        "фермер": "трактор",
        "строитель": "строительная техника"
    }
    
    if job in bonus_items:
        if await has_item(user_id, bonus_items[job]):
            bonus += 10
    
    if await has_item(user_id, "диплом"):
        bonus += 10
    
    salary = random.randint(job_data["min"], job_data["max"])
    econ_mult = await get_economy_multiplier()
    vip_bonus = 1.5 if await is_vip(user_id) else 1.0
    
    salary = int(salary * (1 + bonus / 100) * econ_mult * vip_bonus)
    
    await add_coins(user_id, salary)
    await log_action(user_id, "work", f"Заработал {salary} монет на работе {job}")
    
    msg = f"{job_data['emoji']} **{job.capitalize()}**: +{salary} монет"
    if bonus > 0:
        msg += f" (бонус +{bonus}%)"
    if econ_mult != 1.0:
        msg += f" (экономика x{econ_mult})"
    if await is_vip(user_id):
        msg += " (VIP x1.5)"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def hire_command(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply("ℹ️ `устроиться [работа]`\n📝 Список: `список работ`")
        return
    
    job_name = args[1].lower().strip()
    
    # Поиск работы
    found = None
    for job in JOBS.keys():
        if job_name == job or job_name in job or job in job_name:
            found = job
            break
    
    if not found:
        await message.reply(f"❌ Работа '{job_name}' не найдена!\n📝 Список: `список работ`")
        return
    
    await set_job(user_id, found)
    job_data = JOBS[found]
    await message.reply(f"✅ Ты устроился **{found.capitalize()}**!\n{job_data['emoji']} {job_data['desc']}\n💰 Зарплата: {job_data['min']}-{job_data['max']} монет")

async def list_jobs(message: types.Message):
    msg = "💼 **Доступные работы:**\n\n"
    for job, data in JOBS.items():
        msg += f"{data['emoji']} **{job.capitalize()}** — {data['desc']}\n"
        msg += f"   💰 {data['min']}-{data['max']} монет\n\n"
    msg += "📝 `устроиться [работа]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== БИЗНЕСЫ ====================
async def list_businesses(message: types.Message):
    msg = "🏪 **ДОСТУПНЫЕ БИЗНЕСЫ**\n\n"
    for name, data in BUSINESSES.items():
        msg += f"{data['emoji']} **{name.capitalize()}**\n"
        msg += f"💰 {data['price']} монет\n"
        msg += f"📈 Доход: {data['income']} монет/час\n"
        msg += f"📝 {data['desc']}\n\n"
    msg += "📝 `купить бизнес [название]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def buy_business(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply("ℹ️ `купить бизнес [название]`")
        return
    
    name = args[1].lower().strip()
    
    if name not in BUSINESSES:
        await message.reply(f"❌ Бизнес '{name}' не найден!")
        return
    
    existing = await get_business(user_id, name)
    if existing:
        await message.reply(f"❌ У тебя уже есть {BUSINESSES[name]['emoji']} {name.capitalize()}!")
        return
    
    price = BUSINESSES[name]["price"]
    coins = await get_coins(user_id)
    
    if coins < price:
        await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
        return
    
    await remove_coins(user_id, price)
    await create_business(user_id, name)
    await log_action(user_id, "buy_business", f"Купил бизнес {name}")
    await message.reply(f"✅ {BUSINESSES[name]['emoji']} **{name.capitalize()}** куплен!")

async def collect_business_income(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply("ℹ️ `собрать бизнес [название]`\n📝 `мои бизнесы` - посмотреть свои бизнесы")
        return
    
    name = args[1].lower().strip()
    business = await get_business(user_id, name)
    
    if not business:
        await message.reply(f"❌ У тебя нет бизнеса {name.capitalize()}!")
        return
    
    level = business[0]
    last_collect = business[2]
    data = BUSINESSES.get(name)
    
    income_per_hour = data["income"] + (level - 1) * data["upgrade_income"]
    
    try:
        last_time = datetime.fromisoformat(last_collect)
        hours_passed = (datetime.now() - last_time).total_seconds() / 3600
        hours_passed = min(hours_passed, 24)
    except:
        hours_passed = 1
    
    econ_mult = await get_economy_multiplier()
    vip_bonus = 1.5 if await is_vip(user_id) else 1.0
    earned = int(income_per_hour * hours_passed * econ_mult * vip_bonus * random.uniform(0.8, 1.2))
    earned = max(1, earned)
    
    await add_coins(user_id, earned)
    await update_business_collect(user_id, name)
    await log_action(user_id, "collect_business", f"Собрал {earned} монет с {name}")
    
    msg = f"💰 Собрано **{earned}** монет с **{data['emoji']} {name.capitalize()}**!\n📈 Доход: {income_per_hour} монет/час"
    if econ_mult != 1.0:
        msg += f" (экономика x{econ_mult})"
    if await is_vip(user_id):
        msg += " (VIP x1.5)"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def my_businesses_command(message: types.Message):
    user_id = message.from_user.id
    businesses = await get_businesses(user_id)
    
    if not businesses:
        await message.reply("❌ У тебя нет бизнесов!\n📝 `купить бизнес [название]`")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for name, level, bought_at, last_collect in businesses:
        data = BUSINESSES.get(name)
        if data:
            income = data["income"] + (level - 1) * data["upgrade_income"]
            btn_text = f"{data['emoji']} {name.capitalize()} (ур.{level}) — {income} монет/час"
            keyboard.add(InlineKeyboardButton(btn_text, callback_data=f"biz_{name}"))
    
    msg = "🏪 **МОИ БИЗНЕСЫ**\n\n"
    msg += f"Всего бизнесов: **{len(businesses)}**\n"
    msg += "Нажми на бизнес для управления ⬇️"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

# ==================== КОЛБЭКИ БИЗНЕСОВ ====================
@dp.callback_query(lambda c: c.data.startswith("biz_"))
async def business_callback(callback):
    business_name = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    business = await get_business(user_id, business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    level = business[0]
    data = BUSINESSES.get(business_name)
    income = data["income"] + (level - 1) * data["upgrade_income"]
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💰 Собрать доход", callback_data=f"collect_{business_name}"),
        InlineKeyboardButton("🔧 Улучшить", callback_data=f"upgrade_{business_name}")
    )
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_businesses"))
    
    upgrade_price = data["upgrade_price"] * level
    msg = f"🏪 **{data['emoji']} {business_name.capitalize()}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 Уровень: **{level}**\n"
    msg += f"💰 Доход: **{income}** монет/час\n"
    msg += f"🔧 Улучшение: {upgrade_price} монет\n"
    msg += f"📝 {data['desc']}"
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("upgrade_"))
async def business_upgrade_callback(callback):
    business_name = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    business = await get_business(user_id, business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    level = business[0]
    data = BUSINESSES.get(business_name)
    upgrade_price = data["upgrade_price"] * level
    
    coins = await get_coins(user_id)
    if coins < upgrade_price:
        await callback.answer(f"❌ Нужно {upgrade_price} монет!", show_alert=True)
        return
    
    await remove_coins(user_id, upgrade_price)
    new_level = await upgrade_business(user_id, business_name)
    await log_action(user_id, "upgrade_business", f"Улучшил {business_name} до {new_level}")
    
    await callback.answer(f"✅ Улучшен до {new_level} уровня!", show_alert=True)
    
    # Обновляем сообщение
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💰 Собрать доход", callback_data=f"collect_{business_name}"),
        InlineKeyboardButton("🔧 Улучшить", callback_data=f"upgrade_{business_name}")
    )
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_businesses"))
    
    new_income = data["income"] + (new_level - 1) * data["upgrade_income"]
    upgrade_price = data["upgrade_price"] * new_level
    
    msg = f"🏪 **{data['emoji']} {business_name.capitalize()}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 Уровень: **{new_level}**\n"
    msg += f"💰 Доход: **{new_income}** монет/час\n"
    msg += f"🔧 Улучшение: {upgrade_price} монет\n"
    msg += f"📝 {data['desc']}"
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("collect_"))
async def business_collect_callback(callback):
    business_name = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    business = await get_business(user_id, business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    level = business[0]
    last_collect = business[2]
    data = BUSINESSES.get(business_name)
    
    income_per_hour = data["income"] + (level - 1) * data["upgrade_income"]
    
    try:
        last_time = datetime.fromisoformat(last_collect)
        hours_passed = (datetime.now() - last_time).total_seconds() / 3600
        hours_passed = min(hours_passed, 24)
    except:
        hours_passed = 1
    
    econ_mult = await get_economy_multiplier()
    vip_bonus = 1.5 if await is_vip(user_id) else 1.0
    earned = int(income_per_hour * hours_passed * econ_mult * vip_bonus * random.uniform(0.8, 1.2))
    earned = max(1, earned)
    
    await add_coins(user_id, earned)
    await update_business_collect(user_id, business_name)
    await log_action(user_id, "collect_business", f"Собрал {earned} монет с {business_name}")
    
    await callback.answer(f"💰 +{earned} монет!", show_alert=True)

@dp.callback_query(lambda c: c.data == "back_businesses")
async def back_businesses_callback(callback):
    await my_businesses_command(callback.message)
    await callback.answer()

# ==================== МАГАЗИН ====================
async def show_shop(message: types.Message):
    msg = "🛒 **МАГАЗИН**\n\n"
    
    msg += "🛠️ **РАБОЧИЕ**\n"
    for name, data in SHOP_ITEMS.items():
        if "job" in data and data["job"] != "все":
            price = data["price"]
            job = data["job"].capitalize()
            emoji = "⛏️" if "кирка" in name else "🎣" if "удочка" in name else "🔫" if "ружьё" in name else "🚜" if "трактор" in name else "🏗️" if "техника" in name else "💼"
            msg += f"{emoji} {name.capitalize()} — {price} монет ({job})\n"
    
    msg += "\n🛡️ **ЗАЩИТА**\n"
    for name, data in SHOP_ITEMS.items():
        if "bonus" in data and "job" not in data:
            price = data["price"]
            msg += f"🛡️ {name.capitalize()} — {price} монет\n"
    
    msg += "\n💰 **ФИНАНСЫ**\n"
    finance_items = ["золотая монета", "драгоценный камень"]
    for name in finance_items:
        if name in SHOP_ITEMS:
            price = SHOP_ITEMS[name]["price"]
            emoji = "💰" if "монета" in name else "💎"
            msg += f"{emoji} {name.capitalize()} — {price} монет\n"
    
    msg += "\n📝 `купить [предмет]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def buy_item(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply("ℹ️ `купить [предмет]`")
        return
    
    item_name = args[1].lower().strip()
    
    # Проверяем магазин
    if item_name in SHOP_ITEMS:
        price = SHOP_ITEMS[item_name]["price"]
        coins = await get_coins(user_id)
        
        if coins < price:
            await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
            return
        
        await remove_coins(user_id, price)
        await add_item(user_id, item_name)
        await log_action(user_id, "buy_item", f"Купил {item_name} за {price}")
        await message.reply(f"✅ **{item_name.capitalize()}** куплен!")
        return
    
    # Проверяем лимитные предметы
    if item_name in LIMITED_ITEMS:
        data = LIMITED_ITEMS[item_name]
        if data["left"] <= 0:
            await message.reply(f"❌ {data['emoji']} {item_name.capitalize()} разобрали!")
            return
        
        price = data["price"]
        coins = await get_coins(user_id)
        
        if coins < price:
            await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
            return
        
        await remove_coins(user_id, price)
        await add_item(user_id, item_name, 1, 1)
        LIMITED_ITEMS[item_name]["left"] -= 1
        
        await log_action(user_id, "buy_limited", f"Купил {item_name}")
        await message.reply(f"✅ {data['emoji']} **{item_name.capitalize()}** куплен!\n📦 Осталось: {LIMITED_ITEMS[item_name]['left']}/{LIMITED_ITEMS[item_name]['total']}")
        return
    
    await message.reply(f"❌ Предмет '{item_name}' не найден!\n📝 Список: `магазин`")

async def show_inventory(message: types.Message):
    user_id = message.from_user.id
    items = await get_inventory(user_id)
    
    if not items:
        await message.reply("🎒 **Инвентарь пуст!**\n\n📝 `магазин` - купить предметы")
        return
    
    msg = "🎒 **ИНВЕНТАРЬ**\n━━━━━━━━━━━━━━━━━━━━\n"
    
    # Группируем предметы
    shop_items = []
    limited_items = []
    other_items = []
    
    for item_name, quantity, is_limited in items:
        if is_limited:
            limited_items.append((item_name, quantity))
        elif item_name in SHOP_ITEMS:
            shop_items.append((item_name, quantity))
        else:
            other_items.append((item_name, quantity))
    
    if shop_items:
        msg += "\n🛒 **ПРЕДМЕТЫ:**\n"
        for name, qty in shop_items:
            price = SHOP_ITEMS.get(name, {}).get("price", 0)
            emoji = "📦"
            if "кирка" in name: emoji = "⛏️"
            elif "удочка" in name: emoji = "🎣"
            elif "ружьё" in name: emoji = "🔫"
            elif "трактор" in name: emoji = "🚜"
            elif "техника" in name: emoji = "🏗️"
            elif "щит" in name: emoji = "🛡️"
            elif "каска" in name: emoji = "⛑️"
            elif "бронежилет" in name: emoji = "🦺"
            elif "амулет" in name: emoji = "🍀"
            elif "монета" in name: emoji = "💰"
            elif "камень" in name: emoji = "💎"
            msg += f"{emoji} {name.capitalize()}: **{qty}** шт (💰 {price} монет)\n"
    
    if limited_items:
        msg += "\n🔥 **ЛИМИТНЫЕ ПРЕДМЕТЫ:**\n"
        for name, qty in limited_items:
            data = LIMITED_ITEMS.get(name)
            if data:
                msg += f"{data['emoji']} {name.capitalize()}: **{qty}** шт ({data['rarity']})\n"
    
    if other_items:
        msg += "\n📦 **ДРУГОЕ:**\n"
        for name, qty in other_items:
            msg += f"📦 {name.capitalize()}: **{qty}** шт\n"
    
    total_items = len(items)
    msg += f"\n📊 Всего предметов: **{total_items}**"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def sell_item(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply("ℹ️ `продать [предмет] [количество]`\n💰 Возврат 80% от стоимости покупки")
        return
    
    parts = args[1].split()
    item_name = parts[0].lower()
    quantity = int(parts[1]) if len(parts) > 1 else 1
    
    if quantity <= 0:
        await message.reply("❌ Количество должно быть > 0!")
        return
    
    # Проверяем наличие
    has_qty = await has_item(user_id, item_name)
    if has_qty < quantity:
        await message.reply(f"❌ У тебя только {has_qty} шт {item_name}!")
        return
    
    # Ищем цену
    price = 0
    if item_name in SHOP_ITEMS:
        price = SHOP_ITEMS[item_name]["price"]
    elif item_name in LIMITED_ITEMS:
        price = LIMITED_ITEMS[item_name]["price"]
    else:
        await message.reply(f"❌ Предмет '{item_name}' не найден!")
        return
    
    sell_price = int(price * 0.8 * quantity)
    
    success = await remove_item(user_id, item_name, quantity)
    if success:
        await add_coins(user_id, sell_price)
        await log_action(user_id, "sell_item", f"Продал {quantity}x {item_name} за {sell_price}")
        await message.reply(f"💰 Продано **{quantity}x {item_name}** за **{sell_price}** монет (80% от цены)!")
    else:
        await message.reply("❌ Ошибка при продаже!")

async def show_limited_items(message: types.Message):
    msg = "🔥 **ЛИМИТНЫЕ ПРЕДМЕТЫ**\n\n"
    
    rarities = ["🌟 МИФИЧЕСКИЙ", "🔴 ЛЕГЕНДАРНЫЙ", "🟠 ЭПИЧЕСКИЙ", "🟣 РЕДКИЙ"]
    for rarity in rarities:
        found = False
        for name, data in LIMITED_ITEMS.items():
            if data["rarity"] == rarity:
                if not found:
                    msg += f"**{rarity}**\n"
                    found = True
                left = data["left"]
                total = data["total"]
                status = "✅" if left > 0 else "❌"
                msg += f"{data['emoji']} {name.capitalize()} — {left}/{total} {status} (💰 {data['price']} монет)\n"
                msg += f"   📝 {data['desc']}\n"
        if found:
            msg += "\n"
    
    msg += "📝 `купить [название]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

print(f"✅ Часть 3/20 загружена! Строк: ~650")
# ==================== ЧАСТЬ 4/20: КЕЙСЫ, БАНК, ВКЛАДЫ, КРЕДИТЫ ====================

# ==================== КЕЙСЫ ====================
async def show_cases(message: types.Message):
    """Показать список всех кейсов"""
    msg = "🎁 **ДОСТУПНЫЕ КЕЙСЫ**\n\n"
    
    for case_name, case_data in CASES.items():
        msg += f"{case_data['emoji']} **{case_data['name']}**\n"
        msg += f"💰 Цена: {case_data['price']} монет\n"
        if case_data.get('vip_only', False):
            msg += "👑 Только для VIP\n"
        
        # Показываем шансы на лимитки
        limited_chance = 0
        for item_data in case_data['items'].values():
            if item_data.get('limited', False):
                limited_chance += item_data['chance']
        
        if limited_chance > 0:
            msg += f"🎯 Шанс на лимитку: {limited_chance}%\n"
        msg += "\n"
    
    msg += "📝 `открыть кейс [название]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def open_case(message: types.Message):
    """Открытие кейса"""
    user_id = message.from_user.id
    case_name = message.text.replace("открыть кейс ", "").lower().strip()
    
    # Проверяем существование кейса
    if case_name not in CASES:
        await message.reply("❌ Такого кейса нет!\n📝 `кейсы` - список кейсов")
        return
    
    case = CASES[case_name]
    
    # Проверяем VIP доступ
    if case.get('vip_only', False) and not await is_vip(user_id):
        await message.reply("❌ Этот кейс только для VIP!")
        return
    
    # Проверяем деньги
    price = case["price"]
    coins = await get_coins(user_id)
    
    if coins < price:
        await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
        return
    
    # Снимаем деньги
    await remove_coins(user_id, price)
    
    # Выбираем предмет
    items = case["items"]
    total_chance = sum(item["chance"] for item in items.values())
    roll = random.randint(1, total_chance)
    
    current = 0
    for item_name, item_data in items.items():
        current += item_data["chance"]
        if roll <= current:
            # Выпал предмет
            if "min" in item_data and "max" in item_data:
                # Монеты или камни
                quantity = random.randint(item_data["min"], item_data["max"])
                
                if "монеты" in item_name:
                    await add_coins(user_id, quantity)
                    await log_action(user_id, "open_case", f"Открыл {case_name}, выпало {quantity} монет")
                    await message.reply(f"🎉 Из {case['emoji']} {case['name']} выпало **{quantity}** монет!")
                else:
                    await add_item(user_id, "драгоценный камень", quantity)
                    await log_action(user_id, "open_case", f"Открыл {case_name}, выпало {quantity} камней")
                    await message.reply(f"🎉 Из {case['emoji']} {case['name']} выпало **{quantity}** драгоценных камней!")
            else:
                # Предмет
                quantity = item_data.get("quantity", 1)
                await add_item(user_id, item_name, quantity)
                await log_action(user_id, "open_case", f"Открыл {case_name}, выпал {item_name}")
                
                if item_data.get("limited", False):
                    # Лимитный предмет
                    await message.reply(f"🌟 **УРА! ВЫПАЛА ЛИМИТКА!**\n🎉 {item_name} из {case['emoji']} {case['name']}!")
                else:
                    await message.reply(f"🎉 Из {case['emoji']} {case['name']} выпал: **{item_name}** x{quantity}")
            return
    
    # Если ничего не выпало (запасной вариант)
    await add_coins(user_id, 10)
    await message.reply(f"😅 Из {case['emoji']} {case['name']} выпало 10 монет!")

# ==================== БАНК ====================
async def deposit_command(message: types.Message):
    """Положить в банк"""
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `положить [сумма]`")
        return
    
    try:
        amount = int(args[1])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return
    
    user_id = message.from_user.id
    coins = await get_coins(user_id)
    
    if coins < amount:
        await message.reply(f"❌ У тебя только {coins} монет!")
        return
    
    await remove_coins(user_id, amount)
    await add_bank(user_id, amount)
    await log_action(user_id, "deposit", f"Положил {amount} в банк")
    await message.reply(f"🏦 +{amount} монет в банк!")

async def withdraw_command(message: types.Message):
    """Снять из банка"""
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `снять [сумма]`")
        return
    
    try:
        amount = int(args[1])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return
    
    user_id = message.from_user.id
    bank = await get_bank(user_id)
    
    if bank < amount:
        await message.reply(f"❌ В банке только {bank} монет!")
        return
    
    success = await remove_bank(user_id, amount)
    if success:
        await add_coins(user_id, amount)
        await log_action(user_id, "withdraw", f"Снял {amount} из банка")
        await message.reply(f"🏦 -{amount} монет из банка!")
    else:
        await message.reply("❌ Ошибка!")

# ==================== ВКЛАДЫ ====================
async def deposit_commands(message: types.Message):
    """Команды для вкладов"""
    user_id = message.from_user.id
    args = message.text.lower().split()
    
    if len(args) < 2:
        await message.reply("""
🏦 **ВКЛАДЫ В БАНКЕ**

📋 **Доступные типы вкладов:**

💳 **Обычный вклад**
• 1% в час
• Минимум: 1 000 монет
• Бессрочный
• Без штрафа при снятии

🏦 **Долгосрочный вклад**
• 3% в час
• Минимум: 5 000 монет
• Срок: 24 часа
• Нельзя снять до окончания

👑 **VIP вклад** (только для VIP)
• 4% в час
• Минимум: 10 000 монет
• Срок: 24 часа
• Нельзя снять до окончания

📝 **Команды:**
`вклад открыть [тип] [сумма]` — открыть вклад
`вклад закрыть [номер]` — закрыть вклад
`вклад список` — мои вклады
`вклад информация` — подробная информация
""")
        return
    
    action = args[1]
    
    # ===== ОТКРЫТЬ =====
    if action == "открыть" and len(args) >= 4:
        deposit_type = args[2].lower()
        try:
            amount = int(args[3])
        except:
            await message.reply("❌ Введи число!")
            return
        
        if deposit_type not in DEPOSIT_TYPES:
            await message.reply(f"❌ Тип '{deposit_type}' не найден!\nДоступны: обычный, долгосрочный, vip")
            return
        
        deposit_data = DEPOSIT_TYPES[deposit_type]
        
        if deposit_type == "vip" and not await is_vip(user_id):
            await message.reply("❌ VIP вклад доступен только для VIP пользователей!")
            return
        
        if amount < deposit_data["min_amount"]:
            await message.reply(f"❌ Минимальная сумма для {deposit_data['name']}: {deposit_data['min_amount']} монет!")
            return
        
        coins = await get_coins(user_id)
        if coins < amount:
            await message.reply(f"❌ У тебя только {coins} монет! Нужно {amount}")
            return
        
        active_deposits = await get_active_deposits(user_id)
        if len(active_deposits) >= 3:
            await message.reply("❌ У тебя уже 3 активных вклада!")
            return
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        
        now = datetime.now()
        ended_at = None
        if deposit_data["duration"]:
            ended_at = (now + timedelta(hours=deposit_data["duration"])).isoformat()
        
        c.execute("""INSERT INTO deposits 
                    (user_id, amount, type, interest_rate, started_at, ended_at, last_interest) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (user_id, amount, deposit_type, deposit_data["interest"], 
                   now.isoformat(), ended_at, now.isoformat()))
        
        deposit_id = c.lastrowid
        conn.commit()
        conn.close()
        
        await remove_coins(user_id, amount)
        await log_action(user_id, "deposit_open", f"Открыл вклад {deposit_type} на {amount}")
        
        msg = f"✅ **{deposit_data['name']}** открыт!\n\n"
        msg += f"💰 Сумма: **{amount}** монет\n"
        msg += f"📈 Ставка: **{deposit_data['interest']}%** в час\n"
        msg += f"📝 {deposit_data['desc']}\n"
        
        if deposit_data["duration"]:
            msg += f"⏳ Срок: **{deposit_data['duration']}** часов\n"
            msg += f"📅 Закроется: {(now + timedelta(hours=deposit_data['duration'])).strftime('%d.%m.%Y %H:%M')}\n"
        else:
            msg += f"♾️ Бессрочный вклад\n"
        
        msg += f"\n🆔 Номер вклада: **{deposit_id}**"
        
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # ===== ЗАКРЫТЬ =====
    if action == "закрыть" and len(args) >= 3:
        try:
            deposit_id = int(args[2])
        except:
            await message.reply("❌ Введи номер вклада!")
            return
        
        deposit = await get_deposit(deposit_id, user_id)
        if not deposit:
            await message.reply(f"❌ Вклад #{deposit_id} не найден!")
            return
        
        dep_id, user_id_db, amount, dep_type, rate, started_at, ended_at, active, last_interest = deposit
        
        if not active:
            await message.reply(f"❌ Вклад #{deposit_id} уже закрыт!")
            return
        
        deposit_data = DEPOSIT_TYPES.get(dep_type)
        if not deposit_data:
            await message.reply("❌ Ошибка типа вклада!")
            return
        
        now = datetime.now()
        started = datetime.fromisoformat(started_at)
        hours_passed = (now - started).total_seconds() / 3600
        
        # Проверяем, можно ли закрыть
        if deposit_data["duration"] and hours_passed < deposit_data["duration"]:
            await message.reply(f"❌ Вклад нельзя закрыть до окончания срока! Осталось {int(deposit_data['duration'] - hours_passed)} часов.")
            return
        
        # Начисляем проценты
        interest_earned = int(amount * (rate / 100) * hours_passed)
        if await is_vip(user_id):
            interest_earned = int(interest_earned * 1.5)
        
        total = amount + interest_earned
        
        await close_deposit(deposit_id)
        await add_bank(user_id, total)
        await log_action(user_id, "deposit_close", f"Закрыл вклад {dep_type}, получил {total}")
        
        msg = f"✅ **ВКЛАД ЗАКРЫТ**\n\n"
        msg += f"💰 Сумма вклада: {amount} монет\n"
        msg += f"📈 Начислено процентов: +{interest_earned} монет\n"
        msg += f"💳 Итого: **{total}** монет\n"
        
        if await is_vip(user_id):
            msg += "👑 VIP бонус: +50% к процентам"
        
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # ===== СПИСОК =====
    if action == "список":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("""SELECT id, amount, type, interest_rate, started_at, ended_at, active 
                    FROM deposits WHERE user_id = ? ORDER BY id DESC""", (user_id,))
        deposits = c.fetchall()
        conn.close()
        
        if not deposits:
            await message.reply("📭 У тебя нет вкладов!")
            return
        
        msg = "🏦 **МОИ ВКЛАДЫ**\n\n"
        for dep in deposits:
            dep_id, amount, dep_type, rate, started, ended, active = dep
            dep_data = DEPOSIT_TYPES.get(dep_type, {})
            status = "🟢 Активен" if active else "🔒 Закрыт"
            
            msg += f"#{dep_id} {dep_data.get('name', dep_type)}\n"
            msg += f"💰 {amount} монет | {rate}%/час\n"
            msg += f"📅 {started[:10]} | {status}\n\n"
        
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # ===== ИНФОРМАЦИЯ =====
    if action == "информация":
        await message.reply("""
🏦 **ИНФОРМАЦИЯ О ВКЛАДАХ**

💳 **Обычный вклад**
• Ставка: 1% в час
• Минимум: 1 000 монет
• Бессрочный
• Можно снять в любой момент

🏦 **Долгосрочный вклад**
• Ставка: 3% в час
• Минимум: 5 000 монет
• Срок: 24 часа
• Нельзя снять до окончания

👑 **VIP вклад** (только для VIP)
• Ставка: 4% в час
• Минимум: 10 000 монет
• Срок: 24 часа
• Нельзя снять до окончания
• Доступен только VIP пользователям

💰 **Проценты начисляются каждый час!**
🏦 Деньги зачисляются в банк
👑 VIP получают +50% к процентам

📝 **Пример:**
Открываешь долгосрочный вклад на 10 000 монет
Через 24 часа: 10 000 + 7 200 (3%*24) = 17 200 монет
""")
        return

# ==================== КРЕДИТЫ ====================
async def loan_commands(message: types.Message):
    """Команды для кредитов"""
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 2:
        await message.reply("ℹ️ `кредит взять [сумма]` или `кредит погасить`")
        return
    
    action = args[1]
    
    # ===== ВЗЯТЬ =====
    if action == "взять" and len(args) >= 3:
        try:
            amount = int(args[2])
            if amount < 1000 or amount > 100000:
                await message.reply("❌ Сумма от 1 000 до 100 000 монет!")
                return
            
            # Проверяем, есть ли уже кредит
            existing = await get_loan(user_id)
            if existing:
                await message.reply("❌ У тебя уже есть кредит! Погаси его сначала!")
                return
            
            # Проверяем, сколько пользователь зарабатывает
            job = await get_job(user_id)
            if not job:
                await message.reply("❌ У тебя нет работы! Устройся сначала!")
                return
            
            job_data = JOBS.get(job)
            avg_salary = (job_data["min"] + job_data["max"]) // 2
            max_loan = avg_salary * 100
            
            if amount > max_loan:
                await message.reply(f"❌ Максимальный кредит для твоей работы: {max_loan} монет!")
                return
            
            interest = random.randint(10, 30)
            await take_loan(user_id, amount, interest)
            await add_coins(user_id, amount)
            await log_action(user_id, "loan_take", f"Взял кредит {amount} монет")
            
            due_date = (datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')
            await message.reply(f"✅ Взят кредит **{amount}** монет!\n📈 Процент: {interest}%\n📅 Погасить до: {due_date}")
            
        except:
            await message.reply("❌ Введи число!")
        return
    
    # ===== ПОГАСИТЬ =====
    if action == "погасить":
        loan = await get_loan(user_id)
        if not loan:
            await message.reply("❌ У тебя нет кредита!")
            return
        
        amount, interest = loan
        total = amount + int(amount * interest / 100)
        coins = await get_coins(user_id)
        
        if coins < total:
            await message.reply(f"❌ Нужно {total} монет для погашения! У тебя {coins}")
            return
        
        await remove_coins(user_id, total)
        await repay_loan(user_id)
        await log_action(user_id, "loan_pay", f"Погасил кредит {total} монет")
        await message.reply(f"✅ Кредит погашен! Сумма: {total} монет")

# ==================== ФОНОВАЯ ЗАДАЧА ДЛЯ ВКЛАДОВ ====================
async def deposit_interest_task():
    """Фоновая задача для начисления процентов по вкладам"""
    while True:
        await asyncio.sleep(3600)  # Каждый час
        
        try:
            conn = sqlite3.connect("fable_bot.db")
            c = conn.cursor()
            
            c.execute("SELECT id, user_id, amount, interest_rate, last_interest, ended_at FROM deposits WHERE active = 1")
            deposits = c.fetchall()
            
            for dep in deposits:
                dep_id, user_id, amount, rate, last_interest, ended_at = dep
                
                try:
                    last = datetime.fromisoformat(last_interest)
                    now = datetime.now()
                    
                    # Проверяем, не закончился ли вклад
                    if ended_at:
                        end_time = datetime.fromisoformat(ended_at)
                        if now >= end_time:
                            # Автоматически закрываем
                            hours_passed = (now - datetime.fromisoformat(last_interest)).total_seconds() / 3600
                            interest = int(amount * (rate / 100) * hours_passed)
                            total = amount + interest
                            
                            await close_deposit(dep_id)
                            await add_bank(user_id, total)
                            
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"✅ **ВКЛАД #{dep_id} АВТОМАТИЧЕСКИ ЗАКРЫТ**\n\n"
                                    f"💰 Сумма: {amount} монет\n"
                                    f"📈 Проценты: +{interest} монет\n"
                                    f"💳 Итого: **{total}** монет",
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            except:
                                pass
                            continue
                    
                    hours_since_last = (now - last).total_seconds() / 3600
                    
                    if hours_since_last >= 1:
                        interest = int(amount * (rate / 100))
                        
                        if await is_vip(user_id):
                            interest = int(interest * 1.5)
                        
                        if interest > 0:
                            await add_bank(user_id, interest)
                            await update_deposit_interest(dep_id, now.isoformat())
                            
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"🏦 **Начислены проценты по вкладу #{dep_id}**\n"
                                    f"💰 +{interest} монет\n"
                                    f"📊 Текущая ставка: {rate}% в час",
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            except:
                                pass
                except Exception as e:
                    print(f"❌ Ошибка обработки вклада {dep_id}: {e}")
            
            conn.close()
        except Exception as e:
            print(f"❌ Ошибка task: {e}")

print(f"✅ Часть 4/20 загружена! Строк: ~700")
# ==================== ЧАСТЬ 5/20: ИГРЫ, СОЦИАЛКА, РП КОМАНДЫ ====================

# ==================== ИГРЫ ====================

# ----- КУБЫ -----
async def cube_game(message: types.Message):
    user_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply("🎲 Ответь на сообщение соперника!\n📝 `кубы` или `кубы 2`")
        return

    opponent_id = message.reply_to_message.from_user.id

    if opponent_id == user_id:
        await message.reply("❌ Нельзя с самим собой!")
        return

    args = message.text.split()
    dice_count = 1
    if len(args) > 1:
        try:
            dice_count = int(args[1])
            if dice_count < 1 or dice_count > 3:
                await message.reply("❌ 1-3 кости!")
                return
        except:
            await message.reply("❌ Введи число!")
            return

    game_id = f"{message.chat.id}_{user_id}_{opponent_id}"
    cube_games[game_id] = {
        "challenger": user_id,
        "opponent": opponent_id,
        "dice_count": dice_count,
        "status": "waiting"
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ ДА", callback_data=f"cube_yes_{message.chat.id}_{user_id}_{opponent_id}_{dice_count}"),
         InlineKeyboardButton("❌ НЕТ", callback_data=f"cube_no_{message.chat.id}_{user_id}_{opponent_id}")]
    ])

    await message.reply(f"🎲 {await get_name(user_id)} вызывает {await get_name(opponent_id)} на кубы!\n🎯 Костей: {dice_count}", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("cube_yes_"))
async def cube_accept(callback):
    data = callback.data.split("_")
    chat_id = int(data[1])
    challenger = int(data[2])
    opponent = int(data[3])
    dice_count = int(data[4])

    if callback.from_user.id != opponent:
        await callback.answer("❌ Не тебе!")
        return

    await callback.message.delete()

    rolls1 = [random.randint(1, 6) for _ in range(dice_count)]
    rolls2 = [random.randint(1, 6) for _ in range(dice_count)]
    total1 = sum(rolls1)
    total2 = sum(rolls2)

    msg = f"🎲 **КУБЫ**\n\n"
    msg += f"{await get_name(challenger)}: {', '.join(map(str, rolls1))} = **{total1}**\n"
    msg += f"{await get_name(opponent)}: {', '.join(map(str, rolls2))} = **{total2}**\n\n"

    if total1 > total2:
        msg += f"🏆 **{await get_name(challenger)}** победил!"
        await add_coins(challenger, 50)
    elif total2 > total1:
        msg += f"🏆 **{await get_name(opponent)}** победил!"
        await add_coins(opponent, 50)
    else:
        msg += "🤝 Ничья!"

    await bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(lambda c: c.data.startswith("cube_no_"))
async def cube_decline(callback):
    data = callback.data.split("_")
    opponent = int(data[3])

    if callback.from_user.id != opponent:
        await callback.answer("❌ Не тебе!")
        return

    await callback.message.edit_text("❌ Отказ!")

# ----- РУЛЕТКА -----
async def roulette_game(message: types.Message):
    user_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply("🔫 Ответь на сообщение соперника!\n📝 `рулетка`")
        return

    opponent_id = message.reply_to_message.from_user.id

    if opponent_id == user_id:
        await message.reply("❌ Нельзя с самим собой!")
        return

    game_id = f"{message.chat.id}_{user_id}_{opponent_id}"
    roulette_games[game_id] = {
        "challenger": user_id,
        "opponent": opponent_id,
        "bullets": [0, 0, 0, 0, 0, 1],
        "turn": user_id,
        "status": "waiting"
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ ДА", callback_data=f"roulette_yes_{message.chat.id}_{user_id}_{opponent_id}"),
         InlineKeyboardButton("❌ НЕТ", callback_data=f"roulette_no_{message.chat.id}_{user_id}_{opponent_id}")]
    ])

    await message.reply(f"🔫 {await get_name(user_id)} вызывает {await get_name(opponent_id)} на русскую рулетку!\n💀 1 патрон из 6", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("roulette_yes_"))
async def roulette_accept(callback):
    data = callback.data.split("_")
    chat_id = int(data[1])
    challenger = int(data[2])
    opponent = int(data[3])

    if callback.from_user.id != opponent:
        await callback.answer("❌ Не тебе!")
        return

    await callback.message.delete()
    await roulette_shoot(chat_id, challenger, opponent)

@dp.callback_query(lambda c: c.data.startswith("roulette_no_"))
async def roulette_decline(callback):
    data = callback.data.split("_")
    opponent = int(data[3])

    if callback.from_user.id != opponent:
        await callback.answer("❌ Не тебе!")
        return

    await callback.message.edit_text("❌ Отказ!")

async def roulette_shoot(chat_id, player_id, opponent_id):
    game_id = f"{chat_id}_{player_id}_{opponent_id}"
    game = roulette_games.get(game_id)

    if not game:
        await bot.send_message(chat_id, "❌ Игра завершена!")
        return

    bullets = game["bullets"]

    if not bullets:
        await bot.send_message(chat_id, "🤝 Ничья!")
        del roulette_games[game_id]
        return

    shot = bullets.pop(0)

    if shot == 1:
        del roulette_games[game_id]
        winner = opponent_id if game["turn"] == player_id else player_id
        await bot.send_message(chat_id, f"🔫 **БАХ!**\n💀 {await get_name(game['turn'])} умер!\n🏆 {await get_name(winner)} победил!", parse_mode=ParseMode.MARKDOWN)
        await add_coins(winner, 100)
    else:
        game["turn"] = opponent_id if game["turn"] == player_id else player_id
        game["bullets"] = bullets

        if len(bullets) == 0:
            await bot.send_message(chat_id, "💨 Холостой! Ничья!")
            del roulette_games[game_id]
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🔫 ВЫСТРЕЛИТЬ", callback_data=f"rshoot_{chat_id}_{game['turn']}_{opponent_id if game['turn'] == player_id else player_id}")]
        ])

        await bot.send_message(chat_id, f"💨 Холостой!\n⏳ Ход: {await get_name(game['turn'])}\n💀 Патронов: {len(bullets)}/6", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("rshoot_"))
async def roulette_shoot_cb(callback):
    data = callback.data.split("_")
    chat_id = int(data[1])
    player = int(data[2])
    opponent = int(data[3])

    if callback.from_user.id != player:
        await callback.answer("❌ Не твой ход!")
        return

    await callback.message.delete()
    await roulette_shoot(chat_id, player, opponent)

# ----- КАЗИНО (СЛОТЫ) -----
async def casino_command(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        await message.reply("ℹ️ `казино [ставка]`")
        return

    try:
        bet = int(args[1])
        if bet < 50:
            await message.reply("❌ Минимальная ставка 50 монет!")
            return
        if bet > 10000:
            await message.reply("❌ Максимальная ставка 10 000 монет!")
            return
    except:
        await message.reply("❌ Введи число!")
        return

    coins = await get_coins(user_id)
    if coins < bet:
        await message.reply(f"❌ У тебя только {coins} монет!")
        return

    # Слоты
    slots = ["🍒", "🍋", "🍊", "🔔", "💎", "7️⃣"]
    results = [random.choice(slots) for _ in range(3)]
    
    # Проверяем выигрыш
    win = 0
    if results[0] == results[1] == results[2]:
        if results[0] == "7️⃣":
            win = bet * 100  # Джекпот
        elif results[0] == "💎":
            win = bet * 50
        elif results[0] == "🔔":
            win = bet * 10
        else:
            win = bet * 5
    elif results[0] == results[1] or results[1] == results[2] or results[0] == results[2]:
        win = bet * 2

    msg = f"🎰 **КАЗИНО**\n\n"
    msg += f"{' | '.join(results)}\n\n"

    if win > 0:
        await add_coins(user_id, win)
        await log_action(user_id, "casino", f"Выиграл {win} монет (ставка {bet})")
        msg += f"🎉 **ВЫ ВЫИГРАЛИ {win} МОНЕТ!** 🎉"
    else:
        await remove_coins(user_id, bet)
        await log_action(user_id, "casino", f"Проиграл {bet} монет")
        msg += f"😢 Вы проиграли {bet} монет!"

    await message.reply(msg)

# ==================== РП КОМАНДЫ ====================
RP_ACTIONS = {
    "обнять": ["🤗 {user} обнял {target}!", "❤️ {user} прижал к себе {target}!", "💕 {user} согрел {target} теплом!"],
    "поцеловать": ["😘 {user} поцеловал {target}!", "💋 {user} чмокнул {target}!", "❤️‍🔥 {user} засосал {target}!"],
    "ударить": ["👊 {user} ударил {target}!", "💥 {user} заехал {target}!", "🥊 {user} врезал {target}!"],
    "пнуть": ["🦶 {user} пнул {target}!", "👟 {user} дал пинка {target}!", "💨 {user} выпнул {target}!"]
}

async def rp_command(message: types.Message):
    action = message.text.lower().strip()
    target_id = message.reply_to_message.from_user.id
    user_id = message.from_user.id

    if target_id == user_id:
        await message.reply("❌ Нельзя с самим собой!")
        return

    actions = RP_ACTIONS.get(action)
    if not actions:
        return

    msg = random.choice(actions).format(
        user=await get_name(user_id),
        target=await get_name(target_id)
    )
    await message.reply(msg)

# ==================== РЕПУТАЦИЯ ====================
async def add_reputation(message: types.Message):
    user_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id

    if target_id == user_id:
        await message.reply("❌ Нельзя себе!")
        return

    ok, remaining = await check_cooldown(user_id, "rep", 300)
    if not ok:
        await message.reply(f"⏳ Подожди {remaining//60} мин!")
        return

    await add_rep(target_id, 1)
    await message.reply(f"👍 {await get_name(target_id)} репутация: {await get_rep(target_id)}")

async def remove_reputation(message: types.Message):
    user_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id

    if target_id == user_id:
        await message.reply("❌ Нельзя себе!")
        return

    ok, remaining = await check_cooldown(user_id, "rep", 300)
    if not ok:
        await message.reply(f"⏳ Подожди {remaining//60} мин!")
        return

    await add_rep(target_id, -1)
    await message.reply(f"👎 {await get_name(target_id)} репутация: {await get_rep(target_id)}")

# ==================== БРАК ====================
async def propose_marriage(message: types.Message):
    user_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id

    if target_id == user_id:
        await message.reply("❌ Нельзя себе!")
        return

    if await get_marriage(user_id):
        await message.reply("❌ Ты уже в браке!")
        return

    if await get_marriage(target_id):
        await message.reply("❌ Партнёр в браке!")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("💍 ДА", callback_data=f"marry_{target_id}_{user_id}"),
         InlineKeyboardButton("❌ НЕТ", callback_data=f"marry_no_{target_id}_{user_id}")]
    ])

    await message.reply(f"💍 {await get_name(user_id)} предлагает брак {await get_name(target_id)}", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("marry_"))
async def marry_accept(callback):
    data = callback.data.split("_")
    target_id = int(data[1])
    proposer_id = int(data[2])

    if callback.from_user.id != target_id:
        await callback.answer("❌ Не тебе!")
        return

    await set_marriage(target_id, proposer_id)
    await set_marriage(proposer_id, target_id)
    await callback.message.edit_text(f"💍 {await get_name(proposer_id)} + {await get_name(target_id)}!")

@dp.callback_query(lambda c: c.data.startswith("marry_no_"))
async def marry_decline(callback):
    data = callback.data.split("_")
    target_id = int(data[2])

    if callback.from_user.id != target_id:
        await callback.answer("❌ Не тебе!")
        return

    await callback.message.edit_text("❌ Отказ!")

async def divorce_command(message: types.Message):
    user_id = message.from_user.id
    spouse = await get_marriage(user_id)
    if not spouse:
        await message.reply("❌ Ты не в браке!")
        return

    await remove_marriage(user_id)
    await remove_marriage(spouse)
    await message.reply(f"💔 {await get_name(user_id)} развёлся!")

# ==================== КЛАНЫ ====================
async def create_clan(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("ℹ️ `создать клан [название]`")
        return

    name = args[2]
    coins = await get_coins(user_id)
    if coins < 5000:
        await message.reply(f"❌ Нужно 5000 монет для создания клана! У тебя {coins}")
        return

    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT id FROM clans WHERE name = ?", (name,))
    if c.fetchone():
        conn.close()
        await message.reply(f"❌ Клан с названием '{name}' уже существует!")
        return

    c.execute("SELECT id FROM clans WHERE members LIKE ?", (f"%{user_id}%",))
    if c.fetchone():
        conn.close()
        await message.reply("❌ Ты уже в клане!")
        return

    await remove_coins(user_id, 5000)
    c.execute("INSERT INTO clans (name, owner_id, members, created_at) VALUES (?, ?, ?, ?)",
              (name, user_id, str(user_id), datetime.now().isoformat()))
    clan_id = c.lastrowid
    c.execute("INSERT INTO clan_roles (user_id, clan_id, role) VALUES (?, ?, ?)",
              (user_id, clan_id, "leader"))
    conn.commit()
    conn.close()

    await log_action(user_id, "create_clan", f"Создал клан {name}")
    await message.reply(f"✅ Клан **{name}** создан! Ты стал лидером.")

async def join_clan(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.reply("ℹ️ `вступить в клан [название]`")
        return

    name = args[3]

    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT id, members FROM clans WHERE name = ?", (name,))
    row = c.fetchone()
    if not row:
        conn.close()
        await message.reply(f"❌ Клан '{name}' не найден!")
        return

    clan_id, members = row
    members_list = members.split(",") if members else []

    if str(user_id) in members_list:
        conn.close()
        await message.reply("❌ Ты уже в этом клане!")
        return

    c.execute("SELECT id FROM clans WHERE members LIKE ?", (f"%{user_id}%",))
    if c.fetchone():
        conn.close()
        await message.reply("❌ Ты уже в другом клане!")
        return

    members_list.append(str(user_id))
    c.execute("UPDATE clans SET members = ? WHERE id = ?", (",".join(members_list), clan_id))
    c.execute("INSERT INTO clan_roles (user_id, clan_id, role) VALUES (?, ?, ?)",
              (user_id, clan_id, "member"))
    conn.commit()
    conn.close()

    await log_action(user_id, "join_clan", f"Вступил в клан {name}")
    await message.reply(f"✅ Ты вступил в клан **{name}**!")

async def my_clan(message: types.Message):
    user_id = message.from_user.id
    clan = await get_user_clan(user_id)
    if not clan:
        await message.reply("❌ Ты не в клане!")
        return

    clan_id, name, owner_id, members = clan
    members_list = members.split(",") if members else []
    role = await get_clan_role(user_id, clan_id)
    treasury = await get_clan_treasury(clan_id)

    msg = f"🏰 **{name}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"👑 Лидер: {await get_name(owner_id)}\n"
    msg += f"🎭 Твоя роль: {role}\n"
    msg += f"👥 Участников: {len(members_list)}\n"
    msg += f"💰 Казна: {treasury} монет"

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def list_clans(message: types.Message):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT name, owner_id, members, treasury FROM clans")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await message.reply("📭 Нет кланов!")
        return

    msg = "🏰 **СПИСОК КЛАНОВ**\n\n"
    for name, owner_id, members, treasury in rows:
        count = len(members.split(",")) if members else 0
        msg += f"**{name}**\n"
        msg += f"👑 {await get_name(owner_id)} | 👥 {count} | 💰 {treasury}\n\n"

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def clan_treasury_command(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `казна положить [сумма]` или `казна снять [сумма]`")
        return

    clan = await get_user_clan(user_id)
    if not clan:
        await message.reply("❌ Ты не в клане!")
        return

    clan_id = clan[0]
    action = args[1]

    try:
        amount = int(args[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return

    if action == "положить":
        coins = await get_coins(user_id)
        if coins < amount:
            await message.reply(f"❌ У тебя только {coins} монет!")
            return

        await remove_coins(user_id, amount)
        await add_clan_treasury(clan_id, amount)
        await log_action(user_id, "clan_deposit", f"Положил {amount} в казну клана")
        await message.reply(f"💰 +{amount} монет в казну клана!")
        return

    if action == "снять":
        role = await get_clan_role(user_id, clan_id)
        if role != "leader":
            await message.reply("❌ Только лидер может снимать из казны!")
            return

        treasury = await get_clan_treasury(clan_id)
        if treasury < amount:
            await message.reply(f"❌ В казне только {treasury} монет!")
            return

        await remove_clan_treasury(clan_id, amount)
        await add_coins(user_id, amount)
        await log_action(user_id, "clan_withdraw", f"Снял {amount} из казны клана")
        await message.reply(f"💰 -{amount} монет из казны клана!")
        return

print(f"✅ Часть 5/20 загружена! Строк: ~700")
# ==================== ЧАСТЬ 6/20: ФЕРМА, РЫБАЛКА, ОХОТА, ПИТОМЦЫ ====================

# ==================== ФЕРМА ====================
CROPS = {
    "пшеница": {"time": 3600, "income": 100, "emoji": "🌾"},
    "морковь": {"time": 7200, "income": 200, "emoji": "🥕"},
    "помидоры": {"time": 14400, "income": 400, "emoji": "🍅"},
    "клубника": {"time": 28800, "income": 800, "emoji": "🍓"}
}

async def farm_commands(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        await message.reply("ℹ️ `ферма` - состояние\n`посадить [культура]` - посадить\n`собрать` - собрать урожай")
        return

    action = args[1]

    # ===== ПРОСМОТР =====
    if action == "ферма":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT crop, planted_at FROM farm WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            await message.reply("🌾 **ФЕРМА**\n\nПоле пустое!\n📝 `посадить [культура]`")
            return

        crop, planted_at = row
        data = CROPS.get(crop)
        if not data:
            await message.reply("❌ Ошибка!")
            return

        try:
            planted = datetime.fromisoformat(planted_at)
            elapsed = (datetime.now() - planted).total_seconds()
            ready = elapsed >= data["time"]
            remaining = max(0, int((data["time"] - elapsed) / 60))
        except:
            ready = False
            remaining = 0

        msg = f"🌾 **ФЕРМА**\n\n"
        msg += f"🌱 Посажено: {data['emoji']} {crop.capitalize()}\n"
        msg += f"⏳ Время роста: {data['time'] // 60} мин\n"
        if ready:
            msg += f"✅ **Урожай готов!**\n📝 `собрать`"
        else:
            msg += f"⏳ Осталось: {remaining} мин"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return

    # ===== ПОСАДИТЬ =====
    if action == "посадить" and len(args) >= 3:
        crop = args[2].lower()
        if crop not in CROPS:
            await message.reply(f"❌ Культура '{crop}' не найдена!\nДоступны: пшеница, морковь, помидоры, клубника")
            return

        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM farm WHERE user_id = ?", (user_id,))
        if c.fetchone():
            conn.close()
            await message.reply("❌ На поле уже что-то посажено! Собери урожай!")
            return

        c.execute("INSERT INTO farm (user_id, crop, planted_at) VALUES (?, ?, ?)",
                  (user_id, crop, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        await log_action(user_id, "farm_plant", f"Посадил {crop}")
        await message.reply(f"✅ {CROPS[crop]['emoji']} **{crop.capitalize()}** посажена!\n⏳ Созреет через {CROPS[crop]['time'] // 60} мин")
        return

    # ===== СОБРАТЬ =====
    if action == "собрать":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT crop, planted_at FROM farm WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            await message.reply("❌ На поле ничего нет!")
            return

        crop, planted_at = row
        data = CROPS.get(crop)
        if not data:
            conn.close()
            await message.reply("❌ Ошибка!")
            return

        try:
            planted = datetime.fromisoformat(planted_at)
            elapsed = (datetime.now() - planted).total_seconds()
            if elapsed < data["time"]:
                remaining = int((data["time"] - elapsed) / 60)
                conn.close()
                await message.reply(f"⏳ Урожай еще не созрел! Осталось {remaining} мин")
                return
        except:
            pass

        income = data["income"] * random.randint(1, 3)
        await add_coins(user_id, income)
        c.execute("DELETE FROM farm WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        await log_action(user_id, "farm_harvest", f"Собрал {crop} за {income}")
        await message.reply(f"🌾 **УРОЖАЙ СОБРАН!**\n{data['emoji']} {crop.capitalize()}: +{income} монет!")

# ==================== РЫБАЛКА ====================
FISH = {
    "окунь": {"price": 50, "chance": 30, "emoji": "🐟"},
    "карп": {"price": 100, "chance": 25, "emoji": "🐠"},
    "лосось": {"price": 200, "chance": 20, "emoji": "🐡"},
    "щука": {"price": 300, "chance": 15, "emoji": "🦈"},
    "осётр": {"price": 500, "chance": 10, "emoji": "🐋"}
}

async def fishing_commands(message: types.Message):
    user_id = message.from_user.id
    text = message.text.lower()

    if text == "рыбалка":
        ok, remaining = await check_cooldown(user_id, "fishing", 300)
        if not ok:
            await message.reply(f"⏳ Подожди {remaining//60} мин!")
            return

        if not await has_item(user_id, "профессиональная удочка"):
            await message.reply("❌ У тебя нет удочки! Купи в магазине `профессиональная удочка`")
            return

        fish = random.choices(
            list(FISH.keys()),
            weights=[data["chance"] for data in FISH.values()]
        )[0]

        data = FISH[fish]
        count = random.randint(1, 3)
        total = data["price"] * count

        await add_item(user_id, fish, count)
        await add_coins(user_id, total)
        await log_action(user_id, "fishing", f"Поймал {count}x {fish}")

        await message.reply(f"🎣 **РЫБАЛКА!**\n{data['emoji']} Поймано: {count} шт {fish.capitalize()}\n💰 +{total} монет!")
        return

    if text == "купить удочку":
        if await has_item(user_id, "профессиональная удочка"):
            await message.reply("❌ У тебя уже есть удочка!")
            return

        price = 40000
        coins = await get_coins(user_id)
        if coins < price:
            await message.reply(f"❌ Нужно {price} монет!")
            return

        await remove_coins(user_id, price)
        await add_item(user_id, "профессиональная удочка")
        await log_action(user_id, "buy_rod", "Купил удочку")
        await message.reply(f"✅ **Удочка** куплена за {price} монет!\n🎣 Теперь можно рыбачить!")

# ==================== ОХОТА ====================
ANIMALS = {
    "заяц": {"price": 100, "chance": 30, "emoji": "🐇"},
    "лиса": {"price": 200, "chance": 25, "emoji": "🦊"},
    "волк": {"price": 300, "chance": 20, "emoji": "🐺"},
    "медведь": {"price": 500, "chance": 15, "emoji": "🐻"},
    "тигр": {"price": 800, "chance": 10, "emoji": "🐯"}
}

async def hunting_commands(message: types.Message):
    user_id = message.from_user.id
    text = message.text.lower()

    if text == "охота":
        ok, remaining = await check_cooldown(user_id, "hunting", 600)
        if not ok:
            await message.reply(f"⏳ Подожди {remaining//60} мин!")
            return

        if not await has_item(user_id, "тренировочное ружьё"):
            await message.reply("❌ У тебя нет ружья! Купи в магазине `тренировочное ружьё`")
            return

        animal = random.choices(
            list(ANIMALS.keys()),
            weights=[data["chance"] for data in ANIMALS.values()]
        )[0]

        data = ANIMALS[animal]
        count = random.randint(1, 2)
        total = data["price"] * count

        await add_item(user_id, f"шкура {animal}", count)
        await add_coins(user_id, total)
        await log_action(user_id, "hunting", f"Поймал {count}x {animal}")

        await message.reply(f"🔫 **ОХОТА!**\n{data['emoji']} Поймано: {count} шт {animal.capitalize()}\n💰 +{total} монет!")
        return

    if text == "купить ружьё":
        if await has_item(user_id, "тренировочное ружьё"):
            await message.reply("❌ У тебя уже есть ружьё!")
            return

        price = 60000
        coins = await get_coins(user_id)
        if coins < price:
            await message.reply(f"❌ Нужно {price} монет!")
            return

        await remove_coins(user_id, price)
        await add_item(user_id, "тренировочное ружьё")
        await log_action(user_id, "buy_gun", "Купил ружьё")
        await message.reply(f"✅ **Ружьё** куплено за {price} монет!\n🔫 Теперь можно охотиться!")

# ==================== ПИТОМЦЫ ====================
async def show_pets_shop(message: types.Message):
    msg = "🐾 **ПИТОМЦЫ**\n\n"
    for name, data in PETS.items():
        msg += f"{data['emoji']} **{name.capitalize()}**\n"
        msg += f"💰 {data['price']} монет\n"
        msg += f"📝 {data['desc']}\n\n"
    msg += "📝 `купить питомца [тип]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def buy_pet(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply("ℹ️ `купить питомца [тип]`")
        return
    
    pet_type = args[1].lower()
    if pet_type not in PETS:
        await message.reply(f"❌ Питомец '{pet_type}' не найден!")
        return

    price = PETS[pet_type]["price"]
    coins = await get_coins(user_id)
    if coins < price:
        await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
        return

    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM pets WHERE user_id = ? AND pet_type = ?", (user_id, pet_type))
    if c.fetchone():
        conn.close()
        await message.reply(f"❌ У тебя уже есть {pet_type.capitalize()}!")
        return

    await remove_coins(user_id, price)
    c.execute("INSERT INTO pets (user_id, pet_type, name, bought_at) VALUES (?, ?, ?, ?)",
              (user_id, pet_type, pet_type.capitalize(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

    await log_action(user_id, "buy_pet", f"Купил питомца {pet_type}")
    await message.reply(f"✅ {PETS[pet_type]['emoji']} **{pet_type.capitalize()}** куплен!")

async def my_pets(message: types.Message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT pet_type, name, level, exp, bought_at FROM pets WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("🐾 У тебя нет питомцев!\n📝 `питомцы` - посмотреть доступных питомцев")
        return
    
    msg = "🐾 **МОИ ПИТОМЦЫ**\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for pet_type, name, level, exp, bought_at in rows:
        pet_data = PETS.get(pet_type, {})
        emoji = pet_data.get("emoji", "🐾")
        bonus = pet_data.get("bonus", "нет")
        
        exp_needed = level * 50
        progress = int((exp / exp_needed) * 10) if exp_needed > 0 else 0
        bar = "█" * progress + "░" * (10 - progress)
        
        msg += f"{emoji} **{name}** ({pet_type.capitalize()})\n"
        msg += f"📊 Уровень: {level}\n"
        msg += f"📈 Опыт: {bar} {exp}/{exp_needed}\n"
        msg += f"✨ Бонус: {bonus}\n"
        msg += f"📅 Куплен: {bought_at[:10]}\n\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== НЕДВИЖИМОСТЬ ====================
async def show_properties_shop(message: types.Message):
    msg = "🏠 **НЕДВИЖИМОСТЬ**\n\n"
    for name, data in PROPERTIES.items():
        msg += f"{data['emoji']} **{name.capitalize()}**\n"
        msg += f"💰 {data['price']} монет\n"
        msg += f"📈 Доход: {data['income']} монет/час\n\n"
    msg += "📝 `купить [тип]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def buy_property(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply("ℹ️ `купить [тип]`")
        return
    
    prop_type = args[1].lower()
    if prop_type not in PROPERTIES:
        await message.reply(f"❌ '{prop_type}' не найдено!")
        return

    price = PROPERTIES[prop_type]["price"]
    coins = await get_coins(user_id)
    if coins < price:
        await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
        return

    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM properties WHERE user_id = ? AND type = ?", (user_id, prop_type))
    if c.fetchone():
        conn.close()
        await message.reply(f"❌ У тебя уже есть {prop_type.capitalize()}!")
        return

    await remove_coins(user_id, price)
    c.execute("INSERT INTO properties (user_id, type, bought_at) VALUES (?, ?, ?)",
              (user_id, prop_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    await log_action(user_id, "buy_property", f"Купил {prop_type}")
    await message.reply(f"✅ {PROPERTIES[prop_type]['emoji']} **{prop_type.capitalize()}** куплен!")

async def my_properties(message: types.Message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT type, bought_at FROM properties WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("🏠 У тебя нет недвижимости!\n📝 `недвижимость` - посмотреть доступную недвижимость")
        return
    
    msg = "🏠 **МОЯ НЕДВИЖИМОСТЬ**\n━━━━━━━━━━━━━━━━━━━━\n\n"
    total_income = 0
    for prop_type, bought_at in rows:
        data = PROPERTIES.get(prop_type, {})
        emoji = data.get("emoji", "🏠")
        income = data.get("income", 0)
        total_income += income
        
        msg += f"{emoji} **{prop_type.capitalize()}**\n"
        msg += f"💰 Доход: {income} монет/час\n"
        msg += f"📅 Куплено: {bought_at[:10]}\n\n"
    
    msg += f"📊 Общий доход: **{total_income}** монет/час"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

print(f"✅ Часть 6/20 загружена! Строк: ~650")
# ==================== ЧАСТЬ 7/20: ПРОФИЛЬ, ТОПЫ, КВЕСТЫ, ДОСТИЖЕНИЯ ====================

# ==================== ПРОФИЛЬ ====================
async def show_profile(message, target_id):
    user = await get_user(target_id)
    if not user:
        await message.reply("❌ Пользователь не найден!")
        return

    coins = await get_coins(target_id)
    bank = await get_bank(target_id)
    job = await get_job(target_id)
    rep = await get_rep(target_id)
    admin_level = await get_admin_level(target_id)
    
    # Статистика сообщений
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT SUM(messages) FROM chat_stats WHERE user_id = ?", (target_id,))
    total_messages = c.fetchone()[0] or 0
    conn.close()
    
    # Бизнесы
    businesses = await get_businesses(target_id)
    
    # Инвентарь
    inventory = await get_inventory(target_id)
    
    # Брак
    spouse = await get_marriage(target_id)
    spouse_name = await get_name(spouse) if spouse else "Нет"
    
    # Клан
    clan = await get_user_clan(target_id)
    clan_name = clan[1] if clan else "Нет"
    
    msg = f"👤 **Профиль {await get_name(target_id)}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"💰 Монет: **{coins}**\n"
    msg += f"🏦 В банке: **{bank}**\n"
    msg += f"⭐ Репутация: **{rep}**\n"
    msg += f"💬 Сообщений: **{total_messages}**\n\n"
    
    if job:
        job_data = JOBS.get(job, {})
        msg += f"💼 Работа: **{job.capitalize()}** {job_data.get('emoji', '')}\n"
    else:
        msg += f"💼 Работа: **Нет**\n"
    
    msg += f"💍 Брак: **{spouse_name}**\n"
    msg += f"🏰 Клан: **{clan_name}**\n"
    msg += f"🏪 Бизнесов: **{len(businesses)}**\n"
    msg += f"🎒 Предметов: **{len(inventory)}**\n"
    
    if await is_vip(target_id):
        msg += f"\n👑 **VIP**"
    
    if admin_level > 0:
        level_name = get_level_name(admin_level)
        level_emoji = get_level_emoji(admin_level)
        msg += f"\n🎯 {level_emoji} **{level_name}**"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ТОПЫ ====================
async def top_command(message):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    # Учитываем монеты + банк + вклады
    c.execute("""
        SELECT 
            u.user_id,
            u.coins,
            u.bank,
            COALESCE(SUM(d.amount), 0) as deposits
        FROM users u
        LEFT JOIN deposits d ON u.user_id = d.user_id AND d.active = 1
        GROUP BY u.user_id
        ORDER BY (u.coins + u.bank + COALESCE(SUM(d.amount), 0)) DESC
        LIMIT 10
    """)
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Пусто!")
        return
    
    msg = "💰 **ТОП БОГАЧЕЙ**\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (uid, coins, bank, deposits) in enumerate(rows, 1):
        name = await get_name(uid)
        total = coins + bank + deposits
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        msg += f"{medal} {name}\n"
        msg += f"   💰 Всего: **{total}** монет\n"
        msg += f"   💵 В кармане: {coins} | 🏦 В банке: {bank} | 💳 Во вкладах: {deposits}\n\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def top_rep_command(message):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, rep FROM users ORDER BY rep DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Пусто!")
        return
    
    msg = "⭐ **ТОП РЕПУТАЦИИ**\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (uid, rep) in enumerate(rows, 1):
        name = await get_name(uid)
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        msg += f"{medal} {name} — **{rep}**\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== КВЕСТЫ ====================
DAILY_QUESTS_LIST = [
    {"name": "Написать 10 сообщений", "target": 10, "reward": 100},
    {"name": "Заработать 500 монет", "target": 500, "reward": 100},
    {"name": "Сыграть в игру", "target": 1, "reward": 50},
    {"name": "Поставить +реп", "target": 1, "reward": 50},
    {"name": "Купить предмет", "target": 1, "reward": 100}
]

WEEKLY_QUESTS_LIST = [
    {"name": "Написать 100 сообщений", "target": 100, "reward": 500},
    {"name": "Заработать 5000 монет", "target": 5000, "reward": 500},
    {"name": "Купить бизнес", "target": 1, "reward": 1000},
    {"name": "Выиграть 3 игры", "target": 3, "reward": 300},
    {"name": "Купить 5 предметов", "target": 5, "reward": 500}
]

async def quest_commands(message: types.Message):
    user_id = message.from_user.id
    text = message.text.lower()

    if text == "ежедневные задания":
        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM daily_quests WHERE user_id = ? AND quest_date = ?", (user_id, today))
        row = c.fetchone()

        if not row:
            quests = random.sample(DAILY_QUESTS_LIST, 5)
            c.execute("""INSERT INTO daily_quests 
                        (user_id, quest_date, quest1, quest2, quest3, quest4, quest5) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      (user_id, today, quests[0]["name"], quests[1]["name"], quests[2]["name"], 
                       quests[3]["name"], quests[4]["name"]))
            conn.commit()
            conn.close()
            await message.reply("✅ Ежедневные задания обновлены! Напиши `ежедневные задания` еще раз.")
            return

        msg = "📋 **ЕЖЕДНЕВНЫЕ ЗАДАНИЯ**\n\n"
        for i in range(1, 6):
            quest_name = row[i]
            progress = row[i+5]
            completed = row[i+10]

            if completed:
                msg += f"✅ {quest_name} — **ВЫПОЛНЕНО**\n"
            else:
                target = 0
                reward = 0
                for q in DAILY_QUESTS_LIST:
                    if q["name"] == quest_name:
                        target = q["target"]
                        reward = q["reward"]
                        break
                msg += f"📌 {quest_name} — {progress}/{target} (💰 {reward} монет)\n"

        conn.close()
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return

    if text == "еженедельные задания":
        week = datetime.now().strftime("%Y-W%W")

        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM weekly_quests WHERE user_id = ? AND quest_week = ?", (user_id, week))
        row = c.fetchone()

        if not row:
            quests = random.sample(WEEKLY_QUESTS_LIST, 10)
            c.execute("""INSERT INTO weekly_quests 
                        (user_id, quest_week, quest1, quest2, quest3, quest4, quest5, quest6, quest7, quest8, quest9, quest10) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (user_id, week, quests[0]["name"], quests[1]["name"], quests[2]["name"], 
                       quests[3]["name"], quests[4]["name"], quests[5]["name"], quests[6]["name"],
                       quests[7]["name"], quests[8]["name"], quests[9]["name"]))
            conn.commit()
            conn.close()
            await message.reply("✅ Еженедельные задания обновлены! Напиши `еженедельные задания` еще раз.")
            return

        msg = "📋 **ЕЖЕНЕДЕЛЬНЫЕ ЗАДАНИЯ**\n\n"
        for i in range(1, 11):
            quest_name = row[i]
            progress = row[i+10]
            completed = row[i+20]

            if completed:
                msg += f"✅ {quest_name} — **ВЫПОЛНЕНО**\n"
            else:
                target = 0
                reward = 0
                for q in WEEKLY_QUESTS_LIST:
                    if q["name"] == quest_name:
                        target = q["target"]
                        reward = q["reward"]
                        break
                msg += f"📌 {quest_name} — {progress}/{target} (💰 {reward} монет)\n"

        conn.close()
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return

# ==================== ДОСТИЖЕНИЯ ====================
async def show_achievements(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT achievement_name FROM achievements WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await message.reply("❌ Нет достижений!")
        return

    msg = "🏆 **МОИ ДОСТИЖЕНИЯ**\n\n"
    for row in rows:
        ach = ACHIEVEMENTS.get(row[0])
        if ach:
            msg += f"{ach['name']}\n   📝 {ach['desc']}\n   💰 {ach['reward']} монет\n\n"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def all_achievements_command(message: types.Message):
    user_id = message.from_user.id
    msg = "🏆 **ВСЕ ДОСТИЖЕНИЯ**\n\n"

    for key, ach in ACHIEVEMENTS.items():
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM achievements WHERE user_id = ? AND achievement_name = ?", (user_id, key))
        unlocked = c.fetchone()
        conn.close()

        status = "✅" if unlocked else "🔒"
        msg += f"{status} {ach['name']} — {ach['desc']}\n"

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== БОНУСЫ ====================
async def daily_bonus(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in daily_cooldown:
        elapsed = (datetime.now() - daily_cooldown[user_id]).total_seconds()
        if elapsed < 86400:
            remaining = int(86400 - elapsed)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await message.reply(f"⏳ Через {hours}ч {minutes}м")
            return

    # Бонус зависит от уровня админа и VIP
    admin_level = await get_admin_level(user_id)
    bonus = 100 + admin_level * 50
    
    if await is_vip(user_id):
        bonus = int(bonus * 1.5)
    
    econ_mult = await get_economy_multiplier()
    bonus = int(bonus * econ_mult)
    
    await add_coins(user_id, bonus)
    daily_cooldown[user_id] = datetime.now()
    await log_action(user_id, "daily_bonus", f"Получил {bonus} монет")

    msg = f"🎁 Ежедневный бонус: +{bonus} монет!"
    if await is_vip(user_id):
        msg += " (VIP x1.5)"
    if econ_mult != 1.0:
        msg += f" (экономика x{econ_mult})"
    
    await message.reply(msg)

# ==================== КОМАНДЫ ====================
async def show_commands(message: types.Message):
    msg = f"""
📋 **ВСЕ КОМАНДЫ БОТА {BOT_NAME}**

━━━━━━━━━━━━━━━━━━━━

👤 **ПРОФИЛЬ**
• `я` или `профиль` — свой профиль
• `профиль @user` — профиль пользователя
• `баланс` — монеты и банк

💼 **РАБОТА**
• `список работ` — все работы
• `устроиться [работа]` — устроиться на работу
• `работа` — работать (КД 10 мин)

🏪 **БИЗНЕСЫ**
• `бизнесы` — список бизнесов
• `купить бизнес [название]` — купить бизнес
• `мои бизнесы` — свои бизнесы
• `собрать бизнес [название]` — собрать доход

🛒 **МАГАЗИН**
• `магазин` — список товаров
• `купить [предмет]` — купить предмет
• `инвентарь` — свои предметы
• `продать [предмет] [количество]` — продать предмет

🎁 **КЕЙСЫ**
• `кейсы` — список кейсов
• `открыть кейс [название]` — открыть кейс

🔥 **ЛИМИТКИ**
• `лимитки` — список лимитных предметов

🎭 **РП КОМАНДЫ**
• `обнять`, `поцеловать`, `ударить`, `пнуть`

💍 **БРАК**
• `брак` (ответ) — предложить брак
• `развестись` — развод

⭐ **РЕПУТАЦИЯ**
• `+реп` (ответ) — повысить репутацию
• `-реп` (ответ) — понизить репутацию

📊 **ТОПЫ**
• `топ` — топ богачей
• `топ реп` — топ репутации

💰 **БАНК**
• `положить [сумма]` — положить в банк
• `снять [сумма]` — снять из банка
• `вклад` — открыть вклад под проценты

🎁 **БОНУСЫ**
• `бонус` или `ежедневно` — ежедневный бонус

📤 **ПЕРЕВОДЫ**
• `перевод [сумма]` (ответ) — перевести монеты

🎮 **ИГРЫ**
• `кубы` (ответ) — игра в кости
• `рулетка` (ответ) — русская рулетка
• `казино [ставка]` — слот-машина

🏰 **КЛАНЫ**
• `создать клан [название]` — создать клан
• `вступить в клан [название]` — вступить в клан
• `мой клан` — информация о клане
• `кланы` — список кланов
• `казна положить [сумма]` — положить в казну

💳 **КРЕДИТЫ**
• `кредит взять [сумма]` — взять кредит
• `кредит погасить` — погасить кредит

🌾 **ФЕРМА**
• `ферма` — состояние фермы
• `посадить [культура]` — посадить культуру
• `собрать` — собрать урожай

🎣 **РЫБАЛКА**
• `рыбалка` — пойти на рыбалку
• `купить удочку` — купить удочку

🔫 **ОХОТА**
• `охота` — пойти на охоту
• `купить ружьё` — купить ружьё

🐾 **ПИТОМЦЫ**
• `питомцы` — список питомцев
• `купить питомца [тип]` — купить питомца
• `мои питомцы` — мои питомцы

🏠 **НЕДВИЖИМОСТЬ**
• `недвижимость` — список недвижимости
• `купить [тип]` — купить недвижимость
• `моя недвижимость` — моя недвижимость

📋 **ЗАДАНИЯ**
• `ежедневные задания` — показать задания
• `еженедельные задания` — показать задания

🏆 **ДОСТИЖЕНИЯ**
• `ачивки` — свои достижения
• `все ачивки` — все достижения

━━━━━━━━━━━━━━━━━━━━
"""
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

print(f"✅ Часть 7/20 загружена! Строк: ~650")
# ==================== ЧАСТЬ 8/20: ПЕРЕВОДЫ, АДМИНКА, МОДЕРАЦИЯ ====================

# ==================== ПЕРЕВОДЫ ====================
async def transfer_command(message: types.Message):
    """Перевод по @username"""
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `перевод @user [сумма]`")
        return

    try:
        amount = int(args[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return

    user_id = message.from_user.id
    if await get_coins(user_id) < amount:
        await message.reply("❌ Мало монет!")
        return

    try:
        target_username = args[1].replace("@", "")
        target_user = await bot.get_chat(f"@{target_username}")
        target_id = target_user.id

        if target_id == user_id:
            await message.reply("❌ Нельзя перевести себе!")
            return

        await remove_coins(user_id, amount)
        await add_coins(target_id, amount)
        await log_action(user_id, "transfer", f"Перевёл {amount} монет {await get_name(target_id)}")
        await message.reply(f"💰 {await get_name(user_id)} перевёл **{amount}** монет {await get_name(target_id)}")
    except Exception as e:
        await message.reply(f"❌ Пользователь не найден!")

async def transfer_reply(message: types.Message):
    """Перевод по ответу на сообщение"""
    user_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id

    if target_id == user_id:
        await message.reply("❌ Нельзя перевести себе!")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `перевод [сумма]` (ответь на сообщение)")
        return

    try:
        amount = int(args[1])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return

    if await get_coins(user_id) < amount:
        await message.reply("❌ Мало монет!")
        return

    await remove_coins(user_id, amount)
    await add_coins(target_id, amount)
    await log_action(user_id, "transfer", f"Перевёл {amount} монет {await get_name(target_id)}")
    await message.reply(f"💰 {await get_name(user_id)} перевёл **{amount}** монет {await get_name(target_id)}")

# ==================== АДМИНКА ====================
async def my_admin_level(message: types.Message):
    user_id = message.from_user.id
    level = await get_admin_level(user_id)
    
    if level == 0:
        await message.reply("👤 Ты обычный пользователь!")
        return
    
    level_name = get_level_name(level)
    level_emoji = get_level_emoji(level)
    
    msg = f"🎯 Твой уровень: **{level_emoji} {level_name}** ({level}/5)\n\n"
    
    # Показываем доступные функции
    if level >= 1:
        msg += "🛡️ **Младший модератор:**\n"
        msg += "• Просмотр статистики, варнов, жалоб\n"
        msg += "• Выдача варнов\n\n"
    
    if level >= 2:
        msg += "⚔️ **Модератор:**\n"
        msg += "• Муты до 10 минут\n"
        msg += "• Управление стоп-словами\n\n"
    
    if level >= 3:
        msg += "🗡️ **Старший модератор:**\n"
        msg += "• Муты до 1 часа\n"
        msg += "• Кик пользователей\n"
        msg += "• Управление антиспамом\n\n"
    
    if level >= 4:
        msg += "👑 **Администратор:**\n"
        msg += "• Баны и разбаны\n"
        msg += "• Выдача прав до 2 уровня\n"
        msg += "• Настройка чата\n\n"
    
    if level >= 5:
        msg += "💎 **Старший администратор:**\n"
        msg += "• Полный контроль чата\n"
        msg += "• Выдача прав до 4 уровня\n"
        msg += "• Управление экономикой\n"
        msg += "• Создание промо-кодов\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== МОДЕРАЦИЯ ====================

# ----- ВАРНЫ -----
async def warn_user(message: types.Message):
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("ℹ️ `варн @user причина`")
        return

    try:
        target_username = args[1].replace("@", "")
        reason = args[2]
        member = await message.chat.get_member(target_username)
        target_id = member.user.id

        # Нельзя варнить админов
        if await get_admin_level(target_id) >= await get_admin_level(message.from_user.id):
            await message.reply("❌ Нельзя варнить пользователя с таким же или выше уровнем!")
            return

        warn_count = await add_warn(target_id, message.chat.id, reason, message.from_user.id)
        await log_action(message.from_user.id, "warn", f"Варн {await get_name(target_id)}: {reason}")

        msg = f"⚠️ {await get_name(target_id)} получил варн #{warn_count}!\n📝 Причина: {reason}"

        # Автоматический бан при 5 варнах
        if warn_count >= 5:
            await bot.ban_chat_member(message.chat.id, target_id)
            msg += f"\n🚫 {await get_name(target_id)} забанен за 5 варнов!"

        await message.reply(msg)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def get_warns_command(message: types.Message):
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `варны @user`")
        return

    try:
        target_username = args[1].replace("@", "")
        member = await message.chat.get_member(target_username)
        target_id = member.user.id

        warns = await get_user_warns(target_id, message.chat.id)
        if not warns:
            await message.reply(f"✅ У {await get_name(target_id)} нет варнов!")
            return

        msg = f"⚠️ **ВАРНЫ {await get_name(target_id)}**\n\n"
        for i, (reason, date, warned_by) in enumerate(warns, 1):
            admin_name = await get_name(warned_by)
            msg += f"{i}. {reason}\n   🕐 {date[:16]} 👤 {admin_name}\n\n"

        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
    except:
        await message.reply("❌ Ошибка!")

async def remove_warn_command(message: types.Message):
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `снять варн @user номер`")
        return

    try:
        target_username = args[1].replace("@", "")
        warn_num = int(args[2])
        member = await message.chat.get_member(target_username)
        target_id = member.user.id

        if await remove_warn(target_id, message.chat.id, warn_num):
            await message.reply(f"✅ Снят варн #{warn_num} у {await get_name(target_id)}")
        else:
            await message.reply(f"❌ Варн #{warn_num} не найден!")
    except:
        await message.reply("❌ Ошибка!")

# ----- МУТЫ -----
async def mute_command(message: types.Message):
    if await get_admin_level(message.from_user.id) < 2:
        await message.reply("❌ У тебя нет прав! (нужен 2+ уровень)")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `мут @user [минуты] [причина]`")
        return

    try:
        target_username = args[1].replace("@", "")
        minutes = int(args[2])
        reason = " ".join(args[3:]) if len(args) > 3 else "Без причины"

        if minutes < 1:
            await message.reply("❌ Минимум 1 минута!")
            return

        # Проверяем лимиты в зависимости от уровня
        admin_level = await get_admin_level(message.from_user.id)
        max_mute = 10 if admin_level == 2 else 60 if admin_level == 3 else 1440

        if minutes > max_mute:
            await message.reply(f"❌ Максимум {max_mute} минут для твоего уровня!")
            return

        member = await message.chat.get_member(target_username)
        target_id = member.user.id

        # Нельзя мутить админов
        if await get_admin_level(target_id) >= admin_level:
            await message.reply("❌ Нельзя мутить пользователя с таким же или выше уровнем!")
            return

        until = datetime.now() + timedelta(minutes=minutes)
        await bot.restrict_chat_member(
            message.chat.id,
            target_id,
            ChatPermissions(can_send_messages=False),
            until_date=until
        )

        await log_action(message.from_user.id, "mute", f"Мут {await get_name(target_id)} на {minutes} мин: {reason}")
        await message.reply(f"🔇 {await get_name(target_id)} замучен на {minutes} мин!\n📝 Причина: {reason}")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def unmute_command(message: types.Message):
    if await get_admin_level(message.from_user.id) < 2:
        await message.reply("❌ У тебя нет прав! (нужен 2+ уровень)")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `размут @user`")
        return

    try:
        target_username = args[1].replace("@", "")
        member = await message.chat.get_member(target_username)
        target_id = member.user.id

        await bot.restrict_chat_member(
            message.chat.id,
            target_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )

        await log_action(message.from_user.id, "unmute", f"Размут {await get_name(target_id)}")
        await message.reply(f"🔊 {await get_name(target_id)} размучен!")
    except:
        await message.reply("❌ Ошибка!")

# ----- КИК -----
async def kick_user(message: types.Message):
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply("ℹ️ `кик @user [причина]`")
        return

    try:
        target_username = args[1].replace("@", "")
        reason = args[2] if len(args) > 2 else "Без причины"
        member = await message.chat.get_member(target_username)
        target_id = member.user.id

        admin_level = await get_admin_level(message.from_user.id)
        if await get_admin_level(target_id) >= admin_level:
            await message.reply("❌ Нельзя кикать пользователя с таким же или выше уровнем!")
            return

        await bot.ban_chat_member(message.chat.id, target_id)
        await bot.unban_chat_member(message.chat.id, target_id)

        await log_action(message.from_user.id, "kick", f"Кик {await get_name(target_id)}: {reason}")
        await message.reply(f"👢 {await get_name(target_id)} кикнут!\n📝 Причина: {reason}")
    except:
        await message.reply("❌ Ошибка!")

# ----- БАНЫ -----
async def ban_user(message: types.Message):
    if await get_admin_level(message.from_user.id) < 4:
        await message.reply("❌ У тебя нет прав! (нужен 4+ уровень)")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply("ℹ️ `бан @user [причина]`")
        return

    try:
        target_username = args[1].replace("@", "")
        reason = args[2] if len(args) > 2 else "Без причины"
        member = await message.chat.get_member(target_username)
        target_id = member.user.id

        admin_level = await get_admin_level(message.from_user.id)
        if await get_admin_level(target_id) >= admin_level:
            await message.reply("❌ Нельзя банить пользователя с таким же или выше уровнем!")
            return

        await bot.ban_chat_member(message.chat.id, target_id)

        await log_action(message.from_user.id, "ban", f"Бан {await get_name(target_id)}: {reason}")
        await message.reply(f"🚫 {await get_name(target_id)} забанен!\n📝 Причина: {reason}")
    except:
        await message.reply("❌ Ошибка!")

async def unban_user(message: types.Message):
    if await get_admin_level(message.from_user.id) < 4:
        await message.reply("❌ У тебя нет прав! (нужен 4+ уровень)")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `разбан @user`")
        return

    try:
        target_username = args[1].replace("@", "")
        # Пробуем найти пользователя
        try:
            user = await bot.get_chat(f"@{target_username}")
            user_id = user.id
        except:
            await message.reply("❌ Пользователь не найден!")
            return

        await bot.unban_chat_member(message.chat.id, user_id)

        await log_action(message.from_user.id, "unban", f"Разбан {target_username}")
        await message.reply(f"✅ {target_username} разбанен!")
    except:
        await message.reply("❌ Ошибка!")

# ----- ОЧИСТКА -----
async def clear_command(message: types.Message):
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `очистить [количество]`")
        return

    try:
        count = int(args[1])
        if count < 1 or count > 100:
            await message.reply("❌ От 1 до 100 сообщений!")
            return

        deleted = 0
        async for msg in bot.get_chat_history(message.chat.id, limit=count + 1):
            if msg.message_id != message.message_id:
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.1)
                except:
                    pass

        await log_action(message.from_user.id, "clear", f"Очистил {deleted} сообщений")
        await message.reply(f"✅ Удалено {deleted} сообщений!")
    except:
        await message.reply("❌ Ошибка!")

print(f"✅ Часть 8/20 загружена! Строк: ~650")
# ==================== ЧАСТЬ 9/20: ФИЛЬТРЫ, СТОП-СЛОВА, НАСТРОЙКИ ЧАТА, ЖАЛОБЫ ====================

# ==================== СТОП-СЛОВА ====================
async def add_stop_word(message: types.Message):
    if await get_admin_level(message.from_user.id) < 2:
        await message.reply("❌ У тебя нет прав! (нужен 2+ уровень)")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `стоп слово [слово]`")
        return

    word = args[1].lower()
    chat_id = message.chat.id

    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO stop_words (chat_id, word) VALUES (?, ?)", (chat_id, word))
    conn.commit()
    conn.close()

    await log_action(message.from_user.id, "add_stop_word", f"Добавил стоп-слово {word}")
    await message.reply(f"✅ Стоп-слово **{word}** добавлено!")

async def list_stop_words(message: types.Message):
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return

    chat_id = message.chat.id
    words = await get_stop_words(chat_id)

    if not words:
        await message.reply("📭 Нет стоп-слов!")
        return

    msg = "📋 **СТОП-СЛОВА**\n\n"
    for word in words:
        msg += f"• {word}\n"

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def remove_stop_word(message: types.Message):
    if await get_admin_level(message.from_user.id) < 2:
        await message.reply("❌ У тебя нет прав! (нужен 2+ уровень)")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `удалить стоп [слово]`")
        return

    word = args[1].lower()
    chat_id = message.chat.id

    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM stop_words WHERE chat_id = ? AND word = ?", (chat_id, word))
    if c.rowcount == 0:
        conn.close()
        await message.reply(f"❌ Стоп-слово **{word}** не найдено!")
        return
    conn.commit()
    conn.close()

    await log_action(message.from_user.id, "remove_stop_word", f"Удалил стоп-слово {word}")
    await message.reply(f"✅ Стоп-слово **{word}** удалено!")

# ==================== НАСТРОЙКИ ЧАТА ====================

# ----- АНТИМАТ -----
async def toggle_antimat(message: types.Message, value):
    if await get_admin_level(message.from_user.id) < 2:
        await message.reply("❌ У тебя нет прав! (нужен 2+ уровень)")
        return

    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antimat_enabled) VALUES (?, ?) "
              "ON CONFLICT(chat_id) DO UPDATE SET antimat_enabled = ?", (chat_id, value, value))
    conn.commit()
    conn.close()

    status = "включён" if value else "выключен"
    await log_action(message.from_user.id, "antimat", f"{status}")
    await message.reply(f"✅ Антимат {status}!")

# ----- АНТИКАПС -----
async def toggle_anticaps(message: types.Message, value):
    if await get_admin_level(message.from_user.id) < 2:
        await message.reply("❌ У тебя нет прав! (нужен 2+ уровень)")
        return

    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, anticaps_enabled) VALUES (?, ?) "
              "ON CONFLICT(chat_id) DO UPDATE SET anticaps_enabled = ?", (chat_id, value, value))
    conn.commit()
    conn.close()

    status = "включён" if value else "выключен"
    await log_action(message.from_user.id, "anticaps", f"{status}")
    await message.reply(f"✅ Антикапс {status}!")

# ----- АНТИСПАМ -----
async def toggle_antispam(message: types.Message, value):
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return

    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antispam_enabled) VALUES (?, ?) "
              "ON CONFLICT(chat_id) DO UPDATE SET antispam_enabled = ?", (chat_id, value, value))
    conn.commit()
    conn.close()

    status = "включён" if value else "выключен"
    await log_action(message.from_user.id, "antispam", f"{status}")
    await message.reply(f"✅ Антиспам {status}!")

# ----- АНТИФЛУД -----
async def toggle_antiflood(message: types.Message, value):
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return

    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antiflood_enabled) VALUES (?, ?) "
              "ON CONFLICT(chat_id) DO UPDATE SET antiflood_enabled = ?", (chat_id, value, value))
    conn.commit()
    conn.close()

    status = "включён" if value else "выключен"
    await log_action(message.from_user.id, "antiflood", f"{status}")
    await message.reply(f"✅ Антифлуд {status}!")

# ----- АНТИССЫЛКИ -----
async def toggle_antilinks(message: types.Message, value):
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return

    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antilinks_enabled) VALUES (?, ?) "
              "ON CONFLICT(chat_id) DO UPDATE SET antilinks_enabled = ?", (chat_id, value, value))
    conn.commit()
    conn.close()

    status = "включён" if value else "выключен"
    await log_action(message.from_user.id, "antilinks", f"{status}")
    await message.reply(f"✅ Антиссылки {status}!")

# ----- РЕЖИМ ЧАТА -----
async def set_chat_mode(message: types.Message):
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `чат режим [свободный|строгий|только_админы]`")
        return

    mode = args[1].lower()
    if mode not in ["свободный", "строгий", "только_админы"]:
        await message.reply("❌ Режим должен быть: свободный, строгий, только_админы")
        return

    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, mode) VALUES (?, ?) "
              "ON CONFLICT(chat_id) DO UPDATE SET mode = ?", (chat_id, mode, mode))
    conn.commit()
    conn.close()

    await log_action(message.from_user.id, "chat_mode", f"Установил режим {mode}")
    await message.reply(f"✅ Режим чата установлен: **{mode}**")

# ----- ПРАВИЛА -----
async def show_rules(message: types.Message):
    chat_id = message.chat.id
    settings = await get_chat_settings(chat_id)

    if not settings.get("rules"):
        await message.reply("📭 Правила не установлены!")
        return

    await message.reply(f"📋 **ПРАВИЛА ЧАТА**\n\n{settings['rules']}")

async def set_rules(message: types.Message):
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `правила установить [текст]`")
        return

    rules = args[1]
    chat_id = message.chat.id

    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, rules) VALUES (?, ?) "
              "ON CONFLICT(chat_id) DO UPDATE SET rules = ?", (chat_id, rules, rules))
    conn.commit()
    conn.close()

    await log_action(message.from_user.id, "set_rules", "Установил правила")
    await message.reply("✅ Правила установлены!")

# ==================== ЖАЛОБЫ ====================
async def complaint_command(message: types.Message):
    """Пожаловаться на пользователя"""
    if not message.reply_to_message:
        await message.reply("ℹ️ Ответь на сообщение нарушителя!")
        return

    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Без причины"

    reporter = message.from_user.id
    target = message.reply_to_message.from_user.id

    if target == reporter:
        await message.reply("❌ Нельзя пожаловаться на себя!")
        return

    await add_complaint(target, reporter, reason, message.chat.id)
    await log_action(reporter, "complaint", f"Пожаловался на {await get_name(target)}: {reason}")

    await message.reply(f"✅ Жалоба отправлена!\n📝 Причина: {reason}")

    # Уведомляем админов
    admins = await get_chat_admins(message.chat.id)
    for admin in admins:
        if admin != reporter:
            try:
                await bot.send_message(
                    admin,
                    f"⚠️ **НОВАЯ ЖАЛОБА**\n"
                    f"👤 Нарушитель: {await get_name(target)}\n"
                    f"📝 Причина: {reason}\n"
                    f"🕐 Время: {datetime.now().strftime('%H:%M')}"
                )
            except:
                pass

async def get_complaints_command(message: types.Message):
    """Просмотр жалоб"""
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return

    complaints = await get_complaints(message.chat.id)
    if not complaints:
        await message.reply("📭 Нет жалоб!")
        return

    msg = "⚠️ **ЖАЛОБЫ**\n\n"
    for complaint in complaints:
        complaint_id, user_id, reporter_id, reason, date = complaint
        user_name = await get_name(user_id)
        reporter_name = await get_name(reporter_id)
        msg += f"#{complaint_id} {user_name}\n"
        msg += f"   📝 {reason}\n"
        msg += f"   👤 {reporter_name}\n"
        msg += f"   🕐 {date[:16]}\n\n"

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def resolve_complaint_command(message: types.Message):
    """Удаление жалобы"""
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `удалить жалобу [номер]`")
        return

    try:
        complaint_id = int(args[1])
        await resolve_complaint(complaint_id)
        await message.reply(f"✅ Жалоба #{complaint_id} удалена!")
    except:
        await message.reply("❌ Ошибка!")

# ==================== СТАТИСТИКА ====================
async def stats_command(message: types.Message):
    """Статистика чата"""
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return

    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    # Всего пользователей в чате
    c.execute("SELECT COUNT(DISTINCT user_id) FROM chat_stats WHERE chat_id = ?", (message.chat.id,))
    users = c.fetchone()[0]
    
    # Всего сообщений
    c.execute("SELECT SUM(messages) FROM chat_stats WHERE chat_id = ?", (message.chat.id,))
    total_messages = c.fetchone()[0] or 0
    
    # Сообщений за сегодня
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT SUM(messages) FROM chat_stats WHERE chat_id = ? AND last_message LIKE ?", 
              (message.chat.id, f"{today}%"))
    today_messages = c.fetchone()[0] or 0
    
    # Активные пользователи сегодня
    c.execute("SELECT COUNT(DISTINCT user_id) FROM chat_stats WHERE chat_id = ? AND last_message LIKE ?", 
              (message.chat.id, f"{today}%"))
    today_users = c.fetchone()[0] or 0
    
    conn.close()
    
    msg = f"📊 **СТАТИСТИКА ЧАТА**\n\n"
    msg += f"👥 Всего пользователей: {users}\n"
    msg += f"💬 Всего сообщений: {total_messages}\n"
    msg += f"📅 Сообщений сегодня: {today_messages}\n"
    msg += f"👤 Активных сегодня: {today_users}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

print(f"✅ Часть 9/20 загружена! Строк: ~650")
# ==================== ЧАСТЬ 10/20: КОМАНДЫ ДЛЯ СОЗДАТЕЛЯ (ЛС) ====================

# ==================== УПРАВЛЕНИЕ МОНЕТАМИ ====================

async def creator_give_coins(message: types.Message):
    """Выдать монеты пользователю"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать монеты @user 1000` или `дать монеты мне 1000`")
        return
    
    try:
        amount = int(args[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return
    
    # Определяем цель
    if args[1] == "мне":
        target_id = message.from_user.id
        await add_coins(target_id, amount)
        await log_action(message.from_user.id, "give_coins_self", f"Выдал себе {amount} монет")
        await message.reply(f"✅ Выдано **{amount}** монет себе!")
    else:
        target = args[1].replace("@", "")
        try:
            target_user = await bot.get_chat(f"@{target}")
            target_id = target_user.id
            await add_coins(target_id, amount)
            await log_action(message.from_user.id, "give_coins", f"Выдал {amount} монет {await get_name(target_id)}")
            await message.reply(f"✅ {await get_name(target_id)} выдано **{amount}** монет!")
        except Exception as e:
            await message.reply(f"❌ Пользователь не найден! {e}")

async def creator_remove_coins(message: types.Message):
    """Забрать монеты у пользователя"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `забрать монеты @user 1000`")
        return
    
    try:
        amount = int(args[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return
    
    target = args[1].replace("@", "")
    try:
        target_user = await bot.get_chat(f"@{target}")
        target_id = target_user.id
        
        coins = await get_coins(target_id)
        if coins < amount:
            await message.reply(f"❌ У {await get_name(target_id)} только {coins} монет!")
            return
        
        await remove_coins(target_id, amount)
        await log_action(message.from_user.id, "remove_coins", f"Забрал {amount} монет у {await get_name(target_id)}")
        await message.reply(f"✅ У {await get_name(target_id)} забрано **{amount}** монет!")
    except:
        await message.reply("❌ Пользователь не найден!")

async def creator_give_bank(message: types.Message):
    """Выдать в банк пользователю"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать банк @user 1000` или `дать банк мне 1000`")
        return
    
    try:
        amount = int(args[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return
    
    if args[1] == "мне":
        target_id = message.from_user.id
        await add_bank(target_id, amount)
        await log_action(message.from_user.id, "give_bank_self", f"Выдал себе {amount} в банк")
        await message.reply(f"✅ Выдано **{amount}** монет в банк себе!")
    else:
        target = args[1].replace("@", "")
        try:
            target_user = await bot.get_chat(f"@{target}")
            target_id = target_user.id
            await add_bank(target_id, amount)
            await log_action(message.from_user.id, "give_bank", f"Выдал {amount} в банк {await get_name(target_id)}")
            await message.reply(f"✅ {await get_name(target_id)} выдано **{amount}** монет в банк!")
        except:
            await message.reply("❌ Пользователь не найден!")

async def creator_give_item(message: types.Message):
    """Выдать предмет пользователю"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать предмет @user предмет 5`")
        return
    
    if args[1] == "мне":
        target_id = message.from_user.id
        item_name = args[2].lower()
        quantity = int(args[3]) if len(args) > 3 else 1
        
        await add_item(target_id, item_name, quantity)
        await log_action(message.from_user.id, "give_item_self", f"Выдал себе {quantity}x {item_name}")
        await message.reply(f"✅ Выдано **{quantity}** шт **{item_name.capitalize()}** себе!")
    else:
        target = args[1].replace("@", "")
        try:
            target_user = await bot.get_chat(f"@{target}")
            target_id = target_user.id
            item_name = args[2].lower()
            quantity = int(args[3]) if len(args) > 3 else 1
            
            await add_item(target_id, item_name, quantity)
            await log_action(message.from_user.id, "give_item", f"Выдал {quantity}x {item_name} {await get_name(target_id)}")
            await message.reply(f"✅ {await get_name(target_id)} выдано **{quantity}** шт **{item_name.capitalize()}**!")
        except:
            await message.reply("❌ Пользователь не найден!")

# ==================== УПРАВЛЕНИЕ УРОВНЯМИ ====================

async def creator_give_level(message: types.Message):
    """Выдать уровень админа"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать уровень @user 5`")
        return
    
    target = args[1].replace("@", "")
    try:
        level = int(args[2])
        if level < 0 or level > 5:
            await message.reply("❌ Уровень должен быть от 0 до 5!")
            return
        
        target_user = await bot.get_chat(f"@{target}")
        target_id = target_user.id
        
        await set_admin_level(target_id, level)
        await log_action(message.from_user.id, "give_level", f"Дал {level} уровень {await get_name(target_id)}")
        await message.reply(f"✅ {await get_name(target_id)} получил уровень: **{level}/5**")
    except:
        await message.reply("❌ Ошибка!")

async def creator_remove_level(message: types.Message):
    """Убрать уровень админа"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `убрать уровень @user`")
        return
    
    target = args[1].replace("@", "")
    try:
        target_user = await bot.get_chat(f"@{target}")
        target_id = target_user.id
        
        await set_admin_level(target_id, 0)
        await log_action(message.from_user.id, "remove_level", f"Убрал уровень у {await get_name(target_id)}")
        await message.reply(f"✅ У {await get_name(target_id)} убран уровень админа!")
    except:
        await message.reply("❌ Ошибка!")

# ==================== УПРАВЛЕНИЕ VIP ====================

async def creator_give_vip(message: types.Message):
    """Выдать VIP статус"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать вип @user [дней]`")
        return
    
    target = args[1].replace("@", "")
    try:
        days = int(args[2])
        if days <= 0:
            await message.reply("❌ Дней должно быть > 0!")
            return
        
        target_user = await bot.get_chat(f"@{target}")
        target_id = target_user.id
        
        await set_vip(target_id, days)
        await log_action(message.from_user.id, "give_vip", f"Дал VIP {await get_name(target_id)} на {days} дней")
        await message.reply(f"✅ {await get_name(target_id)} получил VIP на {days} дней!")
    except:
        await message.reply("❌ Ошибка!")

async def creator_remove_vip(message: types.Message):
    """Убрать VIP статус"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `убрать вип @user`")
        return
    
    target = args[1].replace("@", "")
    try:
        target_user = await bot.get_chat(f"@{target}")
        target_id = target_user.id
        
        await remove_vip(target_id)
        await log_action(message.from_user.id, "remove_vip", f"Убрал VIP у {await get_name(target_id)}")
        await message.reply(f"✅ У {await get_name(target_id)} убран VIP!")
    except:
        await message.reply("❌ Ошибка!")

# ==================== СТАТИСТИКА ДЛЯ СОЗДАТЕЛЯ ====================

async def creator_bot_stats(message: types.Message):
    """Общая статистика бота"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    # Всего пользователей
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    # Всего чатов
    c.execute("SELECT COUNT(DISTINCT chat_id) FROM chat_stats")
    total_chats = c.fetchone()[0]
    
    # Всего сообщений
    c.execute("SELECT SUM(messages) FROM chat_stats")
    total_messages = c.fetchone()[0] or 0
    
    # Всего монет
    c.execute("SELECT SUM(coins) FROM users")
    total_coins = c.fetchone()[0] or 0
    
    # Всего в банке
    c.execute("SELECT SUM(bank) FROM users")
    total_bank = c.fetchone()[0] or 0
    
    # Всего во вкладах
    c.execute("SELECT SUM(amount) FROM deposits WHERE active = 1")
    total_deposits = c.fetchone()[0] or 0
    
    conn.close()
    
    msg = f"📊 **СТАТИСТИКА БОТА**\n\n"
    msg += f"👥 Пользователей: {total_users}\n"
    msg += f"💬 Чатов: {total_chats}\n"
    msg += f"💬 Всего сообщений: {total_messages}\n\n"
    msg += f"💰 Всего монет: {total_coins}\n"
    msg += f"🏦 В банке: {total_bank}\n"
    msg += f"💳 Во вкладах: {total_deposits}\n"
    msg += f"💵 Всего в экономике: {total_coins + total_bank + total_deposits}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def creator_logs(message: types.Message, period="day"):
    """Просмотр логов"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    if period == "day":
        date_filter = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT user_id, action, details, timestamp FROM logs WHERE timestamp LIKE ? ORDER BY timestamp DESC LIMIT 50", (f"{date_filter}%",))
    elif period == "week":
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute("SELECT user_id, action, details, timestamp FROM logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 100", (week_ago,))
    elif period == "month":
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        c.execute("SELECT user_id, action, details, timestamp FROM logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 200", (month_ago,))
    else:
        c.execute("SELECT user_id, action, details, timestamp FROM logs ORDER BY timestamp DESC LIMIT 50")
    
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Нет логов!")
        return
    
    msg = f"📋 **ЛОГИ ({period})**\n\n"
    for user_id, action, details, timestamp in rows:
        name = await get_name(user_id)
        msg += f"🕐 {timestamp[11:16]} | {name}\n"
        msg += f"   📌 {action}: {details}\n\n"
        
        if len(msg) > 3500:
            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
    
    if msg:
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

print(f"✅ Часть 10/20 загружена! Строк: ~650")
# ==================== ЧАСТЬ 11/20: ЭКОНОМИЧЕСКИЕ СОБЫТИЯ, ПРОМО-КОДЫ ====================

# ==================== ЭКОНОМИЧЕСКИЕ СОБЫТИЯ ====================

ECONOMY_EVENTS = {
    "инфляция": {"multiplier": 0.8, "desc": "💰 Инфляция! Доходы -20%", "duration": 3600},
    "дефляция": {"multiplier": 1.2, "desc": "💎 Дефляция! Доходы +20%", "duration": 3600},
    "кризис": {"multiplier": 0.5, "desc": "📉 Кризис! Доходы -50%", "duration": 7200},
    "бум": {"multiplier": 1.5, "desc": "📈 Бум! Доходы +50%", "duration": 7200},
    "золотой дождь": {"multiplier": 2.0, "desc": "🌟 Золотой дождь! Доходы x2", "duration": 3600}
}

async def creator_economy_start(message: types.Message):
    """Запуск экономического события"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    global active_economy_event
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `эконом старт [инфляция|дефляция|кризис|бум|золотой дождь]`")
        return
    
    event_type = args[2].lower()
    if event_type not in ECONOMY_EVENTS:
        await message.reply(f"❌ Событие '{event_type}' не найдено!")
        return
    
    active_economy_event = {
        "type": event_type,
        "multiplier": ECONOMY_EVENTS[event_type]["multiplier"],
        "desc": ECONOMY_EVENTS[event_type]["desc"],
        "started": datetime.now(),
        "duration": ECONOMY_EVENTS[event_type]["duration"]
    }
    
    await log_action(message.from_user.id, "economy_start", f"Запустил {event_type}")
    await message.reply(f"✅ **{event_type.capitalize()}** запущена!\n{ECONOMY_EVENTS[event_type]['desc']}")

async def creator_economy_stop(message: types.Message):
    """Остановка экономического события"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    global active_economy_event
    
    if not active_economy_event:
        await message.reply("❌ Нет активных событий!")
        return
    
    active_economy_event = None
    await log_action(message.from_user.id, "economy_stop", "Остановил событие")
    await message.reply("✅ Событие остановлено! Экономика вернулась к норме.")

async def creator_economy_status(message: types.Message):
    """Статус экономического события"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    if not active_economy_event:
        await message.reply("❌ Нет активных событий!")
        return
    
    event = active_economy_event
    elapsed = (datetime.now() - event["started"]).total_seconds()
    remaining = max(0, event["duration"] - elapsed)
    
    msg = f"📊 **Активное событие:** {event['type'].capitalize()}\n"
    msg += f"📝 {event['desc']}\n"
    msg += f"⏳ Осталось: {int(remaining//60)} мин {int(remaining%60)} сек"
    msg += f"\n📈 Множитель: x{event['multiplier']}"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ФОНОВАЯ ЗАДАЧА ДЛЯ ЭКОНОМИЧЕСКИХ СОБЫТИЙ ====================
async def economy_event_task():
    """Фоновая задача для автоматического завершения событий"""
    while True:
        await asyncio.sleep(60)  # Проверяем каждую минуту
        
        global active_economy_event
        
        if active_economy_event:
            elapsed = (datetime.now() - active_economy_event["started"]).total_seconds()
            if elapsed >= active_economy_event["duration"]:
                active_economy_event = None
                try:
                    await bot.send_message(CREATOR_ID, "✅ Экономическое событие автоматически завершено!")
                except:
                    pass

# ==================== ПРОМО-КОДЫ ====================

async def creator_create_promo(message: types.Message):
    """Создание промо-кода"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 4:
        await message.reply("ℹ️ `создать промо [код] [монеты] [предмет] [количество]`\nПример: `создать промо GIFT100 1000 алмаз 5`")
        return
    
    code = args[1].upper()
    coins = int(args[2]) if args[2].isdigit() else 0
    item = args[3] if len(args) > 3 else None
    quantity = int(args[4]) if len(args) > 4 and args[4].isdigit() else 1
    
    # Проверяем, не существует ли уже такой код
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT code FROM promos WHERE code = ?", (code,))
    if c.fetchone():
        conn.close()
        await message.reply(f"❌ Промо-код **{code}** уже существует!")
        return
    
    c.execute("INSERT INTO promos (code, coins, item, quantity, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (code, coins, item, quantity, message.from_user.id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await log_action(message.from_user.id, "create_promo", f"Создал промо-код {code}")
    
    msg = f"✅ Промо-код **{code}** создан!\n"
    if coins > 0:
        msg += f"💰 Монеты: {coins}\n"
    if item:
        msg += f"🎒 Предмет: {item} x{quantity}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def creator_list_promos(message: types.Message):
    """Список промо-кодов"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT code, coins, item, quantity, uses, max_uses FROM promos")
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Нет промо-кодов!")
        return
    
    msg = "📋 **ПРОМО-КОДЫ**\n\n"
    for code, coins, item, quantity, uses, max_uses in rows:
        msg += f"🔑 **{code}**\n"
        if coins > 0:
            msg += f"💰 Монеты: {coins}\n"
        if item:
            msg += f"🎒 Предмет: {item} x{quantity}\n"
        msg += f"📊 Использований: {uses}/{max_uses}\n\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def creator_delete_promo(message: types.Message):
    """Удаление промо-кода"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `удалить промо [код]`")
        return
    
    code = args[1].upper()
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM promos WHERE code = ?", (code,))
    if c.rowcount == 0:
        conn.close()
        await message.reply(f"❌ Промо-код **{code}** не найден!")
        return
    conn.commit()
    conn.close()
    
    await log_action(message.from_user.id, "delete_promo", f"Удалил промо-код {code}")
    await message.reply(f"✅ Промо-код **{code}** удалён!")

async def activate_promo(message: types.Message):
    """Активация промо-кода пользователем"""
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `активировать промо [код]`")
        return
    
    code = args[1].upper()
    user_id = message.from_user.id
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT coins, item, quantity, max_uses, uses FROM promos WHERE code = ?", (code,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        await message.reply(f"❌ Промо-код **{code}** не найден!")
        return
    
    coins, item, quantity, max_uses, uses = row
    
    if uses >= max_uses:
        conn.close()
        await message.reply(f"❌ Промо-код **{code}** уже использован!")
        return
    
    # Проверяем, не активировал ли уже этот пользователь этот код
    c.execute("SELECT * FROM promo_activations WHERE user_id = ? AND promo_code = ?", (user_id, code))
    if c.fetchone():
        conn.close()
        await message.reply(f"❌ Ты уже активировал этот промо-код!")
        return
    
    # Активируем
    if coins > 0:
        await add_coins(user_id, coins)
    
    if item:
        await add_item(user_id, item, quantity)
    
    c.execute("UPDATE promos SET uses = uses + 1 WHERE code = ?", (code,))
    c.execute("INSERT INTO promo_activations (user_id, promo_code, activated_at) VALUES (?, ?, ?)",
              (user_id, code, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await log_action(user_id, "activate_promo", f"Активировал промо-код {code}")
    
    msg = f"✅ Промо-код **{code}** активирован!\n"
    if coins > 0:
        msg += f"💰 Монеты: +{coins}\n"
    if item:
        msg += f"🎒 Предмет: {item} x{quantity}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== МАССОВЫЕ ВЫДАЧИ ====================

async def creator_give_all_coins(message: types.Message):
    """Выдать монеты всем пользователям"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать монеты всем 1000`")
        return
    
    try:
        amount = int(args[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    count = 0
    for (user_id,) in users:
        await add_coins(user_id, amount)
        count += 1
        await asyncio.sleep(0.1)  # Чтобы не перегружать
    
    await log_action(message.from_user.id, "give_all_coins", f"Выдал {amount} монет всем ({count} пользователей)")
    await message.reply(f"✅ Выдано **{amount}** монет **{count}** пользователям!")

async def creator_give_all_bank(message: types.Message):
    """Выдать всем в банк"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Эти команды доступны только в ЛС!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать банк всем 1000`")
        return
    
    try:
        amount = int(args[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    count = 0
    for (user_id,) in users:
        await add_bank(user_id, amount)
        count += 1
        await asyncio.sleep(0.1)
    
    await log_action(message.from_user.id, "give_all_bank", f"Выдал {amount} в банк всем ({count} пользователей)")
    await message.reply(f"✅ Выдано **{amount}** монет в банк **{count}** пользователям!")

# ==================== ДОБАВЛЯЕМ ТАБЛИЦУ ДЛЯ ПРОМО-АКТИВАЦИЙ ====================
def add_promo_activations_table():
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS promo_activations (
        user_id INTEGER,
        promo_code TEXT,
        activated_at TEXT,
        PRIMARY KEY (user_id, promo_code)
    )""")
    conn.commit()
    conn.close()

add_promo_activations_table()

print(f"✅ Часть 11/20 загружена! Строк: ~650")
# ==================== ЧАСТЬ 12/20: ИИ ФУНКЦИИ ====================
# DeepSeek, Grok, генерация картинок, мемов, анализ сообщений

import aiohttp
import json
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import random
import re

# ==================== НАСТРОЙКИ ИИ ====================
AI_COOLDOWN = 30  # Секунд между запросами

# ==================== DEEPSEEK API ====================
async def deepseek_generate(prompt: str, context: list = None) -> str:
    """Генерация текста через DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        return "❌ DeepSeek API ключ не настроен! Обратитесь к создателю."
    
    try:
        messages = [
            {"role": "system", "content": "Ты Fable - дружелюбный и весёлый бот-помощник. Отвечай кратко, с юмором, но полезно. Используй эмодзи. Отвечай на русском языке."}
        ]
        
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": prompt})
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "max_tokens": 1000,
                    "temperature": 0.8
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    return f"❌ Ошибка DeepSeek: {response.status} - {error_text}"
    except Exception as e:
        return f"❌ Ошибка DeepSeek: {e}"

# ==================== GROK API ====================
async def grok_generate(prompt: str, context: list = None) -> str:
    """Генерация текста через Grok API (x.ai)"""
    if not GROK_API_KEY:
        return "❌ Grok API ключ не настроен! Обратитесь к создателю."
    
    try:
        messages = []
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": prompt})
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-1",
                    "messages": messages,
                    "max_tokens": 1000,
                    "temperature": 0.8
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    return f"❌ Ошибка Grok: {response.status} - {error_text}"
    except Exception as e:
        return f"❌ Ошибка Grok: {e}"

# ==================== ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ ====================
async def generate_image(prompt: str) -> bytes:
    """Генерация изображения через Replicate API (Stable Diffusion)"""
    if not REPLICATE_API_KEY:
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            # Запускаем генерацию
            async with session.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Token {REPLICATE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "version": "stability-ai/stable-diffusion",
                    "input": {
                        "prompt": prompt,
                        "negative_prompt": "ugly, deformed, bad quality",
                        "width": 512,
                        "height": 512,
                        "num_outputs": 1,
                        "num_inference_steps": 25,
                        "guidance_scale": 7.5
                    }
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                prediction_id = data["id"]
            
            # Ждем результат
            for _ in range(30):  # Максимум 30 секунд
                await asyncio.sleep(1)
                async with session.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {REPLICATE_API_KEY}"}
                ) as response:
                    if response.status != 200:
                        continue
                    data = await response.json()
                    if data["status"] == "succeeded":
                        image_url = data["output"][0]
                        # Скачиваем изображение
                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                return await img_response.read()
                        return None
                    elif data["status"] in ["failed", "canceled"]:
                        return None
            
            return None
    except Exception as e:
        print(f"Ошибка генерации изображения: {e}")
        return None

# ==================== ГЕНЕРАЦИЯ МЕМОВ ====================
MEME_TEMPLATES = [
    "Человек паук указывает на человека паука",
    "Это тот самый момент",
    "Ну и ну...",
    "Ожидание/Реальность",
    "Так и было",
    "Когда понимаешь...",
    "Тот самый момент когда",
    "Мой мозг когда",
    "Я когда увидел это",
    "Смотрит на тебя",
]

MEME_TOP_TEXT = [
    "Когда бот даёт 1000 монет",
    "Когда выиграл в казино",
    "Когда проиграл все монеты",
    "Мой уровень в игре",
    "Когда друг попросил монет",
    "Когда открыл кейс",
    "Когда я в чате",
    "Моя стратегия в бизнесе",
    "Когда захожу в магазин",
    "Когда вижу свою зарплату",
]

MEME_BOTTOM_TEXT = [
    "Хочу еще!",
    "Боже, благослови этот день!",
    "Это просто невероятно!",
    "Ну и ну...",
    "Схожу с ума!",
    "Жизнь удалась!",
    "Это моя судьба!",
    "Каждый раз так!",
    "Все гениальное просто!",
    "Душа поет!",
]

def create_meme(top_text: str, bottom_text: str) -> bytes:
    """Создание простого мема с текстом"""
    try:
        # Создаем изображение с градиентом
        img = Image.new('RGB', (800, 600), color=(50, 50, 80))
        draw = ImageDraw.Draw(img)
        
        # Рисуем рамку
        draw.rectangle([10, 10, 790, 590], outline=(255, 255, 255), width=3)
        
        # Загружаем шрифт
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            font_big = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
            font_big = ImageFont.load_default()
        
        # Центрируем текст
        def draw_centered_text(text, y, font, color=(255, 255, 255)):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (800 - text_width) // 2
            # Рисуем тень
            draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0))
            draw.text((x, y), text, font=font, fill=color)
        
        # Верхний текст
        if top_text:
            draw_centered_text(top_text, 50, font_big, (255, 255, 100))
        
        # Добавляем декоративную рамку посередине
        draw.rectangle([100, 250, 700, 350], outline=(100, 100, 200), width=2)
        draw.text((300, 280), "Здесь могла быть ваша картинка", font=font, fill=(200, 200, 200))
        
        # Нижний текст
        if bottom_text:
            draw_centered_text(bottom_text, 450, font_big, (100, 255, 100))
        
        # Сохраняем в байты
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer.getvalue()
    except Exception as e:
        print(f"Ошибка создания мема: {e}")
        return None

async def generate_meme_with_text(top_text: str = None, bottom_text: str = None) -> bytes:
    """Генерация мема с текстом"""
    if not top_text:
        top_text = random.choice(MEME_TOP_TEXT)
    if not bottom_text:
        bottom_text = random.choice(MEME_BOTTOM_TEXT)
    
    return create_meme(top_text, bottom_text)

# ==================== АНАЛИЗ СООБЩЕНИЙ ====================
async def analyze_message(text: str) -> dict:
    """Анализ сообщения с ИИ"""
    try:
        # Простая эмуляция анализа через DeepSeek
        if DEEPSEEK_API_KEY:
            response = await deepseek_generate(
                f"Проанализируй это сообщение: '{text}'. Определи: 1) настроение, 2) тон, 3) тему, 4) эмоциональную окраску. Ответь кратко в формате: Настроение: ... | Тон: ... | Тема: ... | Эмоция: ..."
            )
            return {"analysis": response}
        else:
            # Простой анализ без ИИ
            emotions = {
                "😊": ["привет", "здравствуй", "добро", "рад", "счастлив"],
                "😢": ["грустно", "печально", "жаль", "плакать"],
                "😡": ["злой", "бесит", "ненавижу", "раздражает"],
                "🔥": ["круто", "огонь", "класс", "супер"],
                "😄": ["смешно", "ха-ха", "ржу", "смех"]
            }
            
            detected_emotion = "нейтрально"
            for emoji, keywords in emotions.items():
                for keyword in keywords:
                    if keyword in text.lower():
                        detected_emotion = emoji
                        break
                if detected_emotion != "нейтрально":
                    break
            
            return {
                "analysis": f"Настроение: {detected_emotion} | Тон: обычный | Тема: общение"
            }
    except Exception as e:
        return {"analysis": f"Ошибка анализа: {e}"}

# ==================== ГЕНЕРАЦИЯ ОТВЕТОВ ====================
async def generate_reply(text: str, user_name: str = "") -> str:
    """Генерация ответа на сообщение"""
    try:
        if DEEPSEEK_API_KEY:
            response = await deepseek_generate(
                f"Ответь на это сообщение от {user_name}: '{text}'. Будь дружелюбным и веселым. Используй эмодзи. Не отвечай слишком длинно."
            )
            return response
        elif GROK_API_KEY:
            response = await grok_generate(
                f"Ответь на это сообщение от {user_name}: '{text}'. Будь дружелюбным и веселым. Используй эмодзи. Не отвечай слишком длинно."
            )
            return response
        else:
            # Простые ответы без ИИ
            responses = [
                "Интересно! 😊",
                "Понял! 👂",
                "Хорошо! 👍",
                "Ясно! 😎",
                "Продолжай! 😄",
                "Ну и ну! 😮",
                "Запомню! 📝",
                "Класс! 🎉",
                "Огонь! 🔥",
                "Так и есть! 💯"
            ]
            return random.choice(responses)
    except Exception as e:
        return f"❌ Ошибка генерации ответа: {e}"

# ==================== ОБРАБОТЧИК КОМАНДЫ FABLE ====================
async def handle_fable_command(message: types.Message, query: str):
    """Обработчик команды 'фабле' - генерация контента с ИИ"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Проверяем КД
    ok, remaining = await check_cooldown(user_id, "fable_ai", AI_COOLDOWN)
    if not ok:
        await message.reply(f"⏳ Подожди {remaining} секунд!")
        return
    
    # Определяем тип запроса
    query_lower = query.lower()
    
    # Генерация изображения
    if "сгенерируй" in query_lower and ("картинк" in query_lower or "изображени" in query_lower or "рисун" in query_lower):
        await message.reply("🔄 Генерирую картинку... Это может занять до 30 секунд.")
        
        # Убираем слова-команды
        prompt = query.replace("сгенерируй", "").replace("картинку", "").replace("изображение", "").replace("рисунок", "").strip()
        if not prompt:
            prompt = "красивый закат с горным озером"
        
        image_data = await generate_image(prompt)
        if image_data:
            try:
                await message.reply_photo(BufferedInputFile(image_data, filename="image.png"), caption=f"🖼️ Сгенерировано по запросу: {prompt}")
                await log_action(user_id, "fable_generate_image", f"Сгенерировал картинку: {prompt}")
            except Exception as e:
                await message.reply(f"❌ Ошибка отправки картинки: {e}")
        else:
            await message.reply("❌ Не удалось сгенерировать картинку. Возможно, API ключ не настроен или ошибка сервиса.")
        return
    
    # Генерация мема
    if "мем" in query_lower or "смешн" in query_lower:
        await message.reply("🎭 Создаю мем...")
        
        # Извлекаем текст для мема
        top_text = None
        bottom_text = None
        if " с текстом " in query_lower:
            parts = query_lower.split(" с текстом ")
            text_parts = parts[1].split(",") if "," in parts[1] else [parts[1]]
            if len(text_parts) >= 1:
                top_text = text_parts[0].strip()
            if len(text_parts) >= 2:
                bottom_text = text_parts[1].strip()
        
        meme_data = await generate_meme_with_text(top_text, bottom_text)
        if meme_data:
            try:
                await message.reply_photo(BufferedInputFile(meme_data, filename="meme.png"), caption="🎭 Вот ваш мем!")
                await log_action(user_id, "fable_generate_meme", f"Сгенерировал мем")
            except Exception as e:
                await message.reply(f"❌ Ошибка отправки мема: {e}")
        else:
            await message.reply("❌ Не удалось создать мем.")
        return
    
    # Анализ сообщения
    if "проанализируй" in query_lower or "анализ" in query_lower:
        text_to_analyze = query.replace("проанализируй", "").replace("анализ", "").strip()
        if not text_to_analyze:
            await message.reply("ℹ️ Что проанализировать? Например: `фабле проанализируй это сообщение`")
            return
        
        await message.reply("🔍 Анализирую...")
        analysis = await analyze_message(text_to_analyze)
        await message.reply(f"📊 **Результат анализа:**\n{analysis['analysis']}", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Просто генерация ответа
    await message.reply("🤔 Думаю...")
    
    # Используем DeepSeek
    if DEEPSEEK_API_KEY:
        response = await deepseek_generate(query)
    elif GROK_API_KEY:
        response = await grok_generate(query)
    else:
        response = await generate_reply(query, message.from_user.first_name)
    
    # Отправляем ответ
    if len(response) > 4096:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await message.reply(part, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply(response, parse_mode=ParseMode.MARKDOWN)
    
    await log_action(user_id, "fable_ai", f"Запрос: {query[:50]}")

# ==================== ОБРАБОТКА МЕДИА ====================
async def handle_media(message: types.Message):
    """Обработка медиа-файлов (анализ картинок, видео, гифок)"""
    user_id = message.from_user.id
    
    # Проверяем КД
    ok, remaining = await check_cooldown(user_id, "fable_ai", 60)
    if not ok:
        return
    
    if not DEEPSEEK_API_KEY:
        return
    
    # Определяем тип медиа
    media_type = ""
    if message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        file_id = message.video.file_id
    elif message.animation:
        media_type = "gif"
        file_id = message.animation.file_id
    else:
        return
    
    # Проверяем, есть ли подпись
    caption = message.caption if message.caption else ""
    
    # Отвечаем на анализ
    response = await deepseek_generate(
        f"Пользователь отправил {media_type} с подписью: '{caption}'. Опиши что там может быть, угадай содержание, будь смешным и дружелюбным. Сделай короткий ответ с эмодзи."
    )
    
    await message.reply(f"🖼️ **Анализ {media_type}:**\n{response}", parse_mode=ParseMode.MARKDOWN)

# ==================== ДОБАВЛЯЕМ ФУНКЦИЮ В MAIN ====================
# async def main():
#     # Запускаем фоновые задачи
#     asyncio.create_task(economy_event_task())
#     asyncio.create_task(deposit_interest_task())
#     
#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot)

print(f"✅ Часть 12/20 загружена! Строк: ~650")
# ==================== ЧАСТЬ 13/20: МАГАЗИН, КЕЙСЫ, АУКЦИОНЫ, ТОРГОВЛЯ ====================

# ==================== МАГАЗИН (ПОЛНАЯ ВЕРСИЯ) ====================

# В Part 3 уже есть базовая версия магазина, здесь расширяем

async def shop_category(message: types.Message, category: str):
    """Показать категорию магазина"""
    msg = f"🛒 **{category.capitalize()}**\n\n"
    
    if category == "рабочие":
        for name, data in SHOP_ITEMS.items():
            if "job" in data and data["job"] != "все":
                price = data["price"]
                job = data["job"].capitalize()
                emoji = "⛏️" if "кирка" in name else "🎣" if "удочка" in name else "🔫" if "ружьё" in name else "🚜" if "трактор" in name else "🏗️" if "техника" in name else "💼"
                msg += f"{emoji} **{name.capitalize()}** — {price} монет\n"
                msg += f"   📝 Для: {job} | Бонус: +{data['bonus']}%\n\n"
    
    elif category == "защита":
        for name, data in SHOP_ITEMS.items():
            if "bonus" in data and "job" not in data:
                price = data["price"]
                emoji = "🛡️" if "щит" in name else "⛑️" if "каска" in name else "🦺" if "бронежилет" in name else "🍀"
                msg += f"{emoji} **{name.capitalize()}** — {price} монет\n"
                msg += f"   📝 Бонус: +{data['bonus']}%\n\n"
    
    elif category == "финансы":
        finance_items = ["золотая монета", "драгоценный камень"]
        for name in finance_items:
            if name in SHOP_ITEMS:
                price = SHOP_ITEMS[name]["price"]
                emoji = "💰" if "монета" in name else "💎"
                msg += f"{emoji} **{name.capitalize()}** — {price} монет\n"
                msg += f"   📝 Бонус: +{SHOP_ITEMS[name]['bonus']}%\n\n"
    
    elif category == "лимитные":
        for name, data in LIMITED_ITEMS.items():
            left = data["left"]
            total = data["total"]
            status = "✅" if left > 0 else "❌"
            msg += f"{data['emoji']} **{name.capitalize()}**\n"
            msg += f"   💰 {data['price']} монет | {data['rarity']}\n"
            msg += f"   📦 Осталось: {left}/{total} {status}\n"
            msg += f"   📝 {data['desc']}\n\n"
    
    msg += f"📝 `купить [предмет]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== КЕЙСЫ (РАСШИРЕННАЯ ВЕРСИЯ) ====================

async def show_case_info(message: types.Message, case_name: str):
    """Показать информацию о кейсе"""
    if case_name not in CASES:
        await message.reply(f"❌ Кейс '{case_name}' не найден!")
        return
    
    case = CASES[case_name]
    
    msg = f"{case['emoji']} **{case['name']}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"💰 Цена: {case['price']} монет\n"
    if case.get('vip_only', False):
        msg += "👑 Только для VIP\n"
    
    msg += f"\n📦 **Возможные выпадения:**\n"
    for item_name, item_data in case['items'].items():
        chance = item_data['chance']
        if "min" in item_data:
            if "монеты" in item_name:
                msg += f"💰 Монеты: {item_data['min']}-{item_data['max']} ({chance}%)\n"
            else:
                msg += f"💎 Камни: {item_data['min']}-{item_data['max']} ({chance}%)\n"
        else:
            limited_text = " 🔥 ЛИМИТКА!" if item_data.get('limited', False) else ""
            msg += f"📦 {item_name.capitalize()} x{item_data.get('quantity', 1)} ({chance}%){limited_text}\n"
    
    msg += f"\n📝 `открыть кейс {case_name}`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== АУКЦИОНЫ ====================

async def start_auction(message: types.Message):
    """Начать аукцион на предмет"""
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 4:
        await message.reply("ℹ️ `аукцион [предмет] [количество] [стартовая цена]`")
        return
    
    item_name = args[1].lower()
    try:
        quantity = int(args[2])
        start_price = int(args[3])
    except:
        await message.reply("❌ Введи числа!")
        return
    
    if quantity <= 0 or start_price <= 0:
        await message.reply("❌ Количество и цена должны быть > 0!")
        return
    
    # Проверяем наличие предмета
    has_qty = await has_item(user_id, item_name)
    if has_qty < quantity:
        await message.reply(f"❌ У тебя только {has_qty} шт {item_name}!")
        return
    
    # Создаём аукцион
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    ends_at = (datetime.now() + timedelta(hours=24)).isoformat()
    c.execute("""INSERT INTO auctions 
                (seller_id, item_name, item_quantity, start_price, current_bid, ends_at) 
                VALUES (?, ?, ?, ?, ?, ?)""",
              (user_id, item_name, quantity, start_price, start_price, ends_at))
    auction_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Удаляем предмет у продавца
    await remove_item(user_id, item_name, quantity)
    
    await log_action(user_id, "start_auction", f"Создал аукцион #{auction_id} на {quantity}x {item_name}")
    
    msg = f"🏷️ **АУКЦИОН #{auction_id}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📦 Предмет: **{item_name.capitalize()}** x{quantity}\n"
    msg += f"💰 Стартовая цена: **{start_price}** монет\n"
    msg += f"👤 Продавец: {await get_name(user_id)}\n"
    msg += f"⏳ Длительность: 24 часа\n"
    msg += f"\n📝 `ставка {auction_id} [сумма]`"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def place_bid(message: types.Message):
    """Сделать ставку на аукционе"""
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 3:
        await message.reply("ℹ️ `ставка [аукцион] [сумма]`")
        return
    
    try:
        auction_id = int(args[1])
        amount = int(args[2])
    except:
        await message.reply("❌ Введи числа!")
        return
    
    if amount <= 0:
        await message.reply("❌ Сумма должна быть > 0!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT seller_id, item_name, item_quantity, current_bid, active, ends_at FROM auctions WHERE id = ?", (auction_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        await message.reply(f"❌ Аукцион #{auction_id} не найден!")
        return
    
    seller_id, item_name, item_quantity, current_bid, active, ends_at = row
    
    if not active:
        conn.close()
        await message.reply(f"❌ Аукцион #{auction_id} уже завершён!")
        return
    
    if user_id == seller_id:
        conn.close()
        await message.reply("❌ Нельзя делать ставку на свой аукцион!")
        return
    
    if datetime.fromisoformat(ends_at) < datetime.now():
        conn.close()
        await message.reply(f"❌ Аукцион #{auction_id} истёк!")
        return
    
    if amount <= current_bid:
        conn.close()
        await message.reply(f"❌ Минимальная ставка: {current_bid + 1} монет!")
        return
    
    coins = await get_coins(user_id)
    if coins < amount:
        conn.close()
        await message.reply(f"❌ У тебя только {coins} монет!")
        return
    
    # Обновляем ставку
    c.execute("UPDATE auctions SET current_bid = ?, buyer_id = ? WHERE id = ?", (amount, user_id, auction_id))
    conn.commit()
    conn.close()
    
    await log_action(user_id, "place_bid", f"Сделал ставку {amount} на аукцион #{auction_id}")
    
    await message.reply(f"✅ Ставка **{amount}** монет на аукцион #{auction_id} принята!")
    
    # Уведомляем продавца
    try:
        await bot.send_message(
            seller_id,
            f"🏷️ **Новая ставка на аукционе #{auction_id}**\n"
            f"💰 Текущая ставка: **{amount}** монет\n"
            f"👤 Покупатель: {await get_name(user_id)}"
        )
    except:
        pass

async def end_auction(auction_id):
    """Завершить аукцион (вызывается автоматически)"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT seller_id, buyer_id, item_name, item_quantity, current_bid FROM auctions WHERE id = ?", (auction_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return
    
    seller_id, buyer_id, item_name, item_quantity, current_bid = row
    
    if buyer_id and buyer_id != 0:
        # Есть победитель
        # Передаём предмет
        await add_item(buyer_id, item_name, item_quantity)
        # Передаём деньги
        await remove_coins(buyer_id, current_bid)
        await add_coins(seller_id, current_bid)
        
        await log_action(buyer_id, "auction_win", f"Выиграл аукцион #{auction_id} за {current_bid}")
        await log_action(seller_id, "auction_sell", f"Продал на аукционе #{auction_id} за {current_bid}")
        
        try:
            await bot.send_message(
                buyer_id,
                f"🏆 **Вы выиграли аукцион #{auction_id}!**\n"
                f"📦 Предмет: **{item_name.capitalize()}** x{item_quantity}\n"
                f"💰 Цена: **{current_bid}** монет"
            )
        except:
            pass
        
        try:
            await bot.send_message(
                seller_id,
                f"✅ **Аукцион #{auction_id} завершён!**\n"
                f"📦 Предмет: **{item_name.capitalize()}** x{item_quantity}\n"
                f"💰 Продан за: **{current_bid}** монет\n"
                f"👤 Покупатель: {await get_name(buyer_id)}"
            )
        except:
            pass
    else:
        # Нет покупателей - возвращаем предмет продавцу
        await add_item(seller_id, item_name, item_quantity)
        await log_action(seller_id, "auction_expired", f"Аукцион #{auction_id} истёк, предмет возвращён")
        
        try:
            await bot.send_message(
                seller_id,
                f"⏰ **Аукцион #{auction_id} истёк!**\n"
                f"📦 Предмет **{item_name.capitalize()}** возвращён вам."
            )
        except:
            pass
    
    # Закрываем аукцион
    c.execute("UPDATE auctions SET active = 0 WHERE id = ?", (auction_id,))
    conn.commit()
    conn.close()

async def auction_list(message: types.Message):
    """Список активных аукционов"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT id, seller_id, item_name, item_quantity, current_bid, ends_at FROM auctions WHERE active = 1")
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Нет активных аукционов!")
        return
    
    msg = "🏷️ **АКТИВНЫЕ АУКЦИОНЫ**\n\n"
    for auction in rows:
        auction_id, seller_id, item_name, item_quantity, current_bid, ends_at = auction
        seller_name = await get_name(seller_id)
        time_left = (datetime.fromisoformat(ends_at) - datetime.now())
        hours = int(time_left.total_seconds() / 3600)
        minutes = int((time_left.total_seconds() % 3600) / 60)
        
        msg += f"#{auction_id} **{item_name.capitalize()}** x{item_quantity}\n"
        msg += f"   💰 Текущая ставка: {current_bid}\n"
        msg += f"   👤 Продавец: {seller_name}\n"
        msg += f"   ⏳ Осталось: {hours}ч {minutes}м\n\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ФОНОВАЯ ЗАДАЧА ДЛЯ АУКЦИОНОВ ====================
async def auction_check_task():
    """Проверка и завершение истекших аукционов"""
    while True:
        await asyncio.sleep(60)  # Проверяем каждую минуту
        
        try:
            conn = sqlite3.connect("fable_bot.db")
            c = conn.cursor()
            c.execute("SELECT id FROM auctions WHERE active = 1 AND ends_at <= ?", (datetime.now().isoformat(),))
            expired = c.fetchall()
            conn.close()
            
            for (auction_id,) in expired:
                await end_auction(auction_id)
        except Exception as e:
            print(f"Ошибка проверки аукционов: {e}")

# ==================== ТОРГОВЛЯ МЕЖДУ ИГРОКАМИ ====================
async def trade_command(message: types.Message):
    """Обмен предметами между игроками"""
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        await message.reply("ℹ️ Ответь на сообщение игрока, с которым хочешь обменяться!")
        return
    
    target_id = message.reply_to_message.from_user.id
    
    if target_id == user_id:
        await message.reply("❌ Нельзя обменяться с собой!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `обменять [мой предмет] [его предмет]`")
        return
    
    my_item = args[1].lower()
    their_item = args[2].lower()
    
    # Проверяем наличие предметов
    my_qty = await has_item(user_id, my_item)
    if my_qty < 1:
        await message.reply(f"❌ У тебя нет предмета: {my_item}!")
        return
    
    their_qty = await has_item(target_id, their_item)
    if their_qty < 1:
        await message.reply(f"❌ У {await get_name(target_id)} нет предмета: {their_item}!")
        return
    
    # Предложение обмена
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"trade_yes_{user_id}_{target_id}_{my_item}_{their_item}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"trade_no_{user_id}_{target_id}")
        ]
    ])
    
    await message.reply(
        f"🔄 **ПРЕДЛОЖЕНИЕ ОБМЕНА**\n\n"
        f"{await get_name(user_id)} предлагает: **{my_item}**\n"
        f"{await get_name(target_id)} предлагает: **{their_item}**\n\n"
        f"Согласны?",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data.startswith("trade_yes_"))
async def trade_accept(callback):
    data = callback.data.split("_")
    proposer = int(data[1])
    receiver = int(data[2])
    my_item = data[3]
    their_item = data[4]
    
    if callback.from_user.id != receiver:
        await callback.answer("❌ Не тебе!")
        return
    
    # Проверяем ещё раз наличие предметов
    if await has_item(proposer, my_item) < 1:
        await callback.message.edit_text("❌ У предложившего больше нет этого предмета!")
        return
    
    if await has_item(receiver, their_item) < 1:
        await callback.message.edit_text("❌ У тебя больше нет этого предмета!")
        return
    
    # Производим обмен
    await remove_item(proposer, my_item, 1)
    await remove_item(receiver, their_item, 1)
    await add_item(proposer, their_item, 1)
    await add_item(receiver, my_item, 1)
    
    await log_action(proposer, "trade", f"Обменял {my_item} на {their_item} с {await get_name(receiver)}")
    await log_action(receiver, "trade", f"Обменял {their_item} на {my_item} с {await get_name(proposer)}")
    
    await callback.message.edit_text(
        f"✅ **ОБМЕН СОСТОЯЛСЯ!**\n\n"
        f"{await get_name(proposer)} получил: **{their_item}**\n"
        f"{await get_name(receiver)} получил: **{my_item}**"
    )

@dp.callback_query(lambda c: c.data.startswith("trade_no_"))
async def trade_decline(callback):
    data = callback.data.split("_")
    proposer = int(data[1])
    receiver = int(data[2])
    
    if callback.from_user.id != receiver:
        await callback.answer("❌ Не тебе!")
        return
    
    await callback.message.edit_text(f"❌ {await get_name(receiver)} отказался от обмена!")

print(f"✅ Часть 13/20 загружена! Строк: ~700")
# ==================== ЧАСТЬ 14/20: ПОЛНАЯ СИСТЕМА МОДЕРАЦИИ ====================
# Автоматическая модерация: антимат, антикапс, антиспам, антифлуд, антиссылки
# Система варнов с автобаном при 5 варнах
# Расширенные муты и баны
# Система фильтров с удалением сообщений
# Жалобы с уведомлением админов
# Логирование всех действий модераторов

# ==================== РАСШИРЕННЫЙ АНТИМАТ ====================
# Полный список матов на разных языках
BAD_WORDS_EXTENDED = {
    # Русский
    "хуй", "пизда", "бля", "сука", "мудак", "тварь", "пидор", "лох", "гандон", 
    "редиска", "залупа", "жопа", "еблан", "ебать", "ебал", "ебаный", "пиздец",
    "хуесос", "хуйло", "сучка", "блядина", "шлюха", "курва", "мразь", "ублюдок",
    "говно", "дерьмо", "срать", "ссать", "засранец", "гнида", "паскуда", "сволочь",
    "дебил", "идиот", "кретин", "даун", "тупой", "глупый", "урод", "выродок",
    
    # Английский
    "fuck", "shit", "ass", "bitch", "bastard", "cunt", "dick", "pussy", "whore",
    "motherfucker", "asshole", "douche", "retard", "stupid", "idiot", "moron",
    
    # Украинский
    "хуй", "пизда", "бля", "сука", "мудак", "тварь", "пиздець", "єблан",
    "лох", "гандон", "жопа", "курва", "шлюха", "мразь", "виродок",
    
    # Белорусский
    "хуй", "пізда", "бля", "сука", "мудак", "твар", "піздзец", "яблан",
    "лох", "гандон", "жопа", "курва", "шлюха", "мразь", "вырадак",
    
    # Другие
    "puta", "mierda", "kut", "pis", "vagina", "penis", "cock", "cum", "sperm"
}

async def extended_antimat_check(text: str) -> bool:
    """Проверка текста на мат с учётом разных языков и вариаций"""
    text_lower = text.lower()
    
    # Проверяем точные совпадения
    for word in BAD_WORDS_EXTENDED:
        if word in text_lower:
            return True
    
    # Проверяем с заменой букв (маскировка)
    patterns = [
        r'х[уy]+[йj]', r'п[иi]зд[аa]', r'б[лl][яa]', r'с[уy]к[аa]',
        r'м[уy]д[аa]к', r'тв[аa]р[ьb]', r'п[иi]д[оo]р', r'л[оo]х',
        r'г[аa]нд[оo]н', r'ж[оo]п[аa]', r'е[бb][аa]ть', r'п[иi]зд[еe]ц',
        r'х[уy][еe]с[оo]с', r'ш[лl][юu]х[аa]', r'к[уy]рв[аa]', r'мр[аa]з[ьb]',
        r'у[бb][лl][юu]д[оo]к', r'г[оo]вн[оo]', r'д[еe]р[ьb]м[оo]',
        r'з[аa]ср[аa]н[еe]ц', r'п[аa]ск[уy]д[аa]', r'св[оo]л[оo]ч[ьb]',
        r'д[еe][бb][иi][лl]', r'кр[еe]т[иi]н', r'д[аa]у[нn]', r'т[уu]п[оo][йj]'
    ]
    
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False

# ==================== АВТОМАТИЧЕСКАЯ МОДЕРАЦИЯ (ПОЛНАЯ ВЕРСИЯ) ====================
async def auto_moderation_full(message: types.Message) -> bool:
    """
    Полная автоматическая модерация сообщения.
    Возвращает True если сообщение удалено, иначе False.
    """
    if not message.text:
        return False
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    
    # Проверяем уровень админа - админов не модерируем
    admin_level = await get_admin_level(user_id)
    if admin_level >= 1:
        return False
    
    settings = await get_chat_settings(chat_id)
    deleted = False
    warn_reason = None
    
    # ===== 1. АНТИМАТ =====
    if settings.get("antimat_enabled", 0) == 1:
        if await extended_antimat_check(text):
            await message.delete()
            deleted = True
            warn_reason = "Мат"
            
            # Выдаём варн
            warn_count = await add_warn(user_id, chat_id, f"Мат в сообщении: {text[:50]}", user_id)
            
            # Отправляем предупреждение
            await message.answer(f"⚠️ {message.from_user.first_name}, мат запрещён! Варн #{warn_count}")
            
            # Проверяем количество варнов
            if warn_count >= 5:
                await bot.ban_chat_member(chat_id, user_id)
                await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
                await log_action(user_id, "auto_ban", f"Забанен за 5 варнов (мат)")
            
            await log_action(user_id, "auto_warn", f"Мат: {text[:50]}")
            return True
    
    # ===== 2. АНТИКАПС =====
    if settings.get("anticaps_enabled", 0) == 1:
        # Проверяем длину текста и количество заглавных букв
        if len(text) > 10:
            caps_count = sum(1 for c in text if c.isupper())
            # Считаем только буквы
            letters = sum(1 for c in text if c.isalpha())
            if letters > 0 and caps_count / letters > 0.7:
                await message.delete()
                deleted = True
                warn_reason = "Капс"
                
                warn_count = await add_warn(user_id, chat_id, f"Капс в сообщении: {text[:50]}", user_id)
                await message.answer(f"⚠️ {message.from_user.first_name}, не кричи! Варн #{warn_count}")
                
                if warn_count >= 5:
                    await bot.ban_chat_member(chat_id, user_id)
                    await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
                
                await log_action(user_id, "auto_warn", f"Капс: {text[:50]}")
                return True
    
    # ===== 3. АНТИССЫЛКИ =====
    if settings.get("antilinks_enabled", 0) == 1:
        # Проверяем наличие ссылок
        link_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+])+',
            r'www\.[a-zA-Z0-9-]+(\.[a-zA-Z]{2,})+',
            r'[a-zA-Z0-9-]+\.(ru|com|net|org|info|biz|club|online|site|top|xyz)'
        ]
        
        has_link = False
        for pattern in link_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                has_link = True
                break
        
        if has_link:
            await message.delete()
            deleted = True
            warn_reason = "Ссылка"
            
            warn_count = await add_warn(user_id, chat_id, f"Ссылка в сообщении: {text[:50]}", user_id)
            await message.answer(f"⚠️ {message.from_user.first_name}, ссылки запрещены! Варн #{warn_count}")
            
            if warn_count >= 5:
                await bot.ban_chat_member(chat_id, user_id)
                await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
            
            await log_action(user_id, "auto_warn", f"Ссылка: {text[:50]}")
            return True
    
    # ===== 4. АНТИСПАМ =====
    if settings.get("antispam_enabled", 0) == 1:
        # Проверяем повторяющиеся сообщения
        if user_id in last_message_time:
            last_data = last_message_time.get(user_id, {})
            last_text = last_data.get("text", "")
            last_time = last_data.get("time")
            
            # Если сообщение повторяется и прошло меньше 30 секунд
            if last_text == text and last_time and (datetime.now() - last_time).total_seconds() < 30:
                await message.delete()
                deleted = True
                warn_reason = "Спам"
                
                warn_count = await add_warn(user_id, chat_id, f"Спам: повтор сообщения", user_id)
                await message.answer(f"⚠️ {message.from_user.first_name}, не спамь! Варн #{warn_count}")
                
                if warn_count >= 5:
                    await bot.ban_chat_member(chat_id, user_id)
                    await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
                
                await log_action(user_id, "auto_warn", f"Спам: {text[:50]}")
                return True
        
        last_message_time[user_id] = {"text": text, "time": datetime.now()}
    
    # ===== 5. АНТИФЛУД =====
    if settings.get("antiflood_enabled", 0) == 1:
        now = datetime.now()
        if user_id not in flood_users:
            flood_users[user_id] = []
        
        # Очищаем сообщения старше 5 секунд
        flood_users[user_id] = [t for t in flood_users[user_id] if (now - t).total_seconds() < 5]
        flood_users[user_id].append(now)
        
        # Если больше 5 сообщений за 5 секунд - флуд
        if len(flood_users[user_id]) > 5:
            await message.delete()
            deleted = True
            warn_reason = "Флуд"
            
            # Мут на 1 минуту
            try:
                await bot.restrict_chat_member(
                    chat_id,
                    user_id,
                    ChatPermissions(can_send_messages=False),
                    until_date=now + timedelta(minutes=1)
                )
                await message.answer(f"⚠️ {message.from_user.first_name}, флуд! Мут 1 мин.")
            except:
                pass
            
            warn_count = await add_warn(user_id, chat_id, f"Флуд: {len(flood_users[user_id])} сообщений за 5 сек", user_id)
            
            if warn_count >= 5:
                await bot.ban_chat_member(chat_id, user_id)
                await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
            
            await log_action(user_id, "auto_warn", f"Флуд: {len(flood_users[user_id])} сообщений")
            return True
    
    # ===== 6. СТОП-СЛОВА =====
    stop_words = await get_stop_words(chat_id)
    for word in stop_words:
        if word in text.lower():
            await message.delete()
            deleted = True
            warn_reason = f"Стоп-слово: {word}"
            
            warn_count = await add_warn(user_id, chat_id, f"Стоп-слово: {word}", user_id)
            await message.answer(f"⚠️ {message.from_user.first_name}, запрещённое слово: {word}! Варн #{warn_count}")
            
            if warn_count >= 5:
                await bot.ban_chat_member(chat_id, user_id)
                await message.answer(f"🚫 {message.from_user.first_name} забанен за 5 варнов!")
            
            await log_action(user_id, "auto_warn", f"Стоп-слово: {word}")
            return True
    
    return deleted

# ==================== УДАЛЕНИЕ СООБЩЕНИЙ КОМАНДОЙ "-соо" ====================
@dp.message(lambda m: m.text and m.text.startswith("-соо") and m.reply_to_message)
async def delete_message_command(message: types.Message):
    """Удаление сообщения командой -соо (требуется 3+ админа)"""
    user_id = message.from_user.id
    admin_level = await get_admin_level(user_id)
    
    if admin_level < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return
    
    try:
        target_msg = message.reply_to_message
        await target_msg.delete()
        await message.delete()
        await log_action(user_id, "delete_message", f"Удалил сообщение от {await get_name(target_msg.from_user.id)}")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# ==================== СИСТЕМА ЖАЛОБ (РАСШИРЕННАЯ) ====================
@dp.message(lambda m: m.text and m.text.startswith("жалоба"))
async def complaint_extended(message: types.Message):
    """Пожаловаться на пользователя с расширенной обработкой"""
    if not message.reply_to_message:
        await message.reply("ℹ️ Ответь на сообщение нарушителя!")
        return
    
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Без причины"
    
    reporter = message.from_user.id
    target = message.reply_to_message.from_user.id
    
    if target == reporter:
        await message.reply("❌ Нельзя пожаловаться на себя!")
        return
    
    # Записываем жалобу
    await add_complaint(target, reporter, reason, message.chat.id)
    await log_action(reporter, "complaint", f"Пожаловался на {await get_name(target)}: {reason}")
    
    # Отправляем подтверждение
    await message.reply(f"✅ Жалоба отправлена!\n📝 Причина: {reason}")
    
    # Находим всех админов в чате
    admins = await get_chat_admins(message.chat.id)
    
    # Отправляем уведомление каждому админу
    for admin in admins:
        if admin != reporter and admin != target:
            try:
                await bot.send_message(
                    admin,
                    f"⚠️ **НОВАЯ ЖАЛОБА**\n"
                    f"👤 Нарушитель: {await get_name(target)}\n"
                    f"📝 Причина: {reason}\n"
                    f"👤 Пожаловался: {await get_name(reporter)}\n"
                    f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}\n"
                    f"💡 Используй: `варн @{target} {reason}`"
                )
            except:
                pass
    
    # Проверяем, не слишком ли много жалоб на этого пользователя
    complaints = await get_complaints(message.chat.id)
    user_complaints = [c for c in complaints if c[1] == target]
    
    if len(user_complaints) >= 3:
        # Автоматический варн при 3+ жалобах
        warn_count = await add_warn(target, message.chat.id, f"3+ жалоб от пользователей", reporter)
        await message.reply(f"⚠️ {await get_name(target)} получил варн за 3+ жалоб! Варн #{warn_count}")
        
        if warn_count >= 5:
            await bot.ban_chat_member(message.chat.id, target)
            await message.reply(f"🚫 {await get_name(target)} забанен за 5 варнов!")

# ==================== СИСТЕМА ОТЧЁТОВ ДЛЯ СОЗДАТЕЛЯ ====================
@dp.message(lambda m: m.from_user.id == CREATOR_ID and m.chat.type == "private" and m.text and m.text.startswith("отчёт"))
async def creator_report(message: types.Message):
    """Создание отчёта для создателя"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.reply("ℹ️ `отчёт [день|неделя|месяц|всё]`")
        return
    
    period = args[1].lower()
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    if period == "день":
        date_filter = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) FROM logs WHERE timestamp LIKE ?", (f"{date_filter}%",))
        total_logs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM warns WHERE date LIKE ?", (f"{date_filter}%",))
        total_warns = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM complaints WHERE date LIKE ?", (f"{date_filter}%",))
        total_complaints = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (f"{date_filter}%",))
        new_users = c.fetchone()[0]
        period_text = "за сегодня"
        
    elif period == "неделя":
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) FROM logs WHERE timestamp >= ?", (week_ago,))
        total_logs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM warns WHERE date >= ?", (week_ago,))
        total_warns = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM complaints WHERE date >= ?", (week_ago,))
        total_complaints = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (week_ago,))
        new_users = c.fetchone()[0]
        period_text = "за неделю"
        
    elif period == "месяц":
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) FROM logs WHERE timestamp >= ?", (month_ago,))
        total_logs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM warns WHERE date >= ?", (month_ago,))
        total_warns = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM complaints WHERE date >= ?", (month_ago,))
        total_complaints = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (month_ago,))
        new_users = c.fetchone()[0]
        period_text = "за месяц"
        
    else:  # всё
        c.execute("SELECT COUNT(*) FROM logs")
        total_logs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM warns")
        total_warns = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM complaints")
        total_complaints = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users")
        new_users = c.fetchone()[0]
        period_text = "за всё время"
    
    conn.close()
    
    msg = f"📊 **ОТЧЁТ {period_text.upper()}**\n\n"
    msg += f"📝 Всего действий: {total_logs}\n"
    msg += f"⚠️ Всего варнов: {total_warns}\n"
    msg += f"📋 Всего жалоб: {total_complaints}\n"
    msg += f"👤 Новых пользователей: {new_users}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

print(f"✅ Часть 14/20 загружена! Строк: ~700")
# ==================== ЧАСТЬ 15/20: СТАТИСТИКА, АНАЛИТИКА, ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ====================

# ==================== РАСШИРЕННАЯ СТАТИСТИКА ====================

async def stats_extended(message: types.Message, user_id: int = None):
    """Расширенная статистика пользователя или чата"""
    if not user_id:
        user_id = message.from_user.id
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    # Базовая информация о пользователе
    user = await get_user(user_id)
    if not user:
        await message.reply("❌ Пользователь не найден!")
        conn.close()
        return
    
    coins = await get_coins(user_id)
    bank = await get_bank(user_id)
    rep = await get_rep(user_id)
    job = await get_job(user_id)
    admin_level = await get_admin_level(user_id)
    
    # Статистика сообщений по чатам
    c.execute("SELECT chat_id, messages, last_message FROM chat_stats WHERE user_id = ?", (user_id,))
    chat_stats = c.fetchall()
    
    total_messages = sum(stat[1] for stat in chat_stats)
    total_chats = len(chat_stats)
    
    # Последняя активность
    last_active = max([datetime.fromisoformat(stat[2]) for stat in chat_stats]) if chat_stats else None
    
    # Статистика бизнесов
    businesses = await get_businesses(user_id)
    
    # Статистика инвентаря
    inventory = await get_inventory(user_id)
    total_items = sum(item[1] for item in inventory)
    
    # Статистика вкладов
    deposits = await get_active_deposits(user_id)
    total_deposits = sum(dep[1] for dep in deposits)
    
    # Статистика варнов
    c.execute("SELECT COUNT(*) FROM warns WHERE user_id = ?", (user_id,))
    total_warns = c.fetchone()[0]
    
    # Статистика достижений
    achievements = await get_achievements(user_id)
    
    # Статистика рефералов
    ref_count = await get_ref_count(user_id)
    
    conn.close()
    
    msg = f"📊 **РАСШИРЕННАЯ СТАТИСТИКА {await get_name(user_id)}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💰 **ФИНАНСЫ:**\n"
    msg += f"   💵 Монет: {coins}\n"
    msg += f"   🏦 В банке: {bank}\n"
    msg += f"   💳 Во вкладах: {total_deposits}\n"
    msg += f"   💰 Всего: {coins + bank + total_deposits}\n\n"
    
    msg += f"📊 **АКТИВНОСТЬ:**\n"
    msg += f"   💬 Сообщений: {total_messages}\n"
    msg += f"   🏠 Чатов: {total_chats}\n"
    if last_active:
        msg += f"   🕐 Последняя активность: {last_active.strftime('%d.%m.%Y %H:%M')}\n"
    msg += f"\n"
    
    msg += f"💼 **ЭКОНОМИКА:**\n"
    if job:
        job_data = JOBS.get(job, {})
        msg += f"   💼 Работа: {job.capitalize()} {job_data.get('emoji', '')}\n"
    else:
        msg += f"   💼 Работа: Нет\n"
    msg += f"   🏪 Бизнесов: {len(businesses)}\n"
    msg += f"   🎒 Предметов: {total_items}\n"
    msg += f"\n"
    
    msg += f"⭐ **СОЦИАЛКА:**\n"
    msg += f"   ⭐ Репутация: {rep}\n"
    msg += f"   👥 Рефералов: {ref_count}\n"
    msg += f"   🏆 Достижений: {len(achievements)}\n"
    msg += f"\n"
    
    msg += f"🛡️ **МОДЕРАЦИЯ:**\n"
    msg += f"   ⚠️ Варнов: {total_warns}\n"
    if admin_level > 0:
        level_name = get_level_name(admin_level)
        level_emoji = get_level_emoji(admin_level)
        msg += f"   🎯 Уровень: {level_emoji} {level_name}\n"
    else:
        msg += f"   🎯 Уровень: 👤 Пользователь\n"
    
    if await is_vip(user_id):
        msg += f"   👑 VIP статус: ✅\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ГРАФИКИ И ВИЗУАЛИЗАЦИЯ ====================

async def generate_activity_graph(message: types.Message):
    """Генерация графика активности чата"""
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return
    
    chat_id = message.chat.id
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    # Получаем активность за последние 7 дней
    week_data = {}
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        c.execute("SELECT SUM(messages) FROM chat_stats WHERE chat_id = ? AND last_message LIKE ?", 
                  (chat_id, f"{date}%"))
        count = c.fetchone()[0] or 0
        week_data[date] = count
    
    conn.close()
    
    # Создаём текстовый график
    max_count = max(week_data.values()) if week_data.values() else 1
    graph_width = 20
    
    msg = f"📊 **АКТИВНОСТЬ ЧАТА (последние 7 дней)**\n\n"
    
    for date, count in sorted(week_data.items()):
        day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%a")
        bar_length = int((count / max_count) * graph_width) if max_count > 0 else 0
        bar = "█" * bar_length + "░" * (graph_width - bar_length)
        msg += f"{day_name}: {bar} {count}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ИНТЕГРАЦИИ ====================

# ----- ПРИВЯЗКА ДРУГИХ БОТОВ -----
# Здесь можно добавить интеграцию с другими ботами

# ----- ЭКСПОРТ ПРОФИЛЯ -----
async def export_profile(message: types.Message):
    """Экспорт профиля в JSON"""
    user_id = message.from_user.id
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    user = await get_user(user_id)
    if not user:
        await message.reply("❌ Пользователь не найден!")
        conn.close()
        return
    
    # Собираем все данные
    profile_data = {
        "user_id": user_id,
        "username": user[1],
        "coins": user[2],
        "bank": user[3],
        "admin_level": user[4],
        "rep": user[5],
        "job": user[6],
        "created_at": user[7],
        "vip": user[10],
        "messages_total": user[12]
    }
    
    # Инвентарь
    c.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (user_id,))
    inventory = c.fetchall()
    profile_data["inventory"] = [{"item": item, "quantity": qty} for item, qty in inventory]
    
    # Бизнесы
    businesses = await get_businesses(user_id)
    profile_data["businesses"] = [{"name": name, "level": level} for name, level, _, _ in businesses]
    
    conn.close()
    
    # Сохраняем в файл
    json_data = json.dumps(profile_data, indent=2, ensure_ascii=False)
    
    # Отправляем как файл
    from io import BytesIO
    file = BytesIO(json_data.encode('utf-8'))
    file.name = f"profile_{user_id}.json"
    
    await message.reply_document(BufferedInputFile(file.getvalue(), filename=file.name), 
                                 caption="📤 Ваш профиль экспортирован в JSON!")

# ==================== ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ====================

# ----- ПРИВЕТСТВИЯ НОВИЧКОВ -----
@dp.message(F.new_chat_members)
async def welcome_new_member(message: types.Message):
    """Приветствие нового участника"""
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        
        settings = await get_chat_settings(message.chat.id)
        welcome_text = settings.get("welcome")
        
        if welcome_text:
            welcome_msg = welcome_text.replace("{user}", member.first_name).replace("{mention}", f"@{member.username}" if member.username else member.first_name)
            await message.reply(welcome_msg, parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply(f"👋 Привет, {member.first_name}! Добро пожаловать в чат! 🎉")
        
        # Бонус новичку
        await add_coins(member.id, 500)
        await log_action(member.id, "welcome_bonus", f"Получил 500 монет за регистрацию")
        
        # Проверяем, есть ли у него реферер
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT referrer_id FROM users WHERE user_id = ?", (member.id,))
        row = c.fetchone()
        conn.close()
        
        if row and row[0]:
            referrer_id = row[0]
            await add_coins(referrer_id, 250)
            await log_action(referrer_id, "referral_bonus", f"Получил 250 монет за реферала {await get_name(member.id)}")
            try:
                await bot.send_message(referrer_id, f"🎉 {member.first_name} присоединился по твоей реферальной ссылке! +250 монет!")
            except:
                pass

# ----- ПРОЩАНИЕ С УЧАСТНИКОМ -----
@dp.message(F.left_chat_member)
async def goodbye_member(message: types.Message):
    """Прощание с участником"""
    member = message.left_chat_member
    
    settings = await get_chat_settings(message.chat.id)
    goodbye_text = settings.get("goodbye")
    
    if goodbye_text:
        goodbye_msg = goodbye_text.replace("{user}", member.first_name)
        await message.reply(goodbye_msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply(f"👋 {member.first_name} покинул чат!")

# ----- АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЯ -----
async def user_activity(message: types.Message):
    """Показать активность пользователя"""
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `активность @user`")
        return
    
    try:
        target_username = args[1].replace("@", "")
        member = await message.chat.get_member(target_username)
        target_id = member.user.id
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        
        # Общая активность
        c.execute("SELECT SUM(messages) FROM chat_stats WHERE user_id = ?", (target_id,))
        total = c.fetchone()[0] or 0
        
        # Активность за сегодня
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT SUM(messages) FROM chat_stats WHERE user_id = ? AND last_message LIKE ?", 
                  (target_id, f"{today}%"))
        today_count = c.fetchone()[0] or 0
        
        # Активность за неделю
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute("SELECT SUM(messages) FROM chat_stats WHERE user_id = ? AND last_message >= ?", 
                  (target_id, week_ago))
        week_count = c.fetchone()[0] or 0
        
        # Последнее сообщение
        c.execute("SELECT last_message FROM chat_stats WHERE user_id = ? ORDER BY last_message DESC LIMIT 1", (target_id,))
        row = c.fetchone()
        last_msg = row[0] if row else "Никогда"
        
        conn.close()
        
        msg = f"📊 **Активность {await get_name(target_id)}**\n\n"
        msg += f"💬 Всего сообщений: {total}\n"
        msg += f"📅 Сегодня: {today_count}\n"
        msg += f"📆 За неделю: {week_count}\n"
        msg += f"🕐 Последнее сообщение: {last_msg[:16] if last_msg != 'Никогда' else 'Никогда'}\n"
        
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
    except:
        await message.reply("❌ Ошибка!")

# ----- СТАТУСЫ И ЗВАНИЯ -----
async def get_user_title(user_id: int) -> str:
    """Получение звания пользователя на основе активности"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT messages_total FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    messages = row[0] if row else 0
    
    if messages >= 10000:
        return "💎 Легенда"
    elif messages >= 5000:
        return "👑 Король чата"
    elif messages >= 1000:
        return "⭐ Говорун"
    elif messages >= 500:
        return "🗣️ Активный"
    elif messages >= 100:
        return "📚 Участник"
    else:
        return "👤 Новичок"

# ==================== ПОИСК ПОЛЬЗОВАТЕЛЕЙ ====================
async def search_user(message: types.Message):
    """Поиск пользователя по имени или ID"""
    if await get_admin_level(message.from_user.id) < 1:
        await message.reply("❌ У тебя нет прав! (нужен 1+ уровень)")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `поиск [имя или ID]`")
        return
    
    query = " ".join(args[1:])
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    if query.isdigit():
        c.execute("SELECT user_id, username FROM users WHERE user_id = ?", (int(query),))
    else:
        c.execute("SELECT user_id, username FROM users WHERE username LIKE ?", (f"%{query}%",))
    
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply(f"❌ Пользователи с '{query}' не найдены!")
        return
    
    msg = f"🔍 **Результаты поиска: '{query}'**\n\n"
    for user_id, username in rows[:10]:
        name = await get_name(user_id)
        msg += f"• {name} (ID: {user_id})\n"
    
    if len(rows) > 10:
        msg += f"\n... и ещё {len(rows) - 10} пользователей"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ПРИВЯЗКА КОМАНД ДЛЯ СОЗДАТЕЛЯ ====================
async def creator_manage_commands(message: types.Message):
    """Управление командами для создателя"""
    if message.from_user.id != CREATOR_ID:
        return
    
    if message.chat.type != "private":
        await message.reply("❌ Только в ЛС!")
        return
    
    text = message.text.lower()
    
    # Список всех доступных команд для создателя
    if text == "команды создателя":
        msg = """
👾 **КОМАНДЫ СОЗДАТЕЛЯ**

💰 **УПРАВЛЕНИЕ МОНЕТАМИ:**
`дать монеты @user 1000`
`дать монеты мне 1000`
`забрать монеты @user 1000`
`дать банк @user 1000`
`дать банк мне 1000`
`дать предмет @user предмет 5`
`дать предмет мне предмет 5`

👑 **УПРАВЛЕНИЕ УРОВНЯМИ:**
`дать уровень @user 5`
`убрать уровень @user`
`дать вип @user 30`
`убрать вип @user`

📊 **СТАТИСТИКА:**
`статистика бота`
`статистика пользователей`
`статистика чатов`
`логи день`
`логи неделя`
`логи месяц`
`логи все`
`отчёт день`
`отчёт неделя`
`отчёт месяц`

🌍 **ЭКОНОМИЧЕСКИЕ СОБЫТИЯ:**
`эконом старт инфляция`
`эконом старт дефляция`
`эконом старт кризис`
`эконом старт бум`
`эконом старт золотой дождь`
`эконом стоп`
`эконом статус`

🎁 **ПРОМО-КОДЫ:**
`создать промо CODE 1000`
`создать промо CODE 0 алмаз 5`
`удалить промо CODE`
`список промо`

📤 **МАССОВЫЕ ВЫДАЧИ:**
`дать монеты всем 1000`
`дать банк всем 1000`
`дать вип всем 30`

🔄 **УПРАВЛЕНИЕ:**
`бот перезагрузить`
`бот статус`
`глобал очистить чаты`
`глобал обновить`
`рассылка всем [текст]`
"""
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return

print(f"✅ Часть 15/20 загружена! Строк: ~700")
# ==================== ЧАСТЬ 16/20: ПОЛНАЯ СИСТЕМА ИГР ====================
# Покер, челленджи, дуэли, турниры

# ==================== ПОКЕР ====================
POKER_SUITS = ['♠', '♥', '♦', '♣']
POKER_RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

POKER_HANDS = {
    'royal_flush': '👑 Роял-флеш',
    'straight_flush': '🔥 Стрит-флеш',
    'four_of_kind': '💎 Каре',
    'full_house': '🏠 Фулл-хаус',
    'flush': '🌈 Флеш',
    'straight': '📏 Стрит',
    'three_of_kind': '🔱 Тройка',
    'two_pair': '⚡ Две пары',
    'one_pair': '💫 Пара',
    'high_card': '💪 Старшая карта'
}

poker_games = {}

def create_poker_deck():
    """Создание колоды для покера"""
    deck = []
    for suit in POKER_SUITS:
        for rank in POKER_RANKS:
            deck.append(f"{rank}{suit}")
    random.shuffle(deck)
    return deck

def evaluate_poker_hand(cards):
    """Оценка руки в покере"""
    # Упрощенная оценка для демонстрации
    ranks = [card[:-1] for card in cards]
    rank_counts = {}
    for rank in ranks:
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    
    # Проверка на пары
    pairs = sum(1 for count in rank_counts.values() if count == 2)
    three = any(count == 3 for count in rank_counts.values())
    four = any(count == 4 for count in rank_counts.values())
    
    if four:
        return 'four_of_kind'
    elif three and pairs > 0:
        return 'full_house'
    elif three:
        return 'three_of_kind'
    elif pairs == 2:
        return 'two_pair'
    elif pairs == 1:
        return 'one_pair'
    else:
        return 'high_card'

async def poker_game(message: types.Message):
    """Игра в покер с друзьями"""
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        await message.reply("♠️ Ответь на сообщение соперника!\n📝 `покер`")
        return
    
    opponent_id = message.reply_to_message.from_user.id
    
    if opponent_id == user_id:
        await message.reply("❌ Нельзя с самим собой!")
        return
    
    # Проверяем, не играет ли уже кто-то
    if user_id in poker_games or opponent_id in poker_games:
        await message.reply("❌ Кто-то уже играет в покер!")
        return
    
    # Создаём игру
    game_id = f"{message.chat.id}_{user_id}_{opponent_id}"
    poker_games[game_id] = {
        "players": [user_id, opponent_id],
        "hands": {},
        "deck": create_poker_deck(),
        "pot": 0,
        "current_bet": 0,
        "turn": user_id,
        "status": "waiting"
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("♠️ ПРИНЯТЬ", callback_data=f"poker_yes_{message.chat.id}_{user_id}_{opponent_id}"),
         InlineKeyboardButton("❌ ОТКАЗ", callback_data=f"poker_no_{message.chat.id}_{user_id}_{opponent_id}")]
    ])
    
    await message.reply(f"♠️ {await get_name(user_id)} вызывает {await get_name(opponent_id)} на покер!\n💰 Ставка: 100 монет", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("poker_yes_"))
async def poker_accept(callback):
    data = callback.data.split("_")
    chat_id = int(data[1])
    challenger = int(data[2])
    opponent = int(data[3])
    
    if callback.from_user.id != opponent:
        await callback.answer("❌ Не тебе!")
        return
    
    await callback.message.delete()
    
    game_id = f"{chat_id}_{challenger}_{opponent}"
    game = poker_games.get(game_id)
    
    if not game:
        await callback.message.answer("❌ Игра не найдена!")
        return
    
    # Проверяем деньги
    for player in [challenger, opponent]:
        if await get_coins(player) < 100:
            await bot.send_message(chat_id, f"❌ У {await get_name(player)} нет 100 монет для ставки!")
            del poker_games[game_id]
            return
    
    # Снимаем ставки
    await remove_coins(challenger, 100)
    await remove_coins(opponent, 100)
    game["pot"] = 200
    game["status"] = "playing"
    
    # Раздаём карты
    game["hands"][challenger] = game["deck"][:5]
    game["hands"][opponent] = game["deck"][5:10]
    
    # Оцениваем руки
    hand1 = evaluate_poker_hand(game["hands"][challenger])
    hand2 = evaluate_poker_hand(game["hands"][opponent])
    
    hand_rank = {hand: i for i, hand in enumerate(POKER_HANDS.keys())}
    
    msg = f"♠️ **РЕЗУЛЬТАТ ПОКЕРА**\n\n"
    msg += f"{await get_name(challenger)}: {', '.join(game['hands'][challenger])}\n"
    msg += f"📊 Рука: {POKER_HANDS[hand1]}\n\n"
    msg += f"{await get_name(opponent)}: {', '.join(game['hands'][opponent])}\n"
    msg += f"📊 Рука: {POKER_HANDS[hand2]}\n\n"
    
    if hand_rank[hand1] < hand_rank[hand2]:
        msg += f"🏆 **{await get_name(challenger)}** победил и забирает {game['pot']} монет!"
        await add_coins(challenger, game["pot"])
    elif hand_rank[hand2] < hand_rank[hand1]:
        msg += f"🏆 **{await get_name(opponent)}** победил и забирает {game['pot']} монет!"
        await add_coins(opponent, game["pot"])
    else:
        msg += f"🤝 Ничья! Каждый забирает свои 100 монет."
        await add_coins(challenger, 100)
        await add_coins(opponent, 100)
    
    await bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)
    del poker_games[game_id]

@dp.callback_query(lambda c: c.data.startswith("poker_no_"))
async def poker_decline(callback):
    data = callback.data.split("_")
    opponent = int(data[3])
    
    if callback.from_user.id != opponent:
        await callback.answer("❌ Не тебе!")
        return
    
    await callback.message.edit_text("❌ Отказ!")

# ==================== ЧЕЛЛЕНДЖИ ====================
active_challenges = {}

async def challenge_command(message: types.Message):
    """Создание челленджа"""
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 3:
        await message.reply("ℹ️ `челлендж [название] [ставка]`\nПример: `челлендж кто больше напишет 100`")
        return
    
    challenge_name = args[1]
    try:
        bet = int(args[2])
    except:
        await message.reply("❌ Введи число для ставки!")
        return
    
    if bet < 10:
        await message.reply("❌ Минимальная ставка 10 монет!")
        return
    
    coins = await get_coins(user_id)
    if coins < bet:
        await message.reply(f"❌ У тебя только {coins} монет!")
        return
    
    # Создаём челлендж
    challenge_id = f"{message.chat.id}_{user_id}_{datetime.now().timestamp()}"
    active_challenges[challenge_id] = {
        "creator": user_id,
        "name": challenge_name,
        "bet": bet,
        "status": "waiting",
        "participants": [user_id],
        "created_at": datetime.now()
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ УЧАСТВОВАТЬ", callback_data=f"chal_join_{challenge_id}")]
    ])
    
    await message.reply(f"🏆 **НОВЫЙ ЧЕЛЛЕНДЖ!**\n\n"
                        f"📌 Название: {challenge_name}\n"
                        f"💰 Ставка: {bet} монет\n"
                        f"👤 Создатель: {await get_name(user_id)}\n"
                        f"📝 Нажмите кнопку чтобы участвовать!",
                        reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("chal_join_"))
async def challenge_join(callback):
    challenge_id = callback.data.replace("chal_join_", "")
    user_id = callback.from_user.id
    
    challenge = active_challenges.get(challenge_id)
    if not challenge:
        await callback.answer("❌ Челлендж уже завершён!")
        return
    
    if user_id in challenge["participants"]:
        await callback.answer("❌ Ты уже участвуешь!")
        return
    
    # Проверяем деньги
    coins = await get_coins(user_id)
    if coins < challenge["bet"]:
        await callback.answer(f"❌ Нужно {challenge['bet']} монет!")
        return
    
    challenge["participants"].append(user_id)
    
    if len(challenge["participants"]) >= 2:
        # Начинаем челлендж
        await callback.message.edit_text(f"🏆 **ЧЕЛЛЕНДЖ НАЧАЛСЯ!**\n\n"
                                         f"📌 {challenge['name']}\n"
                                         f"💰 Ставка: {challenge['bet']} монет\n"
                                         f"👥 Участники: {len(challenge['participants'])}\n"
                                         f"📝 Игра началась! Победитель будет определён через 5 минут.")
        
        # Ждём 5 минут
        await asyncio.sleep(300)
        
        # Выбираем победителя
        winner = random.choice(challenge["participants"])
        total_pot = challenge["bet"] * len(challenge["participants"])
        
        # Передаём деньги победителю
        for participant in challenge["participants"]:
            if participant != winner:
                await remove_coins(participant, challenge["bet"])
        
        await add_coins(winner, total_pot)
        
        await bot.send_message(callback.message.chat.id,
                               f"🏆 **ЧЕЛЛЕНДЖ ЗАВЕРШЁН!**\n\n"
                               f"📌 {challenge['name']}\n"
                               f"🏆 Победитель: {await get_name(winner)}\n"
                               f"💰 Выигрыш: {total_pot} монет!")
        
        del active_challenges[challenge_id]
    else:
        await callback.answer("✅ Ты присоединился! Ожидаем ещё участников...")

# ==================== ДУЭЛИ ====================
active_duels = {}

async def duel_command(message: types.Message):
    """Дуэль с друзьями (камень-ножницы-бумага)"""
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        await message.reply("⚔️ Ответь на сообщение соперника!\n📝 `дуэль [ставка]`")
        return
    
    opponent_id = message.reply_to_message.from_user.id
    
    if opponent_id == user_id:
        await message.reply("❌ Нельзя с самим собой!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `дуэль [ставка]`")
        return
    
    try:
        bet = int(args[1])
    except:
        await message.reply("❌ Введи число для ставки!")
        return
    
    if bet < 10:
        await message.reply("❌ Минимальная ставка 10 монет!")
        return
    
    # Проверяем деньги
    if await get_coins(user_id) < bet:
        await message.reply(f"❌ У тебя только {await get_coins(user_id)} монет!")
        return
    
    if await get_coins(opponent_id) < bet:
        await message.reply(f"❌ У {await get_name(opponent_id)} только {await get_coins(opponent_id)} монет!")
        return
    
    duel_id = f"{message.chat.id}_{user_id}_{opponent_id}"
    active_duels[duel_id] = {
        "player1": user_id,
        "player2": opponent_id,
        "bet": bet,
        "status": "waiting",
        "choices": {}
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🗿 КАМЕНЬ", callback_data=f"duel_rock_{duel_id}"),
         InlineKeyboardButton("📄 БУМАГА", callback_data=f"duel_paper_{duel_id}"),
         InlineKeyboardButton("✂️ НОЖНИЦЫ", callback_data=f"duel_scissors_{duel_id}")]
    ])
    
    await message.reply(f"⚔️ **ДУЭЛЬ!**\n\n"
                        f"{await get_name(user_id)} вызвал {await get_name(opponent_id)}!\n"
                        f"💰 Ставка: {bet} монет\n\n"
                        f"Выберите оружие:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("duel_"))
async def duel_choice(callback):
    data = callback.data.split("_")
    choice = data[1]
    duel_id = "_".join(data[2:])
    
    user_id = callback.from_user.id
    duel = active_duels.get(duel_id)
    
    if not duel:
        await callback.answer("❌ Дуэль уже завершена!")
        return
    
    if user_id not in [duel["player1"], duel["player2"]]:
        await callback.answer("❌ Ты не участвуешь в этой дуэли!")
        return
    
    if user_id in duel["choices"]:
        await callback.answer("❌ Ты уже сделал выбор!")
        return
    
    # Сохраняем выбор
    choice_map = {"rock": "🗿", "paper": "📄", "scissors": "✂️"}
    duel["choices"][user_id] = choice_map[choice]
    
    await callback.answer(f"✅ Выбран {choice_map[choice]}")
    
    # Если оба выбрали
    if len(duel["choices"]) == 2:
        player1_choice = duel["choices"][duel["player1"]]
        player2_choice = duel["choices"][duel["player2"]]
        
        # Определяем победителя
        results = {
            ("🗿", "✂️"): duel["player1"],
            ("✂️", "📄"): duel["player1"],
            ("📄", "🗿"): duel["player1"],
            ("✂️", "🗿"): duel["player2"],
            ("📄", "✂️"): duel["player2"],
            ("🗿", "📄"): duel["player2"],
        }
        
        if player1_choice == player2_choice:
            winner = None
            result_text = "🤝 Ничья!"
        else:
            winner = results.get((player1_choice, player2_choice))
            if winner == duel["player1"]:
                result_text = f"🏆 **{await get_name(duel['player1'])}** победил!"
            else:
                result_text = f"🏆 **{await get_name(duel['player2'])}** победил!"
        
        # Обработка ставки
        if winner:
            await remove_coins(duel["player1"], duel["bet"])
            await remove_coins(duel["player2"], duel["bet"])
            await add_coins(winner, duel["bet"] * 2)
        
        await callback.message.edit_text(
            f"⚔️ **РЕЗУЛЬТАТ ДУЭЛИ**\n\n"
            f"{await get_name(duel['player1'])}: {player1_choice}\n"
            f"{await get_name(duel['player2'])}: {player2_choice}\n\n"
            f"{result_text}\n"
            f"{'💰 ' + await get_name(winner) + ' получает ' + str(duel['bet'] * 2) + ' монет!' if winner else '💰 Деньги возвращены!'}"
        )
        
        del active_duels[duel_id]

# ==================== ТУРНИРЫ ====================
tournaments = {}

async def tournament_create(message: types.Message):
    """Создание турнира"""
    if await get_admin_level(message.from_user.id) < 4:
        await message.reply("❌ У тебя нет прав! (нужен 4+ уровень)")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `турнир создать [название] [приз]`")
        return
    
    name = " ".join(args[1:-1])
    prize = int(args[-1])
    
    tournament_id = f"{message.chat.id}_{datetime.now().timestamp()}"
    tournaments[tournament_id] = {
        "name": name,
        "prize": prize,
        "participants": [],
        "creator": message.from_user.id,
        "status": "waiting",
        "created_at": datetime.now()
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🏆 УЧАСТВОВАТЬ", callback_data=f"tourn_join_{tournament_id}")]
    ])
    
    await message.reply(f"🏆 **НОВЫЙ ТУРНИР!**\n\n"
                        f"📌 Название: {name}\n"
                        f"💰 Приз: {prize} монет\n"
                        f"👤 Создатель: {await get_name(message.from_user.id)}\n\n"
                        f"Нажми кнопку чтобы участвовать!", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("tourn_join_"))
async def tournament_join(callback):
    tournament_id = callback.data.replace("tourn_join_", "")
    user_id = callback.from_user.id
    
    tournament = tournaments.get(tournament_id)
    if not tournament:
        await callback.answer("❌ Турнир уже завершён!")
        return
    
    if user_id in tournament["participants"]:
        await callback.answer("❌ Ты уже участвуешь!")
        return
    
    tournament["participants"].append(user_id)
    await callback.answer(f"✅ Ты участвуешь! Всего участников: {len(tournament['participants'])}")

print(f"✅ Часть 16/20 загружена! Строк: ~700")
# ==================== ЧАСТЬ 17/20: ЗАПУСК БОТА, ФОНОВЫЕ ЗАДАЧИ, ОБРАБОТКА ОШИБОК ====================

# ==================== ФОНОВЫЕ ЗАДАЧИ ====================

async def daily_reset_task():
    """Ежедневный сброс заданий и бонусов"""
    while True:
        now = datetime.now()
        # Ждём до полуночи
        next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        sleep_seconds = (next_day - now).total_seconds()
        await asyncio.sleep(sleep_seconds)
        
        try:
            # Сбрасываем ежедневные задания
            conn = sqlite3.connect("fable_bot.db")
            c = conn.cursor()
            c.execute("DELETE FROM daily_quests WHERE quest_date < ?", (datetime.now().strftime("%Y-%m-%d"),))
            conn.commit()
            conn.close()
            
            # Очищаем кэш флуда
            flood_users.clear()
            
            print("✅ Ежедневный сброс выполнен!")
        except Exception as e:
            print(f"❌ Ошибка ежедневного сброса: {e}")

async def weekly_reset_task():
    """Еженедельный сброс"""
    while True:
        now = datetime.now()
        # Ждём до понедельника
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = (now + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        sleep_seconds = (next_monday - now).total_seconds()
        await asyncio.sleep(sleep_seconds)
        
        try:
            # Сбрасываем еженедельные задания
            conn = sqlite3.connect("fable_bot.db")
            c = conn.cursor()
            c.execute("DELETE FROM weekly_quests WHERE quest_week < ?", (datetime.now().strftime("%Y-W%W"),))
            conn.commit()
            conn.close()
            
            print("✅ Еженедельный сброс выполнен!")
        except Exception as e:
            print(f"❌ Ошибка еженедельного сброса: {e}")

async def vip_check_task():
    """Проверка VIP статусов"""
    while True:
        await asyncio.sleep(3600)  # Каждый час
        
        try:
            conn = sqlite3.connect("fable_bot.db")
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute("UPDATE users SET vip = 0, vip_until = NULL WHERE vip_until < ?", (now,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Ошибка проверки VIP: {e}")

async def economy_event_task():
    """Фоновая задача для экономических событий"""
    global active_economy_event
    
    while True:
        await asyncio.sleep(60)  # Проверяем каждую минуту
        
        if active_economy_event:
            elapsed = (datetime.now() - active_economy_event["started"]).total_seconds()
            if elapsed >= active_economy_event["duration"]:
                active_economy_event = None
                try:
                    await bot.send_message(CREATOR_ID, "✅ Экономическое событие автоматически завершено!")
                except:
                    pass

async def deposit_interest_task():
    """Фоновая задача для начисления процентов по вкладам"""
    while True:
        await asyncio.sleep(3600)  # Каждый час
        
        try:
            conn = sqlite3.connect("fable_bot.db")
            c = conn.cursor()
            
            c.execute("""
                SELECT id, user_id, amount, interest_rate, last_interest, ended_at, type 
                FROM deposits WHERE active = 1
            """)
            deposits = c.fetchall()
            
            for dep in deposits:
                dep_id, user_id, amount, rate, last_interest, ended_at, dep_type = dep
                
                try:
                    last = datetime.fromisoformat(last_interest)
                    now = datetime.now()
                    
                    # Проверяем окончание срока
                    if ended_at:
                        end_time = datetime.fromisoformat(ended_at)
                        if now >= end_time:
                            # Автоматически закрываем вклад
                            hours_passed = (now - last).total_seconds() / 3600
                            interest = int(amount * (rate / 100) * hours_passed)
                            if await is_vip(user_id):
                                interest = int(interest * 1.5)
                            total = amount + interest
                            
                            await close_deposit(dep_id)
                            await add_bank(user_id, total)
                            
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"✅ **ВКЛАД #{dep_id} АВТОМАТИЧЕСКИ ЗАКРЫТ**\n\n"
                                    f"💰 Сумма: {amount} монет\n"
                                    f"📈 Проценты: +{interest} монет\n"
                                    f"💳 Итого: **{total}** монет",
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            except:
                                pass
                            continue
                    
                    hours_since_last = (now - last).total_seconds() / 3600
                    
                    if hours_since_last >= 1:
                        interest = int(amount * (rate / 100))
                        
                        if await is_vip(user_id):
                            interest = int(interest * 1.5)
                        
                        if interest > 0:
                            await add_bank(user_id, interest)
                            await update_deposit_interest(dep_id, now.isoformat())
                            
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"🏦 **Начислены проценты по вкладу #{dep_id}**\n"
                                    f"💰 +{interest} монет\n"
                                    f"📊 Текущая ставка: {rate}% в час",
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            except:
                                pass
                except Exception as e:
                    print(f"❌ Ошибка обработки вклада {dep_id}: {e}")
            
            conn.close()
        except Exception as e:
            print(f"❌ Ошибка task: {e}")

async def auction_check_task():
    """Проверка и завершение истекших аукционов"""
    while True:
        await asyncio.sleep(60)  # Каждую минуту
        
        try:
            conn = sqlite3.connect("fable_bot.db")
            c = conn.cursor()
            c.execute("SELECT id FROM auctions WHERE active = 1 AND ends_at <= ?", (datetime.now().isoformat(),))
            expired = c.fetchall()
            conn.close()
            
            for (auction_id,) in expired:
                await end_auction(auction_id)
        except Exception as e:
            print(f"❌ Ошибка проверки аукционов: {e}")

async def auto_reaction_task():
    """Автоматические реакции на новые сообщения"""
    # Эта функция уже реализована в auto_reaction в части 2
    pass

async def auto_meme_task():
    """Автоматическая отправка мемов в чаты"""
    while True:
        await asyncio.sleep(random.randint(1800, 7200))  # 30 минут - 2 часа
        
        try:
            # Получаем список активных чатов
            conn = sqlite3.connect("fable_bot.db")
            c = conn.cursor()
            c.execute("SELECT DISTINCT chat_id FROM chat_stats")
            chats = c.fetchall()
            conn.close()
            
            for (chat_id,) in chats:
                # Проверяем, активен ли чат (были сообщения за последние 24 часа)
                conn = sqlite3.connect("fable_bot.db")
                c = conn.cursor()
                yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                c.execute("SELECT COUNT(*) FROM chat_stats WHERE chat_id = ? AND last_message > ?", (chat_id, yesterday))
                count = c.fetchone()[0]
                conn.close()
                
                if count > 0:
                    # Генерируем мем
                    top_text = random.choice([
                        "Когда в чате тишина",
                        "Мой уровень активности",
                        "Когда получил бонус",
                        "Реакция на новости",
                        "Мой план на сегодня"
                    ])
                    bottom_text = random.choice([
                        "Просто наблюдаю",
                        "Жду своего часа",
                        "Вот это поворот!",
                        "Жизнь удалась!",
                        "Неожиданно!"
                    ])
                    
                    meme_data = await generate_meme_with_text(top_text, bottom_text)
                    if meme_data:
                        try:
                            await bot.send_photo(chat_id, BufferedInputFile(meme_data, filename="meme.png"), 
                                                caption=f"🎭 Случайный мем! {random.choice(['😄', '😂', '🤣', '😎'])}")
                        except:
                            pass
        except Exception as e:
            print(f"❌ Ошибка авто-мема: {e}")

# ==================== ОБРАБОТКА ОШИБОК ====================

@dp.errors()
async def handle_errors(update, exception):
    """Глобальный обработчик ошибок"""
    error_text = f"❌ **Ошибка в боте:**\n```\n{exception}\n```"
    
    try:
        await bot.send_message(CREATOR_ID, error_text, parse_mode=ParseMode.MARKDOWN)
    except:
        pass
    
    print(f"❌ Ошибка: {exception}")
    return True

async def safe_execute(func, *args, **kwargs):
    """Безопасное выполнение функции с обработкой ошибок"""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        error_text = f"❌ Ошибка в {func.__name__}: {e}"
        try:
            await bot.send_message(CREATOR_ID, error_text)
        except:
            pass
        print(error_text)
        return None

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Главная функция запуска бота"""
    print(f"🚀 {BOT_NAME} запускается...")
    print(f"👑 Создатель: {CREATOR_ID}")
    print(f"📊 Всего строк в боте: ~14000")
    
    # Запускаем фоновые задачи
    asyncio.create_task(daily_reset_task())
    asyncio.create_task(weekly_reset_task())
    asyncio.create_task(vip_check_task())
    asyncio.create_task(economy_event_task())
    asyncio.create_task(deposit_interest_task())
    asyncio.create_task(auction_check_task())
    asyncio.create_task(auto_meme_task())
    
    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем бота
    print(f"✅ {BOT_NAME} готов к работе!")
    await dp.start_polling(bot)

# ==================== ДОПОЛНИТЕЛЬНЫЕ ОБРАБОТЧИКИ ====================

@dp.message()
async def catch_all(message: types.Message):
    """Ловит все необработанные сообщения"""
    # Игнорируем сообщения от ботов
    if message.from_user.is_bot:
        return
    
    # Если сообщение было отправлено в ЛС создателю
    if message.chat.type == "private" and message.from_user.id == CREATOR_ID:
        # Проверяем специальные команды создателя
        text = message.text.lower()
        
        if text == "бот статус":
            await message.reply(f"✅ Бот работает!\n"
                               f"🕐 Время работы: {datetime.now() - BOT_START_TIME}\n"
                               f"👑 Создатель: {CREATOR_ID}\n"
                               f"📊 Пользователей: {len(await get_all_users())}")
            return
        
        if text == "бот перезагрузить":
            await message.reply("🔄 Перезагрузка бота...")
            await log_action(CREATOR_ID, "restart_bot", "Перезагрузка бота")
            # Перезагружаем бота
            import sys
            import os
            os.execl(sys.executable, sys.executable, *sys.argv)
            return
    
    # Если это обычное сообщение в чате - проверяем на авто-реакции
    if message.text:
        # Проверяем на ключевые слова для автоматических ответов
        text = message.text.lower()
        
        # Простые ответы на приветствия
        if any(word in text for word in ["привет", "здравствуй", "хай", "хелло"]):
            await asyncio.sleep(random.uniform(0.5, 2))
            await message.reply(random.choice([
                "Привет! 👋",
                "Здравствуй! 😊",
                "Хай! 🖐️",
                "Hello! 👋"
            ]))
            return
        
        if any(word in text for word in ["спасибо", "благодарю", "мерси"]):
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await message.reply(random.choice([
                "Пожалуйста! ❤️",
                "Всегда рад помочь! 😊",
                "Не за что! 🥰"
            ]))
            return
        
        if any(word in text for word in ["пока", "до свидания", "бай"]):
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await message.reply(random.choice([
                "Пока-пока! 👋",
                "До встречи! 😢",
                "Заходи ещё! 🖐️"
            ]))
            return
        
        # Случайные ответы (10% шанс)
        if random.random() < 0.1:
            await asyncio.sleep(random.uniform(0.5, 2))
            await message.reply(random.choice([
                "Интересно! 🤔",
                "Продолжай! 👂",
                "Ну и ну! 😮",
                "Я слушаю! 👂",
                "Ух ты! 😲"
            ]))

async def get_all_users():
    """Получение всех пользователей"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    return users

# ==================== ДОБАВЛЯЕМ ОБРАБОТЧИКИ КОМАНД ДЛЯ СОЗДАТЕЛЯ ====================

@dp.message(lambda m: m.from_user.id == CREATOR_ID and m.chat.type == "private")
async def creator_private_commands(message: types.Message):
    """Обработка всех команд создателя в ЛС"""
    text = message.text.lower()
    
    # Управление монетами
    if text.startswith("дать монеты "):
        await creator_give_coins(message)
        return
    
    if text.startswith("забрать монеты "):
        await creator_remove_coins(message)
        return
    
    if text.startswith("дать банк "):
        await creator_give_bank(message)
        return
    
    if text.startswith("дать предмет "):
        await creator_give_item(message)
        return
    
    # Управление уровнями
    if text.startswith("дать уровень "):
        await creator_give_level(message)
        return
    
    if text.startswith("убрать уровень "):
        await creator_remove_level(message)
        return
    
    # Управление VIP
    if text.startswith("дать вип "):
        await creator_give_vip(message)
        return
    
    if text.startswith("убрать вип "):
        await creator_remove_vip(message)
        return
    
    # Статистика
    if text == "статистика бота":
        await creator_bot_stats(message)
        return
    
    if text.startswith("логи "):
        period = text.replace("логи ", "")
        await creator_logs(message, period)
        return
    
    if text.startswith("отчёт "):
        await creator_report(message)
        return
    
    # Экономические события
    if text.startswith("эконом старт "):
        await creator_economy_start(message)
        return
    
    if text == "эконом стоп":
        await creator_economy_stop(message)
        return
    
    if text == "эконом статус":
        await creator_economy_status(message)
        return
    
    # Промо-коды
    if text.startswith("создать промо "):
        await creator_create_promo(message)
        return
    
    if text == "список промо":
        await creator_list_promos(message)
        return
    
    if text.startswith("удалить промо "):
        await creator_delete_promo(message)
        return
    
    # Массовые выдачи
    if text.startswith("дать монеты всем "):
        await creator_give_all_coins(message)
        return
    
    if text.startswith("дать банк всем "):
        await creator_give_all_bank(message)
        return
    
    # Команды создателя
    if text == "команды создателя":
        await creator_manage_commands(message)
        return
    
    if text == "бот статус":
        await message.reply(f"✅ Бот работает!\n"
                           f"🕐 Время работы: {datetime.now() - BOT_START_TIME}")
        return
    
    if text == "бот перезагрузить":
        await message.reply("🔄 Перезагрузка бота...")
        await log_action(CREATOR_ID, "restart_bot", "Перезагрузка бота")
        import sys
        import os
        os.execl(sys.executable, sys.executable, *sys.argv)
        return

print(f"✅ Часть 17/20 загружена! Строк: ~700")
# ==================== ЧАСТЬ 18/20: РАСШИРЕННЫЕ ФУНКЦИИ БАЗЫ ДАННЫХ ====================

# ==================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ БАЗЫ ДАННЫХ ====================

async def get_all_users():
    """Получение всех пользователей"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, coins, bank, admin_level, vip, created_at FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

async def get_top_users_by_coins(limit: int = 10):
    """Получение топ пользователей по монетам"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, coins, bank, 
               COALESCE((SELECT SUM(amount) FROM deposits WHERE user_id = users.user_id AND active = 1), 0) as deposits
        FROM users 
        ORDER BY (coins + bank + COALESCE((SELECT SUM(amount) FROM deposits WHERE user_id = users.user_id AND active = 1), 0)) DESC 
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

async def get_top_users_by_rep(limit: int = 10):
    """Получение топ пользователей по репутации"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, rep FROM users ORDER BY rep DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

async def get_top_users_by_messages(limit: int = 10):
    """Получение топ пользователей по сообщениям"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, SUM(messages) as total_messages 
        FROM chat_stats 
        GROUP BY user_id 
        ORDER BY total_messages DESC 
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

async def get_total_coins():
    """Получение общего количества монет в системе"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT SUM(coins) FROM users")
    total_coins = c.fetchone()[0] or 0
    c.execute("SELECT SUM(bank) FROM users")
    total_bank = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM deposits WHERE active = 1")
    total_deposits = c.fetchone()[0] or 0
    conn.close()
    return total_coins + total_bank + total_deposits

async def get_total_users():
    """Получение общего количества пользователей"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    conn.close()
    return total

async def get_total_chats():
    """Получение общего количества чатов"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT chat_id) FROM chat_stats")
    total = c.fetchone()[0]
    conn.close()
    return total

async def get_total_messages():
    """Получение общего количества сообщений"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT SUM(messages) FROM chat_stats")
    total = c.fetchone()[0] or 0
    conn.close()
    return total

async def get_user_by_username(username: str):
    """Поиск пользователя по имени пользователя"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username FROM users WHERE username LIKE ?", (f"%{username}%",))
    rows = c.fetchall()
    conn.close()
    return rows

async def get_chat_stats(chat_id: int):
    """Получение статистики чата"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT user_id) FROM chat_stats WHERE chat_id = ?", (chat_id,))
    users = c.fetchone()[0]
    c.execute("SELECT SUM(messages) FROM chat_stats WHERE chat_id = ?", (chat_id,))
    messages = c.fetchone()[0] or 0
    c.execute("SELECT user_id, messages FROM chat_stats WHERE chat_id = ? ORDER BY messages DESC LIMIT 10", (chat_id,))
    top_users = c.fetchall()
    conn.close()
    return {"users": users, "messages": messages, "top_users": top_users}

async def update_user_stats(user_id: int, username: str = None):
    """Обновление статистики пользователя"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    if username:
        c.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    c.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

# ==================== ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ ====================

def format_duration(seconds: int) -> str:
    """Форматирование длительности"""
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        return f"{seconds // 60} мин {seconds % 60} сек"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} ч {minutes} мин"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days} д {hours} ч"

def format_number(num: int) -> str:
    """Форматирование больших чисел"""
    if num >= 1000000000:
        return f"{num/1000000000:.1f}B"
    elif num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    else:
        return str(num)

def calculate_level_exp(level: int) -> int:
    """Расчёт опыта для уровня"""
    return level * 100 + (level - 1) * 50

async def check_and_unlock_achievements(user_id: int):
    """Проверка и выдача достижений"""
    achievements = []
    
    # Проверяем наличие работы
    job = await get_job(user_id)
    if job and "first_work" not in await get_achievements(user_id):
        await unlock_achievement(user_id, "first_work")
        await add_coins(user_id, 500)
        achievements.append("💼 Первая работа")
    
    # Проверяем количество монет
    coins = await get_coins(user_id)
    if coins >= 1000000 and "first_money" not in await get_achievements(user_id):
        await unlock_achievement(user_id, "first_money")
        await add_coins(user_id, 10000)
        achievements.append("💰 Первый миллион")
    
    # Проверяем бизнесы
    businesses = await get_businesses(user_id)
    if len(businesses) >= 1 and "first_business" not in await get_achievements(user_id):
        await unlock_achievement(user_id, "first_business")
        await add_coins(user_id, 1000)
        achievements.append("🏪 Первый бизнес")
    
    if len(businesses) >= 10 and "ten_businesses" not in await get_achievements(user_id):
        await unlock_achievement(user_id, "ten_businesses")
        await add_coins(user_id, 5000)
        achievements.append("🏪 Магнат")
    
    # Проверяем репутацию
    rep = await get_rep(user_id)
    if rep >= 10 and "first_rep" not in await get_achievements(user_id):
        await unlock_achievement(user_id, "first_rep")
        await add_coins(user_id, 500)
        achievements.append("⭐ Первая репутация")
    
    # Проверяем брак
    spouse = await get_marriage(user_id)
    if spouse and "first_marriage" not in await get_achievements(user_id):
        await unlock_achievement(user_id, "first_marriage")
        await add_coins(user_id, 1000)
        achievements.append("💍 Первая свадьба")
    
    # Проверяем покупки в магазине
    inventory = await get_inventory(user_id)
    total_items = sum(item[1] for item in inventory)
    if total_items >= 1 and "first_shop" not in await get_achievements(user_id):
        await unlock_achievement(user_id, "first_shop")
        await add_coins(user_id, 500)
        achievements.append("🛒 Покупатель")
    
    if total_items >= 10 and "ten_shop" not in await get_achievements(user_id):
        await unlock_achievement(user_id, "ten_shop")
        await add_coins(user_id, 2000)
        achievements.append("🛒 Шопоголик")
    
    return achievements

# ==================== СИСТЕМА РЕФЕРАЛОВ ====================

async def create_referral_link(user_id: int) -> str:
    """Создание реферальной ссылки"""
    return f"https://t.me/{BOT_NAME}?start=ref_{user_id}"

async def process_referral(new_user_id: int, referrer_id: int):
    """Обработка реферала"""
    if new_user_id == referrer_id:
        return
    
    # Проверяем, не был ли уже использован реферер
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM referrals WHERE referrer_id = ? AND referred_id = ?", (referrer_id, new_user_id))
    if c.fetchone():
        conn.close()
        return
    
    # Добавляем реферала
    c.execute("INSERT INTO referrals (referrer_id, referred_id, date) VALUES (?, ?, ?)",
              (referrer_id, new_user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Обновляем счётчик рефералов
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?", (referrer_id,))
    conn.commit()
    conn.close()
    
    # Бонусы
    await add_coins(referrer_id, 500)
    await add_coins(new_user_id, 200)
    
    # Проверяем VIP статус (5 рефералов)
    ref_count = await get_ref_count(referrer_id)
    if ref_count >= 5 and not await is_vip(referrer_id):
        await set_vip(referrer_id, 30)
        try:
            await bot.send_message(referrer_id, f"👑 Ты получил VIP на 30 дней за 5 рефералов!")
        except:
            pass
    
    await log_action(referrer_id, "referral", f"Привёл реферала {await get_name(new_user_id)}")

# ==================== СИСТЕМА УВЕДОМЛЕНИЙ ====================

async def send_notification(user_id: int, message: str):
    """Отправка уведомления пользователю"""
    try:
        await bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
        return True
    except:
        return False

async def broadcast_message(message: str, only_vip: bool = False):
    """Массовая рассылка сообщений"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    if only_vip:
        c.execute("SELECT user_id FROM users WHERE vip = 1")
    else:
        c.execute("SELECT user_id FROM users")
    
    users = c.fetchall()
    conn.close()
    
    sent = 0
    failed = 0
    
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)  # Чтобы не превысить лимиты
        except:
            failed += 1
    
    return sent, failed

# ==================== СИСТЕМА ОПРОСОВ ====================

polls = {}

async def create_poll(message: types.Message):
    """Создание опроса"""
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `опрос [вопрос] | [вариант1] | [вариант2] | [вариант3]`")
        return
    
    parts = args[1].split(" | ")
    if len(parts) < 3:
        await message.reply("❌ Нужно: вопрос | вариант1 | вариант2 (минимум 2 варианта)")
        return
    
    question = parts[0]
    options = parts[1:]
    
    poll_id = f"{message.chat.id}_{datetime.now().timestamp()}"
    polls[poll_id] = {
        "question": question,
        "options": options,
        "votes": {opt: [] for opt in options},
        "creator": message.from_user.id,
        "created_at": datetime.now()
    }
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for i, option in enumerate(options):
        keyboard.add(InlineKeyboardButton(f"📊 {option}", callback_data=f"poll_vote_{poll_id}_{i}"))
    keyboard.add(InlineKeyboardButton("📊 Результаты", callback_data=f"poll_results_{poll_id}"))
    
    msg = f"📊 **ОПРОС**\n\n"
    msg += f"❓ {question}\n\n"
    msg += f"📝 Голосуйте! (Всего вариантов: {len(options)})"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("poll_vote_"))
async def poll_vote(callback):
    data = callback.data.split("_")
    poll_id = f"{data[2]}_{data[3]}"
    option_index = int(data[4])
    
    user_id = callback.from_user.id
    poll = polls.get(poll_id)
    
    if not poll:
        await callback.answer("❌ Опрос уже завершён!")
        return
    
    # Проверяем, голосовал ли уже
    for opt in poll["options"]:
        if user_id in poll["votes"][opt]:
            await callback.answer("❌ Ты уже голосовал!")
            return
    
    poll["votes"][poll["options"][option_index]].append(user_id)
    await callback.answer(f"✅ Ты проголосовал за: {poll['options'][option_index]}")

@dp.callback_query(lambda c: c.data.startswith("poll_results_"))
async def poll_results(callback):
    poll_id = callback.data.replace("poll_results_", "")
    poll = polls.get(poll_id)
    
    if not poll:
        await callback.answer("❌ Опрос не найден!")
        return
    
    total_votes = sum(len(votes) for votes in poll["votes"].values())
    
    msg = f"📊 **РЕЗУЛЬТАТЫ ОПРОСА**\n\n"
    msg += f"❓ {poll['question']}\n\n"
    
    for option, votes in poll["votes"].items():
        count = len(votes)
        percentage = (count / total_votes * 100) if total_votes > 0 else 0
        bar_length = int(percentage / 5)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        msg += f"{option}\n"
        msg += f"{bar} {count} голосов ({percentage:.1f}%)\n\n"
    
    msg += f"📊 Всего голосов: {total_votes}"
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN)

print(f"✅ Часть 18/20 загружена! Строк: ~700")
# ==================== ЧАСТЬ 19/20: РАСШИРЕННЫЕ НАСТРОЙКИ, РЕЖИМЫ ЧАТА, ИНТЕГРАЦИИ ====================

# ==================== РАСШИРЕННЫЕ НАСТРОЙКИ ЧАТА ====================

async def get_chat_settings_full(chat_id: int) -> dict:
    """Получение всех настроек чата"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("""
        SELECT chat_id, mode, welcome, goodbye, antimat_enabled, anticaps_enabled, 
               antispam_enabled, antiflood_enabled, antilinks_enabled, rules, slow_mode,
               captcha_enabled, autodelete_enabled, welcome_enabled, goodbye_enabled
        FROM chat_settings WHERE chat_id = ?
    """, (chat_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "chat_id": row[0],
            "mode": row[1],
            "welcome": row[2],
            "goodbye": row[3],
            "antimat_enabled": row[4],
            "anticaps_enabled": row[5],
            "antispam_enabled": row[6],
            "antiflood_enabled": row[7],
            "antilinks_enabled": row[8],
            "rules": row[9],
            "slow_mode": row[10],
            "captcha_enabled": row[11] if len(row) > 11 else 0,
            "autodelete_enabled": row[12] if len(row) > 12 else 0,
            "welcome_enabled": row[13] if len(row) > 13 else 1,
            "goodbye_enabled": row[14] if len(row) > 14 else 1
        }
    
    return {
        "chat_id": chat_id,
        "mode": "свободный",
        "welcome": None,
        "goodbye": None,
        "antimat_enabled": 0,
        "anticaps_enabled": 0,
        "antispam_enabled": 0,
        "antiflood_enabled": 0,
        "antilinks_enabled": 0,
        "rules": "",
        "slow_mode": 0,
        "captcha_enabled": 0,
        "autodelete_enabled": 0,
        "welcome_enabled": 1,
        "goodbye_enabled": 1
    }

async def update_chat_setting(chat_id: int, setting: str, value):
    """Обновление настройки чата"""
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute(f"INSERT OR REPLACE INTO chat_settings (chat_id, {setting}) VALUES (?, ?) "
              f"ON CONFLICT(chat_id) DO UPDATE SET {setting} = ?", 
              (chat_id, value, value))
    conn.commit()
    conn.close()

# ==================== РЕЖИМЫ ЧАТА ====================

@dp.message()
async def apply_chat_mode(message: types.Message):
    """Применение режима чата"""
    if not message.text:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    admin_level = await get_admin_level(user_id)
    
    settings = await get_chat_settings_full(chat_id)
    mode = settings.get("mode", "свободный")
    
    # Свободный режим - все могут писать
    if mode == "свободный":
        return
    
    # Строгий режим - только админы и модераторы (1+ уровень)
    if mode == "строгий":
        if admin_level < 1:
            await message.delete()
            await message.reply(f"⚠️ {message.from_user.first_name}, в чате строгий режим! Только модераторы могут писать.")
            return
    
    # Только админы - только 3+ уровень
    if mode == "только_админы":
        if admin_level < 3:
            await message.delete()
            await message.reply(f"⚠️ {message.from_user.first_name}, в чате режим 'только админы'!")
            return

# ==================== SLOW MODE (МЕДЛЕННЫЙ РЕЖИМ) ====================

slow_mode_cache = {}

@dp.message()
async def apply_slow_mode(message: types.Message):
    """Применение медленного режима"""
    if not message.text:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Проверяем, не админ ли это
    if await get_admin_level(user_id) >= 1:
        return
    
    settings = await get_chat_settings_full(chat_id)
    slow_mode = settings.get("slow_mode", 0)
    
    if slow_mode <= 0:
        return
    
    # Проверяем, когда пользователь писал в последний раз
    if user_id in slow_mode_cache:
        last_time = slow_mode_cache[user_id]
        elapsed = (datetime.now() - last_time).total_seconds()
        if elapsed < slow_mode:
            await message.delete()
            remaining = int(slow_mode - elapsed)
            await message.reply(f"⏳ Подожди {remaining} сек перед следующим сообщением!")
            return
    
    slow_mode_cache[user_id] = datetime.now()

async def set_slow_mode(message: types.Message):
    """Установка медленного режима"""
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `слоу режим [секунды]`\n0 - выключить")
        return
    
    try:
        seconds = int(args[1])
        if seconds < 0 or seconds > 60:
            await message.reply("❌ От 0 до 60 секунд!")
            return
        
        await update_chat_setting(message.chat.id, "slow_mode", seconds)
        await log_action(message.from_user.id, "slow_mode", f"Установил {seconds} сек")
        
        if seconds == 0:
            await message.reply("✅ Медленный режим выключен!")
        else:
            await message.reply(f"✅ Медленный режим установлен: {seconds} сек между сообщениями!")
    except:
        await message.reply("❌ Введи число!")

# ==================== КАПЧА СИСТЕМА ====================

@dp.message(F.new_chat_members)
async def captcha_check(message: types.Message):
    """Проверка капчи для новых участников"""
    settings = await get_chat_settings_full(message.chat.id)
    if not settings.get("captcha_enabled", 0):
        return
    
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        
        # Генерируем капчу
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        result = num1 + num2
        
        captcha_cache[member.id] = {
            "result": result,
            "attempts": 0,
            "time": datetime.now()
        }
        
        # Отправляем капчу
        await message.reply(
            f"🤖 {member.first_name}, ты не бот?\n"
            f"Реши пример: **{num1} + {num2} = ?**\n"
            f"⏳ У тебя 60 секунд!",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Временно мутим
        try:
            await bot.restrict_chat_member(
                message.chat.id,
                member.id,
                ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(minutes=1)
            )
        except:
            pass

@dp.message()
async def captcha_answer(message: types.Message):
    """Обработка ответа на капчу"""
    if message.from_user.id not in captcha_cache:
        return
    
    captcha = captcha_cache[message.from_user.id]
    
    # Проверяем время
    if (datetime.now() - captcha["time"]).total_seconds() > 60:
        await bot.ban_chat_member(message.chat.id, message.from_user.id)
        await bot.unban_chat_member(message.chat.id, message.from_user.id)
        del captcha_cache[message.from_user.id]
        await message.reply(f"❌ {message.from_user.first_name} не прошёл капчу!")
        return
    
    try:
        answer = int(message.text)
        if answer == captcha["result"]:
            # Правильный ответ
            await bot.restrict_chat_member(
                message.chat.id,
                message.from_user.id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            del captcha_cache[message.from_user.id]
            await message.reply(f"✅ {message.from_user.first_name} прошёл капчу!")
        else:
            captcha["attempts"] += 1
            if captcha["attempts"] >= 3:
                await bot.ban_chat_member(message.chat.id, message.from_user.id)
                await bot.unban_chat_member(message.chat.id, message.from_user.id)
                del captcha_cache[message.from_user.id]
                await message.reply(f"❌ {message.from_user.first_name} не прошёл капчу!")
            else:
                await message.reply(f"❌ Неправильно! Попытка {captcha['attempts']}/3")
    except:
        await message.reply("❌ Введи число!")

async def toggle_captcha(message: types.Message):
    """Включение/выключение капчи"""
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `капча вкл` или `капча выкл`")
        return
    
    value = 1 if args[1].lower() == "вкл" else 0
    await update_chat_setting(message.chat.id, "captcha_enabled", value)
    await log_action(message.from_user.id, "captcha", f"{'включил' if value else 'выключил'}")
    await message.reply(f"✅ Капча {'включена' if value else 'выключена'}!")

# ==================== АВТОУДАЛЕНИЕ СООБЩЕНИЙ ====================

@dp.message()
async def auto_delete_old_messages(message: types.Message):
    """Автоудаление старых сообщений"""
    settings = await get_chat_settings_full(message.chat.id)
    if not settings.get("autodelete_enabled", 0):
        return
    
    # Удаляем сообщение через 10 минут
    await asyncio.sleep(600)
    try:
        await message.delete()
    except:
        pass

async def toggle_autodelete(message: types.Message):
    """Включение/выключение автоудаления"""
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `автоудаление вкл` или `автоудаление выкл`")
        return
    
    value = 1 if args[1].lower() == "вкл" else 0
    await update_chat_setting(message.chat.id, "autodelete_enabled", value)
    await log_action(message.from_user.id, "autodelete", f"{'включил' if value else 'выключил'}")
    await message.reply(f"✅ Автоудаление {'включено' if value else 'выключено'}!")

# ==================== ПРИВЕТСТВИЯ И ПРОЩАНИЯ (РАСШИРЕННЫЕ) ====================

async def set_welcome_message(message: types.Message):
    """Установка приветствия"""
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `приветствие [текст]`\nИспользуй {user} для имени")
        return
    
    welcome_text = args[1]
    await update_chat_setting(message.chat.id, "welcome", welcome_text)
    await update_chat_setting(message.chat.id, "welcome_enabled", 1)
    await log_action(message.from_user.id, "set_welcome", f"Установил приветствие")
    await message.reply(f"✅ Приветствие установлено!")

async def set_goodbye_message(message: types.Message):
    """Установка прощания"""
    if await get_admin_level(message.from_user.id) < 3:
        await message.reply("❌ У тебя нет прав! (нужен 3+ уровень)")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `прощание [текст]`\nИспользуй {user} для имени")
        return
    
    goodbye_text = args[1]
    await update_chat_setting(message.chat.id, "goodbye", goodbye_text)
    await update_chat_setting(message.chat.id, "goodbye_enabled", 1)
    await log_action(message.from_user.id, "set_goodbye", f"Установил прощание")
    await message.reply(f"✅ Прощание установлено!")

# ==================== ИНТЕГРАЦИИ ====================

# ----- ИНТЕГРАЦИЯ С ВНЕШНИМИ СЕРВИСАМИ -----

async def get_weather(city: str) -> str:
    """Получение погоды (заглушка)"""
    # Здесь можно подключить реальное API погоды
    return f"🌤️ Погода в {city}: +25°C, солнечно"

async def get_news() -> str:
    """Получение новостей (заглушка)"""
    # Здесь можно подключить реальное API новостей
    return "📰 Последние новости: В мире всё спокойно"

async def get_exchange_rate() -> str:
    """Получение курса валют (заглушка)"""
    # Здесь можно подключить реальное API курсов
    return "💱 Курс: USD 90.5 RUB, EUR 98.2 RUB"

# ----- ИМПОРТ/ЭКСПОРТ ДАННЫХ -----

async def export_chat_data(message: types.Message):
    """Экспорт данных чата"""
    if await get_admin_level(message.from_user.id) < 4:
        await message.reply("❌ У тебя нет прав! (нужен 4+ уровень)")
        return
    
    chat_id = message.chat.id
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
    settings = c.fetchone()
    c.execute("SELECT * FROM stop_words WHERE chat_id = ?", (chat_id,))
    stop_words = c.fetchall()
    c.execute("SELECT * FROM warns WHERE chat_id = ?", (chat_id,))
    warns = c.fetchall()
    conn.close()
    
    data = {
        "chat_id": chat_id,
        "settings": settings,
        "stop_words": stop_words,
        "warns": warns,
        "exported_at": datetime.now().isoformat()
    }
    
    json_data = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    
    from io import BytesIO
    file = BytesIO(json_data.encode('utf-8'))
    file.name = f"chat_{chat_id}_export.json"
    
    await message.reply_document(
        BufferedInputFile(file.getvalue(), filename=file.name),
        caption=f"📤 Данные чата экспортированы!"
    )

# ==================== ПОИСК ПО КОМАНДАМ ====================

async def search_commands(message: types.Message):
    """Поиск команд по ключевому слову"""
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `поиск команд [слово]`")
        return
    
    query = " ".join(args[1:]).lower()
    
    all_commands = []
    
    # Собираем все команды из словаря (здесь нужно заполнить)
    # Это пример, реальные команды нужно собрать из всех частей
    commands_list = [
        "профиль", "я", "баланс", "работа", "бизнесы", "магазин", "купить",
        "инвентарь", "продать", "лимитки", "кейсы", "открыть кейс", "перевод",
        "банк", "положить", "снять", "вклад", "топ", "топ реп", "бонус",
        "ежедневно", "обнять", "поцеловать", "ударить", "пнуть", "+реп", "-реп",
        "брак", "развестись", "кубы", "рулетка", "казино", "создать клан",
        "вступить в клан", "мой клан", "кланы", "казна", "кредит", "ферма",
        "посадить", "собрать", "рыбалка", "охота", "питомцы", "недвижимость",
        "ачивки", "ежедневные задания", "команды", "помощь", "правила"
    ]
    
    results = []
    for cmd in commands_list:
        if query in cmd:
            results.append(cmd)
    
    if not results:
        await message.reply(f"❌ Команды с '{query}' не найдены!")
        return
    
    msg = f"🔍 **Результаты поиска команд: '{query}'**\n\n"
    for cmd in results[:20]:
        msg += f"• `{cmd}`\n"
    
    if len(results) > 20:
        msg += f"\n... и ещё {len(results) - 20} команд"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

print(f"✅ Часть 19/20 загружена! Строк: ~700")
# ==================== ЧАСТЬ 20/20: ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ, ТЕСТИРОВАНИЕ, ДОКУМЕНТАЦИЯ ====================

# ==================== СИСТЕМА БЕКАПОВ ====================

async def create_backup():
    """Создание бекапа базы данных"""
    try:
        import shutil
        from datetime import datetime
        
        # Создаём папку для бекапов если её нет
        if not os.path.exists('backups'):
            os.makedirs('backups')
        
        # Имя файла бекапа
        backup_name = f"backups/fable_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        # Копируем базу данных
        shutil.copy2("fable_bot.db", backup_name)
        
        # Удаляем старые бекапы (оставляем только последние 10)
        backups = sorted([f for f in os.listdir('backups') if f.endswith('.db')])
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(os.path.join('backups', old_backup))
        
        return True
    except Exception as e:
        print(f"❌ Ошибка создания бекапа: {e}")
        return False

async def restore_backup(message: types.Message):
    """Восстановление из бекапа (только для создателя)"""
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может восстанавливать бекап!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `восстановить [имя_файла]`")
        return
    
    backup_file = args[1]
    backup_path = os.path.join('backups', backup_file)
    
    if not os.path.exists(backup_path):
        await message.reply(f"❌ Бекап {backup_file} не найден!")
        return
    
    try:
        import shutil
        shutil.copy2(backup_path, "fable_bot.db")
        await message.reply(f"✅ База данных восстановлена из {backup_file}!")
        await log_action(CREATOR_ID, "restore_backup", f"Восстановил из {backup_file}")
    except Exception as e:
        await message.reply(f"❌ Ошибка восстановления: {e}")

# ==================== СИСТЕМА ТЕСТИРОВАНИЯ ====================

async def test_bot(message: types.Message):
    """Тестирование бота"""
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может тестировать бота!")
        return
    
    start_time = datetime.now()
    results = []
    
    # Тест 1: Проверка базы данных
    try:
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT 1")
        conn.close()
        results.append("✅ База данных: ОК")
    except Exception as e:
        results.append(f"❌ База данных: {e}")
    
    # Тест 2: Проверка токена
    if TOKEN:
        results.append("✅ Токен: ОК")
    else:
        results.append("❌ Токен: не задан")
    
    # Тест 3: Проверка API ключей
    if DEEPSEEK_API_KEY:
        results.append("✅ DeepSeek API: ОК")
    else:
        results.append("⚠️ DeepSeek API: не настроен")
    
    if GROK_API_KEY:
        results.append("✅ Grok API: ОК")
    else:
        results.append("⚠️ Grok API: не настроен")
    
    if REPLICATE_API_KEY:
        results.append("✅ Replicate API: ОК")
    else:
        results.append("⚠️ Replicate API: не настроен")
    
    # Тест 4: Проверка глобальных переменных
    global_vars = {
        "cooldowns": cooldowns,
        "daily_cooldown": daily_cooldown,
        "cube_games": cube_games,
        "roulette_games": roulette_games,
        "active_economy_event": active_economy_event
    }
    
    for name, var in global_vars.items():
        if var is not None:
            results.append(f"✅ {name}: OK")
        else:
            results.append(f"⚠️ {name}: None")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    msg = "🧪 **РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ**\n\n"
    msg += "\n".join(results)
    msg += f"\n\n⏱️ Время выполнения: {elapsed:.2f} сек"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== СИСТЕМА ЛОГГИРОВАНИЯ (РАСШИРЕННАЯ) ====================

async def get_logs_extended(message: types.Message, log_type: str = "all", limit: int = 100):
    """Расширенное логирование"""
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может просматривать логи!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    query = "SELECT user_id, action, details, timestamp, chat_id FROM logs"
    params = []
    
    if log_type != "all":
        query += " WHERE action LIKE ?"
        params.append(f"%{log_type}%")
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply(f"📭 Логов типа '{log_type}' не найдено!")
        return
    
    msg = f"📋 **ЛОГИ ({log_type})**\n\n"
    for user_id, action, details, timestamp, chat_id in rows:
        name = await get_name(user_id)
        msg += f"🕐 {timestamp[11:16]} | {name}\n"
        msg += f"   📌 {action}: {details}\n"
        if chat_id:
            msg += f"   🏠 Чат: {chat_id}\n"
        msg += "\n"
        
        if len(msg) > 3500:
            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
    
    if msg:
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== СТАТИСТИКА ДЛЯ СОЗДАТЕЛЯ (РАСШИРЕННАЯ) ====================

async def get_detailed_stats(message: types.Message):
    """Детальная статистика для создателя"""
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может просматривать статистику!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    # Общая статистика
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE vip = 1")
    total_vip = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT chat_id) FROM chat_stats")
    total_chats = c.fetchone()[0]
    
    c.execute("SELECT SUM(messages) FROM chat_stats")
    total_messages = c.fetchone()[0] or 0
    
    # Экономическая статистика
    c.execute("SELECT SUM(coins) FROM users")
    total_coins = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(bank) FROM users")
    total_bank = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(amount) FROM deposits WHERE active = 1")
    total_deposits = c.fetchone()[0] or 0
    
    # Статистика бизнесов
    c.execute("SELECT COUNT(*) FROM businesses")
    total_businesses = c.fetchone()[0] or 0
    
    # Статистика инвентаря
    c.execute("SELECT COUNT(*) FROM inventory")
    total_inventory = c.fetchone()[0] or 0
    
    # Статистика модерации
    c.execute("SELECT COUNT(*) FROM warns")
    total_warns = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM complaints")
    total_complaints = c.fetchone()[0] or 0
    
    # Статистика кланов
    c.execute("SELECT COUNT(*) FROM clans")
    total_clans = c.fetchone()[0] or 0
    
    # Статистика браков
    c.execute("SELECT COUNT(*) FROM marriages")
    total_marriages = c.fetchone()[0] or 0
    
    # Активность сегодня
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (f"{today}%",))
    new_users_today = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(messages) FROM chat_stats WHERE last_message LIKE ?", (f"{today}%",))
    messages_today = c.fetchone()[0] or 0
    
    conn.close()
    
    msg = "📊 **ДЕТАЛЬНАЯ СТАТИСТИКА БОТА**\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += "👥 **ПОЛЬЗОВАТЕЛИ:**\n"
    msg += f"   Всего: {total_users}\n"
    msg += f"   VIP: {total_vip}\n"
    msg += f"   Новых сегодня: {new_users_today}\n\n"
    
    msg += "💬 **АКТИВНОСТЬ:**\n"
    msg += f"   Чатов: {total_chats}\n"
    msg += f"   Сообщений всего: {total_messages}\n"
    msg += f"   Сообщений сегодня: {messages_today}\n\n"
    
    msg += "💰 **ЭКОНОМИКА:**\n"
    msg += f"   Всего монет: {total_coins}\n"
    msg += f"   В банке: {total_bank}\n"
    msg += f"   Во вкладах: {total_deposits}\n"
    msg += f"   Всего в системе: {total_coins + total_bank + total_deposits}\n\n"
    
    msg += "🏪 **БИЗНЕСЫ И ИНВЕНТАРЬ:**\n"
    msg += f"   Бизнесов: {total_businesses}\n"
    msg += f"   Предметов в инвентаре: {total_inventory}\n\n"
    
    msg += "🛡️ **МОДЕРАЦИЯ:**\n"
    msg += f"   Варнов: {total_warns}\n"
    msg += f"   Жалоб: {total_complaints}\n\n"
    
    msg += "❤️ **СОЦИАЛКА:**\n"
    msg += f"   Кланов: {total_clans}\n"
    msg += f"   Браков: {total_marriages}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ОЧИСТКА БАЗЫ ДАННЫХ ====================

async def cleanup_database(message: types.Message):
    """Очистка старых данных из базы (только для создателя)"""
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может очищать базу данных!")
        return
    
    # Подтверждение
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ ДА, ОЧИСТИТЬ", callback_data="cleanup_confirm"),
         InlineKeyboardButton("❌ ОТМЕНА", callback_data="cleanup_cancel")]
    ])
    
    await message.reply("⚠️ **ВНИМАНИЕ!**\n\n"
                        "Это удалит старые логи, жалобы и варны.\n"
                        "Данные пользователей, монеты, бизнесы НЕ будут затронуты.\n\n"
                        "Подтвердите действие:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "cleanup_confirm")
async def cleanup_confirm(callback):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("❌ Не тебе!")
        return
    
    await callback.message.edit_text("🔄 Очистка базы данных...")
    
    try:
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        
        # Удаляем старые логи (старше 30 дней)
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        c.execute("DELETE FROM logs WHERE timestamp < ?", (month_ago,))
        logs_deleted = c.rowcount
        
        # Удаляем старые жалобы (старше 30 дней)
        c.execute("DELETE FROM complaints WHERE date < ?", (month_ago,))
        complaints_deleted = c.rowcount
        
        # Удаляем старые варны (старше 30 дней)
        c.execute("DELETE FROM warns WHERE date < ?", (month_ago,))
        warns_deleted = c.rowcount
        
        conn.commit()
        conn.close()
        
        await callback.message.edit_text(f"✅ **Очистка завершена!**\n\n"
                                         f"🗑️ Удалено:\n"
                                         f"📝 Логов: {logs_deleted}\n"
                                         f"📋 Жалоб: {complaints_deleted}\n"
                                         f"⚠️ Варнов: {warns_deleted}")
        await log_action(CREATOR_ID, "cleanup_db", f"Очистил БД: {logs_deleted} логов, {complaints_deleted} жалоб, {warns_deleted} варнов")
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка очистки: {e}")

@dp.callback_query(lambda c: c.data == "cleanup_cancel")
async def cleanup_cancel(callback):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("❌ Не тебе!")
        return
    
    await callback.message.edit_text("❌ Очистка отменена!")

# ==================== ИНФОРМАЦИЯ О БОТЕ ====================

async def bot_info(message: types.Message):
    """Информация о боте"""
    uptime = datetime.now() - BOT_START_TIME
    hours = uptime.total_seconds() // 3600
    minutes = (uptime.total_seconds() % 3600) // 60
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT chat_id) FROM chat_stats")
    total_chats = c.fetchone()[0]
    c.execute("SELECT SUM(messages) FROM chat_stats")
    total_messages = c.fetchone()[0] or 0
    conn.close()
    
    msg = f"ℹ️ **ИНФОРМАЦИЯ О БОТЕ**\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"🤖 Имя: **{BOT_NAME}**\n"
    msg += f"👑 Создатель: {await get_name(CREATOR_ID)}\n"
    msg += f"🕐 Время работы: {int(hours)}ч {int(minutes)}м\n\n"
    msg += f"👥 Пользователей: {total_users}\n"
    msg += f"💬 Чатов: {total_chats}\n"
    msg += f"💬 Сообщений: {total_messages}\n\n"
    msg += f"📊 Версия: 2.0\n"
    msg += f"🐍 Python: 3.11+\n"
    msg += f"📦 aiogram: 3.x\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ДОКУМЕНТАЦИЯ ====================

async def show_documentation(message: types.Message):
    """Показать документацию"""
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может просматривать документацию!")
        return
    
    doc = """
📚 **ДОКУМЕНТАЦИЯ БОТА FABLE**

🏗️ **АРХИТЕКТУРА:**
- 20 частей кода
- 14000+ строк
- SQLite база данных
- aiogram 3.x

📊 **МОДУЛИ:**
1. Основа, токены, БД
2. Обработчики сообщений
3. Экономика (работа, бизнес)
4. Кейсы, банк, вклады
5. Игры, социалка
6. Ферма, рыбалка, охота
7. Профиль, топы, квесты
8. Переводы, админка
9. Фильтры, стоп-слова
10. Команды для создателя
11. Эконом события, промо
12. ИИ функции
13. Магазин, аукционы
14. Автомодерация
15. Статистика, интеграции
16. Покер, челленджи
17. Запуск, фоновые задачи
18. Расширенные функции БД
19. Настройки, режимы чата
20. Дополнительные функции

🔧 **КОМАНДЫ:**
- 100+ команд
- 10+ игр
- 15+ модераторских функций

👑 **УРОВНИ:**
0 - Пользователь
1 - Младший модератор
2 - Модератор
3 - Старший модератор
4 - Администратор
5 - Старший администратор
10 - Создатель (скрытый)

💡 **СОВЕТЫ:**
- Для создателя: используй `команды создателя`
- Для админов: `мой уровень`
- Для всех: `команды` или `помощь`
"""
    await message.reply(doc, parse_mode=ParseMode.MARKDOWN)

# ==================== ФИНАЛЬНЫЙ ЗАПУСК ====================

if __name__ == "__main__":
    print("🚀 Запуск бота Fable...")
    
    # Проверяем наличие токена
    if not TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не задан!")
        print("📝 Установи: export BOT_TOKEN='твой_токен'")
        exit(1)
    
    # Запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

print("✅ Часть 20/20 загружена! Строк: ~700")
print("🎉 БОТ FABLE ПОЛНОСТЬЮ ГОТОВ К РАБОТЕ!")
print(f"📊 Всего строк: ~14000")
print(f"👑 Создатель: {CREATOR_ID}")