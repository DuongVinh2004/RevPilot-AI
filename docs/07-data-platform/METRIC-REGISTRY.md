# Canonical Metric Registry Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 01 — Canonical Data and Synthetic Benchmark
Owner: Analytics Architecture
Traceability: `BR-001`, `BR-002`, `FR-DET-001`, `FR-INV-004`, `INV-TEN-001`, `INV-DATA-001`, `NFR-AI-002`, `NFR-AI-004`, `AC-002`, `AC-014`

---

## 1. Registry Purpose and Governance Rules

This Metric Registry is the single canonical source of truth for all business metrics calculated, monitored, and analyzed within RevPilot AI. No analytical query, anomaly detector, investigation workflow, or decision optimizer may compute or reference a business metric that is not explicitly registered herein.

### Governance Invariants
1. **Immutable Semantic Contract (`INV-DATA-001`)**: Metric definitions, formulas, numerators, and denominators are versioned data contracts. Code implementations MUST NOT alter semantic definitions or aggregation logic.
2. **Strict Time Semantics**: All metrics are evaluated strictly against `event_time` in UTC. `event_time` and `ingested_at` MUST NEVER be mixed. Queries during investigations, benchmarks, and backtests MUST enforce `as_of` watermarking to eliminate future data leakage.
3. **Mandatory Tenant Scoping (`INV-TEN-001`)**: Every metric query is strictly tenant-scoped. Aggregation across tenants is prohibited at the application layer.
4. **Causal Distinction**: Predictive probabilities (e.g., churn probability) MUST NOT be substituted for causal treatment effects or incremental uplift (`BR-002`, `FR-ML-003`).
5. **No Measurement Fabrication (`AC-014`)**: Performance benchmarks, target values, and design assumptions are documented separately from measured results. Metric definitions define computation contracts, not fabricated outputs.

---

## 2. Canonical Business Metrics Catalog

### 2.1. Metric: `cancellation_rate`

- **Metric ID**: `METRIC-001`
- **Metric Name**: `cancellation_rate`
- **Version**: `1.0.0`
- **Owner**: Analytics Module / Revenue Intelligence Team
- **Business Definition**: The proportion of customer orders placed within a given time window that transitioned to a `CANCELLED` status.
- **Numerator**: Count of distinct `Order` records where `order_status = 'CANCELLED'` and `event_time` falls within the time grain:
  ```sql
  COUNT(DISTINCT CASE WHEN order_status = 'CANCELLED' THEN id END)
  ```
- **Denominator**: Count of total eligible `Order` records placed within the time grain:
  ```sql
  COUNT(DISTINCT id)
  ```
- **Aggregation**: `RATIO` (Numerator / Denominator)
- **Unit**: `PERCENT` (0.00% to 100.00%, or decimal 0.0000 to 1.0000)
- **Currency**: `NOT APPLICABLE`
- **Grain**: `HOURLY`, `DAILY`, `WEEKLY`, `MONTHLY`
- **Dimensions**:
  - `carrier_id`: Associated shipment carrier.
  - `warehouse_id`: Origin fulfillment facility.
  - `origin_region`: Geographic origin (e.g., `US-MIDWEST`).
  - `destination_region`: Customer delivery region.
  - `customer_tier`: Customer segment tier (`TIER_1_PLATINUM`, `TIER_2_GOLD`, `TIER_3_STANDARD`).
  - `product_category`: Primary product category of ordered items.
- **Allowed Filters**: `carrier_id`, `warehouse_id`, `origin_region`, `destination_region`, `customer_tier`, `product_category`.
- **Temporal Semantics**:
  - Timestamp column: `orders.event_time`
  - Effective time: Current active contract version.
  - As-of boundary: `orders.event_time <= :as_of_time AND (orders.cancelled_at IS NULL OR orders.cancelled_at <= :as_of_time)`.
  - Timezone: `UTC`.
