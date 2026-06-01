"""Notification ORM model — tracks which alerts have been sent."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Notification(Base):
    """Records every Telegram alert sent, preventing duplicate messages."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notification_subscriber_listing", "subscriber_id", "listing_id"),
        Index("ix_notification_sent_at", "sent_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subscriber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscribers.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    subscriber: Mapped["Subscriber"] = relationship(  # noqa: F821
        back_populates="notifications"
    )
    listing: Mapped["Listing"] = relationship(  # noqa: F821
        back_populates="notifications"
    )

    def __repr__(self) -> str:
        return (
            f"<Notification sub={self.subscriber_id} listing={self.listing_id}>"
        )
