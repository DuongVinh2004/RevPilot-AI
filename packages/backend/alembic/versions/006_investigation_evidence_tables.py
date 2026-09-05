"""006_investigation_evidence_tables

Revision ID: 006_investigations
Revises: 005_analytics
Create Date: 2026-09-05 11:05:00.000000

Conforms to:
- docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md
- docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §10
- INV-WF-001, INV-EVD-001, INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '006_investigations'
down_revision: Union[str, None] = '005_analytics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Investigations
    op.execute("""
    CREATE TABLE revpilot.investigations (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        anomaly_id VARCHAR(64) NOT NULL,
        metric_name VARCHAR(64) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'INITIALIZING',
        workflow_id VARCHAR(128) NOT NULL,
        investigation_scope JSONB NOT NULL DEFAULT '{}'::jsonb,
        cost_budget_usd NUMERIC(8,2) NOT NULL DEFAULT 2.00,
        time_budget_seconds INT NOT NULL DEFAULT 300,
        tool_call_budget INT NOT NULL DEFAULT 20,
        spent_usd NUMERIC(8,2) NOT NULL DEFAULT 0.00,
        spent_tokens BIGINT NOT NULL DEFAULT 0,
        spent_tool_calls INT NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMPTZ,
        CONSTRAINT pk_investigations PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_investigations_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_investigations_anomaly FOREIGN KEY (tenant_id, anomaly_id)
            REFERENCES revpilot.anomaly_records (tenant_id, id) ON DELETE RESTRICT,
        CONSTRAINT ck_investigations_status CHECK (status IN ('INITIALIZING', 'PLANNING', 'GATHERING_EVIDENCE', 'VERIFYING', 'COMPLETED', 'NEED_MORE_EVIDENCE', 'FAILED', 'PAUSED', 'CANCELLED'))
    );
    CREATE INDEX idx_investigations_tenant_status ON revpilot.investigations (tenant_id, status, created_at DESC);

    ALTER TABLE revpilot.investigations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.investigations FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.investigations AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 2. Investigation Plans
    op.execute("""
    CREATE TABLE revpilot.investigation_plans (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        investigation_id VARCHAR(64) NOT NULL,
        tasks JSONB NOT NULL DEFAULT '[]'::jsonb,
        max_concurrency INT NOT NULL DEFAULT 4,
        estimated_cost_usd NUMERIC(8,2) NOT NULL DEFAULT 0.00,
        version INT NOT NULL DEFAULT 1,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_investigation_plans PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_investigation_plans_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_investigation_plans_inv FOREIGN KEY (tenant_id, investigation_id)
            REFERENCES revpilot.investigations (tenant_id, id) ON DELETE CASCADE
    );
    CREATE INDEX idx_investigation_plans_inv ON revpilot.investigation_plans (tenant_id, investigation_id);

    ALTER TABLE revpilot.investigation_plans ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.investigation_plans FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.investigation_plans AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 3. Evidence Records
    op.execute("""
    CREATE TABLE revpilot.evidence_records (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        investigation_id VARCHAR(64) NOT NULL,
        source_system VARCHAR(64) NOT NULL,
        source_object_ref VARCHAR(255) NOT NULL,
        content_digest VARCHAR(128) NOT NULL,
        classification VARCHAR(32) NOT NULL DEFAULT 'INTERNAL',
        extraction_method VARCHAR(64) NOT NULL,
        retrieval_method VARCHAR(64) NOT NULL,
        citation_span JSONB NOT NULL DEFAULT '{}'::jsonb,
        confidence_score NUMERIC(5,4) NOT NULL DEFAULT 1.0000,
        supersession_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
        effective_time TIMESTAMPTZ NOT NULL,
        as_of_time TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_evidence_records PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_evidence_records_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_evidence_records_inv FOREIGN KEY (tenant_id, investigation_id)
            REFERENCES revpilot.investigations (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_evidence_status CHECK (supersession_status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'EXPIRED'))
    );
    CREATE INDEX idx_evidence_records_inv ON revpilot.evidence_records (tenant_id, investigation_id, source_system);

    ALTER TABLE revpilot.evidence_records ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.evidence_records FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.evidence_records AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 4. Evidence Bundles
    op.execute("""
    CREATE TABLE revpilot.evidence_bundles (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        investigation_id VARCHAR(64) NOT NULL,
        evidence_count INT NOT NULL DEFAULT 0,
        evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
        bundle_digest VARCHAR(128) NOT NULL,
        sealed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_evidence_bundles PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_evidence_bundles_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_evidence_bundles_inv FOREIGN KEY (tenant_id, investigation_id)
            REFERENCES revpilot.investigations (tenant_id, id) ON DELETE CASCADE
    );
    CREATE INDEX idx_evidence_bundles_inv ON revpilot.evidence_bundles (tenant_id, investigation_id);

    ALTER TABLE revpilot.evidence_bundles ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.evidence_bundles FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.evidence_bundles AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.evidence_bundles CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.evidence_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.investigation_plans CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.investigations CASCADE;")
