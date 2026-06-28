import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import os
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

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
cooldowns = {}
daily_cooldown = {}
trade_expeditions = {}
cube_games = {}
roulette_games = {}
active_duels = {}
active_knb = set()
knb_choices = {}
rep_cooldown = {}
work_cooldown = {}
marriage_proposals = {}
bank_rob_cooldown = {}
auction_bids = {}
active_promos = {}
ship_expeditions = {}
user_pets = {}
active_economy_event = None
global_chat_enabled = False
current_season = "весна"
tournaments = {}
active_auctions = {}

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
        last_daily_reset TEXT
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
        count INTEGER,
        reason TEXT,
        date TEXT,
        warned_by INTEGER
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

# ==================== ДАННЫЕ ====================

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
    "first_shop": {"name": "🛒 Покупатель", "desc": "Купить предмет в магазине", "reward": 500},
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

TRADE_GOODS = {
    "алмаз": {"buy": 400, "sell": 500},
    "золото": {"buy": 150, "sell": 200},
    "древесина": {"buy": 20, "sell": 30},
    "металл": {"buy": 150, "sell": 200},
    "рыба": {"buy": 80, "sell": 100},
    "мясо": {"buy": 120, "sell": 150},
    "зерно": {"buy": 30, "sell": 40}
}

CRAFT_RECIPES = {
    "золотая монета": {"resources": {"золото": 5}, "desc": "Сделать золотую монету"},
    "алмаз": {"resources": {"камень": 10, "золото": 5}, "desc": "Сделать алмаз"},
    "щит": {"resources": {"металл": 5, "древесина": 3}, "desc": "Сделать щит"},
    "бронежилет": {"resources": {"металл": 8, "кожа": 5}, "desc": "Сделать бронежилет"},
    "амулет удачи": {"resources": {"золото": 3, "алмаз": 1}, "desc": "Сделать амулет удачи"}
}

SEASONS = {
    "зима": {"emoji": "❄️", "bonus": 0.8, "desc": "Зимний сезон! Доходы -20%"},
    "весна": {"emoji": "🌸", "bonus": 1.0, "desc": "Весенний сезон! Доходы нормальные"},
    "лето": {"emoji": "☀️", "bonus": 1.2, "desc": "Летний сезон! Доходы +20%"},
    "осень": {"emoji": "🍂", "bonus": 0.9, "desc": "Осенний сезон! Доходы -10%"}
}

