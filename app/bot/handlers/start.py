"""Start and help command handlers for @RealtorpalBot.

Browse flow (new):
  /start → select city → rent or buy? → enter max budget → view listings
"""

from __future__ import annotations
import html
import re

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.keyboards import (
    after_listings_keyboard,
    load_more_keyboard,
    rent_or_buy_keyboard,
    start_city_keyboard,
)
from app.logging_config import get_logger

log = get_logger(__name__)

# ── Conversation states for the browse flow ───────────────────────────────────
BROWSE_PURPOSE, BROWSE_BUDGET = range(10, 12)   # 10, 11 (no clash with subscribe's 0-4)

# user_data keys
_KEY_CITY    = "browse_city"
_KEY_PURPOSE = "browse_purpose"
_KEY_BUDGET  = "browse_budget"


# ── Static messages ───────────────────────────────────────────────────────────
def _build_welcome(first_name: str) -> str:
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


# ── Helpers ───────────────────────────────────────────────────────────────────
CITY_DISPLAY = {
    "abuja":        ("Abuja",        "abuja"),
    "lagos":        ("Lagos",        "lagos"),
    "port_harcourt":("Port Harcourt","port harcourt"),
}


def _parse_budget(text: str) -> int | None:
    """Parse a budget string entered by the user.

    Supports:
        0 / skip / no  → None (no cap)
        3000000        → 3_000_000
        3m / 3M        → 3_000_000
        3.5m           → 3_500_000
        500k / 500K    → 500_000
    Returns the integer amount, or None for "no limit".
    """
    text = text.strip().lower().replace(",", "").replace("₦", "")
    if text in ("0", "skip", "no", "none", "any"):
        return None

    multiplier = 1
    if text.endswith("m"):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.endswith("k"):
        multiplier = 1_000
        text = text[:-1]

    try:
        return int(float(text) * multiplier)
    except (ValueError, OverflowError):
        return -1   # sentinel: invalid input


# ── Step 1 — /start ───────────────────────────────────────────────────────────
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — sends a personalised welcome with the city selector."""
    user = update.effective_user
    first_name = user.first_name if user and user.first_name else "there"
    log.info("bot_start", telegram_id=user.id if user else None, first_name=first_name)
    await update.message.reply_html(
        _build_welcome(first_name),
        reply_markup=start_city_keyboard(),
    )


# ── Step 2 — City selected → ask Rent or Buy ──────────────────────────────────
async def start_city_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """City button tapped — store city, ask Rent or Buy."""
    query = update.callback_query
    await query.answer()

    city_code = (query.data or "").replace("start_city:", "").lower()
    context.user_data[_KEY_CITY] = city_code  # type: ignore[index]

    city_name, _ = CITY_DISPLAY.get(city_code, (city_code.replace("_", " ").title(), city_code))

    await query.message.reply_html(
        f"🏙️ <b>{city_name}</b> selected!\n\n"
        "Are you looking to <b>Rent</b> or <b>Buy</b> a property?",
        reply_markup=rent_or_buy_keyboard(city_code),
    )
    return BROWSE_PURPOSE


# ── Step 3 — Rent/Buy chosen → ask budget ─────────────────────────────────────
async def browse_purpose_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Rent/Buy button tapped — store purpose, ask for max budget."""
    query = update.callback_query
    await query.answer()

    # callback_data: browse_purpose:{city_code}:{purpose}
    parts = (query.data or "").split(":")
    if len(parts) < 3:
        return ConversationHandler.END

    city_code = parts[1]
    purpose   = parts[2]   # "rent" or "sale"
    context.user_data[_KEY_CITY]    = city_code  # type: ignore[index]
    context.user_data[_KEY_PURPOSE] = purpose    # type: ignore[index]

    purpose_label = "🔑 Rent" if purpose == "rent" else "🏠 Buy"

    await query.message.reply_html(
        f"{purpose_label} — got it!\n\n"
        "💰 <b>What is your maximum budget?</b>\n\n"
        "Enter an amount in Naira, for example:\n"
        "  • <code>3000000</code> for ₦3M\n"
        "  • <code>3m</code> for ₦3M\n"
        "  • <code>500k</code> for ₦500K\n\n"
        "Type <code>0</code> or <code>skip</code> to see <b>all</b> properties with no budget cap."
    )
    return BROWSE_BUDGET


