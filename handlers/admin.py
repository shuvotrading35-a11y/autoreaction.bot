"""
AutoReactionBot - Admin Handler
Handles /admin command and all admin panel callbacks.
Owner-only access enforced on every entry point.
"""

import logging
import os
import signal
import sys

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
from config import OWNER_ID
from keyboards import (
    admin_back_keyboard,
    admin_panel_keyboard,
    banned_chats_keyboard,
    close_keyboard,
    statistics_keyboard,
)
from utils import get_system_stats, get_uptime, human_readable_size

logger = logging.getLogger(__name__)


# ─── Owner guard ─────────────────────────────────────────────────────────────

def _is_owner(user_id: int) -> bool:
    """Return True if the user is the bot owner."""
    return user_id == OWNER_ID


async def _owner_only(update: Update, respond: bool = True) -> bool:
    """
    Check if the caller is the owner.
    If not, optionally send an error and return False.
    """
    user = update.effective_user
    if not user or not _is_owner(user.id):
        if respond:
            if update.callback_query:
                await update.callback_query.answer(
                    "⛔ Owner only!", show_alert=True
                )
            elif update.message:
                await update.message.reply_text("⛔ This command is restricted to the bot owner.")
        return False
    return True


# ─── /admin command ───────────────────────────────────────────────────────────

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for /admin command — shows the admin panel."""
    if not await _owner_only(update):
        return

    await update.message.reply_text(
        "🟠 <b>Admin Panel</b>\n\nChoose an option:",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard(),
    )


# ─── Callback: admin_panel ────────────────────────────────────────────────────

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-render the admin panel inline."""
    if not await _owner_only(update):
        return
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            "🟠 <b>Admin Panel</b>\n\nChoose an option:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_panel_keyboard(),
        )
    except Exception:
        pass


# ─── Callback: admin_dashboard ────────────────────────────────────────────────

async def dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show the live bot dashboard:
    users, groups, channels, reactions, system metrics, settings snapshot.
    """
    if not await _owner_only(update):
        return
    query = update.callback_query
    await query.answer()

    stats = await get_system_stats()
    settings = await db.get_all_settings()
    uptime = get_uptime()

    total_users = await db.get_total_users()
    today_users = await db.get_today_users()
    total_groups = await db.get_total_groups()
    total_channels = await db.get_total_channels()
    total_reactions = await db.get_total_reactions()
    today_reactions = await db.get_today_reactions()
    db_size = await db.get_database_size()
    db_size_str = await human_readable_size(db_size)

    auto_react = "✅" if settings.get("auto_reaction") == "1" else "❌"
    random_em = "✅" if settings.get("random_emoji") == "1" else "❌"
    big_react = "✅" if settings.get("big_reaction") == "1" else "❌"
    maint = "🔧 ON" if settings.get("maintenance") == "1" else "✅ OFF"

    text = (
        "📊 <b>Bot Dashboard</b>\n"
        f"{'─' * 30}\n\n"
        "👥 <b>Users</b>\n"
        f"  ├ Total: <b>{total_users}</b>\n"
        f"  └ Today: <b>{today_users}</b>\n\n"
        "🏘 <b>Groups</b>\n"
        f"  └ Active: <b>{total_groups}</b>\n\n"
        "📡 <b>Channels</b>\n"
        f"  └ Active: <b>{total_channels}</b>\n\n"
        "⚡ <b>Reactions</b>\n"
        f"  ├ Total: <b>{total_reactions}</b>\n"
        f"  └ Today: <b>{today_reactions}</b>\n\n"
        "🖥 <b>System</b>\n"
        f"  ├ CPU: <b>{stats['cpu_percent']:.1f}%</b>\n"
        f"  ├ RAM: <b>{stats['process_rss_mb']} MB</b>\n"
        f"  ├ DB Size: <b>{db_size_str}</b>\n"
        f"  └ Uptime: <b>{uptime}</b>\n\n"
        "⚙️ <b>Status</b>\n"
        f"  ├ Auto Reaction: {auto_react}\n"
        f"  ├ Random Emoji: {random_em}\n"
        f"  ├ Big Reaction: {big_react}\n"
        f"  └ Maintenance: {maint}"
    )

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_back_keyboard(),
    )


# ─── Callback: admin_groups ───────────────────────────────────────────────────

async def groups_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all active groups the bot is in."""
    if not await _owner_only(update):
        return
    query = update.callback_query
    await query.answer()

    groups = await db.get_all_groups()
    if not groups:
        text = "🏘 <b>Groups</b>\n\nNo groups found."
    else:
        lines = ["🏘 <b>Active Groups</b>\n"]
        for i, g in enumerate(groups[:50], 1):
            username = f"@{g['username']}" if g.get("username") else "Private"
            lines.append(f"{i}. <b>{g['title']}</b>  [<code>{g['chat_id']}</code>]  {username}")
        if len(groups) > 50:
            lines.append(f"\n… and {len(groups) - 50} more.")
        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_back_keyboard(),
    )


