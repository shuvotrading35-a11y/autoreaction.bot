"""
AutoReactionBot - Maintenance Handler
Commands for maintenance mode, DB backup, DB optimization, and health check.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

import database as db
from config import OWNER_ID
from utils import get_system_stats, get_uptime, human_readable_size

logger = logging.getLogger(__name__)


def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def _owner_check(update: Update) -> bool:
    user = update.effective_user
    if not user or not _is_owner(user.id):
        await update.message.reply_text("⛔ Owner only.")
        return False
    return True


# ─── /maintenance command ─────────────────────────────────────────────────────

async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /maintenance on|off
    Toggle maintenance mode directly from a command.
    """
    if not await _owner_check(update):
        return

    if not context.args:
        current = await db.get_setting("maintenance")
        state = "ON 🔧" if current == "1" else "OFF ✅"
        await update.message.reply_text(
            f"🔧 Maintenance mode is currently: <b>{state}</b>\n\n"
            "Usage: <code>/maintenance on</code> or <code>/maintenance off</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    arg = context.args[0].lower()
    if arg in ("on", "1", "enable"):
        await db.set_setting("maintenance", "1")
        await update.message.reply_text("🔧 Maintenance mode <b>ENABLED</b>.", parse_mode=ParseMode.HTML)
        logger.info("Maintenance mode enabled via command.")
    elif arg in ("off", "0", "disable"):
        await db.set_setting("maintenance", "0")
        await update.message.reply_text("✅ Maintenance mode <b>DISABLED</b>.", parse_mode=ParseMode.HTML)
        logger.info("Maintenance mode disabled via command.")
    else:
        await update.message.reply_text("❌ Usage: <code>/maintenance on</code> or <code>/maintenance off</code>", parse_mode=ParseMode.HTML)


# ─── /backup command ──────────────────────────────────────────────────────────

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /backup — Create a database backup and send it to the owner.
    """
    if not await _owner_check(update):
        return

    msg = await update.message.reply_text("🔄 Creating database backup…")
    try:
        backup_path = await db.backup_database()
        size = backup_path.stat().st_size
        size_str = await human_readable_size(size)

        with backup_path.open("rb") as f:
            await update.message.reply_document(
                document=f,
                filename="bot_backup.db",
                caption=(
                    f"✅ <b>Database Backup</b>\n"
                    f"📁 Size: <b>{size_str}</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
        await msg.delete()
    except Exception as exc:
        await msg.edit_text(f"❌ Backup failed: {exc}")
        logger.error("Database backup failed: %s", exc)


# ─── /optimize command ────────────────────────────────────────────────────────

async def optimize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /optimize — Run VACUUM + ANALYZE on the database to reclaim space.
    """
    if not await _owner_check(update):
        return

    msg = await update.message.reply_text("🔄 Optimising database…")
    try:
        before = await db.get_database_size()
        await db.optimize_database()
        after = await db.get_database_size()
        before_str = await human_readable_size(before)
        after_str = await human_readable_size(after)
        saved = before - after
        saved_str = await human_readable_size(max(0, saved))

        await msg.edit_text(
            f"✅ <b>Database Optimised</b>\n\n"
            f"Before: <b>{before_str}</b>\n"
            f"After: <b>{after_str}</b>\n"
            f"Saved: <b>{saved_str}</b>",
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        await msg.edit_text(f"❌ Optimisation failed: {exc}")
        logger.error("Database optimise failed: %s", exc)


# ─── /health command ──────────────────────────────────────────────────────────

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /health — Show a full system health report.
    """
    if not await _owner_check(update):
        return

    stats = await get_system_stats()
    uptime = get_uptime()
    db_size = await db.get_database_size()
    db_size_str = await human_readable_size(db_size)
    total_reactions = await db.get_total_reactions()
    total_users = await db.get_total_users()

    settings = await db.get_all_settings()
    auto_r = "✅" if settings.get("auto_reaction") == "1" else "❌"
    maint = "🔧 ON" if settings.get("maintenance") == "1" else "✅ OFF"

    text = (
        "🏥 <b>System Health Report</b>\n"
        f"{'─' * 30}\n\n"
        f"⏱ Uptime: <b>{uptime}</b>\n"
        f"🖥 CPU Usage: <b>{stats['cpu_percent']:.1f}%</b>\n"
        f"💾 RAM Used: <b>{stats['process_rss_mb']} MB</b>\n"
        f"🐍 Python: <b>{stats['python_version']}</b>\n"
        f"💻 Platform: <b>{stats['platform']}</b>\n\n"
        f"🗄 Database: ✅ Connected\n"
        f"📦 DB Size: <b>{db_size_str}</b>\n\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"⚡ Total Reactions: <b>{total_reactions}</b>\n\n"
        f"Auto Reaction: {auto_r}\n"
        f"Maintenance: {maint}"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ─── Handler registration ─────────────────────────────────────────────────────

def register(application) -> None:
    """Register maintenance-related command handlers."""
    application.add_handler(CommandHandler("maintenance", maintenance_command))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(CommandHandler("optimize", optimize_command))
    application.add_handler(CommandHandler("health", health_command))
