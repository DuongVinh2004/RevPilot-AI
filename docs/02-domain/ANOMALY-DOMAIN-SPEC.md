# Anomaly Domain Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 02 — Detection and Analytics
Owner: Domain Architecture + Analytics Architecture
Traceability: `BR-001`, `FR-DET-001..006`, `INV-TEN-001..003`, `INV-DATA-001`, `NFR-AI-002`, `NFR-AI-004`, `AC-002`, `AC-014`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Architectural Scope and Foundational Distinctions

This specification establishes the canonical domain models, aggregate structure, lifecycle transitions, and semantic boundaries for revenue anomalies within RevPilot AI.

### 1.1. Conceptual Boundary Distinctions
To preserve mathematical rigor and prevent hallucinated certainty, RevPilot strictly separates the analytical lifecycle into discrete conceptual layers:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                RevPilot Analytical Boundary                            │
├──────────────────────┬──────────────────────────────────────────┬──────────────────────┤
│ Concept              │ Definition & Responsibility              │ Owning Phase / Module│
├──────────────────────┼──────────────────────────────────────────┼──────────────────────┤
│ 1. Anomaly Signal    │ Raw statistical divergence from baseline │ Phase 02 / Analytics │
│ 2. Anomaly Record    │ Validated, tenant-isolated state entity  │ Phase 02 / Analytics │
│ 3. Localization      │ Dimensional drill-down (observed assoc.) │ Phase 02 / Analytics │
│ 4. Hypothesis        │ Candidate causal explanation for signal  │ Phase 03 / Investigate│
│ 5. Causal Effect     │ Quantified counterfactual estimand (ATE) │ Phase 04 / Causal AI │
│ 6. Recommendation    │ Policy-compliant intervention proposal   │ Phase 05 / Decisions │
└──────────────────────┴──────────────────────────────────────────┴──────────────────────┘
```

> [!IMPORTANT]
> **No Causal Claim Invariant (`INV-AI-001`)**: An anomaly detector observes statistical deviation; it DOES NOT determine causality. An anomaly record MUST NOT assert root causes, causal attribution, or recommended actions. Root-cause determination is strictly deferred to Phase 04 causal verifiers.

---

## 2. Canonical Anomaly Aggregate Specification

### 2.1. Anomaly Entity Attributes

Every validated anomaly is an immutable tenant-scoped domain entity adhering to the following schema:

| Attribute | Data Type | Nullable | Description |
|---|---|---|---|
| `id` | `VARCHAR(64)` | NO | Unique anomaly identifier. Format: `anm_[a-z0-9]+` (ULID). |
| `tenant_id` | `VARCHAR(64)` | NO | Mandatory tenant ownership (`INV-TEN-001`). Format: `ten_[a-z0-9]+`. |
| `anomaly_type` | `VARCHAR(32)` | NO | Canonical enum: `CANCELLATION`, `REVENUE_AT_RISK`, `FULFILLMENT_DELAY`, `SLA_VIOLATION`, `FAILED_PAYMENT`. |
| `metric_id` | `VARCHAR(32)` | NO | Registered canonical metric (e.g., `METRIC-001`). |
| `metric_version` | `VARCHAR(16)` | NO | Semantic version of metric definition (e.g., `1.0.0`). |
| `detector_id` | `VARCHAR(64)` | NO | Registered detector identifier (e.g., `DET-STL-RESIDUAL-001`). |
| `detector_version` | `VARCHAR(16)` | NO | Version of detection algorithm/configuration. |
| `baseline_id` | `VARCHAR(64)` | NO | Baseline method identifier (e.g., `BASE-SEASONAL-NAIVE-001`). |
| `baseline_version` | `VARCHAR(16)` | NO | Version of baseline definition. |
| `observation_window_start` | `TIMESTAMPTZ` | NO | Start of time window exhibiting anomaly (UTC). |
| `observation_window_end` | `TIMESTAMPTZ` | NO | End of time window exhibiting anomaly (UTC). |
| `comparison_window_start` | `TIMESTAMPTZ` | NO | Start of historical baseline training window (UTC). |
| `comparison_window_end` | `TIMESTAMPTZ` | NO | End of historical baseline training window (UTC). |
| `event_time` | `TIMESTAMPTZ` | NO | Representative timestamp of the anomalous observation (UTC). |
| `effective_from` | `TIMESTAMPTZ` | NO | Watermark from which this anomaly is valid (UTC). |
| `effective_to` | `TIMESTAMPTZ` | YES | Expiration watermark if superseded (NULL = current). |
| `as_of_time` | `TIMESTAMPTZ` | NO | Cut-off timestamp used during detection query (anti-leakage). |
| `ingested_at` | `TIMESTAMPTZ` | NO | Platform persistence timestamp (UTC). |
| `actual_value` | `NUMERIC(18,4)` | NO | Observed metric value during observation window. |
| `expected_value` | `NUMERIC(18,4)` | NO | Point estimate predicted by baseline model. |
| `expected_interval_lower` | `NUMERIC(18,4)` | NO | Lower bound of baseline prediction interval (e.g., 95% CI). |
| `expected_interval_upper` | `NUMERIC(18,4)` | NO | Upper bound of baseline prediction interval (e.g., 95% CI). |
| `anomaly_score` | `NUMERIC(6,4)` | NO | Standardized anomaly severity score (`0.0000` to `1.0000`). |
| `severity` | `VARCHAR(16)` | NO | Canonical enum: `CRITICAL`, `MAJOR`, `MINOR`, `INFORMATIONAL`. |
| `affected_scope` | `JSONB` | NO | Slice filter key-values: `{"warehouse_id": "WH-01", "carrier_id": "CARRIER-A"}`. |
| `data_freshness` | `VARCHAR(32)` | NO | Freshness state: `FRESH`, `STALE_WITHIN_SLA`, `DEGRADED`. |
| `data_quality_state` | `VARCHAR(32)` | NO | Quality state: `PASSED`, `WARNING_IMPUTED`. |
| `confidence` | `NUMERIC(5,4)` | NO | Statistical confidence in anomaly existence (`0.0000` to `1.0000`). |
| `supporting_evidence_refs` | `JSONB` | NO | Array of canonical table record pointers: `[{"entity": "orders", "count": 482}]`. |
| `status` | `VARCHAR(32)` | NO | Lifecycle state: `DETECTED`, `VALIDATED`, `LOCALIZED`, `ACKNOWLEDGED`, `SUPPRESSED`, `RESOLVED`, `REOPENED`. |
| `reproducibility_hash` | `VARCHAR(64)` | NO | SHA-256 digest of input parameters, detector config, and data snapshot. |
| `created_at` | `TIMESTAMPTZ` | NO | Record creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | NO | Record update timestamp. |

---

## 3. Canonical Anomaly Types Catalog

Aligning strictly with PRD §Product Boundaries and canonical metrics:

### 3.1. Cancellation Anomaly (`CANCELLATION`)
- **Metric Reference**: `METRIC-001` (`cancellation_rate`)
- **Trigger**: Observed cancellation rate exceeds `expected_interval_upper` by >= 3 standard deviations for >= 2 consecutive time grains.
- **Representative Scope**: Carrier, origin warehouse, delivery region, customer segment.
- **Example Scenario**: Midwest truck capacity shortage leading to cancellation spike from 1.8% to 8.4%.

### 3.2. Revenue-at-Risk Anomaly (`REVENUE_AT_RISK`)
- **Metric Reference**: `METRIC-002` (`revenue_at_risk`)
- **Trigger**: Sum of exposed delayed order value breaches predefined tenant statistical threshold (e.g., > 2.5x 30-day trailing median).
- **Representative Scope**: High-value accounts (`TIER_1_PLATINUM`), affected warehouse facility.

### 3.3. Fulfillment Delay Anomaly (`FULFILLMENT_DELAY`)
- **Metric Reference**: `METRIC-003` (`fulfillment_delay_rate`)
- **Trigger**: Dispatch or delivery delay rate spikes above 95th percentile baseline.
- **Representative Scope**: Carrier ID, shipping service level, origin facility.

### 3.4. SLA Violation Anomaly (`SLA_VIOLATION`)
- **Metric Reference**: `METRIC-004` (`sla_violation_rate`)
- **Trigger**: Contractual SLA delivery breach rate exceeds contract penalty threshold.
- **Representative Scope**: Enterprise customer ID, contract ID, carrier service.

### 3.5. Failed Payment Anomaly (`FAILED_PAYMENT`)
- **Metric Reference**: `METRIC-005` (`payment_failure_rate`)
- **Trigger**: Authorization/capture failure rate exceeds 3x trailing 7-day hourly baseline.
- **Representative Scope**: Payment gateway provider, currency, card issuer country.

---

## 4. Anomaly Lifecycle State Machine

An anomaly progresses through a deterministic, auditable state machine:

```text
       ┌──────────────┐
       │   DETECTED   │
       └──────┬───────┘
              │ validate_data_quality()
              ▼
       ┌──────────────┐
       │  VALIDATED   │ ──────────────┐
       └──────┬───────┘               │
              │ localize_dimensions() │
              ▼                       │
       ┌──────────────┐               │
       │  LOCALIZED   │               │
       └──────┬───────┘               │
              │ acknowledge()         │ suppress()
              ▼                       │
       ┌──────────────┐               │
       │ ACKNOWLEDGED │               │
       └──────┬───────┘               │
              │ resolve()             │
              ▼                       ▼
       ┌──────────────┐       ┌──────────────┐
       │   RESOLVED   │       │  SUPPRESSED  │
       └──────┬───────┘       └──────────────┘
              │ reopen()
              ▼
       ┌──────────────┐
       │   REOPENED   │
       └──────────────┘
