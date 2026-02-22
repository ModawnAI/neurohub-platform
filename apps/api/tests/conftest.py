"""Shared test fixtures for NeuroHub API tests.

Uses an in-memory SQLite database with SQLAlchemy type compilation
overrides for PostgreSQL-specific types (UUID, JSONB). No external
database or Redis connection is needed.
"""

import re
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# SQLite type compilation — registered before any model import
# ---------------------------------------------------------------------------

@compiles(PG_UUID, "sqlite")
def _uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# Now import app modules (they use PG_UUID / JSONB in column defs)
from app.models.base import Base
import app.models  # noqa: F401 — registers all models with Base.metadata
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_INSTITUTION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEFAULT_SERVICE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEFAULT_PIPELINE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

# ---------------------------------------------------------------------------
# In-memory SQLite engine (StaticPool shares one connection across sessions)
# ---------------------------------------------------------------------------
_test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_test_session_factory = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False,
)

# Strip FOR UPDATE clauses — unsupported by SQLite
_FOR_UPDATE_RE = re.compile(r"\s+FOR\s+UPDATE(?:\s+SKIP\s+LOCKED|\s+NOWAIT)?", re.IGNORECASE)


@event.listens_for(_test_engine.sync_engine, "before_cursor_execute", retval=True)
def _strip_for_update(conn, cursor, statement, parameters, context, executemany):
    statement = _FOR_UPDATE_RE.sub("", statement)
    return statement, parameters


# ---------------------------------------------------------------------------
# Create tables once per session
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
async def _create_tables():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


# ---------------------------------------------------------------------------
# Seed reference data required by request creation
# ---------------------------------------------------------------------------
async def _seed(session: AsyncSession) -> None:
    from sqlalchemy import select
    from app.models.institution import Institution
    from app.models.service import ServiceDefinition, PipelineDefinition

    existing = (await session.execute(
        select(Institution).where(Institution.id == DEFAULT_INSTITUTION_ID)
    )).scalar_one_or_none()
    if existing:
        return

    session.add(Institution(
        id=DEFAULT_INSTITUTION_ID,
        code="TEST-INST",
        name="Test Institution",
        status="ACTIVE",
        institution_type="HOSPITAL",
    ))
    session.add(ServiceDefinition(
        id=DEFAULT_SERVICE_ID,
        institution_id=DEFAULT_INSTITUTION_ID,
        name="test-service",
        display_name="Test Service",
        version="1.0.0",
        status="ACTIVE",
    ))
    session.add(PipelineDefinition(
        id=DEFAULT_PIPELINE_ID,
        service_id=DEFAULT_SERVICE_ID,
        name="test-pipeline",
        version="1.0.0",
        steps=[{"name": "preprocess", "image": "test:latest"}],
    ))
    await session.flush()


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
    return CurrentUser(
        id=uuid.UUID("11111111-1111-1111-1111-111111111199"),
        username="other-institution-user",
        institution_id=uuid.UUID("99999999-9999-9999-9999-999999999999"),
        roles=["SYSTEM_ADMIN"],
        user_type="ADMIN",
    )


# ---------------------------------------------------------------------------
# DB session fixture — transactional, rolls back after each test
# ---------------------------------------------------------------------------
@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        async with session.begin():
            await _seed(session)
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------
@pytest.fixture
async def client(db: AsyncSession, admin_user: CurrentUser) -> AsyncGenerator[AsyncClient, None]:
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
    payload = {
        "service_id": str(service_id),
        "pipeline_id": str(pipeline_id),
        "cases": cases or [{"patient_ref": "PAT-001"}],
    }
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    resp = await client.post("/api/v1/requests", json=payload)
    return resp.json()
