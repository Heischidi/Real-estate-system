"""Celery alert tasks — match new listings to subscribers and send Telegram messages."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.killswitch import SYSTEM_PAUSED
from app.logging_config import get_logger
from app.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(
    name="app.tasks.alerts.process_new_listings",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_new_listings(self: object, since_iso: str) -> dict[str, object]:
    """Find new listings since `since_iso` and dispatch alerts to matching subscribers."""
    if SYSTEM_PAUSED:
        log.info("process_new_listings skipped — system is paused.")
        return {"sent": 0, "skipped": 0, "paused": True}
    return asyncio.run(_async_process_alerts(since_iso))


async def _async_process_alerts(since_iso: str) -> dict[str, object]:
    from datetime import datetime

    from app.database import get_db_context
    from app.services.alert_service import AlertService
    from app.services.listing_service import ListingService
    from app.services.subscriber_service import SubscriberService

    since = datetime.fromisoformat(since_iso)
    alerts_sent = 0
    alerts_skipped = 0

    async with get_db_context() as db:
        listing_service = ListingService(db)
        subscriber_service = SubscriberService(db)
        alert_service = AlertService(db)

        new_listings = await listing_service.get_new_listings_since(since)
        log.info("alert_processing_started", listing_count=len(new_listings))

        for listing in new_listings:
            matching_subs = await subscriber_service.get_matching_subscribers(
                city=listing.city,
                price=listing.price,
                property_type=listing.property_type,
            )

            for subscriber in matching_subs:
                already_notified = await alert_service.has_been_notified(
                    subscriber.id, listing.id
                )
                if already_notified:
                    alerts_skipped += 1
                    continue

                # Dispatch individual send task
                send_telegram_alert.apply_async(
                    kwargs={
                        "telegram_id": subscriber.telegram_id,
                        "listing_id": str(listing.id),
                        "subscriber_id": str(subscriber.id),
                    },
                    queue="alerts",
                )
                alerts_sent += 1

    log.info("alert_processing_done", sent=alerts_sent, skipped=alerts_skipped)
    return {"sent": alerts_sent, "skipped": alerts_skipped}


@celery_app.task(
    name="app.tasks.alerts.send_telegram_alert",
    bind=True,
    max_retries=5,
    default_retry_delay=10,
)
def send_telegram_alert(
    self: object,
    telegram_id: int,
    listing_id: str,
    subscriber_id: str,
) -> dict[str, object]:
    """Send a single Telegram alert message and record the notification."""
    if SYSTEM_PAUSED:
        log.info("send_telegram_alert skipped — system is paused.")
        return {"status": "paused"}
    return asyncio.run(_async_send_alert(telegram_id, listing_id, subscriber_id))


async def _async_send_alert(
    telegram_id: int, listing_id: str, subscriber_id: str
) -> dict[str, object]:
    import uuid

    from telegram import Bot
    from telegram.error import TelegramError

    from app.bot.formatters import format_listing_alert
    from app.config import get_settings
    from app.database import get_db_context
    from app.services.alert_service import AlertService
    from app.services.listing_service import ListingService

    settings = get_settings()

    async with get_db_context() as db:
        listing_service = ListingService(db)
        alert_service = AlertService(db)

        listing = await listing_service.get_by_id(uuid.UUID(listing_id))
        if not listing:
            log.warning("alert_listing_not_found", listing_id=listing_id)
            return {"status": "skipped", "reason": "listing_not_found"}

        message_text = format_listing_alert(listing)

        try:
            bot = Bot(token=settings.telegram_bot_token)
            await bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )

            await alert_service.record_notification(
                subscriber_id=uuid.UUID(subscriber_id),
                listing_id=uuid.UUID(listing_id),
            )

            log.info(
                "alert_sent",
                telegram_id=telegram_id,
                listing_id=listing_id,
            )
            return {"status": "sent"}

        except TelegramError as exc:
            log.error(
                "telegram_send_failed",
                telegram_id=telegram_id,
                error=str(exc),
            )
            raise