```

### 4.1. Transition Table and Invariants

| From State | To State | Trigger / Action | Actor | Precondition | Audit Event |
|---|---|---|---|---|---|
| `INITIAL` | `DETECTED` | Scheduled detector run | `DetectorWorker` | Metric divergence exceeds threshold | `anomaly.detected.v1` |
| `DETECTED` | `VALIDATED` | DQ check passed | `ValidationService` | Data quality `PASSED`, freshness acceptable | `anomaly.validated.v1` |
| `VALIDATED` | `LOCALIZED` | Dimensional drill-down | `LocalizationWorker`| Top contributing segments isolated | `anomaly.localized.v1` |
| `VALIDATED`/`LOCALIZED`| `SUPPRESSED` | Noise filter or user rule | `Operator` / Rule | Known maintenance or volume threshold below min | `anomaly.suppressed.v1` |
| `LOCALIZED` | `ACKNOWLEDGED`| User / Workflow open | `Analyst` / Temporal | User views or Investigation workflow opens | `anomaly.acknowledged.v1` |
| `ACKNOWLEDGED`| `RESOLVED` | Incident subsided | `Detector` / User | Metric returns within expected interval | `anomaly.resolved.v1` |
| `RESOLVED` | `REOPENED` | Metric re-diverges | `DetectorWorker` | Recurrence within 48h of resolution | `anomaly.reopened.v1` |

---

## 5. Confidence, Severity, and Calibration Semantics

1. **Standardized Severity Scoring**:
   - `CRITICAL`: Anomaly score >= 0.85 OR actual value > 4-sigma divergence OR revenue at risk > $100,000 USD.
   - `MAJOR`: Anomaly score 0.65 to 0.84 OR 3 to 4-sigma divergence.
   - `MINOR`: Anomaly score 0.40 to 0.64 OR 2 to 3-sigma divergence.
   - `INFORMATIONAL`: Score < 0.40; tracking purpose only.
2. **Empirical Calibration**: Anomaly confidence represents the empirical non-parametric tail probability $1 - p$ under the baseline distribution, NOT a model subjective certainty.
3. **Reproducibility Input Digest**: Every anomaly record calculates `reproducibility_hash = sha256(tenant_id + metric_id + metric_version + detector_id + detector_version + observation_window_start + as_of_time + config_json)`.
