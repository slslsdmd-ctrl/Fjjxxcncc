# ============================================================
# БОТ ФАБЛЕ - ВСЁ В ОДНОМ ФАЙЛЕ
# ============================================================

import asyncio
import logging
import json
import os
import sys
import random
import time
import re
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

# ============================================================
# КОНСТАНТЫ
# ============================================================

BOT_NAME = "фабле"
SUPER_ADMIN_ID = 8039111975
SUPER_ADMIN_LEVEL = 10
DEFAULT_STARTING_BALANCE = 100
MAX_BALANCE = 999_999_999_999
MAX_WARNS_BEFORE_BAN = 5
MAX_CLAN_MEMBERS = 50
CLAN_CREATION_COST = 50000
MARRIAGE_COST = 5000
DIVORCE_COST = 5000
MAX_BUSINESSES_PER_USER = 25
MAX_BUSINESS_LEVEL = 10
CASINO_MIN_BET = 10
CASINO_MAX_BET = 1_000_000
MIN_DEPOSIT_AMOUNT = 100
MAX_DEPOSIT_AMOUNT = 10_000_000
MIN_LOAN_AMOUNT = 1000
MAX_LOAN_AMOUNT = 5_000_000
LOAN_INTEREST_RATE = 0.15
LOAN_DEFAULT_DURATION_DAYS = 30
BONUS_COOLDOWN_HOURS = 3
DEFAULT_MUTE_DURATION_MINUTES = 60
MAX_MUTE_DURATION_MINUTES = 43200
ROBBERY_JAIL_HOURS = 1
INSURANCE_DURATION_DAYS = 30
AUCTION_DURATION_HOURS_DEFAULT = 24
AUCTION_BID_MIN_INCREMENT = 10
EARTH_PRICE_MULTIPLIER = {"spawn": 0.5, "residential": 1.0, "suburban": 1.5, "business_center": 2.0, "industrial": 1.8, "entertainment": 2.5, "downtown": 3.0, "elite": 5.0}

# ============================================================
# КЛАССЫ
# ============================================================

