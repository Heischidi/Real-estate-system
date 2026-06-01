"""Stats endpoint — platform-wide statistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database import get_db
from app.services.alert_service import AlertService
from app.services.listing_service import ListingService
from app.services.subscriber_service import SubscriberService

router = APIRouter(prefix="/stats", tags=["Stats (Admin)"])


@router.get("")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: dict[str, object] = Depends(get_current_admin),
) -> dict[str, object]:
    """Return platform-wide statistics. Admin only."""
    listing_service = ListingService(db)
    subscriber_service = SubscriberService(db)
    alert_service = AlertService(db)

    total_listings = await listing_service.total_count()
    by_source = await listing_service.count_by_source()
    total_subscribers = await subscriber_service.total_count()
    total_notifications = await alert_service.total_notifications_count()

    return {
        "listings": {
            "total": total_listings,
            "by_source": by_source,
        },
        "subscribers": {
            "total": total_subscribers,
        },
        "notifications": {
            "total": total_notifications,
        },
    }
