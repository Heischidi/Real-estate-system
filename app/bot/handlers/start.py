"""Start and help command handlers for @RealtorpalBot."""

from __future__ import annotations
import html

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import start_city_keyboard, after_listings_keyboard, load_more_keyboard
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
        "👇 <b>Select a city below to view available properties:</b>"
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
    """Handle city selection from start page — queries listings page 1."""
    query = update.callback_query
    await query.answer()

    city_code = (query.data or "").replace("start_city:", "").lower()
    await _send_city_listings(query.message, city_code, page=1)


async def load_more_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Load More button — sends the next page of listings."""
    query = update.callback_query
    await query.answer()

    # callback_data format: load_more:{city_code}:{page}
    parts = (query.data or "").split(":")
    if len(parts) < 3:
        return
    city_code = parts[1]
    try:
        page = int(parts[2])
    except ValueError:
        return

    await _send_city_listings(query.message, city_code, page=page)


async def _send_city_listings(message: object, city_code: str, page: int) -> None:
    """Fetch and send up to 10 listings for `city_code` at `page`."""
    import asyncio
    from telegram import Message

    msg: Message = message  # type: ignore[assignment]

    # Map city code → human-readable name and location keyword for the secondary filter
    CITY_DISPLAY_NAMES = {
        "abuja": ("Abuja", "abuja"),
        "lagos": ("Lagos", "lagos"),
        "port_harcourt": ("Port Harcourt", "port harcourt"),
    }
    city_name, location_kw = CITY_DISPLAY_NAMES.get(city_code, (city_code.replace("_", " ").title(), city_code))

    if page == 1:
        await msg.reply_html(f"🔍 <b>Fetching properties in {city_name}...</b>")

    from app.database import get_db_context
    from app.models.listing import City
    from app.schemas.listing import ListingFilter
    from app.services.listing_service import ListingService
    from app.bot.formatters import format_listing_alert

    PAGE_SIZE = 10

    async def _fetch() -> object:
        async with get_db_context() as db:
            service = ListingService(db)
            filters = ListingFilter(
                city=City(city_code),
                location_keyword=location_kw,
                page=page,
                page_size=PAGE_SIZE,
            )
            return await service.list_listings(filters)

    try:
        paginated = await asyncio.wait_for(_fetch(), timeout=20.0)
        listings = paginated.items
        total = paginated.total
        has_more = (page * PAGE_SIZE) < total

        if not listings:
            if page == 1:
                await msg.reply_html(
                    f"📭 <b>No properties found for {city_name} yet.</b>\n\n"
                    "Properties will appear automatically once they are added by the admin.",
                    reply_markup=after_listings_keyboard(),
                )
            else:
                await msg.reply_html(
                    f"✅ <b>That's all the properties in {city_name}!</b>",
                    reply_markup=after_listings_keyboard(),
                )
            return

        for listing in listings:
            msg_text = format_listing_alert(listing)
            await msg.reply_html(msg_text, disable_web_page_preview=True)

        shown_so_far = page * PAGE_SIZE
        if has_more:
            await msg.reply_html(
                f"📄 <b>Showing {min(shown_so_far, total)} of {total} properties in {city_name}.</b>\n"
                "Tap ⬇️ Load More to see the next 10.",
                reply_markup=load_more_keyboard(city_code, page + 1),
            )
        else:
            await msg.reply_html(
                f"✅ <b>All {total} propert{'y' if total == 1 else 'ies'} in {city_name} shown.</b>\n"
                "Would you like to set up automatic alerts for new ones?",
                reply_markup=after_listings_keyboard(),
            )

    except asyncio.TimeoutError:
        log.error("start_city_db_timeout", city=city_code, page=page)
        await msg.reply_html(
            "⏱️ <b>Request timed out.</b>\n\n"
            "The database is taking too long to respond. Please try again in a moment.",
            reply_markup=after_listings_keyboard(),
        )
    except Exception as e:
        log.exception("error_fetching_start_listings")
        await msg.reply_html(
            f"❌ <b>An error occurred while fetching properties.</b>\n"
            f"<code>{html.escape(str(e))}</code>",
            reply_markup=after_listings_keyboard(),
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