- **Null / Zero Behavior**: If Denominator is `0`, metric value is `0.0` with `is_zero_volume_sample = true`.
- **Late Data Behavior**: Orders arriving with `event_time` within 24 hours of `:as_of_time` trigger an incremental partition update; events older than 7 days require a supervised backfill reconciliation job.
- **Source Entities**: `Order` (`canonical.orders`), `Shipment` (`canonical.shipments`).
- **Tenant Scope**: Strict. Mandatory filter `tenant_id = :current_tenant_id`.
- **Quality Checks**: Value MUST be between `0.0000` and `1.0000`. Denominator MUST be `>= Numerator`.
- **Test Fixture**: `tests/fixtures/metrics/cancellation_rate_fixture.json` (deterministic seed 42 verification).
- **Downstream Consumers**: `AnomalyDetector` (`FR-DET-002`), `InvestigationWorkflow` (`FR-INV-001`), `CausalEngine` (`FR-ML-004`).
- **Deprecation / Replacement Behavior**: SemVer deprecation. Replaced by `METRIC-001-v2` with minimum 60-day dual-run notice.

---

### 2.2. Metric: `revenue_at_risk`

- **Metric ID**: `METRIC-002`
- **Metric Name**: `revenue_at_risk`
- **Version**: `1.0.0`
- **Owner**: Revenue Ledger Module / FinOps
- **Business Definition**: The total monetary value of active orders or subscriptions currently exposed to severe fulfillment delays, SLA breaches, or customer cancellation signals.
- **Numerator**: Sum of net order value (`total_cents`) for distinct orders whose fulfillment is currently flagged `is_delayed = true` OR where associated support tickets have `topic = 'CANCELLATION_INQUIRY'` and `status = 'OPEN'`. To eliminate double-counting across multi-shipment or multi-ticket joins, aggregation enforces distinct order scoping via subqueries:
  ```sql
  SELECT COALESCE(SUM(o.total_cents), 0)
  FROM canonical_orders o
  WHERE o.tenant_id = :tenant_id
    AND o.order_placed_at <= :as_of_time
    AND (
        o.order_id IN (
            SELECT s.order_id 
            FROM canonical_shipments s 
            WHERE s.tenant_id = :tenant_id 
              AND s.is_delayed = true
              AND s.shipped_at <= :as_of_time
        )
        OR o.order_id IN (
            SELECT t.order_id 
            FROM canonical_tickets t 
            WHERE t.tenant_id = :tenant_id 
              AND t.topic = 'CANCELLATION_INQUIRY' 
              AND t.status = 'OPEN'
              AND t.created_at <= :as_of_time
        )
    );
  ```
- **Denominator**: `NOT APPLICABLE`
- **Aggregation**: `SUM`
- **Unit**: `CURRENCY_MINOR_UNITS` (integer cents)
- **Currency**: `USD` (or tenant declared base currency per ISO 4217)
- **Grain**: `DAILY`, `AS_OF_SNAPSHOT`
- **Dimensions**: `customer_tier`, `warehouse_id`, `carrier_id`, `origin_region`.
- **Allowed Filters**: `customer_tier`, `carrier_id`, `warehouse_id`.
- **Temporal Semantics**: Evaluated as an `as_of` snapshot of currently open/unsettled risks.
- **Null / Zero Behavior**: If no matching orders, value is `0` cents.
- **Late Data Behavior**: Snapshot strictly reflects data ingested before `:as_of_time`.
- **Source Entities**: `Order`, `Shipment`, `SupportTicket`, `Customer`.
- **Tenant Scope**: Mandatory `tenant_id` constraint.
- **Quality Checks**: Amount MUST be non-negative (`>= 0`).
- **Test Fixture**: `tests/fixtures/metrics/revenue_at_risk_fixture.json`.
- **Downstream Consumers**: `DecisionOptimizer` (`FR-DEC-001`), `ExecutiveSummaryAgent`.

---

### 2.3. Metric: `fulfillment_delay_rate`

- **Metric ID**: `METRIC-003`
- **Metric Name**: `fulfillment_delay_rate`
- **Version**: `1.0.0`
- **Owner**: Fulfillment Module
- **Business Definition**: The percentage of dispatched or delivered shipments where dispatch or delivery exceeded estimated or contractually promised timestamps.
- **Numerator**: Count of shipments where `is_delayed = true`:
  ```sql
  COUNT(DISTINCT CASE WHEN is_delayed = true THEN id END)
  ```
