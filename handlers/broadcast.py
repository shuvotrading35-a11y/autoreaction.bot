"""
AutoReactionBot - Broadcast Handler
Send messages (text, photo, video, document) to all users, groups, or channels.
Shows live progress bar, success/fail counts, and logs results.
"""

import asyncio
import logging
from typing import Optional

from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db
from config import BROADCAST_BATCH_SIZE, BROADCAST_DELAY, OWNER_ID
from keyboards import admin_back_keyboard, broadcast_menu_keyboard
from utils import make_progress_bar

logger = logging.getLogger(__name__)

# ─── Conversation states ──────────────────────────────────────────────────────

WAITING_BROADCAST_MSG = 1


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


# ─── Broadcast menu ───────────────────────────────────────────────────────────

async def broadcast_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show broadcast target selection menu."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            "📢 <b>Broadcast</b>\n\nChoose broadcast target:",
            parse_mode=ParseMode.HTML,
            reply_markup=broadcast_menu_keyboard(),
        )
    except Exception:
        pass


# ─── /broadcast command ───────────────────────────────────────────────────────

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/broadcast — Open the broadcast menu (owner only)."""
    if not await _owner_check(update):
        return
    await update.message.reply_text(
        "📢 <b>Broadcast</b>\n\nChoose broadcast target:",
        parse_mode=ParseMode.HTML,
        reply_markup=broadcast_menu_keyboard(),
    )


# ─── Start broadcast conversation ─────────────────────────────────────────────

async def _start_broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    target: str,
) -> int:
    """
    Ask the admin to send the message they want to broadcast.
    Stores the target in context.user_data.
    """
    query = update.callback_query
    await query.answer()
    context.user_data["broadcast_target"] = target
    await query.edit_message_text(
        f"📢 <b>Broadcast to: {target.capitalize()}</b>\n\n"
        "Please send the message you want to broadcast.\n"
        "Supported: Text, Photo, Video, Document (with optional caption).\n\n"
        "/cancel to abort.",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_BROADCAST_MSG


async def broadcast_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Broadcast to users — ask for message."""
    if not await _owner_check(update):
        return ConversationHandler.END
    return await _start_broadcast(update, context, "users")


async def broadcast_groups_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _owner_check(update):
        return ConversationHandler.END
    return await _start_broadcast(update, context, "groups")


async def broadcast_channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _owner_check(update):
        return ConversationHandler.END
    return await _start_broadcast(update, context, "channels")


async def broadcast_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _owner_check(update):
        return ConversationHandler.END
    return await _start_broadcast(update, context, "all")


# ─── Receive broadcast message & execute ─────────────────────────────────────

async def _collect_recipients(target: str) -> list[int]:
    """
    Return a list of chat/user IDs for the given broadcast target.
    """
    if target == "users":
        users = await db.get_all_users()
        return [u["user_id"] for u in users]
    if target == "groups":
        groups = await db.get_all_groups()
        return [g["chat_id"] for g in groups]
    if target == "channels":
        channels = await db.get_all_channels()
        return [c["chat_id"] for c in channels]
    if target == "all":
        users = await db.get_all_users()
        groups = await db.get_all_groups()
        channels = await db.get_all_channels()
        ids: list[int] = [u["user_id"] for u in users]
        ids += [g["chat_id"] for g in groups]
        ids += [c["chat_id"] for c in channels]
        return list(set(ids))
    return []


