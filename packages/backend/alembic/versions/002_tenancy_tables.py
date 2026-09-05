"""002_tenancy_tables

Revision ID: 002_tenancy
Revises: 001_roles_ext
Create Date: 2026-09-05 10:48:00.000000

Conforms to:
- docs/27-database/DATABASE-SCHEMA.md §3, §4, §10
- docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md
- INV-TEN-001, INV-TEN-002, NFR-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '002_tenancy'
down_revision: Union[str, None] = '001_roles_ext'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tenants table (platform-scoped catalog, no RLS)
    op.execute("""
    CREATE TABLE revpilot.tenants (
        id VARCHAR(64) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        slug VARCHAR(128) NOT NULL,
        tier VARCHAR(32) NOT NULL DEFAULT 'SHARED',
        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
        config JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_tenants_slug UNIQUE (slug),
        CONSTRAINT ck_tenants_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'LEGAL_HOLD', 'DELETED'))
    );
    """)

    # 2. Organizations table (tenant-scoped)
    op.execute("""
    CREATE TABLE revpilot.organizations (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        name VARCHAR(255) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_organizations PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_organizations_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT
    );
    CREATE INDEX idx_organizations_tenant ON revpilot.organizations (tenant_id, status);

    ALTER TABLE revpilot.organizations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.organizations FORCE ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON revpilot.organizations AS RESTRICTIVE
        USING (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        )
        WITH CHECK (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        );
    """)

    # 3. Entitlements table (tenant-scoped)
    op.execute("""
    CREATE TABLE revpilot.entitlements (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        plan_id VARCHAR(64) NOT NULL,
        token_quota_monthly BIGINT NOT NULL DEFAULT 20000000,
        connector_limit INT NOT NULL DEFAULT 2,
        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_entitlements PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_entitlements_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_entitlements_quota CHECK (token_quota_monthly >= 0),
        CONSTRAINT ck_entitlements_conn CHECK (connector_limit >= 0)
    );
    CREATE INDEX idx_entitlements_tenant ON revpilot.entitlements (tenant_id, status);

    ALTER TABLE revpilot.entitlements ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.entitlements FORCE ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON revpilot.entitlements AS RESTRICTIVE
        USING (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        )
        WITH CHECK (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.entitlements CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.organizations CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.tenants CASCADE;")
