"""
AutoReactionBot - Emoji Manager Handler
Admin UI for managing the emoji pool:
add, remove, toggle, list, set weight, paginate.
Uses ConversationHandler for multi-step input flows.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db
from config import EMOJI_CATEGORIES, OWNER_ID
from keyboards import (
    admin_back_keyboard,
    emoji_list_keyboard,
    emoji_manager_keyboard,
)
from utils import is_valid_emoji

logger = logging.getLogger(__name__)

# ─── Conversation states ──────────────────────────────────────────────────────

WAITING_EMOJI_ADD = 10
WAITING_EMOJI_REMOVE_ID = 11
WAITING_EMOJI_TOGGLE_ID = 12
WAITING_EMOJI_WEIGHT_ID = 13
WAITING_EMOJI_WEIGHT_VALUE = 14


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


# ─── Open emoji manager ───────────────────────────────────────────────────────

async def emoji_manager_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the emoji manager sub-menu."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()
    emojis = await db.get_all_emojis()
    count = len(emojis)
    enabled = sum(1 for e in emojis if e.get("is_enabled"))
    try:
        await query.edit_message_text(
            f"😀 <b>Emoji Manager</b>\n\n"
            f"Total: <b>{count}</b>  |  Enabled: <b>{enabled}</b>\n\n"
            "Choose an action:",
            parse_mode=ParseMode.HTML,
            reply_markup=emoji_manager_keyboard(),
        )
    except Exception:
        pass


# ─── List emojis ──────────────────────────────────────────────────────────────

async def emoji_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show paginated emoji list."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()
    emojis = await db.get_all_emojis()
    if not emojis:
        await query.edit_message_text(
            "📋 <b>Emoji List</b>\n\nNo emojis found.",
            parse_mode=ParseMode.HTML,
            reply_markup=emoji_manager_keyboard(),
        )
        return
    context.user_data["emoji_list_cache"] = emojis
    await query.edit_message_text(
        "📋 <b>All Emojis</b>  (tap for details)\n",
        parse_mode=ParseMode.HTML,
        reply_markup=emoji_list_keyboard(emojis, page=0),
    )


async def emoji_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle emoji list pagination."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[-1])
    emojis = context.user_data.get("emoji_list_cache") or await db.get_all_emojis()
    context.user_data["emoji_list_cache"] = emojis
    try:
        await query.edit_message_reply_markup(
            reply_markup=emoji_list_keyboard(emojis, page=page)
        )
    except Exception:
        pass


async def emoji_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detail of a single emoji."""
    if not await _owner_check(update):
        return
    query = update.callback_query
    await query.answer()
    emoji_id = int(query.data.split("_")[-1])
    emojis = await db.get_all_emojis()
    emoji = next((e for e in emojis if e["id"] == emoji_id), None)
    if not emoji:
        await query.answer("Emoji not found.", show_alert=True)
        return
    state = "✅ Enabled" if emoji.get("is_enabled") else "❌ Disabled"
    text = (
        f"😀 <b>Emoji Detail</b>\n\n"
        f"Emoji: {emoji['emoji']}\n"
        f"ID: <code>{emoji['id']}</code>\n"
        f"Category: <b>{emoji.get('category', 'other')}</b>\n"
        f"Weight: <b>{emoji.get('weight', 1)}</b>\n"
        f"Big: {'✅' if emoji.get('is_big') else '❌'}\n"
        f"Status: {state}\n"
        f"Added: {emoji.get('added_at', 'N/A')}"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=emoji_manager_keyboard(),
    )


# ─── Add emoji flow ───────────────────────────────────────────────────────────

async def emoji_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the add-emoji conversation."""
    if not await _owner_check(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ <b>Add Emoji</b>\n\n"
        "Send the emoji you want to add.\n"
        "Format: <code>emoji [category] [weight]</code>\n\n"
        "Examples:\n"
        "  <code>🎯</code>\n"
        "  <code>🎯 fun 5</code>\n\n"
        f"Categories: {', '.join(EMOJI_CATEGORIES)}\n\n"
        "/cancel to abort.",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_EMOJI_ADD


async def receive_emoji_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process an emoji add input."""
    if not update.message or not update.message.text:
        return WAITING_EMOJI_ADD

    parts = update.message.text.strip().split()
    if not parts:
        await update.message.reply_text("❌ Please send a valid emoji.")
        return WAITING_EMOJI_ADD

    emoji_char = parts[0]
    if not is_valid_emoji(emoji_char):
        await update.message.reply_text("❌ That doesn't look like a valid emoji. Try again.")
        return WAITING_EMOJI_ADD

    category = parts[1].lower() if len(parts) > 1 else "other"
    if category not in EMOJI_CATEGORIES:
        category = "other"

    try:
        weight = int(parts[2]) if len(parts) > 2 else 1
        weight = max(1, min(100, weight))
    except ValueError:
        weight = 1

    added = await db.add_emoji(emoji_char, category, weight)
    if added:
        await update.message.reply_text(
            f"✅ Emoji {emoji_char} added!\n"
            f"Category: {category}  |  Weight: {weight}",
            reply_markup=emoji_manager_keyboard(),
        )
        logger.info("Emoji '%s' added by owner.", emoji_char)
    else:
        await update.message.reply_text(
            f"⚠️ Emoji {emoji_char} already exists in the database.",
            reply_markup=emoji_manager_keyboard(),
        )
    return ConversationHandler.END