async def _forward_message(
    bot, chat_id: int, original: Message
) -> bool:
    """
    Copy (forward without forward tag) the original message to a target chat.
    Returns True on success, False on failure.
    """
    try:
        if original.photo:
            await bot.send_photo(
                chat_id=chat_id,
                photo=original.photo[-1].file_id,
                caption=original.caption or "",
                parse_mode=ParseMode.HTML,
            )
        elif original.video:
            await bot.send_video(
                chat_id=chat_id,
                video=original.video.file_id,
                caption=original.caption or "",
                parse_mode=ParseMode.HTML,
            )
        elif original.document:
            await bot.send_document(
                chat_id=chat_id,
                document=original.document.file_id,
                caption=original.caption or "",
                parse_mode=ParseMode.HTML,
            )
        elif original.text:
            await bot.send_message(
                chat_id=chat_id,
                text=original.text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        else:
            # Fallback: forward the raw message
            await original.forward(chat_id=chat_id)
        return True
    except TelegramError as exc:
        logger.debug("Broadcast failed for %d: %s", chat_id, exc)
        return False


async def receive_broadcast_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Receives the broadcast message and executes the broadcast.
    Shows a live progress bar updated every 10 recipients.
    """
    if not await _owner_check(update):
        return ConversationHandler.END

    original_message: Message = update.message
    target: str = context.user_data.get("broadcast_target", "users")
    recipients = await _collect_recipients(target)
    total = len(recipients)

    if total == 0:
        await update.message.reply_text(
            f"⚠️ No {target} found to broadcast to."
        )
        return ConversationHandler.END

    # Create DB log entry
    log_id = await db.create_broadcast_log(target, total)

    # Send initial progress message
    progress_msg = await update.message.reply_text(
        f"📢 <b>Broadcasting to {total} {target}…</b>\n\n"
        f"{make_progress_bar(0, total)}\n\n"
        f"✅ Success: 0  |  ❌ Failed: 0",
        parse_mode=ParseMode.HTML,
    )

    success = 0
    failed = 0
    UPDATE_EVERY = 10  # update progress bar every N sends

    for idx, chat_id in enumerate(recipients, 1):
        ok = await _forward_message(context.bot, chat_id, original_message)
        if ok:
            success += 1
        else:
            failed += 1

        # Update progress bar periodically
        if idx % UPDATE_EVERY == 0 or idx == total:
            bar = make_progress_bar(idx, total)
            try:
                await progress_msg.edit_text(
                    f"📢 <b>Broadcasting to {total} {target}…</b>\n\n"
                    f"{bar}\n\n"
                    f"✅ Success: {success}  |  ❌ Failed: {failed}",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass  # Ignore edit errors (same message content)

        await asyncio.sleep(BROADCAST_DELAY)

    # Finalise
    await db.update_broadcast_log(log_id, success, failed)

    await progress_msg.edit_text(
        f"✅ <b>Broadcast Complete!</b>\n\n"
        f"📊 Target: <b>{target.capitalize()}</b>\n"
        f"📦 Total: <b>{total}</b>\n"
        f"✅ Success: <b>{success}</b>\n"
        f"❌ Failed: <b>{failed}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_back_keyboard(),
    )

    logger.info(
        "Broadcast to %s complete: %d/%d success.", target, success, total
    )
    return ConversationHandler.END


# ─── Cancel broadcast ─────────────────────────────────────────────────────────

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel an in-progress broadcast conversation."""
    await update.message.reply_text(
        "❌ Broadcast cancelled.", reply_markup=admin_back_keyboard()
    )
    context.user_data.pop("broadcast_target", None)
    return ConversationHandler.END


# ─── Handler registration ─────────────────────────────────────────────────────

def register(application) -> None:
    """Register broadcast handlers, including the conversation handler."""

    # ── ConversationHandler for the broadcast flow ─────────────────────
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(broadcast_users_callback, pattern="^broadcast_users$"),
            CallbackQueryHandler(broadcast_groups_callback, pattern="^broadcast_groups$"),
            CallbackQueryHandler(broadcast_channels_callback, pattern="^broadcast_channels$"),
            CallbackQueryHandler(broadcast_all_callback, pattern="^broadcast_all$"),
        ],
        states={
            WAITING_BROADCAST_MSG: [
                MessageHandler(
                    filters.ALL & ~filters.COMMAND,
                    receive_broadcast_message,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_broadcast)],
        per_message=False,
    )

    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(
        CallbackQueryHandler(broadcast_menu_callback, pattern="^broadcast_menu$")
    )
    application.add_handler(conv_handler)
