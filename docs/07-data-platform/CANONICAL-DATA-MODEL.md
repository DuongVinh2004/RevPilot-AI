# Canonical Data Model Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 01 — Canonical Data and Synthetic Benchmark
Owner: Data Architecture
Traceability: `BR-001`, `BR-004`, `FR-DET-001`, `FR-INV-004`, `INV-TEN-001`, `INV-TEN-002`, `INV-DATA-001`, `INV-DATA-002`, `INV-EVD-001`, `NFR-TEN-001`, `ADR-0001`, `ADR-0004`, `ADR-0005`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Scope and Architectural Principles

This document defines the canonical domain data model for RevPilot AI. Canonical entities represent authoritative, normalized, tenant-scoped representations of business realities across e-commerce, fulfillment, customer service, and contract operations.

### Core Invariants
1. **Mandatory Tenant Scoping (`INV-TEN-001`, `INV-TEN-002`)**: Every canonical entity record MUST include a non-null `tenant_id`. Composite primary keys and foreign keys MUST start with `tenant_id`.
2. **Immutable Event and Audit History (`INV-AUD-001`)**: Historical business events are append-only. Corrections and status updates create new event records or explicit state transitions with recorded timestamps.
3. **Strict Time Disambiguation (`INV-DATA-001`)**: All entities distinguish `event_time`, `effective_from/to`, `ingested_at`, and `as_of_time`. Queries for benchmarks, anomaly baselines, and investigations MUST evaluate strictly `as_of` without future data leakage.
4. **Rebuildable Derived Projections (`INV-DATA-002`)**: Canonical entities are stored authoritatively in PostgreSQL (`ADR-0004`). Search indices, feature stores, and vector embeddings are rebuildable derived projections and never serve as independent transactional authority.
5. **No Ground-Truth Leakage**: Synthetic benchmark labels and causal scenario ground truth are isolated in the `ground_truth` zone and are physically/logically inaccessible to the investigation runtime.

---

## 2. Storage Zones

