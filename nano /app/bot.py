import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import os
import re
import json
import math
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
BOT_NAME = "Fable"

if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не задан!")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()
CREATOR_ID = 8039111975

# Кулдауны
cooldowns = {}
daily_cooldown = {}
trade_expeditions = {}
cube_games = {}
roulette_games = {}
active_duels = set()
active_knb = set()
knb_choices = {}
rep_cooldown = {}
work_cooldown = {}
inventory_cache = {}
marriage_proposals = {}
bank_rob_cooldown = {}
auction_bids = {}

# ==================== БАЗА ДАННЫХ ====================

def init_db():
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    # Пользователи
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        coins INTEGER DEFAULT 0,
        bank INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        rep INTEGER DEFAULT 0,
        job TEXT,
        city TEXT DEFAULT 'деревня',
        ship INTEGER DEFAULT 0,
        created_at TEXT
    )""")
    
    # Статистика чатов
    c.execute("""CREATE TABLE IF NOT EXISTS chat_stats (
        user_id INTEGER,
        chat_id INTEGER,
        messages INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, chat_id)
    )""")
    
    # Инвентарь
    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER,
        item_name TEXT,
        quantity INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, item_name)
    )""")
    
    # Бизнесы
    c.execute("""CREATE TABLE IF NOT EXISTS businesses (
        user_id INTEGER,
        name TEXT,
        level INTEGER DEFAULT 1,
        bought_at TEXT,
        PRIMARY KEY (user_id, name)
    )""")
    
    # Ресурсные бизнесы (добыча)
    c.execute("""CREATE TABLE IF NOT EXISTS resource_businesses (
        user_id INTEGER,
        name TEXT,
        level INTEGER DEFAULT 1,
        last_collect TEXT,
        PRIMARY KEY (user_id, name)
    )""")
    
    # Улучшения корабля
    c.execute("""CREATE TABLE IF NOT EXISTS ship_upgrades (
        user_id INTEGER,
        upgrade_name TEXT,
        PRIMARY KEY (user_id, upgrade_name)
    )""")
    
    # Браки
    c.execute("""CREATE TABLE IF NOT EXISTS marriages (
        user_id INTEGER PRIMARY KEY,
        spouse_id INTEGER,
        date TEXT
    )""")
    
    # Логи
    c.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TEXT
    )""")
    
    # Лимитные предметы
    c.execute("""CREATE TABLE IF NOT EXISTS limited_items (
        name TEXT PRIMARY KEY,
        total INTEGER,
        left_count INTEGER
    )""")
    
    # Достижения
    c.execute("""CREATE TABLE IF NOT EXISTS user_achievements (
        user_id INTEGER,
        achievement_name TEXT,
        unlocked_at TEXT,
        PRIMARY KEY (user_id, achievement_name)
    )""")
    
    # Дуэли
    c.execute("""CREATE TABLE IF NOT EXISTS duels (
        chat_id INTEGER,
        challenger INTEGER,
        opponent INTEGER,
        turn INTEGER,
        aim_bonus INTEGER,
        message_id INTEGER
    )""")
    
    # Варны
    c.execute("""CREATE TABLE IF NOT EXISTS warns (
        user_id INTEGER,
        chat_id INTEGER,
        count INTEGER,
        reason TEXT,
        date TEXT,
        warned_by INTEGER
    )""")
    
    # Кланы
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
    
    # Кредиты
    c.execute("""CREATE TABLE IF NOT EXISTS loans (
        user_id INTEGER PRIMARY KEY,
        amount INTEGER,
        interest INTEGER,
        taken_at TEXT,
        due_date TEXT,
        paid INTEGER DEFAULT 0
    )""")
    
    # Лотерея
    c.execute("""CREATE TABLE IF NOT EXISTS lottery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tickets INTEGER,
        bought_at TEXT
    )""")
    
    # Аукционы
    c.execute("""CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        item_name TEXT,
        item_quantity INTEGER,
        start_price INTEGER,
        current_bid INTEGER,
        buyer_id INTEGER,
        ends_at TEXT
    )""")
    
    # Ежедневные задания
    c.execute("""CREATE TABLE IF NOT EXISTS daily_quests (
        user_id INTEGER,
        quest_date TEXT,
        quest1 TEXT, quest2 TEXT, quest3 TEXT, quest4 TEXT, quest5 TEXT,
        progress1 INTEGER DEFAULT 0, progress2 INTEGER DEFAULT 0, progress3 INTEGER DEFAULT 0,
        progress4 INTEGER DEFAULT 0, progress5 INTEGER DEFAULT 0,
        completed1 INTEGER DEFAULT 0, completed2 INTEGER DEFAULT 0, completed3 INTEGER DEFAULT 0,
        completed4 INTEGER DEFAULT 0, completed5 INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, quest_date)
    )""")
    
    # Еженедельные задания
    c.execute("""CREATE TABLE IF NOT EXISTS weekly_quests (
        user_id INTEGER,
        quest_week TEXT,
        quest1 TEXT, quest2 TEXT, quest3 TEXT, quest4 TEXT, quest5 TEXT,
        quest6 TEXT, quest7 TEXT, quest8 TEXT, quest9 TEXT, quest10 TEXT,
        progress1 INTEGER DEFAULT 0, progress2 INTEGER DEFAULT 0, progress3 INTEGER DEFAULT 0,
        progress4 INTEGER DEFAULT 0, progress5 INTEGER DEFAULT 0, progress6 INTEGER DEFAULT 0,
        progress7 INTEGER DEFAULT 0, progress8 INTEGER DEFAULT 0, progress9 INTEGER DEFAULT 0,
        progress10 INTEGER DEFAULT 0,
        completed1 INTEGER DEFAULT 0, completed2 INTEGER DEFAULT 0, completed3 INTEGER DEFAULT 0,
        completed4 INTEGER DEFAULT 0, completed5 INTEGER DEFAULT 0, completed6 INTEGER DEFAULT 0,
        completed7 INTEGER DEFAULT 0, completed8 INTEGER DEFAULT 0, completed9 INTEGER DEFAULT 0,
        completed10 INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, quest_week)
    )""")
    
    # Экономические события
    c.execute("""CREATE TABLE IF NOT EXISTS economy_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        multiplier REAL DEFAULT 1.0,
        started_at TEXT,
        ended_at TEXT,
        active INTEGER DEFAULT 0
    )""")
    
    # Акции
    c.execute("""CREATE TABLE IF NOT EXISTS stocks (
        user_id INTEGER,
        company TEXT,
        quantity INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, company)
    )""")
    
    # Недвижимость
    c.execute("""CREATE TABLE IF NOT EXISTS properties (
        user_id INTEGER,
        type TEXT,
        bought_at TEXT,
        PRIMARY KEY (user_id, type)
    )""")
    
    # Ферма
    c.execute("""CREATE TABLE IF NOT EXISTS farm (
        user_id INTEGER,
        crop TEXT,
        planted_at TEXT,
        PRIMARY KEY (user_id, crop)
    )""")
    
    conn.commit()
    conn.close()

def init_limited_items():
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    for name, data in LIMITED_ITEMS.items():
        c.execute("INSERT OR IGNORE INTO limited_items (name, total, left_count) VALUES (?, ?, ?)",
                  (name, data["total"], data["total"]))
    conn.commit()
    conn.close()

init_db()
init_limited_items()

# ==================== JOBS ====================

JOBS = {
    "шахтёр": {"min": 1000, "max": 2000, "emoji": "⛏️", "desc": "Добывает руду в шахте"},
    "рыбак": {"min": 800, "max": 1600, "emoji": "🎣", "desc": "Ловит рыбу в море"},
    "программист": {"min": 1500, "max": 3000, "emoji": "💻", "desc": "Пишет код"},
    "фермер": {"min": 700, "max": 1400, "emoji": "🌾", "desc": "Выращивает овощи"},
    "майнер": {"min": 2000, "max": 4000, "emoji": "⛏️", "desc": "Добывает криптовалюту"},
    "полицейский": {"min": 1200, "max": 2500, "emoji": "👮", "desc": "Охраняет порядок"},
    "врач": {"min": 1500, "max": 3500, "emoji": "🏥", "desc": "Лечит людей"},
    "учитель": {"min": 1000, "max": 2000, "emoji": "📚", "desc": "Учит детей"},
    "строитель": {"min": 1400, "max": 2800, "emoji": "🏗️", "desc": "Строит дома"},
    "водитель": {"min": 1100, "max": 2200, "emoji": "🚕", "desc": "Возит людей"},
    "повар": {"min": 900, "max": 1800, "emoji": "🍳", "desc": "Готовит еду"},
    "дизайнер": {"min": 1300, "max": 2600, "emoji": "🎨", "desc": "Создаёт дизайн"},
    "музыкант": {"min": 1200, "max": 3000, "emoji": "🎵", "desc": "Играет музыку"},
    "атлет": {"min": 1400, "max": 2800, "emoji": "🏋️", "desc": "Занимается спортом"},
    "фотограф": {"min": 1100, "max": 2200, "emoji": "📸", "desc": "Снимает фото"},
    "охотник": {"min": 1300, "max": 2600, "emoji": "🔫", "desc": "Охотится на зверей"},
    "механик": {"min": 1200, "max": 2400, "emoji": "🔧", "desc": "Ремонтирует технику"},
    "бизнесмен": {"min": 1800, "max": 3600, "emoji": "💼", "desc": "Управляет бизнесом"},
    "курьер": {"min": 800, "max": 1600, "emoji": "📦", "desc": "Развозит заказы"},
    "журналист": {"min": 1000, "max": 2000, "emoji": "📰", "desc": "Пишет новости"}
}

# ==================== BUSINESSES ====================

BUSINESSES = {
    "кафе": {"price": 50000, "emoji": "☕", "income": 200, "upgrade_price": 25000, "upgrade_income": 20, "max_level": 10, "desc": "Продаёт кофе и булочки"},
    "магазин": {"price": 80000, "emoji": "🏪", "income": 300, "upgrade_price": 40000, "upgrade_income": 30, "max_level": 10, "desc": "Продаёт товары"},
    "ферма": {"price": 60000, "emoji": "🌾", "income": 250, "upgrade_price": 30000, "upgrade_income": 25, "max_level": 10, "desc": "Выращивает овощи"},
    "шахта": {"price": 100000, "emoji": "⛏️", "income": 400, "upgrade_price": 50000, "upgrade_income": 40, "max_level": 10, "desc": "Добывает руду"},
    "ресторан": {"price": 120000, "emoji": "🍽️", "income": 500, "upgrade_price": 60000, "upgrade_income": 50, "max_level": 10, "desc": "Готовит блюда"},
    "отель": {"price": 150000, "emoji": "🏨", "income": 600, "upgrade_price": 75000, "upgrade_income": 60, "max_level": 10, "desc": "Принимает гостей"},
    "криптоферма": {"price": 200000, "emoji": "💎", "income": 800, "upgrade_price": 100000, "upgrade_income": 80, "max_level": 10, "desc": "Майнит криптовалюту"},
    "студия": {"price": 140000, "emoji": "🎬", "income": 550, "upgrade_price": 70000, "upgrade_income": 55, "max_level": 10, "desc": "Снимает фильмы"},
    "завод": {"price": 250000, "emoji": "🏭", "income": 1000, "upgrade_price": 125000, "upgrade_income": 100, "max_level": 10, "desc": "Производит товары"},
    "клуб": {"price": 300000, "emoji": "🎉", "income": 1200, "upgrade_price": 150000, "upgrade_income": 120, "max_level": 10, "desc": "Ночной клуб с вечеринками"}
}

# ==================== РЕСУРСНЫЕ БИЗНЕСЫ (ДОБЫЧА) ====================

RESOURCE_BUSINESSES = {
    "шахта": {
        "emoji": "⛏️", "price": 50000, "time": 30,
        "resources": {
            "камень": {"price": 50, "chance": 60, "min": 2, "max": 4},
            "золото": {"price": 200, "chance": 30, "min": 1, "max": 2},
            "алмаз": {"price": 500, "chance": 10, "min": 1, "max": 1}
        }
    },
    "лесопилка": {
        "emoji": "🌲", "price": 40000, "time": 45,
        "resources": {
            "древесина": {"price": 30, "chance": 70, "min": 3, "max": 5},
            "доски": {"price": 100, "chance": 30, "min": 2, "max": 3}
        }
    },
    "ферма": {
        "emoji": "🌾", "price": 30000, "time": 60,
        "resources": {
            "пшеница": {"price": 40, "chance": 50, "min": 3, "max": 6},
            "морковь": {"price": 60, "chance": 30, "min": 2, "max": 4},
            "яблоки": {"price": 80, "chance": 20, "min": 1, "max": 3}
        }
    },
    "скотоводство": {
        "emoji": "🐄", "price": 45000, "time": 60,
        "resources": {
            "мясо": {"price": 150, "chance": 50, "min": 2, "max": 4},
            "масло": {"price": 200, "chance": 30, "min": 1, "max": 3},
            "сыр": {"price": 250, "chance": 20, "min": 1, "max": 2}
        }
    },
    "рыболовная база": {
        "emoji": "🎣", "price": 35000, "time": 30,
        "resources": {
            "рыба": {"price": 100, "chance": 70, "min": 2, "max": 4},
            "креветки": {"price": 300, "chance": 30, "min": 1, "max": 2}
        }
    },
    "завод": {
        "emoji": "🏭", "price": 60000, "time": 60,
        "resources": {
            "металл": {"price": 200, "chance": 60, "min": 2, "max": 4},
            "детали": {"price": 350, "chance": 40, "min": 1, "max": 3}
        }
    },
    "копи": {
        "emoji": "💎", "price": 70000, "time": 120,
        "resources": {
            "алмаз": {"price": 500, "chance": 60, "min": 1, "max": 2},
            "сапфир": {"price": 700, "chance": 40, "min": 1, "max": 1}
        }
    },
    "плантация": {
        "emoji": "🌿", "price": 55000, "time": 90,
        "resources": {
            "кофе": {"price": 150, "chance": 40, "min": 2, "max": 4},
            "какао": {"price": 200, "chance": 30, "min": 1, "max": 3},
            "трава": {"price": 80, "chance": 30, "min": 2, "max": 4}
        }
    },
    "карьер": {
        "emoji": "🪨", "price": 25000, "time": 20,
        "resources": {
            "камень": {"price": 50, "chance": 70, "min": 2, "max": 4},
            "глина": {"price": 70, "chance": 30, "min": 1, "max": 3}
        }
    },
    "пасека": {
        "emoji": "🐝", "price": 20000, "time": 60,
        "resources": {
            "мёд": {"price": 200, "chance": 70, "min": 2, "max": 4},
            "воск": {"price": 150, "chance": 30, "min": 1, "max": 3}
        }
    }
}

# ==================== LIMITED ITEMS ====================

LIMITED_ITEMS = {
    "кольцо тутанхамона": {"emoji": "💍", "total": 5, "left": 5, "rarity": "🟣 РЕДКИЙ", "effect": "удача", "bonus": 5, "desc": "+5% удачи НАВСЕГДА", "price": 15000},
    "амфора счастья": {"emoji": "🏺", "total": 5, "left": 5, "rarity": "🟣 РЕДКИЙ", "effect": "доход", "bonus": 3, "desc": "+3% ко всем доходам НАВСЕГДА", "price": 20000},
    "чётки будды": {"emoji": "📿", "total": 5, "left": 5, "rarity": "🟠 ЭПИЧЕСКИЙ", "effect": "торговля", "bonus": 10, "desc": "+10% в торговле НАВСЕГДА", "price": 30000},
    "меч саладина": {"emoji": "⚔️", "total": 5, "left": 5, "rarity": "🟠 ЭПИЧЕСКИЙ", "effect": "дуэль", "bonus": 8, "desc": "+8% в дуэлях НАВСЕГДА", "price": 25000},
    "щит спартанца": {"emoji": "🛡️", "total": 5, "left": 5, "rarity": "🟠 ЭПИЧЕСКИЙ", "effect": "защита", "bonus": 10, "desc": "-10% потерь при грабеже НАВСЕГДА", "price": 35000},
    "корона карла": {"emoji": "👑", "total": 4, "left": 4, "rarity": "🟣 РЕДКИЙ", "effect": "доход", "bonus": 2, "desc": "+2% ко всем доходам НАВСЕГДА", "price": 10000},
    "свиток мёртвого моря": {"emoji": "📜", "total": 4, "left": 4, "rarity": "🟣 РЕДКИЙ", "effect": "опыт", "bonus": 5, "desc": "+5% опыта НАВСЕГДА", "price": 18000},
    "кинжал цезаря": {"emoji": "🗡️", "total": 3, "left": 3, "rarity": "🔴 ЛЕГЕНДАРНЫЙ", "effect": "pvp", "bonus": 15, "desc": "+15% в PvP НАВСЕГДА", "price": 50000},
    "глаз гора": {"emoji": "🧿", "total": 3, "left": 3, "rarity": "🔴 ЛЕГЕНДАРНЫЙ", "effect": "удача", "bonus": 10, "desc": "+10% удачи НАВСЕГДА", "price": 40000},
    "маска царя": {"emoji": "🎭", "total": 2, "left": 2, "rarity": "🌟 МИФИЧЕСКИЙ", "effect": "скрытность", "bonus": 20, "desc": "+20% скрытность (нельзя ограбить) НАВСЕГДА", "price": 80000}
}

# ==================== SHOP ITEMS ====================

SHOP_ITEMS = {
    "улучшенная кирка": {"price": 50000, "category": "рабочие", "job": "шахтёр", "bonus": 10},
    "профессиональная удочка": {"price": 40000, "category": "рабочие", "job": "рыбак", "bonus": 10},
    "тренировочное ружьё": {"price": 60000, "category": "рабочие", "job": "охотник", "bonus": 10},
    "мощный пк": {"price": 80000, "category": "рабочие", "job": "программист", "bonus": 10},
    "трактор": {"price": 70000, "category": "рабочие", "job": "фермер", "bonus": 10},
    "строительная техника": {"price": 90000, "category": "рабочие", "job": "строитель", "bonus": 10},
    "диплом": {"price": 30000, "category": "рабочие", "job": "все", "bonus": 10},
    "деловой костюм": {"price": 25000, "category": "рабочие", "job": "бизнесмен", "bonus": 10},
    "щит": {"price": 3000, "category": "защита", "bonus": 5},
    "каска": {"price": 2000, "category": "защита", "bonus": 3},
    "бронежилет": {"price": 5000, "category": "защита", "bonus": 10},
    "амулет удачи": {"price": 8000, "category": "защита", "bonus": 3},
    "золотая монета": {"price": 1000, "category": "финансы", "bonus": 2},
    "драгоценный камень": {"price": 5000, "category": "финансы", "bonus": 5}
}

# ==================== SHIP UPGRADES ====================

SHIP_UPGRADES = {
    "паруса": {"price": 50000, "effect": "speed", "bonus": 10, "emoji": "⛵", "desc": "-10% времени пути"},
    "карта": {"price": 10000, "effect": "risk", "bonus": 5, "emoji": "🗺️", "desc": "-5% риск"},
    "компас": {"price": 15000, "effect": "risk", "bonus": 5, "emoji": "🧭", "desc": "-5% риск"},
    "радар": {"price": 20000, "effect": "risk", "bonus": 5, "emoji": "📡", "desc": "-5% риск"},
    "бронированный корабль": {"price": 80000, "effect": "defense", "bonus": 40, "emoji": "🛡️", "desc": "+40% защита от пиратов, +30% риск утонуть"}
}

# ==================== ITEM EMOJIS ====================

ITEM_EMOJIS = {
    "камень": "🪨", "золото": "🪙", "алмаз": "💎", "древесина": "🪵", "доски": "📦",
    "пшеница": "🌾", "морковь": "🥕", "яблоки": "🍎", "мясо": "🥩", "масло": "🧈",
    "сыр": "🧀", "рыба": "🐟", "креветки": "🦐", "металл": "🔩", "детали": "⚙️",
    "сапфир": "🔮", "кофе": "☕", "какао": "🍫", "трава": "🌿", "глина": "🧱",
    "мёд": "🍯", "воск": "🕯️", "щит": "🛡️", "каска": "⛑️", "бронежилет": "🦺",
    "амулет удачи": "🍀", "золотая монета": "💰", "драгоценный камень": "💎",
    "улучшенная кирка": "⛏️", "профессиональная удочка": "🎣", "тренировочное ружьё": "🔫",
    "мощный пк": "💻", "трактор": "🚜", "строительная техника": "🏗️", "диплом": "🎓",
    "деловой костюм": "👔"
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

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
    c.execute("INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)",
              (user_id, username, datetime.now().isoformat()))
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
    conn.commit()
    conn.close()

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

async def get_level(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT level, exp FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (1, 0)

async def add_exp(user_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET exp = exp + ? WHERE user_id = ?", (amount, user_id))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (user_id, exp) VALUES (?, ?)", (user_id, amount))
    conn.commit()
    conn.close()

async def get_inventory(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

async def add_item(user_id, item_name, quantity=1):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?",
              (user_id, item_name, quantity, quantity))
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

async def has_item(user_id, item_name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

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

async def get_businesses(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT name, level, bought_at FROM businesses WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

async def get_business(user_id, name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT level, bought_at FROM businesses WHERE user_id = ? AND name = ?", (user_id, name))
    row = c.fetchone()
    conn.close()
    return row

async def create_business(user_id, name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO businesses (user_id, name, bought_at) VALUES (?, ?, ?)",
              (user_id, name, datetime.now().isoformat()))
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

async def get_user_city(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT city FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "деревня"

async def set_user_city(user_id, city):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET city = ? WHERE user_id = ?", (city, user_id))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (user_id, city) VALUES (?, ?)", (user_id, city))
    conn.commit()
    conn.close()

async def get_ship_upgrades(user_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT upgrade_name FROM ship_upgrades WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

async def add_ship_upgrade(user_id, upgrade_name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO ship_upgrades (user_id, upgrade_name) VALUES (?, ?)",
              (user_id, upgrade_name))
    conn.commit()
    conn.close()

async def get_ship_stats(user_id):
    upgrades = await get_ship_upgrades(user_id)
    stats = {"speed": 0, "risk": 0, "defense": 0}
    for upgrade in upgrades:
        data = SHIP_UPGRADES.get(upgrade)
        if data:
            if data["effect"] == "speed":
                stats["speed"] += data["bonus"]
            elif data["effect"] == "risk":
                stats["risk"] += data["bonus"]
            elif data["effect"] == "defense":
                stats["defense"] += data["bonus"]
    return stats

async def get_name(user_id):
    try:
        user = await bot.get_chat(user_id)
        return f"@{user.username}" if user.username else user.first_name
    except:
        return f"id{user_id}"

async def log_action(user_id, action, details):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, action, details, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    try:
        await bot.send_message(CREATOR_ID, f"📋 **ЛОГ**\n👤 {await get_name(user_id)}\n📌 {action}\n📝 {details}\n🕐 {datetime.now().strftime('%H:%M:%S')}")
    except:
        pass

def get_item_emoji(item_name):
    return ITEM_EMOJIS.get(item_name, "📦")

def get_item_price(item_name):
    for shop_name, data in SHOP_ITEMS.items():
        if shop_name == item_name:
            return data.get("price", 0)
    for limited_name, data in LIMITED_ITEMS.items():
        if limited_name == item_name:
            return data.get("price", 0)
    return None

async def check_cooldown(user_id, action, seconds):
    key = f"{action}_{user_id}"
    if key in cooldowns:
        elapsed = (datetime.now() - cooldowns[key]).total_seconds()
        if elapsed < seconds:
            return False, int(seconds - elapsed)
    cooldowns[key] = datetime.now()
    return True, 0

# ==================== ПРОФИЛЬ ====================

async def show_profile(message, target_id):
    user = await get_user(target_id)
    if not user:
        await message.reply("❌ Пользователь не найден!")
        return
    
    level, exp = await get_level(target_id)
    coins = await get_coins(target_id)
    bank = await get_bank(target_id)
    job = await get_job(target_id)
    rep = await get_rep(target_id)
    city = await get_user_city(target_id)
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT SUM(messages) FROM chat_stats WHERE user_id = ?", (target_id,))
    total_messages = c.fetchone()[0] or 0
    conn.close()
    
    businesses = await get_businesses(target_id)
    inventory = await get_inventory(target_id)
    spouse = await get_marriage(target_id)
    spouse_name = await get_name(spouse) if spouse else "Нет"
    
    exp_needed = level * 100
    exp_progress = int((exp / exp_needed) * 20)
    exp_bar = "█" * exp_progress + "░" * (20 - exp_progress)
    
    msg = f"👤 **Профиль {await get_name(target_id)}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 Уровень: **{level}**\n"
    msg += f"📈 Опыт: {exp_bar} {exp}/{exp_needed}\n"
    msg += f"💰 Монет: **{coins}**\n"
    msg += f"🏦 В банке: **{bank}**\n"
    msg += f"⭐ Репутация: **{rep}**\n"
    msg += f"📝 Сообщений: **{total_messages}**\n"
    msg += f"🏙️ Город: **{city.capitalize()}**\n\n"
    
    if job:
        job_data = JOBS.get(job, {})
        msg += f"💼 Работа: **{job.capitalize()}** {job_data.get('emoji', '')}\n"
    else:
        msg += f"💼 Работа: **Нет**\n"
    
    msg += f"💍 Брак: **{spouse_name}**\n"
    msg += f"🏪 Бизнесов: **{len(businesses)}**\n"
    msg += f"🎒 Предметов: **{len(inventory)}**\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== КОМАНДЫ ====================

async def show_commands(message):
    msg = f"""
