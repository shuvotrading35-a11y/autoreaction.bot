"""
AutoReactionBot - Statistics Handler
Shows daily, weekly, and monthly bot statistics.
"""

import logging
from datetime import date

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
from config import OWNER_ID
from keyboards import admin_back_keyboard, statistics_keyboard

logger = logging.getLogger(__name__)


def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def _owner_check(update: Update) -> bool:
    user = update.effective_user
    if not user or not _is_owner(user.id):
        if update.callback_query:
            await update.callback_query.answer("⛔ Owner only!", show_alert=True)
        elif update.message:
            await update.message.reply_text("⛔ Owner only.")
        return False
    return True


# ─── /stats command ───────────────────────────────────────────────────────────

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stats — Show the statistics menu (owner only)."""
    if not await _owner_check(update):
        return
    await update.message.reply_text(
        "📈 <b>Statistics</b>\n\nChoose a time range:",
        parse_mode=ParseMode.HTML,
        reply_markup=statistics_keyboard(),
    )


# ─── Callback: statistics ─────────────────────────────────────────────────────

async def statistics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the statistics time-range selector from admin panel."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            "📈 <b>Statistics</b>\n\nChoose a time range:",
            parse_mode=ParseMode.HTML,
            reply_markup=statistics_keyboard(),
        )
    except Exception:
        pass


# ─── Today statistics ─────────────────────────────────────────────────────────

async def stats_today_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show today's statistics."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()

    today = date.today().isoformat()
    total_reactions = await db.get_today_reactions()
    total_users = await db.get_today_users()
    top_emojis = await db.get_most_used_emojis(5)
    top_chats = await db.get_top_active_chats(5)

    emoji_lines = "\n".join(
        f"  {i}. {e['emoji']}  ×{e['usage_count']}"
        for i, e in enumerate(top_emojis, 1)
    ) or "  (none yet)"

    chat_lines = "\n".join(
        f"  {i}. <code>{c['chat_id']}</code>  ×{c['reaction_count']}"
        for i, c in enumerate(top_chats, 1)
    ) or "  (none yet)"

    text = (
        f"📅 <b>Today's Statistics</b>  [{today}]\n"
        f"{'─' * 30}\n\n"
        f"⚡ Reactions Sent: <b>{total_reactions}</b>\n"
        f"👤 New Users: <b>{total_users}</b>\n\n"
        f"🏆 <b>Top Emojis</b>\n{emoji_lines}\n\n"
        f"🔥 <b>Most Active Chats</b>\n{chat_lines}"
    )

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=statistics_keyboard(),
    )


# ─── Weekly statistics ────────────────────────────────────────────────────────

async def stats_weekly_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show weekly statistics (last 7 days)."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()

    rows = await db.get_weekly_stats()
    if not rows:
        await query.edit_message_text(
            "📆 <b>Weekly Statistics</b>\n\nNo data yet.",
            parse_mode=ParseMode.HTML,
            reply_markup=statistics_keyboard(),
        )
        return

    total_r = sum(r["reactions_sent"] for r in rows)
    total_u = sum(r["new_users"] for r in rows)
    total_g = sum(r["new_groups"] for r in rows)
    total_c = sum(r["new_channels"] for r in rows)

    day_lines = []
    for row in rows:
        day_lines.append(
            f"  📅 {row['stat_date']}: "
            f"⚡{row['reactions_sent']}  👤{row['new_users']}"
        )

    text = (
        "📆 <b>Weekly Statistics (Last 7 Days)</b>\n"
        f"{'─' * 30}\n\n"
        f"⚡ Total Reactions: <b>{total_r}</b>\n"
        f"👤 New Users: <b>{total_u}</b>\n"
        f"🏘 New Groups: <b>{total_g}</b>\n"
        f"📡 New Channels: <b>{total_c}</b>\n\n"
        "<b>Daily Breakdown:</b>\n" + "\n".join(day_lines)
    )

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=statistics_keyboard(),
    )


# ─── Monthly statistics ───────────────────────────────────────────────────────

async def stats_monthly_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show monthly statistics (last 30 days)."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()

    rows = await db.get_monthly_stats()
    if not rows:
        await query.edit_message_text(
            "🗓 <b>Monthly Statistics</b>\n\nNo data yet.",
            parse_mode=ParseMode.HTML,
            reply_markup=statistics_keyboard(),
        )
        return

    total_r = sum(r["reactions_sent"] for r in rows)
    total_u = sum(r["new_users"] for r in rows)
    total_g = sum(r["new_groups"] for r in rows)
    total_c = sum(r["new_channels"] for r in rows)

    # Show only last 10 days for space; total covers all 30
    day_lines = []
    for row in rows[:10]:
        day_lines.append(
            f"  📅 {row['stat_date']}: "
            f"⚡{row['reactions_sent']}  👤{row['new_users']}"
        )
    if len(rows) > 10:
        day_lines.append(f"  … ({len(rows) - 10} more days in total)")

    text = (
        "🗓 <b>Monthly Statistics (Last 30 Days)</b>\n"
        f"{'─' * 30}\n\n"
        f"⚡ Total Reactions: <b>{total_r}</b>\n"
        f"👤 New Users: <b>{total_u}</b>\n"
        f"🏘 New Groups: <b>{total_g}</b>\n"
        f"📡 New Channels: <b>{total_c}</b>\n\n"
        "<b>Recent Days:</b>\n" + "\n".join(day_lines)
    )

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=statistics_keyboard(),
    )


# ─── Handler registration ─────────────────────────────────────────────────────

def register(application) -> None:
    """Register statistics handlers."""
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(statistics_callback, pattern="^statistics$"))
    application.add_handler(CallbackQueryHandler(stats_today_callback, pattern="^stats_today$"))
    application.add_handler(CallbackQueryHandler(stats_weekly_callback, pattern="^stats_weekly$"))
    application.add_handler(CallbackQueryHandler(stats_monthly_callback, pattern="^stats_monthly$"))
