"""Start and help command handlers for @RealtorpalBot."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import start_city_keyboard, after_listings_keyboard
from app.logging_config import get_logger

log = get_logger(__name__)


def _build_welcome(first_name: str) -> str:
    """Build a personalised welcome message for the given user's first name."""
    return (
        f"🏡 <b>Hey {first_name}, welcome to RealtorPal!</b>\n\n"
        "I'm your personal Nigerian property scout. 🇳🇬\n"
        "I watch multiple real estate websites around the clock and "
        "ping you the moment a property matching your budget and preferences "
        "goes live — so you never miss a deal again.\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "🏙️  <b>Cities I cover</b>\n"
        "   📍 Abuja  •  📍 Lagos  •  📍 Port Harcourt\n\n"
        "🏠  <b>Property types</b>\n"
        "   Apartments • Flats • Duplexes\n"
        "   Detached Houses • Terraces\n"
        "   Lands • Commercial\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "👇 <b>Select a city below to view the latest 5 listings:</b>"
    )


HELP_MESSAGE = (
    "📖 <b>RealtorPal Commands</b>\n\n"
    "🔔 /subscribe — Set up your property alerts\n"
    "⚙️ /mysettings — View your current preferences\n"
    "🔕 /unsubscribe — Stop receiving alerts\n"
    "🏙️ /cities — List supported cities\n"
    "❓ /help — Show this help message\n"
    "🏠 /start — Show the main menu\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "💡 <b>How it works:</b>\n"
    "1️⃣  Use /subscribe to pick your city, property type & budget\n"
    "2️⃣  Sit back — I'll scan the web every 15 minutes\n"
    "3️⃣  Get instant alerts when matching properties appear\n\n"
    "<i>Use /subscribe anytime to update your preferences.</i>"
)


CITIES_MESSAGE = (
    "🗺️ <b>Cities RealtorPal Monitors</b>\n\n"
    "🏛️ <b>Abuja</b>\n"
    "   Federal Capital Territory\n\n"
    "🌊 <b>Lagos</b>\n"
    "   Nigeria's commercial & financial hub\n\n"
    "⚓ <b>Port Harcourt</b>\n"
    "   Rivers State capital & oil city\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "📡 <i>Sources monitored: PropertyPro, Nigeria Property Centre,\n"
    "PrivateProperty & Property24</i>\n\n"
    "<i>More cities coming soon! Use /subscribe to get started.</i>"
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — sends a personalised welcome message with the city selector."""
    user = update.effective_user
    first_name = user.first_name if user and user.first_name else "there"
    log.info("bot_start", telegram_id=user.id if user else None, first_name=first_name)

    await update.message.reply_html(
        _build_welcome(first_name),
        reply_markup=start_city_keyboard(),
    )


async def start_city_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle city selection from start page — queries last 5 listings."""
    import asyncio

    query = update.callback_query
    await query.answer()

    city_code = (query.data or "").replace("start_city:", "")
    city_name = city_code.replace("_", " ").title()

    await query.message.reply_html(f"🔍 <b>Fetching the latest 5 properties in {city_name}...</b>")

    from app.database import get_db_context
    from app.models.listing import City
    from app.schemas.listing import ListingFilter
    from app.services.listing_service import ListingService
    from app.bot.formatters import format_listing_alert

    async def _fetch() -> list:
        async with get_db_context() as db:
            service = ListingService(db)
            filters = ListingFilter(city=City(city_code), page=1, page_size=5)
            paginated = await service.list_listings(filters)
            return paginated.items

    try:
        # 20-second timeout so the bot never hangs silently
        listings = await asyncio.wait_for(_fetch(), timeout=20.0)

        if not listings:
            await query.message.reply_html(
                f"📭 <b>No listings found for {city_name} yet.</b>\n\n"
                "The scraper hasn't run yet. Listings will appear automatically "
                "within the next 15 minutes once the worker processes the first scrape cycle.",
                reply_markup=after_listings_keyboard()
            )
            return

        for listing in listings:
            msg = format_listing_alert(listing)
            await query.message.reply_html(msg, disable_web_page_preview=True)

        await query.message.reply_html(
            f"💡 These are the 5 latest properties in <b>{city_name}</b>.\n"
            "Would you like to set up automatic alerts for new ones?",
            reply_markup=after_listings_keyboard()
        )

    except asyncio.TimeoutError:
        log.error("start_city_db_timeout", city=city_code)
        await query.message.reply_html(
            "⏱️ <b>Request timed out.</b>\n\n"
            "The database is taking too long to respond. Please try again in a moment.",
            reply_markup=after_listings_keyboard()
        )
    except Exception as e:
        log.exception("error_fetching_start_listings")
        await query.message.reply_html(
            f"❌ An error occurred while fetching properties: {e}",
            reply_markup=after_listings_keyboard()
        )


async def back_to_cities_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle back to cities button."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    first_name = user.first_name if user and user.first_name else "there"

    await query.edit_message_text(
        _build_welcome(first_name),
        reply_markup=start_city_keyboard(),
        parse_mode="HTML"
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_html(HELP_MESSAGE)


async def cities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cities command."""
    await update.message.reply_html(CITIES_MESSAGE)
