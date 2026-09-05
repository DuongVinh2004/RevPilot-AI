"""007_hypothesis_causal_tables

Revision ID: 007_hypothesis_causal
Revises: 006_investigations
Create Date: 2026-09-05 11:10:00.000000

Conforms to:
- docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md
- docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §10
- INV-AI-001, INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '007_hypothesis_causal'
down_revision: Union[str, None] = '006_investigations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Causal Studies
    op.execute("""
    CREATE TABLE revpilot.causal_studies (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        investigation_id VARCHAR(64) NOT NULL,
        causal_question TEXT NOT NULL,
        treatment_variable VARCHAR(128) NOT NULL,
        outcome_variable VARCHAR(128) NOT NULL,
        estimand_type VARCHAR(16) NOT NULL DEFAULT 'ATE',
        estimator VARCHAR(32) NOT NULL DEFAULT 'DOUBLY_ROBUST_AIPW',
        point_estimate NUMERIC(12,6),
        standard_error NUMERIC(12,6),
        confidence_interval_95 JSONB NOT NULL DEFAULT '{}'::jsonb,
        p_value NUMERIC(8,6),
        overlap JSONB NOT NULL DEFAULT '{}'::jsonb,
        sensitivity JSONB NOT NULL DEFAULT '{}'::jsonb,
        reproducibility_seed BIGINT NOT NULL DEFAULT 42,
        study_digest VARCHAR(128) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_causal_studies PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_causal_studies_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_causal_studies_inv FOREIGN KEY (tenant_id, investigation_id)
            REFERENCES revpilot.investigations (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_causal_estimand CHECK (estimand_type IN ('ATE', 'ATT', 'ATC', 'CATE'))
    );
    CREATE INDEX idx_causal_studies_inv ON revpilot.causal_studies (tenant_id, investigation_id);

    ALTER TABLE revpilot.causal_studies ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.causal_studies FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.causal_studies AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 2. Hypotheses
    op.execute("""
    CREATE TABLE revpilot.hypotheses (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        investigation_id VARCHAR(64) NOT NULL,
        statement TEXT NOT NULL,
        epistemic_category VARCHAR(32) NOT NULL DEFAULT 'CAUSAL_HYPOTHESIS',
        hypothesis_type VARCHAR(64) NOT NULL,
        supporting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
        contradicting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
        evidence_coverage_ratio NUMERIC(5,4) NOT NULL DEFAULT 0.0000,
        ordinal_rank INT NOT NULL DEFAULT 1,
        ranking_score NUMERIC(8,4) NOT NULL DEFAULT 0.0000,
        status VARCHAR(32) NOT NULL DEFAULT 'PROPOSED',
        causal_study_id VARCHAR(64),
        manifest_digest VARCHAR(128) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_hypotheses PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_hypotheses_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_hypotheses_inv FOREIGN KEY (tenant_id, investigation_id)
            REFERENCES revpilot.investigations (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_hypotheses_status CHECK (status IN ('PROPOSED', 'EVALUATING', 'VERIFIED', 'PARTIALLY_SUPPORTED', 'REFUTED', 'NEED_MORE_EVIDENCE'))
    );
    CREATE INDEX idx_hypotheses_inv_rank ON revpilot.hypotheses (tenant_id, investigation_id, ordinal_rank);

    ALTER TABLE revpilot.hypotheses ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.hypotheses FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.hypotheses AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.hypotheses CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.causal_studies CASCADE;")
