"""Pydantic schemas for Listing API responses and internal data transfer."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.models.listing import City, PropertyType


class ListingData(BaseModel):
    """Data transfer object produced by scrapers — before DB persistence."""

    source: str
    source_listing_id: str
    title: str
    description: str | None = None
    price: int | None = None
    currency: str = "NGN"
    property_type: PropertyType | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    toilets: int | None = None
    location: str | None = None
    city: City | None = None
    state: str | None = None
    agent_name: str | None = None
    agent_phone: str | None = None
    listing_url: str
    image_url: str | None = None

    model_config = {"use_enum_values": True}


class ListingResponse(BaseModel):
    """API response schema for a single listing."""

    id: uuid.UUID
    source: str
    source_listing_id: str
    title: str
    description: str | None
    price: int | None
    currency: str
    property_type: str | None
    bedrooms: int | None
    bathrooms: int | None
    toilets: int | None
    location: str | None
    city: str | None
    state: str | None
    agent_name: str | None
    agent_phone: str | None
    listing_url: str
    image_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ListingFilter(BaseModel):
    """Query parameters for filtering listings."""

    city: City | None = None
    property_type: PropertyType | None = None
    min_price: int | None = Field(default=None, ge=0)
    max_price: int | None = Field(default=None, ge=0)
    source: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=1000)


class PaginatedListings(BaseModel):
    """Paginated listing response."""

    total: int
    page: int
    page_size: int
    items: list[ListingResponse]


class ListingCreate(BaseModel):
    """Schema for manual property listing creation."""

    title: str = Field(..., min_length=3)
    description: str | None = None
    price: int | None = Field(default=None, ge=0)
    currency: str = "NGN"
    property_type: PropertyType
    city: City
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    toilets: int | None = Field(default=None, ge=0)
    location: str | None = None
    state: str | None = None
    agent_name: str | None = None
    agent_phone: str | None = None
    image_url: str | None = None
    listing_url: str | None = None

    model_config = {"use_enum_values": True}


class ListingUpdate(BaseModel):
    """Schema for manual property listing updates."""

    title: str = Field(..., min_length=3)
    description: str | None = None
    price: int | None = Field(default=None, ge=0)
    currency: str = "NGN"
    property_type: PropertyType
    city: City
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    toilets: int | None = Field(default=None, ge=0)
    location: str | None = None
    state: str | None = None
    agent_name: str | None = None
    agent_phone: str | None = None
    image_url: str | None = None
    listing_url: str | None = None

    model_config = {"use_enum_values": True}
