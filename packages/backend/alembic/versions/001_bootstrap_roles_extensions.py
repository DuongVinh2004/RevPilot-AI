"""001_bootstrap_roles_extensions

Revision ID: 001_roles_ext
Revises: 
Create Date: 2026-09-05 10:45:00.000000

Conforms to:
- docs/27-database/DATABASE-SCHEMA.md §1, §5, §7
- ADR-0004 (PostgreSQL Engine)
- ADR-0005 (Tenant Isolation RLS)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001_roles_ext'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gist";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # 2. Schema revpilot
    op.execute('CREATE SCHEMA IF NOT EXISTS revpilot;')

    # 3. Roles (idempotent block)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'revpilot_app') THEN
            CREATE ROLE revpilot_app WITH LOGIN PASSWORD 'placeholder_dev_pw';
        END IF;
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'revpilot_migrator') THEN
            CREATE ROLE revpilot_migrator WITH LOGIN PASSWORD 'placeholder_migrator_pw';
        END IF;
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'revpilot_readonly') THEN
            CREATE ROLE revpilot_readonly WITH LOGIN PASSWORD 'placeholder_ro_pw';
        END IF;
    END
    $$;
    """)

    # 4. Permissions on revpilot schema
    op.execute("GRANT ALL ON SCHEMA revpilot TO revpilot_migrator;")
    op.execute("GRANT USAGE ON SCHEMA revpilot TO revpilot_app;")
    op.execute("GRANT USAGE ON SCHEMA revpilot TO revpilot_readonly;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA revpilot GRANT ALL ON TABLES TO revpilot_migrator;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA revpilot GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO revpilot_app;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA revpilot GRANT SELECT ON TABLES TO revpilot_readonly;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA revpilot GRANT ALL ON SEQUENCES TO revpilot_migrator;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA revpilot GRANT USAGE, SELECT ON SEQUENCES TO revpilot_app;")

    # 5. Baseline session context helper for Row-Level Security (RLS) enforcement
    op.execute("""
    CREATE OR REPLACE FUNCTION revpilot.current_tenant_id() RETURNS TEXT AS $$
        SELECT NULLIF(current_setting('revpilot.tenant_id', true), '')::TEXT;
    $$ LANGUAGE SQL STABLE;
    """)

    # 6. Ensure public schema does not allow unrestricted creation
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC;")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS revpilot.current_tenant_id();")
    op.execute("DROP SCHEMA IF EXISTS revpilot CASCADE;")
