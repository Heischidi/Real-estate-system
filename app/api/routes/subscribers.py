"""Subscribers admin routes (JWT protected)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database import get_db
from app.schemas.subscriber import SubscriberResponse
from app.services.subscriber_service import SubscriberService

router = APIRouter(prefix="/subscribers", tags=["Subscribers (Admin)"])


@router.get("", response_model=dict[str, object])
async def list_subscribers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: dict[str, object] = Depends(get_current_admin),
) -> dict[str, object]:
    """List all subscribers. Admin only."""
    service = SubscriberService(db)
    subscribers, total = await service.list_all(
        page=page, page_size=page_size, active_only=active_only
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [SubscriberResponse.model_validate(s) for s in subscribers],
    }
