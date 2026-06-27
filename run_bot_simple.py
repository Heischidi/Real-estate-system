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
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest
from app.bot.handlers.payment import payment_conv_handler

# ── Kill-switch ──────────────────────────────────────────────────────────────
# Set to True to pause the entire bot. Every interaction will return a
# "license expired" message. Set back to False to re-activate.
SYSTEM_PAUSED = True

LICENSE_EXPIRED_MSG = (
    "⛔ <b>Service Unavailable</b>\n\n"
    "Your license has expired. Please contact support to renew access.\n\n"
    "<i>RealtorPal — Nigerian Property Scout</i>"
)

# ── Conversation states ───────────────────────────────────────────────────────
BROWSE_CITY, BROWSE_PURPOSE, BROWSE_BUDGET = range(10, 13)

_KEY_CATEGORY = "browse_category"
_KEY_CITY     = "browse_city"
_KEY_PURPOSE  = "browse_purpose"
_KEY_BUDGET   = "browse_budget"


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
        "👇 <b>Select what you would like to browse:</b>"
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
        {"title": "Luxury 4 Bedroom Terrace", "location": "Maitama, Abuja", "price": 350_000_000, "purpose": "sale", "type": "Terrace", "bedrooms": 4, "url": "https://example.com/maitama"},
        {"title": "Modern 3 Bedroom Apartment", "location": "Wuye, Abuja", "price": 85_000_000, "purpose": "sale", "type": "Apartment", "bedrooms": 3, "url": "https://example.com/wuye"},
        {"title": "5 Bedroom Detached Duplex", "location": "Gwarinpa, Abuja", "price": 180_000_000, "purpose": "sale", "type": "Duplex", "bedrooms": 5, "url": "https://example.com/gwarinpa"},
        {"title": "3 Bedroom Flat For Rent", "location": "Garki, Abuja", "price": 2_500_000, "purpose": "rent", "type": "Flat", "bedrooms": 3, "url": "https://example.com/garki"},
        {"title": "1 Bedroom Mini Flat", "location": "Kubwa, Abuja", "price": 800_000, "purpose": "rent", "type": "Flat", "bedrooms": 1, "url": "https://example.com/kubwa"},
    ],
    "lagos": [
        {"title": "3 Bedroom Flat in Lekki Phase 1", "location": "Lekki Phase 1, Lagos", "price": 120_000_000, "purpose": "sale", "type": "Flat", "bedrooms": 3, "url": "https://example.com/lekki"},
        {"title": "5 Bedroom Fully Detached House", "location": "Banana Island, Ikoyi, Lagos", "price": 1_200_000_000, "purpose": "sale", "type": "Detached House", "bedrooms": 5, "url": "https://example.com/ikoyi"},
        {"title": "2 Bedroom Apartment For Rent", "location": "Victoria Island, Lagos", "price": 3_500_000, "purpose": "rent", "type": "Apartment", "bedrooms": 2, "url": "https://example.com/vi"},
        {"title": "4 Bedroom Terraced Duplex", "location": "Ajah, Lagos", "price": 65_000_000, "purpose": "sale", "type": "Terrace", "bedrooms": 4, "url": "https://example.com/ajah"},
    ],
    "port_harcourt": [
        {"title": "4 Bedroom Duplex", "location": "Peter Odili Road, Port Harcourt", "price": 95_000_000, "purpose": "sale", "type": "Duplex", "bedrooms": 4, "url": "https://example.com/peterodili"},
        {"title": "3 Bedroom Apartment For Rent", "location": "GRA Phase 2, Port Harcourt", "price": 1_800_000, "purpose": "rent", "type": "Apartment", "bedrooms": 3, "url": "https://example.com/gra2"},
        {"title": "Serviced Residential Land", "location": "Airport Road, Port Harcourt", "price": 15_000_000, "purpose": "sale", "type": "Land", "bedrooms": None, "url": "https://example.com/airportrd"},
        {"title": "5 Bedroom Detached House", "location": "Eliozu, Port Harcourt", "price": 110_000_000, "purpose": "sale", "type": "Detached House", "bedrooms": 5, "url": "https://example.com/eliozu"},
    ],
}