RevPilot structures data processing into five strictly segregated zones:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   RevPilot Data Storage Zones                                    │
├───────────────────┬───────────────────┬───────────────────┬───────────────────┬─────────────────┤
│ Zone              │ Schema / Namespace│ Mutability        │ Access Authority  │ Purpose         │
├───────────────────┼───────────────────┼───────────────────┼───────────────────┼─────────────────┤
│ 1. Raw            │ `raw`             │ Immutable Append  │ Ingestion Engine  │ Source payload  │
│ 2. Normalized     │ `normalized`      │ Immutable Append  │ Transform Workers │ Typed staging   │
│ 3. Canonical      │ `canonical`       │ Versioned / State │ Business Modules  │ Core aggregates │
│ 4. Ground Truth   │ `ground_truth`    │ Read-Only Fixture │ Evaluator Only    │ Hidden labels   │
│ 5. Projections    │ `projections`     │ Rebuildable Read  │ Analytics / RAG   │ Features/Index  │
└───────────────────┴───────────────────┴───────────────────┴───────────────────┴─────────────────┘
```

1. **Raw Zone (`raw`)**: Immutable capture of inbound provider payloads (webhooks, API sync, batch files). Retains verbatim raw payload, payload hash (`SHA-256`), source identifier, tenant context, and ingestion timestamp.
2. **Normalized Zone (`normalized`)**: Staging tables where raw payloads are parsed into strongly-typed tabular formats before domain validation.
3. **Canonical Zone (`canonical`)**: The authoritative business model. Enforces relational integrity, business validation rules, tenant isolation, and currency/temporal invariants.
4. **Ground-Truth Zone (`ground_truth`)**: Dedicated, isolated storage containing hidden scenario labels, true root-cause annotations, and counterfactual treatment effects for synthetic benchmarks. Accessible exclusively by offline evaluation harnesses; blocked from all application and agent query ports.
5. **Derived Projections Zone (`projections`)**: Rebuildable read-optimized views, rolling aggregations, feature tables for machine learning, and chunk/vector indices for retrieval.

---

## 3. Common Entity Header and Audit Metadata

Every canonical entity schema inherits the standard metadata envelope:

| Attribute | Data Type | Nullable | Description |
|---|---|---|---|
| `tenant_id` | `VARCHAR(64)` | NO | Partitioning tenant identifier (`INV-TEN-001`). Format: `ten_[a-z0-9]+`. |
| `id` | `VARCHAR(64)` | NO | Entity unique identifier within tenant. Format: prefix + ULID/UUIDv7. |
| `schema_version` | `VARCHAR(16)` | NO | SemVer string of the entity contract (e.g., `1.0.0`). |
| `source_system` | `VARCHAR(64)` | NO | Ingesting provider/system (e.g., `shopify`, `salesforce`, `synthetic_v1`). |
| `source_id` | `VARCHAR(128)` | NO | Primary key of the record in the external source system. |
| `event_time` | `TIMESTAMPTZ` | NO | Business timestamp when event occurred in reality (UTC). |
| `effective_from` | `TIMESTAMPTZ` | NO | Watermark from which this version becomes valid (UTC). |
| `effective_to` | `TIMESTAMPTZ` | YES | Watermark after which this version is superseded (NULL = current). |
| `ingested_at` | `TIMESTAMPTZ` | NO | Platform arrival timestamp in UTC (`CURRENT_TIMESTAMP`). |
| `data_classification`| `VARCHAR(32)` | NO | `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED_PII`. |
| `retention_class` | `VARCHAR(32)` | NO | Retention lifecycle rule (e.g., `REVENUE_FINANCIAL_7YR`). |
| `lineage_trace_id` | `VARCHAR(64)` | NO | Trace ID of the ingestion job/batch pipeline. |
| `dedup_key` | `VARCHAR(128)` | NO | Deterministic hash for idempotent replay (`SHA-256`). |

---

## 4. Canonical Entities Specification

### 4.1. Entity: `Customer` (Customer 360 Context)

- **Entity ID & Prefix**: `Customer` (`cus_...`), Version `1.0.0`
- **Tenant Ownership**: Strict. Owned by `tenancy` & `Customer 360` context.
- **Aggregate Owner**: Customer 360 module.
- **Primary Key**: `(tenant_id, id)`
- **Business Key**: `(tenant_id, source_system, source_id)`
- **Relationships**:
  - `Customer` 1---* `Order` (FK: `tenant_id`, `customer_id`)
  - `Customer` 1---* `SupportTicket` (FK: `tenant_id`, `customer_id`)
  - `Customer` 1---* `Contract` (FK: `tenant_id`, `customer_id`)
- **Fields**:
  - `name`: `VARCHAR(255)` [REQUIRED] — Customer organization / individual name (PII: `CONFIDENTIAL`).
  - `email`: `VARCHAR(255)` [REQUIRED] — Contact email (PII: `RESTRICTED_PII`, masked in logs).
  - `segment`: `VARCHAR(64)` [REQUIRED] — Segment enum: `ENTERPRISE`, `MID_MARKET`, `SMB`, `CONSUMER`.
  - `account_tier`: `VARCHAR(32)` [REQUIRED] — Tier enum: `TIER_1_PLATINUM`, `TIER_2_GOLD`, `TIER_3_STANDARD`.
  - `billing_country`: `VARCHAR(2)` [REQUIRED] — ISO 3166-1 alpha-2 country code.
  - `contract_mrr_cents`: `BIGINT` [REQUIRED] — Normalized Monthly Recurring Revenue in minor units (cents).
  - `currency`: `VARCHAR(3)` [REQUIRED] — ISO 4217 currency code (e.g., `USD`).
  - `status`: `VARCHAR(32)` [REQUIRED] — Enum: `ACTIVE`, `CHURN_RISK`, `CHURNED`, `SUSPENDED`.
- **Deduplication Key**: `sha256(tenant_id + ":" + source_system + ":" + source_id)`
- **Quality Rules**: `email` must match RFC 5322 regex; `contract_mrr_cents >= 0`; `currency` must be valid ISO 4217.
- **Quarantine Behavior**: Unparseable email or invalid country code routes to `raw_quarantine` with error `DQ-ERR-CUS-001`.

---

### 4.2. Entity: `Order` (Fulfillment Context)

- **Entity ID & Prefix**: `Order` (`ord_...`), Version `1.0.0`
- **Tenant Ownership**: Strict.
- **Aggregate Owner**: Fulfillment & Revenue Ledger modules.
- **Primary Key**: `(tenant_id, id)`
- **Business Key**: `(tenant_id, source_system, source_id)`
- **Relationships**:
  - `Customer` 1---* `Order`
  - `Order` 1---* `OrderLine` (FK: `tenant_id`, `order_id`)
  - `Order` 1---* `Shipment` (FK: `tenant_id`, `order_id`)
  - `Order` 1---* `PaymentReference` (FK: `tenant_id`, `order_id`)
- **Fields**:
  - `customer_id`: `VARCHAR(64)` [REQUIRED] — Foreign key to `Customer(tenant_id, id)`.
  - `order_number`: `VARCHAR(64)` [REQUIRED] — Business human-readable order number.
  - `order_status`: `VARCHAR(32)` [REQUIRED] — Enum: `PLACED`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `RETURNED`.
  - `cancellation_reason`: `VARCHAR(128)` [OPTIONAL] — Non-null if status is `CANCELLED`. Enum: `CUSTOMER_REQUEST_DELAY`, `OUT_OF_STOCK`, `PAYMENT_FAILURE`, `FRAUD_SUSPECTED`, `OTHER`.
  - `cancellation_requested_at`: `TIMESTAMPTZ` [OPTIONAL] — Timestamp of cancellation request.
  - `cancelled_at`: `TIMESTAMPTZ` [OPTIONAL] — Timestamp cancellation finalized.
  - `currency`: `VARCHAR(3)` [REQUIRED] — ISO 4217 currency code.
  - `subtotal_cents`: `BIGINT` [REQUIRED] — Total amount before tax/shipping in minor units.
  - `tax_cents`: `BIGINT` [REQUIRED] — Tax amount in minor units.
  - `shipping_cents`: `BIGINT` [REQUIRED] — Shipping fee in minor units.
  - `total_cents`: `BIGINT` [REQUIRED] — Net order value: `subtotal_cents + tax_cents + shipping_cents`.
  - `sla_delivery_deadline`: `TIMESTAMPTZ` [REQUIRED] — Guaranteed delivery deadline.
- **Monetary Semantics**: All amounts are positive or zero integers representing minor currency units (cents). `total_cents == subtotal_cents + tax_cents + shipping_cents`.
- **Late/Out-of-order Behavior**: If `CANCELLED` arrives before `PLACED`, event is buffered in `raw_pending_dependency` for up to 15 minutes before raising `DQ-ERR-ORD-ORPHAN`.
- **Quality Rules**: `total_cents >= 0`; `cancelled_at >= event_time` if present; `customer_id` must resolve.

---

### 4.3. Entity: `OrderLine` (Fulfillment Context)

- **Entity ID & Prefix**: `OrderLine` (`orl_...`), Version `1.0.0`
- **Tenant Ownership**: Strict.
- **Aggregate Owner**: Fulfillment module.
- **Primary Key**: `(tenant_id, id)`
- **Foreign Key**: `(tenant_id, order_id)` REFERENCES `Order(tenant_id, id)` ON DELETE RESTRICT
- **Fields**:
  - `order_id`: `VARCHAR(64)` [REQUIRED] — Parent order ID.
  - `sku`: `VARCHAR(64)` [REQUIRED] — Product SKU.
  - `product_name`: `VARCHAR(255)` [REQUIRED] — Item display name.
  - `product_category`: `VARCHAR(64)` [REQUIRED] — Item category (e.g., `ELECTRONICS`, `APPAREL`, `HOME`).
  - `quantity`: `INTEGER` [REQUIRED] — Quantity ordered (`quantity > 0`).
  - `unit_price_cents`: `BIGINT` [REQUIRED] — Item price in minor units.
  - `total_price_cents`: `BIGINT` [REQUIRED] — `quantity * unit_price_cents`.
- **Quality Rules**: `quantity > 0`; `total_price_cents == quantity * unit_price_cents`.

---

### 4.4. Entity: `Shipment` (Fulfillment Context)

- **Entity ID & Prefix**: `Shipment` (`shp_...`), Version `1.0.0`
- **Tenant Ownership**: Strict.
- **Aggregate Owner**: Fulfillment module.
- **Primary Key**: `(tenant_id, id)`
- **Foreign Key**: `(tenant_id, order_id)` REFERENCES `Order(tenant_id, id)` ON DELETE RESTRICT
- **Relationships**:
  - `Warehouse` 1---* `Shipment` (FK: `tenant_id`, `warehouse_id`)
  - `Shipment` *---1 `Carrier` (Carrier reference)
- **Fields**:
  - `order_id`: `VARCHAR(64)` [REQUIRED] — Associated order.
  - `tracking_number`: `VARCHAR(128)` [REQUIRED] — Carrier tracking code.
  - `carrier_id`: `VARCHAR(64)` [REQUIRED] — Carrier identifier (e.g., `CARRIER_REGIONAL_LOGISTICS`, `CARRIER_AIR_EXPRESS`).
  - `carrier_name`: `VARCHAR(128)` [REQUIRED] — Friendly carrier name.
  - `warehouse_id`: `VARCHAR(64)` [REQUIRED] — Origin warehouse identifier (e.g., `WH-MIDWEST-01`).
  - `origin_region`: `VARCHAR(64)` [REQUIRED] — Geographic region (e.g., `US-MIDWEST`, `US-WEST`).
  - `destination_region`: `VARCHAR(64)` [REQUIRED] — Destination region.
  - `dispatch_status`: `VARCHAR(32)` [REQUIRED] — Enum: `PENDING`, `DISPATCHED`, `IN_TRANSIT`, `DELIVERED`, `DELAYED`, `LOST`.
  - `dispatched_at`: `TIMESTAMPTZ` [OPTIONAL] — Actual dispatch timestamp from warehouse.
  - `estimated_delivery_at`: `TIMESTAMPTZ` [REQUIRED] — Dynamic estimated delivery time.
  - `actual_delivered_at`: `TIMESTAMPTZ` [OPTIONAL] — Proof of delivery timestamp.
  - `delay_reason`: `VARCHAR(128)` [OPTIONAL] — Enum: `FLEET_CAPACITY_SHORTAGE`, `WEATHER_DISRUPTION`, `MECHANICAL_FAILURE`, `CUSTOMS_HOLD`, `NONE`.
  - `is_delayed`: `BOOLEAN` [REQUIRED] — Generated or computed flag: `dispatched_at > estimated_dispatch_by` OR `actual_delivered_at > sla_delivery_deadline`.
- **Quality Rules**: `dispatched_at <= actual_delivered_at` if both present; `warehouse_id` must resolve.

---

### 4.5. Entity: `SupportTicket` (Service Intelligence Context)

- **Entity ID & Prefix**: `SupportTicket` (`tkt_...`), Version `1.0.0`
- **Tenant Ownership**: Strict.
- **Aggregate Owner**: Service Intelligence module.
- **Primary Key**: `(tenant_id, id)`
- **Relationships**:
  - `Customer` 1---* `SupportTicket` (FK: `tenant_id`, `customer_id`)
  - `Order` 1---* `SupportTicket` (FK: `tenant_id`, `order_id`, OPTIONAL)
- **Fields**:
  - `customer_id`: `VARCHAR(64)` [REQUIRED] — Ticket submitter customer ID.
  - `order_id`: `VARCHAR(64)` [OPTIONAL] — Referenced order if ticket pertains to an order.
  - `ticket_number`: `VARCHAR(64)` [REQUIRED] — Display ticket reference.
  - `topic`: `VARCHAR(64)` [REQUIRED] — Category enum: `ORDER_STATUS_DELAY`, `CANCELLATION_INQUIRY`, `PAYMENT_ISSUE`, `DAMAGED_ITEM`, `GENERAL_SUPPORT`.
  - `priority`: `VARCHAR(16)` [REQUIRED] — Enum: `P1_URGENT`, `P2_HIGH`, `P3_NORMAL`, `P4_LOW`.
  - `status`: `VARCHAR(32)` [REQUIRED] — Enum: `OPEN`, `PENDING_CUSTOMER`, `RESOLVED`, `CLOSED`.
  - `subject`: `VARCHAR(255)` [REQUIRED] — Ticket subject line (PII: `CONFIDENTIAL`).
  - `transcript_text`: `TEXT` [REQUIRED] — Ticket message conversation (PII: `RESTRICTED_PII`, DLP scanned).
  - `first_response_at`: `TIMESTAMPTZ` [OPTIONAL] — Agent first response time.
  - `resolved_at`: `TIMESTAMPTZ` [OPTIONAL] — Resolution timestamp.
- **Quality Rules**: `resolved_at >= event_time` if present; `topic` in canonical enum list.

---

### 4.6. Entity: `MaintenanceEvent` (Fulfillment Context)

- **Entity ID & Prefix**: `MaintenanceEvent` (`mte_...`), Version `1.0.0`
- **Tenant Ownership**: Strict (facility/asset owned or leased by tenant).
- **Aggregate Owner**: Fulfillment module.
- **Primary Key**: `(tenant_id, id)`
- **Fields**:
  - `facility_id`: `VARCHAR(64)` [REQUIRED] — Warehouse or fleet terminal ID (e.g., `WH-MIDWEST-01`).
  - `facility_type`: `VARCHAR(32)` [REQUIRED] — Enum: `WAREHOUSE`, `FLEET_DEPOT`, `SORTATION_HUB`.
  - `event_type`: `VARCHAR(64)` [REQUIRED] — Enum: `CARRIER_CAPACITY_SHORTAGE`, `EQUIPMENT_BREAKDOWN`, `SCHEDULED_MAINTENANCE`, `WEATHER_CLOSURE`.
  - `severity`: `VARCHAR(16)` [REQUIRED] — Enum: `CRITICAL`, `MAJOR`, `MINOR`, `INFORMATIONAL`.
  - `start_window`: `TIMESTAMPTZ` [REQUIRED] — Outage/disruption start time (UTC).
  - `end_window`: `TIMESTAMPTZ` [OPTIONAL] — Disruption end time (NULL = ongoing).
  - `impact_capacity_reduction_pct`: `NUMERIC(5,2)` [REQUIRED] — Percentage reduction in dispatch capacity (0.00 to 100.00%).
  - `description`: `TEXT` [REQUIRED] — Operational incident log description.
- **Quality Rules**: `impact_capacity_reduction_pct BETWEEN 0.00 AND 100.00`; `end_window >= start_window` if present.

---

### 4.7. Entity: `Contract` & `ContractClause` (Contract Intelligence Context)

- **Entity ID & Prefix**: `Contract` (`ctr_...`), `ContractClause` (`cls_...`), Version `1.0.0`
- **Tenant Ownership**: Strict.
- **Aggregate Owner**: Contract Intelligence module.
- **Primary Key**: `(tenant_id, id)`
- **Relationships**:
  - `Customer` 1---* `Contract` (FK: `tenant_id`, `customer_id`)
  - `Contract` 1---* `ContractClause` (FK: `tenant_id`, `contract_id`)
- **Fields (`Contract`)**:
  - `customer_id`: `VARCHAR(64)` [REQUIRED] — Associated account.
  - `title`: `VARCHAR(255)` [REQUIRED] — Contract title (e.g., "Enterprise SLA Agreement 2026").
  - `contract_type`: `VARCHAR(32)` [REQUIRED] — Enum: `ENTERPRISE_SLA`, `STANDARD_TERMS`, `SUPPLIER_AGREEMENT`.
  - `effective_from`: `TIMESTAMPTZ` [REQUIRED] — Validity start watermark.
  - `effective_to`: `TIMESTAMPTZ` [OPTIONAL] — Expiration watermark.
  - `document_uri`: `VARCHAR(512)` [REQUIRED] — Reference to governed document store.
  - `document_digest`: `VARCHAR(64)` [REQUIRED] — SHA-256 digest of contract text.
- **Fields (`ContractClause`)**:
  - `contract_id`: `VARCHAR(64)` [REQUIRED] — Parent contract.
  - `clause_number`: `VARCHAR(32)` [REQUIRED] — Clause reference (e.g., "Sec 4.2.1").
  - `clause_type`: `VARCHAR(64)` [REQUIRED] — Enum: `DELIVERY_SLA`, `CANCELLATION_POLICY`, `PENALTY_CREDIT`, `FORCE_MAJEURE`.
  - `clause_text`: `TEXT` [REQUIRED] — Verbatim text of the SLA clause.
  - `sla_threshold_hours`: `INTEGER` [OPTIONAL] — Maximum allowable fulfillment delay before breach.
  - `penalty_per_hour_cents`: `BIGINT` [OPTIONAL] — Financial penalty per delayed hour.
- **Quality Rules**: `effective_to >= effective_from` if present; `document_digest` must be 64-char hex string.

---

### 4.8. Entity: `PaymentReference` (Revenue Ledger Context)

- **Entity ID & Prefix**: `PaymentReference` (`pay_...`), Version `1.0.0`
- **Tenant Ownership**: Strict.
- **Aggregate Owner**: Revenue Ledger module.
- **Primary Key**: `(tenant_id, id)`
- **Foreign Key**: `(tenant_id, order_id)` REFERENCES `Order(tenant_id, id)` ON DELETE RESTRICT
- **Fields**:
  - `order_id`: `VARCHAR(64)` [REQUIRED] — Associated order.
  - `gateway_provider`: `VARCHAR(64)` [REQUIRED] — Enum: `STRIPE`, `ADYEN`, `SYNTHETIC_BANK`.
  - `transaction_type`: `VARCHAR(32)` [REQUIRED] — Enum: `AUTHORIZATION`, `CAPTURE`, `REFUND`, `CHARGEBACK`.
  - `payment_status`: `VARCHAR(32)` [REQUIRED] — Enum: `SUCCEEDED`, `FAILED`, `PENDING`, `DISPUTED`.
  - `amount_cents`: `BIGINT` [REQUIRED] — Transaction amount in minor units.
  - `currency`: `VARCHAR(3)` [REQUIRED] — ISO 4217 code.
  - `gateway_error_code`: `VARCHAR(64)` [OPTIONAL] — Error code if failed (e.g., `INSUFFICIENT_FUNDS`).
  - `processed_at`: `TIMESTAMPTZ` [REQUIRED] — Gateway execution timestamp.
- **Quality Rules**: No credit card PAN or CVV stored (`INV-SEC-001`, `ADR-0004`). Only tokenized references and status codes.

---

### 4.9. Entity: `BenchmarkGroundTruthIncident` (Ground-Truth Zone ONLY)

- **Entity ID & Prefix**: `BenchmarkGroundTruthIncident` (`inc_...`), Version `1.0.0`
- **Storage Location**: `ground_truth` schema (`ground_truth.incidents`).
- **Access Boundary**: Accessible strictly by test runner and evaluation framework (`docs/20-evaluation/EVALUATION-FRAMEWORK.md`). Blocked from `revpilot_app` database role via PostgreSQL privileges.
- **Fields**:
  - `tenant_id`: `VARCHAR(64)` [REQUIRED] — Target tenant where incident was injected.
  - `incident_id`: `VARCHAR(64)` [REQUIRED] — Unique scenario incident ID (e.g., `INC-SYNTH-TRUCK-001`).
  - `scenario_name`: `VARCHAR(128)` [REQUIRED] — e.g., "Midwest Regional Truck Capacity Disruption".
  - `causal_start_time`: `TIMESTAMPTZ` [REQUIRED] — Day 45 08:00:00Z.
  - `causal_end_time`: `TIMESTAMPTZ` [REQUIRED] — Day 52 23:59:59Z.
  - `primary_root_cause`: `VARCHAR(128)` [REQUIRED] — "TRUCK_CAPACITY_SHORTAGE_MIDWEST".
  - `affected_facility_id`: `VARCHAR(64)` [REQUIRED] — "WH-MIDWEST-01".
  - `affected_carrier_id`: `VARCHAR(64)` [REQUIRED] — "CARRIER_REGIONAL_LOGISTICS".
  - `affected_scope_filter`: `JSONB` [REQUIRED] — `{"origin_region": "US-MIDWEST", "carrier_id": "CARRIER_REGIONAL_LOGISTICS"}`.
  - `true_ate_cancellation_rate_delta`: `NUMERIC(6,4)` [REQUIRED] — `+0.0660` (+6.6% absolute increase).
  - `true_delayed_shipment_count`: `INTEGER` [REQUIRED] — Exact number of delayed shipments.
  - `true_revenue_at_risk_cents`: `BIGINT` [REQUIRED] — Exact ground truth revenue at risk.
  - `competing_hypotheses`: `JSONB` [REQUIRED] — Array of plausible alternative causes with rejection evidence keys:
    ```json
    [
      {"hypothesis_id": "ALT_01", "name": "Payment Gateway Latency", "ground_truth_valid": false, "disproving_metric": "payment_failure_rate"},
      {"hypothesis_id": "ALT_02", "name": "Product Quality Defect", "ground_truth_valid": false, "disproving_metric": "return_defect_ratio"}
    ]
    ```

---

## 5. Schema Evolution and Migration Rules

1. **Additive Changes Only**: Column additions must be nullable or provide an immutable non-breaking default.
2. **Expand/Contract Workflow**:
   - Version 1: Add new nullable column, application writes both.
   - Version 2: Backfill historical rows with verified checksums.
   - Version 3: Contract phase: deprecate and remove old column.
3. **No In-Place Type Changes**: Type alterations or column renames without an expand/contract deprecation period are prohibited.
4. **Tenant Key Immutability**: The `tenant_id` column can never be altered, removed, or made nullable.

---

## 6. Traceability and Verification Matrix

| Entity | Primary Module Owner | Invariants Enforced | Test Category | Acceptance Criteria |
|---|---|---|---|---|
| `Customer` | Customer 360 | `INV-TEN-001`, `INV-TEN-002` | `contract/test_customer_contracts.py` | `AC-001`, `AC-010` |
| `Order` | Fulfillment / Revenue | `INV-TEN-001`, `INV-DATA-001` | `contract/test_order_contracts.py` | `AC-001`, `AC-002` |
| `OrderLine` | Fulfillment | `INV-TEN-001` | `contract/test_order_contracts.py` | `AC-001` |
| `Shipment` | Fulfillment | `INV-TEN-001`, `INV-DATA-001` | `contract/test_shipment_contracts.py` | `AC-001` |
| `SupportTicket`| Service Intelligence | `INV-TEN-001`, `INV-PRV-001` | `contract/test_ticket_contracts.py` | `AC-001` |
| `MaintenanceEvent`| Fulfillment | `INV-TEN-001` | `contract/test_maintenance_contracts.py` | `AC-001` |
| `Contract` | Contract Intelligence| `INV-TEN-001`, `INV-EVD-001` | `contract/test_contract_contracts.py` | `AC-001`, `AC-005` |
| `PaymentReference`| Revenue Ledger | `INV-TEN-001`, `INV-SEC-001` | `contract/test_payment_contracts.py` | `AC-001` |
| `GroundTruth` | Evaluation System | `INV-DATA-001`, `NFR-AI-002` | `eval/test_ground_truth_isolation.py` | `AC-001`, `AC-006` |
