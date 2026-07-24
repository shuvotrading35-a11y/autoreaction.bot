"""
AutoReactionBot - Reaction Handler
Core auto-reaction engine:
- Listens to every message in groups/channels where the bot is admin.
- Queues reactions with delay, rate limiting, and flood protection.
- Handles retries and graceful skipping.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from telegram import Message, ReactionTypeEmoji, Update
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TelegramError
from telegram.ext import ContextTypes, MessageHandler, filters

import database as db
from config import (
    REACTION_RETRY_COUNT,
    REACTION_RETRY_DELAY,
    SUPPORTED_MESSAGE_TYPES,
)
from utils import FloodProtector, RateLimiter, get_message_type, pick_emoji

logger = logging.getLogger(__name__)

# ─── Shared limiters (module-level singletons) ───────────────────────────────

_rate_limiter = RateLimiter()
_flood_protector = FloodProtector()

# ─── Reaction queue ───────────────────────────────────────────────────────────

@dataclass
class _ReactionJob:
    chat_id: int
    message_id: int
    emoji: str
    is_big: bool


_reaction_queue: asyncio.Queue[Optional[_ReactionJob]] = asyncio.Queue(maxsize=500)
_queue_worker_task: Optional[asyncio.Task] = None


async def _queue_worker(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Background worker that processes the reaction queue one job at a time.
    Respects reaction delay between sends.
    """
    logger.info("Reaction queue worker started.")
    while True:
        job = await _reaction_queue.get()

        # Sentinel value: shut down worker
        if job is None:
            logger.info("Reaction queue worker shutting down.")
            _reaction_queue.task_done()
            break

        await _send_reaction_with_retry(context, job)
        _reaction_queue.task_done()

        # Per-setting delay between reactions
        try:
            delay_str = await db.get_setting("reaction_delay")
            delay = float(delay_str) if delay_str else 0.5
        except Exception:
            delay = 0.5
        await asyncio.sleep(max(0.0, delay))


async def _send_reaction_with_retry(
    context: ContextTypes.DEFAULT_TYPE, job: _ReactionJob
) -> None:
    """
    Attempt to set a message reaction, retrying up to REACTION_RETRY_COUNT times.
    Handles RetryAfter (flood wait) by sleeping the required time.
    """
    for attempt in range(1, REACTION_RETRY_COUNT + 1):
        try:
            await context.bot.set_message_reaction(
                chat_id=job.chat_id,
                message_id=job.message_id,
                reaction=[ReactionTypeEmoji(emoji=job.emoji)],
                is_big=job.is_big,
            )
            # Log to DB
            await db.log_reaction(job.chat_id, job.message_id, job.emoji, job.is_big)
            logger.debug(
                "Reacted %s (big=%s) to msg %d in chat %d",
                job.emoji, job.is_big, job.message_id, job.chat_id,
            )
            return

        except RetryAfter as exc:
            wait = exc.retry_after + 1
            logger.warning(
                "Flood wait %ds for chat %d, sleeping…", wait, job.chat_id
            )
            await asyncio.sleep(wait)

        except TelegramError as exc:
            error_msg = str(exc).lower()
            # Non-retriable errors
            if any(
                phrase in error_msg
                for phrase in (
                    "chat not found",
                    "bot was kicked",
                    "bot is not a member",
                    "message to react not found",
                    "message not found",
                    "reactions are not supported",
                    "reaction_invalid",
                    "invalid reaction",
                    "reactioninvalid",
                )
            ):
                logger.warning(
                    "Skipping reaction for chat %d msg %d: %s",
                    job.chat_id, job.message_id, exc,
                )
                return

            logger.error(
                "TelegramError on attempt %d/%d for chat %d msg %d: %s",
                attempt, REACTION_RETRY_COUNT, job.chat_id, job.message_id, exc,
            )
            if attempt < REACTION_RETRY_COUNT:
                await asyncio.sleep(REACTION_RETRY_DELAY * attempt)

        except Exception as exc:
            logger.error(
                "Unexpected error on attempt %d/%d for chat %d msg %d: %s",
                attempt, REACTION_RETRY_COUNT, job.chat_id, job.message_id, exc,
            )
            if attempt < REACTION_RETRY_COUNT:
                await asyncio.sleep(REACTION_RETRY_DELAY)

    logger.warning(
        "All %d retries exhausted for chat %d msg %d. Skipping.",
        REACTION_RETRY_COUNT, job.chat_id, job.message_id,
    )