MOCK_CARS = {
    "abuja": [
        {"title": "Toyota Corolla 2018 (Silver)", "location": "Wuse 2, Abuja", "price": 11_500_000, "purpose": "sale", "type": "Car", "year": 2018, "colour": "Silver", "url": "https://wa.me/2348012345678"},
        {"title": "Honda Accord 2017 (Black)", "location": "Garki, Abuja", "price": 12_800_000, "purpose": "sale", "type": "Car", "year": 2017, "colour": "Black", "url": "https://wa.me/2348012345678"},
        {"title": "Hyundai Elantra 2019 (White)", "location": "Maitama, Abuja", "price": 13_500_000, "purpose": "sale", "type": "Car", "year": 2019, "colour": "White", "url": "https://wa.me/2348012345678"},
        {"title": "Kia Sportage 2016 (Blue)", "location": "Asokoro, Abuja", "price": 14_200_000, "purpose": "sale", "type": "Car", "year": 2016, "colour": "Blue", "url": "https://wa.me/2348012345678"},
        {"title": "Lexus IS 250 2015 (Red)", "location": "Gwarinpa, Abuja", "price": 14_900_000, "purpose": "sale", "type": "Car", "year": 2015, "colour": "Red", "url": "https://wa.me/2348012345678"},
    ],
    "lagos": [],
    "port_harcourt": []
}


CITY_DISPLAY = {
    "abuja":         ("Abuja",         "abuja"),
    "lagos":         ("Lagos",         "lagos"),
    "port_harcourt": ("Port Harcourt", "port harcourt"),
}


def _fmt_price(p: int) -> str:
    if p >= 1_000_000_000:
        return f"₦{p/1_000_000_000:.2g}B"
    if p >= 1_000_000:
        return f"₦{p/1_000_000:.4g}M"
    if p >= 1_000:
        return f"₦{p/1_000:.4g}K"
    return f"₦{p:,}"


def _format_mock(listing: dict) -> str:
    emoji = {"Apartment": "🏢", "Flat": "🏠", "Duplex": "🏘️",
             "Detached House": "🏡", "Terrace": "🏢", "Land": "🌍",
             "Commercial": "🏪"}.get(listing["type"], "🏠")
    beds = f"\n🛏 <b>Bedrooms:</b> {listing['bedrooms']}" if listing.get("bedrooms") else ""
    purpose_tag = " (For Rent)" if listing.get("purpose") == "rent" else " (For Sale)"
    return (
        f"{emoji} <b>{listing['title']}{purpose_tag}</b>\n\n"
        f"📍 <b>Location:</b> {listing['location']}\n"
        f"🏷️ <b>Type:</b> {listing['type']}\n"
        f"💰 <b>Price:</b> {_fmt_price(listing['price'])}"
        f"{beds}\n\n"
        f"🔗 <a href='{listing['url']}'>View Listing</a>\n\n"
        f"<i>📡 via PropertyPro (demo)</i>"
    )


def _format_mock_car(listing: dict) -> str:
    purpose_tag = " (For Rent)" if listing.get("purpose") == "rent" else " (For Sale)"
    return (
        f"🚗 <b>{listing['title']}{purpose_tag}</b>\n\n"
        f"📍 <b>Location:</b> {listing['location']}\n"
        f"🏷️ <b>Type:</b> Car\n"
        f"💰 <b>Price:</b> {_fmt_price(listing['price'])}\n"
        f"📅 <b>Year of Make:</b> {listing.get('year', 'N/A')}\n"
        f"🎨 <b>Colour:</b> {listing.get('colour', 'N/A')}\n\n"
        f"🔗 <a href='{listing['url']}'>Contact Seller</a>\n\n"
        f"<i>📡 via RealtorPal (demo)</i>"
    )



def _parse_budget(text: str) -> int | None | int:
    """Returns amount (int), None (no cap), or -1 (invalid)."""
    text = text.strip().lower().replace(",", "").replace("₦", "")
    if text in ("0", "skip", "no", "none", "any"):
        return None
    multiplier = 1
    if text.endswith("m"):
        multiplier = 1_000_000; text = text[:-1]
    elif text.endswith("k"):
        multiplier = 1_000; text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except (ValueError, OverflowError):
        return -1


# ── Keyboards ─────────────────────────────────────────────────────────────────
def start_category_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Houses & Properties", callback_data="category:houses")],
        [InlineKeyboardButton("🚗 Cars & Vehicles", callback_data="category:cars")],
    ])