@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    balance: int = DEFAULT_STARTING_BALANCE
    bank_balance: int = 0
    loan_amount: int = 0
    loan_due_date: Optional[datetime] = None
    total_messages: int = 0
    last_bonus_time: Optional[datetime] = None
    level: int = 1
    reputation_score: int = 0
    karma: int = 0
    achievements: Set[int] = field(default_factory=set)
    last_seen: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    global_blacklisted: bool = False
    muted_until: Optional[datetime] = None
    jailed_until: Optional[datetime] = None
    health: int = 100
    stress: int = 0
    is_sick: bool = False
    has_ip: bool = False
    ip_name: str = ""
    car_id: Optional[str] = None
    car_fuel: int = 100
    house_id: Optional[str] = None
    is_employed: bool = False
    job_salary: int = 0
    has_insurance: bool = False
    credit_history: float = 1.0
    loan_blocked: bool = False
    work_blocked: bool = False
    tax_debt: int = 0
    quests: Dict[str, int] = field(default_factory=dict)
    bonus_streak: int = 0
    last_bonus_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["achievements"] = list(self.achievements)
        data["last_bonus_time"] = self.last_bonus_time.isoformat() if self.last_bonus_time else None
        data["loan_due_date"] = self.loan_due_date.isoformat() if self.loan_due_date else None
        data["jailed_until"] = self.jailed_until.isoformat() if self.jailed_until else None
        data["last_seen"] = self.last_seen.isoformat()
        data["created_at"] = self.created_at.isoformat()
        data["muted_until"] = self.muted_until.isoformat() if self.muted_until else None
        data["last_bonus_date"] = self.last_bonus_date.isoformat() if self.last_bonus_date else None
        data["quests"] = self.quests
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        data["achievements"] = set(data.get("achievements", []))
        data["last_bonus_time"] = datetime.fromisoformat(data["last_bonus_time"]) if data.get("last_bonus_time") else None
        data["loan_due_date"] = datetime.fromisoformat(data["loan_due_date"]) if data.get("loan_due_date") else None
        data["jailed_until"] = datetime.fromisoformat(data["jailed_until"]) if data.get("jailed_until") else None
        data["last_seen"] = datetime.fromisoformat(data["last_seen"]) if isinstance(data.get("last_seen"), str) else data.get("last_seen", datetime.now())
        data["created_at"] = datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now())
        data["muted_until"] = datetime.fromisoformat(data["muted_until"]) if data.get("muted_until") else None
        data["last_bonus_date"] = datetime.fromisoformat(data["last_bonus_date"]) if data.get("last_bonus_date") else None
        data["quests"] = data.get("quests", {})
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class ChatConfig:
    chat_id: int
    chat_title: str = ""
    rules: str = ""
    slowmode_seconds: int = 0
    is_locked: bool = False
    antispam_enabled: bool = False
    welcome_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self); data["created_at"] = self.created_at.isoformat(); return data
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatConfig":
        data["created_at"] = datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now())
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class Business:
    business_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: int = 0
    name: str = ""
    business_type: str = ""
    level: int = 1
    purchase_price: int = 0
    current_value: int = 0
    hourly_income: int = 0
    employees: List[int] = field(default_factory=list)
    max_employees: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    last_collected: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self); data["created_at"] = self.created_at.isoformat(); data["last_collected"] = self.last_collected.isoformat(); return data
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Business":
        data["created_at"] = datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now())
        data["last_collected"] = datetime.fromisoformat(data["last_collected"]) if isinstance(data.get("last_collected"), str) else data.get("last_collected", datetime.now())
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class CryptoAsset:
    ticker: str; name: str; current_price: float; previous_price: float = 0.0
    change_percent: float = 0.0; last_updated: datetime = field(default_factory=datetime.now)
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self); data["last_updated"] = self.last_updated.isoformat(); return data
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CryptoAsset":
        data["last_updated"] = datetime.fromisoformat(data["last_updated"]) if isinstance(data.get("last_updated"), str) else data.get("last_updated", datetime.now())
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class StockAsset:
    ticker: str; company_name: str; current_price: float; previous_price: float = 0.0
    change_percent: float = 0.0; dividend_yield: float = 0.01; sector: str = ""
    last_updated: datetime = field(default_factory=datetime.now)
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self); data["last_updated"] = self.last_updated.isoformat(); return data
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockAsset":
        data["last_updated"] = datetime.fromisoformat(data["last_updated"]) if isinstance(data.get("last_updated"), str) else data.get("last_updated", datetime.now())
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class Clan:
    clan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""; leader_id: int = 0; members: List[int] = field(default_factory=list)
    treasury: int = 0; logo_emoji: str = "🏰"; created_at: datetime = field(default_factory=datetime.now)
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self); data["created_at"] = self.created_at.isoformat(); return data
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Clan":
        data["created_at"] = datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now())
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class Transaction:
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int = 0; amount: int = 0
    balance_after: int = 0; description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self); data["timestamp"] = self.timestamp.isoformat(); return data
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        data["timestamp"] = datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else data.get("timestamp", datetime.now())
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

def generate_id() -> str:
    return str(uuid.uuid4())

def is_super_admin(user_id: int) -> bool:
    return user_id == SUPER_ADMIN_ID

def format_currency(amount: int) -> str:
    return f"{amount:,} 💰"

def format_duration(seconds: int) -> str:
    if seconds < 60: return f"{seconds} сек"
    if seconds < 3600: return f"{seconds // 60} мин"
    if seconds < 86400: return f"{seconds // 3600} ч"
    return f"{seconds // 86400} дн"

def format_datetime(dt: datetime) -> str:
    if dt is None: return "Никогда"
    now = datetime.now(); diff = now - dt
    if diff.total_seconds() < 60: return "Только что"
    if diff.total_seconds() < 3600: return f"{int(diff.total_seconds() // 60)} мин назад"
    if diff.total_seconds() < 86400: return f"{int(diff.total_seconds() // 3600)} ч назад"
    if diff.days < 7: return f"{diff.days} дн назад"
    return dt.strftime("%d.%m.%Y %H:%M")

# ============================================================
# ХРАНИЛИЩЕ
# ============================================================