# ─── Callback: admin_channels ─────────────────────────────────────────────────

async def channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all active channels the bot is in."""
    if not await _owner_only(update):
        return
    query = update.callback_query
    await query.answer()

    channels = await db.get_all_channels()
    if not channels:
        text = "📡 <b>Channels</b>\n\nNo channels found."
    else:
        lines = ["📡 <b>Active Channels</b>\n"]
        for i, ch in enumerate(channels[:50], 1):
            username = f"@{ch['username']}" if ch.get("username") else "Private"
            lines.append(
                f"{i}. <b>{ch['title']}</b>  [<code>{ch['chat_id']}</code>]  {username}"
            )
        if len(channels) > 50:
            lines.append(f"\n… and {len(channels) - 50} more.")
        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_back_keyboard(),
    )


# ─── Callback: banned_chats ───────────────────────────────────────────────────

async def banned_chats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show banned chats management panel."""
    if not await _owner_only(update):
        return
    query = update.callback_query
    await query.answer()

    chats = await db.get_banned_chats()
    if not chats:
        text = "🚫 <b>Banned Chats</b>\n\nNo chats are banned."
    else:
        lines = ["🚫 <b>Banned Chats</b>\n"]
        for i, c in enumerate(chats[:30], 1):
            lines.append(
                f"{i}. <code>{c['chat_id']}</code>  —  {c.get('reason', 'N/A')}"
            )
        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=banned_chats_keyboard(),
    )


# ─── /ban command ─────────────────────────────────────────────────────────────

async def ban_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /ban <chat_id> [reason]
    Ban a chat so the bot never reacts to messages there.
    """
    if not await _owner_only(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <chat_id> [reason]")
        return
    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid chat_id — must be an integer.")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason"
    await db.ban_chat(chat_id, reason)
    await update.message.reply_text(
        f"✅ Chat <code>{chat_id}</code> has been banned.\nReason: {reason}",
        parse_mode=ParseMode.HTML,
    )
    logger.info("Admin banned chat %d: %s", chat_id, reason)


# ─── /unban command ───────────────────────────────────────────────────────────

async def unban_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/unban <chat_id> — Unban a previously banned chat."""
    if not await _owner_only(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <chat_id>")
        return
    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid chat_id.")
        return
    await db.unban_chat(chat_id)
    await update.message.reply_text(
        f"✅ Chat <code>{chat_id}</code> has been unbanned.",
        parse_mode=ParseMode.HTML,
    )


# ─── Callback: admin_logs ─────────────────────────────────────────────────────

async def admin_logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show the last 20 lines of the log file inline.
    """
    if not await _owner_only(update):
        return
    query = update.callback_query
    await query.answer()

    from config import LOG_FILE

    try:
        with LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = lines[-20:] if len(lines) >= 20 else lines
        log_text = "".join(tail).strip()
        if not log_text:
            log_text = "(Log file is empty)"
    except Exception as exc:
        log_text = f"Could not read log: {exc}"

    # Truncate to Telegram's message limit
    if len(log_text) > 3800:
        log_text = log_text[-3800:]

    await query.edit_message_text(
        f"📋 <b>Recent Logs</b>\n\n<pre>{log_text}</pre>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_back_keyboard(),
    )


# ─── Callback: admin_restart ──────────────────────────────────────────────────

async def restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Confirm then restart the bot process.
    Uses os.execv to replace the current process.
    """
    if not await _owner_only(update):
        return
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔄 <b>Restarting bot…</b>\nSee you in a moment!",
        parse_mode=ParseMode.HTML,
    )

    logger.info("Admin triggered bot restart.")
    # Schedule restart after a short delay to allow the message to send
    asyncio.get_event_loop().call_later(
        1.5,
        lambda: os.execv(sys.executable, [sys.executable] + sys.argv),
    )


# ─── Handler registration ─────────────────────────────────────────────────────

def register(application) -> None:
    """Register all admin handlers."""
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("ban", ban_chat_command))
    application.add_handler(CommandHandler("unban", unban_chat_command))

    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(dashboard_callback, pattern="^admin_dashboard$"))
    application.add_handler(CallbackQueryHandler(groups_callback, pattern="^admin_groups$"))
    application.add_handler(CallbackQueryHandler(channels_callback, pattern="^admin_channels$"))
    application.add_handler(CallbackQueryHandler(banned_chats_callback, pattern="^banned_chats$"))
    application.add_handler(CallbackQueryHandler(admin_logs_callback, pattern="^admin_logs$"))
    application.add_handler(CallbackQueryHandler(restart_callback, pattern="^admin_restart$"))
