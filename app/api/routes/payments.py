"""Payments admin routes (JWT protected)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database import get_db
from app.models.payment import PaymentStatus
from app.schemas.payment import PaginatedPayments, PaymentResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments (Admin)"])


@router.get("", response_model=PaginatedPayments)
async def list_payments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status: PaymentStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: dict[str, object] = Depends(get_current_admin),
) -> dict[str, object]:
    """List all manual payment claims. Admin only."""
    service = PaymentService(db)
    rows, total = await service.list_payments(
        page=page, page_size=page_size, status=status
    )
    
    items = []
    for payment, subscriber in rows:
        data = PaymentResponse.model_validate(payment).model_dump()
        if subscriber:
            data["first_name"] = subscriber.first_name
            data["username"] = subscriber.username
        items.append(data)
        
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.post("/{payment_id}/approve")
async def approve_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict[str, object] = Depends(get_current_admin),
) -> dict[str, str]:
    """Approve a payment and activate subscription. Admin only."""
    service = PaymentService(db)
    payment, subscriber = await service.approve_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Normally we would trigger a Telegram message to the user here
    # Since we are in the API context without direct bot access easily, 
    # the bot runner could periodically check or we rely on them noticing.
    # In a full production system we'd enqueue a task to notify them.
    return {"status": "success", "message": "Payment approved"}


@router.post("/{payment_id}/reject")
async def reject_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict[str, object] = Depends(get_current_admin),
) -> dict[str, str]:
    """Reject a payment claim. Admin only."""
    service = PaymentService(db)
    payment = await service.reject_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"status": "success", "message": "Payment rejected"}
