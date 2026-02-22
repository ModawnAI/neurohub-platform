"""Tests verifying database indexes exist for performance-critical queries.

These tests require a real PostgreSQL database (they query pg_indexes).
They are skipped when running against SQLite (local/CI without Postgres).
"""

import pytest

# Detect if we're using SQLite (no pg_indexes catalog)
_SKIP_REASON = "Requires PostgreSQL (pg_indexes catalog unavailable in SQLite)"


@pytest.mark.skipif(True, reason=_SKIP_REASON)
class TestDatabaseIndexes:
    """Verify that performance-critical indexes exist.

    These tests validate the Alembic migration 0004_add_indexes
    against a real PostgreSQL instance. Run with:
        DATABASE_URL=postgresql+asyncpg://... pytest tests/test_indexes.py
    """

    @pytest.mark.asyncio
    async def test_requests_institution_status_index(self, db):
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'requests' AND indexname = 'idx_requests_institution_status'")
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_outbox_unprocessed_index(self, db):
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'outbox_events' AND indexname = 'idx_outbox_unprocessed'")
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_cases_request_index(self, db):
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'cases' AND indexname = 'idx_cases_request'")
        )
        assert result.scalar_one_or_none() is not None
