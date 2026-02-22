"""Shared test fixtures for NeuroHub API tests.

Uses dependency overrides on the FastAPI app so that every test
runs against an in-memory/test database session and a deterministic
mock user.  No real Supabase or Redis connection is needed.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.main import app
from app.models.base import Base

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_DB_URL = settings.database_url  # use the dev DB for now; CI uses service container
DEFAULT_INSTITUTION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEFAULT_SERVICE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEFAULT_PIPELINE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------
_test_engine = create_async_engine(TEST_DB_URL, echo=False, pool_pre_ping=True, pool_size=5)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional DB session that rolls back after each test."""
    async with _test_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# Mock user fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def admin_user() -> CurrentUser:
    return CurrentUser(
        id=DEFAULT_USER_ID,
        username="test-admin",
        institution_id=DEFAULT_INSTITUTION_ID,
        roles=["SYSTEM_ADMIN"],
        user_type="ADMIN",
    )


@pytest.fixture
def service_user() -> CurrentUser:
    return CurrentUser(
        id=uuid.UUID("11111111-1111-1111-1111-111111111112"),
        username="test-service-user",
        institution_id=DEFAULT_INSTITUTION_ID,
        roles=["PHYSICIAN"],
        user_type="SERVICE_USER",
    )


@pytest.fixture
def expert_user() -> CurrentUser:
    return CurrentUser(
        id=uuid.UUID("11111111-1111-1111-1111-111111111113"),
        username="test-expert",
        institution_id=DEFAULT_INSTITUTION_ID,
        roles=["REVIEWER"],
        user_type="EXPERT",
    )


@pytest.fixture
def other_institution_user() -> CurrentUser:
    """User from a different institution — for cross-tenant isolation tests."""
    return CurrentUser(
        id=uuid.UUID("11111111-1111-1111-1111-111111111199"),
        username="other-institution-user",
        institution_id=uuid.UUID("99999999-9999-9999-9999-999999999999"),
        roles=["SYSTEM_ADMIN"],
        user_type="ADMIN",
    )


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------
@pytest.fixture
async def client(db: AsyncSession, admin_user: CurrentUser) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX async client with dependency overrides for DB and auth."""

    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: admin_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def client_as(db: AsyncSession):
    """Factory fixture to create a client authenticated as a specific user."""

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _make_client(user: CurrentUser):
        async def _override_db():
            yield db

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = lambda: user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

        app.dependency_overrides.clear()

    return _make_client


# ---------------------------------------------------------------------------
# Helper: create a request via API (used by multiple test files)
# ---------------------------------------------------------------------------
async def create_test_request(
    client: AsyncClient,
    *,
    service_id: uuid.UUID = DEFAULT_SERVICE_ID,
    pipeline_id: uuid.UUID = DEFAULT_PIPELINE_ID,
    cases: list[dict] | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """POST /api/v1/requests and return the JSON body."""
    payload = {
        "service_id": str(service_id),
        "pipeline_id": str(pipeline_id),
        "cases": cases or [{"patient_ref": "PAT-001"}],
    }
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    resp = await client.post("/api/v1/requests", json=payload)
    return resp.json()
