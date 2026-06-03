"""Tests for the Telegram bot message formatters."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.bot.formatters import format_listing_alert, format_price
from app.models.listing import City, Listing, PropertyType


@pytest.mark.unit
class TestFormatPrice:
    def test_billion(self):
        assert "1.0B" in format_price(1_000_000_000)

    def test_million(self):
        assert "₦45.0M" in format_price(45_000_000)

    def test_thousands(self):
        assert "K" in format_price(500_000)

    def test_none_price(self):
        assert format_price(None) == "Price on request"

    def test_naira_symbol(self):
        result = format_price(10_000_000)
        assert "₦" in result


@pytest.mark.unit
class TestFormatListingAlert:
    def _make_listing(self, **kwargs) -> Listing:
        defaults = dict(
            id=uuid.uuid4(),
            source="propertypro",
            source_listing_id="test-001",
            title="3 Bedroom Apartment in Guzape",
            price=45_000_000,
            currency="NGN",
            property_type=PropertyType.APARTMENT,
            bedrooms=3,
            bathrooms=2,
            toilets=3,
            location="Guzape",
            city=City.ABUJA,
            state="Abuja",
            listing_url="https://propertypro.ng/listing/test-001",
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
        )
        defaults.update(kwargs)
        return Listing(**defaults)

    def test_contains_title(self):
        listing = self._make_listing()
        msg = format_listing_alert(listing)
        assert "3 Bedroom Apartment" in msg

    def test_contains_price(self):
        listing = self._make_listing()
        msg = format_listing_alert(listing)
        assert "₦" in msg
        assert "45" in msg

    def test_contains_location(self):
        listing = self._make_listing()
        msg = format_listing_alert(listing)
        assert "Guzape" in msg
        assert "Abuja" in msg

    def test_contains_view_link(self):
        listing = self._make_listing()
        msg = format_listing_alert(listing)
        assert "View Listing" in msg
        assert "propertypro.ng" in msg

    def test_bedrooms_shown(self):
        listing = self._make_listing()
        msg = format_listing_alert(listing)
        assert "3" in msg

    def test_no_price_listing(self):
        listing = self._make_listing(price=None)
        msg = format_listing_alert(listing)
        assert "Price on request" in msg

    def test_long_title_truncated(self):
        long_title = "A" * 100
        listing = self._make_listing(title=long_title)
        msg = format_listing_alert(listing)
        assert "..." in msg

    def test_html_formatting(self):
        listing = self._make_listing()
        msg = format_listing_alert(listing)
        assert "<b>" in msg
        assert "</b>" in msg
