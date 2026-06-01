"""Listing ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PropertyType(str, PyEnum):
    APARTMENT = "apartment"
    FLAT = "flat"
    DUPLEX = "duplex"
    DETACHED_HOUSE = "detached_house"
    TERRACE = "terrace"
    LAND = "land"
    COMMERCIAL = "commercial"


class City(str, PyEnum):
    ABUJA = "abuja"
    LAGOS = "lagos"
    PORT_HARCOURT = "port_harcourt"


class Listing(Base):
    """Represents a single property listing scraped from any source."""

    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("source", "source_listing_id", name="uq_listing_source"),
        Index("ix_listing_city", "city"),
        Index("ix_listing_property_type", "property_type"),
        Index("ix_listing_price", "price"),
        Index("ix_listing_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_listing_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="NGN", nullable=False)
    property_type: Mapped[PropertyType | None] = mapped_column(
        Enum(PropertyType, name="property_type_enum"), nullable=True
    )
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    toilets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[City | None] = mapped_column(
        Enum(City, name="city_enum"), nullable=True, index=True
    )
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    listing_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    notifications: Mapped[list["Notification"]] = relationship(  # noqa: F821
        back_populates="listing", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Listing id={self.id} source={self.source} city={self.city}>"
