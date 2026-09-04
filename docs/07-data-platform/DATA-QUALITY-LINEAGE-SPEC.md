# Data Quality, Lineage, and Quarantine Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 01 — Canonical Data and Synthetic Benchmark
Owner: Data Platform Architecture
Traceability: `BR-001`, `BR-004`, `INV-TEN-001`, `INV-TEN-002`, `INV-DATA-001`, `INV-DATA-002`, `NFR-TEN-001`, `NFR-AUD-001`, `NFR-PRV-001`, `ADR-0004`, `ADR-0005`

---

## 1. Principles and Architectural Invariants

1. **No Silent Mutations**: Ingestion pipelines and transformation jobs MUST NEVER silently alter, coerce, or "repair" corrupted or invalid business data in ways that alter business meaning. Malformed data is routed to quarantine.
2. **Fail-Closed Isolation (`INV-TEN-001`, `INV-TEN-002`)**: Records missing tenant context or presenting mismatched tenant credentials fail immediately and cannot be persisted to canonical tables.
3. **Immutable Lineage (`INV-DATA-002`, `INV-AUD-001`)**: Every canonical entity record carries lineage references (`lineage_trace_id`, `source_system`, `source_id`, `dedup_key`) linking back to raw source payloads.
4. **Deterministic Replay**: Ingestion pipelines are idempotent. Reprocessing the same raw payload with the same transformation version yields identical canonical state without duplicate entries or state corruption.
5. **Operator Visibility**: Quarantined records generate structured telemetry, alerts, and operator-visible diagnostics with precise error codes.

---

## 2. Ingestion Pipeline and Storage Zones

```text
[Raw Source / Webhook / Batch]
            │
            ▼
   ┌───────────────────┐
   │ 1. Raw Zone (raw) │ ──> Store verbatim payload, compute payload_hash (SHA-256)
   └───────────────────┘
            │
            ▼
 ┌──────────────────────┐   FAIL    ┌───────────────────────┐
 │ Data Quality Filter  │ ────────> │ raw_quarantine Table  │ (Operator review / DLQ)
 └──────────────────────┘           └───────────────────────┘
            │ PASS
            ▼
┌────────────────────────────┐
│ 2. Normalized Zone         │ ──> Syntactic parsing, tabular typing
└────────────────────────────┘
            │
            ▼
┌────────────────────────────┐
│ 3. Canonical Zone          │ ──> Authoritative domain aggregates, composite tenant keys
└────────────────────────────┘
            │
            ▼
┌────────────────────────────┐
│ 4. Projections / Views     │ ──> Read-only feature stores, metrics, vector index
└────────────────────────────┘
```

---

## 3. Data Quality Rules Catalog

### 3.1. Rule: `DQ-SCH-001` — Schema Validation
- **Rule ID**: `DQ-SCH-001`
- **Scope**: Inbound raw payload across all source systems.
- **Severity**: `CRITICAL`
- **Owner**: Data Platform Core
- **Input**: Raw JSON, CSV, or Avro payload.
- **Expected Result**: Payload conforms strictly to the registered JSON Schema / Pydantic model for the declared `schema_version`. Unknown fields in strict mode or missing required structure are rejected.
- **Failure Behavior**: Drop write to normalized/canonical; persist raw payload into `raw_quarantine` with status `SCHEMA_VALIDATION_FAILED`.
- **Quarantine / Retry Policy**: Non-retryable without pipeline schema update or upstream provider payload fix.
- **Metric / Telemetry**: `data_quality_rejections_total{rule_id="DQ-SCH-001", source_system=...}`
- **Test Case**: `tests/data_quality/test_schema_validation.py::test_malformed_json_schema_rejection`
- **Acceptance Condition**: 100% of schema-violating payloads route to quarantine; 0 write to canonical.

---

### 3.2. Rule: `DQ-REQ-001` — Required Non-Null Field Check
- **Rule ID**: `DQ-REQ-001`
- **Scope**: Core canonical fields (`tenant_id`, `id`, `event_time`, `currency`, `total_cents`).
- **Severity**: `CRITICAL`
- **Owner**: Data Architecture
- **Input**: Parsed entity dictionary.
- **Expected Result**: None of the mandatory fields evaluate to `NULL`, empty string, or whitespace.
- **Failure Behavior**: Fail-closed rejection. Route to `raw_quarantine` with `rejection_code = 'MISSING_MANDATORY_FIELD'`.
- **Quarantine / Retry Policy**: Quarantined until manually resolved or re-ingested with valid fields.
- **Metric / Telemetry**: `data_quality_null_failures_total{rule_id="DQ-REQ-001", field=...}`
- **Test Case**: `tests/data_quality/test_required_fields.py::test_missing_tenant_id_fails`
- **Acceptance Condition**: Missing any required field produces immediate quarantine entry.

