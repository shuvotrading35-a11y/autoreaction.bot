"""
AutoReactionBot - Force Join Handler
Admin commands to add/remove/list force-join channels.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

import database as db
from config import OWNER_ID

logger = logging.getLogger(__name__)


def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def _owner_check(update: Update) -> bool:
    user = update.effective_user
    if not user or not _is_owner(user.id):
        await update.message.reply_text("⛔ Owner only.")
        return False
    return True


# ─── /addfj ──────────────────────────────────────────────────────────────────

async def add_force_join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addfj <channel_id_or_username> [invite_link]
    Add a channel to the force-join list.
    Channel must be a numeric ID (preferred) or @username.
    """
    if not await _owner_check(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/addfj &lt;channel_id&gt; [invite_link]</code>\n\n"
            "Example: <code>/addfj -1001234567890 https://t.me/+abc</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    raw = context.args[0]
    invite_link = context.args[1] if len(context.args) > 1 else None
    username: str | None = None
    channel_id: int

    # Try to resolve numeric ID first
    if raw.lstrip("-").isdigit():
        channel_id = int(raw)
        # Attempt to fetch channel info from Telegram
        try:
            chat = await context.bot.get_chat(channel_id)
            username = chat.username
            invite_link = invite_link or await _get_invite_link(context, chat)
        except Exception as exc:
            logger.warning("Could not fetch chat %s: %s", raw, exc)
    else:
        # Treat as username
        username_clean = raw.lstrip("@")
        try:
            chat = await context.bot.get_chat(f"@{username_clean}")
            channel_id = chat.id
            username = chat.username
            invite_link = invite_link or await _get_invite_link(context, chat)
        except Exception as exc:
            await update.message.reply_text(
                f"❌ Could not resolve channel <code>{raw}</code>: {exc}",
                parse_mode=ParseMode.HTML,
            )
            return

    added = await db.add_force_join_channel(channel_id, username, invite_link)
    if added:
        await update.message.reply_text(
            f"✅ Channel <code>{channel_id}</code> added to force-join list.",
            parse_mode=ParseMode.HTML,
        )
        logger.info("Force-join channel %d added.", channel_id)
    else:
        await update.message.reply_text(
            f"⚠️ Channel <code>{channel_id}</code> is already in the force-join list.",
            parse_mode=ParseMode.HTML,
        )


async def _get_invite_link(context, chat) -> str | None:
    """Try to get or create an invite link for the channel."""
    try:
        link = await context.bot.export_chat_invite_link(chat.id)
        return link
    except Exception:
        if chat.username:
            return f"https://t.me/{chat.username}"
        return None


# ─── /removefj ───────────────────────────────────────────────────────────────

async def remove_force_join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /removefj <channel_id>
    Remove a channel from the force-join list.
    """
    if not await _owner_check(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/removefj &lt;channel_id&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    raw = context.args[0].lstrip("-")
    if not raw.isdigit():
        await update.message.reply_text("❌ Please provide a numeric channel ID.")
        return

    channel_id = int(context.args[0])
    removed = await db.remove_force_join_channel(channel_id)
    if removed:
        await update.message.reply_text(
            f"✅ Channel <code>{channel_id}</code> removed from force-join list.",
            parse_mode=ParseMode.HTML,
        )
        logger.info("Force-join channel %d removed.", channel_id)
    else:
        await update.message.reply_text(
            f"⚠️ Channel <code>{channel_id}</code> was not in the force-join list.",
            parse_mode=ParseMode.HTML,
        )


# ─── /listfj ─────────────────────────────────────────────────────────────────

async def list_force_join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/listfj — List all force-join channels."""
    if not await _owner_check(update):
        return
    channels = await db.get_force_join_channels()
    if not channels:
        await update.message.reply_text("🔗 No force-join channels configured.")
        return

    lines = ["🔗 <b>Force-Join Channels</b>\n"]
    for i, ch in enumerate(channels, 1):
        username = f"@{ch['channel_username']}" if ch.get("channel_username") else "Private"
        link = ch.get("invite_link") or "N/A"
        lines.append(
            f"{i}. <code>{ch['channel_id']}</code>  {username}\n"
            f"   🔗 {link}"
        )
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


# ─── Handler registration ─────────────────────────────────────────────────────

def register(application) -> None:
    """Register force-join management handlers."""
    application.add_handler(CommandHandler("addfj", add_force_join_command))
    application.add_handler(CommandHandler("removefj", remove_force_join_command))
    application.add_handler(CommandHandler("listfj", list_force_join_command))
