"""Telegram bot entry point — builds and runs the Application."""

from __future__ import annotations

import asyncio
import sys
import traceback

from telegram import Update
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.bot.handlers.settings import (
    my_settings_handler,
    settings_callback_handler,
    unsubscribe_handler,
)
from app.bot.handlers.start import (
    cities_handler,
    help_handler,
    start_handler,
    load_more_callback_handler,
    back_to_cities_callback_handler,
    build_browse_handler,
    check_membership_callback_handler,
)
from app.bot.handlers.subscribe import build_subscribe_handler
from app.bot.handlers.payment import payment_conv_handler
from app.config import get_settings
from app.logging_config import get_logger, setup_logging

log = get_logger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors; silently ignore Conflict (rolling-deploy overlap)."""
    if isinstance(context.error, Conflict):
        # Two instances briefly overlap during Railway rolling deploys — not an error
        log.warning("bot_conflict_ignored", detail=str(context.error))
        return
    print("=== BOT EXCEPTION START ===", file=sys.stderr)
    traceback.print_exception(None, context.error, context.error.__traceback__, file=sys.stderr)
    print("=== BOT EXCEPTION END ===", file=sys.stderr)


def build_application() -> Application:
    """Build the Telegram Application with all handlers registered."""
    settings = get_settings()
    setup_logging(log_level="INFO", json_logs=settings.is_production)

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # Register error handler
    app.add_error_handler(error_handler)

    # Subscription conversation (must be first — handles /subscribe and menu:subscribe)
    app.add_handler(build_subscribe_handler())

    # Browse conversation: city → rent/buy → budget → listings
    # Must be registered before the bare back_to_cities callback handler.
    app.add_handler(build_browse_handler())
    
    # Payment conversation
    app.add_handler(payment_conv_handler)

    # Basic commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("cities", cities_handler))
    app.add_handler(CommandHandler("mysettings", my_settings_handler))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_handler))

    # Standalone callbacks (outside conversations)
    app.add_handler(
        CallbackQueryHandler(check_membership_callback_handler, pattern="^check_membership$")
    )
    app.add_handler(
        CallbackQueryHandler(load_more_callback_handler, pattern="^load_more:")
    )
    app.add_handler(
        CallbackQueryHandler(back_to_cities_callback_handler, pattern="^back_to_cities$")
    )
    app.add_handler(
        CallbackQueryHandler(settings_callback_handler, pattern="^menu:settings$")
    )
    app.add_handler(
        CallbackQueryHandler(unsubscribe_handler, pattern="^menu:unsubscribe$")
    )
    app.add_handler(
        CallbackQueryHandler(cities_handler, pattern="^menu:cities$")
    )

    return app


def main() -> None:
    """Run the bot with long-polling."""
    log.info("telegram_bot_starting")
    # Small delay so Railway's old container can finish shutting down before we
    # start polling — prevents the Conflict error on rolling deploys.
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(3))
    app = build_application()
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()

