"""Subscriber service — database operations for subscribers."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.listing import City, PropertyType
from app.models.subscriber import Subscriber
from app.schemas.subscriber import SubscriberCreate, SubscriberUpdate

log = get_logger(__name__)


class SubscriberService:
    """All database interactions for the Subscriber model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_telegram_id(self, telegram_id: int) -> Subscriber | None:
        stmt = select(Subscriber).where(Subscriber.telegram_id == telegram_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, subscriber_id: uuid.UUID) -> Subscriber | None:
        stmt = select(Subscriber).where(Subscriber.id == subscriber_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update(self, data: SubscriberCreate) -> tuple[Subscriber, bool]:
        """
        Create a new subscriber or update an existing one (upsert by telegram_id).

        Returns:
            (subscriber, is_new)
        """
        existing = await self.get_by_telegram_id(data.telegram_id)
        if existing:
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(existing, field, value)
            await self.db.flush()
            log.info("subscriber_updated", telegram_id=data.telegram_id)
            return existing, False

        subscriber = Subscriber(**data.model_dump())
        self.db.add(subscriber)
        await self.db.flush()
        log.info("subscriber_created", telegram_id=data.telegram_id)
        return subscriber, True

    async def update_preferences(
        self, telegram_id: int, update: SubscriberUpdate
    ) -> Subscriber | None:
        subscriber = await self.get_by_telegram_id(telegram_id)
        if not subscriber:
            return None
        for field, value in update.model_dump(exclude_none=True).items():
            setattr(subscriber, field, value)
        await self.db.flush()
        return subscriber

    async def deactivate(self, telegram_id: int) -> bool:
        subscriber = await self.get_by_telegram_id(telegram_id)
        if not subscriber:
            return False
        subscriber.active = False
        await self.db.flush()
        log.info("subscriber_deactivated", telegram_id=telegram_id)
        return True

    async def get_matching_subscribers(
        self,
        city: City | None,
        price: int | None,
        property_type: PropertyType | None,
    ) -> list[Subscriber]:
        """
        Return active subscribers whose preferences match a given listing.

        Matching rules:
        - city must match (if subscriber has city set)
        - property_type must match (if subscriber has property_type set)
        - price must be within [min_price, max_price] (null = no constraint)
        - Listings with null price are sent to subscribers with no price constraint
        """
        stmt = select(Subscriber).where(Subscriber.active == True)  # noqa: E712

        if city:
            stmt = stmt.where(
                (Subscriber.city == city) | (Subscriber.city == None)  # noqa: E711
            )
        if property_type:
            stmt = stmt.where(
                (Subscriber.property_type == property_type)
                | (Subscriber.property_type == None)  # noqa: E711
            )
        if price is not None:
            stmt = stmt.where(
                ((Subscriber.min_price == None) | (Subscriber.min_price <= price))  # noqa: E711
                & ((Subscriber.max_price == None) | (Subscriber.max_price >= price))  # noqa: E711
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_all(
        self, page: int = 1, page_size: int = 50, active_only: bool = False
    ) -> tuple[list[Subscriber], int]:
        stmt = select(Subscriber)
        if active_only:
            stmt = stmt.where(Subscriber.active == True)  # noqa: E712
        count = (
            await self.db.execute(
                select(func.count()).select_from(stmt.subquery())
            )
        ).scalar_one()
        offset = (page - 1) * page_size
        stmt = stmt.order_by(Subscriber.created_at.desc()).offset(offset).limit(page_size)
        rows = (await self.db.execute(stmt)).scalars().all()
        return list(rows), count

    async def total_count(self) -> int:
        stmt = select(func.count(Subscriber.id))
        return (await self.db.execute(stmt)).scalar_one()
