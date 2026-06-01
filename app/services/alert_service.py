"""Alert service — matches listings to subscribers and sends Telegram alerts."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.listing import Listing
from app.models.notification import Notification
from app.models.subscriber import Subscriber

log = get_logger(__name__)


class AlertService:
    """Orchestrates matching new listings to subscribers and recording alerts."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def has_been_notified(
        self, subscriber_id: uuid.UUID, listing_id: uuid.UUID
    ) -> bool:
        """Return True if this subscriber already received an alert for this listing."""
        stmt = select(Notification).where(
            Notification.subscriber_id == subscriber_id,
            Notification.listing_id == listing_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def record_notification(
        self, subscriber_id: uuid.UUID, listing_id: uuid.UUID
    ) -> Notification:
        """Persist a notification record to prevent re-sending."""
        notification = Notification(
            id=uuid.uuid4(),
            subscriber_id=subscriber_id,
            listing_id=listing_id,
        )
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def delete_old_notifications(self, older_than_days: int) -> int:
        """Clean up old notification logs. Returns deleted count."""
        from sqlalchemy import delete

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=older_than_days)
        stmt = delete(Notification).where(Notification.sent_at < cutoff)
        result = await self.db.execute(stmt)
        deleted: int = result.rowcount
        log.info("notifications_cleaned", deleted=deleted, older_than_days=older_than_days)
        return deleted

    async def total_notifications_count(self) -> int:
        stmt = select(func.count(Notification.id))
        return (await self.db.execute(stmt)).scalar_one()

    async def get_recent_notifications(
        self, limit: int = 100
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .order_by(Notification.sent_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
