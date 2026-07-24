"""
AutoReactionBot - Settings Handler
Toggle all bot settings via inline buttons and /setdelay command.
Owner-only access.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
from config import OWNER_ID
from keyboards import settings_keyboard

logger = logging.getLogger(__name__)


def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def _owner_check(update: Update) -> bool:
    """Guard for owner-only actions."""
    user = update.effective_user
    if not user or not _is_owner(user.id):
        if update.callback_query:
            await update.callback_query.answer("⛔ Owner only!", show_alert=True)
        elif update.message:
            await update.message.reply_text("⛔ Owner only.")
        return False
    return True


# ─── /settings command ────────────────────────────────────────────────────────

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/settings — Open the settings panel (owner only)."""
    if not await _owner_check(update):
        return
    settings = await db.get_all_settings()
    await update.message.reply_text(
        "⚙️ <b>Bot Settings</b>\n\nTap a button to toggle a setting:",
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard(settings),
    )


# ─── Shared: re-render settings message ──────────────────────────────────────

async def _refresh_settings(update: Update, changed: str) -> None:
    """
    After toggling a setting, re-render the settings keyboard with updated state.
    Also sends a brief toast notification via query.answer().
    """
    query = update.callback_query
    settings = await db.get_all_settings()
    new_val = settings.get(changed, "0")
    state_str = "✅ Enabled" if new_val == "1" else "❌ Disabled"

    label_map = {
        "auto_reaction": "Auto Reaction",
        "random_emoji": "Random Emoji",
        "big_reaction": "Big Reaction",
        "maintenance": "Maintenance Mode",
        "force_join": "Force Join",
        "logging_enabled": "Logging",
    }
    label = label_map.get(changed, changed)
    await query.answer(f"{label}: {state_str}", show_alert=False)

    try:
        await query.edit_message_reply_markup(reply_markup=settings_keyboard(settings))
    except Exception:
        pass


# ─── Toggle: auto_reaction ────────────────────────────────────────────────────

async def toggle_auto_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle the auto-reaction feature on/off."""
    if not await _owner_check(update):
        return
    current = await db.get_setting("auto_reaction")
    new_val = "0" if current == "1" else "1"
    await db.set_setting("auto_reaction", new_val)
    logger.info("auto_reaction toggled to %s by owner.", new_val)
    await _refresh_settings(update, "auto_reaction")


# ─── Toggle: random_emoji ────────────────────────────────────────────────────

async def toggle_random_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle random emoji selection mode."""
    if not await _owner_check(update):
        return
    current = await db.get_setting("random_emoji")
    new_val = "0" if current == "1" else "1"
    await db.set_setting("random_emoji", new_val)
    logger.info("random_emoji toggled to %s by owner.", new_val)
    await _refresh_settings(update, "random_emoji")


# ─── Toggle: big_reaction ────────────────────────────────────────────────────

async def toggle_big_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle big/animated reactions."""
    if not await _owner_check(update):
        return
    current = await db.get_setting("big_reaction")
    new_val = "0" if current == "1" else "1"
    await db.set_setting("big_reaction", new_val)
    logger.info("big_reaction toggled to %s by owner.", new_val)
    await _refresh_settings(update, "big_reaction")


# ─── Toggle: maintenance ────────────────────────────────────────────────────

async def toggle_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle maintenance mode."""
    if not await _owner_check(update):
        return
    current = await db.get_setting("maintenance")
    new_val = "0" if current == "1" else "1"
    await db.set_setting("maintenance", new_val)
    logger.info("maintenance toggled to %s by owner.", new_val)
    await _refresh_settings(update, "maintenance")


# ─── Toggle: force_join ─────────────────────────────────────────────────────

