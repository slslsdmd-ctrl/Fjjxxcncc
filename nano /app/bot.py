
import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberAdministrator, ChatMemberOwner
from aiogram.enums import ParseMode
import os
import re

# ==================== ТОКЕН ====================
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не задан!")
    print("📝 Установи: export BOT_TOKEN='твой_токен'")
    exit(1)

BOT_NAME = "Fable"
CREATOR_ID = 8039111975

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
cooldowns = {}
daily_cooldown = {}
cube_games = {}
roulette_games = {}
marriage_proposals = {}
active_economy_event = None
user_warns = {}
user_mutes = {}
chat_settings = {}
stop_words = {}

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
        created_at TEXT,
        last_message_time TEXT,
        daily_messages INTEGER DEFAULT 0,
        last_daily_reset TEXT,
        vip INTEGER DEFAULT 0,
        vip_until TEXT,
        admin_level INTEGER DEFAULT 0
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
    
    c.execute("""CREATE TABLE IF NOT EXISTS marriages (
        user_id INTEGER PRIMARY KEY,
        spouse_id INTEGER,
        date TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS warns (
        user_id INTEGER,
        chat_id INTEGER,
        reason TEXT,
        date TEXT,
        warned_by INTEGER
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS chat_settings (
        chat_id INTEGER PRIMARY KEY,
        mode TEXT DEFAULT 'свободный',
        welcome TEXT,
        goodbye TEXT,
        welcome_enabled INTEGER DEFAULT 0,
        goodbye_enabled INTEGER DEFAULT 0,
        antispam_enabled INTEGER DEFAULT 0,
        antiflood_enabled INTEGER DEFAULT 0,
        anticaps_enabled INTEGER DEFAULT 0,
        slow_mode INTEGER DEFAULT 0
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS stop_words (
        chat_id INTEGER,
        word TEXT,
        PRIMARY KEY (chat_id, word)
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
    
    conn.commit()
    conn.close()

init_db()

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
    "водитель": {"min": 1100, "max": 2200, "emoji": "🚕", "desc": "Возит людей"}
}

BUSINESSES = {
    "кафе": {"price": 50000, "emoji": "☕", "income": 200, "upgrade_price": 25000, "upgrade_income": 20, "max_level": 10},
    "магазин": {"price": 80000, "emoji": "🏪", "income": 300, "upgrade_price": 40000, "upgrade_income": 30, "max_level": 10},
    "ферма": {"price": 60000, "emoji": "🌾", "income": 250, "upgrade_price": 30000, "upgrade_income": 25, "max_level": 10}
}

SHOP_ITEMS = {
    "улучшенная кирка": {"price": 50000, "category": "рабочие", "job": "шахтёр", "bonus": 10},
    "профессиональная удочка": {"price": 40000, "category": "рабочие", "job": "рыбак", "bonus": 10},
    "тренировочное ружьё": {"price": 60000, "category": "рабочие", "job": "охотник", "bonus": 10},
    "мощный пк": {"price": 80000, "category": "рабочие", "job": "программист", "bonus": 10},
    "трактор": {"price": 70000, "category": "рабочие", "job": "фермер", "bonus": 10},
    "диплом": {"price": 30000, "category": "рабочие", "job": "все", "bonus": 10},
    "деловой костюм": {"price": 25000, "category": "рабочие", "job": "бизнесмен", "bonus": 10},
    "щит": {"price": 3000, "category": "защита", "bonus": 5},
    "каска": {"price": 2000, "category": "защита", "bonus": 3},
    "бронежилет": {"price": 5000, "category": "защита", "bonus": 10},
    "амулет удачи": {"price": 8000, "category": "защита", "bonus": 3},
    "золотая монета": {"price": 1000, "category": "финансы", "bonus": 2},
    "драгоценный камень": {"price": 5000, "category": "финансы", "bonus": 5}
}

LIMITED_ITEMS = {
    "кольцо удачи": {"emoji": "💍", "price": 15000, "total": 5, "left": 5, "rarity": "🟣 РЕДКИЙ", "bonus": 5},
    "амулет богатства": {"emoji": "📿", "price": 30000, "total": 3, "left": 3, "rarity": "🟠 ЭПИЧЕСКИЙ", "bonus": 10},
    "корона власти": {"emoji": "👑", "price": 50000, "total": 1, "left": 1, "rarity": "🌟 МИФИЧЕСКИЙ", "bonus": 20}
}

RP_ACTIONS = {
    "обнять": ["🤗 {user} обнял {target}!", "❤️ {user} прижал к себе {target}!"],
    "поцеловать": ["😘 {user} поцеловал {target}!", "💋 {user} чмокнул {target}!"],
    "ударить": ["👊 {user} ударил {target}!", "💥 {user} заехал {target}!"],
    "пнуть": ["🦶 {user} пнул {target}!", "👟 {user} дал пинка {target}!"]
}

# ==================== ФУНКЦИИ БАЗЫ ДАННЫХ ====================
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
    
    level, exp = await get_level(user_id)
    exp_needed = level * 100
    if exp >= exp_needed:
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE user_id = ?", (exp_needed, user_id))
        conn.commit()
        conn.close()
        return True
    return False

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

async def get_name(user_id):
    try:
        user = await bot.get_chat(user_id)
        return f"@{user.username}" if user.username else user.first_name
    except:
        return f"id{user_id}"

async def is_admin(user_id):
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

async def get_vip_bonus(user_id):
    return 1.5 if await is_vip(user_id) else 1.0

async def check_cooldown(user_id, action, seconds):
    key = f"{action}_{user_id}"
    if key in cooldowns:
        elapsed = (datetime.now() - cooldowns[key]).total_seconds()
        if elapsed < seconds:
            return False, int(seconds - elapsed)
    cooldowns[key] = datetime.now()
    return True, 0

async def log_action(user_id, action, details):
    try:
        await bot.send_message(CREATOR_ID, f"📋 **ЛОГ**\n👤 {await get_name(user_id)}\n📌 {action}\n📝 {details}\n🕐 {datetime.now().strftime('%H:%M:%S')}")
    except:
        pass

# ==================== ОБРАБОТЧИК СООБЩЕНИЙ ====================
@dp.message()
async def handle_all_messages(message: types.Message):
    if message.text and message.text.startswith('/'):
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    await create_user(user_id, message.from_user.username)
    
    # Статистика чата
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat_stats (user_id, chat_id, messages, last_message) VALUES (?, ?, 1, ?) "
              "ON CONFLICT(user_id, chat_id) DO UPDATE SET messages = messages + 1, last_message = ?",
              (user_id, chat_id, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    if not message.text:
        return
    
    text = message.text.lower().strip()
    
    # ===== ПРОФИЛЬ =====
    if text in ["я", "профиль"]:
        await show_profile(message, user_id)
        return
    
    if text.startswith("я @") or text.startswith("профиль @"):
        try:
            username = text.split("@")[1].split()[0]
            member = await message.chat.get_member(username)
            await show_profile(message, member.user.id)
            return
        except:
            await message.reply("❌ Пользователь не найден!")
            return
    
    # ===== БАЛАНС =====
    if text == "баланс":
        coins = await get_coins(user_id)
        bank = await get_bank(user_id)
        await message.reply(f"💰 **Баланс:**\n💵 Монет: {coins}\n🏦 В банке: {bank}")
        return
    
    # ===== КОМАНДЫ =====
    if text == "команды":
        await show_commands(message)
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
    
    # ===== ЛИМИТКИ =====
    if text == "лимитки":
        await show_limited_items(message)
        return
    
    # ===== ПЕРЕВОДЫ =====
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
    if text in RP_ACTIONS and message.reply_to_message:
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
    
    # ===== МОДЕРАЦИЯ =====
    if text.startswith("варн "):
        await warn_user(message)
        return
    
    if text.startswith("варны "):
        await get_warns(message)
        return
    
    if text.startswith("снять варн "):
        await remove_warn(message)
        return
    
    if text.startswith("мут "):
        await mute_user(message)
        return
    
    if text.startswith("размут "):
        await unmute_user(message)
        return
    
    if text == "муты":
        await list_mutes(message)
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
    
    if text == "банлист":
        await banlist(message)
        return
    
    if text.startswith("очистить "):
        await clear_messages(message)
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
    
    if text == "анти спам вкл":
        await enable_antispam(message)
        return
    
    if text == "анти спам выкл":
        await disable_antispam(message)
        return
    
    if text == "анти флуд вкл":
        await enable_antiflood(message)
        return
    
    if text == "анти флуд выкл":
        await disable_antiflood(message)
        return
    
    if text == "анти капс вкл":
        await enable_anticaps(message)
        return
    
    if text == "анти капс выкл":
        await disable_anticaps(message)
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
    
    if text == "статистика":
        await show_stats(message)
        return
    
    if text == "чат стата":
        await chat_stats_command(message)
        return
    
    if text == "онлайн":
        await online_command(message)
        return
    
    if text == "мой уровень":
        await my_admin_level(message)
        return
    
    # ===== КОМАНДЫ СОЗДАТЕЛЯ =====
    if message.chat.type == "private":
        if text.startswith("дать монеты "):
            await give_coins(message)
            return
        
        if text.startswith("дать банк "):
            await give_bank(message)
            return
        
        if text.startswith("забрать монеты "):
            await remove_coins_creator(message)
            return
        
        if text.startswith("дать предмет "):
            await give_item_creator(message)
            return
        
        if text.startswith("дать уровень "):
            await give_admin_level(message)
            return
        
        if text.startswith("убрать уровень "):
            await remove_admin_level(message)
            return
        
        if text.startswith("создать промо "):
            await create_promo(message)
            return
        
        if text.startswith("активировать промо "):
            await activate_promo(message)
            return
        
        if text == "список промо":
            await list_promos(message)
            return
        
        if text.startswith("удалить промо "):
            await delete_promo(message)
            return
        
        if text.startswith("дать вип "):
            await give_vip_command(message)
            return
        
        if text.startswith("убрать вип "):
            await remove_vip_command(message)
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
    msg += f"📝 Сообщений: **{total_messages}**\n\n"
    
    if job:
        job_data = JOBS.get(job, {})
        msg += f"💼 Работа: **{job.capitalize()}** {job_data.get('emoji', '')}\n"
    else:
        msg += f"💼 Работа: **Нет**\n"
    
    msg += f"💍 Брак: **{spouse_name}**\n"
    msg += f"🏪 Бизнесов: **{len(businesses)}**\n"
    msg += f"🎒 Предметов: **{len(inventory)}**\n"
    
    if await is_vip(target_id):
        msg += f"\n👑 **VIP**"
    
    admin_level = await is_admin(target_id)
    if admin_level > 0:
        msg += f"\n🎯 Уровень админа: **{admin_level}/10**"
    
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

🎮 **ИГРЫ**
• `кубы` (ответ) — игра в кости
• `рулетка` (ответ) — русская рулетка

🏰 **КЛАНЫ**
• `создать клан [название]` — создать клан
• `вступить в клан [название]` — вступить в клан
• `мой клан` — информация о клане
• `кланы` — список кланов

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
    if await has_item(user_id, "улучшенная кирка") and job == "шахтёр":
        bonus += 10
    if await has_item(user_id, "профессиональная удочка") and job == "рыбак":
        bonus += 10
    if await has_item(user_id, "мощный пк") and job == "программист":
        bonus += 10
    if await has_item(user_id, "трактор") and job == "фермер":
        bonus += 10
    
    salary = random.randint(job_data["min"], job_data["max"])
    vip_bonus = await get_vip_bonus(user_id)
    salary = int(salary * (1 + bonus / 100) * vip_bonus)
    
    await add_coins(user_id, salary)
    leveled_up = await add_exp(user_id, 5)
    await log_action(user_id, "work", f"Заработал {salary} монет на работе {job}")
    
    msg = f"{job_data['emoji']} **{job.capitalize()}**: +{salary} монет"
    if bonus > 0:
        msg += f" (бонус +{bonus}%)"
    if await is_vip(user_id):
        msg += " (VIP x1.5)"
    if leveled_up:
        level, _ = await get_level(user_id)
        msg += f"\n🎉 **НОВЫЙ УРОВЕНЬ!** Ты достиг {level} уровня!"
    
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
        msg += f"📈 Доход: {data['income']} монет/час\n"
        msg += f"📊 Макс. уровень: {data['max_level']}\n\n"
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
    
    vip_bonus = await get_vip_bonus(user_id)
    earned = int(income_per_hour * hours_passed * vip_bonus * random.uniform(0.8, 1.2))
    earned = max(1, earned)
    
    await add_coins(user_id, earned)
    await update_business_collect(user_id, name)
    await log_action(user_id, "collect_business", f"Собрал {earned} монет с {name}")
    
    msg = f"💰 Собрано **{earned}** монет с **{data['emoji']} {name.capitalize()}**!\n📈 Доход: {income_per_hour} монет/час"
    if await is_vip(user_id):
        msg += " (VIP x1.5)"
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
    msg += f"🔧 Улучшение: {data['upgrade_price'] * level} монет"
    
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
    msg += f"🔧 Улучшение: {data['upgrade_price'] * new_level} монет"
    
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
    
    vip_bonus = await get_vip_bonus(user_id)
    earned = int(income_per_hour * hours_passed * vip_bonus * random.uniform(0.8, 1.2))
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
            job_name = data.get("job", "все")
            msg += f"• {name.capitalize()} — {data['price']} монет ({job_name})\n"
    msg += "\n"
    
    msg += "🛡️ **ЗАЩИТА**\n"
    for name, data in SHOP_ITEMS.items():
        if data.get("category") == "защита":
            msg += f"• {name.capitalize()} — {data['price']} монет\n"
    msg += "\n"
    
    msg += "💰 **ФИНАНСЫ**\n"
    for name, data in SHOP_ITEMS.items():
        if data.get("category") == "финансы":
            msg += f"• {name.capitalize()} — {data['price']} монет\n"
    
    msg += "\n📝 `купить [предмет]`"
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def buy_item(message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `купить [предмет]`")
        return
    
    item_name = args[1].lower().strip()
    
    # Проверка в магазине
    if item_name in SHOP_ITEMS:
        price = SHOP_ITEMS[item_name]["price"]
        if await get_coins(user_id) < price:
            await message.reply(f"❌ Нужно {price} монет!")
            return
        
        await remove_coins(user_id, price)
        await add_item(user_id, item_name)
        await log_action(user_id, "buy_item", f"Купил {item_name} за {price}")
        await message.reply(f"✅ **{item_name.capitalize()}** куплен!")
        return
    
    # Проверка в лимитках
    if item_name in LIMITED_ITEMS:
        data = LIMITED_ITEMS[item_name]
        if data["left"] <= 0:
            await message.reply(f"❌ {data['emoji']} {item_name.capitalize()} разобрали!")
            return
        
        price = data["price"]
        if await get_coins(user_id) < price:
            await message.reply(f"❌ Нужно {price} монет!")
            return
        
        await remove_coins(user_id, price)
        await add_item(user_id, item_name)
        
        # Обновляем остаток
        LIMITED_ITEMS[item_name]["left"] -= 1
        
        await log_action(user_id, "buy_limited", f"Купил {item_name}")
        await message.reply(f"✅ {data['emoji']} **{item_name.capitalize()}** куплен!\n📦 Осталось: {LIMITED_ITEMS[item_name]['left']}/{LIMITED_ITEMS[item_name]['total']}")
        return
    
    await message.reply(f"❌ Предмет '{item_name}' не найден!\n📝 Список: `магазин`")

async def show_inventory(message):
    user_id = message.from_user.id
    items = await get_inventory(user_id)
    
    if not items:
        await message.reply("🎒 **Инвентарь пуст!**\n\n📝 `магазин` - купить предметы")
        return
    
    msg = "🎒 **ИНВЕНТАРЬ**\n━━━━━━━━━━━━━━━━━━━━\n"
    
    shop_items = []
    limited_items = []
    other = []
    
    for item_name, quantity in items:
        if item_name in SHOP_ITEMS:
            shop_items.append((item_name, quantity))
        elif item_name in LIMITED_ITEMS:
            limited_items.append((item_name, quantity))
        else:
            other.append((item_name, quantity))
    
    if shop_items:
        msg += "\n🛒 **ПРЕДМЕТЫ:**\n"
        for name, qty in shop_items:
            price = SHOP_ITEMS[name]["price"]
            msg += f"• {name.capitalize()}: **{qty}** шт (💰 {price} монет)\n"
    
    if limited_items:
        msg += "\n🔥 **ЛИМИТНЫЕ ПРЕДМЕТЫ:**\n"
        for name, qty in limited_items:
            data = LIMITED_ITEMS.get(name)
            if data:
                msg += f"• {data['emoji']} {name.capitalize()}: **{qty}** шт ({data['rarity']})\n"
    
    if other:
        msg += "\n📦 **ДРУГОЕ:**\n"
        for name, qty in other:
            msg += f"• {name.capitalize()}: **{qty}** шт\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== ЛИМИТКИ ====================
async def show_limited_items(message):
    msg = "🔥 **ЛИМИТНЫЕ ПРЕДМЕТЫ**\n\n"
    
    rarities = ["🌟 МИФИЧЕСКИЙ", "🟠 ЭПИЧЕСКИЙ", "🟣 РЕДКИЙ"]
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
                msg += f"{emoji} {name.capitalize()} — {left}/{total} {status} (💰 {data['price']} монет)\n"
        if found:
            msg += "\n"
    
    msg += "📝 `купить [название]`"
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
    except Exception as e:
        await message.reply(f"❌ Пользователь не найден! Ошибка: {e}")

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
    
    success = await remove_bank(user_id, amount)
    if success:
        await add_coins(user_id, amount)
        await message.reply(f"🏦 -{amount} монет из банка!")
    else:
        await message.reply("❌ Ошибка!")

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
    
    level, _ = await get_level(user_id)
    bonus = 100 + level * 10
    vip_bonus = await get_vip_bonus(user_id)
    bonus = int(bonus * vip_bonus)
    await add_coins(user_id, bonus)
    daily_cooldown[user_id] = datetime.now()
    msg = f"🎁 Ежедневный бонус: +{bonus} монет!"
    if await is_vip(user_id):
        msg += " (VIP x1.5)"
    await message.reply(msg)

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
        msg = f"🔫 **БАХ!**\n💀 {await get_name(game['turn'])} умер!\n🏆 {await get_name(winner)} победил!"
        await bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)
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
        
        msg = f"💨 Холостой!\n⏳ Ход: {await get_name(game['turn'])}\n💀 Патронов: {len(bullets)}/6"
        await bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

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

# ==================== МОДЕРАЦИЯ ====================
async def warn_user(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
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
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO warns (user_id, chat_id, reason, date, warned_by) VALUES (?, ?, ?, ?, ?)",
                  (target_id, message.chat.id, reason, datetime.now().isoformat(), message.from_user.id))
        conn.commit()
        conn.close()
        
        await message.reply(f"⚠️ {await get_name(target_id)} получил варн!\n📝 Причина: {reason}")
        await log_action(message.from_user.id, "warn", f"Варн {await get_name(target_id)}: {reason}")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def get_warns(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `варны @user`")
        return
    
    try:
        target_username = args[1].replace("@", "")
        member = await message.chat.get_member(target_username)
        target_id = member.user.id
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT reason, date, warned_by FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY date DESC", 
                  (target_id, message.chat.id))
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            await message.reply(f"✅ У {await get_name(target_id)} нет варнов!")
            return
        
        msg = f"⚠️ **ВАРНЫ {await get_name(target_id)}**\n\n"
        for i, (reason, date, warned_by) in enumerate(rows, 1):
            admin_name = await get_name(warned_by)
            msg += f"{i}. {reason}\n   🕐 {date[:16]} 👤 {admin_name}\n\n"
        
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def remove_warn(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
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
        
        conn = sqlite3.connect("fable_bot.db")
        c = conn.cursor()
        c.execute("SELECT rowid FROM warns WHERE user_id = ? AND chat_id = ? ORDER BY date DESC LIMIT 1 OFFSET ?", 
                  (target_id, message.chat.id, warn_num - 1))
        row = c.fetchone()
        if row:
            c.execute("DELETE FROM warns WHERE rowid = ?", (row[0],))
            conn.commit()
            conn.close()
            await message.reply(f"✅ Снят варн #{warn_num} у {await get_name(target_id)}")
        else:
            conn.close()
            await message.reply(f"❌ Варн #{warn_num} не найден!")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def mute_user(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("ℹ️ `мут @user время(мин) причина`")
        return
    
    try:
        target_username = args[1].replace("@", "")
        minutes = int(args[2])
        member = await message.chat.get_member(target_username)
        
        if minutes <= 0 or minutes > 1440:
            await message.reply("❌ Время от 1 до 1440 минут!")
            return
        
        until = datetime.now() + timedelta(minutes=minutes)
        await bot.restrict_chat_member(
            message.chat.id,
            member.user.id,
            ChatPermissions(can_send_messages=False),
            until_date=until
        )
        
        await message.reply(f"🔇 {await get_name(member.user.id)} замучен на {minutes} мин!")
        await log_action(message.from_user.id, "mute", f"Мут {await get_name(member.user.id)} на {minutes} мин")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def unmute_user(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `размут @user`")
        return
    
    try:
        target_username = args[1].replace("@", "")
        member = await message.chat.get_member(target_username)
        
        await bot.restrict_chat_member(
            message.chat.id,
            member.user.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
        )
        
        await message.reply(f"🔊 {await get_name(member.user.id)} размучен!")
        await log_action(message.from_user.id, "unmute", f"Размут {await get_name(member.user.id)}")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def list_mutes(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    # Простая проверка - бот не хранит активные муты
    await message.reply("📋 Бот не хранит список активных мутов. Используйте /муты для просмотра.")

async def kick_user(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ `кик @user`")
        return
    
    try:
        target_username = args[1].replace("@", "")
        member = await message.chat.get_member(target_username)
        
        await bot.ban_chat_member(message.chat.id, member.user.id)
        await bot.unban_chat_member(message.chat.id, member.user.id)
        
        await message.reply(f"👢 {await get_name(member.user.id)} кикнут!")
        await log_action(message.from_user.id, "kick", f"Кик {await get_name(member.user.id)}")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def ban_user(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply("ℹ️ `бан @user причина`")
        return
    
    try:
        target_username = args[1].replace("@", "")
        reason = args[2] if len(args) > 2 else "Без причины"
        member = await message.chat.get_member(target_username)
        
        await bot.ban_chat_member(message.chat.id, member.user.id)
        
        await message.reply(f"🚫 {await get_name(member.user.id)} забанен!\n📝 Причина: {reason}")
        await log_action(message.from_user.id, "ban", f"Бан {await get_name(member.user.id)}: {reason}")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def unban_user(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `разбан @user`")
        return
    
    try:
        target_username = args[1].replace("@", "")
        member = await message.chat.get_member(target_username)
        
        await bot.unban_chat_member(message.chat.id, member.user.id)
        
        await message.reply(f"✅ {await get_name(member.user.id)} разбанен!")
        await log_action(message.from_user.id, "unban", f"Разбан {await get_name(member.user.id)}")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def banlist(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    # Бот не хранит список банов в БД, только в Telegram
    await message.reply("📋 Бот не хранит список банов. Используйте /банлист для просмотра.")

async def clear_messages(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `очистить количество`")
        return
    
    try:
        count = int(args[1])
        if count <= 0 or count > 100:
            await message.reply("❌ От 1 до 100 сообщений!")
            return
        
        deleted = 0
        async for msg in bot.get_chat_history(message.chat.id, limit=count):
            if msg.message_id != message.message_id:
                try:
                    await msg.delete()
                    deleted += 1
                except:
                    pass
        
        await message.reply(f"✅ Удалено {deleted} сообщений!")
        await log_action(message.from_user.id, "clear", f"Очистил {deleted} сообщений")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def add_stop_word(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
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
    
    await message.reply(f"✅ Стоп-слово **{word}** добавлено!")

async def list_stop_words(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    chat_id = message.chat.id
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT word FROM stop_words WHERE chat_id = ?", (chat_id,))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Нет стоп-слов!")
        return
    
    msg = "📋 **СТОП-СЛОВА**\n\n"
    for row in rows:
        msg += f"• {row[0]}\n"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def remove_stop_word(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
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
    
    await message.reply(f"✅ Стоп-слово **{word}** удалено!")

async def enable_antispam(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antispam_enabled) VALUES (?, 1) "
              "ON CONFLICT(chat_id) DO UPDATE SET antispam_enabled = 1", (chat_id,))
    conn.commit()
    conn.close()
    
    await message.reply("✅ Антиспам включен!")

async def disable_antispam(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antispam_enabled) VALUES (?, 0) "
              "ON CONFLICT(chat_id) DO UPDATE SET antispam_enabled = 0", (chat_id,))
    conn.commit()
    conn.close()
    
    await message.reply("✅ Антиспам выключен!")

async def enable_antiflood(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antiflood_enabled) VALUES (?, 1) "
              "ON CONFLICT(chat_id) DO UPDATE SET antiflood_enabled = 1", (chat_id,))
    conn.commit()
    conn.close()
    
    await message.reply("✅ Антифлуд включен!")

async def disable_antiflood(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antiflood_enabled) VALUES (?, 0) "
              "ON CONFLICT(chat_id) DO UPDATE SET antiflood_enabled = 0", (chat_id,))
    conn.commit()
    conn.close()
    
    await message.reply("✅ Антифлуд выключен!")

async def enable_anticaps(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, anticaps_enabled) VALUES (?, 1) "
              "ON CONFLICT(chat_id) DO UPDATE SET anticaps_enabled = 1", (chat_id,))
    conn.commit()
    conn.close()
    
    await message.reply("✅ Антикапс включен!")

async def disable_anticaps(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, anticaps_enabled) VALUES (?, 0) "
              "ON CONFLICT(chat_id) DO UPDATE SET anticaps_enabled = 0", (chat_id,))
    conn.commit()
    conn.close()
    
    await message.reply("✅ Антикапс выключен!")

async def set_chat_mode(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
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
    
    await message.reply(f"✅ Режим чата установлен: **{mode}**")

async def show_rules(message):
    chat_id = message.chat.id
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT rules FROM chat_settings WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()
    
    if not row or not row[0]:
        await message.reply("📭 Правила не установлены!")
        return
    
    await message.reply(f"📋 **ПРАВИЛА ЧАТА**\n\n{row[0]}")

async def set_rules(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
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
    
    await message.reply("✅ Правила установлены!")

async def show_stats(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
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

async def chat_stats_command(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
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

async def online_command(message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ У тебя нет прав!")
        return
    
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

async def my_admin_level(message):
    level = await is_admin(message.from_user.id)
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

# ==================== КОМАНДЫ СОЗДАТЕЛЯ ====================
async def give_coins(message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может выдавать монеты!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать монеты @user 1000` или `дать монеты мне 1000`")
        return
    
    try:
        target_raw = args[1]
        if target_raw == "мне":
            target_id = message.from_user.id
        elif target_raw.startswith("@"):
            member = await message.chat.get_member(target_raw.replace("@", ""))
            target_id = member.user.id
        else:
            target_id = int(target_raw)
        
        amount = int(args[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Ошибка! Формат: `дать монеты @user 1000`")
        return
    
    await add_coins(target_id, amount)
    await log_action(message.from_user.id, "give_coins", f"Выдал {amount} монет {await get_name(target_id)}")
    await message.reply(f"✅ {await get_name(target_id)} выдано **{amount}** монет!")

async def give_bank(message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может выдавать в банк!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать банк @user 1000`")
        return
    
    try:
        target_raw = args[1]
        if target_raw == "мне":
            target_id = message.from_user.id
        elif target_raw.startswith("@"):
            member = await message.chat.get_member(target_raw.replace("@", ""))
            target_id = member.user.id
        else:
            target_id = int(target_raw)
        
        amount = int(args[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть > 0!")
            return
    except:
        await message.reply("❌ Ошибка! Формат: `дать банк @user 1000`")
        return
    
    await add_bank(target_id, amount)
    await log_action(message.from_user.id, "give_bank", f"Выдал {amount} в банк {await get_name(target_id)}")
    await message.reply(f"✅ {await get_name(target_id)} выдано **{amount}** в банк!")

async def remove_coins_creator(message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может забирать монеты!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `забрать монеты @user 1000`")
        return
    
    try:
        target_raw = args[1]
        if target_raw.startswith("@"):
            member = await message.chat.get_member(target_raw.replace("@", ""))
            target_id = member.user.id
        else:
            target_id = int(target_raw)
        
        amount = int(args[2])
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
    
    success = await remove_coins(target_id, amount)
    if success:
        await log_action(message.from_user.id, "remove_coins", f"Забрал {amount} монет у {await get_name(target_id)}")
        await message.reply(f"✅ У {await get_name(target_id)} забрано **{amount}** монет!")
    else:
        await message.reply("❌ Ошибка!")

async def give_item_creator(message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может выдавать предметы!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("ℹ️ `дать предмет @user предмет 5`")
        return
    
    try:
        target_raw = args[1]
        if target_raw == "мне":
            target_id = message.from_user.id
        elif target_raw.startswith("@"):
            member = await message.chat.get_member(target_raw.replace("@", ""))
            target_id = member.user.id
        else:
            target_id = int(target_raw)
        
        item_name = args[2].lower()
        quantity = int(args[3]) if len(args) > 3 else 1
        if quantity <= 0:
            await message.reply("❌ Количество должно быть > 0!")
            return
    except:
        await message.reply("❌ Ошибка! Формат: `дать предмет @user алмаз 5`")
        return
    
    await add_item(target_id, item_name, quantity)
    await log_action(message.from_user.id, "give_item", f"Выдал {quantity}x {item_name} {await get_name(target_id)}")
    await message.reply(f"✅ {await get_name(target_id)} выдано **{quantity}** шт **{item_name.capitalize()}**!")

async def give_admin_level(message):
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
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def remove_admin_level(message):
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
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def create_promo(message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может создавать промо-коды!")
        return
    
    args = message.text.split()
    if len(args) < 4:
        await message.reply("ℹ️ `создать промо [код] [монеты] [предмет] [количество]`\n"
                          "Пример: `создать промо новогодний 1000 алмаз 5`")
        return
    
    code = args[1]
    coins = int(args[2]) if args[2].isdigit() else 0
    item = args[3] if len(args) > 3 else None
    quantity = int(args[4]) if len(args) > 4 and args[4].isdigit() else 1
    
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

async def activate_promo(message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `активировать промо [код]`")
        return
    
    code = args[1]
    
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

async def list_promos(message):
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

async def delete_promo(message):
    if message.from_user.id != CREATOR_ID:
        await message.reply("❌ Только создатель может удалять промо-коды!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("ℹ️ `удалить промо [код]`")
        return
    
    code = args[1]
    
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

async def give_vip_command(message):
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
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def remove_vip_command(message):
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
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# ==================== КЛАНЫ ====================
async def create_clan(message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("ℹ️ `создать клан [название]`")
        return
    
    name = args[2]
    
    # Проверка на существование клана
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT id FROM clans WHERE name = ?", (name,))
    if c.fetchone():
        conn.close()
        await message.reply(f"❌ Клан с названием '{name}' уже существует!")
        return
    
    # Проверка на уже в клане
    c.execute("SELECT id FROM clans WHERE members LIKE ?", (f"%{user_id}%",))
    if c.fetchone():
        conn.close()
        await message.reply("❌ Ты уже в клане!")
        return
    
    # Создание клана
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

async def join_clan(message):
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

async def my_clan(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect("fable_bot.db")
    c = conn.cursor()
    c.execute("SELECT id, name, owner_id, members, treasury FROM clans WHERE members LIKE ?", (f"%{user_id}%",))
    row = c.fetchone()
    
    if not row:
        conn.close()
        await message.reply("❌ Ты не в клане!")
        return
    
    clan_id, name, owner_id, members, treasury = row
    members_list = members.split(",") if members else []
    
    c.execute("SELECT role FROM clan_roles WHERE user_id = ? AND clan_id = ?", (user_id, clan_id))
    role_row = c.fetchone()
    role = role_row[0] if role_row else "member"
    conn.close()
    
    msg = f"🏰 **{name}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"👑 Лидер: {await get_name(owner_id)}\n"
    msg += f"🎭 Твоя роль: {role}\n"
    msg += f"👥 Участников: {len(members_list)}\n"
    msg += f"💰 Казна: {treasury} монет"
    
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)

async def list_clans(message):
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

# ==================== ЗАПУСК ====================
async def main():
    print(f"✅ {BOT_NAME} запущен!")
    print(f"👑 Создатель: {CREATOR_ID}")
    print(f"💼 Работ: {len(JOBS)}")
    print(f"🏪 Бизнесов: {len(BUSINESSES)}")
    print(f"🔥 Лимиток: {len(LIMITED_ITEMS)}")
    print("⏳ Бот запускается...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


