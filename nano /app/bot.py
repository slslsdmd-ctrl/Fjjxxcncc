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

# ==================== ТОКЕН ====================
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не задан!")
    print("📝 Установи: export BOT_TOKEN='твой_токен'")
    exit(1)

BOT_NAME = "Fable"
CREATOR_ID = 8039111975  # ЗАМЕНИ НА СВОЙ ID

ADMINS = [CREATOR_ID]

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
cooldowns = {}
daily_cooldown = {}
cube_games = {}
roulette_games = {}
active_duels = {}
rep_cooldown = {}
marriage_proposals = {}
user_pets = {}
tournaments = {}
active_economy_event = None
active_promos = {}
ship_expeditions = {}
active_auctions = {}
auction_bids = {}
global_chat_enabled = False
current_season = "весна"
knb_choices = {}
active_knb = set()

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
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
        created_at TEXT,
        last_message_time TEXT,
        daily_messages INTEGER DEFAULT 0,
        last_daily_reset TEXT,
        referrer_id INTEGER DEFAULT 0,
        ref_count INTEGER DEFAULT 0,
        vip INTEGER DEFAULT 0,
        vip_until TEXT,
        admin_level INTEGER DEFAULT 1,
        house INTEGER DEFAULT 0,
        house_level INTEGER DEFAULT 1,
        car INTEGER DEFAULT 0,
        car_level INTEGER DEFAULT 1
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
    
    c.execute("""CREATE TABLE IF NOT EXISTS resource_businesses (
        user_id INTEGER,
        name TEXT,
        level INTEGER DEFAULT 1,
        last_collect TEXT,
        PRIMARY KEY (user_id, name)
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS ship_upgrades (
        user_id INTEGER,
        upgrade_name TEXT,
        PRIMARY KEY (user_id, upgrade_name)
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
        timestamp TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS limited_items (
        name TEXT PRIMARY KEY,
        total INTEGER,
        left_count INTEGER
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS user_achievements (
        user_id INTEGER,
        achievement_name TEXT,
        unlocked_at TEXT,
        PRIMARY KEY (user_id, achievement_name)
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
    
    c.execute("""CREATE TABLE IF NOT EXISTS lottery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tickets INTEGER,
        bought_at TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS stocks (
        user_id INTEGER,
        company TEXT,
        quantity INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, company)
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
    
    c.execute("""CREATE TABLE IF NOT EXISTS economy_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        multiplier REAL DEFAULT 1.0,
        started_at TEXT,
        ended_at TEXT,
        active INTEGER DEFAULT 0
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
    
    c.execute("""CREATE TABLE IF NOT EXISTS investments (
        user_id INTEGER PRIMARY KEY,
        amount INTEGER DEFAULT 0,
        invested_at TEXT,
        last_claim TEXT,
        multiplier REAL DEFAULT 1.0
    )""")
    
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
        welcome_enabled INTEGER DEFAULT 0,
        goodbye_enabled INTEGER DEFAULT 0,
        captcha_enabled INTEGER DEFAULT 0,
        antimat_enabled INTEGER DEFAULT 0,
        antispam_enabled INTEGER DEFAULT 0,
        antiflood_enabled INTEGER DEFAULT 0,
        anticaps_enabled INTEGER DEFAULT 0,
        slow_mode INTEGER DEFAULT 0,
        rules TEXT DEFAULT ''
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS duels (
        chat_id INTEGER,
        challenger INTEGER,
        opponent INTEGER,
        turn INTEGER,
        aim_bonus INTEGER,
        message_id INTEGER
    )""")
    
    conn.commit()
    conn.close()

# ==================== ЛИМИТНЫЕ ПРЕДМЕТЫ ====================
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

def init_limited_items():
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    for name, data in LIMITED_ITEMS.items():
        c.execute("INSERT OR IGNORE INTO limited_items (name, total, left_count) VALUES (?, ?, ?)",
                  (name, data["total"], data["total"]))
    conn.commit()
    conn.close()

# ==================== ЗАПУСК ====================
init_db()
init_limited_items()

# ==================== ДАННЫЕ ====================
JOBS = {
    "шахтёр": {"min": 1000, "max": 2000, "emoji": "⛏️", "desc": "Добывает руду"},
    "рыбак": {"min": 800, "max": 1600, "emoji": "🎣", "desc": "Ловит рыбу"},
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

SHIP_UPGRADES = {
    "паруса": {"price": 50000, "effect": "speed", "bonus": 10, "emoji": "⛵", "desc": "-10% времени пути"},
    "карта": {"price": 10000, "effect": "risk", "bonus": 5, "emoji": "🗺️", "desc": "-5% риск"},
    "компас": {"price": 15000, "effect": "risk", "bonus": 5, "emoji": "🧭", "desc": "-5% риск"},
    "радар": {"price": 20000, "effect": "risk", "bonus": 5, "emoji": "📡", "desc": "-5% риск"},
    "бронированный корабль": {"price": 80000, "effect": "defense", "bonus": 40, "emoji": "🛡️", "desc": "+40% защита от пиратов, +30% риск утонуть"}
}

RESOURCE_BUSINESSES = {
    "шахта": {"emoji": "⛏️", "price": 50000, "time": 30, "resources": {"камень": {"price": 50, "chance": 60, "min": 2, "max": 4}, "золото": {"price": 200, "chance": 30, "min": 1, "max": 2}, "алмаз": {"price": 500, "chance": 10, "min": 1, "max": 1}}},
    "лесопилка": {"emoji": "🌲", "price": 40000, "time": 45, "resources": {"древесина": {"price": 30, "chance": 70, "min": 3, "max": 5}, "доски": {"price": 100, "chance": 30, "min": 2, "max": 3}}},
    "ферма": {"emoji": "🌾", "price": 30000, "time": 60, "resources": {"пшеница": {"price": 40, "chance": 50, "min": 3, "max": 6}, "морковь": {"price": 60, "chance": 30, "min": 2, "max": 4}, "яблоки": {"price": 80, "chance": 20, "min": 1, "max": 3}}},
    "скотоводство": {"emoji": "🐄", "price": 45000, "time": 60, "resources": {"мясо": {"price": 150, "chance": 50, "min": 2, "max": 4}, "масло": {"price": 200, "chance": 30, "min": 1, "max": 3}, "сыр": {"price": 250, "chance": 20, "min": 1, "max": 2}}},
    "рыболовная база": {"emoji": "🎣", "price": 35000, "time": 30, "resources": {"рыба": {"price": 100, "chance": 70, "min": 2, "max": 4}, "креветки": {"price": 300, "chance": 30, "min": 1, "max": 2}}},
    "завод": {"emoji": "🏭", "price": 60000, "time": 60, "resources": {"металл": {"price": 200, "chance": 60, "min": 2, "max": 4}, "детали": {"price": 350, "chance": 40, "min": 1, "max": 3}}},
    "копи": {"emoji": "💎", "price": 70000, "time": 120, "resources": {"алмаз": {"price": 500, "chance": 60, "min": 1, "max": 2}, "сапфир": {"price": 700, "chance": 40, "min": 1, "max": 1}}},
    "плантация": {"emoji": "🌿", "price": 55000, "time": 90, "resources": {"кофе": {"price": 150, "chance": 40, "min": 2, "max": 4}, "какао": {"price": 200, "chance": 30, "min": 1, "max": 3}, "трава": {"price": 80, "chance": 30, "min": 2, "max": 4}}},
    "карьер": {"emoji": "🪨", "price": 25000, "time": 20, "resources": {"камень": {"price": 50, "chance": 70, "min": 2, "max": 4}, "глина": {"price": 70, "chance": 30, "min": 1, "max": 3}}},
    "пасека": {"emoji": "🐝", "price": 20000, "time": 60, "resources": {"мёд": {"price": 200, "chance": 70, "min": 2, "max": 4}, "воск": {"price": 150, "chance": 30, "min": 1, "max": 3}}}
}

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

ACHIEVEMENTS = {
    "first_work": {"name": "💼 Первая работа", "desc": "Устроиться на первую работу", "reward": 500},
    "first_money": {"name": "💰 Первый миллион", "desc": "Накопить 1 000 000 монет", "reward": 10000},
    "first_business": {"name": "🏪 Первый бизнес", "desc": "Купить первый бизнес", "reward": 1000},
    "ten_businesses": {"name": "🏪 Магнат", "desc": "Купить 10 бизнесов", "reward": 5000},
    "first_marriage": {"name": "💍 Первая свадьба", "desc": "Вступить в брак", "reward": 1000},
    "first_rep": {"name": "⭐ Первая репутация", "desc": "Получить +реп", "reward": 500},
    "first_shop": {"name": "🛒 Покупатель", "desc": "Купить предмет", "reward": 500},
    "ten_shop": {"name": "🛒 Шопоголик", "desc": "Купить 10 предметов", "reward": 2000},
    "first_limited": {"name": "🔥 Коллекционер", "desc": "Купить лимитный предмет", "reward": 5000},
    "first_mine": {"name": "🪨 Шахтёр", "desc": "Добыть ресурсы", "reward": 500},
    "level_5": {"name": "🎯 Уровень 5", "desc": "Достигнуть уровня 5", "reward": 2000},
    "level_10": {"name": "👑 Уровень 10", "desc": "Достигнуть уровня 10", "reward": 5000}
}

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

PROPERTIES = {
    "дом": {"price": 100000, "income": 500, "emoji": "🏠"},
    "квартира": {"price": 80000, "income": 400, "emoji": "🏢"},
    "особняк": {"price": 200000, "income": 1000, "emoji": "🏰"},
    "замок": {"price": 500000, "income": 2500, "emoji": "🏯"}
}

CROPS = {
    "пшеница": {"time": 3600, "income": 100, "emoji": "🌾"},
    "морковь": {"time": 7200, "income": 200, "emoji": "🥕"},
    "помидоры": {"time": 14400, "income": 400, "emoji": "🍅"},
    "клубника": {"time": 28800, "income": 800, "emoji": "🍓"}
}

FISH = {
    "окунь": {"price": 50, "chance": 30, "emoji": "🐟"},
    "карп": {"price": 100, "chance": 25, "emoji": "🐠"},
    "лосось": {"price": 200, "chance": 20, "emoji": "🐡"},
    "щука": {"price": 300, "chance": 15, "emoji": "🦈"},
    "осётр": {"price": 500, "chance": 10, "emoji": "🐋"}
}

ANIMALS = {
    "заяц": {"price": 100, "chance": 30, "emoji": "🐇"},
    "лиса": {"price": 200, "chance": 25, "emoji": "🦊"},
    "волк": {"price": 300, "chance": 20, "emoji": "🐺"},
    "медведь": {"price": 500, "chance": 15, "emoji": "🐻"},
    "тигр": {"price": 800, "chance": 10, "emoji": "🐯"}
}

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

PET_TYPES = {
    "собака": {"price": 10000, "emoji": "🐕", "bonus": "защита", "desc": "Защищает от грабежа"},
    "кот": {"price": 8000, "emoji": "🐱", "bonus": "удача", "desc": "Приносит удачу"},
    "орёл": {"price": 20000, "emoji": "🦅", "bonus": "охота", "desc": "Помогает в охоте"},
    "волк": {"price": 25000, "emoji": "🐺", "bonus": "война", "desc": "Помогает в битвах"},
    "дракон": {"price": 50000, "emoji": "🐉", "bonus": "всё", "desc": "Помогает во всём"}
}

ECONOMY_EVENTS = {
    "инфляция": {"multiplier": 0.8, "desc": "💰 Инфляция! Доходы -20%", "duration": 3600},
    "дефляция": {"multiplier": 1.2, "desc": "💎 Дефляция! Доходы +20%", "duration": 3600},
    "кризис": {"multiplier": 0.5, "desc": "📉 Кризис! Доходы -50%", "duration": 7200},
    "бум": {"multiplier": 1.5, "desc": "📈 Бум! Доходы +50%", "duration": 7200},
    "золотой дождь": {"multiplier": 2.0, "desc": "🌟 Золотой дождь! Доходы x2", "duration": 3600}
}

CRAFT_RECIPES = {
    "золотая монета": {"resources": {"золото": 5}, "desc": "Сделать золотую монету"},
    "алмаз": {"resources": {"камень": 10, "золото": 5}, "desc": "Сделать алмаз"},
    "щит": {"resources": {"металл": 5, "древесина": 3}, "desc": "Сделать щит"},
    "бронежилет": {"resources": {"металл": 8, "кожа": 5}, "desc": "Сделать бронежилет"},
    "амулет удачи": {"resources": {"золото": 3, "алмаз": 1}, "desc": "Сделать амулет удачи"}
}

RP_ACTIONS = {
    "обнять": ["🤗 {user} обнял {target}!", "❤️ {user} прижал к себе {target}!", "💕 {user} согрел {target} теплом!"],
    "поцеловать": ["😘 {user} поцеловал {target}!", "💋 {user} чмокнул {target}!", "❤️‍🔥 {user} засосал {target}!"],
    "ударить": ["👊 {user} ударил {target}!", "💥 {user} заехал {target}!", "🥊 {user} врезал {target}!"],
    "пнуть": ["🦶 {user} пнул {target}!", "👟 {user} дал пинка {target}!", "💨 {user} выпнул {target}!"]
}

TRADE_GOODS = {
    "алмаз": {"buy": 400, "sell": 500},
    "золото": {"buy": 150, "sell": 200},
    "древесина": {"buy": 20, "sell": 30},
    "металл": {"buy": 150, "sell": 200},
    "рыба": {"buy": 80, "sell": 100},
    "мясо": {"buy": 120, "sell": 150},
    "зерно": {"buy": 30, "sell": 40}
}

SEASONS = {
    "зима": {"emoji": "❄️", "bonus": 0.8, "desc": "Зимний сезон! Доходы -20%"},
    "весна": {"emoji": "🌸", "bonus": 1.0, "desc": "Весенний сезон! Доходы нормальные"},
    "лето": {"emoji": "☀️", "bonus": 1.2, "desc": "Летний сезон! Доходы +20%"},
    "осень": {"emoji": "🍂", "bonus": 0.9, "desc": "Осенний сезон! Доходы -10%"}
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
    c.execute("INSERT OR IGNORE INTO users (user_id, username, created_at, admin_level) VALUES (?, ?, ?, 1)",
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
    c.execute("SELECT name, level, bought_at, last_collect FROM businesses WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

async def get_business(user_id, name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT level, bought_at, last_collect FROM businesses WHERE user_id = ? AND name = ?", (user_id, name))
    row = c.fetchone()
    conn.close()
    return row

async def create_business(user_id, name):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO businesses (user_id, name, bought_at, last_collect) VALUES (?, ?, ?, ?)",
              (user_id, name, datetime.now().isoformat(), datetime.now().isoformat()))
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

# ==================== ПРАВА АДМИНОВ ====================

DEFAULT_RIGHTS = {
    1: ["статистика", "чат стата", "онлайн", "мой уровень"],
    2: ["варн", "варны", "снять варн"],
    3: ["мут", "размут", "муты"],
    4: ["кик", "очистить"],
    5: ["бан", "разбан", "банлист"],
    6: ["стоп слово", "стоп слова", "удалить стоп"],
    7: ["чат режим", "правила"],
    8: ["приветствие", "прощание", "капча"],
    9: ["анти спам", "анти флуд", "анти капс", "замедление"],
    10: ["всё"]
}

CUSTOM_RIGHTS = {}

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

async def is_admin(user_id):
    level = await get_admin_level(user_id)
    return level >= 1

async def check_admin_level(user_id, required_level):
    level = await get_admin_level(user_id)
    return level >= required_level

async def has_right(user_id, command):
    level = await get_admin_level(user_id)
    
    if user_id == CREATOR_ID:
        return True
    
    if user_id in CUSTOM_RIGHTS:
        if command in CUSTOM_RIGHTS[user_id]:
            return True
    
    rights = DEFAULT_RIGHTS.get(level, [])
    if "всё" in rights or command in rights:
        return True
    
    for lvl in range(1, level + 1):
        if command in DEFAULT_RIGHTS.get(lvl, []):
            return True
    
    return False

# ==================== VIP СИСТЕМА ====================

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

async def get_vip_bonus(user_id):
    if await is_vip(user_id):
        return 1.5
    return 1.0

# ==================== ЭКОНОМИКА ====================

async def get_economy_multiplier():
    global active_economy_event
    if active_economy_event:
        return active_economy_event["data"]["multiplier"]
    return 1.0

async def get_season_multiplier():
    global current_season
    return SEASONS.get(current_season, {}).get("bonus", 1.0)

# ==================== СИСТЕМА НАГРАД ЗА СООБЩЕНИЯ ====================

async def check_message_reward(user_id, chat_id):
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    
    c.execute("SELECT last_message_time, daily_messages, last_daily_reset FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    
    if not row:
        c.execute("INSERT INTO users (user_id, created_at, last_message_time, daily_messages, last_daily_reset) VALUES (?, ?, ?, ?, ?)",
                  (user_id, now.isoformat(), now.isoformat(), 0, today))
        conn.commit()
        conn.close()
        return None
    
    last_msg_time, daily_messages, last_daily_reset = row
    
    if last_daily_reset != today:
        daily_messages = 0
        last_daily_reset = today
        c.execute("UPDATE users SET daily_messages = 0, last_daily_reset = ? WHERE user_id = ?", (today, user_id))
        conn.commit()
    
    if last_msg_time:
        try:
            last_time = datetime.fromisoformat(last_msg_time)
            hours_diff = (now - last_time).total_seconds() / 3600
            
            if hours_diff >= 24:
                reward = random.randint(1, 1000)
                vip_bonus = await get_vip_bonus(user_id)
                reward = int(reward * vip_bonus)
                
                await add_coins(user_id, reward)
                
                c.execute("UPDATE users SET last_message_time = ?, daily_messages = 1 WHERE user_id = ?", 
                         (now.isoformat(), user_id))
                conn.commit()
                conn.close()
                
                mention = f"[{await get_name(user_id)}](tg://user?id={user_id})"
                await bot.send_message(
                    chat_id,
                    f"💰 {mention} получил **+{reward}** монет за активность!\n"
                    f"📊 Сообщений за сегодня: **{daily_messages + 1}**",
                    parse_mode=ParseMode.MARKDOWN
                )
                return reward
        except:
            pass
    
    c.execute("UPDATE users SET daily_messages = daily_messages + 1, last_message_time = ? WHERE user_id = ?", 
             (now.isoformat(), user_id))
    conn.commit()
    conn.close()
    return None

# ==================== ОБРАБОТЧИК СООБЩЕНИЙ ====================

@dp.message()
async def handle_all_messages(message: types.Message):
    if message.text and message.text.startswith('/'):
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    await create_user(user_id, message.from_user.username)
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat_stats (user_id, chat_id, messages, last_message) VALUES (?, ?, 1, ?) "
              "ON CONFLICT(user_id, chat_id) DO UPDATE SET messages = messages + 1, last_message = ?",
              (user_id, chat_id, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await check_message_reward(user_id, chat_id)
    
    if message.text:
        text_lower = message.text.lower().strip()
        
        # ===== ПРОФИЛЬ =====
        if text_lower in ["я", "профиль"]:
            await show_profile(message, user_id)
            return
        
        if text_lower.startswith("я @") or text_lower.startswith("профиль @"):
            try:
                username = text_lower.split("@")[1].split()[0]
                member = await message.chat.get_member(username)
                await show_profile(message, member.user.id)
                return
            except:
                await message.reply("❌ Пользователь не найден!")
                return
        
        # ===== БАЛАНС =====
        if text_lower == "баланс":
            coins = await get_coins(user_id)
            bank = await get_bank(user_id)
            await message.reply(f"💰 **Баланс:**\n💵 Монет: {coins}\n🏦 В банке: {bank}")
            return
        
        # ===== КОМАНДЫ =====
        if text_lower == "команды":
            await show_commands(message)
            return
        
        # ===== РАБОТА =====
        if text_lower == "работа":
            await work_command(message)
            return
        
        if text_lower.startswith("устроиться "):
            await hire_command(message)
            return
        
        if text_lower == "список работ":
            await list_jobs(message)
            return
        
        # ===== БИЗНЕСЫ =====
        if text_lower == "бизнесы":
            await list_businesses(message)
            return
        
        if text_lower.startswith("купить бизнес "):
            await buy_business(message)
            return
        
        if text_lower.startswith("собрать бизнес "):
            await collect_business_income(message)
            return
        
        if text_lower == "мои бизнесы":
            await my_businesses_command(message)
            return
        
        # ===== РЕСУРСЫ =====
        if text_lower == "бизнесы ресурсы":
            await list_resource_businesses(message)
            return
        
        if text_lower.startswith("добыть "):
            await mine_resource_command(message)
            return
        
        if text_lower == "собрать ресурсы":
            await collect_all_resources(message)
            return
        
        # ===== КОРАБЛЬ =====
        if text_lower == "улучшения":
            await show_ship_upgrades(message)
            return
        
        if text_lower.startswith("купить улучшение "):
            await buy_ship_upgrade(message)
            return
        
        if text_lower == "мой корабль":
            await my_ship(message)
            return
        
        # ===== МАГАЗИН =====
        if text_lower == "магазин":
            await show_shop(message)
            return
        
        if text_lower.startswith("купить "):
            await buy_item(message)
            return
        
        if text_lower in ["инвентарь", "мой инвентарь", "предметы", "вещи"]:
            await show_inventory(message)
            return
        
        # ===== ЛИМИТКИ =====
        if text_lower == "лимитки":
            await show_limited_items(message)
            return
        
        if text_lower.startswith("лимитка "):
            await show_limited_item_info(message)
            return
        
        # ===== ПЕРЕВОДЫ =====
        if text_lower.startswith("перевод "):
            await transfer_command(message)
            return
        
        # ===== БАНК =====
        if text_lower.startswith("положить "):
            await deposit_command(message)
            return
        
        if text_lower.startswith("снять "):
            await withdraw_command(message)
            return
        
        # ===== ТОПЫ =====
        if text_lower == "топ":
            await top_command(message)
            return
        
        if text_lower == "топ реп":
            await top_rep_command(message)
            return
        
        # ===== БОНУСЫ =====
        if text_lower in ["бонус", "ежедневно"]:
            await daily_bonus(message)
            return
        
        # ===== РП КОМАНДЫ =====
        if text_lower in RP_ACTIONS and message.reply_to_message:
            await rp_command(message)
            return
        
        # ===== РЕПУТАЦИЯ =====
        if text_lower == "+реп" and message.reply_to_message:
            await add_reputation(message)
            return
        
        if text_lower == "-реп" and message.reply_to_message:
            await remove_reputation(message)
            return
        
        # ===== БРАК =====
        if text_lower == "брак" and message.reply_to_message:
            await propose_marriage(message)
            return
        
        if text_lower == "развестись":
            await divorce_command(message)
            return
        
        # ===== ИГРЫ =====
        if text_lower.startswith("кубы"):
            await cube_game(message)
            return
        
        if text_lower == "рулетка" and message.reply_to_message:
            await roulette_game(message)
            return
        
        # ===== ДОСТИЖЕНИЯ =====
        if text_lower == "ачивки":
            await show_achievements(message)
            return
        
        if text_lower == "все ачивки":
            await all_achievements_command(message)
            return
        
        # ===== КЛАНЫ =====
        if text_lower.startswith(("создать клан", "вступить в клан", "мой клан", "кланы", "казна")):
            await clan_commands(message)
            return
        
        # ===== КРЕДИТЫ =====
        if text_lower.startswith("кредит"):
            await loan_commands(message)
            return
        
        # ===== ЛОТЕРЕЯ =====
        if text_lower.startswith("лотерея"):
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
        
        # ===== МОДЕРАЦИЯ =====
        # Проверяем права для каждой команды
        if text_lower.startswith("варн "):
            await warn_user(message)
            return
        
        if text_lower.startswith("варны "):
            await get_warns(message)
            return
        
        if text_lower.startswith("снять варн "):
            await remove_warn(message)
            return
        
        if text_lower.startswith("мут "):
            await mute_user(message)
            return
        
        if text_lower.startswith("размут "):
            await unmute_user(message)
            return
        
        if text_lower == "муты":
            await list_mutes(message)
            return
        
        if text_lower.startswith("кик "):
            await kick_user(message)
            return
        
        if text_lower.startswith("бан "):
            await ban_user(message)
            return
        
        if text_lower.startswith("разбан "):
            await unban_user(message)
            return
        
        if text_lower == "банлист":
            await banlist(message)
            return
        
        if text_lower.startswith("очистить "):
            await clear_messages(message)
            return
        
        if text_lower.startswith("стоп слово "):
            await add_stop_word(message)
            return
        
        if text_lower == "стоп слова":
            await list_stop_words(message)
            return
        
        if text_lower.startswith("удалить стоп "):
            await remove_stop_word(message)
            return
        
        if text_lower == "анти спам вкл":
            await enable_antispam(message)
            return
        
        if text_lower == "анти спам выкл":
            await disable_antispam(message)
            return
        
        if text_lower == "анти флуд вкл":
            await enable_antiflood(message)
            return
        
        if text_lower == "анти флуд выкл":
            await disable_antiflood(message)
            return
        
        if text_lower == "анти капс вкл":
            await enable_anticaps(message)
            return
        
        if text_lower == "анти капс выкл":
            await disable_anticaps(message)
            return
        
        if text_lower.startswith("чат режим "):
            await set_chat_mode(message)
            return
        
        if text_lower == "правила":
            await show_rules(message)
            return
        
        if text_lower.startswith("правила установить "):
            await set_rules(message)
            return
        
        if text_lower.startswith("правила добавить "):
            await add_rule(message)
            return
        
        if text_lower.startswith("правила удалить "):
            await remove_rule(message)
            return
        
        if text_lower == "статистика":
            await show_stats(message)
            return
        
        if text_lower == "чат стата":
            await chat_stats_command(message)
            return
        
        if text_lower == "онлайн":
            await online_command(message)
            return
        
        if text_lower == "мой уровень":
            await my_admin_level(message)
            return
        
        # ===== КОМАНДЫ ТОЛЬКО СОЗДАТЕЛЮ =====
        if message.chat.type == "private":
            if text_lower.startswith("дать монеты "):
                await give_coins(message)
                return
            
            if text_lower.startswith("дать банк "):
                await give_bank(message)
                return
            
            if text_lower.startswith("забрать монеты "):
                await remove_coins_creator(message)
                return
            
            if text_lower.startswith("дать предмет "):
                await give_item_creator(message)
                return
            
            if text_lower.startswith("дать уровень "):
                await give_admin_level(message)
                return
            
            if text_lower.startswith("убрать уровень "):
                await remove_admin_level(message)
                return
            
            if text_lower.startswith("настроить права "):
                await configure_rights(message)
                return
            
            if text_lower.startswith("добавить право "):
                await add_user_right(message)
                return
            
            if text_lower.startswith("убрать право "):
                await remove_user_right(message)
                return
            
            if text_lower.startswith("создать промо "):
                await create_promo(message)
                return
            
            if text_lower.startswith("активировать промо "):
                await activate_promo(message)
                return
            
            if text_lower == "список промо":
                await list_promos(message)
                return
            
            if text_lower.startswith("удалить промо "):
                await delete_promo(message)
                return
            
            if text_lower.startswith("эконом старт "):
                await economy_start(message)
                return
            
            if text_lower == "эконом стоп":
                await economy_stop(message)
                return
            
            if text_lower == "эконом статус":
                await economy_status(message)
                return
            
            if text_lower.startswith("дать вип "):
                await give_vip_command(message)
                return
            
            if text_lower.startswith("убрать вип "):
                await remove_vip_command(message)
                return

# ==================== ЗАПУСК ====================

async def main():
    print(f"✅ {BOT_NAME} запущен!")
    print(f"👑 Создатель: {CREATOR_ID}")
    print(f"💼 Работ: {len(JOBS)}")
    print(f"🏪 Бизнесов: {len(BUSINESSES)}")
    print(f"🔥 Лимиток: {len(LIMITED_ITEMS)}")
    print(f"💰 Награда за сообщения: +1-1000 монет каждые 24 часа")
    print("⏳ Бот запускается...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    from part1 import *

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
    c.execute("SELECT daily_messages FROM users WHERE user_id = ?", (target_id,))
    daily_row = c.fetchone()
    daily_messages = daily_row[0] if daily_row else 0
    c.execute("SELECT vip, vip_until FROM users WHERE user_id = ?", (target_id,))
    vip_row = c.fetchone()
    c.execute("SELECT admin_level FROM users WHERE user_id = ?", (target_id,))
    admin_row = c.fetchone()
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
    msg += f"💬 Сегодня: **{daily_messages}** сообщений\n"
    msg += f"🏙️ Город: **{city.capitalize()}**\n\n"
    
    if job:
        job_data = JOBS.get(job, {})
        msg += f"💼 Работа: **{job.capitalize()}** {job_data.get('emoji', '')}\n"
    else:
        msg += f"💼 Работа: **Нет**\n"
    
    msg += f"💍 Брак: **{spouse_name}**\n"
    msg += f"🏪 Бизнесов: **{len(businesses)}**\n"
    msg += f"🎒 Предметов: **{len(inventory)}**\n"
    
    if vip_row and vip_row[0]:
        msg += f"\n👑 **VIP**"
    
    if admin_row and admin_row[0] > 0:
        msg += f"\n🎯 Уровень админа: **{admin_row[0]}/10**"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def show_commands(message):
    msg = f"""
📋 **ВСЕ КОМАНДЫ БОТА {BOT_NAME}**

━━━━━━━━━━━━━━━━━━━━

👤 **ПРОФИЛЬ**
• `я` или `профиль` — свой профиль
• `я @user` — профиль пользователя
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

🪨 **РЕСУРСЫ**
• `бизнесы ресурсы` — список ресурсных бизнесов
• `добыть [бизнес]` — добыть ресурсы
• `собрать ресурсы` — собрать всё

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

🎁 **БОНУСЫ**
• `бонус` или `ежедневно` — ежедневный бонус

📤 **ПЕРЕВОДЫ**
• `перевод @user [сумма]` — перевести монеты

🏆 **ДОСТИЖЕНИЯ**
• `ачивки` — свои достижения
• `все ачивки` — все достижения

🎮 **ИГРЫ**
• `кубы` (ответ) — игра в кости
• `рулетка` (ответ) — русская рулетка

🏰 **КЛАНЫ**
• `создать клан [название]` — создать клан
• `вступить в клан [название]` — вступить в клан
• `мой клан` — информация о клане
• `кланы` — список кланов

💳 **КРЕДИТЫ**
• `кредит взять [сумма]` — взять кредит
• `кредит погасить` — погасить кредит

🎲 **ЛОТЕРЕЯ**
• `лотерея купить [количество]` — купить билеты
• `лотерея розыгрыш` — провести розыгрыш

📈 **ФОНДОВЫЙ РЫНОК**
• `рынок` — список компаний
• `купить акции [компания] [количество]` — купить акции
• `мой портфель` — мои акции

🏠 **НЕДВИЖИМОСТЬ**
• `недвижимость` — список недвижимости
• `купить дом` — купить дом
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

📋 **ЗАДАНИЯ**
• `ежедневные задания` — показать задания
• `еженедельные задания` — показать задания

━━━━━━━━━━━━━━━━━━━━
"""
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== РАБОТА ====================

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
    econ_mult = await get_economy_multiplier()
    season_mult = await get_season_multiplier()
    salary = int(salary * (1 + bonus / 100) * econ_mult * season_mult)
    
    await add_coins(user_id, salary)
    await add_exp(user_id, 5)
    await log_action(user_id, "work", f"Заработал {salary} монет на работе {job}")
    
    msg = f"{job_data['emoji']} **{job.capitalize()}**: +{salary} монет"
    if bonus > 0:
        msg += f" (бонус +{bonus}%)"
    if econ_mult != 1.0:
        msg += f" (экономика x{econ_mult})"
    if season_mult != 1.0:
        msg += f" (сезон x{season_mult})"
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

# ==================== БИЗНЕСЫ ====================

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

async def collect_business_income(message):
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
    season_mult = await get_season_multiplier()
    earned = int(income_per_hour * hours_passed * econ_mult * season_mult * random.uniform(0.8, 1.2))
    earned = max(1, earned)
    
    await add_coins(user_id, earned)
    await update_business_collect(user_id, name)
    await log_action(user_id, "collect_business", f"Собрал {earned} монет с {name}")
    
    msg = f"💰 Собрано **{earned}** монет с **{data['emoji']} {name.capitalize()}**!\n📈 Доход: {income_per_hour} монет/час"
    if econ_mult != 1.0:
        msg += f" (экономика x{econ_mult})"
    if season_mult != 1.0:
        msg += f" (сезон x{season_mult})"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def my_businesses_command(message):
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
    
    msg = f"🏪 **{data['emoji']} {business_name.capitalize()}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 Уровень: **{level}/{data['max_level']}**\n"
    msg += f"💰 Доход: **{income}** монет/час\n"
    msg += f"🔧 Улучшение: {data['upgrade_price'] * level} монет\n"
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
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💰 Собрать доход", callback_data=f"collect_{business_name}"),
        InlineKeyboardButton("🔧 Улучшить", callback_data=f"upgrade_{business_name}")
    )
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_businesses"))
    
    new_income = data["income"] + (new_level - 1) * data["upgrade_income"]
    msg = f"🏪 **{data['emoji']} {business_name.capitalize()}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 Уровень: **{new_level}/{data['max_level']}**\n"
    msg += f"💰 Доход: **{new_income}** монет/час\n"
    msg += f"🔧 Улучшение: {data['upgrade_price'] * new_level} монет\n"
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
    season_mult = await get_season_multiplier()
    earned = int(income_per_hour * hours_passed * econ_mult * season_mult * random.uniform(0.8, 1.2))
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
        
        await log_action(user_id, "buy_limited", f"Купил {item_name}")
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

async def show_inventory(message):
    user_id = message.from_user.id
    items = await get_inventory(user_id)
    
    if not items:
        await message.reply("🎒 **Инвентарь пуст!**\n\n📝 `магазин` - купить предметы")
        return
    
    resources = []
    shop_items = []
    limited_items = []
    other = []
    
    for item_name, quantity in items:
        is_resource = False
        for biz in RESOURCE_BUSINESSES.values():
            if item_name in biz["resources"]:
                resources.append((item_name, quantity))
                is_resource = True
                break
        
        if is_resource:
            continue
        
        if item_name in SHOP_ITEMS:
            shop_items.append((item_name, quantity))
        elif item_name in LIMITED_ITEMS:
            limited_items.append((item_name, quantity))
        else:
            other.append((item_name, quantity))
    
    msg = "🎒 **ИНВЕНТАРЬ**\n━━━━━━━━━━━━━━━━━━━━\n"
    
    if resources:
        msg += "\n🪨 **РЕСУРСЫ:**\n"
        for name, qty in resources:
            emoji = get_item_emoji(name)
            price = get_item_price(name)
            price_str = f"💰 {price} монет" if price else ""
            msg += f"{emoji} {name.capitalize()}: **{qty}** шт {price_str}\n"
    
    if shop_items:
        msg += "\n🛒 **ПРЕДМЕТЫ:**\n"
        for name, qty in shop_items:
            emoji = get_item_emoji(name)
            price = get_item_price(name)
            price_str = f"💰 {price} монет" if price else ""
            msg += f"{emoji} {name.capitalize()}: **{qty}** шт {price_str}\n"
    
    if limited_items:
        msg += "\n🔥 **ЛИМИТНЫЕ ПРЕДМЕТЫ:**\n"
        for name, qty in limited_items:
            emoji = get_item_emoji(name)
            data = LIMITED_ITEMS.get(name)
            if data:
                msg += f"{emoji} {name.capitalize()}: **{qty}** шт ({data['rarity']})\n"
    
    if other:
        msg += "\n📦 **ДРУГОЕ:**\n"
        for name, qty in other:
            emoji = get_item_emoji(name)
            msg += f"{emoji} {name.capitalize()}: **{qty}** шт\n"
    
    total_items = len(items)
    msg += f"\n📊 Всего предметов: **{total_items}**"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ПЕРЕВОДЫ ====================

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

# ==================== БАНК ====================

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

# ==================== ТОПЫ ====================

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

# ==================== БОНУСЫ ====================

async def daily_bonus(message):
    user_id = message.from_user.id
    if user_id in daily_cooldown:
        elapsed = (datetime.now() - daily_cooldown[user_id]).total_seconds()
        if elapsed < 86400:
            remaining = int(86400 - elapsed)
            await message.reply(f"⏳ Через {remaining//3600}ч {(remaining%3600)//60}м")
            return
    
    bonus = 100 + (await get_level(user_id))[0] * 10
    econ_mult = await get_economy_multiplier()
    season_mult = await get_season_multiplier()
    bonus = int(bonus * econ_mult * season_mult)
    await add_coins(user_id, bonus)
    daily_cooldown[user_id] = datetime.now()
    await message.reply(f"🎁 Ежедневный бонус: +{bonus} монет!")

# ==================== РП КОМАНДЫ ====================

async def rp_command(message):
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

# ==================== ИГРЫ ====================

async def cube_game(message):
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

async def roulette_game(message):
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
        await bot.send_message(chat_id, f"🔫 **БАХ!**\n💀 {await get_name(game['turn'])} умер!\n🏆 {await get_name(winner)} победил!")
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

# ==================== ДОСТИЖЕНИЯ ====================

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

# ==================== ПРОДОЛЖЕНИЕ В PART3 ====================
from part1 import *

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

async def collect_all_resources(message):
    user_id = message.from_user.id
    businesses = await get_businesses(user_id)
    
    total_resources = []
    for name, level, bought_at, last_collect in businesses:
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
        await message.reply("❌ Ничего не добыто! Попробуй позже.")
        return
    
    msg = "📦 **СОБРАНО РЕСУРСОВ**\n\n"
    msg += "\n".join(total_resources)
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== КОРАБЛЬ ====================

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

# ==================== ЛИМИТНЫЕ ПРЕДМЕТЫ ====================

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

# ==================== КЛАНЫ ====================

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

async def clan_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    if text.startswith("создать клан"):
        if len(args) < 3:
            await message.reply("ℹ️ `создать клан [название]`")
            return
        
        name = " ".join(args[2:])
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
        return
    
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

# ==================== ПРОДОЛЖЕНИЕ В PART4 ====================
from part1 import *

# ==================== КОМАНДЫ СОЗДАТЕЛЯ ====================

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower().startswith("дать монеты "))
async def give_coins(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может выдавать монеты!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать монеты @user 1000` или `дать монеты мне 1000`")
        return
    
    try:
        target_raw = args[2]
        if target_raw == "мне":
            target_id = message.from_user.id
        elif target_raw.startswith("@"):
            member = await message.chat.get_member(target_raw.replace("@", ""))
            target_id = member.user.id
        else:
            target_id = int(target_raw)
        
        amount = int(args[3])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Ошибка! Формат: `дать монеты @user 1000`")
        return
    
    await add_coins(target_id, amount)
    await log_action(message.from_user.id, "give_coins", f"Выдал {amount} монет {await get_name(target_id)}")
    await message.reply(f"✅ {await get_name(target_id)} выдано **{amount}** монет!")

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower().startswith("дать банк "))
async def give_bank(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может выдавать в банк!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать банк @user 1000`")
        return
    
    try:
        target_raw = args[2]
        if target_raw == "мне":
            target_id = message.from_user.id
        elif target_raw.startswith("@"):
            member = await message.chat.get_member(target_raw.replace("@", ""))
            target_id = member.user.id
        else:
            target_id = int(target_raw)
        
        amount = int(args[3])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Ошибка! Формат: `дать банк @user 1000`")
        return
    
    await add_bank(target_id, amount)
    await log_action(message.from_user.id, "give_bank", f"Выдал {amount} в банк {await get_name(target_id)}")
    await message.reply(f"✅ {await get_name(target_id)} выдано **{amount}** в банк!")

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower().startswith("забрать монеты "))
async def remove_coins_creator(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может забирать монеты!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `забрать монеты @user 1000`")
        return
    
    try:
        target_raw = args[2]
        if target_raw.startswith("@"):
            member = await message.chat.get_member(target_raw.replace("@", ""))
            target_id = member.user.id
        else:
            target_id = int(target_raw)
        
        amount = int(args[3])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Ошибка! Формат: `забрать монеты @user 1000`")
        return
    
    coins = await get_coins(target_id)
    if coins < amount:
        await message.reply(f"❌ У {await get_name(target_id)} только {coins} монет!")
        return
    
    await remove_coins(target_id, amount)
    await log_action(message.from_user.id, "remove_coins", f"Забрал {amount} монет у {await get_name(target_id)}")
    await message.reply(f"✅ У {await get_name(target_id)} забрано **{amount}** монет!")

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower().startswith("дать предмет "))
async def give_item_creator(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может выдавать предметы!")
        return
    
    args = message.text.split()
    if len(args) < 4:
        await message.reply("ℹ️ `дать предмет @user предмет 5`")
        return
    
    try:
        target_raw = args[2]
        if target_raw == "мне":
            target_id = message.from_user.id
        elif target_raw.startswith("@"):
            member = await message.chat.get_member(target_raw.replace("@", ""))
            target_id = member.user.id
        else:
            target_id = int(target_raw)
        
        item_name = args[3].lower()
        quantity = int(args[4]) if len(args) > 4 else 1
        if quantity <= 0:
            await message.reply("❌ Количество должно быть > 0!")
            return
    except:
        await message.reply("❌ Ошибка! Формат: `дать предмет @user алмаз 5`")
        return
    
    await add_item(target_id, item_name, quantity)
    await log_action(message.from_user.id, "give_item", f"Выдал {quantity}x {item_name} {await get_name(target_id)}")
    await message.reply(f"✅ {await get_name(target_id)} выдано **{quantity}** шт **{item_name.capitalize()}**!")

# ==================== УПРАВЛЕНИЕ УРОВНЯМИ АДМИНОВ ====================

@dp.message(lambda message: message.text and message.text.lower().startswith("дать уровень "))
async def give_admin_level(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может выдавать уровни!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать уровень @user [1-10]`")
        return
    
    try:
        target = args[1].replace("@", "")
        level = int(args[2])
        
        if level < 0 or level > 10:
            await message.reply("❌ Уровень должен быть от 0 до 10!")
            return
        
        member = await message.chat.get_member(target)
        await set_admin_level(member.user.id, level)
        
        await message.reply(f"✅ {member.user.first_name} получил уровень админа: **{level}/10**")
        await log_action(message.from_user.id, "give_admin", f"Дал {level} уровень {member.user.first_name}")
    except:
        await message.reply("❌ Ошибка!")

@dp.message(lambda message: message.text and message.text.lower().startswith("убрать уровень "))
async def remove_admin_level(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может убирать уровни!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `убрать уровень @user`")
        return
    
    try:
        target = args[1].replace("@", "")
        member = await message.chat.get_member(target)
        await set_admin_level(member.user.id, 0)
        
        await message.reply(f"✅ У {member.user.first_name} убран уровень админа!")
        await log_action(message.from_user.id, "remove_admin", f"Убрал уровень у {member.user.first_name}")
    except:
        await message.reply("❌ Ошибка!")

@dp.message(lambda message: message.text and message.text.lower().startswith("настроить права "))
async def configure_rights(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может настраивать права!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `настроить права [уровень] [команда1,команда2,...]`")
        return
    
    try:
        level = int(args[1])
        if level < 1 or level > 10:
            await message.reply("❌ Уровень от 1 до 10!")
            return
        
        commands = " ".join(args[2:]).split(",")
        commands = [c.strip() for c in commands if c.strip()]
        
        DEFAULT_RIGHTS[level] = commands
        
        await message.reply(f"✅ Права для уровня **{level}** обновлены!\n📋 Команды: {', '.join(commands)}")
        await log_action(message.from_user.id, "configure_rights", f"Настроил права для {level} уровня: {commands}")
    except:
        await message.reply("❌ Ошибка!")

@dp.message(lambda message: message.text and message.text.lower().startswith("добавить право "))
async def add_user_right(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может добавлять права!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `добавить право @user [команда]`")
        return
    
    try:
        target = args[1].replace("@", "")
        command = args[2].lower()
        
        member = await message.chat.get_member(target)
        user_id = member.user.id
        
        if user_id not in CUSTOM_RIGHTS:
            CUSTOM_RIGHTS[user_id] = []
        
        if command not in CUSTOM_RIGHTS[user_id]:
            CUSTOM_RIGHTS[user_id].append(command)
        
        await message.reply(f"✅ {member.user.first_name} получил право на команду: **{command}**")
        await log_action(message.from_user.id, "add_right", f"Добавил право {command} для {member.user.first_name}")
    except:
        await message.reply("❌ Ошибка!")

@dp.message(lambda message: message.text and message.text.lower().startswith("убрать право "))
async def remove_user_right(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может убирать права!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `убрать право @user [команда]`")
        return
    
    try:
        target = args[1].replace("@", "")
        command = args[2].lower()
        
        member = await message.chat.get_member(target)
        user_id = member.user.id
        
        if user_id in CUSTOM_RIGHTS and command in CUSTOM_RIGHTS[user_id]:
            CUSTOM_RIGHTS[user_id].remove(command)
        
        await message.reply(f"✅ У {member.user.first_name} убрано право на команду: **{command}**")
        await log_action(message.from_user.id, "remove_right", f"Убрал право {command} у {member.user.first_name}")
    except:
        await message.reply("❌ Ошибка!")

# ==================== VIP ====================

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower().startswith("дать вип "))
async def give_vip_command(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может выдавать VIP!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать вип @user [дней]`")
        return
    
    try:
        target = args[1].replace("@", "")
        days = int(args[2])
        
        member = await message.chat.get_member(target)
        target_id = member.user.id
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        until = (datetime.now() + timedelta(days=days)).isoformat()
        c.execute("UPDATE users SET vip = 1, vip_until = ? WHERE user_id = ?", (until, target_id))
        conn.commit()
        conn.close()
        
        await message.reply(f"✅ {member.user.first_name} получил VIP на {days} дней!")
        await log_action(message.from_user.id, "give_vip", f"Дал VIP {member.user.first_name} на {days} дней")
    except:
        await message.reply("❌ Ошибка!")

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower().startswith("убрать вип "))
async def remove_vip_command(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может убирать VIP!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `убрать вип @user`")
        return
    
    try:
        target = args[1].replace("@", "")
        member = await message.chat.get_member(target)
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET vip = 0, vip_until = NULL WHERE user_id = ?", (member.user.id,))
        conn.commit()
        conn.close()
        
        await message.reply(f"✅ У {member.user.first_name} убран VIP!")
        await log_action(message.from_user.id, "remove_vip", f"Убрал VIP у {member.user.first_name}")
    except:
        await message.reply("❌ Ошибка!")

# ==================== ПРОМО-КОДЫ ====================

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower().startswith("создать промо "))
async def create_promo(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может создавать промо-коды!")
        return
    
    args = message.text.split()
    if len(args) < 4:
        await message.reply("ℹ️ `создать промо [код] [монеты] [предмет] [количество]`\n"
                          "Пример: `создать промо новогодний 1000 алмаз 5`")
        return
    
    code = args[2]
    coins = int(args[3]) if args[3].isdigit() else 0
    item = args[4] if len(args) > 4 else None
    quantity = int(args[5]) if len(args) > 5 and args[5].isdigit() else 1
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO promos (code, coins, item, quantity, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (code, coins, item, quantity, message.from_user.id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await log_action(message.from_user.id, "create_promo", f"Создал промо-код {code}")
    await message.reply(f"✅ Промо-код **{code}** создан!\n"
                      f"💰 Монеты: {coins}\n"
                      f"🎒 Предмет: {item} x{quantity}")

@dp.message(lambda message: message.text and message.text.lower().startswith("активировать промо "))
async def activate_promo(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `активировать промо [код]`")
        return
    
    code = args[2]
    
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
    
    user_id = message.from_user.id
    
    if coins > 0:
        await add_coins(user_id, coins)
    
    if item:
        await add_item(user_id, item, quantity)
    
    c.execute("UPDATE promos SET uses = uses + 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    
    await log_action(user_id, "activate_promo", f"Активировал промо-код {code}")
    await message.reply(f"✅ Промо-код **{code}** активирован!\n"
                      f"💰 Монеты: +{coins}\n"
                      f"🎒 Предмет: {item} x{quantity}")

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower() == "список промо")
async def list_promos(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может смотреть промо-коды!")
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
        msg += f"💰 Монеты: {coins}\n"
        msg += f"🎒 Предмет: {item} x{quantity}\n"
        msg += f"📊 Использований: {uses}/{max_uses}\n\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower().startswith("удалить промо "))
async def delete_promo(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может удалять промо-коды!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `удалить промо [код]`")
        return
    
    code = args[2]
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM promos WHERE code = ?", (code,))
    if c.rowcount == 0:
        conn.close()
        await message.reply(f"❌ Промо-код **{code}** не найден!")
        return
    
    conn.commit()
    conn.close()
    
    await message.reply(f"✅ Промо-код **{code}** удалён!")

# ==================== ЭКОНОМИЧЕСКИЕ СОБЫТИЯ ====================

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower().startswith("эконом старт "))
async def economy_start(message: types.Message):
    global active_economy_event
    
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может управлять экономикой!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `эконом старт [инфляция|дефляция|кризис|бум|золотой дождь]`")
        return
    
    event_type = args[2].lower()
    if event_type not in ECONOMY_EVENTS:
        await message.reply(f"❌ Событие '{event_type}' не найдено!\n"
                          f"📝 Доступные: {', '.join(ECONOMY_EVENTS.keys())}")
        return
    
    active_economy_event = {
        "type": event_type,
        "data": ECONOMY_EVENTS[event_type],
        "started": datetime.now()
    }
    
    await log_action(message.from_user.id, "economy_start", f"Запустил {event_type}")
    await message.reply(f"✅ **{event_type.capitalize()}** запущена!\n{ECONOMY_EVENTS[event_type]['desc']}")

@dp.message(lambda message: message.chat.type == "private" and message.text and message.text.lower() == "эконом стоп")
async def economy_stop(message: types.Message):
    global active_economy_event
    
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может управлять экономикой!")
        return
    
    if not active_economy_event:
        await message.reply("❌ Нет активных событий!")
        return
    
    active_economy_event = None
    await message.reply("✅ Событие остановлено!")

@dp.message(lambda message: message.text and message.text.lower() == "эконом статус")
async def economy_status(message: types.Message):
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

# ==================== МОДЕРАЦИЯ ====================

@dp.message(lambda message: message.text and message.text.lower() == "статистика")
async def show_stats(message: types.Message):
    if not await has_right(message.from_user.id, "статистика"):
        await message.reply("❌ У тебя нет прав на эту команду!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT SUM(coins) FROM users")
    total_coins = c.fetchone()[0] or 0
    conn.close()
    
    await message.reply(f"📊 **СТАТИСТИКА БОТА**\n"
                       f"👥 Пользователей: {users}\n"
                       f"💰 Всего монет: {total_coins}")

@dp.message(lambda message: message.text and message.text.lower() == "чат стата")
async def chat_stats_command(message: types.Message):
    if not await has_right(message.from_user.id, "чат стата"):
        await message.reply("❌ У тебя нет прав на эту команду!")
        return
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM chat_stats WHERE chat_id = ?", (message.chat.id,))
    users = c.fetchone()[0]
    c.execute("SELECT SUM(messages) FROM chat_stats WHERE chat_id = ?", (message.chat.id,))
    messages = c.fetchone()[0] or 0
    conn.close()
    
    await message.reply(f"📊 **СТАТИСТИКА ЧАТА**\n"
                       f"👥 Участников: {users}\n"
                       f"💬 Сообщений: {messages}")

@dp.message(lambda message: message.text and message.text.lower() == "онлайн")
async def online_command(message: types.Message):
    if not await has_right(message.from_user.id, "онлайн"):
        await message.reply("❌ У тебя нет прав на эту команду!")
        return
    
    # Простая проверка - кто недавно писал
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM chat_stats WHERE chat_id = ? ORDER BY last_message DESC LIMIT 10", (message.chat.id,))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Нет данных!")
        return
    
    msg = "🟢 **ОНЛАЙН (последние 10):**\n"
    for row in rows:
        name = await get_name(row[0])
        msg += f"• {name}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

@dp.message(lambda message: message.text and message.text.lower() == "мой уровень")
async def my_admin_level(message: types.Message):
    level = await get_admin_level(message.from_user.id)
    await message.reply(f"🎯 Твой уровень админа: **{level}/10**\n"
                       f"\n📋 **Что доступно:**\n"
                       f"1️⃣ Просмотр статистики\n"
                       f"2️⃣ Выдача варнов\n"
                       f"3️⃣ Мут\n"
                       f"4️⃣ Размут\n"
                       f"5️⃣ Кик\n"
                       f"6️⃣ Бан\n"
                       f"7️⃣ Разбан\n"
                       f"8️⃣ Очистка чата\n"
                       f"9️⃣ Стоп-слова\n"
                       f"🔟 Всё остальное")

# ==================== ЗАПУСК ====================

async def main():
    print(f"✅ {BOT_NAME} запущен!")
    print(f"👑 Создатель: {CREATOR_ID}")
    print(f"💼 Работ: {len(JOBS)}")
    print(f"🏪 Бизнесов: {len(BUSINESSES)}")
    print(f"🔥 Лимиток: {len(LIMITED_ITEMS)}")
    print(f"💰 Награда за сообщения: +1-1000 монет каждые 24 часа")
    print("⏳ Бот запускается...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