- **Denominator**: Total count of shipments with dispatch attempts in window:
  ```sql
  COUNT(DISTINCT id)
  ```
- **Aggregation**: `RATIO`
- **Unit**: `PERCENT` (0.00% to 100.00%)
- **Currency**: `NOT APPLICABLE`
- **Grain**: `HOURLY`, `DAILY`, `WEEKLY`
- **Dimensions**: `carrier_id`, `warehouse_id`, `origin_region`, `destination_region`.
- **Allowed Filters**: `carrier_id`, `warehouse_id`, `origin_region`.
- **Temporal Semantics**: `shipments.event_time` (dispatch event). UTC.
- **Null / Zero Behavior**: 0 shipments yields `0.0`.
- **Late Data Behavior**: Standard 24h watermark window.
- **Source Entities**: `Shipment` (`canonical.shipments`).
- **Tenant Scope**: Mandatory `tenant_id`.
- **Quality Checks**: Value between `0.0` and `1.0`.
- **Test Fixture**: `tests/fixtures/metrics/fulfillment_delay_fixture.json`.
- **Downstream Consumers**: `AnomalyDetector`, `RootCauseAnalyzer`.

---

### 2.4. Metric: `sla_violation_rate`

- **Metric ID**: `METRIC-004`
- **Metric Name**: `sla_violation_rate`
- **Version**: `1.0.0`
- **Owner**: Contract Intelligence Module
- **Business Definition**: The proportion of customer orders or shipments that breached explicit contractual SLA thresholds defined in active contracts.
- **Numerator**: Count of orders/shipments exceeding `ContractClause.sla_threshold_hours`:
  ```sql
  COUNT(DISTINCT CASE
      WHEN EXTRACT(EPOCH FROM (shipments.actual_delivered_at - orders.event_time))/3600.0
           > contract_clauses.sla_threshold_hours
      THEN orders.id
  END)
  ```
- **Denominator**: Total count of contract-governed delivered orders:
  ```sql
  COUNT(DISTINCT orders.id)
  ```
- **Aggregation**: `RATIO`
- **Unit**: `PERCENT`
- **Currency**: `NOT APPLICABLE`
- **Grain**: `DAILY`, `WEEKLY`, `MONTHLY`
- **Dimensions**: `customer_tier`, `contract_type`, `carrier_id`.
- **Allowed Filters**: `customer_tier`, `contract_type`.
- **Temporal Semantics**: Order completion time `orders.event_time`.
- **Null / Zero Behavior**: Denominator 0 yields `0.0`.
- **Late Data Behavior**: Reconciled at month-end billing closure.
- **Source Entities**: `Order`, `Shipment`, `Contract`, `ContractClause`.
- **Tenant Scope**: Mandatory `tenant_id`.
- **Quality Checks**: Between `0.0` and `1.0`.
- **Test Fixture**: `tests/fixtures/metrics/sla_violation_fixture.json`.
- **Downstream Consumers**: `ContractIntelligenceAgent`, `BillingModule`.

---

### 2.5. Metric: `payment_failure_rate`

- **Metric ID**: `METRIC-005`
- **Metric Name**: `payment_failure_rate`
- **Version**: `1.0.0`
- **Owner**: Revenue Ledger Module
- **Business Definition**: The ratio of failed payment attempts to total payment authorization and capture attempts.
- **Numerator**: Count of payments where `payment_status = 'FAILED'`:
  ```sql
  COUNT(DISTINCT CASE WHEN payment_status = 'FAILED' THEN id END)
  ```
- **Denominator**: Total payment transaction attempts:
  ```sql
  COUNT(DISTINCT id)
  ```