📋 **ВСЕ КОМАНДЫ БОТА {BOT_NAME}**

━━━━━━━━━━━━━━━━━━━━

👤 **ПРОФИЛЬ**
• `я` или `профиль` — свой профиль
• `я @user` или `профиль @user` — профиль пользователя
• `кто ты` (ответ на сообщение) — профиль того, кому ответил
• `баланс` — монеты и банк

💼 **РАБОТА**
• `список работ` — все работы
• `устроиться [работа]` — устроиться на работу
• `работа` — работать (КД 10 мин)

🏪 **БИЗНЕСЫ**
• `бизнесы` — список бизнесов
• `купить бизнес [название]` — купить бизнес
• `мои бизнесы` — свои бизнесы (с кнопками)
• `улучшить бизнес [название]` — улучшить бизнес

🪨 **РЕСУРСЫ (ДОБЫЧА)**
• `бизнесы ресурсы` — список ресурсных бизнесов
• `добыть [бизнес]` — добыть ресурсы
• `собрать ресурсы` — собрать все добытые ресурсы

⛵ **КОРАБЛЬ**
• `улучшения` — список улучшений
• `купить улучшение [название]` — купить улучшение
• `мой корабль` — состояние корабля

🛒 **МАГАЗИН**
• `магазин` — список товаров
• `купить [предмет]` — купить предмет
• `инвентарь` — свои предметы

🔥 **ЛИМИТКИ**
• `лимитки` — список лимитных предметов
• `лимитка [название]` — информация о предмете

🎭 **РП КОМАНДЫ**
• `обнять`, `поцеловать`, `ударить`, `пнуть`
• (ответь на сообщение)

💍 **БРАК**
• `брак` (ответ на сообщение) — предложить брак
• `развестись` — развод

⭐ **РЕПУТАЦИЯ**
• `+реп` (ответ на сообщение) — повысить репутацию
• `-реп` (ответ на сообщение) — понизить репутацию

📊 **ТОПЫ**
• `топ` — топ богачей
• `топ реп` — топ репутации

💰 **БАНК**
• `положить [сумма]` — положить в банк
• `снять [сумма]` — снять из банка

🎁 **БОНУСЫ**
• `бонус` или `ежедневно` — ежедневный бонус

📤 **ПЕРЕВОДЫ**
• `перевод @user [сумма]` — перевести монеты

🏆 **ДОСТИЖЕНИЯ**
• `ачивки` — свои достижения
• `все ачивки` — все достижения

🎮 **ИГРЫ**
• `кубы` (ответ на сообщение) — игра в кости
• `кубы 2` (ответ на сообщение) — 2 кости
• `рулетка` (ответ на сообщение) — русская рулетка

🏰 **КЛАНЫ**
• `создать клан [название]` — создать клан
• `вступить в клан [название]` — вступить в клан
• `мой клан` — информация о клане
• `кланы` — список кланов
• `казна [положить/снять] [сумма]` — управление казной

💳 **КРЕДИТЫ**
• `кредит взять [сумма]` — взять кредит
• `кредит погасить` — погасить кредит
• `кредит мои` — информация о кредите

🎲 **ЛОТЕРЕЯ**
• `лотерея купить [количество]` — купить билеты
• `лотерея мои` — мои билеты
• `лотерея розыгрыш` — провести розыгрыш

📈 **ФОНДОВЫЙ РЫНОК**
• `рынок` — список компаний
• `купить акции [компания] [количество]` — купить акции
• `продать акции [компания] [количество]` — продать акции
• `мой портфель` — мои акции

🏠 **НЕДВИЖИМОСТЬ**
• `недвижимость` — список недвижимости
• `купить дом` — купить дом
• `купить квартиру` — купить квартиру
• `моя недвижимость` — моя недвижимость

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

🏆 **ТУРНИРЫ**
• `турнир` — участвовать в турнире
• `топ турниров` — лучшие игроки

📋 **ЕЖЕДНЕВНЫЕ ЗАДАНИЯ**
• `ежедневные задания` — показать задания
• `еженедельные задания` — показать задания

