"""Pydantic schemas for Subscriber."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.listing import City, PropertyType
from app.models.subscriber import SubscriptionTier


class SubscriberCreate(BaseModel):
    """Data needed to create/update a subscriber's preferences."""

    telegram_id: int
    username: str | None = None
    first_name: str
    city: City | None = None
    min_price: int | None = Field(default=None, ge=0)
    max_price: int | None = Field(default=None, ge=0)
    property_type: PropertyType | None = None
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    active: bool = True

    model_config = {"use_enum_values": True}


class SubscriberUpdate(BaseModel):
    """Partial update for subscriber preferences."""

    city: City | None = None
    min_price: int | None = Field(default=None, ge=0)
    max_price: int | None = Field(default=None, ge=0)
    property_type: PropertyType | None = None
    active: bool | None = None

    model_config = {"use_enum_values": True}


class SubscriberResponse(BaseModel):
    """API response schema for a subscriber."""

    id: uuid.UUID
    telegram_id: int
    username: str | None
    first_name: str
    city: str | None
    min_price: int | None
    max_price: int | None
    property_type: str | None
    subscription_tier: str
    subscription_expiry: datetime | None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
