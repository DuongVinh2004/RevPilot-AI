# Database Schema and Persistence Isolation Specification (Rail 5 Canonical Contract)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Rail Alignment: Rail 5 (Persistence Isolation)
Owner: Data Architecture + Security Architecture
Traceability: `INV-TEN-001`, `INV-TEN-002`, `INV-TEN-003`, `INV-DATA-001`, `INV-DATA-002`, `NFR-TEN-001`, `NFR-TEN-002`, `ADR-0001`, `ADR-0004`, `ADR-0005`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Executive Summary and Invariants

This specification defines the persistence isolation architecture, database schema standards, and relational safety mechanisms for RevPilot AI. It operationalizes PostgreSQL as the primary authoritative relational persistence store (`ADR-0004`), enforcing tenant isolation through composite constraints, strict role boundaries, and PostgreSQL Row-Level Security (RLS) (`ADR-0005`).

### Architectural Invariants
1. `INV-TEN-001`: Every tenant-owned persistent/derived record has enforceable Tenant ownership; an application query filter alone is insufficient.
2. `INV-TEN-002`: Tenant context is server-derived from authenticated membership and cannot be supplied/overridden by client or model payload.
3. `INV-TEN-003`: Global/platform operations use an explicit privileged context, never `tenant = null`.
4. `INV-DATA-001`: Metric semantics and `as_of` are versioned; training/backtests cannot use future information.
5. `INV-DATA-002`: Source systems remain authoritative; derived stores are rebuildable projections.
6. `NFR-TEN-001`: Cross-tenant data leakage must equal zero (0).
7. `NFR-TEN-002`: Isolation controls hold at 120% peak load; never disable isolation for availability.

---

## 2. Data Classification and Storage Taxonomy

Data within RevPilot is strictly categorized into four architectural families:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                            RevPilot Data Taxonomy                             │
├────────────────────────┬────────────────────────┬────────────────────────────┤
│ Category               │ Mutability             │ Store & Authority          │
├────────────────────────┼────────────────────────┼────────────────────────────┤
│ 1. Source Transactional│ Read/Write (ACID)      │ PostgreSQL (Authoritative) │
│ 2. Immutable Audit     │ Append-Only (WORM)     │ PostgreSQL Audit + WORM    │
│ 3. Derived Projections │ Rebuildable / Read-Only│ Vector/Elastic/Caches      │
│ 4. Operational Metadata│ Bounded Ephemeral      │ Redis / Valkey / Logs      │
└────────────────────────┴────────────────────────┴────────────────────────────┘
```

1. **Source-of-Truth Transactional Data**: Entities owned by modular-monolith domains (Tenants, Users, Investigations, Hypotheses, Decisions, Policies, Approvals, Actions, Connectors). Stored exclusively in PostgreSQL tables with transactional aggregate boundaries.
2. **Immutable Audit Data**: High-integrity log of security, policy, and action changes (`AuditEvent`, `IntegrityCheckpoint`). Append-only, non-updatable, tamper-evident.
3. **Derived / Rebuildable Data**: Document chunks, embeddings, search indexes, feature tables, analytical aggregations. Always rebuildable from source transactional aggregates. Derived stores never grant authority absent source PostgreSQL validation.
4. **Operational Metadata**: Bounded cache keys, session tokens, cursor paginations, distributed locks, rate-limit counters. Stored in memory or transient key-value stores.

---

## 3. Transactional Aggregate Ownership and Module Boundaries

Per `ADR-0001` and `docs/04-system-architecture/MODULE-BOUNDARIES.md`:
- **Exclusive Ownership**: Exactly one module owns write operations for each table or aggregate.
- **Cross-Module Isolation**: No direct database foreign keys or joins across module boundaries. A module accesses data owned by another module strictly through published query/command ports or domain events.
- **Transaction Scope**: A single database transaction must not cross module ownership boundaries without explicit architectural exception review.

### Table Ownership Map

| Module | Owned Tables / Aggregates | Persistence Port Interface |
|---|---|---|
| `tenancy` | `tenants`, `organizations`, `entitlements` | `TenantRepositoryPort` |
| `identity` | `principals`, `memberships`, `roles`, `delegations`, `revocations` | `IdentityRepositoryPort` |
| `investigations` | `investigations`, `investigation_runs`, `hypotheses`, `decision_refs` | `InvestigationRepositoryPort`|
| `evidence` | `evidence_records`, `evidence_bundles`, `provenance_chains` | `EvidenceRepositoryPort` |
| `policy` | `policy_definitions`, `policy_versions`, `policy_evaluations` | `PolicyRepositoryPort` |
| `approvals` | `approval_requests`, `approvals`, `approval_digests` | `ApprovalRepositoryPort` |
| `actions` | `actions`, `action_attempts`, `action_ledgers`, `kill_switches` | `ActionLedgerPort` |
| `connectors` | `connectors`, `connector_sync_states`, `provider_capabilities` | `ConnectorRepositoryPort` |
| `audit` | `audit_events`, `audit_checkpoints` | `AuditAppendPort`, `AuditQueryPort`|
| `usage` | `usage_records`, `cost_allocations` | `UsageRepositoryPort` |
| `billing` | `plans`, `subscriptions`, `billing_records`, `credit_ledgers` | `BillingRepositoryPort` |

---

## 4. Tenant-Scoped Keys and Primary Key Strategy

### 4.1. Composite Primary and Unique Constraints
All tenant-owned tables MUST include `tenant_id` as part of their composite primary key and composite unique constraints:

```sql
-- Standard Tenant-Owned Table Template
CREATE TABLE investigations (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    organization_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_investigations PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_investigations_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) ON DELETE RESTRICT
);
```

### 4.2. Indexing Strategy
1. **Tenant-Prefixed Indexes**: Every index on a tenant-owned table must specify `tenant_id` as the leading column:
   ```sql
   CREATE INDEX idx_investigations_tenant_status
       ON investigations (tenant_id, status, created_at DESC);
   ```
2. **No Unscoped Foreign Keys**: Foreign keys between tables within the same module MUST be composite:
   ```sql
   CONSTRAINT fk_runs_investigation FOREIGN KEY (tenant_id, investigation_id)
       REFERENCES investigations (tenant_id, id) ON DELETE CASCADE
   ```

---

## 5. PostgreSQL Row-Level Security (RLS) Policy Model

Row-Level Security serves as the second, independent layer of defense (`ADR-0005`, `INV-TEN-001`). Even if application code has a query defect, the database engine enforces tenant boundaries.

### 5.1. Table Configuration
Every tenant-owned table MUST enable and force RLS:
```sql
ALTER TABLE investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigations FORCE ROW LEVEL SECURITY; -- Enforces for table owners too
```

### 5.2. Tenant Isolation Policy Definition
The canonical tenant isolation policy checks the transaction-scoped session setting:
```sql
CREATE POLICY tenant_isolation_policy ON investigations
    AS RESTRICTIVE
    USING (
        -- Allow if explicit system privileged override
        current_setting('revpilot.is_system', true) = 'true'
        OR
        -- Strictly match current tenant setting
        tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR
        tenant_id = current_setting('revpilot.current_tenant_id', true)
    );
