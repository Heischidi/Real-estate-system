"""Listings API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database import get_db
from app.models.listing import City, PropertyType
from app.schemas.listing import ListingFilter, PaginatedListings
from app.services.listing_service import ListingService

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.get("", response_model=PaginatedListings)
async def list_listings(
    city: City | None = Query(default=None),
    property_type: PropertyType | None = Query(default=None),
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    source: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedListings:
    """Browse and filter property listings. Public endpoint."""
    filters = ListingFilter(
        city=city,
        property_type=property_type,
        min_price=min_price,
        max_price=max_price,
        source=source,
        page=page,
        page_size=page_size,
    )
    service = ListingService(db)
    return await service.list_listings(filters)
