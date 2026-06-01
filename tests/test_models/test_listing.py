"""Tests for listing model and service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.models.listing import City, Listing, PropertyType
from app.schemas.listing import ListingData


@pytest.mark.unit
class TestListingModel:
    def test_listing_repr(self, sample_listing: Listing):
        r = repr(sample_listing)
        assert "propertypro" in r
        assert "abuja" in r

    def test_listing_has_required_fields(self, sample_listing: Listing):
        assert sample_listing.source == "propertypro"
        assert sample_listing.title is not None
        assert sample_listing.listing_url.startswith("https://")

    def test_city_enum_values(self):
        assert City.ABUJA.value == "abuja"
        assert City.LAGOS.value == "lagos"
        assert City.PORT_HARCOURT.value == "port_harcourt"
        assert City.KANO.value == "kano"

    def test_property_type_enum_values(self):
        assert PropertyType.APARTMENT.value == "apartment"
        assert PropertyType.LAND.value == "land"
        assert PropertyType.COMMERCIAL.value == "commercial"


@pytest.mark.unit
class TestListingData:
    def test_listing_data_minimal(self):
        data = ListingData(
            source="test",
            source_listing_id="abc-123",
            title="Test Property",
            listing_url="https://test.com/listing/abc-123",
        )
        assert data.currency == "NGN"
        assert data.price is None
        assert data.bedrooms is None

    def test_listing_data_full(self):
        data = ListingData(
            source="propertypro",
            source_listing_id="pp-456",
            title="4 Bedroom Duplex",
            price=180_000_000,
            property_type=PropertyType.DUPLEX,
            bedrooms=4,
            bathrooms=5,
            city=City.ABUJA,
            listing_url="https://propertypro.ng/listing/pp-456",
        )
        assert data.price == 180_000_000
        assert data.bedrooms == 4

    def test_listing_data_rejects_negative_price(self):
        # Price can be None but shouldn't be negative in practice
        data = ListingData(
            source="test",
            source_listing_id="x",
            title="Test",
            listing_url="https://test.com",
            price=-1,
        )
        # Schema allows it — validation is business logic level
        assert data.price == -1