# ─── Remove emoji flow ────────────────────────────────────────────────────────

async def emoji_remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start remove-emoji conversation."""
    if not await _owner_check(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🗑 <b>Remove Emoji</b>\n\n"
        "Send the emoji <b>ID</b> you want to remove.\n"
        "Use 📋 List Emojis to find IDs.\n\n"
        "/cancel to abort.",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_EMOJI_REMOVE_ID


async def receive_emoji_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process emoji removal by ID."""
    if not update.message or not update.message.text:
        return WAITING_EMOJI_REMOVE_ID

    raw = update.message.text.strip()
    if not raw.isdigit():
        await update.message.reply_text("❌ Please send a numeric emoji ID.")
        return WAITING_EMOJI_REMOVE_ID

    emoji_id = int(raw)
    removed = await db.remove_emoji(emoji_id)
    if removed:
        await update.message.reply_text(
            f"✅ Emoji with ID <code>{emoji_id}</code> has been removed.",
            parse_mode=ParseMode.HTML,
            reply_markup=emoji_manager_keyboard(),
        )
        logger.info("Emoji #%d removed by owner.", emoji_id)
    else:
        await update.message.reply_text(
            f"❌ No emoji found with ID <code>{emoji_id}</code>.",
            parse_mode=ParseMode.HTML,
        )
    return ConversationHandler.END


# ─── Toggle emoji flow ────────────────────────────────────────────────────────

async def emoji_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start toggle-emoji conversation."""
    if not await _owner_check(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔀 <b>Toggle Emoji</b>\n\n"
        "Send the emoji <b>ID</b> to enable/disable.\n\n"
        "/cancel to abort.",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_EMOJI_TOGGLE_ID


async def receive_emoji_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle an emoji on/off by ID."""
    if not update.message or not update.message.text:
        return WAITING_EMOJI_TOGGLE_ID

    raw = update.message.text.strip()
    if not raw.isdigit():
        await update.message.reply_text("❌ Please send a numeric emoji ID.")
        return WAITING_EMOJI_TOGGLE_ID

    emoji_id = int(raw)
    new_state = await db.toggle_emoji(emoji_id)
    if new_state is None:
        await update.message.reply_text(
            f"❌ No emoji found with ID <code>{emoji_id}</code>.",
            parse_mode=ParseMode.HTML,
        )
    else:
        state_str = "✅ Enabled" if new_state else "❌ Disabled"
        await update.message.reply_text(
            f"Emoji <code>#{emoji_id}</code> is now {state_str}.",
            parse_mode=ParseMode.HTML,
            reply_markup=emoji_manager_keyboard(),
        )
    return ConversationHandler.END


# ─── Set weight flow ──────────────────────────────────────────────────────────

