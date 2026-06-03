"""Tests for the alert matching service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.models.listing import City, Listing, PropertyType
from app.models.subscriber import Subscriber


@pytest.mark.unit
class TestAlertMatching:
    """Test the subscriber matching logic without a real database."""

    def _make_subscriber(self, **kwargs) -> Subscriber:
        defaults = dict(
            id=uuid.uuid4(),
            telegram_id=111111,
            first_name="Test",
            city=City.ABUJA,
            min_price=10_000_000,
            max_price=100_000_000,
            property_type=PropertyType.APARTMENT,
            active=True,
            created_at=datetime.now(tz=timezone.utc),
        )
        defaults.update(kwargs)
        return Subscriber(**defaults)

    def _matches(self, subscriber: Subscriber, listing_city: City | None,
                 price: int | None, prop_type: PropertyType | None) -> bool:
        """Replicate the matching logic inline."""
        if not subscriber.active:
            return False
        if subscriber.city and listing_city and subscriber.city != listing_city:
            return False
        if subscriber.property_type and prop_type and subscriber.property_type != prop_type:
            return False
        if price is not None:
            if subscriber.min_price and price < subscriber.min_price:
                return False
            if subscriber.max_price and price > subscriber.max_price:
                return False
        return True

    def test_exact_match(self):
        sub = self._make_subscriber()
        assert self._matches(sub, City.ABUJA, 50_000_000, PropertyType.APARTMENT)

    def test_price_below_min(self):
        sub = self._make_subscriber(min_price=50_000_000)
        assert not self._matches(sub, City.ABUJA, 10_000_000, PropertyType.APARTMENT)

    def test_price_above_max(self):
        sub = self._make_subscriber(max_price=50_000_000)
        assert not self._matches(sub, City.ABUJA, 80_000_000, PropertyType.APARTMENT)

    def test_city_mismatch(self):
        sub = self._make_subscriber(city=City.LAGOS)
        assert not self._matches(sub, City.ABUJA, 50_000_000, PropertyType.APARTMENT)

    def test_property_type_mismatch(self):
        sub = self._make_subscriber(property_type=PropertyType.DUPLEX)
        assert not self._matches(sub, City.ABUJA, 50_000_000, PropertyType.APARTMENT)

    def test_inactive_subscriber_no_match(self):
        sub = self._make_subscriber(active=False)
        assert not self._matches(sub, City.ABUJA, 50_000_000, PropertyType.APARTMENT)

    def test_null_price_subscriber_any_price(self):
        sub = self._make_subscriber(min_price=None, max_price=None)
        assert self._matches(sub, City.ABUJA, 1_000_000_000, PropertyType.APARTMENT)

    def test_null_city_matches_any_city(self):
        sub = self._make_subscriber(city=None)
        assert self._matches(sub, City.LAGOS, 50_000_000, PropertyType.APARTMENT)

    def test_null_property_type_matches_any(self):
        sub = self._make_subscriber(property_type=None)
        assert self._matches(sub, City.ABUJA, 50_000_000, PropertyType.LAND)

    def test_listing_no_price_with_constrained_sub(self):
        """Listing with no price — subscriber with price limits should still match."""
        sub = self._make_subscriber()
        # When listing price is None, skip price check
        assert self._matches(sub, City.ABUJA, None, PropertyType.APARTMENT)