class DataStore:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.chats: Dict[int, ChatConfig] = {}
        self.businesses: Dict[str, Business] = {}
        self.crypto_assets: Dict[str, CryptoAsset] = {}
        self.stock_assets: Dict[str, StockAsset] = {}
        self.clans: Dict[str, Clan] = {}
        self.transactions: List[Transaction] = []
        self.command_cooldowns: Dict[int, Dict[str, datetime]] = {}
        self.message_counters: Dict[int, Dict[str, int]] = {}

    def get_user(self, user_id: int) -> User:
        if user_id not in self.users:
            self.users[user_id] = User(user_id=user_id)
        return self.users[user_id]

    def get_chat(self, chat_id: int) -> ChatConfig:
        if chat_id not in self.chats:
            self.chats[chat_id] = ChatConfig(chat_id=chat_id)
        return self.chats[chat_id]

    def get_user_businesses(self, user_id: int) -> List[Business]:
        return [b for b in self.businesses.values() if b.owner_id == user_id]

    def add_business(self, business: Business) -> None:
        self.businesses[business.business_id] = business

    def get_crypto_asset(self, ticker: str) -> Optional[CryptoAsset]:
        return self.crypto_assets.get(ticker.upper())

    def get_all_crypto_assets(self) -> List[CryptoAsset]:
        return list(self.crypto_assets.values())

    def get_stock_asset(self, ticker: str) -> Optional[StockAsset]:
        return self.stock_assets.get(ticker.upper())

    def get_all_stock_assets(self) -> List[StockAsset]:
        return list(self.stock_assets.values())

    def get_clan(self, clan_id: str) -> Optional[Clan]:
        return self.clans.get(clan_id)

    def add_transaction(self, transaction: Transaction) -> None:
        self.transactions.append(transaction)

    def get_user_transactions(self, user_id: int, limit: int = 20) -> List[Transaction]:
        result = [t for t in self.transactions if t.user_id == user_id]
        result.sort(key=lambda x: x.timestamp, reverse=True)
        return result[:limit]

    def set_command_cooldown(self, user_id: int, command: str, cooldown_minutes: int) -> None:
        if user_id not in self.command_cooldowns:
            self.command_cooldowns[user_id] = {}
        self.command_cooldowns[user_id][command] = datetime.now() + timedelta(minutes=cooldown_minutes)

    def is_on_cooldown(self, user_id: int, command: str) -> bool:
        if user_id in self.command_cooldowns and command in self.command_cooldowns[user_id]:
            return datetime.now() < self.command_cooldowns[user_id][command]
        return False

    def get_cooldown_remaining(self, user_id: int, command: str) -> int:
        if self.is_on_cooldown(user_id, command):
            remaining = self.command_cooldowns[user_id][command] - datetime.now()
            return max(0, int(remaining.total_seconds()))
        return 0

    def increment_message_counter(self, user_id: int, counter_type: str) -> int:
        if user_id not in self.message_counters:
            self.message_counters[user_id] = {}
        if counter_type not in self.message_counters[user_id]:
            self.message_counters[user_id][counter_type] = 0
        self.message_counters[user_id][counter_type] += 1
        return self.message_counters[user_id][counter_type]

    def reset_message_counter(self, user_id: int, counter_type: str) -> None:
        if user_id in self.message_counters and counter_type in self.message_counters[user_id]:
            self.message_counters[user_id][counter_type] = 0

    def get_total_users(self) -> int:
        return len(self.users)

    def get_total_chats(self) -> int:
        return len(self.chats)

    def get_active_users_today(self) -> int:
        today = datetime.now().date()
        return sum(1 for u in self.users.values() if u.last_seen.date() == today)

    def get_total_money_in_circulation(self) -> int:
        return sum(u.balance + u.bank_balance for u in self.users.values())

    def save_to_disk(self, filepath: str) -> None:
        try:
            data = {
                "users": {str(k): v.to_dict() for k, v in self.users.items()},
                "chats": {str(k): v.to_dict() for k, v in self.chats.items()},
                "businesses": {k: v.to_dict() for k, v in self.businesses.items()},
                "crypto_assets": {k: v.to_dict() for k, v in self.crypto_assets.items()},
                "stock_assets": {k: v.to_dict() for k, v in self.stock_assets.items()},
                "clans": {k: v.to_dict() for k, v in self.clans.items()},
                "transactions": [t.to_dict() for t in self.transactions[-10000:]],
            }
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 Данные сохранены в {filepath}")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")

    def load_from_disk(self, filepath: str) -> bool:
        try:
            if not os.path.exists(filepath):
                print(f"⚠️ Файл {filepath} не найден")
                return False
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.users = {int(k): User.from_dict(v) for k, v in data.get("users", {}).items()}
            self.chats = {int(k): ChatConfig.from_dict(v) for k, v in data.get("chats", {}).items()}
            self.businesses = {k: Business.from_dict(v) for k, v in data.get("businesses", {}).items()}
            self.crypto_assets = {k: CryptoAsset.from_dict(v) for k, v in data.get("crypto_assets", {}).items()}
            self.stock_assets = {k: StockAsset.from_dict(v) for k, v in data.get("stock_assets", {}).items()}
            self.clans = {k: Clan.from_dict(v) for k, v in data.get("clans", {}).items()}
            self.transactions = [Transaction.from_dict(v) for v in data.get("transactions", [])]
            print(f"✅ Данные загружены из {filepath}")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            return False


