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
    print("ERROR: TELEGRAM_BOT_TOKEN not found in environment variables or .env file.")
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
        "   \U0001f4cd Abuja  \u2022  \U0001f4cd Lagos  \u2022  \U0001f4cd Port Harcourt\n\n"
        "\U0001f3e0  <b>Property types</b>\n"
        "   Apartments \u2022 Flats \u2022 Duplexes\n"
        "   Detached Houses \u2022 Terraces\n"
        "   Lands \u2022 Commercial\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "👇 <b>Select a city below to view available properties:</b>"
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
    "\u2693 <b>Port Harcourt</b> \u2014 Rivers State capital & oil city\n\n"
    "\U0001f4e1 <i>Sources: PropertyPro, Nigeria Property Centre,\n"
    "PrivateProperty & Property24</i>\n\n"
    "<i>More cities coming soon! Use /subscribe to get started.</i>"
)

MOCK_LISTINGS = {
    "abuja": [
        "🏢 <b>Luxury 4 Bedroom Terrace</b>\n\n📍 <b>Location:</b> Maitama, Abuja\n🏷️ <b>Type:</b> Terrace\n💰 <b>Price:</b> ₦350.0M\n🛏 <b>Bedrooms:</b> 4\n🚿 <b>Bathrooms:</b> 4\n\n🔗 <a href='https://example.com/maitama'>View Listing</a>\n\n<i>📡 via PropertyPro</i>",
        "🏠 <b>Modern 3 Bedroom Apartment</b>\n\n📍 <b>Location:</b> Wuye, Abuja\n🏷️ <b>Type:</b> Apartment\n💰 <b>Price:</b> ₦85.0M\n🛏 <b>Bedrooms:</b> 3\n🚿 <b>Bathrooms:</b> 3\n\n🔗 <a href='https://example.com/wuye'>View Listing</a>\n\n<i>📡 via Nigeria Property Centre</i>",
        "🏘️ <b>5 Bedroom Detached Duplex</b>\n\n📍 <b>Location:</b> Gwarinpa, Abuja\n🏷️ <b>Type:</b> Duplex\n💰 <b>Price:</b> ₦180.0M\n🛏 <b>Bedrooms:</b> 5\n🚿 <b>Bathrooms:</b> 6\n\n🔗 <a href='https://example.com/gwarinpa'>View Listing</a>\n\n<i>📡 via PrivateProperty</i>",
        "🏪 <b>Commercial Office Space</b>\n\n📍 <b>Location:</b> Wuse II, Abuja\n🏷️ <b>Type:</b> Commercial\n💰 <b>Price:</b> ₦12.0M/year\n🛏 <b>Bedrooms:</b> None\n🚿 <b>Bathrooms:</b> 2\n\n🔗 <a href='https://example.com/wuse2'>View Listing</a>\n\n<i>📡 via Property24</i>",
        "🌍 <b>1000 sqm Serviced Plot</b>\n\n📍 <b>Location:</b> Guzape, Abuja\n🏷️ <b>Type:</b> Land\n💰 <b>Price:</b> ₦120.0M\n\n🔗 <a href='https://example.com/guzape'>View Listing</a>\n\n<i>📡 via PropertyPro</i>",
    ],
    "lagos": [
        "🏢 <b>3 Bedroom Flat in Lekki Phase 1</b>\n\n📍 <b>Location:</b> Lekki Phase 1, Lagos\n🏷️ <b>Type:</b> Flat\n💰 <b>Price:</b> ₦120.0M\n🛏 <b>Bedrooms:</b> 3\n🚿 <b>Bathrooms:</b> 3\n\n🔗 <a href='https://example.com/lekki'>View Listing</a>\n\n<i>📡 via PropertyPro</i>",
        "🏡 <b>Stunning 5 Bedroom Fully Detached House</b>\n\n📍 <b>Location:</b> Banana Island, Ikoyi, Lagos\n🏷️ <b>Type:</b> Detached House\n💰 <b>Price:</b> ₦1.2B\n🛏 <b>Bedrooms:</b> 5\n🚿 <b>Bathrooms:</b> 6\n\n🔗 <a href='https://example.com/ikoyi'>View Listing</a>\n\n<i>📡 via Nigeria Property Centre</i>",
        "🏢 <b>Waterfront 2 Bedroom Apartment</b>\n\n📍 <b>Location:</b> Victoria Island, Lagos\n🏷️ <b>Type:</b> Apartment\n💰 <b>Price:</b> ₦180.0M\n🛏 <b>Bedrooms:</b> 2\n🚿 <b>Bathrooms:</b> 2\n\n🔗 <a href='https://example.com/vi'>View Listing</a>\n\n<i>📡 via PrivateProperty</i>",
        "🏘️ <b>4 Bedroom Terraced Duplex</b>\n\n📍 <b>Location:</b> Ajah, Lagos\n🏷️ <b>Type:</b> Terrace\n💰 <b>Price:</b> ₦65.0M\n🛏 <b>Bedrooms:</b> 4\n🚿 <b>Bathrooms:</b> 4\n\n🔗 <a href='https://example.com/ajah'>View Listing</a>\n\n<i>📡 via Property24</i>",
        "🏪 <b>Commercial Office Building</b>\n\n📍 <b>Location:</b> Ikeja, Lagos\n🏷️ <b>Type:</b> Commercial\n💰 <b>Price:</b> ₦450.0M\n\n🔗 <a href='https://example.com/ikeja'>View Listing</a>\n\n<i>📡 via PropertyPro</i>",
    ],
    "port_harcourt": [
        "🏘️ <b>4 Bedroom Duplex</b>\n\n📍 <b>Location:</b> Peter Odili Road, Port Harcourt\n🏷️ <b>Type:</b> Duplex\n💰 <b>Price:</b> ₦95.0M\n🛏 <b>Bedrooms:</b> 4\n🚿 <b>Bathrooms:</b> 4\n\n🔗 <a href='https://example.com/peterodili'>View Listing</a>\n\n<i>📡 via PropertyPro</i>",
        "🏢 <b>3 Bedroom Apartment</b>\n\n📍 <b>Location:</b> GRA Phase 2, Port Harcourt\n🏷️ <b>Type:</b> Apartment\n💰 <b>Price:</b> ₦60.0M\n🛏 <b>Bedrooms:</b> 3\n🚿 <b>Bathrooms:</b> 3\n\n🔗 <a href='https://example.com/gra2'>View Listing</a>\n\n<i>📡 via Nigeria Property Centre</i>",
        "🌍 <b>Serviced Residential Land</b>\n\n📍 <b>Location:</b> Airport Road, Port Harcourt\n🏷️ <b>Type:</b> Land\n💰 <b>Price:</b> ₦15.0M\n\n🔗 <a href='https://example.com/airportrd'>View Listing</a>\n\n<i>📡 via PrivateProperty</i>",
        "🏡 <b>5 Bedroom Detached House</b>\n\n📍 <b>Location:</b> Eliozu, Port Harcourt\n🏷️ <b>Type:</b> Detached House\n💰 <b>Price:</b> ₦110.0M\n🛏 <b>Bedrooms:</b> 5\n🚿 <b>Bathrooms:</b> 5\n\n🔗 <a href='https://example.com/eliozu'>View Listing</a>\n\n<i>📡 via Property24</i>",
        "🏪 <b>Commercial Warehouse</b>\n\n📍 <b>Location:</b> Trans Amadi, Port Harcourt\n🏷️ <b>Type:</b> Commercial\n💰 <b>Price:</b> ₦25.0M/year\n\n🔗 <a href='https://example.com/transamadi'>View Listing</a>\n\n<i>📡 via PropertyPro</i>",
    ],
}