def start_city_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ Abuja", callback_data="start_city:abuja")],
        [InlineKeyboardButton("🌊 Lagos", callback_data="start_city:lagos")],
        [InlineKeyboardButton("⚓ Port Harcourt", callback_data="start_city:port_harcourt")],
        [InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")],
    ])


def rent_or_buy_keyboard(city_code: str, is_car: bool = False) -> InlineKeyboardMarkup:
    back_callback = "back_to_categories" if is_car else "back_to_cities"
    buy_label = "🚗 Buy" if is_car else "🏠 Buy"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔑 Rent", callback_data=f"browse_purpose:{city_code}:rent"),
            InlineKeyboardButton(buy_label,  callback_data=f"browse_purpose:{city_code}:sale"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data=back_callback)],
    ])


def after_listings_menu(category: str = "houses") -> InlineKeyboardMarkup:
    back_callback = "back_to_cities" if category == "houses" else "back_to_categories"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Subscribe for Alerts", callback_data="menu:subscribe")],
        [InlineKeyboardButton("🔙 Back", callback_data=back_callback)],
    ])


def load_more_menu(city_code: str, next_page: int, purpose: str, max_budget: int, category: str = "houses") -> InlineKeyboardMarkup:
    back_callback = "back_to_cities" if category == "houses" else "back_to_categories"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ Load More",
            callback_data=f"load_more:{city_code}:{next_page}:{purpose}:{max_budget}:{category}")],
        [InlineKeyboardButton("🔔 Subscribe for Alerts", callback_data="menu:subscribe")],
        [InlineKeyboardButton("🔙 Back", callback_data=back_callback)],
    ])



# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if SYSTEM_PAUSED:
        await update.message.reply_html(LICENSE_EXPIRED_MSG)
        return

    from app.bot.middleware import enforce_community_membership
    if not await enforce_community_membership(update, context):
        return

    # Clear previous browsing state
    context.user_data.pop(_KEY_CATEGORY, None)
    context.user_data.pop(_KEY_CITY, None)
    context.user_data.pop(_KEY_PURPOSE, None)
    context.user_data.pop(_KEY_BUDGET, None)

    user = update.effective_user
    name = (user.first_name or "there") if user else "there"
    log.info("User /start — name=%s id=%s", name, user.id if user else "?")
    await update.message.reply_html(build_welcome(name), reply_markup=start_category_menu())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if SYSTEM_PAUSED:
        await update.message.reply_html(LICENSE_EXPIRED_MSG)
        return
    await update.message.reply_html(HELP_TEXT)


async def cities_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if SYSTEM_PAUSED:
        await update.message.reply_html(LICENSE_EXPIRED_MSG)
        return
    await update.message.reply_html(CITIES_TEXT)


# Entry point callback after category is selected
async def start_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if SYSTEM_PAUSED:
        await query.edit_message_text(LICENSE_EXPIRED_MSG, parse_mode="HTML")
        return ConversationHandler.END
    category = (query.data or "").replace("category:", "")
    context.user_data[_KEY_CATEGORY] = category
    
    if category == "houses":
        await query.edit_message_text(
            "👇 <b>Select a city below to view available properties:</b>",
            reply_markup=start_city_menu(),
            parse_mode="HTML"
        )
        return BROWSE_CITY
    else:
        # Cars (Abuha only)
        context.user_data[_KEY_CITY] = "abuja"
        await query.edit_message_text(
            "🚗 Cars are only available in <b>Abuja</b>.\n\n"
            "Are you looking to <b>Rent</b> or <b>Buy</b> a car?",
            reply_markup=rent_or_buy_keyboard("abuja", is_car=True),
            parse_mode="HTML"
        )
        return BROWSE_PURPOSE


# Step 1 — city selected (for Houses)
async def start_city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    city_code = (query.data or "").replace("start_city:", "")
    context.user_data[_KEY_CITY] = city_code  # type: ignore[index]
    city_name, _ = CITY_DISPLAY.get(city_code, (city_code.replace("_", " ").title(), city_code))
    await query.edit_message_text(
        f"🏙️ <b>{city_name}</b> selected!\n\n"
        "Are you looking to <b>Rent</b> or <b>Buy</b> a property?",
        reply_markup=rent_or_buy_keyboard(city_code, is_car=False),
        parse_mode="HTML"
    )
    return BROWSE_PURPOSE


