"""Unit tests for manual property listing CRUD API endpoints."""

from __future__ import annotations

import pytest
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.listing import City, PropertyType, Listing
import uuid


@pytest.fixture(autouse=True)
def mock_celery_task():
    """Mock the Celery task to prevent Redis connection attempts during tests."""
    with patch("app.tasks.alerts.process_new_listings.apply_async") as mock:
        yield mock


@pytest.fixture
async def admin_token(client: AsyncClient, mock_settings) -> str:
    """Fixture to obtain a valid admin JWT token."""
    resp = await client.post(
        "/auth/token",
        data={"username": "admin", "password": "test-admin-password"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
class TestManualListingsCRUD:
    async def test_create_listing_unauthorized(self, client: AsyncClient):
        """Creating a manual listing should fail without token."""
        payload = {
            "title": "Beautiful 3 Bedroom Flat",
            "city": "lagos",
            "property_type": "flat",
            "price": 45000000,
        }
        resp = await client.post("/listings", json=payload)
        assert resp.status_code == 403

    async def test_create_listing_authorized(self, client: AsyncClient, admin_token: str):
        """Creating a manual listing should succeed with valid admin token."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "title": "Premium 4 Bedroom Duplex",
            "city": "abuja",
            "property_type": "duplex",
            "price": 120000000,
            "location": "Maitama",
            "bedrooms": 4,
            "bathrooms": 4,
            "toilets": 5,
            "agent_name": "Realtor Pro",
            "agent_phone": "08012345678",
            "description": "Luxurious property with top-tier finishes",
            "image_url": "https://example.com/duplex.jpg",
        }
        resp = await client.post("/listings", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Premium 4 Bedroom Duplex"
        assert data["city"] == "abuja"
        assert data["property_type"] == "duplex"
        assert data["source"] == "manual"
        assert data["listing_url"] == "https://wa.me/2348012345678"
        assert data["id"] is not None

    async def test_update_listing_authorized(self, client: AsyncClient, admin_token: str, db_session: AsyncSession):
        """Updating a listing should succeed with valid token."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Manually create a listing directly in the DB
        listing_id = uuid.uuid4()
        listing = Listing(
            id=listing_id,
            title="Old Title",
            city=City.LAGOS,
            property_type=PropertyType.FLAT,
            source="manual",
            source_listing_id=listing_id.hex,
            listing_url="https://t.me/RealtorpalBot",
        )
        db_session.add(listing)
        await db_session.commit()

        # Update payload
        payload = {
            "title": "New Updated Title",
            "city": "lagos",
            "property_type": "flat",
            "price": 50000000,
            "location": "Ikeja",
        }
        resp = await client.put(f"/listings/{listing_id}", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New Updated Title"
        assert data["price"] == 50000000
        assert data["location"] == "Ikeja"

    async def test_delete_listing_authorized(self, client: AsyncClient, admin_token: str, db_session: AsyncSession):
        """Deleting a listing should succeed with valid token."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create a listing directly in the DB
        listing_id = uuid.uuid4()
        listing = Listing(
            id=listing_id,
            title="Listing to Delete",
            city=City.PORT_HARCOURT,
            property_type=PropertyType.APARTMENT,
            source="manual",
            source_listing_id=listing_id.hex,
            listing_url="https://t.me/RealtorpalBot",
        )
        db_session.add(listing)
        await db_session.commit()

        # Delete the listing
        resp = await client.delete(f"/listings/{listing_id}", headers=headers)
        assert resp.status_code == 204

        # Verify it is deleted from DB
        resp_check = await client.get("/listings")
        data = resp_check.json()
        assert all(item["id"] != str(listing_id) for item in data["items"])