async def emoji_weight_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start set-weight conversation."""
    if not await _owner_check(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚖️ <b>Set Emoji Weight</b>\n\n"
        "Send the emoji <b>ID</b> first:\n\n"
        "/cancel to abort.",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_EMOJI_WEIGHT_ID


async def receive_emoji_weight_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the emoji ID for weight update."""
    if not update.message or not update.message.text:
        return WAITING_EMOJI_WEIGHT_ID

    raw = update.message.text.strip()
    if not raw.isdigit():
        await update.message.reply_text("❌ Please send a numeric emoji ID.")
        return WAITING_EMOJI_WEIGHT_ID

    context.user_data["weight_emoji_id"] = int(raw)
    await update.message.reply_text(
        f"Now send the new <b>weight</b> (1-100) for emoji <code>#{raw}</code>:",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_EMOJI_WEIGHT_VALUE


async def receive_emoji_weight_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and apply the new weight."""
    if not update.message or not update.message.text:
        return WAITING_EMOJI_WEIGHT_VALUE

    raw = update.message.text.strip()
    if not raw.isdigit():
        await update.message.reply_text("❌ Please send a number between 1 and 100.")
        return WAITING_EMOJI_WEIGHT_VALUE

    weight = max(1, min(100, int(raw)))
    emoji_id = context.user_data.pop("weight_emoji_id", None)
    if emoji_id is None:
        await update.message.reply_text("❌ Session expired. Start again.")
        return ConversationHandler.END

    updated = await db.update_emoji_weight(emoji_id, weight)
    if updated:
        await update.message.reply_text(
            f"✅ Weight for emoji <code>#{emoji_id}</code> set to <b>{weight}</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=emoji_manager_keyboard(),
        )
    else:
        await update.message.reply_text(
            f"❌ No emoji found with ID <code>{emoji_id}</code>.",
            parse_mode=ParseMode.HTML,
        )
    return ConversationHandler.END


# ─── Cancel ───────────────────────────────────────────────────────────────────

async def cancel_emoji_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel any ongoing emoji conversation."""
    await update.message.reply_text(
        "❌ Operation cancelled.",
        reply_markup=emoji_manager_keyboard(),
    )
    context.user_data.pop("weight_emoji_id", None)
    return ConversationHandler.END


# ─── /addemoji command (shortcut) ────────────────────────────────────────────

async def add_emoji_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addemoji <emoji> [category] [weight]
    Quick command to add an emoji without the conversation flow.
    """
    if not await _owner_check(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/addemoji &lt;emoji&gt; [category] [weight]</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    emoji_char = context.args[0]
    category = context.args[1].lower() if len(context.args) > 1 else "other"
    if category not in EMOJI_CATEGORIES:
        category = "other"
    try:
        weight = int(context.args[2]) if len(context.args) > 2 else 1
    except ValueError:
        weight = 1

    added = await db.add_emoji(emoji_char, category, weight)
    if added:
        await update.message.reply_text(
            f"✅ Emoji {emoji_char} added! Category: {category}, Weight: {weight}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(f"⚠️ Emoji {emoji_char} already exists.")


# ─── /listemojis command ─────────────────────────────────────────────────────

async def list_emojis_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/listemojis — Show all emojis as plain text."""
    if not await _owner_check(update):
        return
    emojis = await db.get_all_emojis()
    if not emojis:
        await update.message.reply_text("No emojis in database.")
        return
    lines = ["😀 <b>All Emojis</b>\n"]
    for e in emojis:
        state = "✅" if e.get("is_enabled") else "❌"
        lines.append(
            f"{state} {e['emoji']}  ID:<code>{e['id']}</code>"
            f"  cat:{e.get('category','?')}  w:{e.get('weight',1)}"
        )
    # Split into chunks of 50 to avoid message length limit
    chunk: list[str] = []
    for line in lines:
        chunk.append(line)
        if len(chunk) >= 50:
            await update.message.reply_text(
                "\n".join(chunk), parse_mode=ParseMode.HTML
            )
            chunk = []
    if chunk:
        await update.message.reply_text("\n".join(chunk), parse_mode=ParseMode.HTML)


# ─── Handler registration ─────────────────────────────────────────────────────

def register(application) -> None:
    """Register emoji manager handlers."""

    # Add emoji conversation
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(emoji_add_callback, pattern="^emoji_add$")],
        states={WAITING_EMOJI_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_emoji_add)]},
        fallbacks=[CommandHandler("cancel", cancel_emoji_conversation)],
        per_message=False,
    )

    # Remove emoji conversation
    remove_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(emoji_remove_callback, pattern="^emoji_remove$")],
        states={WAITING_EMOJI_REMOVE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_emoji_remove)]},
        fallbacks=[CommandHandler("cancel", cancel_emoji_conversation)],
        per_message=False,
    )

    # Toggle emoji conversation
    toggle_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(emoji_toggle_callback, pattern="^emoji_toggle$")],
        states={WAITING_EMOJI_TOGGLE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_emoji_toggle)]},
        fallbacks=[CommandHandler("cancel", cancel_emoji_conversation)],
        per_message=False,
    )

    # Set weight conversation
    weight_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(emoji_weight_callback, pattern="^emoji_weight$")],
        states={
            WAITING_EMOJI_WEIGHT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_emoji_weight_id)],
            WAITING_EMOJI_WEIGHT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_emoji_weight_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel_emoji_conversation)],
        per_message=False,
    )

    application.add_handler(add_conv)
    application.add_handler(remove_conv)
    application.add_handler(toggle_conv)
    application.add_handler(weight_conv)

    application.add_handler(CallbackQueryHandler(emoji_manager_callback, pattern="^emoji_manager$"))
    application.add_handler(CallbackQueryHandler(emoji_list_callback, pattern="^emoji_list$"))
    application.add_handler(CallbackQueryHandler(emoji_page_callback, pattern="^emoji_page_\\d+$"))
    application.add_handler(CallbackQueryHandler(emoji_detail_callback, pattern="^emoji_detail_\\d+$"))

    application.add_handler(CommandHandler("addemoji", add_emoji_command))
    application.add_handler(CommandHandler("listemojis", list_emojis_command))