# ============================================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================================

def extract_command_args(text: str) -> Tuple[Optional[str], List[str]]:
    text = text.strip()
    parts = text.split()
    if not parts: return None, []
    return parts[0].lower(), parts[1:] if len(parts) > 1 else []

def extract_numbers(text: str) -> List[int]:
    return [int(m) for m in re.findall(r"-?\d+", text)]

def extract_mentions(text: str) -> List[int]:
    matches = re.findall(r"(?:@|tg://user\?id=)(\d+)", text)
    return [int(m) for m in matches if m.isdigit()]

def find_bot_mention(text: str) -> bool:
    text_lower = text.lower()
    for alias in ["фабле", "фабл", "fable"]:
        if alias in text_lower:
            return True
    return False

def parse_amount_from_text(text: str) -> Optional[int]:
    nums = extract_numbers(text)
    return nums[0] if nums else None

def validate_bet(bet: int) -> Tuple[bool, str]:
    if bet < CASINO_MIN_BET:
        return False, f"Минимальная ставка: {CASINO_MIN_BET}"
    if bet > CASINO_MAX_BET:
        return False, f"Максимальная ставка: {CASINO_MAX_BET}"
    return True, ""

def format_balance_card(user: User) -> str:
    lines = [
        f"👤 {user.first_name or user.username or user.user_id}",
        f"💰 Баланс: {format_currency(user.balance)}",
        f"🏦 В банке: {format_currency(user.bank_balance)}",
    ]
    if user.loan_amount > 0:
        lines.append(f"💳 Кредит: {format_currency(user.loan_amount)}")
    return "\n".join(lines)

# ============================================================
# ЭКОНОМИКА
# ============================================================

class EconomyService:
    def __init__(self, store: DataStore):
        self.store = store

    def get_balance(self, user_id: int) -> int:
        return self.store.get_user(user_id).balance

    def add_money(self, user_id: int, amount: int, description: str = "") -> Tuple[bool, str, int]:
        if amount <= 0:
            return False, "Сумма должна быть положительной", 0
        user = self.store.get_user(user_id)
        if user.balance + amount > MAX_BALANCE:
            return False, f"Баланс не может превышать {MAX_BALANCE}", 0
        user.balance += amount
        self.store.add_transaction(Transaction(
            user_id=user_id, amount=amount, balance_after=user.balance, description=description
        ))
        return True, f"Получено {format_currency(amount)}", user.balance

    def remove_money(self, user_id: int, amount: int, description: str = "") -> Tuple[bool, str, int]:
        if amount <= 0:
            return False, "Сумма должна быть положительной", 0
        user = self.store.get_user(user_id)
        if user.balance < amount:
            return False, f"Недостаточно средств. Баланс: {user.balance}", 0
        user.balance -= amount
        self.store.add_transaction(Transaction(
            user_id=user_id, amount=-amount, balance_after=user.balance, description=description
        ))
        return True, f"Списано {format_currency(amount)}", user.balance

    def transfer_money(self, sender_id: int, receiver_id: int, amount: int) -> Tuple[bool, str]:
        if sender_id == receiver_id:
            return False, "Нельзя перевести самому себе"
        success, error, _ = self.remove_money(sender_id, amount, f"Перевод пользователю {receiver_id}")
        if not success:
            return False, error
        self.add_money(receiver_id, amount, f"Перевод от пользователя {sender_id}")
        return True, f"✅ Переведено {format_currency(amount)}"

    def process_work(self, user_id: int) -> Tuple[bool, str, int]:
        user = self.store.get_user(user_id)
        if self.store.is_on_cooldown(user_id, "work"):
            remaining = self.store.get_cooldown_remaining(user_id, "work")
            return False, f"Работать можно раз в час. Осталось {format_duration(remaining)}", 0
        income = 50 + (user.level - 1) * 10
        self.store.set_command_cooldown(user_id, "work", 60)
        success, error, balance = self.add_money(user_id, income, f"Работа")
        if success:
            return True, f"✅ Вы заработали {format_currency(income)}. Баланс: {format_currency(balance)}", income
        return False, error, 0

    def process_bonus(self, user_id: int) -> Tuple[bool, str, int]:
        user = self.store.get_user(user_id)
        if user.last_bonus_time:
            hours = (datetime.now() - user.last_bonus_time).total_seconds() / 3600
            if hours < BONUS_COOLDOWN_HOURS:
                remaining = BONUS_COOLDOWN_HOURS - hours
                return False, f"Бонус доступен через {int(remaining)} ч", 0
        msg_count = self.store.get_message_counter(user_id, "bonus_messages")
        if msg_count < 1:
            return False, "Напишите хотя бы 1 сообщение", 0
        bonus = min(100 + msg_count * 10, 1000)
        user.last_bonus_time = datetime.now()
        self.store.reset_message_counter(user_id, "bonus_messages")
        success, error, balance = self.add_money(user_id, bonus, f"Бонус за {msg_count} сообщений")
        if success:
            return True, f"🎁 Бонус: {format_currency(bonus)}. Баланс: {format_currency(balance)}", bonus
        return False, error, 0

    def get_top_balances(self, limit: int = 10) -> List[Tuple[int, int, str]]:
        users = sorted(self.store.users.values(), key=lambda u: u.balance, reverse=True)[:limit]
        return [(u.user_id, u.balance, u.first_name or u.username or str(u.user_id)) for u in users]