- **Aggregation**: `RATIO`
- **Unit**: `PERCENT`
- **Currency**: `NOT APPLICABLE`
- **Grain**: `HOURLY`, `DAILY`
- **Dimensions**: `gateway_provider`, `transaction_type`, `currency`.
- **Allowed Filters**: `gateway_provider`.
- **Temporal Semantics**: `payment_references.processed_at`.
- **Null / Zero Behavior**: 0 attempts yields `0.0`.
- **Late Data Behavior**: Gateway webhook retry window (4 hours).
- **Source Entities**: `PaymentReference` (`canonical.payment_references`).
- **Tenant Scope**: Mandatory `tenant_id`.
- **Quality Checks**: Range `[0.0, 1.0]`.
- **Test Fixture**: `tests/fixtures/metrics/payment_failure_fixture.json`.
- **Downstream Consumers**: `AnomalyDetector` (competing hypothesis disprover).

---

### 2.6. Metric: `customer_churn_rate`

- **Metric ID**: `METRIC-006`
- **Metric Name**: `customer_churn_rate`
- **Version**: `1.0.0`
- **Owner**: Customer 360 / ML Platform
- **Business Definition**: The percentage of active customers at the start of a 30-day cohort period who transitioned to `CHURNED` status before period end.
- **Numerator**: Count of cohort customers whose status became `CHURNED` within window:
  ```sql
  COUNT(DISTINCT CASE WHEN status = 'CHURNED' THEN id END)
  ```
- **Denominator**: Total count of active customers at cohort start timestamp:
  ```sql
  COUNT(DISTINCT CASE WHEN status IN ('ACTIVE', 'CHURN_RISK', 'CHURNED') THEN id END)
  ```
- **Aggregation**: `RATIO`
- **Unit**: `PERCENT`
- **Currency**: `NOT APPLICABLE`
- **Grain**: `MONTHLY` (30-day rolling window)
- **Dimensions**: `segment`, `account_tier`, `billing_country`.
- **Allowed Filters**: `segment`, `account_tier`.
- **Temporal Semantics**: Evaluated on fixed cohort boundary dates.
- **Null / Zero Behavior**: 0 customers yields `0.0`.
- **Late Data Behavior**: Retrospective adjustments not permitted after cohort freeze.
- **Source Entities**: `Customer` (`canonical.customers`).
- **Tenant Scope**: Mandatory `tenant_id`.
- **Quality Checks**: Range `[0.0, 1.0]`.
- **Test Fixture**: `tests/fixtures/metrics/churn_rate_fixture.json`.
- **Downstream Consumers**: `MLPlatform` (`FR-ML-002`), `DecisionOptimizer`.

---

### 2.7. Metric: `order_volume`

- **Metric ID**: `METRIC-007`
- **Metric Name**: `order_volume`
- **Version**: `1.0.0`
- **Owner**: Fulfillment Module
- **Business Definition**: Total count of distinct orders placed within the time grain.
- **Numerator**: Count of distinct order IDs:
  ```sql
  COUNT(DISTINCT id)
  ```
- **Denominator**: `NOT APPLICABLE`
- **Aggregation**: `COUNT`
- **Unit**: `COUNT` (integer >= 0)
- **Currency**: `NOT APPLICABLE`
- **Grain**: `HOURLY`, `DAILY`, `WEEKLY`
- **Dimensions**: `customer_tier`, `origin_region`, `product_category`.
- **Allowed Filters**: `customer_tier`, `origin_region`.
- **Temporal Semantics**: `orders.event_time`.
- **Null / Zero Behavior**: Absence of rows returns `0`.
- **Late Data Behavior**: Standard 24h arrival window.
- **Source Entities**: `Order` (`canonical.orders`).
- **Tenant Scope**: Mandatory `tenant_id`.
- **Quality Checks**: Value MUST be `>= 0`.
- **Test Fixture**: `tests/fixtures/metrics/order_volume_fixture.json`.
- **Downstream Consumers**: `AnomalyDetector`, `CapacityPlanner`.

---

### 2.8. Metric: `shipment_volume`

