"""Start and help command handlers for @RealtorpalBot."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu_keyboard
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
        "   📍 Abuja  •  📍 Lagos\n"
        "   📍 Port Harcourt  •  📍 Kano\n\n"
        "🏠  <b>Property types</b>\n"
        "   Apartments • Flats • Duplexes\n"
        "   Detached Houses • Terraces\n"
        "   Lands • Commercial\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "👇 <b>What would you like to do?</b>"
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
    "🌾 <b>Kano</b>\n"
    "   Largest city in northern Nigeria\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "📡 <i>Sources monitored: PropertyPro, Nigeria Property Centre,\n"
    "PrivateProperty & Property24</i>\n\n"
    "<i>More cities coming soon! Use /subscribe to get started.</i>"
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — sends a personalised welcome message with the main menu."""
    user = update.effective_user
    first_name = user.first_name if user and user.first_name else "there"
    log.info("bot_start", telegram_id=user.id if user else None, first_name=first_name)

    await update.message.reply_html(
        _build_welcome(first_name),
        reply_markup=main_menu_keyboard(),
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_html(HELP_MESSAGE)


async def cities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cities command."""
    await update.message.reply_html(CITIES_MESSAGE)