# ============================================================
# БАНК
# ============================================================

class BankService:
    def __init__(self, store: DataStore):
        self.store = store

    def deposit(self, user_id: int, amount: int) -> Tuple[bool, str, int]:
        if amount < MIN_DEPOSIT_AMOUNT:
            return False, f"Минимальный вклад: {format_currency(MIN_DEPOSIT_AMOUNT)}", 0
        if amount > MAX_DEPOSIT_AMOUNT:
            return False, f"Максимальный вклад: {format_currency(MAX_DEPOSIT_AMOUNT)}", 0
        user = self.store.get_user(user_id)
        if user.balance < amount:
            return False, f"Недостаточно средств. Баланс: {user.balance}", 0
        user.balance -= amount
        user.bank_balance += amount
        self.store.add_transaction(Transaction(user_id, -amount, user.balance, f"Вклад в банк"))
        return True, f"✅ Вклад {format_currency(amount)} принят. В банке: {format_currency(user.bank_balance)}", user.balance

    def withdraw(self, user_id: int, amount: int) -> Tuple[bool, str, int]:
        if amount <= 0:
            return False, "Сумма должна быть положительной", 0
        user = self.store.get_user(user_id)
        if user.bank_balance < amount:
            return False, f"Недостаточно средств в банке. На счету: {format_currency(user.bank_balance)}", 0
        user.bank_balance -= amount
        user.balance += amount
        self.store.add_transaction(Transaction(user_id, amount, user.balance, f"Снятие с банка"))
        return True, f"✅ Снято {format_currency(amount)}. Баланс: {format_currency(user.balance)}", user.balance

    def take_loan(self, user_id: int, amount: int) -> Tuple[bool, str, int]:
        if amount < MIN_LOAN_AMOUNT:
            return False, f"Минимальный кредит: {format_currency(MIN_LOAN_AMOUNT)}", 0
        if amount > MAX_LOAN_AMOUNT:
            return False, f"Максимальный кредит: {format_currency(MAX_LOAN_AMOUNT)}", 0
        user = self.store.get_user(user_id)
        if user.loan_amount > 0:
            return False, f"У вас уже есть кредит: {format_currency(user.loan_amount)}", 0
        total_debt = int(amount * (1 + LOAN_INTEREST_RATE))
        user.loan_amount = total_debt
        user.loan_due_date = datetime.now() + timedelta(days=LOAN_DEFAULT_DURATION_DAYS)
        user.balance += amount
        self.store.add_transaction(Transaction(user_id, amount, user.balance, f"Кредит {amount}"))
        return True, f"✅ Кредит {format_currency(amount)} выдан. Вернуть: {format_currency(total_debt)} до {user.loan_due_date.strftime('%d.%m.%Y')}", user.balance

    def repay_loan(self, user_id: int, amount: int = 0) -> Tuple[bool, str, int]:
        user = self.store.get_user(user_id)
        if user.loan_amount <= 0:
            return False, "У вас нет кредита", 0
        repay = amount if amount > 0 else user.loan_amount
        repay = min(repay, user.loan_amount)
        if user.balance < repay:
            return False, f"Недостаточно средств. Нужно: {format_currency(repay)}", 0
        user.balance -= repay
        user.loan_amount -= repay
        if user.loan_amount <= 0:
            user.loan_amount = 0
            user.loan_due_date = None
        self.store.add_transaction(Transaction(user_id, -repay, user.balance, f"Погашение кредита"))
        return True, f"✅ Погашено {format_currency(repay)}. Остаток: {format_currency(user.loan_amount)}", user.balance


