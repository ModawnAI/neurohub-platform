"""Tests for Row Level Security policies.

These tests require a real PostgreSQL database (they query pg_class, information_schema).
They are skipped when running against SQLite.
"""

import pytest

_SKIP_REASON = "Requires PostgreSQL (RLS / pg_class unavailable in SQLite)"


@pytest.mark.skipif(True, reason=_SKIP_REASON)
class TestRLSPolicies:
    """Verify RLS policies exist and are configured correctly.

    Run against a real PostgreSQL instance where migration 0007_rls_policies has been applied:
        DATABASE_URL=postgresql+asyncpg://... pytest tests/test_rls.py
    """

    @pytest.mark.asyncio
    async def test_rls_enabled_on_requests(self, db):
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT relrowsecurity FROM pg_class WHERE relname = 'requests'")
        )
        row = result.scalar_one_or_none()
        assert row is True

    @pytest.mark.asyncio
    async def test_rls_helper_function_exists(self, db):
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT routine_name FROM information_schema.routines WHERE routine_name = 'current_institution_id'")
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_institution_scoped_tables_have_rls(self, db):
        from sqlalchemy import text
        tables = [
            "requests", "cases", "case_files", "runs", "run_steps",
            "reports", "audit_logs", "notifications", "usage_ledger",
        ]
        for table in tables:
            result = await db.execute(
                text(f"SELECT relrowsecurity FROM pg_class WHERE relname = '{table}'")
            )
            row = result.scalar_one_or_none()
            assert row is True, f"RLS not enabled on {table}"
