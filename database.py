"""
AutoReactionBot - Database Module
Handles all async SQLite operations with parameterized queries.
"""

import asyncio
import logging
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite
from contextlib import asynccontextmanager

from config import DATABASE_PATH, DATABASE_BACKUP_PATH, DEFAULT_EMOJIS

logger = logging.getLogger(__name__)


# ─── Connection Pool ──────────────────────────────────────────────────────────

_db_lock = asyncio.Lock()


@asynccontextmanager
async def get_db():
    conn = await aiosqlite.connect(DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
    finally:
        await conn.close()


# ─── Schema Initialisation ────────────────────────────────────────────────────

async def init_db() -> None:
    """
    Create all required tables if they do not already exist
    and seed default data.
    """
    async with get_db() as db:
        # ── users ──────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                last_name   TEXT,
                language    TEXT DEFAULT 'en',
                is_banned   INTEGER DEFAULT 0,
                joined_at   TEXT DEFAULT (datetime('now')),
                last_seen   TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── groups ─────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id     INTEGER PRIMARY KEY,
                title       TEXT,
                username    TEXT,
                is_active   INTEGER DEFAULT 1,
                added_at    TEXT DEFAULT (datetime('now')),
                last_seen   TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── channels ───────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                chat_id     INTEGER PRIMARY KEY,
                title       TEXT,
                username    TEXT,
                is_active   INTEGER DEFAULT 1,
                added_at    TEXT DEFAULT (datetime('now')),
                last_seen   TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── settings ───────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT NOT NULL
            )
        """)

        # ── admins ─────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                added_by    INTEGER,
                added_at    TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── emojis ─────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS emojis (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                emoji       TEXT NOT NULL UNIQUE,
                category    TEXT DEFAULT 'other',
                weight      INTEGER DEFAULT 1,
                is_big      INTEGER DEFAULT 0,
                is_enabled  INTEGER DEFAULT 1,
                added_at    TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── statistics ─────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_date       TEXT NOT NULL,
                reactions_sent  INTEGER DEFAULT 0,
                messages_seen   INTEGER DEFAULT 0,
                new_users       INTEGER DEFAULT 0,
                new_groups      INTEGER DEFAULT 0,
                new_channels    INTEGER DEFAULT 0,
                UNIQUE(stat_date)
            )
        """)

        # ── broadcast_logs ─────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_type  TEXT,
                total           INTEGER DEFAULT 0,
                success         INTEGER DEFAULT 0,
                failed          INTEGER DEFAULT 0,
                started_at      TEXT DEFAULT (datetime('now')),
                finished_at     TEXT
            )
        """)

        # ── reaction_logs ──────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                message_id  INTEGER NOT NULL,
                emoji       TEXT NOT NULL,
                is_big      INTEGER DEFAULT 0,
                reacted_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── banned_chats ───────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS banned_chats (
                chat_id     INTEGER PRIMARY KEY,
                reason      TEXT,
                banned_at   TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── force_join ─────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS force_join (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id  INTEGER NOT NULL UNIQUE,
                channel_username TEXT,
                invite_link TEXT,
                added_at    TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.commit()

        # ── Seed default settings ─────────────────────────────────────────
        defaults = {
            "auto_reaction": "1",
            "random_emoji": "1",
            "big_reaction": "0",
            "reaction_delay": "0.5",
            "maintenance": "0",
            "force_join": "0",
            "logging_enabled": "1",
        }
        for key, value in defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

        # ── Seed default emojis ───────────────────────────────────────────
        for emoji_data in DEFAULT_EMOJIS:
            await db.execute(
                """
                INSERT OR IGNORE INTO emojis (emoji, category, weight, is_big)
                VALUES (?, ?, ?, ?)
                """,
                (
                    emoji_data["emoji"],
                    emoji_data["category"],
                    emoji_data["weight"],
                    int(emoji_data["is_big"]),
                ),
            )

        await db.commit()

    logger.info("Database initialised at %s", DATABASE_PATH)


# ─── Settings ─────────────────────────────────────────────────────────────────

async def get_setting(key: str) -> Optional[str]:
    """Return the string value of a setting, or None if not found."""
    async with get_db() as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["value"] if row else None


async def set_setting(key: str, value: str) -> None:
    """Upsert a setting value."""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


async def get_all_settings() -> dict[str, str]:
    """Return all settings as a dictionary."""
    async with get_db() as db:
        async with db.execute("SELECT key, value FROM settings") as cursor:
            rows = await cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}


# ─── Users ────────────────────────────────────────────────────────────────────

async def upsert_user(
    user_id: int,
    username: Optional[str],
    first_name: str,
    last_name: Optional[str],
) -> bool:
    """
    Insert or update a user record.
    Returns True if this is a new user.
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            await db.execute(
                """
                UPDATE users
                SET username = ?, first_name = ?, last_name = ?, last_seen = datetime('now')
                WHERE user_id = ?
                """,
                (username, first_name, last_name, user_id),
            )
            await db.commit()
            return False
        else:
            await db.execute(
                """
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, username, first_name, last_name),
            )
            await db.commit()
            await _increment_stat("new_users")
            return True


async def get_user(user_id: int) -> Optional[dict]:
    """Fetch a single user by ID."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def is_user_banned(user_id: int) -> bool:
    """Check if a user is banned."""
    user = await get_user(user_id)
    return bool(user and user.get("is_banned"))


async def get_all_users() -> list[dict]:
    """Return all non-banned users."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM users WHERE is_banned = 0"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_total_users() -> int:
    """Return total user count."""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) AS cnt FROM users") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


async def get_today_users() -> int:
    """Return count of users who joined today."""
    today = date.today().isoformat()
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) AS cnt FROM users WHERE DATE(joined_at) = ?",
            (today,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


# ─── Groups ───────────────────────────────────────────────────────────────────

async def upsert_group(chat_id: int, title: str, username: Optional[str]) -> bool:
    """Insert or update a group record. Returns True if new."""
    async with get_db() as db:
        async with db.execute(
            "SELECT chat_id FROM groups WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            await db.execute(
                """
                UPDATE groups
                SET title = ?, username = ?, last_seen = datetime('now'), is_active = 1
                WHERE chat_id = ?
                """,
                (title, username, chat_id),
            )
            await db.commit()
            return False
        else:
            await db.execute(
                "INSERT INTO groups (chat_id, title, username) VALUES (?, ?, ?)",
                (chat_id, title, username),
            )
            await db.commit()
            await _increment_stat("new_groups")
            return True


async def get_all_groups() -> list[dict]:
    """Return all active groups."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM groups WHERE is_active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_total_groups() -> int:
    """Return total group count."""
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) AS cnt FROM groups WHERE is_active = 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