# ============================================================
# БИЗНЕС
# ============================================================

class BusinessService:
    def __init__(self, store: DataStore):
        self.store = store

    def create_business(self, user_id: int, business_type: str, name: str = "") -> Tuple[bool, str, Optional[Business]]:
        user = self.store.get_user(user_id)
        businesses = self.store.get_user_businesses(user_id)
        if len(businesses) >= MAX_BUSINESSES_PER_USER:
            return False, f"Максимум {MAX_BUSINESSES_PER_USER} бизнесов", None
        cost = 50000
        if user.balance < cost:
            return False, f"Недостаточно средств. Нужно: {format_currency(cost)}", None
        user.balance -= cost
        business = Business(
            owner_id=user_id,
            name=name or business_type,
            business_type=business_type,
            purchase_price=cost,
            current_value=cost,
            hourly_income=100,
        )
        self.store.add_business(business)
        self.store.add_transaction(Transaction(user_id, -cost, user.balance, f"Создание бизнеса {business.name}"))
        return True, f"✅ Бизнес '{business.name}' создан!", business

    def collect_income(self, user_id: int, business_id: str) -> Tuple[bool, str, int]:
        business = self.store.businesses.get(business_id)
        if not business or business.owner_id != user_id:
            return False, "Бизнес не найден", 0
        income = business.hourly_income * business.level
        user = self.store.get_user(user_id)
        user.balance += income
        business.last_collected = datetime.now()
        self.store.add_transaction(Transaction(user_id, income, user.balance, f"Доход от {business.name}"))
        return True, f"✅ Собрано {format_currency(income)} с бизнеса '{business.name}'", income

    def upgrade_business(self, user_id: int, business_id: str) -> Tuple[bool, str, Optional[Business]]:
        business = self.store.businesses.get(business_id)
        if not business or business.owner_id != user_id:
            return False, "Бизнес не найден", None
        if business.level >= MAX_BUSINESS_LEVEL:
            return False, "Бизнес максимального уровня", None
        cost = business.purchase_price * business.level * 0.5
        user = self.store.get_user(user_id)
        if user.balance < cost:
            return False, f"Недостаточно средств. Нужно: {format_currency(cost)}", None
        user.balance -= cost
        business.level += 1
        business.hourly_income = int(business.hourly_income * 1.5)
        business.current_value += cost
        self.store.add_transaction(Transaction(user_id, -cost, user.balance, f"Улучшение {business.name}"))
        return True, f"✅ Бизнес '{business.name}' улучшен до {business.level} уровня", business


# ============================================================
# КАЗИНО
# ============================================================

class CasinoService:
    def __init__(self, store: DataStore):
        self.store = store

    def play_slots(self, user_id: int, bet: int) -> Tuple[bool, str, Dict]:
        valid, error = validate_bet(bet)
        if not valid:
            return False, error, {}
        user = self.store.get_user(user_id)
        if user.balance < bet:
            return False, f"Недостаточно средств. Баланс: {format_currency(user.balance)}", {}
        if self.store.is_on_cooldown(user_id, "slots"):
            return False, f"Подождите {format_duration(self.store.get_cooldown_remaining(user_id, 'slots'))}", {}
        symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "🎰"]
        reels = [[random.choice(symbols) for _ in range(3)] for _ in range(3)]
        win = 0
        for row in range(3):
            if reels[0][row] == reels[1][row] == reels[2][row]:
                mult = {"🍒": 2, "🍋": 3, "🍊": 5, "🍇": 10, "💎": 25, "7️⃣": 50, "🎰": 100}
                win += bet * mult.get(reels[0][row], 1)
        if win > 0:
            user.balance += win - bet
            result = f"🎰 Выигрыш: {format_currency(win)}!"
        else:
            user.balance -= bet
            win = -bet
            result = f"🎰 Проигрыш: {format_currency(bet)}"
        self.store.set_command_cooldown(user_id, "slots", 1)
        return True, result, {"reels": reels, "win": win}


# ============================================================
# КРИПТА И АКЦИИ
# ============================================================

