"""008_decision_budget_tables

Revision ID: 008_decision_budget
Revises: 007_hypothesis_causal
Create Date: 2026-09-05 11:15:00.000000

Conforms to:
- docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md
- docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md
- docs/08-ml-platform/ML-SYSTEM-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §10
- INV-COST-001, INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '008_decision_budget'
down_revision: Union[str, None] = '007_hypothesis_causal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Churn Predictions
    op.execute("""
    CREATE TABLE revpilot.churn_predictions (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        customer_id VARCHAR(64) NOT NULL,
        as_of_time TIMESTAMPTZ NOT NULL,
        model_artifact_id VARCHAR(64) NOT NULL,
        calibrated_probability NUMERIC(8,6) NOT NULL,
        risk_tier VARCHAR(16) NOT NULL,
        ece_at_release NUMERIC(6,4) NOT NULL,
        feature_snapshot_digest VARCHAR(128) NOT NULL,
        is_treatment_contaminated BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_churn_predictions PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_churn_predictions_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_churn_predictions_cust FOREIGN KEY (tenant_id, customer_id)
            REFERENCES revpilot.canonical_customers (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_churn_prob CHECK (calibrated_probability >= 0.000000 AND calibrated_probability <= 1.000000)
    );
    CREATE INDEX idx_churn_predictions_cust ON revpilot.churn_predictions (tenant_id, customer_id, as_of_time DESC);

    ALTER TABLE revpilot.churn_predictions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.churn_predictions FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.churn_predictions AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 2. Uplift Scores
    op.execute("""
    CREATE TABLE revpilot.uplift_scores (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        customer_id VARCHAR(64) NOT NULL,
        intervention_type VARCHAR(64) NOT NULL,
        cate_estimate NUMERIC(12,6) NOT NULL,
        standard_error NUMERIC(12,6) NOT NULL,
        confidence_interval JSONB NOT NULL DEFAULT '{}'::jsonb,
        persuadability_segment VARCHAR(32) NOT NULL,
        as_of_time TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_uplift_scores PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_uplift_scores_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_uplift_scores_cust FOREIGN KEY (tenant_id, customer_id)
            REFERENCES revpilot.canonical_customers (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_uplift_segment CHECK (persuadability_segment IN ('PERSUADABLE', 'SURE_THING', 'LOST_CAUSE', 'DO_NOT_DISTURB'))
    );
    CREATE INDEX idx_uplift_scores_cust ON revpilot.uplift_scores (tenant_id, customer_id, intervention_type);

    ALTER TABLE revpilot.uplift_scores ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.uplift_scores FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.uplift_scores AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 3. Decision Recommendations
    op.execute("""
    CREATE TABLE revpilot.decision_recommendations (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        investigation_id VARCHAR(64) NOT NULL,
        customer_id VARCHAR(64) NOT NULL,
        selected_action VARCHAR(64) NOT NULL,
        expected_utility NUMERIC(12,4) NOT NULL,
        constraint_results JSONB NOT NULL DEFAULT '{}'::jsonb,
        decision_digest VARCHAR(128) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'PROPOSED',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_decision_recommendations PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_decision_rec_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_decision_rec_inv FOREIGN KEY (tenant_id, investigation_id)
            REFERENCES revpilot.investigations (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT fk_decision_rec_cust FOREIGN KEY (tenant_id, customer_id)
            REFERENCES revpilot.canonical_customers (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_decision_status CHECK (status IN ('PROPOSED', 'SELECTED', 'ABSTAINED', 'REJECTED'))
    );
    CREATE INDEX idx_decision_rec_inv ON revpilot.decision_recommendations (tenant_id, investigation_id);

    ALTER TABLE revpilot.decision_recommendations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.decision_recommendations FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.decision_recommendations AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 4. Budget Ledger (with OCC version)
    op.execute("""
    CREATE TABLE revpilot.budget_ledger (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        ledger_date DATE NOT NULL,
        daily_budget_usd NUMERIC(10,2) NOT NULL,
        spent_usd NUMERIC(10,2) NOT NULL DEFAULT 0.00,
        reserved_usd NUMERIC(10,2) NOT NULL DEFAULT 0.00,
        version INT NOT NULL DEFAULT 1,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_budget_ledger PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_budget_ledger_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT uq_budget_ledger_date UNIQUE (tenant_id, ledger_date),
        CONSTRAINT ck_budget_positive CHECK (daily_budget_usd >= 0.00 AND spent_usd >= 0.00 AND reserved_usd >= 0.00)
    );
    CREATE INDEX idx_budget_ledger_date ON revpilot.budget_ledger (tenant_id, ledger_date);

    ALTER TABLE revpilot.budget_ledger ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.budget_ledger FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.budget_ledger AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.budget_ledger CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.decision_recommendations CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.uplift_scores CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.churn_predictions CASCADE;")
