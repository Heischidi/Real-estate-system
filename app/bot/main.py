"""Telegram bot entry point — builds and runs the Application."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
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
    start_city_callback_handler,
    back_to_cities_callback_handler,
)
from app.bot.handlers.subscribe import build_subscribe_handler
from app.config import get_settings
from app.logging_config import get_logger, setup_logging

log = get_logger(__name__)


def build_application() -> Application:
    """Build the Telegram Application with all handlers registered."""
    settings = get_settings()
    setup_logging(log_level="INFO", json_logs=settings.is_production)

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # Subscription conversation (must be first — handles /subscribe and menu:subscribe)
    app.add_handler(build_subscribe_handler())

    # Basic commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("cities", cities_handler))
    app.add_handler(CommandHandler("mysettings", my_settings_handler))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_handler))

    # Inline keyboard menu callbacks
    app.add_handler(
        CallbackQueryHandler(start_city_callback_handler, pattern="^start_city:")
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
    app = build_application()
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
