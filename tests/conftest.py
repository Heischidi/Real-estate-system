"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.listing import City, Listing, PropertyType
from app.models.subscriber import Subscriber

# Use SQLite for tests (no PostgreSQL required)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with DB override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sample_listing() -> Listing:
    import uuid
    from datetime import datetime, timezone

    return Listing(
        id=uuid.uuid4(),
        source="propertypro",
        source_listing_id="test-123",
        title="3 Bedroom Apartment in Guzape",
        price=45_000_000,
        currency="NGN",
        property_type=PropertyType.APARTMENT,
        bedrooms=3,
        bathrooms=2,
        location="Guzape, Abuja",
        city=City.ABUJA,
        state="Abuja",
        listing_url="https://propertypro.ng/test-123",
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def sample_subscriber() -> Subscriber:
    import uuid
    from datetime import datetime, timezone

    return Subscriber(
        id=uuid.uuid4(),
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        city=City.ABUJA,
        min_price=10_000_000,
        max_price=100_000_000,
        property_type=PropertyType.APARTMENT,
        active=True,
        created_at=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Override settings for tests by mutating the cached Settings instance directly."""
    from app.config import get_settings
    settings = get_settings()
    
    # Store original values
    orig_secret = settings.secret_key
    orig_bot_token = settings.telegram_bot_token
    orig_username = settings.admin_username
    orig_password = settings.admin_password
    orig_jwt_key = settings.jwt_secret_key
    
    # Mutate attributes on the active instance
    settings.secret_key = "test-secret-key-32-characters-long!"
    settings.telegram_bot_token = "123456789:AABBCCDDEEFFaabbccddeeff_test_token"
    settings.admin_username = "admin"
    settings.admin_password = "test-admin-password"
    settings.jwt_secret_key = "test-jwt-secret-key-32-chars-long!"
    
    yield settings
    
    # Restore original values
    settings.secret_key = orig_secret
    settings.telegram_bot_token = orig_bot_token
    settings.admin_username = orig_username
    settings.admin_password = orig_password
    settings.jwt_secret_key = orig_jwt_key