---

### 3.3. Rule: `DQ-TYP-001` — Type and Numeric Range Check
- **Rule ID**: `DQ-TYP-001`
- **Scope**: Monetary values, quantities, percentages, and status enums.
- **Severity**: `HIGH`
- **Owner**: Revenue Ledger & Fulfillment
- **Input**: `Order.total_cents`, `OrderLine.quantity`, `MaintenanceEvent.impact_capacity_reduction_pct`.
- **Expected Result**:
  - `total_cents >= 0` and integer
  - `quantity > 0` and integer
  - `impact_capacity_reduction_pct BETWEEN 0.00 AND 100.00`
  - Enums belong to defined canonical set.
- **Failure Behavior**: Rejection to quarantine; do not coerce negative numbers to zero.
- **Quarantine / Retry Policy**: Non-retryable without upstream correction.
- **Metric / Telemetry**: `data_quality_range_failures_total{rule_id="DQ-TYP-001"}`
- **Test Case**: `tests/data_quality/test_range_checks.py::test_negative_monetary_amount_rejection`
- **Acceptance Condition**: Negative prices and out-of-range percentages quarantined 100%.

---

### 3.4. Rule: `DQ-REF-001` — Cross-Entity Referential Integrity
- **Rule ID**: `DQ-REF-001`
- **Scope**: Foreign key references within canonical zone (`Order.customer_id`, `Shipment.order_id`).
- **Severity**: `HIGH`
- **Owner**: Data Architecture
- **Input**: Child entity and referenced parent entity key within same `tenant_id`.
- **Expected Result**: Parent entity exists in `canonical` tables under the identical `tenant_id`.
- **Failure Behavior**: If parent record has not arrived, buffer child in `raw_pending_dependency` for a 15-minute grace window. If parent still absent after timeout, route to `raw_quarantine` with `ORPHAN_FOREIGN_KEY`.
- **Quarantine / Retry Policy**: Automatic retry every 60s during 15-min window; quarantine if unresolved.
- **Metric / Telemetry**: `data_quality_orphan_records_total{rule_id="DQ-REF-001"}`
- **Test Case**: `tests/data_quality/test_referential_integrity.py::test_orphan_order_line_quarantined`
- **Acceptance Condition**: Zero foreign keys point to non-existent or cross-tenant parents in canonical tables.

---

### 3.5. Rule: `DQ-TEN-001` — Tenant Ownership Validation
- **Rule ID**: `DQ-TEN-001`
- **Scope**: Ingestion authorization and persistence boundary.
- **Severity**: `CRITICAL`
- **Owner**: Security & Tenancy Architecture
- **Input**: Inbound record `tenant_id` vs authenticated connector/session tenant identity.
- **Expected Result**: Record `tenant_id` strictly matches the authenticated connector tenant. Cross-tenant injection attempts or empty tenant headers are blocked.
- **Failure Behavior**: Reject payload with `AuthorizationError`, log security audit event, route to isolated security quarantine.
- **Quarantine / Retry Policy**: Non-retryable. Alert security operations.
- **Metric / Telemetry**: `security_tenant_mismatch_total{rule_id="DQ-TEN-001"}`
- **Test Case**: `tests/tenancy/test_tenant_isolation_negative.py::test_payload_tenant_mismatch_rejected`
- **Acceptance Condition**: 100% of mismatched tenant payloads blocked; zero row leakage.

---

### 3.6. Rule: `DQ-DUP-001` — Idempotent Duplicate Detection
- **Rule ID**: `DQ-DUP-001`
- **Scope**: Ingestion endpoint and transform loader.
- **Severity**: `MEDIUM`
- **Owner**: Data Platform Core
- **Input**: Record `dedup_key` (hash of `tenant_id:source_system:source_id:event_time`).
- **Expected Result**: If `dedup_key` already exists with matching payload hash, acknowledge as duplicate and skip redundant write (idempotent 200 OK). If payload hash differs, flag as `UNEXPECTED_DUPLICATE_PAYLOAD_MUTATION`.
- **Failure Behavior**: Conflicting duplicate routes to quarantine for operator inspection.
- **Quarantine / Retry Policy**: Idempotent pass for identical; quarantine for conflicting payload.
- **Metric / Telemetry**: `ingestion_duplicates_skipped_total{rule_id="DQ-DUP-001"}`
- **Test Case**: `tests/data_quality/test_duplicate_detection.py::test_idempotent_reingestion`
- **Acceptance Condition**: Replaying 1,000 identical events produces exactly 0 duplicate canonical rows.

