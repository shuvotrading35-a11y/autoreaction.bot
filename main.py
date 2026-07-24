"""
AutoReactionBot - Entry Point
Initialises logging, database, registers all handlers,
starts the reaction queue worker, and runs the bot.
"""

import asyncio
import logging
import sys

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder

import database as db
from config import BOT_TOKEN, BOT_VERSION, OWNER_ID
from handlers import register_all
from handlers.reaction import start_queue_worker, stop_queue_worker
from utils import setup_logging

logger = logging.getLogger(__name__)


# ─── Bot commands list ────────────────────────────────────────────────────────

BOT_COMMANDS: list[BotCommand] = [
    BotCommand("start", "Start the bot & show welcome screen"),
    BotCommand("admin", "Open the admin panel (owner only)"),
    BotCommand("settings", "Toggle bot settings (owner only)"),
    BotCommand("stats", "View statistics (owner only)"),
    BotCommand("broadcast", "Send a broadcast message (owner only)"),
    BotCommand("addemoji", "Add an emoji to the pool (owner only)"),
    BotCommand("listemojis", "List all emojis (owner only)"),
    BotCommand("setdelay", "Set reaction delay in seconds (owner only)"),
    BotCommand("ban", "Ban a chat from reactions (owner only)"),
    BotCommand("unban", "Unban a chat (owner only)"),
    BotCommand("addfj", "Add force-join channel (owner only)"),
    BotCommand("removefj", "Remove force-join channel (owner only)"),
    BotCommand("listfj", "List force-join channels (owner only)"),
    BotCommand("maintenance", "Toggle maintenance mode (owner only)"),
    BotCommand("backup", "Download database backup (owner only)"),
    BotCommand("optimize", "Optimise the database (owner only)"),
    BotCommand("health", "System health report (owner only)"),
]


# ─── Lifecycle callbacks ──────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """
    Called after the Application is fully initialised but before polling starts.
    - Initialise the database.
    - Set bot commands.
    - Start the reaction queue worker.
    - Notify the owner.
    """
    # Initialise database schema and seed data
    await db.init_db()
    logger.info("Database ready.")

    # Register bot commands in Telegram UI
    try:
        await application.bot.set_my_commands(BOT_COMMANDS)
        logger.info("Bot commands registered.")
    except Exception as exc:
        logger.warning("Could not set bot commands: %s", exc)

    # Start the background reaction queue worker
    await start_queue_worker(application)

    # Notify owner
    try:
        bot_info = await application.bot.get_me()
        uptime_msg = (
            f"🟢 <b>AutoReactionBot v{BOT_VERSION} is online!</b>\n\n"
            f"🤖 Username: @{bot_info.username}\n"
            f"🆔 Bot ID: <code>{bot_info.id}</code>\n"
            f"🐍 Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
            f"✅ Database connected\n"
            f"✅ Queue worker running\n"
            f"✅ Ready to react!"
        )
        await application.bot.send_message(
            chat_id=OWNER_ID,
            text=uptime_msg,
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.warning("Could not notify owner on startup: %s", exc)


async def post_shutdown(application: Application) -> None:
    """
    Called during graceful shutdown.
    Stops the reaction queue worker cleanly.
    """
    logger.info("Shutting down — draining reaction queue…")
    await stop_queue_worker()
    logger.info("AutoReactionBot shutdown complete.")


# ─── Error handler ────────────────────────────────────────────────────────────

async def error_handler(update: object, context) -> None:
    """
    Global error handler.
    Logs every unhandled exception that bubbles up through the dispatcher.
    """
    logger.error("Unhandled exception:", exc_info=context.error)

    # Notify the owner about unexpected errors
    try:
        error_text = (
            f"⚠️ <b>Bot Error</b>\n\n"
            f"<code>{type(context.error).__name__}: {context.error}</code>"
        )
        # Truncate to stay within Telegram limits
        if len(error_text) > 4000:
            error_text = error_text[:4000] + "…"
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=error_text,
            parse_mode="HTML",
        )
    except Exception:
        pass  # Never crash inside the error handler


# ─── Build application ────────────────────────────────────────────────────────

def build_application() -> Application:
    """
    Construct and configure the Application instance.
    """
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        # Allow concurrent updates in different chats for throughput
        .concurrent_updates(True)
        # Connection pool: tune for your server
        .connection_pool_size(16)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    # Register all handlers
    register_all(app)

    # Attach global error handler
    app.add_error_handler(error_handler)

    return app


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    """
    Set up logging, build the application, and start polling.
    Blocks until the process receives a termination signal.
    """
    setup_logging()

    logger.info("=" * 50)
    logger.info("  AutoReactionBot v%s starting…", BOT_VERSION)
    logger.info("  Owner ID: %d", OWNER_ID)
    logger.info("=" * 50)

    application = build_application()

    logger.info("Starting polling…")
    application.run_polling(
        allowed_updates=[
            "message",
            "callback_query",
            "my_chat_member",
            "chat_member",
        ],
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting.")
        sys.exit(0)