# Step 2 — rent or buy
async def browse_purpose_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    parts = (query.data or "").split(":")
    if len(parts) < 3:
        return ConversationHandler.END
    city_code = parts[1]
    purpose   = parts[2]
    context.user_data[_KEY_CITY]    = city_code  # type: ignore[index]
    context.user_data[_KEY_PURPOSE] = purpose    # type: ignore[index]
    
    category = context.user_data.get(_KEY_CATEGORY, "houses")
    items_label = "cars" if category == "cars" else "properties"
    label = "🔑 Rent" if purpose == "rent" else ("🚗 Buy" if category == "cars" else "🏠 Buy")
    
    await query.edit_message_text(
        f"{label} — got it!\n\n"
        "💰 <b>What is your maximum budget?</b>\n\n"
        "Enter an amount in Naira:\n"
        "  • <code>12000000</code> for ₦12M\n"
        "  • <code>12m</code> for ₦12M\n"
        "  • <code>500k</code> for ₦500K\n\n"
        f"Type <code>0</code> or <code>skip</code> to see <b>all</b> {items_label} with no budget cap.",
        parse_mode="HTML"
    )
    return BROWSE_BUDGET


# Step 3 — budget entered
async def browse_budget_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text or ""
    budget = _parse_budget(text)
    if budget == -1:
        await update.message.reply_html(
            "⚠️ I didn't understand that amount. Please try again.\n"
            "Examples: <code>12000000</code>, <code>12m</code>, <code>500k</code>, <code>0</code>"
        )
        return BROWSE_BUDGET
    context.user_data[_KEY_BUDGET] = budget  # type: ignore[index]
    category  = context.user_data.get(_KEY_CATEGORY, "houses")
    city_code = context.user_data.get(_KEY_CITY, "")  # type: ignore[index]
    purpose   = context.user_data.get(_KEY_PURPOSE, "")  # type: ignore[index]
    await _send_listings(update.message, city_code, purpose, budget, page=1, category=category)
    return ConversationHandler.END


async def load_more_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = (query.data or "").split(":")
    if len(parts) < 3:
        return
    city_code = parts[1]
    try:
        page = int(parts[2])
    except ValueError:
        return
        
    if page > 1:
        is_free = True
        try:
            from app.database import AsyncSessionLocal
            from app.models.subscriber import SubscriptionTier
            from app.services.subscriber_service import SubscriberService
            
            async with AsyncSessionLocal() as db:
                sub_service = SubscriberService(db)
                subscriber = await sub_service.get_by_telegram_id(update.effective_user.id)
                if subscriber and subscriber.subscription_tier != SubscriptionTier.FREE:
                    is_free = False
        except Exception:
            pass # allow in fallback mode if DB fails, or we could block. We'll block to be safe.
            
        if is_free:
            keyboard = [[InlineKeyboardButton("💎 Upgrade to Premium", callback_data="trigger_payment")]]
            await query.message.reply_text(
                "🔒 *Premium Feature*\n\n"
                "Free users are limited to 10 properties per search.\n"
                "Upgrade to Premium to view unlimited properties!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
    purpose    = parts[3] if len(parts) > 3 else ""
    try:
        max_budget: int | None = int(parts[4]) if len(parts) > 4 and parts[4] else None
    except ValueError:
        max_budget = None
    if max_budget == 0:
        max_budget = None
    category = parts[5] if len(parts) > 5 else "houses"
    await _send_listings(query.message, city_code, purpose, max_budget, page=page, category=category)


async def back_to_cities_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👇 <b>Select a city below to view available properties:</b>",
        reply_markup=start_city_menu(),
        parse_mode="HTML"
    )
    return BROWSE_CITY


async def back_to_categories_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    name = (user.first_name or "there") if user else "there"
    await query.edit_message_text(
        build_welcome(name),
        reply_markup=start_category_menu(),
        parse_mode="HTML"
    )
    return ConversationHandler.END



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