async def deactivate_group(chat_id: int) -> None:
    """Mark a group as inactive (bot removed)."""
    async with get_db() as db:
        await db.execute(
            "UPDATE groups SET is_active = 0 WHERE chat_id = ?", (chat_id,)
        )
        await db.commit()


# ─── Channels ─────────────────────────────────────────────────────────────────

async def upsert_channel(chat_id: int, title: str, username: Optional[str]) -> bool:
    """Insert or update a channel record. Returns True if new."""
    async with get_db() as db:
        async with db.execute(
            "SELECT chat_id FROM channels WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            await db.execute(
                """
                UPDATE channels
                SET title = ?, username = ?, last_seen = datetime('now'), is_active = 1
                WHERE chat_id = ?
                """,
                (title, username, chat_id),
            )
            await db.commit()
            return False
        else:
            await db.execute(
                "INSERT INTO channels (chat_id, title, username) VALUES (?, ?, ?)",
                (chat_id, title, username),
            )
            await db.commit()
            await _increment_stat("new_channels")
            return True


async def get_all_channels() -> list[dict]:
    """Return all active channels."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM channels WHERE is_active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_total_channels() -> int:
    """Return total channel count."""
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) AS cnt FROM channels WHERE is_active = 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


async def deactivate_channel(chat_id: int) -> None:
    """Mark a channel as inactive."""
    async with get_db() as db:
        await db.execute(
            "UPDATE channels SET is_active = 0 WHERE chat_id = ?", (chat_id,)
        )
        await db.commit()


# ─── Emojis ───────────────────────────────────────────────────────────────────

async def get_active_emojis(category: Optional[str] = None) -> list[dict]:
    """Return all enabled emojis, optionally filtered by category."""
    async with get_db() as db:
        if category:
            async with db.execute(
                "SELECT * FROM emojis WHERE is_enabled = 1 AND category = ?",
                (category,),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM emojis WHERE is_enabled = 1"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_emojis() -> list[dict]:
    """Return all emojis (including disabled)."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM emojis ORDER BY weight DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def add_emoji(
    emoji: str,
    category: str = "other",
    weight: int = 1,
    is_big: bool = False,
) -> bool:
    """
    Add a new emoji to the database.
    Returns False if emoji already exists.
    """
    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO emojis (emoji, category, weight, is_big)
                VALUES (?, ?, ?, ?)
                """,
                (emoji, category, weight, int(is_big)),
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def remove_emoji(emoji_id: int) -> bool:
    """Delete an emoji by ID. Returns False if not found."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM emojis WHERE id = ?", (emoji_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        await db.execute("DELETE FROM emojis WHERE id = ?", (emoji_id,))
        await db.commit()
    return True


async def toggle_emoji(emoji_id: int) -> Optional[bool]:
    """
    Toggle is_enabled for an emoji.
    Returns the new state (True=enabled), or None if not found.
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT is_enabled FROM emojis WHERE id = ?", (emoji_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        new_state = 0 if row["is_enabled"] else 1
        await db.execute(
            "UPDATE emojis SET is_enabled = ? WHERE id = ?", (new_state, emoji_id)
        )
        await db.commit()
    return bool(new_state)


async def update_emoji_weight(emoji_id: int, weight: int) -> bool:
    """Update the weight of an emoji."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM emojis WHERE id = ?", (emoji_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        await db.execute(
            "UPDATE emojis SET weight = ? WHERE id = ?", (weight, emoji_id)
        )
        await db.commit()
    return True


# ─── Reaction Logs ────────────────────────────────────────────────────────────

async def log_reaction(
    chat_id: int, message_id: int, emoji: str, is_big: bool
) -> None:
    """Store a reaction event in the log."""
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO reaction_logs (chat_id, message_id, emoji, is_big)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, message_id, emoji, int(is_big)),
        )
        await db.commit()
    await _increment_stat("reactions_sent")


