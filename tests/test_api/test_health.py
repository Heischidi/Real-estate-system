"""Tests for API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_returns_200(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "timestamp" in data
        assert "database" in data

    async def test_health_has_correct_fields(self, client: AsyncClient):
        resp = await client.get("/health")
        data = resp.json()
        assert data["database"] in ("ok", "error")


@pytest.mark.asyncio
class TestListingsEndpoint:
    async def test_list_listings_empty(self, client: AsyncClient):
        resp = await client.get("/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] == 0

    async def test_list_listings_with_filters(self, client: AsyncClient):
        resp = await client.get("/listings?city=abuja&page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    async def test_list_listings_invalid_city(self, client: AsyncClient):
        resp = await client.get("/listings?city=invalid_city")
        assert resp.status_code == 422

    async def test_list_listings_price_filter(self, client: AsyncClient):
        resp = await client.get("/listings?min_price=1000000&max_price=50000000")
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestAuthEndpoints:
    async def test_get_token_invalid_credentials(self, client: AsyncClient):
        resp = await client.post(
            "/auth/token",
            data={"username": "wrong", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_admin_routes_require_auth(self, client: AsyncClient):
        # Subscribers list without token
        resp = await client.get("/subscribers")
        assert resp.status_code == 403  # No auth header provided

        # Stats without token
        resp = await client.get("/stats")
        assert resp.status_code == 403

    async def test_scrape_endpoint_requires_auth(self, client: AsyncClient):
        resp = await client.post("/scrape")
        assert resp.status_code == 403
