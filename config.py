"""
AutoReactionBot - Configuration Module
Loads and validates all environment variables and constants.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# ─── Base Paths ───────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
DATABASE_DIR = BASE_DIR / "database"
CACHE_DIR = BASE_DIR / "cache"
ASSETS_DIR = BASE_DIR / "assets"

# Ensure directories exist
for _dir in [LOG_DIR, DATABASE_DIR, CACHE_DIR, ASSETS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ─── Bot Credentials ──────────────────────────────────────────────────────────

OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
DEVELOPER_USERNAME: str = os.getenv("DEVELOPER_USERNAME", "@developer")

if not OWNER_ID:
    logging.critical("OWNER_ID is not set. Exiting.")
    sys.exit(1)

# ─── Multi-Token Load Balancing (১০টা পর্যন্ত) ───────────────────────────────

BOT_TOKENS: list[str] = []
for _i in range(1, 11):
    _token = os.getenv(f"BOT_TOKEN_{_i}", "")
    if _token:
        BOT_TOKENS.append(_token)

# Fallback: single BOT_TOKEN support (পুরনো .env এর জন্য)
if not BOT_TOKENS:
    _single = os.getenv("BOT_TOKEN", "")
    if _single:
        BOT_TOKENS.append(_single)

if not BOT_TOKENS:
    logging.critical("কোনো BOT_TOKEN পাওয়া যায়নি! .env এ BOT_TOKEN_1 থেকে BOT_TOKEN_10 দাও।")
    sys.exit(1)

# Primary token (first one) — single-instance fallback
BOT_TOKEN: str = BOT_TOKENS[0]

logging.info("✅ %d টা Bot Token লোড হয়েছে।", len(BOT_TOKENS))

# ─── Bot Metadata ─────────────────────────────────────────────────────────────

BOT_VERSION: str = "2.0.0"
BOT_NAME: str = "AutoReactionBot"
PYTHON_VERSION: str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

# ─── Database ─────────────────────────────────────────────────────────────────

DATABASE_PATH: Path = DATABASE_DIR / "bot.db"
DATABASE_BACKUP_PATH: Path = DATABASE_DIR / "bot_backup.db"

# ─── Logging ──────────────────────────────────────────────────────────────────

LOG_FILE: Path = LOG_DIR / "bot.log"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_MAX_BYTES: int = 10 * 1024 * 1024   # 10 MB
LOG_BACKUP_COUNT: int = 5

# ─── Reaction Settings ────────────────────────────────────────────────────────

DEFAULT_REACTION_DELAY: float = float(os.getenv("REACTION_DELAY", "0.5"))   # seconds
DEFAULT_REACTION_COOLDOWN: float = float(os.getenv("REACTION_COOLDOWN", "2.0"))  # seconds
REACTION_QUEUE_MAX_SIZE: int = int(os.getenv("REACTION_QUEUE_MAX_SIZE", "500"))
REACTION_RETRY_COUNT: int = int(os.getenv("REACTION_RETRY_COUNT", "3"))
REACTION_RETRY_DELAY: float = float(os.getenv("REACTION_RETRY_DELAY", "1.0"))  # seconds
FLOOD_THRESHOLD: int = int(os.getenv("FLOOD_THRESHOLD", "10"))   # reactions per 10 sec
FLOOD_WINDOW: float = float(os.getenv("FLOOD_WINDOW", "10.0"))    # seconds

# ─── Default Emoji List ───────────────────────────────────────────────────────

# ⚠️ শুধু Telegram officially supported reaction emoji ব্যবহার করা হয়েছে
# অন্য emoji দিলে Reaction_invalid error আসবে
DEFAULT_EMOJIS: list[dict] = [
    {"emoji": "👍",  "category": "positive", "weight": 10, "is_big": False},
    {"emoji": "👎",  "category": "other",    "weight": 2,  "is_big": False},
    {"emoji": "❤",   "category": "love",     "weight": 10, "is_big": False},
    {"emoji": "🔥",  "category": "fire",     "weight": 9,  "is_big": False},
    {"emoji": "🥰",  "category": "love",     "weight": 8,  "is_big": False},
    {"emoji": "👏",  "category": "positive", "weight": 7,  "is_big": False},
    {"emoji": "😁",  "category": "happy",    "weight": 7,  "is_big": False},
    {"emoji": "🤔",  "category": "other",    "weight": 4,  "is_big": False},
    {"emoji": "🤯",  "category": "fun",      "weight": 4,  "is_big": False},
    {"emoji": "😱",  "category": "fun",      "weight": 4,  "is_big": False},
    {"emoji": "🤬",  "category": "other",    "weight": 2,  "is_big": False},
    {"emoji": "😢",  "category": "other",    "weight": 3,  "is_big": False},
    {"emoji": "🎉",  "category": "fun",      "weight": 8,  "is_big": False},
    {"emoji": "🤩",  "category": "happy",    "weight": 6,  "is_big": False},
    {"emoji": "🤮",  "category": "other",    "weight": 1,  "is_big": False},
    {"emoji": "💩",  "category": "fun",      "weight": 1,  "is_big": False},
    {"emoji": "🙏",  "category": "positive", "weight": 5,  "is_big": False},
    {"emoji": "👌",  "category": "positive", "weight": 6,  "is_big": False},
    {"emoji": "🕊",  "category": "other",    "weight": 3,  "is_big": False},
    {"emoji": "🤡",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "🥱",  "category": "other",    "weight": 2,  "is_big": False},
    {"emoji": "🥴",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "😍",  "category": "love",     "weight": 7,  "is_big": False},
    {"emoji": "🐳",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "❤‍🔥", "category": "love",    "weight": 5,  "is_big": False},
    {"emoji": "🌚",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "🌭",  "category": "fun",      "weight": 1,  "is_big": False},
    {"emoji": "💯",  "category": "positive", "weight": 6,  "is_big": False},
    {"emoji": "🤣",  "category": "fun",      "weight": 5,  "is_big": False},
    {"emoji": "⚡",  "category": "fire",     "weight": 4,  "is_big": False},
    {"emoji": "🍌",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "🏆",  "category": "positive", "weight": 5,  "is_big": False},
    {"emoji": "💔",  "category": "other",    "weight": 2,  "is_big": False},
    {"emoji": "🤨",  "category": "other",    "weight": 2,  "is_big": False},
    {"emoji": "😐",  "category": "other",    "weight": 2,  "is_big": False},
    {"emoji": "🍓",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "🍾",  "category": "fun",      "weight": 3,  "is_big": False},
    {"emoji": "💋",  "category": "love",     "weight": 4,  "is_big": False},
    {"emoji": "🖕",  "category": "other",    "weight": 1,  "is_big": False},
    {"emoji": "😈",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "😴",  "category": "other",    "weight": 2,  "is_big": False},
    {"emoji": "😭",  "category": "other",    "weight": 3,  "is_big": False},
    {"emoji": "🤓",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "👻",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "👨‍💻", "category": "other",   "weight": 2,  "is_big": False},
    {"emoji": "👀",  "category": "other",    "weight": 3,  "is_big": False},
    {"emoji": "🎃",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "🙈",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "😇",  "category": "happy",    "weight": 3,  "is_big": False},
    {"emoji": "😂",  "category": "fun",      "weight": 7,  "is_big": False},
    {"emoji": "🎅",  "category": "fun",      "weight": 1,  "is_big": False},
    {"emoji": "🎄",  "category": "fun",      "weight": 1,  "is_big": False},
    {"emoji": "☃",   "category": "fun",      "weight": 1,  "is_big": False},
    {"emoji": "💅",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "🤪",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "🗿",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "🆒",  "category": "positive", "weight": 3,  "is_big": False},
    {"emoji": "💘",  "category": "love",     "weight": 3,  "is_big": False},
    {"emoji": "🙉",  "category": "fun",      "weight": 1,  "is_big": False},
    {"emoji": "🦄",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "😘",  "category": "love",     "weight": 4,  "is_big": False},
    {"emoji": "💊",  "category": "other",    "weight": 1,  "is_big": False},
    {"emoji": "🙊",  "category": "fun",      "weight": 1,  "is_big": False},
    {"emoji": "😎",  "category": "happy",    "weight": 3,  "is_big": False},
    {"emoji": "👾",  "category": "fun",      "weight": 2,  "is_big": False},
    {"emoji": "🤷",  "category": "other",    "weight": 2,  "is_big": False},
]

# ─── Broadcast ────────────────────────────────────────────────────────────────

BROADCAST_BATCH_SIZE: int = int(os.getenv("BROADCAST_BATCH_SIZE", "25"))
BROADCAST_DELAY: float = float(os.getenv("BROADCAST_DELAY", "0.05"))  # seconds between sends

# ─── Force Join ───────────────────────────────────────────────────────────────

FORCE_JOIN_CHECK_INTERVAL: int = int(os.getenv("FORCE_JOIN_CHECK_INTERVAL", "3600"))  # seconds

# ─── Supported Message Types ──────────────────────────────────────────────────

SUPPORTED_MESSAGE_TYPES: list[str] = [
    "text",
    "photo",
    "video",
    "voice",
    "animation",
    "sticker",
    "document",
    "audio",
    "poll",
    "location",
    "contact",
]

# ─── Emoji Categories ─────────────────────────────────────────────────────────

EMOJI_CATEGORIES: list[str] = ["love", "fire", "positive", "happy", "fun", "other"]

# ─── Admin Channel/Group (optional logging) ───────────────────────────────────

LOG_CHANNEL_ID: int = int(os.getenv("LOG_CHANNEL_ID", "0"))  # 0 = disabled

# ─── Health Check ─────────────────────────────────────────────────────────────

HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "300"))  # 5 minutes

# ─── Rate Limiter ─────────────────────────────────────────────────────────────

RATE_LIMIT_PER_CHAT: int = int(os.getenv("RATE_LIMIT_PER_CHAT", "5"))   # reactions per window
RATE_LIMIT_WINDOW: float = float(os.getenv("RATE_LIMIT_WINDOW", "10.0"))  # seconds

# ─── Maintenance ──────────────────────────────────────────────────────────────

MAINTENANCE_MESSAGE: str = (
    "🔧 Bot is currently under maintenance.\n"
    "Please try again later."
)

# ─── Add-to links ─────────────────────────────────────────────────────────────
# These are filled at runtime once the bot username is known.
ADD_TO_GROUP_LINK: str = ""
ADD_TO_CHANNEL_LINK: str = ""
MORE_BOTS_LINK: str = os.getenv("MORE_BOTS_LINK", "https://t.me/")
HOW_TO_USE_TEXT: str = (
    "📖 <b>How To Use AutoReactionBot</b>\n\n"
    "1️⃣ Add the bot to your <b>channel</b> or <b>group</b>.\n"
    "2️⃣ Grant the bot <b>Admin</b> permissions.\n"
    "3️⃣ The bot will automatically react to every message! 🎉\n\n"
    "💡 <b>Tips:</b>\n"
    "• Use /settings to customise reaction behaviour.\n"
    "• Use /admin to access the admin panel (owner only).\n"
    "• Random emoji mode picks a different emoji each time.\n"
    "• Enable Big Reaction for animated reactions.\n\n"
    "📞 Support: @developer"
)