class MarketService:
    def __init__(self, store: DataStore):
        self.store = store

    def initialize_crypto(self):
        crypto_list = [
            {"ticker": "FABC", "name": "ФаблКоин", "price": 10.0},
            {"ticker": "GRTK", "name": "ГрокТокен", "price": 50.0},
            {"ticker": "DPCN", "name": "ДипЧейн", "price": 25.0},
        ]
        for c in crypto_list:
            self.store.crypto_assets[c["ticker"]] = CryptoAsset(
                ticker=c["ticker"], name=c["name"], current_price=c["price"], previous_price=c["price"]
            )

    def initialize_stocks(self):
        stock_list = [
            {"ticker": "FBLK", "name": "ФабликТех", "price": 500.0},
            {"ticker": "GRKC", "name": "ГрокКорп", "price": 1200.0},
        ]
        for s in stock_list:
            self.store.stock_assets[s["ticker"]] = StockAsset(
                ticker=s["ticker"], company_name=s["name"], current_price=s["price"], previous_price=s["price"]
            )

    def update_prices(self):
        for ticker, asset in self.store.crypto_assets.items():
            change = random.uniform(-0.05, 0.05)
            asset.previous_price = asset.current_price
            asset.current_price = round(asset.current_price * (1 + change), 2)
            asset.change_percent = round(change * 100, 2)
        for ticker, asset in self.store.stock_assets.items():
            change = random.uniform(-0.03, 0.03)
            asset.previous_price = asset.current_price
            asset.current_price = round(asset.current_price * (1 + change), 2)
            asset.change_percent = round(change * 100, 2)