async def toggle_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle force-join requirement."""
    if not await _owner_check(update):
        return
    current = await db.get_setting("force_join")
    new_val = "0" if current == "1" else "1"
    await db.set_setting("force_join", new_val)
    logger.info("force_join toggled to %s by owner.", new_val)
    await _refresh_settings(update, "force_join")


# ─── Toggle: logging_enabled ────────────────────────────────────────────────

async def toggle_logging(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle reaction/event logging to file."""
    if not await _owner_check(update):
        return
    current = await db.get_setting("logging_enabled")
    new_val = "0" if current == "1" else "1"
    await db.set_setting("logging_enabled", new_val)
    logger.info("logging_enabled toggled to %s by owner.", new_val)
    await _refresh_settings(update, "logging_enabled")


# ─── /setdelay command ────────────────────────────────────────────────────────

async def set_delay_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /setdelay <seconds>
    Set the delay between consecutive reactions (0.0 – 30.0 seconds).
    """
    if not await _owner_check(update):
        return
    if not context.args:
        current = await db.get_setting("reaction_delay")
        await update.message.reply_text(
            f"⏱ Current reaction delay: <b>{current}s</b>\n\n"
            "Usage: <code>/setdelay &lt;seconds&gt;</code>  (e.g. <code>/setdelay 1.5</code>)",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        delay = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Provide a valid number, e.g. <code>/setdelay 1.5</code>", parse_mode=ParseMode.HTML)
        return

    if delay < 0 or delay > 30:
        await update.message.reply_text("❌ Delay must be between 0 and 30 seconds.")
        return

    await db.set_setting("reaction_delay", str(delay))
    logger.info("reaction_delay set to %s by owner.", delay)
    await update.message.reply_text(
        f"✅ Reaction delay set to <b>{delay}s</b>.",
        parse_mode=ParseMode.HTML,
    )


# ─── Admin settings callback (opens panel) ───────────────────────────────────

async def admin_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the settings panel inline from admin panel."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()
    settings = await db.get_all_settings()
    try:
        await query.edit_message_text(
            "⚙️ <b>Bot Settings</b>\n\nTap a button to toggle a setting:",
            parse_mode=ParseMode.HTML,
            reply_markup=settings_keyboard(settings),
        )
    except Exception:
        pass


# ─── Maintenance toggle from admin panel ─────────────────────────────────────

async def maintenance_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick maintenance toggle directly from the admin panel button."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    current = await db.get_setting("maintenance")
    new_val = "0" if current == "1" else "1"
    await db.set_setting("maintenance", new_val)
    state = "🔧 ENABLED" if new_val == "1" else "✅ DISABLED"
    await query.answer(f"Maintenance mode: {state}", show_alert=True)
    logger.info("Maintenance toggled to %s from admin panel.", new_val)
    # Refresh admin panel
    from keyboards import admin_panel_keyboard
    try:
        await query.edit_message_reply_markup(reply_markup=admin_panel_keyboard())
    except Exception:
        pass


# ─── Noop callbacks ───────────────────────────────────────────────────────────

async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle no-op callbacks (page count displays etc.)."""
    await update.callback_query.answer()


# ─── Handler registration ─────────────────────────────────────────────────────

def register(application) -> None:
    """Register all settings handlers."""
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("setdelay", set_delay_command))

    application.add_handler(
        CallbackQueryHandler(admin_settings_callback, pattern="^admin_settings$")
    )
    application.add_handler(
        CallbackQueryHandler(toggle_auto_reaction, pattern="^toggle_auto_reaction$")
    )
    application.add_handler(
        CallbackQueryHandler(toggle_random_emoji, pattern="^toggle_random_emoji$")
    )
    application.add_handler(
        CallbackQueryHandler(toggle_big_reaction, pattern="^toggle_big_reaction$")
    )
    application.add_handler(
        CallbackQueryHandler(toggle_maintenance, pattern="^toggle_maintenance$")
    )
    application.add_handler(
        CallbackQueryHandler(maintenance_toggle_callback, pattern="^maintenance_toggle$")
    )
    application.add_handler(
        CallbackQueryHandler(toggle_force_join, pattern="^toggle_force_join$")
    )
    application.add_handler(
        CallbackQueryHandler(toggle_logging, pattern="^toggle_logging$")
    )
    application.add_handler(
        CallbackQueryHandler(noop_callback, pattern="^noop_")
    )
