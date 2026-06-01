"""Pydantic schemas for Notification."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """API response schema for a notification record."""

    id: uuid.UUID
    subscriber_id: uuid.UUID
    listing_id: uuid.UUID
    sent_at: datetime

    model_config = {"from_attributes": True}
