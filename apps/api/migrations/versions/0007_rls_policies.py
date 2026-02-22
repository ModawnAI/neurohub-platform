"""Add Row Level Security policies to all tenant-scoped tables.

Revision ID: 0007_rls_policies
Revises: 0006_webhooks
"""
from alembic import op

revision = "0007_rls_policies"
down_revision = "0006_webhooks"
branch_labels = None
depends_on = None

# Tables that have institution_id column directly
INSTITUTION_SCOPED = [
    "requests",
    "cases",
    "case_files",
    "runs",
    "run_steps",
    "reports",
    "report_reviews",
    "qc_decisions",
    "audit_logs",
    "patient_access_logs",
    "notifications",
    "usage_ledger",
    "institution_members",
    "institution_api_keys",
    "institution_invites",
    "outbox_events",
    "upload_sessions",
    "webhooks",
]

# Tables scoped by user_id instead
USER_SCOPED = [
    "idempotency_keys",
]


def upgrade() -> None:
    # Create helper function to get current institution from JWT
    op.execute("""
        CREATE OR REPLACE FUNCTION public.current_institution_id()
        RETURNS uuid
        LANGUAGE sql STABLE
        AS $$
            SELECT COALESCE(
                (current_setting('request.jwt.claims', true)::json ->> 'institution_id')::uuid,
                (current_setting('request.jwt.claims', true)::json -> 'app_metadata' ->> 'institution_id')::uuid,
                '00000000-0000-0000-0000-000000000001'::uuid
            )
        $$;
    """)

    # Enable RLS and create policies for institution-scoped tables
    for table in INSTITUTION_SCOPED:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

        # Service role bypass (API server uses service role)
        op.execute(f"""
            CREATE POLICY "{table}_service_bypass" ON {table}
            FOR ALL TO service_role
            USING (true)
            WITH CHECK (true);
        """)

        # Authenticated users can only see their institution's data
        op.execute(f"""
            CREATE POLICY "{table}_institution_isolation" ON {table}
            FOR ALL TO authenticated
            USING (institution_id = public.current_institution_id())
            WITH CHECK (institution_id = public.current_institution_id());
        """)

    # User-scoped tables
    op.execute("ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "idempotency_keys_service_bypass" ON idempotency_keys
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true);
    """)

    # Institutions table - users can read their own institution
    op.execute("ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE institutions FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "institutions_service_bypass" ON institutions
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true);
    """)
    op.execute("""
        CREATE POLICY "institutions_read_own" ON institutions
        FOR SELECT TO authenticated
        USING (id = public.current_institution_id());
    """)

    # Users table - users can read users in their institution
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "users_service_bypass" ON users
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true);
    """)

    # Service definitions - readable by all authenticated
    op.execute("ALTER TABLE service_definitions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE service_definitions FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "service_definitions_service_bypass" ON service_definitions
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true);
    """)
    op.execute("""
        CREATE POLICY "service_definitions_read_all" ON service_definitions
        FOR SELECT TO authenticated
        USING (true);
    """)

    # Pipeline definitions - readable by all authenticated
    op.execute("ALTER TABLE pipeline_definitions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE pipeline_definitions FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "pipeline_definitions_service_bypass" ON pipeline_definitions
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true);
    """)
    op.execute("""
        CREATE POLICY "pipeline_definitions_read_all" ON pipeline_definitions
        FOR SELECT TO authenticated
        USING (true);
    """)


def downgrade() -> None:
    all_tables = INSTITUTION_SCOPED + USER_SCOPED + [
        "institutions", "users", "service_definitions", "pipeline_definitions"
    ]
    for table in all_tables:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        # Drop all policies (use pg_policies to find them)
        op.execute(f"""
            DO $$
            DECLARE
                pol RECORD;
            BEGIN
                FOR pol IN SELECT policyname FROM pg_policies WHERE tablename = '{table}'
                LOOP
                    EXECUTE format('DROP POLICY IF EXISTS %I ON {table}', pol.policyname);
                END LOOP;
            END $$;
        """)

    op.execute("DROP FUNCTION IF EXISTS public.current_institution_id();")
