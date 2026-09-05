"""009_approval_action_tables

Revision ID: 009_approval_action
Revises: 008_decision_budget
Create Date: 2026-09-05 11:20:00.000000

Conforms to:
- docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md
- docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §10
- INV-ACT-001, INV-ACT-002, INV-ACT-003, INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '009_approval_action'
down_revision: Union[str, None] = '008_decision_budget'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Approval Requests
    op.execute("""
    CREATE TABLE revpilot.approval_requests (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        decision_id VARCHAR(64),
        action_type VARCHAR(64) NOT NULL,
        target_entity_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
        payload_digest VARCHAR(128) NOT NULL,
        policy_digest VARCHAR(128) NOT NULL,
        estimated_cost_usd NUMERIC(10,2) NOT NULL DEFAULT 0.00,
        required_approval_tier VARCHAR(16) NOT NULL DEFAULT 'TIER_1',
        approver_principal_id VARCHAR(64),
        status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
        rejection_reason TEXT,
        expiry_time TIMESTAMPTZ NOT NULL,
        correlation_id VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_approval_requests PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_approval_requests_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_approval_tier CHECK (required_approval_tier IN ('TIER_1', 'TIER_2', 'TIER_3')),
        CONSTRAINT ck_approval_status CHECK (status IN ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'AMENDED', 'EXPIRED', 'REVOKED', 'SUPERSEDED', 'EXECUTING', 'COMPLETED', 'UNKNOWN', 'RECONCILIATION_REQUIRED'))
    );
    CREATE INDEX idx_approval_requests_status ON revpilot.approval_requests (tenant_id, status, expiry_time);

    ALTER TABLE revpilot.approval_requests ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.approval_requests FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.approval_requests AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 2. Action Intents
    op.execute("""
    CREATE TABLE revpilot.action_intents (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        approval_id VARCHAR(64) NOT NULL,
        idempotency_key VARCHAR(128) NOT NULL,
        action_type VARCHAR(64) NOT NULL,
        classification VARCHAR(32) NOT NULL DEFAULT 'REVERSIBLE',
        is_dry_run BOOLEAN NOT NULL DEFAULT FALSE,
        max_retries INT NOT NULL DEFAULT 3,
        timeout_seconds INT NOT NULL DEFAULT 30,
        payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        payload_digest VARCHAR(128) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_action_intents PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_action_intents_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_action_intents_approval FOREIGN KEY (tenant_id, approval_id)
            REFERENCES revpilot.approval_requests (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT uq_action_intents_idempotency UNIQUE (tenant_id, idempotency_key),
        CONSTRAINT ck_action_intent_class CHECK (classification IN ('REVERSIBLE', 'COMPENSATABLE', 'PARTIALLY_COMPENSATABLE', 'IRREVERSIBLE', 'MANUAL_RECONCILIATION'))
    );
    CREATE INDEX idx_action_intents_approval ON revpilot.action_intents (tenant_id, approval_id);

    ALTER TABLE revpilot.action_intents ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.action_intents FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.action_intents AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 3. Action Ledger
    op.execute("""
    CREATE TABLE revpilot.action_ledger (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        intent_id VARCHAR(64) NOT NULL,
        attempt_number INT NOT NULL DEFAULT 1,
        provider_name VARCHAR(64) NOT NULL,
        provider_tx_id VARCHAR(128),
        execution_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
        http_status_code INT,
        request_digest VARCHAR(128) NOT NULL,
        response_digest VARCHAR(128),
        started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMPTZ,
        CONSTRAINT pk_action_ledger PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_action_ledger_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_action_ledger_intent FOREIGN KEY (tenant_id, intent_id)
            REFERENCES revpilot.action_intents (tenant_id, id) ON DELETE CASCADE,
        CONSTRAINT ck_action_ledger_status CHECK (execution_status IN ('PENDING', 'SUCCESS', 'PROVIDER_ERROR', 'TIMEOUT_UNKNOWN', 'RECONCILED', 'COMPENSATED'))
    );
    CREATE INDEX idx_action_ledger_intent ON revpilot.action_ledger (tenant_id, intent_id, attempt_number);

    ALTER TABLE revpilot.action_ledger ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.action_ledger FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.action_ledger AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 4. Kill Switches (Platform-scoped registry, no RLS)
    op.execute("""
    CREATE TABLE revpilot.kill_switches (
        id VARCHAR(64) PRIMARY KEY,
        scope VARCHAR(32) NOT NULL,
        target_id VARCHAR(128),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        reason TEXT NOT NULL,
        activated_by VARCHAR(64) NOT NULL,
        activated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        deactivated_at TIMESTAMPTZ,
        CONSTRAINT ck_kill_scope CHECK (scope IN ('GLOBAL', 'TENANT', 'CAPABILITY', 'PROVIDER', 'INVESTIGATION'))
    );
    CREATE INDEX idx_kill_switches_lookup ON revpilot.kill_switches (scope, is_active);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.kill_switches CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.action_ledger CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.action_intents CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.approval_requests CASCADE;")