async def _send_listings(
    message: object,
    city_code: str,
    purpose: str,
    max_budget: int | None,
    page: int,
    category: str = "houses",
) -> None:
    """Fetch & send paginated listings with budget + purpose filter."""
    from telegram import Message
    msg: Message = message  # type: ignore[assignment]

    city_name, location_kw = CITY_DISPLAY.get(
        city_code, (city_code.replace("_", " ").title(), city_code)
    )
    purpose_label = "for rent" if purpose == "rent" else "for sale" if purpose == "sale" else ""
    budget_label  = f" within {_fmt_price(max_budget)}" if max_budget else ""

    PAGE_SIZE = 10
    item_type_label = "cars" if category == "cars" else "properties"
    item_type_label_single = "car" if category == "cars" else "property"
    item_type_label_plural = "cars" if category == "cars" else "properties"

    if page == 1:
        summary = f"🔍 <b>Fetching {item_type_label} in {city_name}"
        if purpose_label:
            summary += f" {purpose_label}"
        summary += budget_label + "...</b>"
        await msg.reply_html(summary)

    # Try live database first
    listings = []
    total = 0
    has_more = False
    try:
        from app.database import get_db_context
        from app.models.listing import City as DBCity, ListingPurpose, PropertyType
        from app.schemas.listing import ListingFilter
        from app.services.listing_service import ListingService
        from app.bot.formatters import format_listing_alert

        async def _fetch() -> object:
            async with get_db_context() as db:
                service = ListingService(db)
                purpose_enum = (
                    ListingPurpose(purpose) if purpose in ("rent", "sale") else None
                )
                prop_type_filter = PropertyType.CAR if category == "cars" else None
                exclude_type_filter = PropertyType.CAR if category == "houses" else None
                filt = ListingFilter(
                    city=DBCity(city_code),
                    location_keyword=location_kw,
                    listing_purpose=purpose_enum,
                    property_type=prop_type_filter,
                    exclude_type=exclude_type_filter,
                    max_price=max_budget,
                    page=page,
                    page_size=PAGE_SIZE,
                )
                return await service.list_listings(filt)

        paginated = await asyncio.wait_for(_fetch(), timeout=20.0)
        listings  = paginated.items
        total     = paginated.total
        has_more  = (page * PAGE_SIZE) < total

    except Exception as e:
        log.warning("DB unavailable, using mock listings: %s", e)
        # Fall back to mock data with local filtering
        raw = MOCK_LISTINGS.get(city_code, []) if category == "houses" else MOCK_CARS.get(city_code, [])
        filtered = [
            l for l in raw
            if (not purpose or l.get("purpose") == purpose or l.get("purpose") is None)
            and (not max_budget or (l.get("price") is not None and l["price"] <= max_budget))
        ]
        start_idx = (page - 1) * PAGE_SIZE
        end_idx   = start_idx + PAGE_SIZE
        page_items = filtered[start_idx:end_idx]
        listings   = page_items
        total      = len(filtered)
        has_more   = end_idx < total

    if not listings:
        no_msg = f"📭 <b>No {item_type_label} found in {city_name}"
        if purpose_label:
            no_msg += f" {purpose_label}"
        no_msg += budget_label + ".</b>\n\n"
        no_msg += (
            "Try a higher budget or different search criteria.\n"
            "You can also 🔔 Subscribe to get notified when new ones arrive!"
            if max_budget else
            f"Listings will appear once they are added."
        )
        await msg.reply_html(no_msg, reply_markup=after_listings_menu(category))
        return

    is_premium = False
    try:
        from app.database import AsyncSessionLocal
        from app.models.subscriber import SubscriptionTier
        from app.services.subscriber_service import SubscriberService
        async with AsyncSessionLocal() as db:
            sub_service = SubscriberService(db)
            subscriber = await sub_service.get_by_telegram_id(msg.chat_id)
            if subscriber and subscriber.subscription_tier != SubscriptionTier.FREE:
                is_premium = True
    except Exception as e:
        log.warning("Could not check premium status for images: %s", e)

    from app.bot.formatters import format_listing_alert

    for item in listings:
        if isinstance(item, dict):
            # Mock data
            text = _format_mock_car(item) if category == "cars" else _format_mock(item)
            image_url = item.get("image_url")
            l_id = item.get("title", "mock")
        else:
            # DB model
            text = format_listing_alert(item)
            image_url = getattr(item, "image_url", None)
            l_id = getattr(item, "id", "db")

        if is_premium and image_url:
            try:
                await msg.reply_photo(photo=image_url, caption=text, parse_mode="HTML")
            except Exception as e:
                log.warning("Failed to send photo for listing %s: %s", l_id, e)
                await msg.reply_html(text, disable_web_page_preview=True)
        else:
            await msg.reply_html(text, disable_web_page_preview=True)

    shown = page * PAGE_SIZE
    if has_more:
        await msg.reply_html(
            f"📄 <b>Showing {min(shown, total)} of {total} {item_type_label_plural}.</b>\n"
            "Tap ⬇️ Load More to see the next 10.",
            reply_markup=load_more_menu(city_code, page + 1, purpose, max_budget or 0, category),
        )
    else:
        await msg.reply_html(
            f"✅ <b>All {total} {item_type_label_single if total == 1 else item_type_label_plural} shown.</b>\n"
            "Would you like to set up automatic alerts for new ones?",
            reply_markup=after_listings_menu(category),
        )



