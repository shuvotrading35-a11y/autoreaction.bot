"""
AutoReactionBot - Entry Point (Multi-Token Load Balancing)
১০টা পর্যন্ত bot token একসাথে চালায়।
প্রতিটা token আলাদা process এ run করে।
"""

import asyncio
import logging
import multiprocessing
import sys

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder

import database as db
from config import BOT_TOKENS, BOT_VERSION, OWNER_ID
from handlers import register_all
from handlers.reaction import start_queue_worker, stop_queue_worker
from utils import setup_logging

logger = logging.getLogger(__name__)

# ─── Bot commands list ────────────────────────────────────────────────────────

BOT_COMMANDS: list[BotCommand] = [
    BotCommand("start",       "Start the bot & show welcome screen"),
    BotCommand("admin",       "Open the admin panel (owner only)"),
    BotCommand("settings",    "Toggle bot settings (owner only)"),
    BotCommand("stats",       "View statistics (owner only)"),
    BotCommand("broadcast",   "Send a broadcast message (owner only)"),
    BotCommand("addemoji",    "Add an emoji to the pool (owner only)"),
    BotCommand("listemojis",  "List all emojis (owner only)"),
    BotCommand("setdelay",    "Set reaction delay in seconds (owner only)"),
    BotCommand("ban",         "Ban a chat from reactions (owner only)"),
    BotCommand("unban",       "Unban a chat (owner only)"),
    BotCommand("addfj",       "Add force-join channel (owner only)"),
    BotCommand("removefj",    "Remove force-join channel (owner only)"),
    BotCommand("listfj",      "List force-join channels (owner only)"),
    BotCommand("maintenance", "Toggle maintenance mode (owner only)"),
    BotCommand("backup",      "Download database backup (owner only)"),
    BotCommand("optimize",    "Optimise the database (owner only)"),
    BotCommand("health",      "System health report (owner only)"),
]


# ─── Lifecycle callbacks ──────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """DB init, commands set, queue worker start, owner notify."""
    await db.init_db()
    logger.info("Database ready.")

    try:
        await application.bot.set_my_commands(BOT_COMMANDS)
    except Exception as exc:
        logger.warning("Could not set bot commands: %s", exc)

    await start_queue_worker(application)

    try:
        bot_info = await application.bot.get_me()
        total_bots = len(BOT_TOKENS)
        await application.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                f"🟢 <b>AutoReactionBot v{BOT_VERSION} Online!</b>\n\n"
                f"🤖 @{bot_info.username}\n"
                f"🔑 Token {BOT_TOKENS.index(application.bot.token) + 1}/{total_bots}\n"
                f"✅ Database connected\n"
                f"✅ Queue worker running\n"
                f"⚡ Load balancing: {total_bots} bots active"
            ),
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.warning("Could not notify owner: %s", exc)


async def post_shutdown(application: Application) -> None:
    """Graceful shutdown."""
    logger.info("Shutting down bot instance…")
    await stop_queue_worker()


async def error_handler(update: object, context) -> None:
    """Global error handler."""
    logger.error("Unhandled exception:", exc_info=context.error)
    try:
        error_text = (
            f"⚠️ <b>Bot Error</b>\n\n"
            f"<code>{type(context.error).__name__}: {context.error}</code>"
        )
        if len(error_text) > 4000:
            error_text = error_text[:4000] + "…"
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=error_text,
            parse_mode="HTML",
        )
    except Exception:
        pass


# ─── Single bot instance ──────────────────────────────────────────────────────

def run_single_bot(token: str, token_index: int) -> None:
    """
    একটা token দিয়ে একটা bot instance চালায়।
    আলাদা process এ run হয়।
    """
    setup_logging()
    logger.info("Bot instance #%d starting…", token_index + 1)

    app = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)
        .connection_pool_size(16)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    register_all(app)
    app.add_error_handler(error_handler)

    app.run_polling(
        allowed_updates=[
            "message",
            "callback_query",
            "my_chat_member",
            "chat_member",
        ],
        drop_pending_updates=True,
        close_loop=False,
    )


# ─── Multi-process launcher ───────────────────────────────────────────────────

def main() -> None:
    """
    প্রতিটা token এর জন্য আলাদা process চালু করে।
    সব process একসাথে চলে — load balancing।
    """
    setup_logging()

    total = len(BOT_TOKENS)

    logger.info("=" * 50)
    logger.info("  AutoReactionBot v%s", BOT_VERSION)
    logger.info("  Load Balancing: %d bot instance চালু হচ্ছে…", total)
    logger.info("=" * 50)

    if total == 1:
        # Single bot — directly run (no multiprocessing overhead)
        logger.info("Single token mode — directly running…")
        run_single_bot(BOT_TOKENS[0], 0)
        return

    # Multiple tokens — spawn separate process per token
    processes: list[multiprocessing.Process] = []

    for idx, token in enumerate(BOT_TOKENS):
        p = multiprocessing.Process(
            target=run_single_bot,
            args=(token, idx),
            name=f"BotInstance-{idx + 1}",
            daemon=False,
        )
        p.start()
        logger.info("✅ Bot instance #%d started (PID: %d)", idx + 1, p.pid)
        processes.append(p)

    logger.info("🚀 সব %d টা bot instance চালু হয়েছে!", total)

    # Wait for all processes
    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        logger.info("Interrupted — সব bot instance বন্ধ করা হচ্ছে…")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        logger.info("সব instance বন্ধ হয়েছে।")


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted. Exiting.")
        sys.exit(0)