# ============================================================
# ОСНОВНОЙ БОТ
# ============================================================

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.store = DataStore()
        self.economy = EconomyService(self.store)
        self.bank = BankService(self.store)
        self.business = BusinessService(self.store)
        self.casino = CasinoService(self.store)
        self.market = MarketService(self.store)
        self.market.initialize_crypto()
        self.market.initialize_stocks()
        self.update_offset = 0
        self.running = True

    async def send_message(self, chat_id: int, text: str, reply_to: Optional[int] = None):
        import aiohttp
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_to:
            data["reply_to_message_id"] = reply_to
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=data)

    async def delete_message(self, chat_id: int, message_id: int):
        import aiohttp
        url = f"https://api.telegram.org/bot{self.token}/deleteMessage"
        data = {"chat_id": chat_id, "message_id": message_id}
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=data)

    async def send_dice(self, chat_id: int, emoji: str = "🎲"):
        import aiohttp
        url = f"https://api.telegram.org/bot{self.token}/sendDice"
        data = {"chat_id": chat_id, "emoji": emoji}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as resp:
                return await resp.json()

    def get_updates(self) -> List[Dict]:
        import requests
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params = {"offset": self.update_offset, "timeout": 5, "allowed_updates": ["message", "callback_query"]}
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok") and data.get("result"):
                    self.update_offset = data["result"][-1]["update_id"] + 1
                    return data["result"]
        except Exception as e:
            print(f"❌ Ошибка получения обновлений: {e}")
        return []

    async def handle_message(self, message: Dict):
        chat = message.get("chat", {})
        from_user = message.get("from", {})
        text = message.get("text", "")
        chat_id = chat.get("id", 0)
        user_id = from_user.get("id", 0)
        message_id = message.get("message_id", 0)

        if user_id == 0 or chat_id == 0:
            return

        user = self.store.get_user(user_id)
        user.username = from_user.get("username", "")
        user.first_name = from_user.get("first_name", "")
        user.last_seen = datetime.now()
        user.total_messages += 1

        if find_bot_mention(text):
            await self.send_message(chat_id, f"👋 Привет! Я {BOT_NAME}. Напиши 'помощь' для списка команд.", message_id)
            return

        self.store.increment_message_counter(user_id, "bonus_messages")

        command, args = extract_command_args(text)
        if not command:
            return

        response = await self.process_command(user_id, chat_id, command, args)
        if response:
            await self.send_message(chat_id, response, message_id)

    async def process_command(self, user_id: int, chat_id: int, command: str, args: List[str]) -> Optional[str]:
        if command in ["баланс", "б", "balance"]:
            user = self.store.get_user(user_id)
            return format_balance_card(user)

        elif command in ["перевод", "плачу"]:
            mentions = extract_mentions(" ".join(args))
            if not mentions:
                return "❌ Укажите пользователя (@user)"
            target = mentions[0]
            nums = extract_numbers(" ".join(args))
            if not nums:
                return "❌ Укажите сумму"
            amount = nums[0]
            success, result = self.economy.transfer_money(user_id, target, amount)
            return result

        elif command in ["работа", "работка"]:
            success, result, income = self.economy.process_work(user_id)
            return result

        elif command in ["бонус"]:
            success, result, amount = self.economy.process_bonus(user_id)
            return result

        elif command in ["топ", "богачи"]:
            top = self.economy.get_top_balances()
            lines = ["🏆 Топ богачей:"]
            for i, (uid, bal, name) in enumerate(top, 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                lines.append(f"{medal} {name}: {format_currency(bal)}")
            return "\n".join(lines)

        elif command in ["вклад"]:
            nums = extract_numbers(" ".join(args))
            if not nums:
                return "❌ Укажите сумму"
            success, result, balance = self.bank.deposit(user_id, nums[0])
            return result

        elif command in ["снять"]:
            nums = extract_numbers(" ".join(args))
            if not nums:
                return "❌ Укажите сумму"
            success, result, balance = self.bank.withdraw(user_id, nums[0])
            return result

        elif command in ["кредит"]:
            nums = extract_numbers(" ".join(args))
            if not nums:
                return "❌ Укажите сумму"
            success, result, balance = self.bank.take_loan(user_id, nums[0])
            return result

        elif command in ["кредит погасить"]:
            nums = extract_numbers(" ".join(args))
            amount = nums[0] if nums else 0
            success, result, balance = self.bank.repay_loan(user_id, amount)
            return result

        elif command in ["бизнес создать"]:
            if not args:
                return "❌ Укажите тип бизнеса (кофейня, ресторан, отель)"
            name = " ".join(args[1:]) if len(args) > 1 else ""
            success, result, biz = self.business.create_business(user_id, args[0], name)
            return result

        elif command in ["бизнес прибыль"]:
            if not args:
                return "❌ Укажите ID бизнеса"
            success, result, income = self.business.collect_income(user_id, args[0])
            return result

        elif command in ["бизнес прокачать"]:
            if not args:
                return "❌ Укажите ID бизнеса"
            success, result, biz = self.business.upgrade_business(user_id, args[0])
            return result

        elif command in ["бизнес мои"]:
            businesses = self.store.get_user_businesses(user_id)
            if not businesses:
                return "❌ У вас нет бизнесов"
            lines = ["🏢 Ваши бизнесы:"]
            for b in businesses:
                lines.append(f"• {b.name} (ID: {b.business_id[:8]}) - Уровень {b.level}, Доход: {format_currency(b.hourly_income)}/час")
            return "\n".join(lines)

        elif command in ["слоты", "слот"]:
            nums = extract_numbers(" ".join(args))
            bet = nums[0] if nums else CASINO_MIN_BET
            success, result, data = self.casino.play_slots(user_id, bet)
            return result

        elif command in ["помощь", "команды", "help"]:
            return f"""
🤖 {BOT_NAME} - Доступные команды:

💰 Экономика:
баланс / б - показать баланс
перевод @user 100 - перевести деньги
работа - заработать
бонус - ежедневный бонус
топ - топ богачей

🏦 Банк:
вклад 1000 - положить в банк
снять 1000 - снять с банка
кредит 1000 - взять кредит
кредит погасить - погасить кредит

🏢 Бизнес:
бизнес создать кофейня - создать бизнес
бизнес прибыль ID - собрать доход
бизнес прокачать ID - улучшить бизнес
бизнес мои - список бизнесов

🎰 Казино:
слоты 100 - играть в слоты

ℹ️ Другое:
помощь / команды - это сообщение
"""

        return None

    async def handle_callback(self, callback: Dict):
        pass

    async def run(self):
        print(f"🤖 {BOT_NAME} запускается...")
        # Загрузка данных
        self.store.load_from_disk("data/state.json")

        # Запуск обновления цен
        import asyncio
        async def update_prices():
            while self.running:
                await asyncio.sleep(60)
                self.market.update_prices()

        asyncio.create_task(update_prices())

        while self.running:
            updates = self.get_updates()
            for update in updates:
                if "message" in update:
                    await self.handle_message(update["message"])
                elif "callback_query" in update:
                    await self.handle_callback(update["callback_query"])
            await asyncio.sleep(0.5)

    def stop(self):
        self.running = False
        self.store.save_to_disk("data/state.json")
        print("👋 Бот остановлен")


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    token = sys.argv[1] if len(sys.argv) > 1 else os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Укажите токен: python bot.py ТОКЕН")
        return

    bot = TelegramBot(token)
    try:
        await bot.run()
    except KeyboardInterrupt:
        bot.stop()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