# ── Step 4 — Budget entered → fetch & display listings ───────────────────────
async def browse_budget_entered(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """User typed a budget — parse it, run the query, send listings."""
    text = update.message.text or ""
    budget = _parse_budget(text)

    if budget == -1:
        await update.message.reply_text(
            "⚠️ I didn't understand that amount. Please try again.\n"
            "Examples: <code>3000000</code>, <code>3m</code>, <code>500k</code>, <code>0</code>",
            parse_mode="HTML",
        )
        return BROWSE_BUDGET

    context.user_data[_KEY_BUDGET] = budget  # type: ignore[index]

    city_code = context.user_data.get(_KEY_CITY, "")  # type: ignore[index]
    purpose   = context.user_data.get(_KEY_PURPOSE, "")  # type: ignore[index]

    await _send_city_listings(
        message=update.message,
        city_code=city_code,
        purpose=purpose,
        max_budget=budget,
        page=1,
    )
    return ConversationHandler.END


# ── Load More ─────────────────────────────────────────────────────────────────
async def load_more_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle Load More button — sends the next page with same filters."""
    query = update.callback_query
    await query.answer()

    # callback_data: load_more:{city_code}:{page}:{purpose}:{max_budget}
    parts = (query.data or "").split(":")
    if len(parts) < 3:
        return

    city_code  = parts[1]
    try:
        page = int(parts[2])
    except ValueError:
        return

    # Check premium status if loading beyond page 1
    if page > 1:
        from app.database import AsyncSessionLocal
        from app.models.subscriber import SubscriptionTier
        from app.services.subscriber_service import SubscriberService
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        async with AsyncSessionLocal() as db:
            sub_service = SubscriberService(db)
            subscriber = await sub_service.get_by_telegram_id(update.effective_user.id)
            
            is_free = True
            if subscriber and subscriber.subscription_tier != SubscriptionTier.FREE:
                is_free = False
                
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
        max_budget = int(parts[4]) if len(parts) > 4 and parts[4] else 0
    except ValueError:
        max_budget = 0

    await _send_city_listings(
        message=query.message,
        city_code=city_code,
        purpose=purpose,
        max_budget=max_budget if max_budget > 0 else None,
        page=page,
    )


# ── Core listing fetcher ──────────────────────────────────────────────────────
async def _send_city_listings(
    message: object,
    city_code: str,
    purpose: str,
    max_budget: int | None,
    page: int,
) -> None:
    """Fetch and send up to 10 listings for `city_code` with filters applied."""
    import asyncio
    from telegram import Message

    msg: Message = message  # type: ignore[assignment]

    city_name, location_kw = CITY_DISPLAY.get(
        city_code, (city_code.replace("_", " ").title(), city_code)
    )
    purpose_label = "for rent" if purpose == "rent" else "for sale" if purpose == "sale" else ""
    budget_label  = (
        f" within ₦{max_budget:,.0f}" if max_budget else ""
    )

    if page == 1:
        summary = f"🔍 <b>Fetching properties in {city_name}</b>"
        if purpose_label:
            summary += f" {purpose_label}"
        if budget_label:
            summary += budget_label
        summary += "..."
        await msg.reply_html(summary)

    from app.database import get_db_context
    from app.models.listing import City, ListingPurpose
    from app.schemas.listing import ListingFilter
    from app.services.listing_service import ListingService
    from app.bot.formatters import format_listing_alert

    PAGE_SIZE = 10

    async def _fetch() -> object:
        async with get_db_context() as db:
            service = ListingService(db)
            purpose_enum = (
                ListingPurpose(purpose) if purpose in ("rent", "sale") else None
            )
            filters = ListingFilter(
                city=City(city_code),
                location_keyword=location_kw,
                listing_purpose=purpose_enum,
                max_price=max_budget,
                page=page,
                page_size=PAGE_SIZE,
            )
            return await service.list_listings(filters)

    try:
        paginated = await asyncio.wait_for(_fetch(), timeout=20.0)
        listings  = paginated.items
        total     = paginated.total
        has_more  = (page * PAGE_SIZE) < total

        if not listings:
            no_result_msg = (
                f"📭 <b>No properties found in {city_name}"
            )
            if purpose_label:
                no_result_msg += f" {purpose_label}"
            if budget_label:
                no_result_msg += budget_label
            no_result_msg += ".</b>\n\n"
            if max_budget:
                no_result_msg += (
                    "Try a higher budget or select a different city.\n"
                    "You can also tap 🔔 Subscribe to get alerts when new ones arrive!"
                )
            else:
                no_result_msg += "Properties will appear once they are added by the admin."
            await msg.reply_html(no_result_msg, reply_markup=after_listings_keyboard())
            return

        for listing in listings:
            await msg.reply_html(
                format_listing_alert(listing), disable_web_page_preview=True
            )

        shown_so_far = page * PAGE_SIZE
        if has_more:
            await msg.reply_html(
                f"📄 <b>Showing {min(shown_so_far, total)} of {total} properties.</b>\n"
                "Tap ⬇️ Load More to see the next 10.",
                reply_markup=load_more_keyboard(
                    city_code,
                    page + 1,
                    purpose=purpose,
                    max_budget=max_budget or 0,
                ),
            )
        else:
            await msg.reply_html(
                f"✅ <b>All {total} propert{'y' if total == 1 else 'ies'} shown.</b>\n"
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


# ── Back to cities ────────────────────────────────────────────────────────────
async def back_to_cities_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle back-to-cities button."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    first_name = user.first_name if user and user.first_name else "there"

    await query.edit_message_text(
        _build_welcome(first_name),
        reply_markup=start_city_keyboard(),
        parse_mode="HTML",
    )


# ── Static command handlers ───────────────────────────────────────────────────
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_html(HELP_MESSAGE)


async def cities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cities command."""
    await update.message.reply_html(CITIES_MESSAGE)


# ── ConversationHandler builder ───────────────────────────────────────────────
def build_browse_handler() -> ConversationHandler:
    """Build the ConversationHandler for the city-browse flow.

    Flow: city selected → Rent/Buy? → budget input → listings shown
    """
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                start_city_callback_handler, pattern=r"^start_city:"
            ),
        ],
        states={
            BROWSE_PURPOSE: [
                CallbackQueryHandler(
                    browse_purpose_callback_handler, pattern=r"^browse_purpose:"
                ),
                CallbackQueryHandler(
                    back_to_cities_callback_handler, pattern=r"^back_to_cities$"
                ),
            ],
            BROWSE_BUDGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, browse_budget_entered),
            ],
        },
        fallbacks=[
            CommandHandler("start", start_handler),
            CommandHandler("cancel", _cancel_browse),
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        name="browse_flow",
    )


async def _cancel_browse(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel the browse conversation."""
    context.user_data.pop(_KEY_CITY, None)     # type: ignore[union-attr]
    context.user_data.pop(_KEY_PURPOSE, None)  # type: ignore[union-attr]
    context.user_data.pop(_KEY_BUDGET, None)   # type: ignore[union-attr]
    await update.message.reply_html(
        "❌ Browse cancelled. Use /start to begin again.",
        reply_markup=start_city_keyboard(),
    )
    return ConversationHandler.END