━━━━━━━━━━━━━━━━━━━━
"""
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def work_command(message):
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
    
    bonus = 0
    if await has_item(user_id, "диплом"):
        bonus += 10
    if await has_item(user_id, "деловой костюм") and job == "бизнесмен":
        bonus += 10
    if await has_item(user_id, "улучшенная кирка") and job == "шахтёр":
        bonus += 10
    if await has_item(user_id, "профессиональная удочка") and job == "рыбак":
        bonus += 10
    if await has_item(user_id, "тренировочное ружьё") and job == "охотник":
        bonus += 10
    if await has_item(user_id, "мощный пк") and job == "программист":
        bonus += 10
    if await has_item(user_id, "трактор") and job == "фермер":
        bonus += 10
    if await has_item(user_id, "строительная техника") and job == "строитель":
        bonus += 10
    
    salary = random.randint(job_data["min"], job_data["max"])
    salary = int(salary * (1 + bonus / 100))
    
    await add_coins(user_id, salary)
    await add_exp(user_id, 5)
    await log_action(user_id, "work", f"Заработал {salary} монет на работе {job}")
    
    msg = f"{job_data['emoji']} **{job.capitalize()}**: +{salary} монет"
    if bonus > 0:
        msg += f" (бонус +{bonus}%)"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def hire_command(message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `устроиться [работа]`\n📝 Список: `список работ`")
        return
    
    job_name = args[1].lower().strip()
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

async def list_jobs(message):
    msg = "💼 **Доступные работы:**\n\n"
    for job, data in JOBS.items():
        msg += f"{data['emoji']} **{job.capitalize()}** — {data['desc']}\n"
        msg += f"   💰 {data['min']}-{data['max']} монет\n\n"
    msg += "📝 `устроиться [работа]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def transfer_command(message):
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
        member = await message.chat.get_member(target_username)
        target_id = member.user.id
        
        if target_id == user_id:
            await message.reply("❌ Нельзя перевести себе!")
            return
        
        await remove_coins(user_id, amount)
        await add_coins(target_id, amount)
        await log_action(user_id, "transfer", f"Перевёл {amount} монет {await get_name(target_id)}")
        await message.reply(f"💰 {await get_name(user_id)} перевёл **{amount}** монет {await get_name(target_id)}")
    except:
        await message.reply("❌ Пользователь не найден!")

async def daily_bonus(message):
    user_id = message.from_user.id
    if user_id in daily_cooldown:
        elapsed = (datetime.now() - daily_cooldown[user_id]).total_seconds()
        if elapsed < 86400:
            remaining = int(86400 - elapsed)
            await message.reply(f"⏳ Через {remaining//3600}ч {(remaining%3600)//60}м")
            return
    
    bonus = 100 + (await get_level(user_id))[0] * 10
    await add_coins(user_id, bonus)
    daily_cooldown[user_id] = datetime.now()
    await message.reply(f"🎁 Ежедневный бонус: +{bonus} монет!")

async def deposit_command(message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `положить [сумма]`")
        return
    
    try:
        amount = int(args[1])
        if amount <= 0:
            await message.reply("❌ > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return
    
    user_id = message.from_user.id
    if await get_coins(user_id) < amount:
        await message.reply("❌ Мало монет!")
        return
    
    await remove_coins(user_id, amount)
    await add_bank(user_id, amount)
    await message.reply(f"🏦 +{amount} монет в банк!")

async def withdraw_command(message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `снять [сумма]`")
        return
    
    try:
        amount = int(args[1])
        if amount <= 0:
            await message.reply("❌ > 0!")
            return
    except:
        await message.reply("❌ Введи число!")
        return
    
    user_id = message.from_user.id
    if await get_bank(user_id) < amount:
        await message.reply("❌ Мало в банке!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET bank = bank - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    await add_coins(user_id, amount)
    await message.reply(f"🏦 -{amount} монет из банка!")

async def top_command(message):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, coins FROM users ORDER BY coins DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Пусто!")
        return
    
    msg = "💰 **ТОП БОГАЧЕЙ**\n\n"
    for i, (uid, coins) in enumerate(rows, 1):
        name = await get_name(uid)
        msg += f"{i}. {name} — **{coins}** монет\n"
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
    
    msg = "⭐ **ТОП РЕПУТАЦИИ**\n\n"
    for i, (uid, rep) in enumerate(rows, 1):
        name = await get_name(uid)
        msg += f"{i}. {name} — **{rep}**\n"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def show_inventory(message):
    user_id = message.from_user.id
    items = await get_inventory(user_id)
    
    if not items:
        await message.reply("🎒 **Инвентарь пуст!**")
        return
    
    msg = "🎒 **ИНВЕНТАРЬ**\n\n"
    total = 0
    for item, qty in items:
        emoji = get_item_emoji(item)
        price = get_item_price(item)
        if price:
            msg += f"{emoji} **{item.capitalize()}** — {qty} шт (💰 {price} монет)\n"
        else:
            msg += f"{emoji} **{item.capitalize()}** — {qty} шт\n"
        total += qty
    
    msg += f"\n📊 Всего предметов: **{total}**"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def show_shop(message):
    msg = "🛒 **МАГАЗИН**\n\n"
    
    msg += "🛠️ **РАБОЧИЕ**\n"
    for name, data in SHOP_ITEMS.items():
        if data.get("category") == "рабочие":
            emoji = get_item_emoji(name)
            job_name = data.get("job", "все")
            msg += f"{emoji} {name.capitalize()} — {data['price']} монет ({job_name})\n"
    msg += "\n"
    
    msg += "🛡️ **ЗАЩИТА**\n"
    for name, data in SHOP_ITEMS.items():
        if data.get("category") == "защита":
            emoji = get_item_emoji(name)
            msg += f"{emoji} {name.capitalize()} — {data['price']} монет\n"
    msg += "\n"
    
    msg += "💰 **ФИНАНСЫ**\n"
    for name, data in SHOP_ITEMS.items():
        if data.get("category") == "финансы":
            emoji = get_item_emoji(name)
            msg += f"{emoji} {name.capitalize()} — {data['price']} монет\n"
    
    msg += "\n📝 `купить [предмет]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def buy_item(message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `купить [предмет]`")
        return
    
    item_name = args[1].lower().strip()
    
    shop_item = SHOP_ITEMS.get(item_name)
    if not shop_item:
        limited = LIMITED_ITEMS.get(item_name)
        if not limited:
            await message.reply(f"❌ Предмет '{item_name}' не найден!\n📝 Список: `магазин`")
            return
        
        if limited["left"] <= 0:
            await message.reply(f"❌ {limited['emoji']} {item_name.capitalize()} разобрали!")
            return
        
        price = limited["price"]
        if await get_coins(user_id) < price:
            await message.reply(f"❌ Нужно {price} монет!")
            return
        
        await remove_coins(user_id, price)
        await add_item(user_id, item_name)
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("UPDATE limited_items SET left_count = left_count - 1 WHERE name = ?", (item_name,))
        conn.commit()
        conn.close()
        LIMITED_ITEMS[item_name]["left"] -= 1
        
        await log_action(user_id, "buy_limited", f"Купил {item_name} ({LIMITED_ITEMS[item_name]['left']+1}/{LIMITED_ITEMS[item_name]['total']})")
        await message.reply(f"✅ {limited['emoji']} **{item_name.capitalize()}** куплен!\n📦 Осталось: {LIMITED_ITEMS[item_name]['left']}/{LIMITED_ITEMS[item_name]['total']}")
        return
    
    price = shop_item["price"]
    if await get_coins(user_id) < price:
        await message.reply(f"❌ Нужно {price} монет!")
        return
    
    await remove_coins(user_id, price)
    await add_item(user_id, item_name)
    await log_action(user_id, "buy_item", f"Купил {item_name} за {price}")
    await message.reply(f"✅ **{item_name.capitalize()}** куплен!")

async def list_businesses(message):
    msg = "🏪 **ДОСТУПНЫЕ БИЗНЕСЫ**\n\n"
    for name, data in BUSINESSES.items():
        msg += f"{data['emoji']} **{name.capitalize()}**\n"
        msg += f"💰 {data['price']} монет\n"
        msg += f"📈 Доход: {data['income']} монет/час\n\n"
    msg += "📝 `купить бизнес [название]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def buy_business(message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `купить бизнес [название]`")
        return
    
    name = args[1].lower().strip()
    if name not in BUSINESSES:
        await message.reply(f"❌ Бизнес '{name}' не найден!")
        return
    
    if await get_business(user_id, name):
        await message.reply(f"❌ У тебя уже есть {BUSINESSES[name]['emoji']} {name.capitalize()}!")
        return
    
    price = BUSINESSES[name]["price"]
    if await get_coins(user_id) < price:
        await message.reply(f"❌ Нужно {price} монет!")
        return
    
    await remove_coins(user_id, price)
    await create_business(user_id, name)
    await log_action(user_id, "buy_business", f"Купил бизнес {name}")
    await message.reply(f"✅ {BUSINESSES[name]['emoji']} **{name.capitalize()}** куплен!")

# ==================== МОИ БИЗНЕСЫ С КНОПКАМИ ====================

async def my_businesses_command(message):
    user_id = message.from_user.id
    businesses = await get_businesses(user_id)
    
    if not businesses:
        await message.reply("❌ У тебя нет бизнесов!\n📝 `купить бизнес [название]`")
        return
    
    # Создаём кнопки для каждого бизнеса
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for name, level, bought_at in businesses:
        data = BUSINESSES.get(name)
        if data:
            income = data["income"] + (level - 1) * data["upgrade_income"]
            btn_text = f"{data['emoji']} {name.capitalize()} (ур.{level}) — {income} монет/час"
            keyboard.add(InlineKeyboardButton(btn_text, callback_data=f"biz_{name}"))
    
    # Кнопка "Собрать все ресурсы"
    keyboard.add(InlineKeyboardButton("📦 Собрать все ресурсы", callback_data="collect_all_resources"))
    keyboard.add(InlineKeyboardButton("🔄 Обновить", callback_data="refresh_businesses"))
    
    msg = "🏪 **МОИ БИЗНЕСЫ**\n\n"
    msg += f"Всего бизнесов: **{len(businesses)}**\n"
    msg += "Нажми на бизнес для управления ⬇️"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

# ==================== КОЛБЭКИ ДЛЯ БИЗНЕСОВ ====================

@dp.callback_query(lambda c: c.data.startswith("biz_"))
async def business_callback(callback):
    business_name = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    # Получаем данные бизнеса
    business = await get_business(user_id, business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    level = business[0]
    data = BUSINESSES.get(business_name)
    income = data["income"] + (level - 1) * data["upgrade_income"]
    
    # Кнопки управления бизнесом
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 Статистика", callback_data=f"biz_stat_{business_name}"),
        InlineKeyboardButton("🔧 Улучшить", callback_data=f"biz_upgrade_{business_name}")
    )
    keyboard.add(
        InlineKeyboardButton("💰 Собрать доход", callback_data=f"biz_collect_{business_name}"),
        InlineKeyboardButton("📦 Ресурсы", callback_data=f"biz_resources_{business_name}")
    )
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_businesses"))
    
    msg = f"🏪 **{data['emoji']} {business_name.capitalize()}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 Уровень: **{level}/{data['max_level']}**\n"
    msg += f"💰 Доход: **{income}** монет/час\n"
    msg += f"🔧 Улучшение: {data['upgrade_price'] * level} монет\n"
    msg += f"📝 {data['desc']}"
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("biz_upgrade_"))
async def business_upgrade_callback(callback):
    business_name = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    business = await get_business(user_id, business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    level = business[0]
    data = BUSINESSES.get(business_name)
    
    if level >= data["max_level"]:
        await callback.answer("✅ Уже максимальный уровень!", show_alert=True)
        return
    
    price = data["upgrade_price"] * level
    coins = await get_coins(user_id)
    
    if coins < price:
        await callback.answer(f"❌ Нужно {price} монет!", show_alert=True)
        return
    
    await remove_coins(user_id, price)
    new_level = await upgrade_business(user_id, business_name)
    await log_action(user_id, "upgrade_business", f"Улучшил {business_name} до {new_level}")
    
    await callback.answer(f"✅ Улучшен до {new_level} уровня!", show_alert=True)
    
    # Обновляем сообщение
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 Статистика", callback_data=f"biz_stat_{business_name}"),
        InlineKeyboardButton("🔧 Улучшить", callback_data=f"biz_upgrade_{business_name}")
    )
    keyboard.add(
        InlineKeyboardButton("💰 Собрать доход", callback_data=f"biz_collect_{business_name}"),
        InlineKeyboardButton("📦 Ресурсы", callback_data=f"biz_resources_{business_name}")
    )
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_businesses"))
    
    new_income = data["income"] + (new_level - 1) * data["upgrade_income"]
    msg = f"🏪 **{data['emoji']} {business_name.capitalize()}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 Уровень: **{new_level}/{data['max_level']}**\n"
    msg += f"💰 Доход: **{new_income}** монет/час\n"
    msg += f"🔧 Улучшение: {data['upgrade_price'] * new_level} монет\n"
    msg += f"📝 {data['desc']}"
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("biz_collect_"))
async def business_collect_callback(callback):
    business_name = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    # Проверяем бизнес
    business = await get_business(user_id, business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    level = business[0]
    data = BUSINESSES.get(business_name)
    income = data["income"] + (level - 1) * data["upgrade_income"]
    
    # Рандомный доход за час
    earned = random.randint(income // 2, income)
    await add_coins(user_id, earned)
    await log_action(user_id, "collect_business", f"Собрал {earned} монет с {business_name}")
    
    await callback.answer(f"💰 +{earned} монет!", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("biz_resources_"))
async def business_resources_callback(callback):
    business_name = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    # Проверяем бизнес
    business = await get_business(user_id, business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    # Проверяем ресурсный бизнес
    if business_name not in RESOURCE_BUSINESSES:
        await callback.answer("❌ Этот бизнес не добывает ресурсы!", show_alert=True)
        return
    
    level = business[0]
    data = RESOURCE_BUSINESSES[business_name]
    
    # Проверяем КД
    ok, remaining = await check_cooldown(user_id, f"mine_{business_name}", data["time"] * 60)
    if not ok:
        await callback.answer(f"⏳ Подожди {remaining//60} мин {remaining%60} сек!", show_alert=True)
        return
    
    # Добываем ресурсы
    available = []
    for res, res_data in data["resources"].items():
        if random.randint(1, 100) <= res_data["chance"]:
            min_amt = res_data["min"] + (level // 3)
            max_amt = res_data["max"] + (level // 2)
            amount = random.randint(min_amt, max_amt)
            available.append({"name": res, "amount": amount, "price": res_data["price"]})
    
    if not available:
        await callback.answer("❌ Ничего не добыто!", show_alert=True)
        return
    
    # Добавляем ресурсы в инвентарь
    msg = f"{data['emoji']} **{business_name.capitalize()}**\n"
    msg += "📦 **ДОБЫЧА:**\n\n"
    total_value = 0
    for res in available:
        await add_item(user_id, res["name"], res["amount"])
        total = res["amount"] * res["price"]
        total_value += total
        emoji = get_item_emoji(res["name"])
        msg += f"{emoji} {res['name'].capitalize()}: **{res['amount']}** шт (💰 {total} монет)\n"
    
    msg += f"\n💎 Общая стоимость: **{total_value}** монет"
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "collect_all_resources")
async def collect_all_resources_callback(callback):
    user_id = callback.from_user.id
    businesses = await get_businesses(user_id)
    
    total_resources = []
    for name, level, bought_at in businesses:
        if name in RESOURCE_BUSINESSES:
            data = RESOURCE_BUSINESSES[name]
            ok, remaining = await check_cooldown(user_id, f"mine_{name}", data["time"] * 60)
            if ok:
                available = []
                for res, res_data in data["resources"].items():
                    if random.randint(1, 100) <= res_data["chance"]:
                        min_amt = res_data["min"] + (level // 3)
                        max_amt = res_data["max"] + (level // 2)
                        amount = random.randint(min_amt, max_amt)
                        available.append({"name": res, "amount": amount, "price": res_data["price"]})
                
                if available:
                    for res in available:
                        await add_item(user_id, res["name"], res["amount"])
                        total_resources.append(f"{get_item_emoji(res['name'])} {res['name']}: +{res['amount']} шт")
    
    if not total_resources:
        await callback.answer("❌ Ничего не добыто! Попробуй позже.", show_alert=True)
        return
    
    msg = "📦 **СОБРАНО РЕСУРСОВ**\n\n"
    msg += "\n".join(total_resources)
    await callback.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_businesses")
async def back_to_businesses_callback(callback):
    await my_businesses_command(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "refresh_businesses")
async def refresh_businesses_callback(callback):
    await my_businesses_command(callback.message)
    await callback.answer("🔄 Обновлено!")

# ==================== РЕСУРСНЫЕ БИЗНЕСЫ ====================

async def list_resource_businesses(message):
    msg = "🏪 **РЕСУРСНЫЕ БИЗНЕСЫ**\n\n"
    for name, data in RESOURCE_BUSINESSES.items():
        msg += f"{data['emoji']} **{name.capitalize()}**\n"
        msg += f"💰 Цена: {data['price']} монет\n"
        msg += f"⏰ Время: {data['time']} мин\n"
        msg += f"📦 Ресурсы:\n"
        for res, res_data in data["resources"].items():
            emoji = get_item_emoji(res)
            msg += f"   • {emoji} {res.capitalize()} — {res_data['price']} монет ({res_data['chance']}%)\n"
        msg += "\n"
    msg += "📝 `добыть [бизнес]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def mine_resource_command(message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `добыть [бизнес]`")
        return
    
    business_name = args[1].lower().strip()
    if business_name not in RESOURCE_BUSINESSES:
        await message.reply(f"❌ Бизнес '{business_name}' не найден!")
        return
    
    business = await get_business(user_id, business_name)
    if not business:
        await message.reply(f"❌ У тебя нет {RESOURCE_BUSINESSES[business_name]['emoji']} {business_name.capitalize()}!")
        return
    
    ok, remaining = await check_cooldown(user_id, f"mine_{business_name}", RESOURCE_BUSINESSES[business_name]["time"] * 60)
    if not ok:
        await message.reply(f"⏳ Подожди {remaining//60} мин {remaining%60} сек!")
        return
    
    data = RESOURCE_BUSINESSES[business_name]
    level = business[0]
    
    available = []
    for res, res_data in data["resources"].items():
        if random.randint(1, 100) <= res_data["chance"]:
            min_amt = res_data["min"] + (level // 3)
            max_amt = res_data["max"] + (level // 2)
            amount = random.randint(min_amt, max_amt)
            available.append({"name": res, "amount": amount, "price": res_data["price"]})
    
    if not available:
        await message.reply("❌ Сегодня ничего не добыто 😢")
        return
    
    msg = f"{data['emoji']} **{business_name.capitalize()}**\n📦 **ДОБЫЧА:**\n\n"
    total_value = 0
    for res in available:
        await add_item(user_id, res["name"], res["amount"])
        total = res["amount"] * res["price"]
        total_value += total
        emoji = get_item_emoji(res["name"])
        msg += f"{emoji} {res['name'].capitalize()}: **{res['amount']}** шт (💰 {total} монет)\n"
    
    msg += f"\n💎 Общая стоимость: **{total_value}** монет"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== SHIP ====================

async def show_ship_upgrades(message):
    msg = "⛵ **УЛУЧШЕНИЯ КОРАБЛЯ**\n\n"
    for name, data in SHIP_UPGRADES.items():
        msg += f"{data['emoji']} **{name.capitalize()}** — {data['price']} монет\n"
        msg += f"   📝 {data['desc']}\n\n"
    msg += "📝 `купить улучшение [название]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def buy_ship_upgrade(message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `купить улучшение [название]`")
        return
    
    name = args[1].lower().strip()
    if name not in SHIP_UPGRADES:
        await message.reply(f"❌ Улучшение '{name}' не найдено!")
        return
    
    upgrades = await get_ship_upgrades(user_id)
    if name in upgrades:
        await message.reply(f"❌ У тебя уже есть {SHIP_UPGRADES[name]['emoji']} {name.capitalize()}!")
        return
    
    price = SHIP_UPGRADES[name]["price"]
    if await get_coins(user_id) < price:
        await message.reply(f"❌ Нужно {price} монет!")
        return
    
    await remove_coins(user_id, price)
    await add_ship_upgrade(user_id, name)
    await log_action(user_id, "buy_ship_upgrade", f"Купил улучшение {name}")
    await message.reply(f"✅ {SHIP_UPGRADES[name]['emoji']} **{name.capitalize()}** куплен!")

async def my_ship(message):
    user_id = message.from_user.id
    upgrades = await get_ship_upgrades(user_id)
    stats = await get_ship_stats(user_id)
    
    msg = "⛵ **МОЙ КОРАБЛЬ**\n\n"
    msg += f"⚡ Скорость: -{stats['speed']}% времени\n"
    msg += f"🗺️ Навигация: -{stats['risk']}% риск\n"
    msg += f"🛡️ Защита: +{stats['defense']}% защита\n\n"
    
    if upgrades:
        msg += "🛠️ **УЛУЧШЕНИЯ:**\n"
        for upgrade in upgrades:
            data = SHIP_UPGRADES.get(upgrade)
            if data:
                msg += f"{data['emoji']} {upgrade.capitalize()}\n"
    else:
        msg += "❌ Нет улучшений"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== LIMITED ITEMS ====================

async def show_limited_items(message):
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
                emoji = data["emoji"]
                status = "✅" if left > 0 else "❌"
                msg += f"{emoji} {name.capitalize()} — {left}/{total} {status}\n"
        if found:
            msg += "\n"
    
    msg += "📝 `лимитка [название]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def show_limited_item_info(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return
    
    name = args[1].lower().strip()
    data = LIMITED_ITEMS.get(name)
    if not data:
        await message.reply(f"❌ Лимитка '{name}' не найдена!")
        return
    
    msg = f"{data['emoji']} **{name.capitalize()}**\n"
    msg += f"📊 Редкость: {data['rarity']}\n"
    msg += f"📦 Осталось: {data['left']}/{data['total']}\n"
    msg += f"📝 {data['desc']}\n"
    msg += f"💰 Цена: {data['price']} монет\n"
    msg += f"📊 Статус: {'✅ Доступен' if data['left'] > 0 else '❌ РАЗОБРАН'}"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== РЕПУТАЦИЯ ====================

async def add_reputation(message):
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

async def remove_reputation(message):
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

async def propose_marriage(message):
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
    
    await message.reply(f"💍 {await get_name(user_id)} предлагает брак {await get_name(target_id)}",
                        reply_markup=keyboard)

async def divorce_command(message):
    user_id = message.from_user.id
    spouse = await get_marriage(user_id)
    if not spouse:
        await message.reply("❌ Ты не в браке!")
        return
    
    await remove_marriage(user_id)
    await remove_marriage(spouse)
    await message.reply(f"💔 {await get_name(user_id)} развёлся!")

# ==================== КОЛБЭКИ БРАК ====================

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

# ==================== ДОСТИЖЕНИЯ ====================

ACHIEVEMENTS = {
    "first_work": {"name": "💼 Первая работа", "desc": "Устроиться на первую работу", "reward": 500},
    "first_money": {"name": "💰 Первый миллион", "desc": "Накопить 1 000 000 монет", "reward": 10000},
    "first_business": {"name": "🏪 Первый бизнес", "desc": "Купить первый бизнес", "reward": 1000},
    "ten_businesses": {"name": "🏪 Магнат", "desc": "Купить 10 бизнесов", "reward": 5000},
    "first_marriage": {"name": "💍 Первая свадьба", "desc": "Вступить в брак", "reward": 1000},
    "first_rep": {"name": "⭐ Первая репутация", "desc": "Получить +реп", "reward": 500},
    "first_shop": {"name": "🛒 Покупатель", "desc": "Купить предмет в магазине", "reward": 500},
    "ten_shop": {"name": "🛒 Шопоголик", "desc": "Купить 10 предметов", "reward": 2000},
    "first_limited": {"name": "🔥 Коллекционер", "desc": "Купить лимитный предмет", "reward": 5000},
    "first_mine": {"name": "🪨 Шахтёр", "desc": "Добыть ресурсы", "reward": 500},
    "level_5": {"name": "🎯 Уровень 5", "desc": "Достигнуть уровня 5", "reward": 2000},
    "level_10": {"name": "👑 Уровень 10", "desc": "Достигнуть уровня 10", "reward": 5000}
}

async def unlock_achievement(user_id, ach_key):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM user_achievements WHERE user_id = ? AND achievement_name = ?", (user_id, ach_key))
    if c.fetchone():
        conn.close()
        return False
    
    ach_data = ACHIEVEMENTS.get(ach_key)
    if not ach_data:
        conn.close()
        return False
    
    c.execute("INSERT INTO user_achievements (user_id, achievement_name, unlocked_at) VALUES (?, ?, ?)",
              (user_id, ach_key, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await add_coins(user_id, ach_data["reward"])
    return True

async def check_achievements(user_id):
    unlocked = []
    level, _ = await get_level(user_id)
    
    if level >= 5:
        if await unlock_achievement(user_id, "level_5"):
            unlocked.append("🎯 Уровень 5")
    if level >= 10:
        if await unlock_achievement(user_id, "level_10"):
            unlocked.append("👑 Уровень 10")
    
    coins = await get_coins(user_id)
    if coins >= 1000000:
        if await unlock_achievement(user_id, "first_money"):
            unlocked.append("💰 Первый миллион")
    
    job = await get_job(user_id)
    if job:
        if await unlock_achievement(user_id, "first_work"):
            unlocked.append("💼 Первая работа")
    
    businesses = await get_businesses(user_id)
    if len(businesses) >= 1:
        if await unlock_achievement(user_id, "first_business"):
            unlocked.append("🏪 Первый бизнес")
    if len(businesses) >= 10:
        if await unlock_achievement(user_id, "ten_businesses"):
            unlocked.append("🏪 Магнат")
    
    inventory = await get_inventory(user_id)
    if len(inventory) >= 1:
        if await unlock_achievement(user_id, "first_shop"):
            unlocked.append("🛒 Покупатель")
    if len(inventory) >= 10:
        if await unlock_achievement(user_id, "ten_shop"):
            unlocked.append("🛒 Шопоголик")
    
    return unlocked

async def show_achievements(message):
    user_id = message.from_user.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT achievement_name FROM user_achievements WHERE user_id = ?", (user_id,))
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

# ==================== ИГРЫ (КУБЫ) ====================

async def cube_game(message):
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        await message.reply("🎲 Ответь на сообщение соперника!\n📝 `кубы` или `кубы 2` (2 кости)")
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

# ==================== РП КОМАНДЫ ====================

RP_ACTIONS = {
    "обнять": ["🤗 {user} обнял {target}!", "❤️ {user} прижал к себе {target}!", "💕 {user} согрел {target} теплом!"],
    "поцеловать": ["😘 {user} поцеловал {target}!", "💋 {user} чмокнул {target}!", "❤️‍🔥 {user} засосал {target}!"],
    "ударить": ["👊 {user} ударил {target}!", "💥 {user} заехал {target}!", "🥊 {user} врезал {target}!"],
    "пнуть": ["🦶 {user} пнул {target}!", "👟 {user} дал пинка {target}!", "💨 {user} выпнул {target}!"]
}

# ==================== МОДЕРАЦИЯ ====================

async def moderation_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    
    level, _ = await get_level(user_id)
    
    if text.startswith("бан "):
        if level < 10:
            await message.reply("❌ Недостаточно прав!")
            return
        args = text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("ℹ️ `бан @user`")
            return
        try:
            member = await message.chat.get_member(args[1].replace("@", ""))
            await bot.ban_chat_member(message.chat.id, member.user.id)
            await message.reply(f"🔨 {member.user.first_name} забанен!")
            await log_action(user_id, "ban", f"Забанил {member.user.first_name}")
        except:
            await message.reply("❌ Не найден!")
        return
    
    if text.startswith("разбан "):
        if level < 10:
            await message.reply("❌ Недостаточно прав!")
            return
        args = text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("ℹ️ `разбан @user`")
            return
        try:
            member = await message.chat.get_member(args[1].replace("@", ""))
            await bot.unban_chat_member(message.chat.id, member.user.id)
            await message.reply(f"✅ {member.user.first_name} разбанен!")
        except:
            await message.reply("❌ Не найден!")
        return
    
    if text.startswith("мут "):
        if level < 10:
            await message.reply("❌ Недостаточно прав!")
            return
        args = text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("ℹ️ `мут @user`")
            return
        try:
            member = await message.chat.get_member(args[1].replace("@", ""))
            await bot.restrict_chat_member(message.chat.id, member.user.id,
                                          permissions=ChatPermissions(can_send_messages=False))
            await message.reply(f"🔇 {member.user.first_name} замучен!")
        except:
            await message.reply("❌ Не найден!")
        return
    
    if text.startswith("размут "):
        if level < 10:
            await message.reply("❌ Недостаточно прав!")
            return
        args = text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("ℹ️ `размут @user`")
            return
        try:
            member = await message.chat.get_member(args[1].replace("@", ""))
            await bot.restrict_chat_member(message.chat.id, member.user.id,
                                          permissions=ChatPermissions(can_send_messages=True,
                                                                      can_send_media_messages=True,
                                                                      can_send_other_messages=True,
                                                                      can_add_web_page_previews=True))
            await message.reply(f"✅ {member.user.first_name} размучен!")
        except:
            await message.reply("❌ Не найден!")
        return
# ==================== ЧАСТЬ 2: ВСЕ ДОПОЛНИТЕЛЬНЫЕ СИСТЕМЫ ====================

import random
import sqlite3
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

# ==================== 1. ВЫДАЧА ПРЕДМЕТОВ (ТОЛЬКО В ЛС, ТОЛЬКО СОЗДАТЕЛЬ) ====================

@dp.message()
async def give_commands(message: types.Message):
    """Команды выдачи в личку бота (только создатель)"""
    
    # Проверяем ЛС
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    if user_id != CREATOR_ID:
        await message.reply("❌ Только создатель может выдавать предметы!")
        return
    
    if not message.text:
        return
    
    text = message.text.lower().strip()
    args = text.split()
    
    if len(args) < 3:
        await message.reply("""
