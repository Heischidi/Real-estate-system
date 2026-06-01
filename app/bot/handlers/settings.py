"""Settings and unsubscribe handlers."""

from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from app.logging_config import get_logger

log = get_logger(__name__)


async def my_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mysettings command."""
    user = update.effective_user
    if not user:
        return

    from app.bot.formatters import format_settings_summary
    from app.database import get_db_context
    from app.services.subscriber_service import SubscriberService

    async with get_db_context() as db:
        service = SubscriberService(db)
        subscriber = await service.get_by_telegram_id(user.id)

    if not subscriber:
        await update.message.reply_html(
            "❌ You're not subscribed yet.\n\nUse /subscribe to set up your alerts."
        )
        return

    summary = format_settings_summary(subscriber)
    await update.message.reply_html(summary)


async def unsubscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unsubscribe command."""
    user = update.effective_user
    if not user:
        return

    source = update.message or update.callback_query
    is_callback = update.callback_query is not None

    from app.database import get_db_context
    from app.services.subscriber_service import SubscriberService

    async with get_db_context() as db:
        service = SubscriberService(db)
        success = await service.deactivate(user.id)

    msg = (
        "✅ You've been <b>unsubscribed</b>. You won't receive any more alerts.\n\n"
        "Use /subscribe anytime to re-activate your alerts."
        if success
        else "❌ You're not currently subscribed."
    )

    if is_callback and update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg, parse_mode="HTML")
    else:
        await update.message.reply_html(msg)

    log.info("subscriber_unsubscribed", telegram_id=user.id, success=success)


async def settings_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle menu:settings callback."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not user:
        return

    from app.bot.formatters import format_settings_summary
    from app.database import get_db_context
    from app.services.subscriber_service import SubscriberService

    async with get_db_context() as db:
        service = SubscriberService(db)
        subscriber = await service.get_by_telegram_id(user.id)

    if not subscriber:
        await query.edit_message_text(
            "❌ You're not subscribed yet. Use /subscribe to get started.",
            parse_mode="HTML",
        )
        return

    await query.edit_message_text(
        format_settings_summary(subscriber),
        parse_mode="HTML",
    )
