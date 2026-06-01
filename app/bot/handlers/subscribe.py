"""Multi-step subscription ConversationHandler."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.keyboards import city_keyboard, confirm_keyboard, property_type_keyboard
from app.logging_config import get_logger

log = get_logger(__name__)

# Conversation states
CHOOSE_CITY, CHOOSE_TYPE, ENTER_MIN_PRICE, ENTER_MAX_PRICE, CONFIRM = range(5)

# User data keys
KEY_CITY = "sub_city"
KEY_TYPE = "sub_type"
KEY_MIN = "sub_min"
KEY_MAX = "sub_max"


async def subscribe_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point — ask user to select city."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📍 <b>Step 1 of 4</b> — Choose your city:",
            reply_markup=city_keyboard(),
            parse_mode="HTML",
        )
    else:
        await update.message.reply_html(
            "📍 <b>Step 1 of 4</b> — Choose your city:",
            reply_markup=city_keyboard(),
        )
    return CHOOSE_CITY


async def city_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle city selection."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data == "cancel":
        await query.edit_message_text("❌ Subscription cancelled.")
        return ConversationHandler.END

    city = data.split(":")[1]
    context.user_data[KEY_CITY] = city  # type: ignore[index]

    await query.edit_message_text(
        "🏠 <b>Step 2 of 4</b> — Choose property type:",
        reply_markup=property_type_keyboard(),
        parse_mode="HTML",
    )
    return CHOOSE_TYPE


async def type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle property type selection."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data == "cancel":
        await query.edit_message_text("❌ Subscription cancelled.")
        return ConversationHandler.END

    prop_type = data.split(":")[1]
    context.user_data[KEY_TYPE] = None if prop_type == "any" else prop_type  # type: ignore[index]

    await query.edit_message_text(
        "💵 <b>Step 3 of 4</b> — Enter your <b>minimum budget</b> in Naira.\n\n"
        "Example: <code>5000000</code> for ₦5M\n"
        "Type <code>0</code> for no minimum.",
        parse_mode="HTML",
    )
    return ENTER_MIN_PRICE


async def min_price_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle minimum price input."""
    text = (update.message.text or "").strip()
    try:
        amount = int(text.replace(",", "").replace("₦", "").strip())
        if amount < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a valid number (e.g. 5000000). Try again:"
        )
        return ENTER_MIN_PRICE

    context.user_data[KEY_MIN] = amount if amount > 0 else None  # type: ignore[index]
    await update.message.reply_html(
        "💵 <b>Step 4 of 4</b> — Enter your <b>maximum budget</b> in Naira.\n\n"
        "Example: <code>80000000</code> for ₦80M\n"
        "Type <code>0</code> for no maximum."
    )
    return ENTER_MAX_PRICE


async def max_price_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle maximum price input and show confirmation."""
    text = (update.message.text or "").strip()
    try:
        amount = int(text.replace(",", "").replace("₦", "").strip())
        if amount < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a valid number (e.g. 80000000). Try again:"
        )
        return ENTER_MAX_PRICE

    context.user_data[KEY_MAX] = amount if amount > 0 else None  # type: ignore[index]

    # Format confirmation summary
    from app.bot.formatters import format_price

    city = str(context.user_data.get(KEY_CITY, "")).replace("_", " ").title()  # type: ignore[index]
    prop_type_raw = context.user_data.get(KEY_TYPE)  # type: ignore[index]
    prop_type = str(prop_type_raw).replace("_", " ").title() if prop_type_raw else "Any"
    min_p = context.user_data.get(KEY_MIN)  # type: ignore[index]
    max_p = context.user_data.get(KEY_MAX)  # type: ignore[index]

    summary = (
        f"✅ <b>Confirm your preferences:</b>\n\n"
        f"🏙️ City: <b>{city}</b>\n"
        f"🏠 Type: <b>{prop_type}</b>\n"
        f"💵 Min: <b>{format_price(min_p) if min_p else 'None'}</b>\n"
        f"💵 Max: <b>{format_price(max_p) if max_p else 'None'}</b>"
    )

    await update.message.reply_html(summary, reply_markup=confirm_keyboard())
    return CONFIRM


async def confirm_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save subscription preferences to the database."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data == "confirm:no":
        await query.edit_message_text("✏️ Let's start over. Use /subscribe to try again.")
        return ConversationHandler.END

    # Save to database
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    from app.database import get_db_context
    from app.models.listing import City, PropertyType
    from app.schemas.subscriber import SubscriberCreate
    from app.services.subscriber_service import SubscriberService

    city_val = context.user_data.get(KEY_CITY)  # type: ignore[index]
    type_val = context.user_data.get(KEY_TYPE)  # type: ignore[index]

    city_enum = City(city_val) if city_val else None
    type_enum = PropertyType(type_val) if type_val else None

    subscriber_data = SubscriberCreate(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name or "User",
        city=city_enum,
        min_price=context.user_data.get(KEY_MIN),  # type: ignore[index]
        max_price=context.user_data.get(KEY_MAX),  # type: ignore[index]
        property_type=type_enum,
        active=True,
    )

    async with get_db_context() as db:
        service = SubscriberService(db)
        _, is_new = await service.create_or_update(subscriber_data)

    action = "created" if is_new else "updated"
    await query.edit_message_text(
        f"🎉 <b>Subscription {action}!</b>\n\n"
        "You'll receive instant alerts when matching properties are found.\n\n"
        "Use /mysettings to review, or /unsubscribe to stop alerts.",
        parse_mode="HTML",
    )

    log.info("subscriber_subscribed", telegram_id=user.id, is_new=is_new)
    context.user_data.clear()  # type: ignore[union-attr]
    return ConversationHandler.END


async def cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the subscription flow."""
    await update.message.reply_text("❌ Subscription flow cancelled. Use /subscribe to try again.")
    context.user_data.clear()  # type: ignore[union-attr]
    return ConversationHandler.END


def build_subscribe_handler() -> ConversationHandler:
    """Build and return the subscribe ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("subscribe", subscribe_start),
            CallbackQueryHandler(subscribe_start, pattern="^menu:subscribe$"),
        ],
        states={
            CHOOSE_CITY: [
                CallbackQueryHandler(city_chosen, pattern="^city:"),
                CallbackQueryHandler(cancel_subscription, pattern="^cancel$"),
            ],
            CHOOSE_TYPE: [
                CallbackQueryHandler(type_chosen, pattern="^type:"),
                CallbackQueryHandler(cancel_subscription, pattern="^cancel$"),
            ],
            ENTER_MIN_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, min_price_entered)
            ],
            ENTER_MAX_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, max_price_entered)
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_subscription, pattern="^confirm:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_subscription)],
        allow_reentry=True,
        per_user=True,
    )
