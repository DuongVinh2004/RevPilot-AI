"""011_audit_event_tables

Revision ID: 011_audit_events
Revises: 010_connector_ingestion
Create Date: 2026-09-05 11:30:00.000000

Conforms to:
- docs/22-billing/AUDIT-LOG-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §2, §10
- INV-AUD-001 (Immutable Audit Trail), INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '011_audit_events'
down_revision: Union[str, None] = '010_connector_ingestion'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Audit Events (Append-only ledger with cryptographic hash chain)
    op.execute("""
    CREATE TABLE revpilot.audit_events (
        id VARCHAR(64) PRIMARY KEY,
        tenant_id VARCHAR(64) NOT NULL,
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        event_type VARCHAR(128) NOT NULL,
        actor_id VARCHAR(64) NOT NULL,
        actor_type VARCHAR(32) NOT NULL DEFAULT 'USER',
        delegation_id VARCHAR(64),
        resource VARCHAR(256) NOT NULL,
        action VARCHAR(64) NOT NULL,
        outcome VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
        correlation_id VARCHAR(64) NOT NULL,
        causation_id VARCHAR(64),
        details JSONB NOT NULL DEFAULT '{}'::jsonb,
        previous_event_hash VARCHAR(128) NOT NULL,
        event_hash VARCHAR(128) NOT NULL,
        CONSTRAINT fk_audit_events_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_audit_outcome CHECK (outcome IN ('SUCCESS', 'DENIED', 'FAILED', 'ERROR'))
    );
    CREATE INDEX idx_audit_events_tenant_timeline ON revpilot.audit_events (tenant_id, occurred_at DESC);
    CREATE INDEX idx_audit_events_correlation ON revpilot.audit_events (tenant_id, correlation_id);

    ALTER TABLE revpilot.audit_events ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.audit_events FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.audit_events AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));

    -- Immutable trigger: Blocks UPDATE and DELETE on audit_events
    CREATE OR REPLACE FUNCTION revpilot.prevent_audit_mutation() RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Audit events are immutable and cannot be updated or deleted (INV-AUD-001).';
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_audit_immutable
        BEFORE UPDATE OR DELETE ON revpilot.audit_events
        FOR EACH ROW EXECUTE FUNCTION revpilot.prevent_audit_mutation();
    """)

    # 2. Audit Checkpoints
    op.execute("""
    CREATE TABLE revpilot.audit_checkpoints (
        id VARCHAR(64) PRIMARY KEY,
        tenant_id VARCHAR(64) NOT NULL,
        checkpoint_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_event_id VARCHAR(64) NOT NULL,
        chain_digest VARCHAR(128) NOT NULL,
        verified_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_audit_checkpoints_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT
    );
    CREATE INDEX idx_audit_checkpoints_tenant ON revpilot.audit_checkpoints (tenant_id, checkpoint_time DESC);

    ALTER TABLE revpilot.audit_checkpoints ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.audit_checkpoints FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.audit_checkpoints AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.audit_checkpoints CASCADE;")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_immutable ON revpilot.audit_events;")
    op.execute("DROP FUNCTION IF EXISTS revpilot.prevent_audit_mutation();")
    op.execute("DROP TABLE IF EXISTS revpilot.audit_events CASCADE;")