- **Metric ID**: `METRIC-008`
- **Metric Name**: `shipment_volume`
- **Version**: `1.0.0`
- **Owner**: Fulfillment Module
- **Business Definition**: Total count of distinct shipment dispatches initiated within the time grain.
- **Numerator**: Count of distinct shipment IDs:
  ```sql
  COUNT(DISTINCT id)
  ```
- **Denominator**: `NOT APPLICABLE`
- **Aggregation**: `COUNT`
- **Unit**: `COUNT` (integer >= 0)
- **Currency**: `NOT APPLICABLE`
- **Grain**: `HOURLY`, `DAILY`
- **Dimensions**: `carrier_id`, `warehouse_id`, `origin_region`.
- **Allowed Filters**: `carrier_id`, `warehouse_id`.
- **Temporal Semantics**: `shipments.dispatched_at` (or `event_time`).
- **Null / Zero Behavior**: Returns `0`.
- **Late Data Behavior**: 24h window.
- **Source Entities**: `Shipment` (`canonical.shipments`).
- **Tenant Scope**: Mandatory `tenant_id`.
- **Quality Checks**: `>= 0`.
- **Test Fixture**: `tests/fixtures/metrics/shipment_volume_fixture.json`.
- **Downstream Consumers**: `AnomalyDetector`, `RootCauseAnalyzer`.

---

### 2.9. Metric: `support_ticket_volume`

- **Metric ID**: `METRIC-009`
- **Metric Name**: `support_ticket_volume`
- **Version**: `1.0.0`
- **Owner**: Service Intelligence Module
- **Business Definition**: Total count of new support tickets submitted within the time grain.
- **Numerator**: Count of distinct ticket IDs:
  ```sql
  COUNT(DISTINCT id)
  ```
- **Denominator**: `NOT APPLICABLE`
- **Aggregation**: `COUNT`
- **Unit**: `COUNT` (integer >= 0)
- **Currency**: `NOT APPLICABLE`
- **Grain**: `HOURLY`, `DAILY`, `WEEKLY`
- **Dimensions**: `topic`, `priority`, `customer_tier`.
- **Allowed Filters**: `topic`, `priority`.
- **Temporal Semantics**: `support_tickets.event_time`.
- **Null / Zero Behavior**: Returns `0`.
- **Late Data Behavior**: 12h sync window.
- **Source Entities**: `SupportTicket` (`canonical.support_tickets`).
- **Tenant Scope**: Mandatory `tenant_id`.
- **Quality Checks**: `>= 0`.
- **Test Fixture**: `tests/fixtures/metrics/ticket_volume_fixture.json`.
- **Downstream Consumers**: `AnomalyDetector`, `ServiceIntelligenceAgent`.

---

## 3. Metric Registry Summary Matrix

| Metric ID | Metric Name | Aggregation | Unit | Primary Entities | Downstream Use |
|---|---|---|---|---|---|
| `METRIC-001` | `cancellation_rate` | RATIO | PERCENT | `Order`, `Shipment` | Anomaly Detection, Causal Study |
| `METRIC-002` | `revenue_at_risk` | SUM | CENTS (USD) | `Order`, `Shipment`, `Ticket` | Decision Optimization, Alerting |
| `METRIC-003` | `fulfillment_delay_rate` | RATIO | PERCENT | `Shipment` | Investigation Evidence, Anomaly |
| `METRIC-004` | `sla_violation_rate` | RATIO | PERCENT | `Order`, `Shipment`, `Contract` | Billing, Contract Intelligence |
| `METRIC-005` | `payment_failure_rate`| RATIO | PERCENT | `PaymentReference` | Confounder/Alternative Rejection|
| `METRIC-006` | `customer_churn_rate` | RATIO | PERCENT | `Customer` | Churn Baseline, Retention Policy|
| `METRIC-007` | `order_volume` | COUNT | COUNT | `Order` | Baseline Scaling, Workload SLI |
| `METRIC-008` | `shipment_volume` | COUNT | COUNT | `Shipment` | Carrier Load, Dispatch Capacity |
| `METRIC-009` | `support_ticket_volume`| COUNT | COUNT | `SupportTicket` | Customer Sentiment, Signal Flare |
