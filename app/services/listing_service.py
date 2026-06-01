"""Listing service — database operations for listings."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.listing import City, Listing, PropertyType
from app.schemas.listing import ListingData, ListingFilter, PaginatedListings

log = get_logger(__name__)


class ListingService:
    """All database interactions for the Listing model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_listing(self, data: ListingData) -> tuple[Listing, bool]:
        """
        Insert a listing or skip if it already exists.

        Returns:
            (listing, is_new) — is_new=True if this was freshly inserted.
        """
        values = data.model_dump()

        # Use PostgreSQL's ON CONFLICT DO NOTHING for idempotent inserts
        stmt = (
            pg_insert(Listing)
            .values(id=uuid.uuid4(), **values)
            .on_conflict_do_nothing(constraint="uq_listing_source")
            .returning(Listing)
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()

        if row:
            # Freshly inserted
            log.info(
                "new_listing_saved",
                source=data.source,
                source_id=data.source_listing_id,
                city=data.city,
            )
            return row[0], True

        # Already existed — load it
        existing = await self.get_by_source(data.source, data.source_listing_id)
        return existing, False  # type: ignore[return-value]

    async def get_by_source(
        self, source: str, source_listing_id: str
    ) -> Listing | None:
        stmt = select(Listing).where(
            Listing.source == source,
            Listing.source_listing_id == source_listing_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, listing_id: uuid.UUID) -> Listing | None:
        stmt = select(Listing).where(Listing.id == listing_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_listings(self, filters: ListingFilter) -> PaginatedListings:
        """Return paginated, filtered listings."""
        from app.schemas.listing import ListingResponse

        query = select(Listing)

        if filters.city:
            query = query.where(Listing.city == filters.city)
        if filters.property_type:
            query = query.where(Listing.property_type == filters.property_type)
        if filters.min_price is not None:
            query = query.where(Listing.price >= filters.min_price)
        if filters.max_price is not None:
            query = query.where(Listing.price <= filters.max_price)
        if filters.source:
            query = query.where(Listing.source == filters.source)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total: int = (await self.db.execute(count_query)).scalar_one()

        # Apply pagination and ordering
        offset = (filters.page - 1) * filters.page_size
        query = (
            query.order_by(Listing.created_at.desc())
            .offset(offset)
            .limit(filters.page_size)
        )
        rows = (await self.db.execute(query)).scalars().all()

        return PaginatedListings(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            items=[ListingResponse.model_validate(r) for r in rows],
        )

    async def get_new_listings_since(self, since: datetime) -> list[Listing]:
        """Fetch all listings created after `since` — used by alert engine."""
        stmt = (
            select(Listing)
            .where(Listing.created_at >= since)
            .order_by(Listing.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_source(self) -> dict[str, int]:
        """Return listing counts grouped by source."""
        stmt = select(Listing.source, func.count(Listing.id)).group_by(Listing.source)
        result = await self.db.execute(stmt)
        return dict(result.all())

    async def total_count(self) -> int:
        stmt = select(func.count(Listing.id))
        return (await self.db.execute(stmt)).scalar_one()
