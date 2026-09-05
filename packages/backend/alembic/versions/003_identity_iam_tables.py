"""003_identity_iam_tables

Revision ID: 003_identity
Revises: 002_tenancy
Create Date: 2026-09-05 10:50:00.000000

Conforms to:
- docs/14-iam/IAM-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §3, §4
- INV-IAM-001, INV-IAM-002, INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '003_identity'
down_revision: Union[str, None] = '002_tenancy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Principals table (tenant-scoped)
    op.execute("""
    CREATE TABLE revpilot.principals (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        principal_type VARCHAR(32) NOT NULL DEFAULT 'USER',
        email VARCHAR(255) NOT NULL,
        display_name VARCHAR(255) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_principals PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_principals_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_principals_type CHECK (principal_type IN ('USER', 'SERVICE_ACCOUNT', 'AGENT', 'SYSTEM')),
        CONSTRAINT ck_principals_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'REVOKED', 'DELETED'))
    );
    CREATE INDEX idx_principals_tenant_email ON revpilot.principals (tenant_id, email);

    ALTER TABLE revpilot.principals ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.principals FORCE ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON revpilot.principals AS RESTRICTIVE
        USING (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        )
        WITH CHECK (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        );
    """)

    # 2. Memberships table (linking principal to organization with roles)
    op.execute("""
    CREATE TABLE revpilot.memberships (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        principal_id VARCHAR(64) NOT NULL,
        organization_id VARCHAR(64) NOT NULL,
        role_name VARCHAR(64) NOT NULL,
        granted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        revoked_at TIMESTAMPTZ,
        CONSTRAINT pk_memberships PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_memberships_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_memberships_principal FOREIGN KEY (tenant_id, principal_id)
            REFERENCES revpilot.principals (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT fk_memberships_org FOREIGN KEY (tenant_id, organization_id)
            REFERENCES revpilot.organizations (tenant_id, id) ON DELETE CASCADE
    );
    CREATE INDEX idx_memberships_tenant_principal ON revpilot.memberships (tenant_id, principal_id);

    ALTER TABLE revpilot.memberships ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.memberships FORCE ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON revpilot.memberships AS RESTRICTIVE
        USING (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        )
        WITH CHECK (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        );
    """)

    # 3. Delegations table (agent delegation tokens)
    op.execute("""
    CREATE TABLE revpilot.delegations (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        delegator_id VARCHAR(64) NOT NULL,
        task_id VARCHAR(64) NOT NULL,
        allowed_capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
        target_resources JSONB NOT NULL DEFAULT '[]'::jsonb,
        issued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMPTZ NOT NULL,
        revocation_version INT NOT NULL DEFAULT 1,
        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
        CONSTRAINT pk_delegations PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_delegations_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_delegations_delegator FOREIGN KEY (tenant_id, delegator_id)
            REFERENCES revpilot.principals (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_delegations_status CHECK (status IN ('ACTIVE', 'EXPIRED', 'REVOKED'))
    );
    CREATE INDEX idx_delegations_tenant_task ON revpilot.delegations (tenant_id, task_id, status);

    ALTER TABLE revpilot.delegations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.delegations FORCE ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON revpilot.delegations AS RESTRICTIVE
        USING (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        )
        WITH CHECK (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        );
    """)

    # 4. Revocations table
    op.execute("""
    CREATE TABLE revpilot.revocations (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        delegation_id VARCHAR(64) NOT NULL,
        revoked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        reason TEXT NOT NULL,
        revoked_by VARCHAR(64) NOT NULL,
        CONSTRAINT pk_revocations PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_revocations_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_revocations_delegation FOREIGN KEY (tenant_id, delegation_id)
            REFERENCES revpilot.delegations (tenant_id, id) ON DELETE CASCADE
    );
    CREATE INDEX idx_revocations_tenant_del ON revpilot.revocations (tenant_id, delegation_id);

    ALTER TABLE revpilot.revocations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.revocations FORCE ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON revpilot.revocations AS RESTRICTIVE
        USING (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        )
        WITH CHECK (
            current_setting('revpilot.is_system', true) = 'true'
            OR tenant_id = current_setting('revpilot.current_tenant_id', true)
        );
    """)

    # 5. Sessions table (JWT / Bearer token hashes and revocation tracking)
    op.execute("""
    CREATE TABLE revpilot.sessions (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        principal_id VARCHAR(64) NOT NULL,
        token_hash VARCHAR(128) NOT NULL,
        issued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMPTZ NOT NULL,
        revoked_at TIMESTAMPTZ,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        CONSTRAINT pk_sessions PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_sessions_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_sessions_principal FOREIGN KEY (tenant_id, principal_id)
            REFERENCES revpilot.principals (tenant_id, id) ON DELETE CASCADE
    );
    CREATE INDEX idx_sessions_token_hash ON revpilot.sessions (tenant_id, token_hash, is_active);

    ALTER TABLE revpilot.sessions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.sessions FORCE ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON revpilot.sessions AS RESTRICTIVE
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
    op.execute("DROP TABLE IF EXISTS revpilot.sessions CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.revocations CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.delegations CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.memberships CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.principals CASCADE;")
