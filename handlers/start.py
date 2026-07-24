"""
AutoReactionBot - Start Handler
Handles /start command: sends banner image + welcome message + inline menu.
Also handles the 'how_to_use' and 'main_menu' callbacks.
"""

import logging
import sys
from pathlib import Path

from telegram import InputFile, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
from config import (
    ASSETS_DIR,
    BOT_VERSION,
    DEVELOPER_USERNAME,
    MAINTENANCE_MESSAGE,
    OWNER_ID,
    HOW_TO_USE_TEXT,
)
from keyboards import back_to_main_keyboard, main_menu_keyboard
from utils import get_uptime, get_system_stats

logger = logging.getLogger(__name__)

BANNER_PATH = ASSETS_DIR / "banner.jpg"


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _is_maintenance(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Return True if maintenance mode is active and the user is not the owner."""
    if user_id == OWNER_ID:
        return False
    setting = await db.get_setting("maintenance")
    return setting == "1"


async def _build_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Compose the welcome message string with live system/db data.
    """
    user = update.effective_user
    stats = await get_system_stats()
    uptime = get_uptime()
    total_users = await db.get_total_users()
    db_size = await db.get_database_size()
    db_size_kb = db_size / 1024

    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    username_str = f"@{user.username}" if user.username else "N/A"

    text = (
        f"🤖 <b>AutoReactionBot</b>  v{BOT_VERSION}\n"
        f"{'─' * 32}\n\n"
        f"👋 Hello, {mention}!\n\n"
        f"👤 <b>Your Info</b>\n"
        f"  ├ 📛 Name: <b>{user.first_name}</b>\n"
        f"  ├ 🏷 Username: <code>{username_str}</code>\n"
        f"  └ 🆔 User ID: <code>{user.id}</code>\n\n"
        f"🛠 <b>Bot Info</b>\n"
        f"  ├ 👨‍💻 Developer: {DEVELOPER_USERNAME}\n"
        f"  ├ 📦 Version: <b>{BOT_VERSION}</b>\n"
        f"  ├ 🐍 Python: <b>{stats['python_version']}</b>\n"
        f"  ├ 🗄 Database: ✅  ({db_size_kb:.1f} KB)\n"
        f"  ├ ⏱ Uptime: <b>{uptime}</b>\n"
        f"  ├ 👥 Total Users: <b>{total_users}</b>\n"
        f"  ├ 🖥 CPU: <b>{stats['cpu_percent']:.1f}%</b>\n"
        f"  └ 💾 RAM: <b>{stats['process_rss_mb']} MB</b>\n\n"
        f"⚡ Fast  ✅ Stable  🟢 24/7 Active\n\n"
        f"<i>Use the buttons below to get started!</i>"
    )
    return text


# ─── /start command ───────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    - Register/update user in database.
    - Check force-join requirements.
    - Check maintenance mode.
    - Send banner + welcome message.
    """
    user = update.effective_user
    if not user:
        return

    # Register user
    await db.upsert_user(user.id, user.username, user.first_name, user.last_name)

    # Maintenance guard (non-owners see maintenance message)
    if await _is_maintenance(context, user.id):
        await update.message.reply_text(MAINTENANCE_MESSAGE)
        return

    # Force-join check
    fj_enabled = await db.get_setting("force_join")
    if fj_enabled == "1" and user.id != OWNER_ID:
        channels = await db.get_force_join_channels()
        if channels:
            not_joined = []
            for ch in channels:
                try:
                    member = await context.bot.get_chat_member(ch["channel_id"], user.id)
                    if member.status in ("left", "kicked"):
                        not_joined.append(ch)
                except Exception:
                    not_joined.append(ch)

            if not_joined:
                from keyboards import force_join_keyboard

                await update.message.reply_text(
                    "⚠️ <b>You must join the following channels to use this bot:</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=force_join_keyboard(not_joined),
                )
                return

    # Build welcome message
    welcome_text = await _build_welcome(update, context)
    bot_username = (await context.bot.get_me()).username
    keyboard = main_menu_keyboard(bot_username)

    # Send banner image if available
    if BANNER_PATH.exists():
        try:
            with BANNER_PATH.open("rb") as f:
                await update.message.reply_photo(
                    photo=InputFile(f),
                    caption=welcome_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
            return
        except Exception as exc:
            logger.warning("Could not send banner image: %s", exc)

    # Fallback: text-only message
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


# ─── Callback: how_to_use ─────────────────────────────────────────────────────

async def how_to_use_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the 'How To Use' help text."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        HOW_TO_USE_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_main_keyboard(),
    )


# ─── Callback: main_menu ─────────────────────────────────────────────────────

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to main menu (re-draws the welcome message inline)."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    welcome_text = await _build_welcome(update, context)
    bot_username = (await context.bot.get_me()).username
    keyboard = main_menu_keyboard(bot_username)

    try:
        await query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
    except Exception:
        # If the message has a photo, we cannot edit its text
        await query.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


# ─── Callback: close_menu ────────────────────────────────────────────────────

async def close_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the menu message."""
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        await query.edit_message_reply_markup(reply_markup=None)


# ─── Force-join verify callback ──────────────────────────────────────────────

async def fj_verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Re-check force-join membership when the user taps 'Verify'.
    If they've joined everything, send the normal welcome.
    """
    query = update.callback_query
    await query.answer("Checking your membership…", show_alert=False)

    user = update.effective_user
    channels = await db.get_force_join_channels()
    not_joined = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch["channel_id"], user.id)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)

    if not_joined:
        from keyboards import force_join_keyboard

        await query.answer("❌ You haven't joined all channels yet!", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=force_join_keyboard(not_joined))
        return

    # All joined — show main menu
    welcome_text = await _build_welcome(update, context)
    bot_username = (await context.bot.get_me()).username
    keyboard = main_menu_keyboard(bot_username)
    try:
        await query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
    except Exception:
        await query.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


# ─── Handler registration ─────────────────────────────────────────────────────

def register(application) -> None:
    """Register all handlers from this module onto the Application."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(how_to_use_callback, pattern="^how_to_use$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(close_menu_callback, pattern="^close_menu$"))
    application.add_handler(CallbackQueryHandler(fj_verify_callback, pattern="^fj_verify$"))
