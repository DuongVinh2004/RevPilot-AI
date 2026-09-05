"""013_data_quality_lineage_tables

Revision ID: 013_dq_lineage
Revises: 012_billing_finops
Create Date: 2026-09-05 11:40:00.000000

Conforms to:
- docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §10
- INV-DATA-001, INV-DATA-002, INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '013_dq_lineage'
down_revision: Union[str, None] = '012_billing_finops'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Canonical Lineage Log
    op.execute("""
    CREATE TABLE revpilot.canonical_lineage_log (
        tenant_id VARCHAR(64) NOT NULL,
        lineage_id VARCHAR(64) NOT NULL,
        source_system VARCHAR(64) NOT NULL,
        source_batch_id VARCHAR(128) NOT NULL,
        raw_payload_hash VARCHAR(128) NOT NULL,
        transformation_name VARCHAR(128) NOT NULL,
        transformation_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
        input_record_count INT NOT NULL DEFAULT 0,
        canonical_record_count INT NOT NULL DEFAULT 0,
        quarantined_record_count INT NOT NULL DEFAULT 0,
        executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        operator_id VARCHAR(64) NOT NULL,
        CONSTRAINT pk_canonical_lineage_log PRIMARY KEY (tenant_id, lineage_id),
        CONSTRAINT fk_lineage_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT
    );
    CREATE INDEX idx_lineage_log_timeline ON revpilot.canonical_lineage_log (tenant_id, source_system, executed_at DESC);

    ALTER TABLE revpilot.canonical_lineage_log ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.canonical_lineage_log FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.canonical_lineage_log AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 2. Raw Quarantine
    op.execute("""
    CREATE TABLE revpilot.raw_quarantine (
        tenant_id VARCHAR(64) NOT NULL,
        quarantine_id VARCHAR(64) NOT NULL,
        rule_id VARCHAR(32) NOT NULL,
        severity VARCHAR(16) NOT NULL DEFAULT 'HIGH',
        source_system VARCHAR(64) NOT NULL,
        source_id VARCHAR(128),
        raw_payload JSONB NOT NULL,
        rejection_reason TEXT NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'QUARANTINED',
        quarantined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMPTZ,
        resolved_by VARCHAR(64),
        CONSTRAINT pk_raw_quarantine PRIMARY KEY (tenant_id, quarantine_id),
        CONSTRAINT fk_raw_quarantine_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_raw_quarantine_status CHECK (status IN ('QUARANTINED', 'REPROCESSED', 'DISCARDED'))
    );
    CREATE INDEX idx_raw_quarantine_status ON revpilot.raw_quarantine (tenant_id, status, quarantined_at DESC);

    ALTER TABLE revpilot.raw_quarantine ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.raw_quarantine FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.raw_quarantine AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.raw_quarantine CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.canonical_lineage_log CASCADE;")
