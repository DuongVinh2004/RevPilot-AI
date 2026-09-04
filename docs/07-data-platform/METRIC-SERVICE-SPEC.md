# Metric Service Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 02 — Detection and Analytics
Owner: Data Platform Architecture + Analytics Architecture
Traceability: `BR-001`, `FR-DET-001`, `FR-DET-004`, `INV-TEN-001..003`, `INV-DATA-001..002`, `NFR-TEN-001`, `NFR-AI-004`, `AC-002`

---

## 1. Principles and Architectural Invariants

The Metric Service (`revpilot.modules.analytics.metric_service`) is the authoritative query gateway for evaluating business metrics.

### Mandatory Invariants
1. **Canonical Data Exclusivity (`INV-DATA-002`)**: The Metric Service queries only authoritative `canonical.*` tables and governed rollup views. It NEVER queries raw landing tables, unvalidated staging, or external un-ingested systems.
2. **Server-Derived Tenant Context (`INV-TEN-001`, `INV-TEN-002`)**: The service accepts exclusively a cryptographically verified `TenantContext`. All SQL queries inject `tenant_id = :current_tenant_id` and rely on database Row-Level Security. Client header overrides are discarded.
3. **Registry as Sole Semantic Authority**: Metric calculations resolve dynamically from `docs/07-data-platform/METRIC-REGISTRY.md`. Callers cannot supply custom ad-hoc SQL aggregation or modify numerator/denominator semantics.
4. **Strict Temporal As-Of Watermarking (`INV-DATA-001`)**: Every query evaluates relative to an explicit `:as_of_time`. Events with `event_time > :as_of_time` or `ingested_at > :as_of_time` are strictly invisible to prevent lookahead leakage in backtests and investigations.
5. **Air-Gapped from Ground Truth**: The Metric Service has zero read access to `ground_truth.*` schemas.

---

## 2. Metric Query Contract

### 2.1. Request Schema (`MetricQueryRequest`)

```json
{
  "$schema": "https://revpilot.ai/schemas/metric-query-request.v1.json",
  "metric_id": "METRIC-001",
  "metric_version": "1.0.0",
  "time_window": {
    "start_time": "2026-02-01T00:00:00Z",
    "end_time": "2026-02-15T00:00:00Z"
  },
  "grain": "DAILY",
  "group_by_dimensions": ["carrier_id", "warehouse_id"],
  "filters": {
    "origin_region": "US-MIDWEST",
    "customer_tier": "TIER_1_PLATINUM"
  },
  "as_of_time": "2026-02-15T00:00:00Z"
}
```

### 2.2. Response Schema (`MetricQueryResponse`)

```json
{
  "$schema": "https://revpilot.ai/schemas/metric-query-response.v1.json",
  "query_id": "mqy_01h8bcde123456789",
  "metric_id": "METRIC-001",
  "metric_name": "cancellation_rate",
  "metric_version": "1.0.0",
  "tenant_id": "ten_01h7abcde123456789",
  "grain": "DAILY",
  "as_of_time": "2026-02-15T00:00:00Z",
  "freshness_state": "FRESH",
  "data_quality_state": "PASSED",
  "lineage_snapshot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "series": [
    {
      "window_start": "2026-02-14T00:00:00Z",
      "window_end": "2026-02-15T00:00:00Z",
      "dimensions": {
        "carrier_id": "CARRIER_REGIONAL_LOGISTICS",
        "warehouse_id": "WH-MIDWEST-01"
      },
      "actual_value": 0.0842,
      "numerator_value": 42.0,
      "denominator_value": 499.0,
      "sample_size": 499,
      "is_zero_volume_sample": false
    }
  ]
}
```

---

## 3. Data Quality, Freshness, and Corner-Case Handling

1. **Zero Volume / Denominator Zero**:
   - If denominator evaluates to `0`, `actual_value` is set to `0.0`, and `is_zero_volume_sample` is set to `true`. No division-by-zero errors.
2. **Missing / Null Dimension Attributes**:
   - Records with null values in queried dimensions are aggregated under a sentinel category `"UNKNOWN_OR_UNSPECIFIED"`.
3. **Late-Arriving & Out-of-Order Events**:
   - If events arrived after a previously computed rollup, the query engine re-evaluates the slice from canonical base tables if the requested window is within the 7-day volatility buffer.
4. **Duplicate Events**:
   - Handled upstream by `dedup_key` in canonical ingestion; queries perform distinct counting where required by metric contracts (`COUNT(DISTINCT id)`).
5. **Freshness State Evaluation**:
   - `FRESH`: Ingestion latency on source tables is within SLA (< 15 minutes).
   - `STALE_WITHIN_SLA`: Ingestion latency is between 15 and 60 minutes; results flagged with operational notice.
   - `DEGRADED`: Source connector delayed > 60 minutes; results marked `DEGRADED`.

---

## 4. Operational, Security, and Error Contract

### 4.1. Error Matrix

| Error Code | HTTP Status | Trigger Condition | Retryable | Client-Safe Message |
|---|---|---|---:|---|
| `METRIC_NOT_REGISTERED` | 404 | `metric_id` not found in registry | no | Unknown metric identifier |
| `INVALID_DIMENSION_FILTER` | 400 | Dimension requested is not in `allowed_dimensions` | no | Dimension not permitted for this metric |
| `TEMPORAL_LEAKAGE_REJECTED` | 422 | `as_of_time` is in the future relative to server time | no | Future as-of watermark rejected |
| `QUERY_TIMEOUT` | 504 | Aggregation exceeds 10.0s query deadline | yes | Metric computation deadline exceeded |
| `TENANCY_VIOLATION` | 403 | Missing or mismatched tenant token | no | Access denied to tenant metric data |

### 4.2. Observability and Audit Fields
Every execution logs an audit span containing:
- `trace_id`, `correlation_id`
- `tenant_id`
- `metric_id`, `metric_version`
- `duration_ms`
- `rows_scanned`, `series_count`
- `freshness_state`