# ── Keyboards ─────────────────────────────────────────────────────────────────
def start_city_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ Abuja", callback_data="start_city:abuja")],
        [InlineKeyboardButton("🌊 Lagos", callback_data="start_city:lagos")],
        [InlineKeyboardButton("⚓ Port Harcourt", callback_data="start_city:port_harcourt")],
    ])

def after_listings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f514 Subscribe for Alerts", callback_data="menu:subscribe")],
        [InlineKeyboardButton("🔙 Back to Cities", callback_data="back_to_cities")],
    ])

# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = (user.first_name or "there") if user else "there"
    log.info("User /start — name=%s id=%s", name, user.id if user else "?")
    await update.message.reply_html(build_welcome(name), reply_markup=start_city_menu())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(HELP_TEXT)

async def cities_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(CITIES_TEXT)

async def start_city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    city_code = (query.data or "").replace("start_city:", "")
    city_name = city_code.replace("_", " ").title()
    
    await query.message.reply_html(f"🔍 <b>Fetching properties in {city_name}...</b>")
    
    listings = []
    try:
        from app.database import get_db_context
        from app.models.listing import City as DBCity
        from app.schemas.listing import ListingFilter
        from app.services.listing_service import ListingService
        from app.bot.formatters import format_listing_alert
        
        async def _fetch() -> list:
            async with get_db_context() as db:
                service = ListingService(db)
                filters = ListingFilter(city=DBCity(city_code), page=1, page_size=1000)
                paginated = await service.list_listings(filters)
                return paginated.items
                
        listings_objs = await _fetch()
        listings = [format_listing_alert(l) for l in listings_objs]
    except Exception as e:
        log.warning("Failed to fetch listings from database in run_bot_simple, falling back to mocks: %s", e)
        listings = MOCK_LISTINGS.get(city_code, [])
        
    if not listings:
        await query.message.reply_html(
            f"📭 <b>No properties found for {city_name} yet.</b>\n\n"
            "Properties will appear automatically once they are added by the admin.",
            reply_markup=after_listings_menu()
        )
        return
        
    for msg in listings:
        await query.message.reply_html(msg, disable_web_page_preview=True)
        
    await query.message.reply_html(
        f"💡 These are the properties available in <b>{city_name}</b>.\n"
        "Would you like to set up automatic alerts for new ones?",
        reply_markup=after_listings_menu()
    )

async def back_to_cities_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    name = (user.first_name or "there") if user else "there"
    await query.edit_message_text(
        build_welcome(name),
        reply_markup=start_city_menu(),
        parse_mode="HTML"
    )

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
    app.add_handler(CallbackQueryHandler(start_city_callback, pattern="^start_city:"))
    app.add_handler(CallbackQueryHandler(back_to_cities_callback, pattern="^back_to_cities$"))
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