```

### 5.3. Fail-Closed Null Context Evaluation
- The PostgreSQL function `current_setting('revpilot.current_tenant_id', true)` passes `true` as the second argument (missing_ok). If the setting has not been explicitly configured in the current transaction, it evaluates to `NULL`.
- In SQL logic, `tenant_id = NULL` evaluates to `UNKNOWN` (falsy in boolean filter context).
- Therefore, if no tenant context is set, **0 rows are visible and 0 rows can be inserted/updated/deleted**. The database fails closed by default.

---

## 6. Transaction-Scoped Context Management

Database connection pools reuse physical connections. To prevent cross-tenant contamination:

### 6.1. Transaction Lifecycle
1. **Acquire Connection**: Connection leased from pool in clean state.
2. **Begin Transaction**: `BEGIN;`
3. **Establish Tenant Context**:
   ```sql
   -- For tenant-owned operations:
   SET LOCAL revpilot.current_tenant_id = 'ten_01h7abcde123456789';
   SET LOCAL revpilot.is_system = 'false';

   -- For privileged platform operations:
   SET LOCAL revpilot.current_tenant_id = '';
   SET LOCAL revpilot.is_system = 'true';
   ```
   *Note: `SET LOCAL` guarantees the setting is automatically reset upon `COMMIT` or `ROLLBACK`.*
4. **Execute Queries**: Repository executes queries within active transaction.
5. **Commit/Rollback & Clear**:
   ```sql
   COMMIT; -- or ROLLBACK;
   DISCARD TEMP; -- or RESET ALL if manual cleanup required
   ```
6. **Release Connection**: Connection returned to pool clean.

### 6.2. Python Session Context Manager
In the application/adapter layer, context management is encapsulated in an immutable context manager:
```python
class TenantDatabaseSession:
    def __init__(self, connection: Connection, context: TenantContext):
        self._conn = connection
        self._context = context

    def __enter__(self):
        cursor = self._conn.cursor()
        if self._context.is_system:
            cursor.execute("SET LOCAL revpilot.is_system = 'true';")
            cursor.execute("SET LOCAL revpilot.current_tenant_id = '';")
        else:
            cursor.execute("SET LOCAL revpilot.is_system = 'false';")
            cursor.execute(
                "SET LOCAL revpilot.current_tenant_id = %s;",
                (str(self._context.tenant_id),)
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Transaction commit or rollback happens at transaction boundary;
        # SET LOCAL settings expire automatically with transaction.
        pass
```

---

## 7. Database Roles and Principle of Least Privilege

PostgreSQL database roles are segregated according to duty:

1. `revpilot_app`: Used by the running application service.
   - Has `SELECT`, `INSERT`, `UPDATE`, `DELETE` on tenant tables.
   - CANNOT alter schemas, create tables, or drop databases.
   - RLS is forced; cannot bypass RLS.
2. `revpilot_migrator`: Used strictly during deployment pipelines to run schema migrations.
   - Has DDL rights (`CREATE`, `ALTER`, `DROP`).
   - Does NOT handle live customer application traffic.
3. `revpilot_readonly`: Used for reporting, analytics replicas, and compliance auditor queries.
   - Has `SELECT` only. RLS is enforced.
4. `revpilot_admin`: Break-glass database administration role.
   - Strictly reserved for emergency DBA operations. Access is alerted and audited.

---

## 8. Schema Migration Strategy: Expand/Contract

Per `ADR-0004`:
1. **Zero-Downtime Rule**: Migrations must never lock entire tables or break backward compatibility with the immediately preceding application version.
2. **Expand Phase**: Add new nullable columns, create new tables, establish dual-write adapters. Old code continues reading old schema.
3. **Backfill Phase**: Asynchronous, rate-limited backfill jobs populate new columns for historical rows. Backfill runs with explicit tenant context and verification checksums.
4. **Contract Phase**: Once all running application nodes are upgraded and historical rows are verified, old columns/views are removed in a subsequent release.
5. **Prohibited Migrations**: Renaming columns in place, adding non-null columns without default, removing tables without prior deprecation release.

---

## 9. Failure Behavior and Cross-Tenant Persistence Matrix

| Scenario | Trigger / Condition | Enforcing Mechanism | Failure Behavior |
|---|---|---|---|
| **No Session Setting** | Query executed without `SET LOCAL revpilot.current_tenant_id` | RLS Policy | Returns 0 rows on SELECT; raises RLS violation on INSERT/UPDATE |
| **Invalid Tenant ID** | Session setting set to non-existent or invalid tenant | RLS Policy + FK Constraints | Rejects foreign key check; isolates to empty set |
| **Cross-Tenant SELECT** | Query explicitly injects `WHERE tenant_id = 'ten_B'` while session is `ten_A` | RLS Policy | Returns 0 rows (RLS overrides application WHERE clause) |
| **Cross-Tenant INSERT** | Insert payload has `tenant_id = 'ten_B'` while session is `ten_A` | RLS `WITH CHECK` | Raises `insufficient_privilege` / RLS check violation |
| **Cross-Tenant UPDATE** | Update targets `id` belonging to Tenant B while session is `ten_A` | RLS Policy | 0 rows affected |
| **Connection Leak** | Connection returned to pool without clearing session settings | Pool Checkout Hook | Pool reset handler runs `DISCARD ALL` / `RESET ALL` before checkout |
| **System Override Misuse**| Non-system actor attempts to set `revpilot.is_system = 'true'` | Application Session Boundary | Raises `AuthorizationError` / denies context creation |

---

## 10. Phase 01 Canonical Relational Tables

Per `docs/07-data-platform/CANONICAL-DATA-MODEL.md`, the following DDL definitions establish Phase 01 business entities. Every table enforces composite tenant keys, foreign keys within tenant scope, and mandatory RLS.

```sql
-- 1. Customers Table
CREATE TABLE canonical_customers (
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
    CONSTRAINT uq_canonical_customers_source UNIQUE (tenant_id, source_system, source_id),
    CONSTRAINT ck_canonical_customers_mrr CHECK (contract_mrr_cents >= 0)
);
ALTER TABLE canonical_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_customers FORCE ROW LEVEL SECURITY;

-- 2. Orders Table
CREATE TABLE canonical_orders (
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
    sla_delivery_deadline TIMESTAMPTZ NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_classification VARCHAR(32) NOT NULL DEFAULT 'CONFIDENTIAL',
    retention_class VARCHAR(32) NOT NULL DEFAULT 'REVENUE_FINANCIAL_7YR',
    lineage_trace_id VARCHAR(64) NOT NULL,
    dedup_key VARCHAR(128) NOT NULL,
    CONSTRAINT pk_canonical_orders PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_canonical_orders_customer FOREIGN KEY (tenant_id, customer_id)
        REFERENCES canonical_customers (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_canonical_orders_total CHECK (total_cents = subtotal_cents + tax_cents + shipping_cents AND total_cents >= 0)
);
ALTER TABLE canonical_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_orders FORCE ROW LEVEL SECURITY;

-- 3. Order Lines Table
CREATE TABLE canonical_order_lines (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    order_id VARCHAR(64) NOT NULL,
    sku VARCHAR(64) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    product_category VARCHAR(64) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price_cents BIGINT NOT NULL,
    total_price_cents BIGINT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_canonical_order_lines PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_canonical_order_lines_order FOREIGN KEY (tenant_id, order_id)
        REFERENCES canonical_orders (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT ck_canonical_order_lines_qty CHECK (quantity > 0 AND total_price_cents = quantity * unit_price_cents)
);
ALTER TABLE canonical_order_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_order_lines FORCE ROW LEVEL SECURITY;

-- 4. Shipments Table
CREATE TABLE canonical_shipments (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    order_id VARCHAR(64) NOT NULL,
    tracking_number VARCHAR(128) NOT NULL,
    carrier_id VARCHAR(64) NOT NULL,
    carrier_name VARCHAR(128) NOT NULL,
    warehouse_id VARCHAR(64) NOT NULL,
    origin_region VARCHAR(64) NOT NULL,
    destination_region VARCHAR(64) NOT NULL,
    dispatch_status VARCHAR(32) NOT NULL,
    dispatched_at TIMESTAMPTZ,
    estimated_delivery_at TIMESTAMPTZ NOT NULL,
    actual_delivered_at TIMESTAMPTZ,
    delay_reason VARCHAR(128),
    is_delayed BOOLEAN NOT NULL DEFAULT FALSE,
    event_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_canonical_shipments PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_canonical_shipments_order FOREIGN KEY (tenant_id, order_id)
        REFERENCES canonical_orders (tenant_id, id) ON DELETE RESTRICT
);
ALTER TABLE canonical_shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_shipments FORCE ROW LEVEL SECURITY;

-- 5. Support Tickets Table
CREATE TABLE canonical_support_tickets (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    customer_id VARCHAR(64) NOT NULL,
    order_id VARCHAR(64),
    ticket_number VARCHAR(64) NOT NULL,
    topic VARCHAR(64) NOT NULL,
    priority VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    transcript_text TEXT NOT NULL,
    first_response_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    event_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_canonical_support_tickets PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_canonical_tickets_customer FOREIGN KEY (tenant_id, customer_id)
        REFERENCES canonical_customers (tenant_id, id) ON DELETE RESTRICT
);
ALTER TABLE canonical_support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_support_tickets FORCE ROW LEVEL SECURITY;

-- 6. Maintenance Events Table
CREATE TABLE canonical_maintenance_events (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    facility_id VARCHAR(64) NOT NULL,
    facility_type VARCHAR(32) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    start_window TIMESTAMPTZ NOT NULL,
    end_window TIMESTAMPTZ,
    impact_capacity_reduction_pct NUMERIC(5,2) NOT NULL,
    description TEXT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_canonical_maintenance_events PRIMARY KEY (tenant_id, id),
    CONSTRAINT ck_maintenance_reduction CHECK (impact_capacity_reduction_pct BETWEEN 0.00 AND 100.00)
);
ALTER TABLE canonical_maintenance_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_maintenance_events FORCE ROW LEVEL SECURITY;

-- 7. Contracts and Clauses Tables
CREATE TABLE canonical_contracts (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    customer_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    contract_type VARCHAR(32) NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    document_uri VARCHAR(512) NOT NULL,
    document_digest VARCHAR(64) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_canonical_contracts PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_canonical_contracts_customer FOREIGN KEY (tenant_id, customer_id)
        REFERENCES canonical_customers (tenant_id, id) ON DELETE RESTRICT
);
ALTER TABLE canonical_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_contracts FORCE ROW LEVEL SECURITY;

CREATE TABLE canonical_contract_clauses (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    contract_id VARCHAR(64) NOT NULL,
    clause_number VARCHAR(32) NOT NULL,
    clause_type VARCHAR(64) NOT NULL,
    clause_text TEXT NOT NULL,
    sla_threshold_hours INTEGER,
    penalty_per_hour_cents BIGINT,
    CONSTRAINT pk_canonical_contract_clauses PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_canonical_clauses_contract FOREIGN KEY (tenant_id, contract_id)
        REFERENCES canonical_contracts (tenant_id, id) ON DELETE CASCADE
);
ALTER TABLE canonical_contract_clauses ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_contract_clauses FORCE ROW LEVEL SECURITY;

-- 8. Payment References Table
CREATE TABLE canonical_payment_references (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    order_id VARCHAR(64) NOT NULL,
    gateway_provider VARCHAR(64) NOT NULL,
    transaction_type VARCHAR(32) NOT NULL,
    payment_status VARCHAR(32) NOT NULL,
    amount_cents BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    gateway_error_code VARCHAR(64),
    processed_at TIMESTAMPTZ NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_canonical_payment_references PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_canonical_payments_order FOREIGN KEY (tenant_id, order_id)
        REFERENCES canonical_orders (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_canonical_payments_amount CHECK (amount_cents >= 0)
);
ALTER TABLE canonical_payment_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_payment_references FORCE ROW LEVEL SECURITY;
```

---

## 11. Storage Zones Separation

The database enforces schema segregation for the five storage zones:
1. `raw`: Contains immutable landing tables (`raw.events`, `raw.quarantine`).
2. `normalized`: Contains intermediate transformation staging.
3. `canonical`: Contains authoritative domain tables defined in Section 10 (`canonical.*`).
4. `ground_truth`: Contains synthetic incident annotations and counterfactual true DAGs (`ground_truth.incidents`).
5. `projections`: Contains materialized rolling metric summaries and vector embeddings (`projections.*`).

---

## 12. Benchmark Ground-Truth Isolation Model

To strictly satisfy `INV-DATA-001` and guarantee zero leakage to the runtime investigation service (`AC-001`, `AC-014`):
1. **Schema Permissions**:
   ```sql
   CREATE SCHEMA ground_truth;
   -- Revoke runtime access completely
   REVOKE ALL ON SCHEMA ground_truth FROM revpilot_app;
   -- Grant offline evaluation harness only
   GRANT USAGE ON SCHEMA ground_truth TO revpilot_evaluator;
   GRANT SELECT ON ALL TABLES IN SCHEMA ground_truth TO revpilot_evaluator;
   ```
2. **Ground Truth Incident Table**:
   ```sql
   CREATE TABLE ground_truth.incidents (
       tenant_id VARCHAR(64) NOT NULL,
       incident_id VARCHAR(64) NOT NULL,
       scenario_name VARCHAR(128) NOT NULL,
       causal_start_time TIMESTAMPTZ NOT NULL,
       causal_end_time TIMESTAMPTZ NOT NULL,
       primary_root_cause VARCHAR(128) NOT NULL,
       affected_facility_id VARCHAR(64) NOT NULL,
       affected_carrier_id VARCHAR(64) NOT NULL,
       affected_scope_filter JSONB NOT NULL,
       true_ate_cancellation_rate_delta NUMERIC(6,4) NOT NULL,
       true_delayed_shipment_count INTEGER NOT NULL,
       true_revenue_at_risk_cents BIGINT NOT NULL,
       competing_hypotheses JSONB NOT NULL,
       CONSTRAINT pk_ground_truth_incidents PRIMARY KEY (tenant_id, incident_id)
   );
   ```

---

## 13. Indexing and Partitioning Strategy

1. **Composite Tenant-Prefixed Indexes**:
   - `idx_orders_tenant_status_event`: `ON canonical_orders (tenant_id, order_status, event_time DESC)`
   - `idx_shipments_tenant_carrier_status`: `ON canonical_shipments (tenant_id, carrier_id, dispatch_status, event_time DESC)`
   - `idx_tickets_tenant_topic_status`: `ON canonical_support_tickets (tenant_id, topic, status, event_time DESC)`
2. **Table Partitioning Strategy**:
   - For scale tiers (`INITIAL_COMMERCIAL` and `SCALE_GROWTH`), `canonical_orders`, `canonical_order_lines`, and `canonical_shipments` are range-partitioned by month on `event_time`. Each monthly partition maintains its own tenant-prefixed primary key and composite indexes.

---

## 14. Phase 01 Database Migration Sequence

Migrations follow the zero-downtime expand/contract pattern (`ADR-0004`):
- `MIG-P01-001`: Create schemas `raw`, `normalized`, `canonical`, `ground_truth`, `projections`.
- `MIG-P01-002`: Create database roles `revpilot_app`, `revpilot_evaluator`, `revpilot_readonly`, `revpilot_migrator`.
- `MIG-P01-003`: Create canonical tables (`canonical_customers`, `canonical_orders`, `canonical_order_lines`, `canonical_shipments`, etc.).
- `MIG-P01-004`: Enable and force Row-Level Security on all canonical tables.
- `MIG-P01-005`: Create RLS tenant isolation policies referencing `current_setting('revpilot.current_tenant_id', true)`.
- `MIG-P01-006`: Create `ground_truth.incidents` table and apply permission restrictions.
- `MIG-P01-007`: Create `raw.quarantine` table with operator index.

---

## 15. Cross-Tenant Persistence Negative Matrix for Phase 01

| Test Scenario | Query Context | Target Table & Entity | Expected Database Result |
|---|---|---|---|
| Query Order Cross-Tenant | Session `tenant_id = 'ten_A'` | `canonical_orders` WHERE `tenant_id = 'ten_B'` | Returns 0 rows (RLS filter) |
| Insert Order Line Cross-Tenant | Session `tenant_id = 'ten_A'` | Payload with `tenant_id = 'ten_B'` | `insufficient_privilege` / RLS check violation |
| Foreign Key Cross-Tenant | Session `tenant_id = 'ten_A'` | Insert order with `customer_id` belonging to `ten_B` | FK constraint violation (`pk_canonical_customers` composite mismatch) |
| Null Session Context | No `SET LOCAL revpilot.current_tenant_id` | Any `canonical_*` table | Returns 0 rows on SELECT, raises on write |
| Query Ground Truth via App Role | Session using role `revpilot_app` | `ground_truth.incidents` | `insufficient_privilege` (Permission Denied) |

---

## 16. Rail 5 Persistence Isolation Dependency Rule

Notice: Database DDL, RLS policies, and SQL scripts defined in this document represent normative architectural contracts. In accordance with `execution/MICRO-TASK-RAIL-SYSTEM.md`:
- Physical database migration execution and live PostgreSQL RLS verification depend on **Rail 5 (Persistence Isolation)** reaching `GREEN`.
- Rail 0, 1, and 2 are `GREEN`; Rail 3 is currently active in planning. Rail 5 is `LOCKED`.
- Phase 01 implementation tasks MUST NOT attempt to execute database migrations or bypass Rail 5 isolation controls using in-memory mock shortcuts. All persistence tasks will be formally queued once Rail 5 is unlocked and admitted.

---

## 17. Phase 02 Anomaly Persistence and Audit Schema

Per `docs/02-domain/ANOMALY-DOMAIN-SPEC.md`, anomalies and their lifecycle transitions are persisted in PostgreSQL with strict tenant scoping and RLS.

```sql
-- 1. Anomalies Table
CREATE TABLE anomalies (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    anomaly_type VARCHAR(32) NOT NULL,
    metric_id VARCHAR(32) NOT NULL,
    metric_version VARCHAR(16) NOT NULL,
    detector_id VARCHAR(64) NOT NULL,
    detector_version VARCHAR(16) NOT NULL,
    baseline_id VARCHAR(64) NOT NULL,
    baseline_version VARCHAR(16) NOT NULL,
    observation_window_start TIMESTAMPTZ NOT NULL,
    observation_window_end TIMESTAMPTZ NOT NULL,
    comparison_window_start TIMESTAMPTZ NOT NULL,
    comparison_window_end TIMESTAMPTZ NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    as_of_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actual_value NUMERIC(18,4) NOT NULL,
    expected_value NUMERIC(18,4) NOT NULL,
    expected_interval_lower NUMERIC(18,4) NOT NULL,
    expected_interval_upper NUMERIC(18,4) NOT NULL,
    anomaly_score NUMERIC(6,4) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    affected_scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_freshness VARCHAR(32) NOT NULL DEFAULT 'FRESH',
    data_quality_state VARCHAR(32) NOT NULL DEFAULT 'PASSED',
    confidence NUMERIC(5,4) NOT NULL,
    supporting_evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'DETECTED',
    reproducibility_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_anomalies PRIMARY KEY (tenant_id, id),
    CONSTRAINT ck_anomaly_score CHECK (anomaly_score BETWEEN 0.0000 AND 1.0000),
    CONSTRAINT ck_anomaly_confidence CHECK (confidence BETWEEN 0.0000 AND 1.0000)
);
ALTER TABLE anomalies ENABLE ROW LEVEL SECURITY;
ALTER TABLE anomalies FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_anomalies ON anomalies
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- Indexes for Anomaly Queries
CREATE INDEX idx_anomalies_tenant_status_time
    ON anomalies (tenant_id, status, observation_window_start DESC);

CREATE INDEX idx_anomalies_tenant_metric_time
    ON anomalies (tenant_id, metric_id, event_time DESC);

-- 2. Anomaly Transitions Audit Table
CREATE TABLE anomaly_transitions (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    anomaly_id VARCHAR(64) NOT NULL,
    from_state VARCHAR(32) NOT NULL,
    to_state VARCHAR(32) NOT NULL,
    actor_id VARCHAR(64) NOT NULL,
    actor_type VARCHAR(32) NOT NULL, -- PRINCIPAL, AGENT_WORKFLOW, DETECTOR_WORKER
    reason TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    transitioned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_anomaly_transitions PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_anomaly_transitions_anomaly FOREIGN KEY (tenant_id, anomaly_id)
        REFERENCES anomalies (tenant_id, id) ON DELETE CASCADE
);
ALTER TABLE anomaly_transitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE anomaly_transitions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_anomaly_transitions ON anomaly_transitions
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- ============================================================================
-- 18. PHASE 04: HYPOTHESIS, CAUSAL STUDY, AND CLAIM VERIFICATION TABLES
-- ============================================================================

-- 1. Investigation Hypotheses Table
CREATE TABLE hypotheses (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    investigation_id VARCHAR(64) NOT NULL,
    statement TEXT NOT NULL,
    hypothesis_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PROPOSED',
    ordinal_rank INT NOT NULL DEFAULT 1,
    ranking_score NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
    evidence_coverage_ratio NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
    supporting_evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    contradicting_evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    causal_study_id VARCHAR(64),
    manifest_digest CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_hypotheses PRIMARY KEY (tenant_id, id)
);
ALTER TABLE hypotheses ENABLE ROW LEVEL SECURITY;
ALTER TABLE hypotheses FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_hypotheses ON hypotheses
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 2. Verified Claims Table
CREATE TABLE verified_claims (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    hypothesis_id VARCHAR(64) NOT NULL,
    statement TEXT NOT NULL,
    category VARCHAR(32) NOT NULL,
    verifier_status VARCHAR(32) NOT NULL,
    rejection_reason TEXT,
    evidence_references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    temporal_as_of TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_verified_claims PRIMARY KEY (tenant_id, id),
    CONSTRAINT fk_verified_claims_hypothesis FOREIGN KEY (tenant_id, hypothesis_id)
        REFERENCES hypotheses (tenant_id, id) ON DELETE CASCADE
);
ALTER TABLE verified_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE verified_claims FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_verified_claims ON verified_claims
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 3. Causal Studies Table
CREATE TABLE causal_studies (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    investigation_id VARCHAR(64) NOT NULL,
    causal_question TEXT NOT NULL,
    treatment_variable VARCHAR(64) NOT NULL,
    outcome_variable VARCHAR(64) NOT NULL,
    unit_of_analysis VARCHAR(64) NOT NULL,
    estimand_type VARCHAR(32) NOT NULL,
    identification_strategy VARCHAR(64) NOT NULL,
    estimator VARCHAR(64) NOT NULL,
    point_estimate NUMERIC(10, 6) NOT NULL,
    standard_error NUMERIC(10, 6) NOT NULL,
    ci_lower NUMERIC(10, 6) NOT NULL,
    ci_upper NUMERIC(10, 6) NOT NULL,
    p_value NUMERIC(10, 6) NOT NULL,
    overlap_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    sensitivity_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reproducibility_seed INT NOT NULL,
    study_digest CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_causal_studies PRIMARY KEY (tenant_id, id)
);
ALTER TABLE causal_studies ENABLE ROW LEVEL SECURITY;
ALTER TABLE causal_studies FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_causal_studies ON causal_studies
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- ============================================================================
-- 19. PHASE 05: CHURN, UPLIFT, DECISION, AND BUDGET LEDGER TABLES
-- ============================================================================

-- 1. Churn Predictions Table
CREATE TABLE churn_predictions (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    customer_id VARCHAR(64) NOT NULL,
    as_of_time TIMESTAMPTZ NOT NULL,
    model_artifact_id VARCHAR(64) NOT NULL,
    calibrated_probability NUMERIC(5, 4) NOT NULL,
    risk_tier VARCHAR(32) NOT NULL,
    ece_at_release NUMERIC(5, 4) NOT NULL,
    feature_snapshot_digest CHAR(64) NOT NULL,
    is_treatment_contaminated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_churn_predictions PRIMARY KEY (tenant_id, id)
);
ALTER TABLE churn_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE churn_predictions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_churn_predictions ON churn_predictions
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 2. Uplift Scores Table
CREATE TABLE uplift_scores (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    customer_id VARCHAR(64) NOT NULL,
    intervention_type VARCHAR(64) NOT NULL,
    as_of_time TIMESTAMPTZ NOT NULL,
    model_artifact_id VARCHAR(64) NOT NULL,
    cate_estimate NUMERIC(8, 6) NOT NULL,
    standard_error NUMERIC(8, 6) NOT NULL,
    ci_lower NUMERIC(8, 6) NOT NULL,
    ci_upper NUMERIC(8, 6) NOT NULL,
    persuadability_segment VARCHAR(32) NOT NULL,
    overlap_satisfied BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_uplift_scores PRIMARY KEY (tenant_id, id)
);
ALTER TABLE uplift_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE uplift_scores FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_uplift_scores ON uplift_scores
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 3. Decision Records Table
CREATE TABLE decision_records (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    request_id VARCHAR(64) NOT NULL,
    customer_id VARCHAR(64) NOT NULL,
    investigation_id VARCHAR(64),
    selected_candidate_id VARCHAR(64),
    expected_utility_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    direct_cost_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    risk_penalty_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    uncertainty_penalty_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(32) NOT NULL DEFAULT 'RECOMMENDED',
    decision_digest CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_decision_records PRIMARY KEY (tenant_id, id)
);
ALTER TABLE decision_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_records FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_decision_records ON decision_records
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 4. Budget Ledgers Table
CREATE TABLE budget_ledgers (
    tenant_id VARCHAR(64) NOT NULL,
    ledger_date DATE NOT NULL,
    total_allocated_usd NUMERIC(12, 2) NOT NULL,
    committed_expenditure_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    remaining_balance_usd NUMERIC(12, 2) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_budget_ledgers PRIMARY KEY (tenant_id, ledger_date)
);
ALTER TABLE budget_ledgers ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_ledgers FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_budget_ledgers ON budget_ledgers
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- ============================================================================
-- 20. PHASE 06: APPROVAL, ACTION INTENT, LEDGER, AND OUTCOME TABLES
-- ============================================================================

-- 1. Approval Requests Table
CREATE TABLE approval_requests (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    decision_id VARCHAR(64) NOT NULL,
    investigation_id VARCHAR(64),
    action_type VARCHAR(64) NOT NULL,
    action_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    target_customer_id VARCHAR(64) NOT NULL,
    target_entity_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    action_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    payload_digest CHAR(64) NOT NULL,
    policy_digest CHAR(64) NOT NULL,
    estimated_cost_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    reserved_budget_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    risk_tier VARCHAR(32) NOT NULL DEFAULT 'LOW',
    required_approval_tier INT NOT NULL DEFAULT 1,
    approver_principal_id VARCHAR(64),
    approval_timestamp TIMESTAMPTZ,
    rejection_reason TEXT,
    expiry_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    decision_digest CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_approval_requests PRIMARY KEY (tenant_id, id)
);
ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_requests FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_approval_requests ON approval_requests
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 2. Action Intents Table
CREATE TABLE action_intents (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    approval_id VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    action_type VARCHAR(64) NOT NULL,
    classification VARCHAR(32) NOT NULL DEFAULT 'COMPENSATABLE',
    target_set_count INT NOT NULL DEFAULT 1,
    payload_digest CHAR(64) NOT NULL,
    is_dry_run BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(32) NOT NULL DEFAULT 'INITIALIZED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_action_intents PRIMARY KEY (tenant_id, id),
    CONSTRAINT uq_action_intents_idempotency UNIQUE (tenant_id, idempotency_key)
);
ALTER TABLE action_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_intents FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_action_intents ON action_intents
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 3. Action Ledgers Table
CREATE TABLE action_ledgers (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    intent_id VARCHAR(64) NOT NULL,
    attempt_number INT NOT NULL DEFAULT 1,
    idempotency_key VARCHAR(128) NOT NULL,
    provider_name VARCHAR(64) NOT NULL,
    request_digest CHAR(64) NOT NULL,
    response_digest CHAR(64),
    http_status_code INT,
    provider_tx_id VARCHAR(128),
    execution_status VARCHAR(32) NOT NULL DEFAULT 'STARTED',
    error_code VARCHAR(64),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CONSTRAINT pk_action_ledgers PRIMARY KEY (tenant_id, id)
);
ALTER TABLE action_ledgers ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_ledgers FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_action_ledgers ON action_ledgers
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 4. Compensation Records Table
CREATE TABLE compensation_records (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    intent_id VARCHAR(64) NOT NULL,
    step_name VARCHAR(64) NOT NULL,
    compensation_action VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    compensated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_compensation_records PRIMARY KEY (tenant_id, id)
);
ALTER TABLE compensation_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE compensation_records FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_compensation_records ON compensation_records
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 5. Action Outcomes Table
CREATE TABLE action_outcomes (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    intent_id VARCHAR(64) NOT NULL,
    approval_id VARCHAR(64) NOT NULL,
    customer_id VARCHAR(64) NOT NULL,
    observed_revenue_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    expected_revenue_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    actual_cost_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    net_roi_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_action_outcomes PRIMARY KEY (tenant_id, id)
);
ALTER TABLE action_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_outcomes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_action_outcomes ON action_outcomes
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );
```

---

## 21. Phase 07 Multi-Tenant Pilot, Connectors, Identity, and Metering Schema

```sql
-- 1. Tenant Operations and Configuration
CREATE TABLE tenant_operations_config (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    subscription_tier VARCHAR(32) NOT NULL DEFAULT 'SHARED',
    isolation_mode VARCHAR(32) NOT NULL DEFAULT 'RLS_SHARED',
    legal_hold_active BOOLEAN NOT NULL DEFAULT FALSE,
    legal_hold_matter_id VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_tenant_operations_config PRIMARY KEY (tenant_id, id)
);
ALTER TABLE tenant_operations_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_operations_config FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_operations_config ON tenant_operations_config
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 2. OIDC Federation Configurations
CREATE TABLE oidc_federation_configs (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    issuer_url VARCHAR(512) NOT NULL,
    client_id VARCHAR(256) NOT NULL,
    client_secret_ref VARCHAR(256) NOT NULL,
    jwks_uri VARCHAR(512) NOT NULL,
    allowed_clock_skew_seconds INT NOT NULL DEFAULT 60,
    claim_mapping_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_oidc_federation_configs PRIMARY KEY (tenant_id, id)
);
ALTER TABLE oidc_federation_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE oidc_federation_configs FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_oidc_configs ON oidc_federation_configs
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 3. Connector Instances
CREATE TABLE connector_instances (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    provider_name VARCHAR(64) NOT NULL,
    provider_version VARCHAR(32) NOT NULL DEFAULT 'v1',
    capability_type VARCHAR(64) NOT NULL,
    auth_method VARCHAR(64) NOT NULL,
    secret_ref VARCHAR(256) NOT NULL,
    granted_scopes TEXT[] NOT NULL DEFAULT '{}',
    sync_mode VARCHAR(32) NOT NULL DEFAULT 'BATCH_PULL',
    cursor_position VARCHAR(256),
    last_successful_sync_at TIMESTAMPTZ,
    sync_lag_seconds INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'REGISTERED',
    schema_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    mapping_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_connector_instances PRIMARY KEY (tenant_id, id)
);
ALTER TABLE connector_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_instances FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_connector_instances ON connector_instances
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 4. Connector Inbound Inbox Events (Webhook & Batch Ingestion)
CREATE TABLE connector_inbox_events (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    connector_id VARCHAR(64) NOT NULL,
    external_event_id VARCHAR(256) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    raw_payload JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    CONSTRAINT pk_connector_inbox_events PRIMARY KEY (tenant_id, id),
    CONSTRAINT uq_connector_inbox_external UNIQUE (tenant_id, connector_id, external_event_id)
);
ALTER TABLE connector_inbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_inbox_events FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_connector_inbox ON connector_inbox_events
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 5. Connector Quarantine Table (Schema Drift & Malformed Payloads)
CREATE TABLE connector_quarantine (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    connector_id VARCHAR(64) NOT NULL,
    payload_digest VARCHAR(64) NOT NULL,
    raw_payload JSONB NOT NULL,
    error_reason TEXT NOT NULL,
    drift_classification VARCHAR(64) NOT NULL,
    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_REVIEW',
    CONSTRAINT pk_connector_quarantine PRIMARY KEY (tenant_id, id)
);
ALTER TABLE connector_quarantine ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_quarantine FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_connector_quarantine ON connector_quarantine
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 6. Tenant Quotas and Spend Controls
CREATE TABLE tenant_quotas (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    dimension VARCHAR(64) NOT NULL,
    hard_limit NUMERIC(16, 4) NOT NULL,
    soft_limit NUMERIC(16, 4) NOT NULL,
    current_usage NUMERIC(16, 4) NOT NULL DEFAULT 0.0000,
    reserved_usage NUMERIC(16, 4) NOT NULL DEFAULT 0.0000,
    reset_period VARCHAR(32) NOT NULL DEFAULT 'DAILY',
    last_reset_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_tenant_quotas PRIMARY KEY (tenant_id, id),
    CONSTRAINT uq_tenant_quota_dimension UNIQUE (tenant_id, dimension)
);
ALTER TABLE tenant_quotas ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_quotas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_tenant_quotas ON tenant_quotas
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 7. Usage Metering Records
CREATE TABLE usage_records (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    principal_id VARCHAR(64) NOT NULL,
    investigation_id VARCHAR(64),
    workflow_id VARCHAR(128),
    agent_name VARCHAR(64),
    model_or_tool_name VARCHAR(128) NOT NULL,
    connector_id VARCHAR(64),
    unit VARCHAR(32) NOT NULL,
    quantity NUMERIC(16, 4) NOT NULL,
    estimated_cost_usd NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    reconciliation_status VARCHAR(32) NOT NULL DEFAULT 'ESTIMATED',
    idempotency_key VARCHAR(128) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_usage_records PRIMARY KEY (tenant_id, id),
    CONSTRAINT uq_usage_idempotency UNIQUE (tenant_id, idempotency_key)
);
ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_records FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_usage_records ON usage_records
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );

-- 8. Tenant Deletion Certificates (Immutable Proof of Purge)
CREATE TABLE tenant_deletion_certificates (
    tenant_id VARCHAR(64) NOT NULL,
    id VARCHAR(64) NOT NULL,
    deletion_digest VARCHAR(64) NOT NULL,
    purged_by_principal VARCHAR(64) NOT NULL,
    dual_approver_principal VARCHAR(64) NOT NULL,
    purged_partitions JSONB NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_tenant_deletion_certificates PRIMARY KEY (tenant_id, id)
);
ALTER TABLE tenant_deletion_certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_deletion_certificates FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_deletion_certificates ON tenant_deletion_certificates
    AS RESTRICTIVE
    USING (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    )
    WITH CHECK (
        current_setting('revpilot.is_system', true) = 'true'
        OR tenant_id = current_setting('revpilot.current_tenant_id', true)
    );
```