---

### 3.7. Rule: `DQ-ORD-001` — Event Ordering and Timestamp Sanity
- **Rule ID**: `DQ-ORD-001`
- **Scope**: All event-sourced entities.
- **Severity**: `HIGH`
- **Owner**: Data Architecture
- **Input**: `event_time`, `ingested_at`, `effective_from`, `effective_to`.
- **Expected Result**:
  - `event_time <= ingested_at + INTERVAL '5 minutes'` (clock skew tolerance)
  - `event_time > TIMESTAMP '2020-01-01 00:00:00Z'` (reject absurd historical dates)
  - `effective_to >= effective_from` if `effective_to` is non-null.
- **Failure Behavior**: Route to `raw_quarantine` with `INVALID_TIMESTAMP_SEQUENCE`.
- **Quarantine / Retry Policy**: Operator review.
- **Metric / Telemetry**: `data_quality_timestamp_anomalies_total{rule_id="DQ-ORD-001"}`
- **Test Case**: `tests/data_quality/test_timestamp_sanity.py::test_future_timestamp_rejected`
- **Acceptance Condition**: Events with impossible future event times are rejected.

---

### 3.8. Rule: `DQ-CUR-001` — Currency Code and Monetary Consistency
- **Rule ID**: `DQ-CUR-001`
- **Scope**: All financial attributes.
- **Severity**: `HIGH`
- **Owner**: Revenue Ledger
- **Input**: `currency` field.
- **Expected Result**: Must be valid 3-character ISO 4217 currency code matching tenant enabled currency list.
- **Failure Behavior**: Route to `raw_quarantine` with `UNSUPPORTED_CURRENCY`.
- **Quarantine / Retry Policy**: Non-retryable without currency configuration.
- **Metric / Telemetry**: `data_quality_currency_errors_total{rule_id="DQ-CUR-001"}`
- **Test Case**: `tests/data_quality/test_currency_validation.py::test_invalid_currency_rejected`
- **Acceptance Condition**: Unknown or unmapped currencies quarantined 100%.

---

### 3.9. Rule: `DQ-VOL-001` — Ingestion Volume Anomaly Detection
- **Rule ID**: `DQ-VOL-001`
- **Scope**: Tenant-level hourly ingestion volume.
- **Severity**: `MEDIUM` (Warning / Operational Alert)
- **Owner**: SRE / Data Platform
- **Input**: Rolling 1-hour count of received records vs 7-day trailing baseline.
- **Expected Result**: Hourly volume within `[0.1x, 5.0x]` of expected baseline unless explicit batch sync scheduled.
- **Failure Behavior**: Pipeline continues ingestion, but emits `DataFreshnessDegraded` or `VolumeSpikeAlert` alert to monitoring system.
- **Quarantine / Retry Policy**: No quarantine; operational telemetry only.
- **Metric / Telemetry**: `tenant_ingestion_volume_ratio{tenant_id=...}`
- **Test Case**: `tests/data_quality/test_volume_anomaly.py::test_volume_spike_alert`
- **Acceptance Condition**: 5x volume spike generates alert within 60 seconds.

---

### 3.10. Rule: `DQ-DFT-001` — Metric Semantic Drift Detection
- **Rule ID**: `DQ-DFT-001`
- **Scope**: Core metric output distributions.
- **Severity**: `HIGH`
- **Owner**: Analytics Module
- **Input**: Daily aggregated metric values (e.g., `cancellation_rate`).
- **Expected Result**: Daily metric values stay within statistical 3-sigma bounds of rolling 30-day mean unless an anomaly investigation is active.
- **Failure Behavior**: Flag metric distribution drift, notify analytics owner, trigger baseline re-check.
- **Quarantine / Retry Policy**: Output remains visible marked `PRELIMINARY_DRIFT_DETECTED`.
- **Metric / Telemetry**: `metric_distribution_drift_score{metric_id=...}`
- **Test Case**: `tests/data_quality/test_metric_drift.py::test_cancellation_rate_drift_trigger`
- **Acceptance Condition**: Structural drift triggers automated notification.

---

## 4. Lineage Metadata Capture Specification

