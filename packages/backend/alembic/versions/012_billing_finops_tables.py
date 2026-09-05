"""012_billing_finops_tables

Revision ID: 012_billing_finops
Revises: 011_audit_events
Create Date: 2026-09-05 11:35:00.000000

Conforms to:
- docs/21-finops/FINOPS-SPEC.md
- docs/22-billing/BILLING-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §10
- INV-COST-001, INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '012_billing_finops'
down_revision: Union[str, None] = '011_audit_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Billing Plans (Platform Catalog, No RLS)
    op.execute("""
    CREATE TABLE revpilot.billing_plans (
        id VARCHAR(64) PRIMARY KEY,
        name VARCHAR(128) NOT NULL,
        tier VARCHAR(32) NOT NULL DEFAULT 'SHARED',
        base_price_cents BIGINT NOT NULL DEFAULT 0,
        token_quota BIGINT NOT NULL DEFAULT 20000000,
        connector_limit INT NOT NULL DEFAULT 2,
        features JSONB NOT NULL DEFAULT '{}'::jsonb,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Subscriptions
    op.execute("""
    CREATE TABLE revpilot.subscriptions (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        plan_id VARCHAR(64) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
        started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMPTZ,
        auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_subscriptions PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_subscriptions_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_subscriptions_plan FOREIGN KEY (plan_id)
            REFERENCES revpilot.billing_plans (id) ON DELETE RESTRICT,
        CONSTRAINT ck_sub_status CHECK (status IN ('ACTIVE', 'PAST_DUE', 'RESTRICTED', 'CANCELLED', 'EXPIRED'))
    );
    CREATE INDEX idx_subscriptions_tenant ON revpilot.subscriptions (tenant_id, status);

    ALTER TABLE revpilot.subscriptions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.subscriptions FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.subscriptions AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 3. Usage Records
    op.execute("""
    CREATE TABLE revpilot.usage_records (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        resource_type VARCHAR(64) NOT NULL,
        quantity BIGINT NOT NULL,
        unit VARCHAR(32) NOT NULL DEFAULT 'TOKENS',
        recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        CONSTRAINT pk_usage_records PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_usage_records_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_usage_qty CHECK (quantity >= 0)
    );
    CREATE INDEX idx_usage_records_tenant_time ON revpilot.usage_records (tenant_id, resource_type, recorded_at DESC);

    ALTER TABLE revpilot.usage_records ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.usage_records FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.usage_records AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 4. Cost Allocations (FinOps)
    op.execute("""
    CREATE TABLE revpilot.cost_allocations (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        usage_record_id VARCHAR(64),
        cost_usd NUMERIC(10,4) NOT NULL,
        provider VARCHAR(64) NOT NULL,
        allocation_date DATE NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_cost_allocations PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_cost_allocations_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_cost_usd CHECK (cost_usd >= 0.0000)
    );
    CREATE INDEX idx_cost_allocations_date ON revpilot.cost_allocations (tenant_id, allocation_date);

    ALTER TABLE revpilot.cost_allocations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.cost_allocations FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.cost_allocations AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 5. Billing Records (Invoices)
    op.execute("""
    CREATE TABLE revpilot.billing_records (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        subscription_id VARCHAR(64) NOT NULL,
        period_start DATE NOT NULL,
        period_end DATE NOT NULL,
        total_cents BIGINT NOT NULL DEFAULT 0,
        status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
        invoice_digest VARCHAR(128),
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        finalized_at TIMESTAMPTZ,
        CONSTRAINT pk_billing_records PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_billing_records_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_billing_records_sub FOREIGN KEY (tenant_id, subscription_id)
            REFERENCES revpilot.subscriptions (tenant_id, id) ON DELETE RESTRICT,
        CONSTRAINT ck_billing_status CHECK (status IN ('DRAFT', 'PROVISIONAL', 'FINALIZED', 'ADJUSTED'))
    );
    CREATE INDEX idx_billing_records_tenant ON revpilot.billing_records (tenant_id, period_start);

    ALTER TABLE revpilot.billing_records ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.billing_records FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.billing_records AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 6. Credit Ledger
    op.execute("""
    CREATE TABLE revpilot.credit_ledger (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        billing_record_id VARCHAR(64),
        credit_cents BIGINT NOT NULL,
        reason TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_credit_ledger PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_credit_ledger_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_credit_cents CHECK (credit_cents > 0)
    );
    CREATE INDEX idx_credit_ledger_tenant ON revpilot.credit_ledger (tenant_id, created_at DESC);

    ALTER TABLE revpilot.credit_ledger ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.credit_ledger FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.credit_ledger AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.credit_ledger CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.billing_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.cost_allocations CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.usage_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.subscriptions CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.billing_plans CASCADE;")