RP_ACTIONS = {
    "обнять": ["🤗 {user} обнял {target}!", "❤️ {user} прижал к себе {target}!", "💕 {user} согрел {target} теплом!"],
    "поцеловать": ["😘 {user} поцеловал {target}!", "💋 {user} чмокнул {target}!", "❤️‍🔥 {user} засосал {target}!"],
    "ударить": ["👊 {user} ударил {target}!", "💥 {user} заехал {target}!", "🥊 {user} врезал {target}!"],
    "пнуть": ["🦶 {user} пнул {target}!", "👟 {user} дал пинка {target}!", "💨 {user} выпнул {target}!"]
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
                reward = 10
                await add_coins(user_id, reward)
                
                c.execute("UPDATE users SET last_message_time = ?, daily_messages = 1 WHERE user_id = ?", 
                         (now.isoformat(), user_id))
                conn.commit()
                conn.close()
                
                mention = f"[{await get_name(user_id)}](tg://user?id={user_id})"
                await bot.send_message(
                    chat_id,
                    f"💰 {mention} получил **+{reward}** монет за активность в чате за последние 24 часа!\n"
                    f"📊 Всего сообщений за сегодня: **{daily_messages + 1}**",
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

# ==================== ЧАСТЬ 2 ИМПОРТИРУЕТСЯ ТУТ ====================
# from part2 import *
# ==================== ЧАСТЬ 2: ВСЕ КОМАНДЫ ====================

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
    c.execute("SELECT daily_messages, last_daily_reset FROM users WHERE user_id = ?", (target_id,))
    daily_row = c.fetchone()
    daily_messages = daily_row[0] if daily_row else 0
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
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== КОМАНДЫ ====================

async def show_commands(message):
    msg = f"""
📋 **ВСЕ КОМАНДЫ БОТА {BOT_NAME}**

━━━━━━━━━━━━━━━━━━━━

💰 **БОНУСЫ ЗА СООБЩЕНИЯ**
• За каждое сообщение в чате +опыт
• Каждые 24 часа +10 монет за активность

👤 **ПРОФИЛЬ**
• `я` или `профиль` — свой профиль
• `я @user` — профиль пользователя
• `кто ты` (ответ) — профиль того, кому ответил
• `баланс` — монеты и банк

💼 **РАБОТА**
• `список работ` — все работы
• `устроиться [работа]` — устроиться на работу
• `работа` — работать (КД 10 мин)

🏪 **БИЗНЕСЫ**
• `бизнесы` — список бизнесов
• `купить бизнес [название]` — купить бизнес
• `мои бизнесы` — свои бизнесы

🪨 **РЕСУРСЫ**
• `бизнесы ресурсы` — список ресурсных бизнесов
• `добыть [бизнес]` — добыть ресурсы

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

# ==================== ЕЖЕДНЕВНЫЙ БОНУС ====================

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

# ==================== ИНВЕНТАРЬ ====================

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

async def my_businesses_command(message):
    user_id = message.from_user.id
    businesses = await get_businesses(user_id)
    
    if not businesses:
        await message.reply("❌ У тебя нет бизнесов!\n📝 `купить бизнес [название]`")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for name, level, bought_at in businesses:
        data = BUSINESSES.get(name)
        if data:
            income = data["income"] + (level - 1) * data["upgrade_income"]
            btn_text = f"{data['emoji']} {name.capitalize()} (ур.{level}) — {income} монет/час"
            keyboard.add(InlineKeyboardButton(btn_text, callback_data=f"biz_{name}"))
    
    keyboard.add(InlineKeyboardButton("📦 Собрать все ресурсы", callback_data="collect_all_resources"))
    keyboard.add(InlineKeyboardButton("🔄 Обновить", callback_data="refresh_businesses"))
    
    msg = "🏪 **МОИ БИЗНЕСЫ**\n\n"
    msg += f"Всего бизнесов: **{len(businesses)}**\n"
    msg += "Нажми на бизнес для управления ⬇️"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

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
        await message.reply("❌ Ничего не добыто! Попробуй позже.")
        return
    
    msg = "📦 **СОБРАНО РЕСУРСОВ**\n\n"
    msg += "\n".join(total_resources)
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== КОЛБЭКИ ====================

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
    
    business = await get_business(user_id, business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    level = business[0]
    data = BUSINESSES.get(business_name)
    income = data["income"] + (level - 1) * data["upgrade_income"]
    
    earned = random.randint(income // 2, income)
    await add_coins(user_id, earned)
    await log_action(user_id, "collect_business", f"Собрал {earned} монет с {business_name}")
    
    await callback.answer(f"💰 +{earned} монет!", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("biz_resources_"))
async def business_resources_callback(callback):
    business_name = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    business = await get_business(user_id, business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    if business_name not in RESOURCE_BUSINESSES:
        await callback.answer("❌ Этот бизнес не добывает ресурсы!", show_alert=True)
        return
    
    level = business[0]
    data = RESOURCE_BUSINESSES[business_name]
    
    ok, remaining = await check_cooldown(user_id, f"mine_{business_name}", data["time"] * 60)
    if not ok:
        await callback.answer(f"⏳ Подожди {remaining//60} мин {remaining%60} сек!", show_alert=True)
        return
    
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
    
    msg = f"{data['emoji']} **{business_name.capitalize()}**\n📦 **ДОБЫЧА:**\n\n"
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

# ==================== ДОСТИЖЕНИЯ ====================

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

# ==================== КУБЫ ====================

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

# ==================== РУЛЕТКА ====================

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

# ==================== КРЕДИТЫ ====================

async def loan_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
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
        
        job = await get_job(user_id)
        if not job:
            await message.reply("❌ У тебя нет работы! Кредит только с работой.")
            return
        
        job_data = JOBS.get(job)
        if not job_data:
            await message.reply("❌ Ошибка!")
            return
        
        max_loan = (job_data["min"] + job_data["max"]) // 2 * 100
        if amount > max_loan:
            await message.reply(f"❌ Максимум кредита: {max_loan} монет (100x зарплаты)")
            return
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM loans WHERE user_id = ? AND paid = 0", (user_id,))
        if c.fetchone():
            conn.close()
            await message.reply("❌ У тебя уже есть активный кредит!")
            return
        
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

# ==================== ЛОТЕРЕЯ ====================

async def lottery_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
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
    
    if text == "лотерея мои":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT SUM(tickets) FROM lottery WHERE user_id = ?", (user_id,))
        total = c.fetchone()[0] or 0
        conn.close()
        
        await message.reply(f"🎲 У тебя **{total}** билетов!")
        return
    
    if text == "лотерея розыгрыш":
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id, tickets FROM lottery")
        tickets_data = c.fetchall()
        
        if not tickets_data:
            conn.close()
            await message.reply("❌ Нет участников!")
            return
        
        participants = []
        for user_id, tickets in tickets_data:
            participants.extend([user_id] * tickets)
        
        winner_id = random.choice(participants)
        jackpot = len(participants) * 100
        
        c.execute("DELETE FROM lottery")
        conn.commit()
        conn.close()
        
        reward = jackpot // 2
        await add_coins(winner_id, reward)
        
        await log_action(winner_id, "lottery_win", f"Выиграл в лотерею {reward} монет")
        await bot.send_message(message.chat.id, 
                              f"🎉 **ПОБЕДИТЕЛЬ ЛОТЕРЕИ!** 🎉\n"
                              f"🏆 {await get_name(winner_id)}\n"
                              f"💰 Приз: {reward} монет!\n"
                              f"🎫 Всего билетов: {len(participants)}")
        return

# ==================== ФОНДОВЫЙ РЫНОК ====================

async def stock_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    if text == "рынок":
        msg = "📈 **ФОНДОВЫЙ РЫНОК**\n\n"
        for name, data in STOCKS.items():
            price = data["price"]
            vol = data["volatility"]
            msg += f"**{name.capitalize()}** — {price} монет (волатильность {vol}%)\n"
        msg += "\n📝 `купить акции [компания] [количество]`\n📝 `продать акции [компания] [количество]`"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
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

# ==================== НЕДВИЖИМОСТЬ ====================

async def property_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
    if text == "недвижимость":
        msg = "🏠 **НЕДВИЖИМОСТЬ**\n\n"
        for name, data in PROPERTIES.items():
            msg += f"{data['emoji']} **{name.capitalize()}**\n"
            msg += f"💰 Цена: {data['price']} монет\n"
            msg += f"📈 Доход: {data['income']} монет/день\n\n"
        msg += "📝 `купить дом` или `купить квартиру`\n📝 `моя недвижимость`"
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    if text.startswith("купить дом"):
        await buy_property(message, "дом")
        return
    
    if text.startswith("купить квартиру"):
        await buy_property(message, "квартира")
        return
    
    if text.startswith("купить особняк"):
        await buy_property(message, "особняк")
        return
    
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

# ==================== ФЕРМА ====================

async def farm_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    args = text.split()
    
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

# ==================== РЫБАЛКА ====================

async def fishing_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    
    if text == "рыбалка":
        ok, remaining = await check_cooldown(user_id, "fish", 300)
        if not ok:
            await message.reply(f"⏳ Подожди {remaining//60} мин {remaining%60} сек!")
            return
        
        if not await has_item(user_id, "профессиональная удочка"):
            await message.reply("🎣 У тебя нет удочки! Купи: `купить профессиональная удочка`")
            return
        
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

# ==================== ОХОТА ====================

async def hunting_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    
    if text == "охота":
        ok, remaining = await check_cooldown(user_id, "hunt", 300)
        if not ok:
            await message.reply(f"⏳ Подожди {remaining//60} мин {remaining%60} сек!")
            return
        
        if not await has_item(user_id, "тренировочное ружьё"):
            await message.reply("🔫 У тебя нет ружья! Купи: `купить тренировочное ружьё`")
            return
        
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

# ==================== ТУРНИРЫ ====================

async def tournament_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if text == "турнир":
        if chat_id not in tournaments:
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
        
        if len(tournament["players"]) >= 5:
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
            await message.reply(f"✅ Ты участвуешь! Участников: {len(tournament['players'])}/5")
        return
    
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

# ==================== ЗАДАНИЯ ====================

async def quest_commands(message):
    text = message.text.lower()
    user_id = message.from_user.id
    
    if text == "ежедневные задания":
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM daily_quests WHERE user_id = ? AND quest_date = ?", (user_id, today))
        row = c.fetchone()
        
        if not row:
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
    
    if text == "еженедельные задания":
        week = datetime.now().strftime("%Y-W%W")
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM weekly_quests WHERE user_id = ? AND quest_week = ?", (user_id, week))
        row = c.fetchone()
        
        if not row:
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
    await check_achievements(user_id)
    
    if message.text:
        text_lower = message.text.lower().strip()
        
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
        
        if text_lower == "кто ты" and message.reply_to_message:
            await show_profile(message, message.reply_to_message.from_user.id)
            return
        
        if text_lower == "баланс":
            coins = await get_coins(user_id)
            bank = await get_bank(user_id)
            await message.reply(f"💰 **Баланс:**\n💵 Монет: {coins}\n🏦 В банке: {bank}")
            return
        
        if text_lower == "команды":
            await show_commands(message)
            return
        
        if text_lower == "работа":
            await work_command(message)
            return
        
        if text_lower.startswith("устроиться "):
            await hire_command(message)
            return
        
        if text_lower == "список работ":
            await list_jobs(message)
            return
        
        if text_lower == "бизнесы":
            await list_businesses(message)
            return
        
        if text_lower.startswith("купить бизнес "):
            await buy_business(message)
            return
        
        if text_lower == "мои бизнесы":
            await my_businesses_command(message)
            return
        
        if text_lower == "бизнесы ресурсы":
            await list_resource_businesses(message)
            return
        
        if text_lower.startswith("добыть "):
            await mine_resource_command(message)
            return
        
        if text_lower == "собрать ресурсы":
            await collect_all_resources(message)
            return
        
        if text_lower == "улучшения":
            await show_ship_upgrades(message)
            return
        
        if text_lower.startswith("купить улучшение "):
            await buy_ship_upgrade(message)
            return
        
        if text_lower == "мой корабль":
            await my_ship(message)
            return
        
        if text_lower == "магазин":
            await show_shop(message)
            return
        
        if text_lower.startswith("купить "):
            await buy_item(message)
            return
        
        if text_lower in ["инвентарь", "мой инвентарь", "предметы", "вещи"]:
            await show_inventory(message)
            return
        
        if text_lower == "лимитки":
            await show_limited_items(message)
            return
        
        if text_lower.startswith("лимитка "):
            await show_limited_item_info(message)
            return
        
        if text_lower == "брак" and message.reply_to_message:
            await propose_marriage(message)
            return
        
        if text_lower == "развестись":
            await divorce_command(message)
            return
        
        if text_lower == "+реп" and message.reply_to_message:
            await add_reputation(message)
            return
        
        if text_lower == "-реп" and message.reply_to_message:
            await remove_reputation(message)
            return
        
        if text_lower == "топ":
            await top_command(message)
            return
        
        if text_lower == "топ реп":
            await top_rep_command(message)
            return
        
        if text_lower.startswith("положить "):
            await deposit_command(message)
            return
        
        if text_lower.startswith("снять "):
            await withdraw_command(message)
            return
        
        if text_lower in ["бонус", "ежедневно"]:
            await daily_bonus(message)
            return
        
        if text_lower.startswith("перевод "):
            await transfer_command(message)
            return
        
        if text_lower == "ачивки":
            await show_achievements(message)
            return
        
        if text_lower == "все ачивки":
            await all_achievements_command(message)
            return
        
        if text_lower.startswith("кубы"):
            await cube_game(message)
            return
        
        if text_lower == "рулетка" and message.reply_to_message:
            await roulette_game(message)
            return
        
        if text_lower.startswith(("создать клан", "вступить в клан", "мой клан", "кланы", "казна")):
            await clan_commands(message)
            return
        
        if text_lower.startswith("кредит"):
            await loan_commands(message)
            return
        
        if text_lower.startswith("лотерея"):
            await lottery_commands(message)
            return
        
        if text_lower.startswith(("рынок", "купить акции", "продать акции", "мой портфель")):
            await stock_commands(message)
            return
        
        if text_lower.startswith(("недвижимость", "купить дом", "купить квартиру", "купить особняк", "моя недвижимость")):
            await property_commands(message)
            return
        
        if text_lower.startswith(("ферма", "посадить", "собрать")):
            await farm_commands(message)
            return
        
        if text_lower in ["рыбалка", "купить удочку"]:
            await fishing_commands(message)
            return
        
        if text_lower in ["охота", "купить ружьё"]:
            await hunting_commands(message)
            return
        
        if text_lower in ["турнир", "топ турниров"]:
            await tournament_commands(message)
            return
        
        if text_lower in ["ежедневные задания", "еженедельные задания"]:
            await quest_commands(message)
            return
        
        if text_lower in RP_ACTIONS and message.reply_to_message:
            await rp_command(message)
            return

# ==================== ЗАПУСК ====================

async def main():
    print(f"✅ {BOT_NAME} запущен!")
    print(f"👑 Создатель: {CREATOR_ID}")
    print(f"💼 Работ: {len(JOBS)}")
    print(f"🏪 Бизнесов: {len(BUSINESSES)}")
    print(f"🔥 Лимиток: {len(LIMITED_ITEMS)}")
    print(f"💰 Награда за сообщения: +10 монет каждые 24 часа")
    print("⏳ Бот запускается...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())