Every transformation from `raw` to `canonical` produces an immutable lineage event recorded in `canonical_lineage_log`:

```json
{
  "lineage_id": "lin_01h8abcdef9876543210",
  "tenant_id": "ten_01h7abcde123456789",
  "source_system": "shopify_connector_v1",
  "source_batch_id": "batch_20260903_001",
  "raw_payload_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "transformation_name": "TransformShopifyOrdersToCanonical",
  "transformation_version": "1.0.0",
  "input_record_count": 1000,
  "canonical_record_count": 998,
  "quarantined_record_count": 2,
  "executed_at": "2026-09-03T15:00:00Z",
  "operator_id": "system_worker_worker01"
}
```

---

## 5. Quarantine Table Schema and Replay Architecture

### 5.1. Table Definition (`raw_quarantine`)
```sql
CREATE TABLE raw_quarantine (
    tenant_id VARCHAR(64) NOT NULL,
    quarantine_id VARCHAR(64) NOT NULL,
    rule_id VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    source_system VARCHAR(64) NOT NULL,
    source_id VARCHAR(128),
    raw_payload JSONB NOT NULL,
    rejection_reason TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'QUARANTINED', -- QUARANTINED, REPROCESSED, DISCARDED
    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(64),
    CONSTRAINT pk_raw_quarantine PRIMARY KEY (tenant_id, quarantine_id)
);
```

### 5.2. Replay and Reprocessing Workflow
1. **Root-Cause Resolution**: Data engineer or source provider resolves schema mismatch or configuration defect.
2. **Deterministic Replay Tool**: Operator triggers `replay_quarantine_batch(tenant_id, quarantine_id_list, target_transformation_version)`.
3. **Execution**:
   - Re-runs validation rules against original `raw_payload`.
   - On pass: writes to `canonical.*`, updates `raw_quarantine.status = 'REPROCESSED'`.
   - On fail: updates `raw_quarantine.rejection_reason` with new failure output; remains `QUARANTINED`.
4. **Audit Trail**: Every replay attempt logs an immutable `AuditEvent` (`INV-AUD-001`).

---

## 6. Safe Handling of Malformed and Poisoned Inputs

1. **Denial-of-Service Defense**: Maximum payload size enforced at API gateway (10 MB). Oversized payloads rejected with HTTP 413.
2. **No Recursive Unpacking**: JSON nested depth capped at 8 levels. Payloads exceeding depth limit fail `DQ-SCH-001`.
3. **Prompt Injection / Adversarial Text**: Customer reviews, ticket transcripts, and contract texts are categorized as untrusted content (`INV-SEC-002`). They are DLP-scanned, stored verbatim, and NEVER passed to agent instruction prompts without strict XML delimitation and system prompt taint tracking.

---

## 7. Late-Arriving Events, Metric Recomputation, and Anomaly Supersession

### 7.1. Late and Out-of-Order Semantics
1. **Late-Arriving Definition**: An event whose `ingested_at > event_time + INTERVAL '2 hours'`.
2. **7-Day Volatility Buffer**: The analytical platform maintains a trailing 7-day volatility buffer. Canonical rollups within this window are considered mutable projections and recomputable on demand.
3. **Immutability Beyond Buffer**: Records with `event_time < CURRENT_TIMESTAMP - INTERVAL '7 days'` require explicit operator backfill authorization (`OPERATOR_REPLAY_AUTHORIZED`).

### 7.2. Metric Recomputation and Anomaly Reconciliation
1. **Asynchronous Recomputation**: Ingestion of late-arriving batches triggers an outbox event `canonical.batch_updated.v1`. The Metric Service schedules a reconciliation pass for affected slices.
2. **Anomaly Supersession Workflow**:
   - If recalculated metric values no longer exceed the detection threshold:
     - The anomaly status is transitioned to `SUPPRESSED`.
     - `suppression_reason` is set to `SUPERSEDED_BY_RECOMPUTATION`.
     - `effective_to` is updated to the reconciliation timestamp.
     - An audit event `anomaly.suppressed.v1` is emitted.
   - **No Silent Overwrite Invariant (`INV-DATA-002`)**: Historical anomaly records are NEVER deleted or overwritten in place. The entire audit trail remains immutable and inspectable.
3. **Stale Result Marking**: Anomaly records whose underlying metric data is undergoing reconciliation are flagged `data_freshness = 'RECALCULATING'`. Consumers receive a warning header `X-RevPilot-Data-Freshness: RECALCULATING`.
