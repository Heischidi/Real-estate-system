"""
RealtorPal Bot — production-grade runner with auto-reconnect.
Optimised for fast message delivery and automatic crash recovery.

Usage:
    python run_bot_simple.py
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import sys
import time

# Fix Windows console encoding
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Load .env ─────────────────────────────────────────────────────────────────
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
    sys.exit(1)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
log = logging.getLogger("realtorpal")

# ── Telegram ──────────────────────────────────────────────────────────────────
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from telegram.request import HTTPXRequest

# ── Messages ──────────────────────────────────────────────────────────────────
def build_welcome(first_name: str) -> str:
    return (
        f"\U0001f3e1 <b>Hey {first_name}, welcome to RealtorPal!</b>\n\n"
        "I\u2019m your personal Nigerian property scout. \U0001f1f3\U0001f1ec\n"
        "I watch multiple real estate websites and alert you the moment "
        "a property matching your budget goes live \u2014 so you never miss a deal.\n\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\U0001f3d9\ufe0f  <b>Cities I cover</b>\n"
        "   \U0001f4cd Abuja  \u2022  \U0001f4cd Lagos\n"
        "   \U0001f4cd Port Harcourt  \u2022  \U0001f4cd Kano\n\n"
        "\U0001f3e0  <b>Property types</b>\n"
        "   Apartments \u2022 Flats \u2022 Duplexes\n"
        "   Detached Houses \u2022 Terraces\n"
        "   Lands \u2022 Commercial\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "\U0001f447 <b>What would you like to do?</b>"
    )

HELP_TEXT = (
    "\U0001f4d6 <b>RealtorPal Commands</b>\n\n"
    "\U0001f514 /subscribe \u2014 Set up your property alerts\n"
    "\u2699\ufe0f /mysettings \u2014 View your preferences\n"
    "\U0001f515 /unsubscribe \u2014 Stop receiving alerts\n"
    "\U0001f3d9\ufe0f /cities \u2014 Supported cities\n"
    "\u2753 /help \u2014 This message\n\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "<b>How it works:</b>\n"
    "1\ufe0f\u20e3  Use /subscribe to pick city, type & budget\n"
    "2\ufe0f\u20e3  Sit back \u2014 I scan listings every 15 minutes\n"
    "3\ufe0f\u20e3  Get instant alerts when matches appear"
)

CITIES_TEXT = (
    "\U0001f5fa\ufe0f <b>Cities RealtorPal Monitors</b>\n\n"
    "\U0001f3db\ufe0f <b>Abuja</b> \u2014 Federal Capital Territory\n"
    "\U0001f30a <b>Lagos</b> \u2014 Nigeria\u2019s commercial & financial hub\n"
    "\u2693 <b>Port Harcourt</b> \u2014 Rivers State capital & oil city\n"
    "\U0001f33e <b>Kano</b> \u2014 Largest city in northern Nigeria\n\n"
    "\U0001f4e1 <i>Sources: PropertyPro, Nigeria Property Centre,\n"
    "PrivateProperty & Property24</i>\n\n"
    "<i>More cities coming soon! Use /subscribe to get started.</i>"
)

# ── Keyboards ─────────────────────────────────────────────────────────────────
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f514 Subscribe for Alerts", callback_data="menu:subscribe")],
        [InlineKeyboardButton("\u2699\ufe0f My Settings",         callback_data="menu:settings")],
        [InlineKeyboardButton("\U0001f515 Unsubscribe",           callback_data="menu:unsubscribe")],
        [InlineKeyboardButton("\U0001f3d9\ufe0f Available Cities", callback_data="menu:cities")],
    ])

# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = (user.first_name or "there") if user else "there"
    log.info("User /start — name=%s id=%s", name, user.id if user else "?")
    await update.message.reply_html(build_welcome(name), reply_markup=main_menu())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(HELP_TEXT)


async def cities_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(CITIES_TEXT)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = (query.data or "").replace("menu:", "").replace("_", " ").title()
    await query.edit_message_text(
        f"\u2699\ufe0f <b>{action}</b> requires the full platform to be running.\n\n"
        "Start with: <code>docker compose up -d</code>\n"
        "Or deploy to Railway \u2014 see README.md for instructions.",
        parse_mode="HTML",
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Bot error: %s", context.error)


# ── Application builder ───────────────────────────────────────────────────────
def build_app() -> Application:
    # connect_timeout: time to establish connection (raise it for slow networks)
    # read_timeout: MUST be higher than the long-poll timeout sent to Telegram (10s)
    # Setting read_timeout=15 means: wait up to 15s for Telegram to respond
    # Telegram's long-poll will respond immediately when a message arrives
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=20.0,
        read_timeout=15.0,   # ← slightly above the 10s long-poll timeout
        write_timeout=10.0,
        pool_timeout=10.0,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )

    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("help",     help_cmd))
    app.add_handler(CommandHandler("cities",   cities_cmd))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu:"))
    app.add_error_handler(error_handler)

    return app


# ── Main with auto-reconnect loop ─────────────────────────────────────────────
def main() -> None:
    log.info("=" * 50)
    log.info("RealtorPal @RealtorpalBot starting...")
    log.info("Token: %s...", BOT_TOKEN[:20])
    log.info("=" * 50)

    backoff = 5  # seconds before retry after crash
    attempts = 0

    while True:
        attempts += 1
        try:
            log.info("Connecting to Telegram (attempt #%d)...", attempts)
            app = build_app()
            # poll_interval=0 → check for updates immediately after each response
            # timeout=10       → Telegram holds connection up to 10s waiting for updates
            #                    Messages arrive INSTANTLY during this 10s window
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                poll_interval=0.0,
                timeout=10,
            )
            # If run_polling exits cleanly (Ctrl+C), stop retrying
            log.info("Bot stopped cleanly.")
            break

        except KeyboardInterrupt:
            log.info("Stopped by user.")
            break

        except Exception as exc:
            log.error("Bot crashed: %s", exc)
            log.info("Restarting in %d seconds...", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)  # exponential backoff, max 60s


if __name__ == "__main__":
    main()
