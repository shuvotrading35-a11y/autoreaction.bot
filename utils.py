"""
AutoReactionBot - Utilities Module
Colored logging, rate limiter, emoji selector, health check, uptime tracker.
"""

import asyncio
import logging
import os
import platform
import random
import sys
import time
from collections import defaultdict
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import psutil

from config import (
    LOG_FILE,
    LOG_LEVEL,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    RATE_LIMIT_PER_CHAT,
    RATE_LIMIT_WINDOW,
    FLOOD_THRESHOLD,
    FLOOD_WINDOW,
)

# ─── Bot start time ───────────────────────────────────────────────────────────

_BOT_START_TIME: float = time.time()


def get_uptime() -> str:
    """Return human-readable uptime string."""
    elapsed = int(time.time() - _BOT_START_TIME)
    days, remainder = divmod(elapsed, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


# ─── Colored Console Logging ──────────────────────────────────────────────────

class _ColoredFormatter(logging.Formatter):
    """
    Adds ANSI color codes to log level names for terminal output.
    """

    COLORS = {
        "DEBUG":    "\033[94m",   # Blue
        "INFO":     "\033[92m",   # Green
        "WARNING":  "\033[93m",   # Yellow
        "ERROR":    "\033[91m",   # Red
        "CRITICAL": "\033[1;91m", # Bold Red
    }
    RESET = "\033[0m"
    GREY = "\033[90m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        record.name = f"{self.GREY}{record.name}{self.RESET}"
        return super().format(record)


def setup_logging() -> None:
    """
    Configure the root logger with:
    - Colored console handler
    - Rotating file handler
    """
    root = logging.getLogger()
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    root.setLevel(level)

    # Prevent duplicate handlers when called multiple times
    root.handlers.clear()

    # ── Console handler ───────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_fmt = _ColoredFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    root.addHandler(console_handler)

    # ── File handler (rotating) ───────────────────────────────────────────
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)

    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


# ─── Rate Limiter ─────────────────────────────────────────────────────────────

class RateLimiter:
    """
    Per-chat sliding-window rate limiter.
    Tracks timestamps of recent reactions and rejects if over threshold.
    """

    def __init__(
        self,
        max_calls: int = RATE_LIMIT_PER_CHAT,
        window: float = RATE_LIMIT_WINDOW,
    ) -> None:
        self._max_calls = max_calls
        self._window = window
        self._timestamps: dict[int, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, chat_id: int) -> bool:
        """
        Return True if the chat is within rate limits.
        Prune expired timestamps automatically.
        """
        async with self._lock:
            now = time.monotonic()
            ts_list = self._timestamps[chat_id]
            # Remove timestamps outside the window
            self._timestamps[chat_id] = [
                t for t in ts_list if now - t < self._window
            ]
            if len(self._timestamps[chat_id]) < self._max_calls:
                self._timestamps[chat_id].append(now)
                return True
            return False

    async def clear_chat(self, chat_id: int) -> None:
        """Clear rate-limit history for a specific chat."""
        async with self._lock:
            self._timestamps.pop(chat_id, None)


# ─── Flood Protector ──────────────────────────────────────────────────────────

class FloodProtector:
    """
    Global flood guard: tracks total reactions across all chats
    and blocks if the rate exceeds FLOOD_THRESHOLD per FLOOD_WINDOW.
    """

    def __init__(
        self,
        threshold: int = FLOOD_THRESHOLD,
        window: float = FLOOD_WINDOW,
    ) -> None:
        self._threshold = threshold
        self._window = window
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def is_flooding(self) -> bool:
        """Return True if currently flooding (should back off)."""
        async with self._lock:
            now = time.monotonic()
            self._timestamps = [t for t in self._timestamps if now - t < self._window]
            if len(self._timestamps) >= self._threshold:
                return True
            self._timestamps.append(now)
            return False


# ─── Emoji Selector ───────────────────────────────────────────────────────────

def pick_emoji(emojis: list[dict], random_mode: bool = True) -> dict:
    """
    Select an emoji from the list.
    - If random_mode is True, use weighted random selection.
    - Otherwise return the highest-weight emoji.
    """
    if not emojis:
        return {"emoji": "❤️", "is_big": False}

    if random_mode:
        weights = [e.get("weight", 1) for e in emojis]
        return random.choices(emojis, weights=weights, k=1)[0]
    else:
        return max(emojis, key=lambda e: e.get("weight", 1))


# ─── System Health ────────────────────────────────────────────────────────────

async def get_system_stats() -> dict:
    """
    Return a snapshot of current system metrics:
    CPU%, RAM usage, and the current process's memory.
    """
    loop = asyncio.get_event_loop()

    def _gather() -> dict:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        vm = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_total_mb": vm.total // (1024 * 1024),
            "ram_used_mb": vm.used // (1024 * 1024),
            "ram_percent": vm.percent,
            "process_rss_mb": mem_info.rss // (1024 * 1024),
            "python_version": platform.python_version(),
            "platform": platform.system(),
        }

    stats = await loop.run_in_executor(None, _gather)
    return stats


async def human_readable_size(num_bytes: int) -> str:
    """Convert bytes to a human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0  # type: ignore[assignment]
    return f"{num_bytes:.1f} TB"


# ─── Input Validation ─────────────────────────────────────────────────────────

def is_valid_emoji(text: str) -> bool:
    """
    Basic check: the string must be non-empty and reasonably short.
    Telegram reaction emojis are 1-2 Unicode characters.
    """
    text = text.strip()
    return 1 <= len(text) <= 8 and text != ""


def sanitize_text(text: str, max_length: int = 4096) -> str:
    """Strip and truncate text to prevent oversized messages."""
    return text.strip()[:max_length]


# ─── Progress Bar ─────────────────────────────────────────────────────────────

def make_progress_bar(current: int, total: int, width: int = 20) -> str:
    """
    Generate a Unicode progress bar string.
    E.g.  ████████████░░░░░░░░  60%
    """
    if total == 0:
        return f"{'░' * width}  0%"
    ratio = current / total
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar}  {ratio * 100:.1f}%"


# ─── Mention Builder ──────────────────────────────────────────────────────────

def build_mention(user_id: int, first_name: str) -> str:
    """Return an HTML mention link for a Telegram user."""
    safe = first_name.replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="tg://user?id={user_id}">{safe}</a>'


# ─── Chunk List ───────────────────────────────────────────────────────────────

def chunks(lst: list, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


# ─── Supported message detector ───────────────────────────────────────────────

def get_message_type(message) -> Optional[str]:
    """
    Inspect a telegram Message object and return its content type string,
    or None if unsupported.
    """
    if message.text:
        return "text"
    if message.photo:
        return "photo"
    if message.video:
        return "video"
    if message.voice:
        return "voice"
    if message.animation:
        return "animation"
    if message.sticker:
        return "sticker"
    if message.document:
        return "document"
    if message.audio:
        return "audio"
    if message.poll:
        return "poll"
    if message.location:
        return "location"
    if message.contact:
        return "contact"
    return None
