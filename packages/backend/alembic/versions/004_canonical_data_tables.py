"""004_canonical_data_tables

Revision ID: 004_canonical_data
Revises: 003_identity
Create Date: 2026-09-05 10:55:00.000000

Conforms to:
- docs/07-data-platform/CANONICAL-DATA-MODEL.md
- docs/27-database/DATABASE-SCHEMA.md §10
- INV-TEN-001, INV-DATA-001, INV-DATA-002
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '004_canonical_data'
down_revision: Union[str, None] = '003_identity'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Customers
    op.execute("""
    CREATE TABLE revpilot.canonical_customers (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        schema_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
        source_system VARCHAR(64) NOT NULL,
        source_id VARCHAR(128) NOT NULL,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        segment VARCHAR(64) NOT NULL,
        account_tier VARCHAR(32) NOT NULL,
        billing_country VARCHAR(2) NOT NULL,
        contract_mrr_cents BIGINT NOT NULL DEFAULT 0,
        currency VARCHAR(3) NOT NULL DEFAULT 'USD',
        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
        event_time TIMESTAMPTZ NOT NULL,
        effective_from TIMESTAMPTZ NOT NULL,
        effective_to TIMESTAMPTZ,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        data_classification VARCHAR(32) NOT NULL DEFAULT 'CONFIDENTIAL',
        retention_class VARCHAR(32) NOT NULL DEFAULT 'REVENUE_FINANCIAL_7YR',
        lineage_trace_id VARCHAR(64) NOT NULL,
        dedup_key VARCHAR(128) NOT NULL,
        CONSTRAINT pk_canonical_customers PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_canonical_customers_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT uq_canonical_customers_source UNIQUE (tenant_id, source_system, source_id),
        CONSTRAINT ck_canonical_customers_mrr CHECK (contract_mrr_cents >= 0)
    );
    CREATE INDEX idx_canonical_customers_tenant_seg ON revpilot.canonical_customers (tenant_id, segment, status);

    ALTER TABLE revpilot.canonical_customers ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.canonical_customers FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.canonical_customers AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 2. Orders
    op.execute("""
    CREATE TABLE revpilot.canonical_orders (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        customer_id VARCHAR(64) NOT NULL,
        schema_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
        source_system VARCHAR(64) NOT NULL,
        source_id VARCHAR(128) NOT NULL,
        order_number VARCHAR(64) NOT NULL,
        order_status VARCHAR(32) NOT NULL,
        cancellation_reason VARCHAR(128),
        cancellation_requested_at TIMESTAMPTZ,
        cancelled_at TIMESTAMPTZ,
        currency VARCHAR(3) NOT NULL DEFAULT 'USD',
        subtotal_cents BIGINT NOT NULL,
        tax_cents BIGINT NOT NULL DEFAULT 0,
        shipping_cents BIGINT NOT NULL DEFAULT 0,
        total_cents BIGINT NOT NULL,
        event_time TIMESTAMPTZ NOT NULL,
        effective_from TIMESTAMPTZ NOT NULL,
        effective_to TIMESTAMPTZ,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        data_classification VARCHAR(32) NOT NULL DEFAULT 'CONFIDENTIAL',
        retention_class VARCHAR(32) NOT NULL DEFAULT 'REVENUE_FINANCIAL_7YR',
        lineage_trace_id VARCHAR(64) NOT NULL,
        dedup_key VARCHAR(128) NOT NULL,
        CONSTRAINT pk_canonical_orders PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_canonical_orders_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_canonical_orders_customer FOREIGN KEY (tenant_id, customer_id)
            REFERENCES revpilot.canonical_customers (tenant_id, id) ON DELETE RESTRICT,
        CONSTRAINT uq_canonical_orders_source UNIQUE (tenant_id, source_system, source_id),
        CONSTRAINT ck_canonical_orders_total CHECK (total_cents >= 0)
    );
    CREATE INDEX idx_canonical_orders_tenant_status ON revpilot.canonical_orders (tenant_id, order_status, event_time DESC);

    ALTER TABLE revpilot.canonical_orders ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.canonical_orders FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.canonical_orders AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 3. Order Items
    op.execute("""
    CREATE TABLE revpilot.canonical_order_items (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        order_id VARCHAR(64) NOT NULL,
        sku VARCHAR(64) NOT NULL,
        product_name VARCHAR(255) NOT NULL,
        product_category VARCHAR(64) NOT NULL,
        quantity INT NOT NULL,
        unit_price_cents BIGINT NOT NULL,
        total_price_cents BIGINT NOT NULL,
        event_time TIMESTAMPTZ NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_canonical_order_items PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_canonical_order_items_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_canonical_order_items_order FOREIGN KEY (tenant_id, order_id)
            REFERENCES revpilot.canonical_orders (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_order_items_qty CHECK (quantity > 0),
        CONSTRAINT ck_order_items_price CHECK (unit_price_cents >= 0)
    );
    CREATE INDEX idx_canonical_order_items_order ON revpilot.canonical_order_items (tenant_id, order_id);

    ALTER TABLE revpilot.canonical_order_items ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.canonical_order_items FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.canonical_order_items AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 4. Shipments
    op.execute("""
    CREATE TABLE revpilot.canonical_shipments (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        order_id VARCHAR(64) NOT NULL,
        carrier_id VARCHAR(64) NOT NULL,
        tracking_number VARCHAR(128) NOT NULL,
        warehouse_id VARCHAR(64) NOT NULL,
        shipment_status VARCHAR(32) NOT NULL,
        estimated_delivery_at TIMESTAMPTZ,
        actual_delivery_at TIMESTAMPTZ,
        delay_reason VARCHAR(128),
        event_time TIMESTAMPTZ NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_canonical_shipments PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_canonical_shipments_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_canonical_shipments_order FOREIGN KEY (tenant_id, order_id)
            REFERENCES revpilot.canonical_orders (tenant_id, id) ON DELETE CASCADE
    );
    CREATE INDEX idx_canonical_shipments_carrier ON revpilot.canonical_shipments (tenant_id, carrier_id, shipment_status);

    ALTER TABLE revpilot.canonical_shipments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.canonical_shipments FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.canonical_shipments AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 5. Payments
    op.execute("""
    CREATE TABLE revpilot.canonical_payments (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        order_id VARCHAR(64) NOT NULL,
        payment_processor VARCHAR(64) NOT NULL,
        processor_tx_id VARCHAR(128) NOT NULL,
        amount_cents BIGINT NOT NULL,
        currency VARCHAR(3) NOT NULL DEFAULT 'USD',
        payment_status VARCHAR(32) NOT NULL,
        failure_code VARCHAR(64),
        event_time TIMESTAMPTZ NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_canonical_payments PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_canonical_payments_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_canonical_payments_order FOREIGN KEY (tenant_id, order_id)
            REFERENCES revpilot.canonical_orders (tenant_id, id) ON DELETE RESTRICT,
        CONSTRAINT ck_payments_amount CHECK (amount_cents >= 0)
    );
    CREATE INDEX idx_canonical_payments_order ON revpilot.canonical_payments (tenant_id, order_id, payment_status);

    ALTER TABLE revpilot.canonical_payments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.canonical_payments FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.canonical_payments AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 6. Subscriptions
    op.execute("""
    CREATE TABLE revpilot.canonical_subscriptions (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        customer_id VARCHAR(64) NOT NULL,
        plan_name VARCHAR(64) NOT NULL,
        mrr_cents BIGINT NOT NULL,
        currency VARCHAR(3) NOT NULL DEFAULT 'USD',
        status VARCHAR(32) NOT NULL,
        effective_from TIMESTAMPTZ NOT NULL,
        effective_to TIMESTAMPTZ,
        event_time TIMESTAMPTZ NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_canonical_subscriptions PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_canonical_subscriptions_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_canonical_subscriptions_customer FOREIGN KEY (tenant_id, customer_id)
            REFERENCES revpilot.canonical_customers (tenant_id, id) ON DELETE RESTRICT,
        CONSTRAINT ck_subscriptions_mrr CHECK (mrr_cents >= 0)
    );
    CREATE INDEX idx_canonical_subscriptions_customer ON revpilot.canonical_subscriptions (tenant_id, customer_id, status);

    ALTER TABLE revpilot.canonical_subscriptions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.canonical_subscriptions FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.canonical_subscriptions AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 7. Support Tickets
    op.execute("""
    CREATE TABLE revpilot.canonical_support_tickets (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        customer_id VARCHAR(64) NOT NULL,
        subject_masked TEXT NOT NULL,
        body_masked TEXT NOT NULL,
        priority VARCHAR(32) NOT NULL,
        status VARCHAR(32) NOT NULL,
        category VARCHAR(64) NOT NULL,
        sentiment_score NUMERIC(5,4),
        injection_risk_score NUMERIC(5,4) NOT NULL DEFAULT 0.0000,
        is_quarantined BOOLEAN NOT NULL DEFAULT FALSE,
        content_digest VARCHAR(128) NOT NULL,
        event_time TIMESTAMPTZ NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_canonical_support_tickets PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_canonical_support_tickets_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_canonical_support_tickets_customer FOREIGN KEY (tenant_id, customer_id)
            REFERENCES revpilot.canonical_customers (tenant_id, id) ON DELETE RESTRICT
    );
    CREATE INDEX idx_canonical_tickets_customer ON revpilot.canonical_support_tickets (tenant_id, customer_id, status);

    ALTER TABLE revpilot.canonical_support_tickets ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.canonical_support_tickets FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.canonical_support_tickets AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.canonical_support_tickets CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.canonical_subscriptions CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.canonical_payments CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.canonical_shipments CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.canonical_order_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.canonical_orders CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.canonical_customers CASCADE;")