📋 **КОМАНДЫ ВЫДАЧИ (ТОЛЬКО В ЛС)**

💰 **Монеты:**
`дать монеты @user 1000`
`дать монеты мне 1000`

🏦 **Банк:**
`дать банк @user 5000`
`дать банк мне 10000`

🎒 **Предмет:**
`дать предмет @user предмет 5`
`дать предмет мне алмаз 10`

🪨 **Ресурс:**
`дать ресурс @user ресурс 100`
`дать ресурс мне камень 50`

🔥 **Лимитка:**
`дать лимитку @user предмет`
`дать лимитку мне корона карла`

❌ **Забрать:**
`забрать монеты @user 500`
`забрать предмет @user алмаз 1`

📊 **ПРОМО-КОДЫ:**
`создать промо [название] [монеты] [предмет] [количество]`
`активировать промо [код]`
`список промо`
`удалить промо [код]`

━━━━━━━━━━━━━━━━━━━━
""")
        return
    
    action = args[1]  # монеты, банк, предмет, ресурс, лимитку, промо
    target_raw = args[2]  # @user, мне, или id
    
    # Определяем цель
    if target_raw == "мне":
        target_id = user_id
    elif target_raw.startswith("@"):
        try:
            member = await message.chat.get_member(target_raw.replace("@", ""))
            target_id = member.user.id
        except:
            await message.reply("❌ Пользователь не найден!")
            return
    else:
        try:
            target_id = int(target_raw)
        except:
            await message.reply("❌ Неверный формат! Используй: `@user`, `мне` или `id`")
            return
    
    # ===== ВЫДАЧА МОНЕТ =====
    if action == "монеты":
        try:
            amount = int(args[3])
            if amount <= 0:
                await message.reply("❌ Сумма должна быть > 0!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        await add_coins(target_id, amount)
        await log_action(user_id, "give_coins", f"Выдал {amount} монет {await get_name(target_id)}")
        await message.reply(f"✅ {await get_name(target_id)} выдано **{amount}** монет!")
        return
    
    # ===== ВЫДАЧА В БАНК =====
    if action == "банк":
        try:
            amount = int(args[3])
            if amount <= 0:
                await message.reply("❌ Сумма должна быть > 0!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        await add_bank(target_id, amount)
        await log_action(user_id, "give_bank", f"Выдал {amount} монет в банк {await get_name(target_id)}")
        await message.reply(f"✅ {await get_name(target_id)} выдано **{amount}** монет в банк!")
        return
    
    # ===== ВЫДАЧА ПРЕДМЕТА =====
    if action == "предмет":
        if len(args) < 4:
            await message.reply("ℹ️ `дать предмет @user предмет [количество]`")
            return
        
        item_name = args[3].lower()
        quantity = 1
        if len(args) > 4:
            try:
                quantity = int(args[4])
                if quantity <= 0:
                    await message.reply("❌ Количество должно быть > 0!")
                    return
            except:
                await message.reply("❌ Введи число!")
                return
        
        # Проверяем существование предмета
        if item_name not in SHOP_ITEMS and item_name not in LIMITED_ITEMS:
            await message.reply(f"❌ Предмет '{item_name}' не найден!")
            return
        
        await add_item(target_id, item_name, quantity)
        await log_action(user_id, "give_item", f"Выдал {quantity}x {item_name} {await get_name(target_id)}")
        await message.reply(f"✅ {await get_name(target_id)} выдано **{quantity}** шт **{item_name.capitalize()}**!")
        return
    
    # ===== ВЫДАЧА РЕСУРСА =====
    if action == "ресурс":
        if len(args) < 4:
            await message.reply("ℹ️ `дать ресурс @user ресурс [количество]`")
            return
        
        resource_name = args[3].lower()
        quantity = 1
        if len(args) > 4:
            try:
                quantity = int(args[4])
                if quantity <= 0:
                    await message.reply("❌ Количество должно быть > 0!")
                    return
            except:
                await message.reply("❌ Введи число!")
                return
        
        # Проверяем существование ресурса
        found = False
        for biz in RESOURCE_BUSINESSES.values():
            if resource_name in biz["resources"]:
                found = True
                break
        
        if not found:
            await message.reply(f"❌ Ресурс '{resource_name}' не найден!")
            return
        
        await add_item(target_id, resource_name, quantity)
        await log_action(user_id, "give_resource", f"Выдал {quantity}x {resource_name} {await get_name(target_id)}")
        await message.reply(f"✅ {await get_name(target_id)} выдано **{quantity}** шт **{resource_name.capitalize()}**!")
        return
    
    # ===== ВЫДАЧА ЛИМИТКИ =====
    if action == "лимитку":
        if len(args) < 4:
            await message.reply("ℹ️ `дать лимитку @user предмет`")
            return
        
        item_name = args[3].lower()
        
        if item_name not in LIMITED_ITEMS:
            await message.reply(f"❌ Лимитка '{item_name}' не найдена!")
            return
        
        if LIMITED_ITEMS[item_name]["left"] <= 0:
            await message.reply(f"❌ {LIMITED_ITEMS[item_name]['emoji']} {item_name.capitalize()} уже разобрана!")
            return
        
        # Проверяем, есть ли уже у игрока
        if await has_item(target_id, item_name):
            await message.reply(f"❌ У {await get_name(target_id)} уже есть {item_name.capitalize()}!")
            return
        
        # Выдаём
        await add_item(target_id, item_name, 1)
        
        # Уменьшаем остаток
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("UPDATE limited_items SET left_count = left_count - 1 WHERE name = ?", (item_name,))
        conn.commit()
        conn.close()
        LIMITED_ITEMS[item_name]["left"] -= 1
        
        await log_action(user_id, "give_limited", f"Выдал {item_name} {await get_name(target_id)}")
        await message.reply(f"✅ {await get_name(target_id)} выдана **{item_name.capitalize()}**!\n📦 Осталось: {LIMITED_ITEMS[item_name]['left']}/{LIMITED_ITEMS[item_name]['total']}")
        return
    
    # ===== ЗАБРАТЬ МОНЕТЫ =====
    if action == "забрать" and args[2] == "монеты":
        try:
            amount = int(args[3])
            if amount <= 0:
                await message.reply("❌ Сумма должна быть > 0!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        coins = await get_coins(target_id)
        if coins < amount:
            await message.reply(f"❌ У {await get_name(target_id)} только {coins} монет!")
            return
        
        await remove_coins(target_id, amount)
        await log_action(user_id, "remove_coins", f"Забрал {amount} монет у {await get_name(target_id)}")
        await message.reply(f"✅ У {await get_name(target_id)} забрано **{amount}** монет!")
        return
    
    # ===== ЗАБРАТЬ ПРЕДМЕТ =====
    if action == "забрать" and args[2] == "предмет":
        if len(args) < 5:
            await message.reply("ℹ️ `забрать предмет @user предмет [количество]`")
            return
        
        item_name = args[3].lower()
        quantity = 1
        if len(args) > 5:
            try:
                quantity = int(args[4])
                if quantity <= 0:
                    await message.reply("❌ Количество должно быть > 0!")
                    return
            except:
                await message.reply("❌ Введи число!")
                return
        
        if not await has_item(target_id, item_name):
            await message.reply(f"❌ У {await get_name(target_id)} нет {item_name.capitalize()}!")
            return
        
        await remove_item(target_id, item_name, quantity)
        await log_action(user_id, "remove_item", f"Забрал {quantity}x {item_name} у {await get_name(target_id)}")
        await message.reply(f"✅ У {await get_name(target_id)} забрано **{quantity}** шт **{item_name.capitalize()}**!")
        return
    
    # ===== ПРОМО-КОДЫ =====
    if action == "промо":
        if len(args) < 3:
            await message.reply("ℹ️ `создать промо [название] [монеты] [предмет] [количество]`\n"
                              "ℹ️ `активировать промо [код]`\n"
                              "ℹ️ `список промо`\n"
                              "ℹ️ `удалить промо [код]`")
            return
        
        if args[2] == "создать":
            # Создать промо-код
            # Формат: создать промо название 1000 предмет 5
            pass  # TODO: реализовать
        
        if args[2] == "активировать":
            # Активировать промо-код
            pass  # TODO: реализовать
        
        if args[2] == "список":
            # Список промо-кодов
            pass  # TODO: реализовать
        
        if args[2] == "удалить":
            # Удалить промо-код
            pass  # TODO: реализовать
        
        await message.reply("✅ Промо-система в разработке!")

# ==================== 2. КЛАНЫ ====================

async def clan_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Создать клан
    if text.startswith("создать клан"):
        if len(args) < 3:
            await message.reply("ℹ️ `создать клан [название]`")
            return
        
        name = " ".join(args[2:])
        
        # Проверяем монеты
        coins = await get_coins(user_id)
        if coins < 5000:
            await message.reply(f"❌ Нужно 5000 монет для создания клана! У тебя {coins}")
            return
        
        # Проверяем, не в клане ли уже
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
        
        # Создаём клан
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
        return
    
    # Вступить в клан
    if text.startswith("вступить в клан"):
        if len(args) < 4:
            await message.reply("ℹ️ `вступить в клан [название]`")
            return
        
        name = " ".join(args[3:])
        
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
        
        if await get_user_clan(user_id):
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
        return
    
    # Мой клан
    if text == "мой клан":
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
        return
    
    # Список кланов
    if text == "кланы":
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
        return
    
    # Казна
    if text.startswith("казна "):
        args = text.split()
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
            await add_to_clan_treasury(clan_id, amount)
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
            
            await remove_from_clan_treasury(clan_id, amount)
            await add_coins(user_id, amount)
            await log_action(user_id, "clan_withdraw", f"Снял {amount} из казны клана")
            await message.reply(f"💰 -{amount} монет из казны клана!")
            return

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

async def add_to_clan_treasury(clan_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE clans SET treasury = treasury + ? WHERE id = ?", (amount, clan_id))
    conn.commit()
    conn.close()

async def remove_from_clan_treasury(clan_id, amount):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("UPDATE clans SET treasury = treasury - ? WHERE id = ? AND treasury >= ?", (amount, clan_id, amount))
    conn.commit()
    conn.close()

# ==================== 3. КРЕДИТЫ ====================

async def loan_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Взять кредит
    if text.startswith("кредит взять"):
        if len(args) < 3:
            await message.reply("ℹ️ `кредит взять [сумма]`")
            return
        
        try:
            amount = int(args[2])
            if amount <= 0:
                await message.reply("❌ Сумма должна быть > 0!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        # Проверяем работу
        job = await get_job(user_id)
        if not job:
            await message.reply("❌ У тебя нет работы! Кредит только с работой.")
            return
        
        # Максимальный кредит = 100x зарплаты
        job_data = JOBS.get(job)
        if not job_data:
            await message.reply("❌ Ошибка!")
            return
        
        max_loan = (job_data["min"] + job_data["max"]) // 2 * 100
        if amount > max_loan:
            await message.reply(f"❌ Максимум кредита: {max_loan} монет (100x зарплаты)")
            return
        
        # Проверяем, есть ли уже кредит
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM loans WHERE user_id = ? AND paid = 0", (user_id,))
        if c.fetchone():
            conn.close()
            await message.reply("❌ У тебя уже есть активный кредит!")
            return
        
        # Выдаём кредит
        interest = random.randint(10, 30)
        due_date = datetime.now() + timedelta(days=7)
        
        c.execute("INSERT INTO loans (user_id, amount, interest, taken_at, due_date) VALUES (?, ?, ?, ?, ?)",
                  (user_id, amount, interest, datetime.now().isoformat(), due_date.isoformat()))
        conn.commit()
        conn.close()
        
        await add_coins(user_id, amount)
        await log_action(user_id, "take_loan", f"Взял кредит {amount} монет (процент {interest}%)")
        
        await message.reply(f"✅ Кредит **{amount}** монет выдан!\n"
                          f"📈 Процент: {interest}%\n"
                          f"📅 Срок: 7 дней\n"
                          f"💰 К выплате: {amount + amount * interest // 100} монет")
        return
    
    # Погасить кредит
    if text == "кредит погасить":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT amount, interest FROM loans WHERE user_id = ? AND paid = 0", (user_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            await message.reply("❌ У тебя нет активных кредитов!")
            return
        
        amount, interest = row
        total = amount + amount * interest // 100
        coins = await get_coins(user_id)
        
        if coins < total:
            await message.reply(f"❌ Нужно {total} монет для погашения! У тебя {coins}")
            return
        
        await remove_coins(user_id, total)
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("UPDATE loans SET paid = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        await log_action(user_id, "pay_loan", f"Погасил кредит {amount} монет")
        await message.reply(f"✅ Кредит погашен! Спасибо. 💳")
        return
    
    # Мои кредиты
    if text == "кредит мои":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT amount, interest, taken_at, due_date, paid FROM loans WHERE user_id = ?", (user_id,))
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            await message.reply("❌ Нет кредитов!")
            return
        
        msg = "💳 **МОИ КРЕДИТЫ**\n\n"
        for amount, interest, taken_at, due_date, paid in rows:
            status = "✅ ПОГАШЕН" if paid else "⚠️ АКТИВЕН"
            total = amount + amount * interest // 100
            msg += f"{'💰' if not paid else '✅'} Сумма: {amount} (+{interest}% = {total})\n"
            msg += f"📅 Взят: {taken_at[:10]}\n"
            msg += f"📅 Срок: {due_date[:10]}\n"
            msg += f"📊 Статус: {status}\n\n"
        
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== 4. ЛОТЕРЕЯ ====================

async def lottery_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Купить билеты
    if text.startswith("лотерея купить"):
        if len(args) < 3:
            await message.reply("ℹ️ `лотерея купить [количество]`")
            return
        
        try:
            tickets = int(args[2])
            if tickets <= 0:
                await message.reply("❌ Количество должно быть > 0!")
                return
            if tickets > 100:
                await message.reply("❌ Максимум 100 билетов!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        price = tickets * 100
        coins = await get_coins(user_id)
        
        if coins < price:
            await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
            return
        
        await remove_coins(user_id, price)
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO lottery (user_id, tickets, bought_at) VALUES (?, ?, ?)",
                  (user_id, tickets, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        await log_action(user_id, "buy_lottery", f"Купил {tickets} билетов")
        await message.reply(f"✅ Куплено {tickets} билетов за {price} монет!")
        return
    
    # Мои билеты
    if text == "лотерея мои":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT SUM(tickets) FROM lottery WHERE user_id = ?", (user_id,))
        total = c.fetchone()[0] or 0
        conn.close()
        
        await message.reply(f"🎲 У тебя **{total}** билетов!")
        return
    
    # Розыгрыш
    if text == "лотерея розыгрыш":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id, tickets FROM lottery")
        tickets_data = c.fetchall()
        
        if not tickets_data:
            conn.close()
            await message.reply("❌ Нет участников!")
            return
        
        # Создаём список участников
        participants = []
        for user_id, tickets in tickets_data:
            participants.extend([user_id] * tickets)
        
        # Выбираем победителя
        winner_id = random.choice(participants)
        jackpot = len(participants) * 100
        
        # Очищаем лотерею
        c.execute("DELETE FROM lottery")
        conn.commit()
        conn.close()
        
        # Награда
        reward = jackpot // 2
        await add_coins(winner_id, reward)
        
        await log_action(winner_id, "lottery_win", f"Выиграл в лотерею {reward} монет")
        await bot.send_message(message.chat.id, 
                              f"🎉 **ПОБЕДИТЕЛЬ ЛОТЕРЕИ!** 🎉\n"
                              f"🏆 {await get_name(winner_id)}\n"
                              f"💰 Приз: {reward} монет!\n"
                              f"🎫 Всего билетов: {len(participants)}")
        return

# ==================== 5. ФОНДОВЫЙ РЫНОК ====================

STOCKS = {
    "газпром": {"price": 100, "volatility": 5},
    "лукойл": {"price": 120, "volatility": 7},
    "яндекс": {"price": 80, "volatility": 10},
    "озон": {"price": 60, "volatility": 8},
    "сбербанк": {"price": 90, "volatility": 3},
    "мтс": {"price": 70, "volatility": 4},
    "роскосмос": {"price": 150, "volatility": 15},
    "huawei": {"price": 200, "volatility": 12}
}

async def stock_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Рынок
    if text == "рынок":
        msg = "📈 **ФОНДОВЫЙ РЫНОК**\n\n"
        for name, data in STOCKS.items():
            price = data["price"]
            vol = data["volatility"]
            msg += f"**{name.capitalize()}** — {price} монет (волатильность {vol}%)\n"
        msg += "\n📝 `купить акции [компания] [количество]`\n📝 `продать акции [компания] [количество]`"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Купить акции
    if text.startswith("купить акции"):
        if len(args) < 4:
            await message.reply("ℹ️ `купить акции [компания] [количество]`")
            return
        
        company = args[2].lower()
        if company not in STOCKS:
            await message.reply(f"❌ Компания '{company}' не найдена!\n📝 Список: `рынок`")
            return
        
        try:
            quantity = int(args[3])
            if quantity <= 0:
                await message.reply("❌ Количество должно быть > 0!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        price = STOCKS[company]["price"]
        total = price * quantity
        coins = await get_coins(user_id)
        
        if coins < total:
            await message.reply(f"❌ Нужно {total} монет! У тебя {coins}")
            return
        
        await remove_coins(user_id, total)
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO stocks (user_id, company, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, company) DO UPDATE SET quantity = quantity + ?",
                  (user_id, company, quantity, quantity))
        conn.commit()
        conn.close()
        
        await log_action(user_id, "buy_stocks", f"Купил {quantity} акций {company}")
        await message.reply(f"✅ Куплено {quantity} акций **{company.capitalize()}** за {total} монет!")
        return
    
    # Продать акции
    if text.startswith("продать акции"):
        if len(args) < 4:
            await message.reply("ℹ️ `продать акции [компания] [количество]`")
            return
        
        company = args[2].lower()
        if company not in STOCKS:
            await message.reply(f"❌ Компания '{company}' не найдена!")
            return
        
        try:
            quantity = int(args[3])
            if quantity <= 0:
                await message.reply("❌ Количество должно быть > 0!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT quantity FROM stocks WHERE user_id = ? AND company = ?", (user_id, company))
        row = c.fetchone()
        
        if not row or row[0] < quantity:
            conn.close()
            await message.reply(f"❌ У тебя только {row[0] if row else 0} акций {company}!")
            return
        
        # Изменение цены (волатильность)
        price = STOCKS[company]["price"]
        change = random.randint(-price * STOCKS[company]["volatility"] // 100, price * STOCKS[company]["volatility"] // 100)
        final_price = max(1, price + change)
        
        total = final_price * quantity
        
        c.execute("UPDATE stocks SET quantity = quantity - ? WHERE user_id = ? AND company = ?", (quantity, user_id, company))
        if c.rowcount == 0:
            c.execute("DELETE FROM stocks WHERE user_id = ? AND company = ?", (user_id, company))
        conn.commit()
        conn.close()
        
        await add_coins(user_id, total)
        await log_action(user_id, "sell_stocks", f"Продал {quantity} акций {company} за {total}")
        await message.reply(f"✅ Продано {quantity} акций **{company.capitalize()}** за {total} монет!\n📈 Цена: {final_price} монет/шт")
        return
    
    # Мой портфель
    if text == "мой портфель":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT company, quantity FROM stocks WHERE user_id = ?", (user_id,))
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            await message.reply("📭 У тебя нет акций!")
            return
        
        msg = "📊 **МОЙ ПОРТФЕЛЬ**\n\n"
        total_value = 0
        for company, quantity in rows:
            price = STOCKS.get(company, {}).get("price", 0)
            value = price * quantity
            total_value += value
            msg += f"**{company.capitalize()}** — {quantity} шт (💰 {value} монет)\n"
        
        msg += f"\n💎 Общая стоимость: **{total_value}** монет"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== 6. НЕДВИЖИМОСТЬ ====================

PROPERTIES = {
    "дом": {"price": 100000, "income": 500, "emoji": "🏠"},
    "квартира": {"price": 80000, "income": 400, "emoji": "🏢"},
    "особняк": {"price": 200000, "income": 1000, "emoji": "🏰"},
    "замок": {"price": 500000, "income": 2500, "emoji": "🏯"}
}

async def property_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Список недвижимости
    if text == "недвижимость":
        msg = "🏠 **НЕДВИЖИМОСТЬ**\n\n"
        for name, data in PROPERTIES.items():
            msg += f"{data['emoji']} **{name.capitalize()}**\n"
            msg += f"💰 Цена: {data['price']} монет\n"
            msg += f"📈 Доход: {data['income']} монет/день\n\n"
        msg += "📝 `купить дом` или `купить квартиру`\n📝 `моя недвижимость`"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Купить дом
    if text.startswith("купить дом"):
        await buy_property(message, "дом")
        return
    
    # Купить квартиру
    if text.startswith("купить квартиру"):
        await buy_property(message, "квартира")
        return
    
    # Купить особняк
    if text.startswith("купить особняк"):
        await buy_property(message, "особняк")
        return
    
    # Моя недвижимость
    if text == "моя недвижимость":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT type, bought_at FROM properties WHERE user_id = ?", (user_id,))
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            await message.reply("❌ У тебя нет недвижимости!")
            return
        
        msg = "🏠 **МОЯ НЕДВИЖИМОСТЬ**\n\n"
        for prop_type, bought_at in rows:
            data = PROPERTIES.get(prop_type)
            if data:
                msg += f"{data['emoji']} **{prop_type.capitalize()}**\n"
                msg += f"📅 Куплено: {bought_at[:10]}\n"
                msg += f"💰 Доход: {data['income']} монет/день\n\n"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def buy_property(message, prop_type):
    user_id = message.from_user.id
    data = PROPERTIES.get(prop_type)
    if not data:
        await message.reply(f"❌ Недвижимость '{prop_type}' не найдена!")
        return
    
    # Проверяем, есть ли уже
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM properties WHERE user_id = ? AND type = ?", (user_id, prop_type))
    if c.fetchone():
        conn.close()
        await message.reply(f"❌ У тебя уже есть {data['emoji']} {prop_type.capitalize()}!")
        return
    conn.close()
    
    price = data["price"]
    coins = await get_coins(user_id)
    
    if coins < price:
        await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
        return
    
    await remove_coins(user_id, price)
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO properties (user_id, type, bought_at) VALUES (?, ?, ?)",
              (user_id, prop_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await log_action(user_id, "buy_property", f"Купил {prop_type}")
    await message.reply(f"✅ {data['emoji']} **{prop_type.capitalize()}** куплен за {price} монет!")

# ==================== 7. ФЕРМА ====================

CROPS = {
    "пшеница": {"time": 3600, "income": 100, "emoji": "🌾"},
    "морковь": {"time": 7200, "income": 200, "emoji": "🥕"},
    "помидоры": {"time": 14400, "income": 400, "emoji": "🍅"},
    "клубника": {"time": 28800, "income": 800, "emoji": "🍓"}
}

async def farm_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Ферма
    if text == "ферма":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT crop, planted_at FROM farm WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            msg = "🌾 **ФЕРМА**\n\n"
            msg += "📋 Посади культуры:\n"
            for crop, data in CROPS.items():
                msg += f"{data['emoji']} {crop.capitalize()} — {data['time']//3600}ч, доход {data['income']} монет\n"
            msg += "\n📝 `посадить [культура]`"
            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
            return
        
        crop, planted_at = row
        data = CROPS.get(crop)
        elapsed = (datetime.now() - datetime.fromisoformat(planted_at)).total_seconds()
        remaining = max(0, data["time"] - elapsed)
        
        if remaining <= 0:
            msg = f"🌾 **{crop.capitalize()}**\n"
            msg += f"✅ Готово к сбору!\n"
            msg += f"💰 Доход: {data['income']} монет\n"
            msg += "📝 `собрать`"
        else:
            msg = f"🌾 **{crop.capitalize()}**\n"
            msg += f"⏳ Осталось: {int(remaining//3600)}ч {int((remaining%3600)//60)}м\n"
            msg += f"💰 Доход: {data['income']} монет"
        
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Посадить
    if text.startswith("посадить"):
        if len(args) < 2:
            await message.reply("ℹ️ `посадить [культура]`")
            return
        
        crop = args[1].lower()
        if crop not in CROPS:
            await message.reply(f"❌ Культура '{crop}' не найдена!\n📝 Список: `ферма`")
            return
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM farm WHERE user_id = ?", (user_id,))
        if c.fetchone():
            conn.close()
            await message.reply("❌ У тебя уже есть посаженная культура!")
            return
        conn.close()
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO farm (user_id, crop, planted_at) VALUES (?, ?, ?)",
                  (user_id, crop, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        data = CROPS[crop]
        await message.reply(f"✅ {data['emoji']} **{crop.capitalize()}** посажена!\n⏳ {data['time']//3600} часов до сбора")
        return
    
    # Собрать
    if text == "собрать":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT crop, planted_at FROM farm WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            await message.reply("❌ У тебя ничего не посажено!")
            return
        
        crop, planted_at = row
        data = CROPS.get(crop)
        elapsed = (datetime.now() - datetime.fromisoformat(planted_at)).total_seconds()
        
        if elapsed < data["time"]:
            remaining = data["time"] - elapsed
            conn.close()
            await message.reply(f"⏳ Подожди {int(remaining//3600)}ч {int((remaining%3600)//60)}м!")
            return
        
        income = data["income"]
        await add_coins(user_id, income)
        
        c.execute("DELETE FROM farm WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        await log_action(user_id, "farm_harvest", f"Собрал урожай {crop} +{income} монет")
        await message.reply(f"🌾 **УРОЖАЙ СОБРАН!**\n💰 +{income} монет!")

# ==================== 8. РЫБАЛКА ====================

FISH = {
    "окунь": {"price": 50, "chance": 30, "emoji": "🐟"},
    "карп": {"price": 100, "chance": 25, "emoji": "🐠"},
    "лосось": {"price": 200, "chance": 20, "emoji": "🐡"},
    "щука": {"price": 300, "chance": 15, "emoji": "🦈"},
    "осётр": {"price": 500, "chance": 10, "emoji": "🐋"}
}

async def fishing_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    
    # Рыбалка
    if text == "рыбалка":
        ok, remaining = await check_cooldown(user_id, "fish", 300)
        if not ok:
            await message.reply(f"⏳ Подожди {remaining//60} мин {remaining%60} сек!")
            return
        
        # Проверяем удочку
        if not await has_item(user_id, "профессиональная удочка"):
            await message.reply("🎣 У тебя нет удочки! Купи: `купить профессиональная удочка`")
            return
        
        # Ловим рыбу
        fish_list = list(FISH.values())
        total_chance = sum(f["chance"] for f in fish_list)
        roll = random.randint(1, total_chance)
        
        caught = None
        current = 0
        for name, data in FISH.items():
            current += data["chance"]
            if roll <= current:
                caught = (name, data)
                break
        
        if caught:
            name, data = caught
            amount = random.randint(1, 3)
            await add_item(user_id, name, amount)
            await log_action(user_id, "fishing", f"Поймал {amount}x {name}")
            await message.reply(f"🎣 Ты поймал {data['emoji']} **{name.capitalize()}** x{amount}!\n💰 Цена: {data['price']} монет/шт")
        else:
            await message.reply("🎣 Ничего не поймал 😢 Попробуй ещё!")
        return
    
    # Купить удочку
    if text == "купить удочку":
        if await has_item(user_id, "профессиональная удочка"):
            await message.reply("❌ У тебя уже есть удочка!")
            return
        
        price = 40000
        coins = await get_coins(user_id)
        if coins < price:
            await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
            return
        
        await remove_coins(user_id, price)
        await add_item(user_id, "профессиональная удочка")
        await log_action(user_id, "buy_fishing_rod", "Купил удочку")
        await message.reply(f"✅ **Удочка** куплена за {price} монет! Теперь можно рыбачить 🎣")
        return

# ==================== 9. ОХОТА ====================

ANIMALS = {
    "заяц": {"price": 100, "chance": 30, "emoji": "🐇"},
    "лиса": {"price": 200, "chance": 25, "emoji": "🦊"},
    "волк": {"price": 300, "chance": 20, "emoji": "🐺"},
    "медведь": {"price": 500, "chance": 15, "emoji": "🐻"},
    "тигр": {"price": 800, "chance": 10, "emoji": "🐯"}
}

async def hunting_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    
    # Охота
    if text == "охота":
        ok, remaining = await check_cooldown(user_id, "hunt", 300)
        if not ok:
            await message.reply(f"⏳ Подожди {remaining//60} мин {remaining%60} сек!")
            return
        
        # Проверяем ружьё
        if not await has_item(user_id, "тренировочное ружьё"):
            await message.reply("🔫 У тебя нет ружья! Купи: `купить тренировочное ружьё`")
            return
        
        # Охотимся
        animals_list = list(ANIMALS.values())
        total_chance = sum(a["chance"] for a in animals_list)
        roll = random.randint(1, total_chance)
        
        killed = None
        current = 0
        for name, data in ANIMALS.items():
            current += data["chance"]
            if roll <= current:
                killed = (name, data)
                break
        
        if killed:
            name, data = killed
            amount = random.randint(1, 2)
            await add_item(user_id, name, amount)
            await log_action(user_id, "hunting", f"Добыл {amount}x {name}")
            await message.reply(f"🔫 Ты добыл {data['emoji']} **{name.capitalize()}** x{amount}!\n💰 Цена: {data['price']} монет/шт")
        else:
            await message.reply("🔫 Промах! Никого не убил 😢 Попробуй ещё!")
        return
    
    # Купить ружьё
    if text == "купить ружьё":
        if await has_item(user_id, "тренировочное ружьё"):
            await message.reply("❌ У тебя уже есть ружьё!")
            return
        
        price = 60000
        coins = await get_coins(user_id)
        if coins < price:
            await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
            return
        
        await remove_coins(user_id, price)
        await add_item(user_id, "тренировочное ружьё")
        await log_action(user_id, "buy_hunting_rifle", "Купил ружьё")
        await message.reply(f"✅ **Ружьё** куплено за {price} монет! Теперь можно охотиться 🔫")
        return

# ==================== 10. ТУРНИРЫ ====================

tournaments = {}
tournament_players = {}

async def tournament_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    chat_id = message.chat.id
    args = text.split()
    
    # Турнир
    if text == "турнир":
        if chat_id not in tournaments:
            # Создаём турнир
            tournaments[chat_id] = {"status": "active", "players": [], "started": datetime.now()}
            await message.reply("🏆 **ТУРНИР НАЧАЛСЯ!**\n"
                              "Участвуй: просто напиши `турнир`\n"
                              "Призовой фонд: 1000 монет\n"
                              "⏳ Длительность: 10 минут")
            return
        
        tournament = tournaments[chat_id]
        if user_id in tournament["players"]:
            await message.reply("❌ Ты уже участвуешь!")
            return
        
        tournament["players"].append(user_id)
        
        # Проверяем, сколько участников
        if len(tournament["players"]) >= 5:
            # Завершаем турнир
            winner_id = random.choice(tournament["players"])
            reward = 1000
            
            await add_coins(winner_id, reward)
            await log_action(winner_id, "tournament_win", f"Выиграл турнир +{reward} монет")
            
            msg = "🏆 **ТУРНИР ЗАВЕРШЁН!**\n"
            msg += f"👤 Участников: {len(tournament['players'])}\n"
            msg += f"🏆 Победитель: {await get_name(winner_id)}\n"
            msg += f"💰 Приз: {reward} монет!"
            
            await bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)
            del tournaments[chat_id]
        else:
            await message.reply(f"✅ Ты участвуешь! Участников: {len(tournament['players'])}/{5}")
        return
    
    # Топ турниров
    if text == "топ турниров":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id, details FROM logs WHERE action = 'tournament_win' ORDER BY timestamp DESC LIMIT 10")
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            await message.reply("📭 Нет победителей!")
            return
        
        msg = "🏆 **ТОП ТУРНИРОВ**\n\n"
        for i, (uid, details) in enumerate(rows, 1):
            name = await get_name(uid)
            msg += f"{i}. {name} — {details}\n"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== 11. ЕЖЕДНЕВНЫЕ И ЕЖЕНЕДЕЛЬНЫЕ ЗАДАНИЯ ====================

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

async def quest_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    
    # Ежедневные задания
    if text == "ежедневные задания":
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM daily_quests WHERE user_id = ? AND quest_date = ?", (user_id, today))
        row = c.fetchone()
        
        if not row:
            # Создаём задания
            quests = random.sample(DAILY_QUESTS_LIST, 5)
            c.execute("""INSERT INTO daily_quests (user_id, quest_date, quest1, quest2, quest3, quest4, quest5)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      (user_id, today, quests[0]["name"], quests[1]["name"], quests[2]["name"],
                       quests[3]["name"], quests[4]["name"]))
            conn.commit()
            c.execute("SELECT * FROM daily_quests WHERE user_id = ? AND quest_date = ?", (user_id, today))
            row = c.fetchone()
        
        conn.close()
        
        if row:
            msg = "📋 **ЕЖЕДНЕВНЫЕ ЗАДАНИЯ**\n\n"
            for i in range(1, 6):
                name = row[i]
                progress = row[i+5]
                completed = row[i+10]
                
                for q in DAILY_QUESTS_LIST:
                    if q["name"] == name:
                        if completed:
                            status = "✅ ВЫПОЛНЕНО"
                        else:
                            status = f"⏳ {progress}/{q['target']}"
                        msg += f"{i}. {name} — {status} (💰 {q['reward']})\n"
                        break
            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Еженедельные задания
    if text == "еженедельные задания":
        week = datetime.now().strftime("%Y-W%W")
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM weekly_quests WHERE user_id = ? AND quest_week = ?", (user_id, week))
        row = c.fetchone()
        
        if not row:
            # Создаём задания
            quests = random.sample(WEEKLY_QUESTS_LIST, 5)
            c.execute("""INSERT INTO weekly_quests (user_id, quest_week, quest1, quest2, quest3, quest4, quest5)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      (user_id, week, quests[0]["name"], quests[1]["name"], quests[2]["name"],
                       quests[3]["name"], quests[4]["name"]))
            conn.commit()
            c.execute("SELECT * FROM weekly_quests WHERE user_id = ? AND quest_week = ?", (user_id, week))
            row = c.fetchone()
        
        conn.close()
        
        if row:
            msg = "📋 **ЕЖЕНЕДЕЛЬНЫЕ ЗАДАНИЯ**\n\n"
            for i in range(1, 6):
                name = row[i]
                progress = row[i+5]
                completed = row[i+10]
                
                for q in WEEKLY_QUESTS_LIST:
                    if q["name"] == name:
                        if completed:
                            status = "✅ ВЫПОЛНЕНО"
                        else:
                            status = f"⏳ {progress}/{q['target']}"
                        msg += f"{i}. {name} — {status} (💰 {q['reward']})\n"
                        break
            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return

# ==================== 12. ВСЕ АЧИВКИ ====================

async def all_achievements_command(message):
    user_id = message.from_user.id
    msg = "🏆 **ВСЕ ДОСТИЖЕНИЯ**\n\n"
    
    for key, ach in ACHIEVEMENTS.items():
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM user_achievements WHERE user_id = ? AND achievement_name = ?", (user_id, key))
        unlocked = c.fetchone()
        conn.close()
        
        status = "✅" if unlocked else "🔒"
        msg += f"{status} {ach['name']} — {ach['desc']}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== 13. РУЛЕТКА ====================

async def roulette_game(message):
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        await message.reply("🔫 Ответь на сообщение соперника!\n📝 `рулетка`")
        return
    
    opponent_id = message.reply_to_message.from_user.id
    
    if opponent_id == user_id:
        await message.reply("❌ Нельзя с самим собой!")
        return
    
    # Создаём игру
    game_id = f"{message.chat.id}_{user_id}_{opponent_id}"
    roulette_games[game_id] = {
        "challenger": user_id,
        "opponent": opponent_id,
        "bullets": [0, 0, 0, 0, 0, 1],  # 1 боевой
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
        # Попал
        del roulette_games[game_id]
        winner = opponent_id if game["turn"] == player_id else player_id
        await bot.send_message(chat_id, f"🔫 **БАХ!**\n💀 {await get_name(game['turn'])} умер!\n🏆 {await get_name(winner)} победил!")
        await add_coins(winner, 100)
    else:
        # Холостой
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

# ==================== 14. ОСНОВНОЙ ОБРАБОТЧИК (ДОПОЛНЕНИЕ К ЧАСТИ 1) ====================

# Добавить в handle_all_messages в ЧАСТЬ 1:

# ===== КЛАНЫ =====
if text_lower.startswith(("создать клан", "вступить в клан", "мой клан", "кланы", "казна")):
    await clan_commands(message)
    return

# ===== КРЕДИТЫ =====
if text_lower.startswith(("кредит")):
    await loan_commands(message)
    return

# ===== ЛОТЕРЕЯ =====
if text_lower.startswith(("лотерея")):
    await lottery_commands(message)
    return

# ===== РЫНОК =====
if text_lower.startswith(("рынок", "купить акции", "продать акции", "мой портфель")):
    await stock_commands(message)
    return

# ===== НЕДВИЖИМОСТЬ =====
if text_lower.startswith(("недвижимость", "купить дом", "купить квартиру", "купить особняк", "моя недвижимость")):
    await property_commands(message)
    return

# ===== ФЕРМА =====
if text_lower.startswith(("ферма", "посадить", "собрать")):
    await farm_commands(message)
    return

# ===== РЫБАЛКА =====
if text_lower in ["рыбалка", "купить удочку"]:
    await fishing_commands(message)
    return

# ===== ОХОТА =====
if text_lower in ["охота", "купить ружьё"]:
    await hunting_commands(message)
    return

# ===== ТУРНИРЫ =====
if text_lower in ["турнир", "топ турниров"]:
    await tournament_commands(message)
    return

# ===== ЗАДАНИЯ =====
if text_lower in ["ежедневные задания", "еженедельные задания"]:
    await quest_commands(message)
    return

# ===== ВСЕ АЧИВКИ =====
if text_lower == "все ачивки":
    await all_achievements_command(message)
    return

# ===== РУЛЕТКА =====
if text_lower == "рулетка" and message.reply_to_message:
    await roulette_game(message)
    return
   # ==================== ЧАСТЬ 3: ДОПОЛНИТЕЛЬНЫЕ СИСТЕМЫ ====================

import random
import sqlite3
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

# ==================== 1. ПРОМО-КОДЫ ====================

active_promos = {}

async def promo_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Создать промо (только создатель)
    if text.startswith("создать промо"):
        if user_id != CREATOR_ID:
            await message.reply("❌ Только создатель может создавать промо-коды!")
            return
        
        if len(args) < 5:
            await message.reply("ℹ️ `создать промо [название] [монеты] [предмет] [количество]`\n"
                              "Пример: `создать промо новогодний 1000 алмаз 5`")
            return
        
        code = args[2]
        coins = int(args[3]) if args[3].isdigit() else 0
        item = args[4] if len(args) > 4 else None
        quantity = int(args[5]) if len(args) > 5 and args[5].isdigit() else 1
        
        active_promos[code] = {
            "coins": coins,
            "item": item,
            "quantity": quantity,
            "created_by": user_id,
            "created_at": datetime.now().isoformat(),
            "uses": 0,
            "max_uses": 1
        }
        
        await log_action(user_id, "create_promo", f"Создал промо-код {code}")
        await message.reply(f"✅ Промо-код **{code}** создан!\n"
                          f"💰 Монеты: {coins}\n"
                          f"🎒 Предмет: {item} x{quantity}")
        return
    
    # Активировать промо
    if text.startswith("активировать промо"):
        if len(args) < 3:
            await message.reply("ℹ️ `активировать промо [код]`")
            return
        
        code = args[2]
        
        if code not in active_promos:
            await message.reply(f"❌ Промо-код **{code}** не найден!")
            return
        
        promo = active_promos[code]
        
        # Проверяем использование
        if promo["uses"] >= promo["max_uses"]:
            await message.reply(f"❌ Промо-код **{code}** уже использован!")
            return
        
        # Выдаём награду
        if promo["coins"] > 0:
            await add_coins(user_id, promo["coins"])
        
        if promo["item"]:
            await add_item(user_id, promo["item"], promo["quantity"])
        
        promo["uses"] += 1
        
        await log_action(user_id, "activate_promo", f"Активировал промо-код {code}")
        await message.reply(f"✅ Промо-код **{code}** активирован!\n"
                          f"💰 Монеты: +{promo['coins']}\n"
                          f"🎒 Предмет: {promo['item']} x{promo['quantity']}")
        
        # Удаляем если использован
        if promo["uses"] >= promo["max_uses"]:
            del active_promos[code]
        return
    
    # Список промо
    if text == "список промо":
        if user_id != CREATOR_ID:
            await message.reply("❌ Только создатель может просматривать промо-коды!")
            return
        
        if not active_promos:
            await message.reply("📭 Нет активных промо-кодов!")
            return
        
        msg = "📋 **АКТИВНЫЕ ПРОМО-КОДЫ**\n\n"
        for code, data in active_promos.items():
            msg += f"🔑 **{code}**\n"
            msg += f"💰 Монеты: {data['coins']}\n"
            msg += f"🎒 Предмет: {data['item']} x{data['quantity']}\n"
            msg += f"📊 Использований: {data['uses']}/{data['max_uses']}\n\n"
        
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Удалить промо
    if text.startswith("удалить промо"):
        if user_id != CREATOR_ID:
            await message.reply("❌ Только создатель может удалять промо-коды!")
            return
        
        if len(args) < 3:
            await message.reply("ℹ️ `удалить промо [код]`")
            return
        
        code = args[2]
        
        if code not in active_promos:
            await message.reply(f"❌ Промо-код **{code}** не найден!")
            return
        
        del active_promos[code]
        await message.reply(f"✅ Промо-код **{code}** удалён!")

# ==================== 2. КОРАБЛИ (ПОЛНАЯ СИСТЕМА) ====================

SHIP_UPGRADES_FULL = {
    "паруса": {"price": 50000, "effect": "speed", "bonus": 10, "emoji": "⛵", "desc": "-10% времени пути"},
    "карта": {"price": 10000, "effect": "risk", "bonus": 5, "emoji": "🗺️", "desc": "-5% риск"},
    "компас": {"price": 15000, "effect": "risk", "bonus": 5, "emoji": "🧭", "desc": "-5% риск"},
    "радар": {"price": 20000, "effect": "risk", "bonus": 5, "emoji": "📡", "desc": "-5% риск"},
    "бронированный корабль": {"price": 80000, "effect": "defense", "bonus": 40, "emoji": "🛡️", "desc": "+40% защита от пиратов, +30% риск утонуть"}
}

# Глобальные переменные для кораблей
ship_expeditions = {}

async def ship_full_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Купить корабль
    if text == "купить корабль":
        if await has_item(user_id, "корабль"):
            await message.reply("❌ У тебя уже есть корабль!")
            return
        
        price = 100000
        coins = await get_coins(user_id)
        if coins < price:
            await message.reply(f"❌ Нужно {price} монет! У тебя {coins}")
            return
        
        await remove_coins(user_id, price)
        await add_item(user_id, "корабль")
        await log_action(user_id, "buy_ship", "Купил корабль")
        await message.reply(f"⛵ **Корабль** куплен за {price} монет!\n📝 Команды: `мой корабль`, `отправить [товар] [количество]`")
        return
    
    # Отправить в экспедицию
    if text.startswith("отправить"):
        if not await has_item(user_id, "корабль"):
            await message.reply("❌ У тебя нет корабля! Купи: `купить корабль`")
            return
        
        if len(args) < 3:
            await message.reply("ℹ️ `отправить [товар] [количество]`\n📝 Доступные товары: `товары`")
            return
        
        if user_id in ship_expeditions:
            await message.reply("❌ Корабль уже в экспедиции!")
            return
        
        goods = args[1].lower()
        try:
            quantity = int(args[2])
            if quantity <= 0:
                await message.reply("❌ Количество должно быть > 0!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        # Проверяем товар
        if goods not in TRADE_GOODS:
            await message.reply(f"❌ Товар '{goods}' не найден!\n📝 Список: `товары`")
            return
        
        # Проверяем наличие в инвентаре
        if not await has_item(user_id, goods):
            await message.reply(f"❌ У тебя нет {goods.capitalize()}!")
            return
        
        await remove_item(user_id, goods, quantity)
        
        # Улучшения корабля
        upgrades = await get_ship_upgrades(user_id)
        stats = {"speed": 0, "risk": 0, "defense": 0}
        for upgrade in upgrades:
            data = SHIP_UPGRADES_FULL.get(upgrade)
            if data:
                if data["effect"] == "speed":
                    stats["speed"] += data["bonus"]
                elif data["effect"] == "risk":
                    stats["risk"] += data["bonus"]
                elif data["effect"] == "defense":
                    stats["defense"] += data["bonus"]
        
        # Время в пути (база 30 мин - скорость)
        base_time = 1800  # 30 минут
        time_reduction = stats["speed"]
        travel_time = max(300, base_time - int(base_time * time_reduction / 100))
        
        ship_expeditions[user_id] = {
            "goods": goods,
            "quantity": quantity,
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(seconds=travel_time),
            "stats": stats
        }
        
        await log_action(user_id, "ship_expedition", f"Отправил {quantity}x {goods}")
        await message.reply(f"⛵ **ЭКСПЕДИЦИЯ ОТПРАВЛЕНА!**\n"
                          f"📦 Товар: {goods.capitalize()} x{quantity}\n"
                          f"⏳ Время: {travel_time//60} минут\n"
                          f"🛡️ Защита: +{stats['defense']}%\n"
                          f"🎯 Риск: -{stats['risk']}%")
        
        asyncio.create_task(ship_arrival(user_id))
        return
    
    # Мой корабль (статус)
    if text == "мой корабль":
        if not await has_item(user_id, "корабль"):
            await message.reply("❌ У тебя нет корабля! Купи: `купить корабль`")
            return
        
        if user_id in ship_expeditions:
            exp = ship_expeditions[user_id]
            remaining = int((exp["end_time"] - datetime.now()).total_seconds())
            msg = "⛵ **КОРАБЛЬ В ПУТИ**\n\n"
            msg += f"📦 Товар: {exp['goods'].capitalize()} x{exp['quantity']}\n"
            msg += f"⏳ Осталось: {remaining//60} мин {remaining%60} сек\n"
            msg += f"🛡️ Защита: +{exp['stats']['defense']}%\n"
            msg += f"🎯 Риск: -{exp['stats']['risk']}%"
            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        else:
            # Показываем улучшения
            upgrades = await get_ship_upgrades(user_id)
            stats = await get_ship_stats(user_id)
            
            msg = "⛵ **МОЙ КОРАБЛЬ**\n\n"
            msg += f"⚡ Скорость: -{stats['speed']}% времени\n"
            msg += f"🗺️ Навигация: -{stats['risk']}% риск\n"
            msg += f"🛡️ Защита: +{stats['defense']}% защита\n\n"
            
            if upgrades:
                msg += "🛠️ **УЛУЧШЕНИЯ:**\n"
                for upgrade in upgrades:
                    data = SHIP_UPGRADES_FULL.get(upgrade)
                    if data:
                        msg += f"{data['emoji']} {upgrade.capitalize()}\n"
            else:
                msg += "❌ Нет улучшений\n\n"
            
            msg += "📝 `отправить [товар] [количество]`"
            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return

async def ship_arrival(user_id):
    """Прибытие корабля из экспедиции"""
    await asyncio.sleep(1800)  # 30 минут
    
    if user_id not in ship_expeditions:
        return
    
    exp = ship_expeditions.pop(user_id)
    goods = exp["goods"]
    quantity = exp["quantity"]
    stats = exp["stats"]
    
    # Генерируем событие
    events = [
        {"name": "пираты", "chance": 20, "loss": 50},
        {"name": "шторм", "chance": 30, "loss": 30},
        {"name": "удача", "chance": 20, "bonus": 50},
        {"name": "остров сокровищ", "chance": 10, "bonus": 100},
        {"name": "спокойное море", "chance": 20, "bonus": 0}
    ]
    
    # Защита снижает шанс плохих событий
    defense = stats.get("defense", 0)
    risk = stats.get("risk", 0)
    
    # Выбираем событие
    rolled = random.randint(1, 100)
    event = None
    current = 0
    
    for e in events:
        chance = e["chance"]
        if e["name"] in ["пираты", "шторм"]:
            chance = max(5, chance - defense // 5)
        elif e["name"] in ["удача", "остров сокровищ"]:
            chance = min(50, chance + risk // 5)
        
        current += chance
        if rolled <= current:
            event = e
            break
    
    if not event:
        event = {"name": "спокойное море", "bonus": 0}
    
    # Результат
    goods_data = TRADE_GOODS.get(goods)
    if not goods_data:
        await bot.send_message(user_id, "❌ Ошибка!")
        return
    
    base_profit = goods_data["sell"] * quantity
    
    if event["name"] in ["пираты", "шторм"]:
        loss_percent = event.get("loss", 30)
        profit = int(base_profit * (100 - loss_percent) / 100)
        msg = f"⚠️ **{event['name'].capitalize()}!**\n"
        msg += f"📉 Потеряно {loss_percent}% товара\n"
        if profit > 0:
            msg += f"💰 Прибыль: +{profit} монет"
            await add_coins(user_id, profit)
        else:
            msg += f"💀 Всё потеряно!"
    elif event["name"] in ["удача", "остров сокровищ"]:
        bonus = event.get("bonus", 50)
        profit = int(base_profit * (100 + bonus) / 100)
        msg = f"🍀 **{event['name'].capitalize()}!**\n"
        msg += f"💰 Прибыль: +{profit} монет (+{bonus}%)"
        await add_coins(user_id, profit)
    else:
        profit = base_profit
        msg = f"✅ **{event['name'].capitalize()}**\n"
        msg += f"💰 Прибыль: +{profit} монет"
        await add_coins(user_id, profit)
    
    await bot.send_message(user_id, f"⛵ **ЭКСПЕДИЦИЯ ЗАВЕРШЕНА!**\n\n{msg}")

# ==================== 3. ДУЭЛЬ ====================

active_duels = {}

async def duel_commands(message):
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        await message.reply("⚔️ Ответь на сообщение соперника!\n📝 `дуэль`")
        return
    
    opponent_id = message.reply_to_message.from_user.id
    
    if opponent_id == user_id:
        await message.reply("❌ Нельзя с самим собой!")
        return
    
    # Проверяем, не в дуэли ли уже
    for duel in active_duels.values():
        if user_id in [duel["challenger"], duel["opponent"]]:
            await message.reply("❌ Ты уже в дуэли!")
            return
    
    game_id = f"{message.chat.id}_{user_id}_{opponent_id}"
    
    active_duels[game_id] = {
        "challenger": user_id,
        "opponent": opponent_id,
        "turn": user_id,
        "health": 100,
        "status": "waiting"
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("⚔️ ПРИНЯТЬ", callback_data=f"duel_yes_{message.chat.id}_{user_id}_{opponent_id}"),
         InlineKeyboardButton("❌ ОТКАЗ", callback_data=f"duel_no_{message.chat.id}_{user_id}_{opponent_id}")]
    ])
    
    await message.reply(f"⚔️ {await get_name(user_id)} вызывает {await get_name(opponent_id)} на дуэль!", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("duel_yes_"))
async def duel_accept(callback):
    data = callback.data.split("_")
    chat_id = int(data[1])
    challenger = int(data[2])
    opponent = int(data[3])
    
    if callback.from_user.id != opponent:
        await callback.answer("❌ Не тебе!")
        return
    
    game_id = f"{chat_id}_{challenger}_{opponent}"
    active_duels[game_id]["status"] = "active"
    await callback.message.edit_text(f"⚔️ **ДУЭЛЬ НАЧАЛАСЬ!**\n\n{await get_name(challenger)} ❤️100\n{await get_name(opponent)} ❤️100")
    await duel_turn(chat_id, game_id)

async def duel_turn(chat_id, game_id):
    duel = active_duels.get(game_id)
    if not duel:
        return
    
    if duel["status"] == "finished":
        return
    
    player = duel["turn"]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("⚔️ АТАКА", callback_data=f"duel_attack_{game_id}_{player}"),
         InlineKeyboardButton("🛡️ ЗАЩИТА", callback_data=f"duel_defend_{game_id}_{player}")]
    ])
    
    await bot.send_message(chat_id, f"⚔️ **Ход {await get_name(player)}**", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("duel_attack_"))
async def duel_attack(callback):
    data = callback.data.split("_")
    game_id = data[2]
    player = int(data[3])
    
    duel = active_duels.get(game_id)
    if not duel or duel["status"] != "active":
        await callback.answer("❌ Дуэль завершена!")
        return
    
    if callback.from_user.id != player:
        await callback.answer("❌ Не твой ход!")
        return
    
    opponent = duel["challenger"] if player == duel["opponent"] else duel["opponent"]
    damage = random.randint(10, 30)
    duel["health"] -= damage
    duel["turn"] = opponent
    
    if duel["health"] <= 0:
        duel["status"] = "finished"
        winner = opponent
        await callback.message.edit_text(f"⚔️ **ДУЭЛЬ ЗАВЕРШЕНА!**\n\n"
                                        f"🏆 **{await get_name(winner)}** победил!\n"
                                        f"❤️ {await get_name(player)}: 0\n"
                                        f"❤️ {await get_name(winner)}: {duel['health'] + damage}")
        await add_coins(winner, 100)
        del active_duels[game_id]
        return
    
    await callback.message.edit_text(f"⚔️ **ДУЭЛЬ**\n\n"
                                    f"{await get_name(player)} атакует!\n"
                                    f"❤️ {await get_name(player)}: {duel['health']}\n"
                                    f"❤️ {await get_name(opponent)}: {duel['health'] + damage}")
    await duel_turn(callback.message.chat.id, game_id)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("duel_defend_"))
async def duel_defend(callback):
    data = callback.data.split("_")
    game_id = data[2]
    player = int(data[3])
    
    duel = active_duels.get(game_id)
    if not duel or duel["status"] != "active":
        await callback.answer("❌ Дуэль завершена!")
        return
    
    if callback.from_user.id != player:
        await callback.answer("❌ Не твой ход!")
        return
    
    opponent = duel["challenger"] if player == duel["opponent"] else duel["opponent"]
    heal = random.randint(5, 15)
    duel["health"] = min(100, duel["health"] + heal)
    duel["turn"] = opponent
    
    await callback.message.edit_text(f"🛡️ **{await get_name(player)}** защищается!\n"
                                    f"❤️ {await get_name(player)}: {duel['health']}")
    await duel_turn(callback.message.chat.id, game_id)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("duel_no_"))
async def duel_decline(callback):
    data = callback.data.split("_")
    opponent = int(data[3])
    
    if callback.from_user.id != opponent:
        await callback.answer("❌ Не тебе!")
        return
    
    await callback.message.edit_text("❌ Отказ!")

# ==================== 4. КРАФТ ====================

CRAFT_RECIPES = {
    "золотая монета": {"resources": {"золото": 5}, "desc": "Сделать золотую монету"},
    "алмаз": {"resources": {"камень": 10, "золото": 5}, "desc": "Сделать алмаз"},
    "щит": {"resources": {"металл": 5, "дерево": 3}, "desc": "Сделать щит"},
    "бронежилет": {"resources": {"металл": 8, "кожа": 5}, "desc": "Сделать бронежилет"},
    "амулет удачи": {"resources": {"золото": 3, "алмаз": 1}, "desc": "Сделать амулет удачи"}
}

async def craft_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Список рецептов
    if text == "рецепты":
        msg = "🔧 **РЕЦЕПТЫ КРАФТА**\n\n"
        for item, recipe in CRAFT_RECIPES.items():
            msg += f"🔹 **{item.capitalize()}**\n"
            msg += f"   📝 {recipe['desc']}\n"
            msg += f"   📦 Ресурсы:\n"
            for res, qty in recipe["resources"].items():
                msg += f"      • {res.capitalize()}: {qty} шт\n"
            msg += "\n"
        msg += "📝 `скрафтить [предмет]`"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Скрафтить
    if text.startswith("скрафтить"):
        if len(args) < 2:
            await message.reply("ℹ️ `скрафтить [предмет]`")
            return
        
        item = args[1].lower()
        if item not in CRAFT_RECIPES:
            await message.reply(f"❌ Рецепт '{item}' не найден!\n📝 Список: `рецепты`")
            return
        
        recipe = CRAFT_RECIPES[item]
        
        # Проверяем ресурсы
        for res, qty in recipe["resources"].items():
            if not await has_item(user_id, res):
                await message.reply(f"❌ Не хватает {res.capitalize()}! Нужно {qty} шт")
                return
            if await has_item(user_id, res) < qty:
                await message.reply(f"❌ Не хватает {res.capitalize()}! Нужно {qty} шт")
                return
        
        # Забираем ресурсы
        for res, qty in recipe["resources"].items():
            await remove_item(user_id, res, qty)
        
        # Даём предмет
        await add_item(user_id, item, 1)
        await log_action(user_id, "craft", f"Скрафтил {item}")
        await message.reply(f"✅ **{item.capitalize()}** скрафчен!")

# ==================== 5. ПИТОМЦЫ ====================

PET_TYPES = {
    "собака": {"price": 10000, "emoji": "🐕", "bonus": "защита", "desc": "Защищает от грабежа"},
    "кот": {"price": 8000, "emoji": "🐱", "bonus": "удача", "desc": "Приносит удачу"},
    "орёл": {"price": 20000, "emoji": "🦅", "bonus": "охота", "desc": "Помогает в охоте"},
    "волк": {"price": 25000, "emoji": "🐺", "bonus": "война", "desc": "Помогает в битвах"},
    "дракон": {"price": 50000, "emoji": "🐉", "bonus": "всё", "desc": "Помогает во всём"}
}

user_pets = {}

async def pet_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Купить питомца
    if text.startswith("купить питомца"):
        if len(args) < 3:
            await message.reply("ℹ️ `купить питомца [тип]`\n📝 Типы: собака, кот, орёл, волк, дракон")
            return
        
        pet_type = args[2].lower()
        if pet_type not in PET_TYPES:
            await message.reply(f"❌ Питомец '{pet_type}' не найден!")
            return
        
        if user_id in user_pets:
            await message.reply("❌ У тебя уже есть питомец!")
            return
        
        data = PET_TYPES[pet_type]
        coins = await get_coins(user_id)
        
        if coins < data["price"]:
            await message.reply(f"❌ Нужно {data['price']} монет! У тебя {coins}")
            return
        
        await remove_coins(user_id, data["price"])
        
        # Создаём питомца
        user_pets[user_id] = {
            "type": pet_type,
            "name": pet_type.capitalize(),
            "happiness": 100,
            "level": 1
        }
        
        await log_action(user_id, "buy_pet", f"Купил питомца {pet_type}")
        await message.reply(f"✅ {data['emoji']} **{pet_type.capitalize()}** куплен!\n📝 {data['desc']}\n\n"
                          f"📝 `покормить` — поднять счастье\n"
                          f"📝 `питомец` — статус питомца")
        return
    
    # Питомец (статус)
    if text == "питомец":
        if user_id not in user_pets:
            await message.reply("❌ У тебя нет питомца! Купи: `купить питомца [тип]`")
            return
        
        pet = user_pets[user_id]
        data = PET_TYPES[pet["type"]]
        
        msg = f"{data['emoji']} **{pet['name']}**\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 Тип: {pet['type'].capitalize()}\n"
        msg += f"❤️ Счастье: {pet['happiness']}/100\n"
        msg += f"📈 Уровень: {pet['level']}\n"
        msg += f"🎯 Бонус: {data['desc']}\n\n"
        
        if pet["happiness"] < 30:
            msg += "⚠️ Питомец голоден! Покорми: `покормить`"
        else:
            msg += "😊 Питомец счастлив!"
        
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Покормить
    if text == "покормить":
        if user_id not in user_pets:
            await message.reply("❌ У тебя нет питомца!")
            return
        
        pet = user_pets[user_id]
        if pet["happiness"] >= 100:
            await message.reply("😊 Питомец уже сыт!")
            return
        
        pet["happiness"] = min(100, pet["happiness"] + 20)
        await message.reply(f"🍖 {pet['name']} покормлен! ❤️ {pet['happiness']}/100")
        return

async def get_pet_bonus(user_id):
    """Получить бонус от питомца"""
    if user_id not in user_pets:
        return 0
    
    pet = user_pets[user_id]
    if pet["happiness"] < 30:
        return 0
    
    data = PET_TYPES.get(pet["type"])
    if not data:
        return 0
    
    # Бонус зависит от счастья
    return int(pet["happiness"] / 10)

# ==================== 6. ЭКОНОМИЧЕСКИЕ СОБЫТИЯ ====================

ECONOMY_EVENTS_FULL = {
    "инфляция": {"multiplier": 0.8, "desc": "💰 Инфляция! Доходы -20%", "duration": 3600},
    "дефляция": {"multiplier": 1.2, "desc": "💎 Дефляция! Доходы +20%", "duration": 3600},
    "кризис": {"multiplier": 0.5, "desc": "📉 Кризис! Доходы -50%", "duration": 7200},
    "бум": {"multiplier": 1.5, "desc": "📈 Бум! Доходы +50%", "duration": 7200},
    "золотой дождь": {"multiplier": 2.0, "desc": "🌟 Золотой дождь! Доходы x2", "duration": 3600}
}

active_economy_event = None

async def economy_commands(message):
    global active_economy_event
    text = message.text.lower()
    user_id = message.from_user.id
    
    if user_id != CREATOR_ID:
        await message.reply("❌ Только создатель может управлять экономикой!")
        return
    
    # Старт события
    if text.startswith("эконом старт"):
        event_type = text.split()[2] if len(text.split()) > 2 else None
        if not event_type:
            await message.reply("ℹ️ `эконом старт [инфляция|дефляция|кризис|бум|золотой дождь]`")
            return
        
        if event_type not in ECONOMY_EVENTS_FULL:
            await message.reply(f"❌ Событие '{event_type}' не найдено!")
            return
        
        active_economy_event = {
            "type": event_type,
            "data": ECONOMY_EVENTS_FULL[event_type],
            "started": datetime.now()
        }
        
        await log_action(user_id, "economy_event", f"Запустил {event_type}")
        await message.reply(f"✅ **{event_type.capitalize()}** запущена!\n{ECONOMY_EVENTS_FULL[event_type]['desc']}")
        return
    
    # Стоп события
    if text == "эконом стоп":
        if not active_economy_event:
            await message.reply("❌ Нет активных событий!")
            return
        
        active_economy_event = None
        await message.reply("✅ Событие остановлено!")
        return
    
    # Статус события
    if text == "эконом статус":
        if not active_economy_event:
            await message.reply("❌ Нет активных событий!")
            return
        
        event = active_economy_event
        elapsed = (datetime.now() - event["started"]).total_seconds()
        remaining = max(0, event["data"]["duration"] - elapsed)
        
        await message.reply(f"📊 **Активное событие:** {event['type'].capitalize()}\n"
                          f"📝 {event['data']['desc']}\n"
                          f"⏳ Осталось: {int(remaining//60)} мин",
                          parse_mode=ParseMode.MARKDOWN)
        return

def get_economy_multiplier():
    if active_economy_event:
        return active_economy_event["data"]["multiplier"]
    return 1.0

# ==================== 7. МОДЕРАЦИЯ (РАСШИРЕННАЯ) ====================

async def moderation_full_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    chat_id = message.chat.id
    args = text.split()
    
    level, _ = await get_level(user_id)
    if level < 10:
        await message.reply("❌ Недостаточно прав!")
        return
    
    # Бан на время
    if text.startswith("бан "):
        if len(args) < 3:
            await message.reply("ℹ️ `бан @user [время]`\n"
                              "⏳ Формат: 1м, 1ч, 1д, 1н, 1г\n"
                              "Пример: `бан @user 1ч`")
            return
        
        try:
            member = await message.chat.get_member(args[1].replace("@", ""))
            target_id = member.user.id
            
            time_str = args[2]
            duration = parse_time(time_str)
            
            if duration is None:
                await message.reply("❌ Неверный формат времени! Используй: 1м, 1ч, 1д, 1н, 1г")
                return
            
            await bot.ban_chat_member(chat_id, target_id)
            
            # Разбан через время
            if duration > 0:
                asyncio.create_task(unban_after_time(chat_id, target_id, duration))
            
            await log_action(user_id, "ban_time", f"Забанил {await get_name(target_id)} на {time_str}")
            await message.reply(f"🔨 {member.user.first_name} забанен на {time_str}!")
        except:
            await message.reply("❌ Не найден!")
        return
    
    # Мут на время
    if text.startswith("мут "):
        if len(args) < 3:
            await message.reply("ℹ️ `мут @user [время]`\n"
                              "⏳ Формат: 1м, 1ч, 1д, 1н, 1г\n"
                              "Пример: `мут @user 1ч`")
            return
        
        try:
            member = await message.chat.get_member(args[1].replace("@", ""))
            target_id = member.user.id
            
            time_str = args[2]
            duration = parse_time(time_str)
            
            if duration is None:
                await message.reply("❌ Неверный формат времени!")
                return
            
            await bot.restrict_chat_member(chat_id, target_id,
                                          permissions=ChatPermissions(can_send_messages=False))
            
            if duration > 0:
                asyncio.create_task(unmute_after_time(chat_id, target_id, duration))
            
            await log_action(user_id, "mute_time", f"Замутил {await get_name(target_id)} на {time_str}")
            await message.reply(f"🔇 {member.user.first_name} замучен на {time_str}!")
        except:
            await message.reply("❌ Не найден!")
        return
    
    # Список забаненых
    if text == "список банов":
        # TODO: хранить баны в БД
        await message.reply("📋 Список забаненых в разработке...")

def parse_time(time_str):
    """Преобразует строку времени в секунды"""
    if time_str.endswith("м"):
        return int(time_str[:-1]) * 60
    elif time_str.endswith("ч"):
        return int(time_str[:-1]) * 3600
    elif time_str.endswith("д"):
        return int(time_str[:-1]) * 86400
    elif time_str.endswith("н"):
        return int(time_str[:-1]) * 604800
    elif time_str.endswith("г"):
        return int(time_str[:-1]) * 31536000
    return None

async def unban_after_time(chat_id, user_id, duration):
    await asyncio.sleep(duration)
    try:
        await bot.unban_chat_member(chat_id, user_id)
    except:
        pass

async def unmute_after_time(chat_id, user_id, duration):
    await asyncio.sleep(duration)
    try:
        await bot.restrict_chat_member(chat_id, user_id,
                                      permissions=ChatPermissions(
                                          can_send_messages=True,
                                          can_send_media_messages=True,
                                          can_send_other_messages=True,
                                          can_add_web_page_previews=True))
    except:
        pass

# ==================== 8. АУКЦИОН ====================

active_auctions = {}
auction_bids = {}

async def auction_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Выставить на аукцион
    if text.startswith("аукцион выставить"):
        if len(args) < 4:
            await message.reply("ℹ️ `аукцион выставить [предмет] [цена]`")
            return
        
        item = args[2].lower()
        try:
            price = int(args[3])
            if price <= 0:
                await message.reply("❌ Цена должна быть > 0!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        # Проверяем наличие предмета
        if not await has_item(user_id, item):
            await message.reply(f"❌ У тебя нет {item.capitalize()}!")
            return
        
        await remove_item(user_id, item, 1)
        
        # Создаём аукцион
        auction_id = f"{item}_{int(datetime.now().timestamp())}"
        
        active_auctions[auction_id] = {
            "seller": user_id,
            "item": item,
            "price": price,
            "current_bid": price,
            "bidder": None,
            "ends_at": datetime.now() + timedelta(hours=24),
            "status": "active"
        }
        
        auction_bids[auction_id] = []
        
        await log_action(user_id, "auction_start", f"Выставил {item} на аукцион за {price}")
        await message.reply(f"✅ **{item.capitalize()}** выставлен на аукцион!\n"
                          f"💰 Стартовая цена: {price} монет\n"
                          f"⏳ Длительность: 24 часа\n"
                          f"📝 `ставка {auction_id} [сумма]`")
        return
    
    # Сделать ставку
    if text.startswith("ставка"):
        if len(args) < 3:
            await message.reply("ℹ️ `ставка [id аукциона] [сумма]`")
            return
        
        auction_id = args[1]
        try:
            bid = int(args[2])
            if bid <= 0:
                await message.reply("❌ Сумма должна быть > 0!")
                return
        except:
            await message.reply("❌ Введи число!")
            return
        
        if auction_id not in active_auctions:
            await message.reply("❌ Аукцион не найден!")
            return
        
        auction = active_auctions[auction_id]
        
        if auction["seller"] == user_id:
            await message.reply("❌ Нельзя ставить на свой лот!")
            return
        
        if bid <= auction["current_bid"]:
            await message.reply(f"❌ Минимальная ставка: {auction['current_bid'] + 1}")
            return
        
        coins = await get_coins(user_id)
        if coins < bid:
            await message.reply(f"❌ У тебя только {coins} монет!")
            return
        
        # Возвращаем предыдущему лидеру
        if auction["bidder"]:
            await add_coins(auction["bidder"], auction["current_bid"])
        
        auction["current_bid"] = bid
        auction["bidder"] = user_id
        auction_bids[auction_id].append({"user": user_id, "bid": bid, "time": datetime.now().isoformat()})
        
        await log_action(user_id, "auction_bid", f"Сделал ставку {bid} на {auction_id}")
        await message.reply(f"✅ Ставка **{bid}** монет принята!\n"
                          f"📦 Лот: {auction['item'].capitalize()}\n"
                          f"👤 Твой лидер")
        return
    
    # Список аукционов
    if text == "аукционы":
        if not active_auctions:
            await message.reply("📭 Нет активных аукционов!")
            return
        
        msg = "📋 **АКТИВНЫЕ АУКЦИОНЫ**\n\n"
        for aid, data in active_auctions.items():
            if data["status"] == "active":
                msg += f"🔹 **{data['item'].capitalize()}**\n"
                msg += f"   ID: {aid[:8]}...\n"
                msg += f"   💰 Текущая ставка: {data['current_bid']}\n"
                msg += f"   👤 Лидер: {await get_name(data['bidder']) if data['bidder'] else 'Нет'}\n"
                msg += f"   ⏳ Осталось: {int((data['ends_at'] - datetime.now()).total_seconds()//3600)}ч\n\n"
        
        msg += "📝 `ставка [id] [сумма]`"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return

# ==================== 9. ГЛОБАЛЬНЫЙ ЧАТ ====================

global_chat_enabled = False

async def global_chat_commands(message):
    global global_chat_enabled
    text = message.text.lower()
    user_id = message.from_user.id
    
    if text == "глобал чат вкл":
        if user_id != CREATOR_ID:
            await message.reply("❌ Только создатель!")
            return
        
        global_chat_enabled = True
        await message.reply("✅ Глобальный чат включён!\n📝 Пиши `глобал [сообщение]`")
        return
    
    if text == "глобал чат выкл":
        if user_id != CREATOR_ID:
            await message.reply("❌ Только создатель!")
            return
        
        global_chat_enabled = False
        await message.reply("❌ Глобальный чат выключен!")
        return
    
    if text.startswith("глобал ") and global_chat_enabled:
        msg = text[7:].strip()
        if msg:
            # Отправляем во все чаты где есть бот
            # TODO: реализовать рассылку по всем чатам
            await message.reply(f"🌍 **ГЛОБАЛЬНОЕ СООБЩЕНИЕ ОТ {await get_name(user_id)}**\n{msg}")

# ==================== 10. СЕЗОНЫ ====================

seasons = {
    "зима": {"emoji": "❄️", "bonus": 0.8, "desc": "Зимний сезон! Доходы -20%"},
    "весна": {"emoji": "🌸", "bonus": 1.0, "desc": "Весенний сезон! Доходы нормальные"},
    "лето": {"emoji": "☀️", "bonus": 1.2, "desc": "Летний сезон! Доходы +20%"},
    "осень": {"emoji": "🍂", "bonus": 0.9, "desc": "Осенний сезон! Доходы -10%"}
}

current_season = "весна"

async def season_commands(message):
    global current_season
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    if text == "сезон":
        season = seasons[current_season]
        await message.reply(f"{season['emoji']} **СЕЗОН: {current_season.upper()}**\n"
                          f"📝 {season['desc']}\n"
                          f"📊 Бонус: {season['bonus']}x")
        return
    
    if text.startswith("сезон установить"):
        if user_id != CREATOR_ID:
            await message.reply("❌ Только создатель!")
            return
        
        if len(args) < 3:
            await message.reply("ℹ️ `сезон установить [зима|весна|лето|осень]`")
            return
        
        season = args[2].lower()
        if season not in seasons:
            await message.reply(f"❌ Сезон '{season}' не найден!")
            return
        
        current_season = season
        await message.reply(f"✅ Установлен сезон **{season.capitalize()}**!\n{seasons[season]['desc']}")

def get_season_multiplier():
    return seasons[current_season]["bonus"]

# ==================== 11. БАНК 2.0 (ПРОЦЕНТЫ) ====================

async def bank_interest_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    # Информация о банке
    if text == "банк":
        bank = await get_bank(user_id)
        msg = "🏦 **БАНК**\n\n"
        msg += f"💰 На счету: **{bank}** монет\n"
        msg += f"📈 Процент: **5%** в день\n"
        msg += f"💡 Вкладывай и получай пассивный доход!\n\n"
        msg += "📝 `положить [сумма]` — пополнить\n"
        msg += "📝 `снять [сумма]` — снять\n"
        msg += "📝 `проценты` — начислить проценты"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Начислить проценты
    if text == "проценты":
        bank = await get_bank(user_id)
        if bank <= 0:
            await message.reply("❌ На счету нет монет!")
            return
        
        interest = int(bank * 0.05)  # 5%
        if interest < 1:
            await message.reply("❌ Слишком мало для процентов!")
            return
        
        await add_bank(user_id, interest)
        await log_action(user_id, "bank_interest", f"Начислены проценты {interest}")
        await message.reply(f"🏦 Начислены проценты: +{interest} монет (5%)")

# ==================== 12. ЗАПУСК ТРЕТЬЕЙ ЧАСТИ ====================

# Добавить в ОСНОВНОЙ ОБРАБОТЧИК (ЧАСТЬ 1 + ЧАСТЬ 2 + ЧАСТЬ 3):

# ===== ПРОМО =====
if text_lower.startswith(("создать промо", "активировать промо", "список промо", "удалить промо")):
    await promo_commands(message)
    return

# ===== КОРАБЛИ (ПОЛНЫЕ) =====
if text_lower.startswith(("купить корабль", "отправить", "мой корабль")):
    await ship_full_commands(message)
    return

# ===== ДУЭЛЬ =====
if text_lower == "дуэль" and message.reply_to_message:
    await duel_commands(message)
    return

# ===== КРАФТ =====
if text_lower.startswith(("рецепты", "скрафтить")):
    await craft_commands(message)
    return

# ===== ПИТОМЦЫ =====
if text_lower.startswith(("купить питомца", "питомец", "покормить")):
    await pet_commands(message)
    return

# ===== ЭКОНОМИКА =====
if text_lower.startswith(("эконом")):
    await economy_commands(message)
    return

# ===== МОДЕРАЦИЯ (РАСШИРЕННАЯ) =====
if text_lower.startswith(("бан ", "мут ", "список банов")):
    await moderation_full_commands(message)
    return

# ===== АУКЦИОН =====
if text_lower.startswith(("аукцион", "ставка")):
    await auction_commands(message)
    return

# ===== ГЛОБАЛЬНЫЙ ЧАТ =====
if text_lower.startswith(("глобал", "глобал чат")):
    await global_chat_commands(message)
    return

# ===== СЕЗОНЫ =====
if text_lower.startswith(("сезон")):
    await season_commands(message)
    return

# ===== БАНК 2.0 =====
if text_lower in ["банк", "проценты"]:
    await bank_interest_commands(message)
    return
 # ==================== ЗАПУСК ====================

async def main():
    print(f"✅ {BOT_NAME} запущен!")
    print(f"👑 Создатель: {CREATOR_ID}")
    print(f"💼 Работ: {len(JOBS)}")
    print(f"🏪 Бизнесов: {len(BUSINESSES)}")
    print(f"🔥 Лимиток: {len(LIMITED_ITEMS)}")
    print("⏳ Бот запускается...")
    
    init_db()
    init_limited_items()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
