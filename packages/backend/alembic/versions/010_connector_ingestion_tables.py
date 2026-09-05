"""010_connector_ingestion_tables

Revision ID: 010_connector_ingestion
Revises: 009_approval_action
Create Date: 2026-09-05 11:25:00.000000

Conforms to:
- docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §10
- INV-DATA-002, INV-SEC-001, INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '010_connector_ingestion'
down_revision: Union[str, None] = '009_approval_action'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Connectors
    op.execute("""
    CREATE TABLE revpilot.connectors (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        provider VARCHAR(64) NOT NULL,
        sync_mode VARCHAR(32) NOT NULL DEFAULT 'BATCH_PULL',
        auth_method VARCHAR(32) NOT NULL DEFAULT 'api_key_vault',
        secret_ref VARCHAR(128) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'CONFIGURED',
        schema_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
        last_sync_at TIMESTAMPTZ,
        consecutive_failures INT NOT NULL DEFAULT 0,
        config JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_connectors PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_connectors_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_connector_sync_mode CHECK (sync_mode IN ('BATCH_PULL', 'WEBHOOK_PUSH', 'CDC_STREAM')),
        CONSTRAINT ck_connector_status CHECK (status IN ('REGISTERED', 'CONFIGURED', 'VALIDATING', 'ACTIVE', 'DEGRADED', 'AUTH_EXPIRED', 'PAUSED', 'SCHEMA_DRIFT', 'QUARANTINED', 'RECONCILIATION_REQUIRED', 'DELETING', 'DELETED'))
    );
    CREATE INDEX idx_connectors_provider ON revpilot.connectors (tenant_id, provider, status);

    ALTER TABLE revpilot.connectors ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.connectors FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.connectors AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 2. Connector Sync States
    op.execute("""
    CREATE TABLE revpilot.connector_sync_states (
        tenant_id VARCHAR(64) NOT NULL,
        connector_id VARCHAR(64) NOT NULL,
        cursor_value TEXT,
        last_page_token TEXT,
        records_synced BIGINT NOT NULL DEFAULT 0,
        last_sync_status VARCHAR(32) NOT NULL DEFAULT 'IDLE',
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_connector_sync_states PRIMARY KEY (tenant_id, connector_id),
        CONSTRAINT fk_connector_sync_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_connector_sync_conn FOREIGN KEY (tenant_id, connector_id)
            REFERENCES revpilot.connectors (tenant_id, id) ON DELETE CASCADE
    );

    ALTER TABLE revpilot.connector_sync_states ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.connector_sync_states FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.connector_sync_states AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 3. Connector Inbox (Transactional Anti-Replay Inbound Events)
    op.execute("""
    CREATE TABLE revpilot.connector_inbox (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        connector_id VARCHAR(64) NOT NULL,
        external_event_id VARCHAR(256) NOT NULL,
        payload JSONB NOT NULL,
        payload_digest VARCHAR(128) NOT NULL,
        received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMPTZ,
        status VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
        CONSTRAINT pk_connector_inbox PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_connector_inbox_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_connector_inbox_conn FOREIGN KEY (tenant_id, connector_id)
            REFERENCES revpilot.connectors (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT uq_connector_inbox_replay UNIQUE (tenant_id, connector_id, external_event_id),
        CONSTRAINT ck_inbox_status CHECK (status IN ('RECEIVED', 'PROCESSING', 'PROCESSED', 'FAILED', 'QUARANTINED'))
    );
    CREATE INDEX idx_connector_inbox_status ON revpilot.connector_inbox (tenant_id, connector_id, status);

    ALTER TABLE revpilot.connector_inbox ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.connector_inbox FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.connector_inbox AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 4. Connector Quarantine
    op.execute("""
    CREATE TABLE revpilot.connector_quarantine (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        connector_id VARCHAR(64) NOT NULL,
        rule_id VARCHAR(32) NOT NULL,
        severity VARCHAR(16) NOT NULL DEFAULT 'HIGH',
        source_id VARCHAR(128),
        raw_payload JSONB NOT NULL,
        rejection_reason TEXT NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'QUARANTINED',
        quarantined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMPTZ,
        resolved_by VARCHAR(64),
        CONSTRAINT pk_connector_quarantine PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_connector_quarantine_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_connector_quarantine_conn FOREIGN KEY (tenant_id, connector_id)
            REFERENCES revpilot.connectors (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_quarantine_status CHECK (status IN ('QUARANTINED', 'REPROCESSED', 'DISCARDED'))
    );
    CREATE INDEX idx_connector_quarantine_conn ON revpilot.connector_quarantine (tenant_id, connector_id, status);

    ALTER TABLE revpilot.connector_quarantine ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.connector_quarantine FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.connector_quarantine AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.connector_quarantine CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.connector_inbox CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.connector_sync_states CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.connectors CASCADE;")