async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Bot error: %s", context.error)


async def _cancel_browse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(_KEY_CATEGORY, None) # type: ignore[union-attr]
    context.user_data.pop(_KEY_CITY, None)    # type: ignore[union-attr]
    context.user_data.pop(_KEY_PURPOSE, None) # type: ignore[union-attr]
    context.user_data.pop(_KEY_BUDGET, None)  # type: ignore[union-attr]
    await update.message.reply_html(
        "❌ Browse cancelled. Use /start to begin again.",
        reply_markup=start_category_menu(),
    )
    return ConversationHandler.END



# ── Application builder ───────────────────────────────────────────────────────
def build_app() -> Application:
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=20.0,
        read_timeout=15.0,
        write_timeout=10.0,
        pool_timeout=10.0,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )

    # Browse conversation: category → city → rent/buy → budget → listings
    browse_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_category_callback, pattern="^category:"),
        ],
        states={
            BROWSE_CITY: [
                CallbackQueryHandler(start_city_callback, pattern="^start_city:"),
                CallbackQueryHandler(back_to_categories_callback, pattern="^back_to_categories$"),
            ],
            BROWSE_PURPOSE: [
                CallbackQueryHandler(browse_purpose_callback, pattern="^browse_purpose:"),
                CallbackQueryHandler(back_to_cities_callback, pattern="^back_to_cities$"),
                CallbackQueryHandler(back_to_categories_callback, pattern="^back_to_categories$"),
            ],
            BROWSE_BUDGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, browse_budget_entered),
            ],
        },
        fallbacks=[
            CommandHandler("start",  start),
            CommandHandler("cancel", _cancel_browse),
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        name="browse_flow",
    )

    app.add_handler(browse_conv)
    app.add_handler(payment_conv_handler)
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("help",    help_cmd))
    app.add_handler(CommandHandler("cities",  cities_cmd))
    app.add_handler(CallbackQueryHandler(load_more_callback,      pattern="^load_more:"))
    app.add_handler(CallbackQueryHandler(back_to_cities_callback, pattern="^back_to_cities$"))
    app.add_handler(CallbackQueryHandler(back_to_categories_callback, pattern="^back_to_categories$"))
    app.add_handler(CallbackQueryHandler(menu_callback,           pattern="^menu:"))
    
    from app.bot.handlers.start import check_membership_callback_handler
    app.add_handler(CallbackQueryHandler(check_membership_callback_handler, pattern="^check_membership$"))
    
    app.add_error_handler(error_handler)


    return app


# ── Main with auto-reconnect loop ─────────────────────────────────────────────
def main() -> None:
    log.info("=" * 50)
    log.info("RealtorPal @RealtorpalBot starting...")
    log.info("Token: %s...", BOT_TOKEN[:20])
    log.info("=" * 50)

    backoff = 5
    attempts = 0

    while True:
        attempts += 1
        try:
            log.info("Connecting to Telegram (attempt #%d)...", attempts)
            app = build_app()
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                poll_interval=0.0,
                timeout=10,
            )
            log.info("Bot stopped cleanly.")
            break

        except KeyboardInterrupt:
            log.info("Stopped by user.")
            break

        except Exception as exc:
            log.error("Bot crashed: %s", exc)
            log.info("Restarting in %d seconds...", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    main()