# ─── Message handler ──────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main handler for every incoming message.
    Decides whether to react and enqueues the reaction job.
    """
    message: Optional[Message] = update.effective_message
    if not message:
        return

    chat = update.effective_chat
    if not chat:
        return

    chat_id = chat.id
    message_id = message.message_id

    # ── Guard: check all pre-conditions ───────────────────────────────────

    # 1. Auto reaction globally enabled?
    auto_reaction = await db.get_setting("auto_reaction")
    if auto_reaction != "1":
        return

    # 2. Maintenance mode?
    maintenance = await db.get_setting("maintenance")
    if maintenance == "1":
        return

    # 3. Chat banned?
    if await db.is_chat_banned(chat_id):
        return

    # 4. Supported message type?
    msg_type = get_message_type(message)
    if msg_type is None:
        return

    # 5. Only react in groups/supergroups/channels
    if chat.type not in ("group", "supergroup", "channel"):
        return

    # 6. Flood protection
    if await _flood_protector.is_flooding():
        logger.warning("Flood protection triggered for chat %d — skipping.", chat_id)
        return

    # 7. Per-chat rate limit
    if not await _rate_limiter.is_allowed(chat_id):
        logger.debug("Rate limit hit for chat %d — skipping.", chat_id)
        return

    # ── Select emoji ──────────────────────────────────────────────────────
    random_mode = (await db.get_setting("random_emoji")) == "1"
    big_reaction_setting = (await db.get_setting("big_reaction")) == "1"

    emojis = await db.get_active_emojis()
    if not emojis:
        logger.warning("No active emojis in database — skipping reaction.")
        return

    chosen = pick_emoji(emojis, random_mode=random_mode)
    emoji_str = chosen["emoji"]
    is_big = big_reaction_setting or bool(chosen.get("is_big"))

    # ── Enqueue reaction job ──────────────────────────────────────────────
    job = _ReactionJob(
        chat_id=chat_id,
        message_id=message_id,
        emoji=emoji_str,
        is_big=is_big,
    )

    try:
        _reaction_queue.put_nowait(job)
    except asyncio.QueueFull:
        logger.warning(
            "Reaction queue full (%d items). Dropping reaction for chat %d.",
            _reaction_queue.qsize(), chat_id,
        )


# ─── Queue lifecycle ──────────────────────────────────────────────────────────

async def start_queue_worker(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start the background reaction queue worker.
    Called once on bot startup via post_init.
    """
    global _queue_worker_task
    _queue_worker_task = asyncio.create_task(_queue_worker(context))
    logger.info("Reaction queue worker task created.")


async def stop_queue_worker() -> None:
    """
    Gracefully stop the background queue worker by sending a sentinel None.
    """
    global _queue_worker_task
    if _queue_worker_task and not _queue_worker_task.done():
        await _reaction_queue.put(None)
        await _queue_worker_task
    logger.info("Reaction queue worker stopped.")


# ─── my_chat_member handler (track admin status) ─────────────────────────────

async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called when the bot's own member status changes in a chat.
    Registers or deactivates the chat in the database accordingly.
    """
    member_update = update.my_chat_member
    if not member_update:
        return

    chat = member_update.chat
    new_status = member_update.new_chat_member.status

    if chat.type in ("group", "supergroup"):
        if new_status in ("administrator", "member"):
            await db.upsert_group(chat.id, chat.title or "", chat.username)
            logger.info(
                "Bot joined group '%s' (%d) as %s", chat.title, chat.id, new_status
            )
        elif new_status in ("left", "kicked"):
            await db.deactivate_group(chat.id)
            logger.info("Bot left/kicked from group '%s' (%d)", chat.title, chat.id)

    elif chat.type == "channel":
        if new_status in ("administrator",):
            await db.upsert_channel(chat.id, chat.title or "", chat.username)
            logger.info("Bot added to channel '%s' (%d)", chat.title, chat.id)
        elif new_status in ("left", "kicked"):
            await db.deactivate_channel(chat.id)
            logger.info("Bot left/kicked from channel '%s' (%d)", chat.title, chat.id)


# ─── Handler registration ─────────────────────────────────────────────────────

def register(application) -> None:
    """Register all handlers from this module onto the Application."""
    from telegram.ext import ChatMemberHandler

    # React to all message types in groups and channels
    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND & (filters.ChatType.GROUPS | filters.ChatType.CHANNEL),
            handle_message,
        )
    )

    # Track bot's own membership changes
    application.add_handler(
        ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER)
    )
