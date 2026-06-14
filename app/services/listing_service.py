"""Listing service — database operations for listings."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.listing import City, Listing, PropertyType
from app.schemas.listing import (
    ListingData,
    ListingFilter,
    PaginatedListings,
    ListingCreate,
    ListingUpdate,
)

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
        from sqlalchemy import or_
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
        # Secondary guard: if a location_keyword is provided, also require that
        # the scraped location string actually contains that city name.
        # This filters out stale DB rows that were tagged with the wrong city enum.
        if getattr(filters, "location_keyword", None):
            kw = filters.location_keyword.lower()
            query = query.where(
                or_(
                    Listing.location == None,  # noqa: E711 — keep rows with no location
                    func.lower(Listing.location).contains(kw),
                )
            )

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

    async def create_manual_listing(self, data: ListingCreate) -> Listing:
        """Create a property listing manually entered by admin."""
        # Generate UUID for the listing
        listing_id = uuid.uuid4()
        
        # Prepare values
        values = data.model_dump()
        
        # Set manual fields
        values["id"] = listing_id
        values["source"] = "manual"
        values["source_listing_id"] = listing_id.hex
        
        # Handle default listing URL if not provided
        if not values.get("listing_url"):
            phone = values.get("agent_phone")
            if phone:
                # Clean phone number (remove spaces, etc.)
                clean_phone = "".join(c for c in phone if c.isdigit())
                if clean_phone.startswith("0") and len(clean_phone) == 11:
                    clean_phone = "234" + clean_phone[1:]
                elif not clean_phone.startswith("234") and len(clean_phone) == 10:
                    clean_phone = "234" + clean_phone
                values["listing_url"] = f"https://wa.me/{clean_phone}"
            else:
                values["listing_url"] = "https://t.me/RealtorpalBot"
                
        listing = Listing(**values)
        self.db.add(listing)
        await self.db.commit()
        await self.db.refresh(listing)
        
        log.info(
            "manual_listing_created",
            listing_id=str(listing.id),
            city=listing.city,
            title=listing.title
        )
        return listing

    async def update_manual_listing(
        self, listing_id: uuid.UUID, data: ListingUpdate
    ) -> Listing | None:
        """Update a manually created property listing."""
        listing = await self.get_by_id(listing_id)
        if not listing:
            return None
            
        values = data.model_dump()
        
        # If listing_url is blank or not set, and was previously manual, we can update or preserve
        if not values.get("listing_url"):
            phone = values.get("agent_phone")
            if phone:
                clean_phone = "".join(c for c in phone if c.isdigit())
                if clean_phone.startswith("0") and len(clean_phone) == 11:
                    clean_phone = "234" + clean_phone[1:]
                elif not clean_phone.startswith("234") and len(clean_phone) == 10:
                    clean_phone = "234" + clean_phone
                values["listing_url"] = f"https://wa.me/{clean_phone}"
            else:
                values["listing_url"] = "https://t.me/RealtorpalBot"
                
        for key, val in values.items():
            setattr(listing, key, val)
            
        await self.db.commit()
        await self.db.refresh(listing)
        
        log.info("manual_listing_updated", listing_id=str(listing.id))
        return listing

    async def delete_listing(self, listing_id: uuid.UUID) -> bool:
        """Delete a listing by ID."""
        listing = await self.get_by_id(listing_id)
        if not listing:
            return False
        await self.db.delete(listing)
        await self.db.commit()
        log.info("listing_deleted", listing_id=str(listing_id))
        return True
