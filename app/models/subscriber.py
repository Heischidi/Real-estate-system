"""Subscriber ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.listing import City, PropertyType

class SubscriptionTier(str, Enum):
    FREE = "free"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"

class Subscriber(Base):
    """Telegram subscriber with property preferences."""

    __tablename__ = "subscribers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[City | None] = mapped_column(
        Enum(City, name="city_enum", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    min_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    max_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    property_type: Mapped[PropertyType | None] = mapped_column(
        Enum(PropertyType, name="property_type_enum", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier_enum", values_callable=lambda e: [m.value for m in e]),
        default=SubscriptionTier.FREE,
        nullable=False,
    )
    subscription_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    notifications: Mapped[list["Notification"]] = relationship(  # noqa: F821
        back_populates="subscriber", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Subscriber telegram_id={self.telegram_id} username={self.username}>"
        )