async def get_total_reactions() -> int:
    """Return total reactions sent."""
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) AS cnt FROM reaction_logs"
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


async def get_today_reactions() -> int:
    """Return today's reaction count."""
    today = date.today().isoformat()
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) AS cnt FROM reaction_logs WHERE DATE(reacted_at) = ?",
            (today,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


async def get_most_used_emojis(limit: int = 10) -> list[dict]:
    """Return the top N most used emojis."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT emoji, COUNT(*) AS usage_count
            FROM reaction_logs
            GROUP BY emoji
            ORDER BY usage_count DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_top_active_chats(limit: int = 10) -> list[dict]:
    """Return the top N most active chats by reaction count."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT chat_id, COUNT(*) AS reaction_count
            FROM reaction_logs
            GROUP BY chat_id
            ORDER BY reaction_count DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─── Statistics ───────────────────────────────────────────────────────────────

async def _increment_stat(column: str, amount: int = 1) -> None:
    """Increment a daily statistic column for today."""
    today = date.today().isoformat()
    async with get_db() as db:
        await db.execute(
            f"""
            INSERT INTO statistics (stat_date, {column})
            VALUES (?, ?)
            ON CONFLICT(stat_date)
            DO UPDATE SET {column} = {column} + ?
            """,
            (today, amount, amount),
        )
        await db.commit()


async def get_weekly_stats() -> list[dict]:
    """Return statistics for the last 7 days."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT * FROM statistics
            ORDER BY stat_date DESC
            LIMIT 7
            """,
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_monthly_stats() -> list[dict]:
    """Return statistics for the last 30 days."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT * FROM statistics
            ORDER BY stat_date DESC
            LIMIT 30
            """,
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─── Broadcast Logs ───────────────────────────────────────────────────────────

async def create_broadcast_log(broadcast_type: str, total: int) -> int:
    """Create a broadcast log entry and return its ID."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO broadcast_logs (broadcast_type, total)
            VALUES (?, ?)
            """,
            (broadcast_type, total),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def update_broadcast_log(
    log_id: int, success: int, failed: int
) -> None:
    """Update a broadcast log with results."""
    async with get_db() as db:
        await db.execute(
            """
            UPDATE broadcast_logs
            SET success = ?, failed = ?, finished_at = datetime('now')
            WHERE id = ?
            """,
            (success, failed, log_id),
        )
        await db.commit()


# ─── Banned Chats ─────────────────────────────────────────────────────────────

async def ban_chat(chat_id: int, reason: str = "No reason") -> None:
    """Add a chat to the banned list."""
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO banned_chats (chat_id, reason) VALUES (?, ?)",
            (chat_id, reason),
        )
        await db.commit()


