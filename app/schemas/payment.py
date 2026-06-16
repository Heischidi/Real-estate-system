"""Pydantic schemas for Payments."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.payment import PaymentPlan, PaymentStatus


class PaymentCreate(BaseModel):
    """Data needed to create a payment claim."""

    telegram_id: int
    plan: PaymentPlan
    amount: int

    model_config = {"use_enum_values": True}


class PaymentResponse(BaseModel):
    """API response schema for a payment."""

    id: uuid.UUID
    telegram_id: int
    plan: str
    amount: int
    status: str
    created_at: datetime
    updated_at: datetime

    # For admin display convenience (we might join with subscriber to get these)
    first_name: str | None = None
    username: str | None = None

    model_config = {"from_attributes": True}


class PaginatedPayments(BaseModel):
    """Paginated payment response."""

    total: int
    page: int
    page_size: int
    items: list[PaymentResponse]
