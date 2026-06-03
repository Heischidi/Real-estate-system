from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime, timezone, timedelta

from app.api.deps import get_current_admin
from app.database import get_db
from app.models.listing import City, PropertyType
from app.schemas.listing import (
    ListingFilter,
    PaginatedListings,
    ListingCreate,
    ListingUpdate,
    ListingResponse,
)
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
    page_size: int = Query(default=20, ge=1, le=1000),
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


@router.post("", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
    data: ListingCreate,
    db: AsyncSession = Depends(get_db),
    _: dict[str, object] = Depends(get_current_admin),
) -> ListingResponse:
    """Create a manual property listing. Admin only."""
    service = ListingService(db)
    listing = await service.create_manual_listing(data)

    # Trigger alerts for this new listing
    try:
        from app.tasks.alerts import process_new_listings
        # We look for new listings created 5 seconds before now to match
        since_iso = (datetime.now(tz=timezone.utc) - timedelta(seconds=5)).isoformat()
        process_new_listings.apply_async(
            kwargs={"since_iso": since_iso},
            queue="alerts",
        )
    except Exception as exc:
        # Don't fail the listing creation if Celery isn't running or queue dispatch fails
        # but log the warning.
        import logging
        logging.getLogger(__name__).warning(f"Failed to queue alerts task: {exc}")

    return ListingResponse.model_validate(listing)


@router.put("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    data: ListingUpdate,
    listing_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    _: dict[str, object] = Depends(get_current_admin),
) -> ListingResponse:
    """Update a manually created property listing. Admin only."""
    service = ListingService(db)
    listing = await service.update_manual_listing(listing_id, data)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property listing not found or is not editable",
        )
    return ListingResponse.model_validate(listing)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(
    listing_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    _: dict[str, object] = Depends(get_current_admin),
) -> None:
    """Delete a property listing. Admin only."""
    service = ListingService(db)
    success = await service.delete_listing(listing_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property listing not found",
        )
    return None