async def unban_chat(chat_id: int) -> None:
    """Remove a chat from the banned list."""
    async with get_db() as db:
        await db.execute(
            "DELETE FROM banned_chats WHERE chat_id = ?", (chat_id,)
        )
        await db.commit()


async def is_chat_banned(chat_id: int) -> bool:
    """Return True if chat is banned."""
    async with get_db() as db:
        async with db.execute(
            "SELECT chat_id FROM banned_chats WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def get_banned_chats() -> list[dict]:
    """Return all banned chats."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM banned_chats ORDER BY banned_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─── Force Join ───────────────────────────────────────────────────────────────

async def add_force_join_channel(
    channel_id: int, username: Optional[str], invite_link: Optional[str]
) -> bool:
    """Add a channel to the force-join list. Returns False if already present."""
    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO force_join (channel_id, channel_username, invite_link)
                VALUES (?, ?, ?)
                """,
                (channel_id, username, invite_link),
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def remove_force_join_channel(channel_id: int) -> bool:
    """Remove a channel from the force-join list."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM force_join WHERE channel_id = ?", (channel_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        await db.execute(
            "DELETE FROM force_join WHERE channel_id = ?", (channel_id,)
        )
        await db.commit()
    return True


async def get_force_join_channels() -> list[dict]:
    """Return all force-join channels."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM force_join") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─── Admins ───────────────────────────────────────────────────────────────────

async def add_admin(user_id: int, username: Optional[str], added_by: int) -> bool:
    """Add a bot admin. Returns False if already an admin."""
    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO admins (user_id, username, added_by)
                VALUES (?, ?, ?)
                """,
                (user_id, username, added_by),
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def remove_admin(user_id: int) -> bool:
    """Remove a bot admin."""
    async with get_db() as db:
        async with db.execute(
            "SELECT user_id FROM admins WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()
    return True


async def is_admin(user_id: int) -> bool:
    """Return True if user is a bot admin."""
    async with get_db() as db:
        async with db.execute(
            "SELECT user_id FROM admins WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def get_all_admins() -> list[dict]:
    """Return all bot admins."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM admins") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─── Database Utilities ───────────────────────────────────────────────────────

async def backup_database() -> Path:
    """Copy the database file to the backup path and return the backup path."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, shutil.copy2, str(DATABASE_PATH), str(DATABASE_BACKUP_PATH)
    )
    logger.info("Database backed up to %s", DATABASE_BACKUP_PATH)
    return DATABASE_BACKUP_PATH


async def get_database_size() -> int:
    """Return database file size in bytes."""
    loop = asyncio.get_event_loop()
    size = await loop.run_in_executor(None, DATABASE_PATH.stat)
    return size.st_size


async def optimize_database() -> None:
    """Run VACUUM and ANALYZE on the database."""
    async with get_db() as db:
        await db.execute("VACUUM")
        await db.execute("ANALYZE")
        await db.commit()
    logger.info("Database optimised.")
