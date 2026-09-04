# SQL Capability Catalog and Read-Only Policy

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 03 — Governed Evidence and Investigation (Rails 6, 10)
Owner: Data Platform Architecture / Analytics Architecture
Traceability: `FR-INV-004`, `FR-CTL-001`, `INV-TEN-001..003`, `INV-IAM-001`, `INV-DATA-001..002`, `INV-SEC-003`, `INV-PRV-001`, `NFR-AI-004`, `NFR-TEN-001..002`, `AC-004`, `AC-005`, `ADR-0004`, `ADR-0005`

---

## 1. Governance Principles and Architectural Mandate

RevPilot strictly prohibits arbitrary, unconstrained SQL generation by AI agents (`FR-INV-004`). All analytical data access occurs through a pre-registered, versioned **SQL Capability Catalog**.

### 1.1 Non-Negotiable Invariants
1. **Server-Derived Tenant Injection (`INV-TEN-002`)**: Every query enforces tenant isolation via dual protection:
   - Explicit parameterized predicate: `WHERE tenant_id = :tenant_id`
   - Database engine RLS session variable: `SET LOCAL revpilot.current_tenant_id = :tenant_id`
2. **Strict Read-Only Access (`INV-ACT-001`)**: Capabilities execute under the restricted database role `revpilot_app_readonly`. Any DDL or DML (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`) is blocked at both driver and PostgreSQL engine levels.
3. **No Arbitrary Joins (`INV-SEC-003`)**: Only catalog-defined, pre-optimized join paths across canonical tables are permitted. Ad-hoc Cartesian products or arbitrary joins are physically disallowed.
4. **No Hidden Ground Truth Access**: Queries cannot access internal evaluation tables, synthetic ground truth generators, or seed manifests (`incident_ground_truth`, `synthetic_seed_manifest`, hidden causal tags).
5. **No Secret or Raw PII Exposure (`INV-PRV-001`)**: PII columns (customer names, emails, phones, IP addresses) are either omitted from allowed projections or transformed via cryptographic masking/tokenization.

---

## 2. Registered SQL Capability Catalog

### 2.1 Capability Catalog Overview
| Capability ID | Purpose | Canonical Tables | Max Rows | Max Timeout | Required Permission |
|---|---|---|---|---|---|
| `CAP-SQL-DRILLDOWN-DIM` | Drill down metric across allowed dimension | `canonical_orders`, `canonical_order_lines` | 100 | 5,000 ms | `analytics:query` |
| `CAP-SQL-METRIC-TIMESERIES` | Time-bucketed metric series with baseline | `canonical_orders`, `canonical_order_lines` | 500 | 5,000 ms | `analytics:query` |
| `CAP-SQL-SEGMENT-COMPARE` | Compare metric between two segments | `canonical_orders`, `canonical_customers` | 50 | 3,000 ms | `analytics:query` |
| `CAP-SQL-SHIPMENT-DELAY` | Aggregate fulfillment delays by carrier/warehouse | `canonical_shipments` | 100 | 5,000 ms | `analytics:query` |
| `CAP-SQL-TICKET-VOLUME` | Aggregate ticket counts by category/issue type | `canonical_tickets` | 100 | 5,000 ms | `analytics:query` |
| `CAP-SQL-MAINTENANCE-WINDOW`| Check overlapping maintenance events | `canonical_maintenance_events` | 50 | 3,000 ms | `analytics:query` |
| `CAP-SQL-CONTRACT-SLA` | Retrieve active SLA penalty clauses for account | `canonical_contracts`, `canonical_contract_clauses` | 50 | 3,000 ms | `analytics:query` |

---

## 3. Detailed Capability Specifications

### 3.1 `CAP-SQL-DRILLDOWN-DIM`
- **Metric Binding**: Bound to metrics in `METRIC-REGISTRY.md` (e.g. `order_cancellation_rate`, `gross_revenue`).
- **Allowed Dimensions**: `order_status`, `region`, `tier`, `payment_method`, `fulfillment_channel`.
- **Parameterized Inputs**:
  ```python
  class DrilldownDimParams(BaseModel):
      metric_name: str
      dimension: str
      start_time: UtcDateTime
      end_time: UtcDateTime
      as_of_time: UtcDateTime
      filters: Dict[str, Union[str, List[str]]] = Field(default_factory=dict)
  ```
- **Authorized Template**:
  ```sql
  SELECT 
      :dimension_col AS dimension_value,
      COUNT(o.order_id) AS total_orders,
      SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders,
      ROUND(SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(o.order_id), 0), 4) AS cancellation_rate,
      SUM(o.net_amount) AS total_revenue
  FROM canonical_orders o
  WHERE o.tenant_id = :tenant_id
    AND o.order_placed_at >= :start_time
    AND o.order_placed_at < :end_time
    AND o.order_placed_at <= :as_of_time
  GROUP BY :dimension_col
  ORDER BY total_orders DESC
  LIMIT 100;
  ```
- **Validation & Aliases**:
  - Aliased as `CAP-SQL-DRILLDOWN-DIMENSION` in legacy contracts; canonical ID is `CAP-SQL-DRILLDOWN-DIM`.
  - `:dimension_col` validated against strict whitelist;
  - `:as_of_time` anti-leakage clause enforced;
  - Zero-division guarded via `NULLIF`.

### 3.2 `CAP-SQL-METRIC-TIMESERIES`
- **Metric Binding**: Bound to metrics in `METRIC-REGISTRY.md` across time-series buckets.
- **Allowed Intervals**: `hour`, `day`, `week`, `month`.
- **Authorized Template**:
  ```sql
  SELECT 
      to_char(o.event_time, 'YYYY-MM-DD') AS time_bucket,
      COUNT(o.id) AS total_orders,
      SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders,
      ROUND(SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(o.id), 0), 4) AS cancellation_rate,
      SUM(o.total_cents) / 100.0 AS total_revenue
  FROM canonical_orders o
  WHERE o.tenant_id = :tenant_id
    AND o.event_time >= :start_time
    AND o.event_time < :end_time
    AND o.event_time <= :as_of_time
  GROUP BY time_bucket
  ORDER BY time_bucket ASC
  LIMIT :max_rows;
  ```

### 3.3 `CAP-SQL-SEGMENT-COMPARE`
- **Allowed Segments**: `ENTERPRISE`, `MID_MARKET`, `SMB`.
- **Authorized Template**:
  ```sql
  SELECT 
      c.segment,
      COUNT(o.id) AS total_orders,
      SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders,
      ROUND(SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(o.id), 0), 4) AS cancellation_rate,
      SUM(o.total_cents) / 100.0 AS total_revenue
  FROM canonical_orders o
  JOIN canonical_customers c ON o.tenant_id = c.tenant_id AND o.customer_id = c.id
  WHERE o.tenant_id = :tenant_id
    AND o.event_time >= :start_time
    AND o.event_time < :end_time
    AND o.event_time <= :as_of_time
    AND c.segment IN (:segment_a, :segment_b)
  GROUP BY c.segment
  ORDER BY total_orders DESC
  LIMIT :max_rows;
  ```

### 3.4 `CAP-SQL-SHIPMENT-DELAY`
- **Allowed Columns**: `carrier_code`, `origin_warehouse`, `destination_region`, `delayed_status`, `avg_delay_hours`.
- **Authorized Template**:
  ```sql
  SELECT 
      s.carrier_code,
      s.origin_warehouse,
      COUNT(s.shipment_id) AS total_shipments,
      SUM(CASE WHEN s.actual_delivered_at > s.estimated_delivered_at THEN 1 ELSE 0 END) AS delayed_count,
      ROUND(AVG(EXTRACT(EPOCH FROM (s.actual_delivered_at - s.estimated_delivered_at))/3600), 2) AS avg_delay_hours
  FROM canonical_shipments s
  WHERE s.tenant_id = :tenant_id
    AND s.shipped_at >= :start_time
    AND s.shipped_at < :end_time
    AND s.shipped_at <= :as_of_time
  GROUP BY s.carrier_code, s.origin_warehouse
  ORDER BY delayed_count DESC
  LIMIT 100;
  ```

### 3.5 `CAP-SQL-TICKET-VOLUME`
- **Allowed Columns**: `category`, `priority`, `ticket_count`, `avg_first_response_hours`.
- **Authorized Template**:
  ```sql
  SELECT 
      t.category,
      t.priority,
      COUNT(t.ticket_id) AS ticket_count,
      ROUND(AVG(EXTRACT(EPOCH FROM (t.first_response_at - t.created_at))/3600), 2) AS avg_response_hours
  FROM canonical_tickets t
  WHERE t.tenant_id = :tenant_id
    AND t.created_at >= :start_time
    AND t.created_at < :end_time
    AND t.created_at <= :as_of_time
  GROUP BY t.category, t.priority
  ORDER BY ticket_count DESC
  LIMIT 100;
  ```

### 3.6 `CAP-SQL-MAINTENANCE-WINDOW`
- **Allowed Columns**: `system_component`, `event_type`, `scheduled_start`, `scheduled_end`, `actual_impact_duration_min`.
- **Authorized Template**:
  ```sql
  SELECT 
      m.system_component,
      m.event_type,
      m.scheduled_start,
      m.scheduled_end,
      m.status
  FROM canonical_maintenance_events m
  WHERE m.tenant_id = :tenant_id
    AND m.scheduled_start < :end_time
    AND m.scheduled_end > :start_time
    AND m.scheduled_start <= :as_of_time
  ORDER BY m.scheduled_start ASC
  LIMIT 50;
  ```

### 3.7 `CAP-SQL-CONTRACT-SLA`
- **Allowed Columns**: `contract_id`, `customer_id`, `title`, `contract_type`, `clause_number`, `clause_type`, `sla_threshold_hours`, `penalty_per_hour_cents`.
- **Authorized Template**:
  ```sql
  SELECT 
      c.id AS contract_id,
      c.customer_id,
      c.title,
      c.contract_type,
      cl.clause_number,
      cl.clause_type,
      cl.sla_threshold_hours,
      cl.penalty_per_hour_cents
  FROM canonical_contracts c
  JOIN canonical_contract_clauses cl ON c.tenant_id = cl.tenant_id AND c.id = cl.contract_id
  WHERE c.tenant_id = :tenant_id
    AND c.customer_id = :customer_id
    AND c.effective_from <= :as_of_time
    AND (c.effective_to IS NULL OR c.effective_to >= :as_of_time)
  ORDER BY cl.clause_number ASC
  LIMIT :max_rows;
  ```

---

## 4. Query Execution Engine and Safety Boundaries

1. **Query Digest Generation**: Every executed query produces a deterministic SHA-256 digest:
   ```text
   query_digest = SHA256(canonicalize_sql(template) + ":" + sort_keys_json(params))
   ```
2. **Result Size and Memory Limits**:
   - Max rows returned: 500 rows.
   - Max JSON payload: 500 KB.
   - Exceeding limit truncates result and flags `TRUNCATED_OVER_LIMIT`.
3. **Execution Timeout**: Enforced via PostgreSQL `statement_timeout = '5000ms'`. If timeout occurs, database terminates connection; caller receives `ERR_QUERY_TIMEOUT`.
4. **Provenance Attachment**: Query results are transformed into immutable `EvidenceReference` records containing the `query_digest`, executing role, row count, execution time, and `as_of_time`.

---

## 5. Security and Tenancy Failure Matrix

| Failure Mode / Attack Attempt | Detection Point | System Response | Audit Event |
|---|---|---|---|
| Attempt to query non-catalog table (e.g. `users`, `credentials`) | Capability Router | Block query; return `ERR_UNAUTHORIZED_ENTITY` | `security.unauthorized_entity.attempted` |
| Attempt to project non-whitelisted column (e.g. `card_number`) | Parameter Validator | Reject query; return `ERR_COLUMN_PROHIBITED` | `security.unauthorized_column.attempted` |
| Missing or forged `TenantContext` | Gateway Interceptor | Fail closed; return HTTP 403 `ERR_TENANT_CONTEXT_INVALID` | `identity.tenant.violation_detected` |
| Cross-tenant parameter injection (`:tenant_id` mismatch) | Context Resolver | Discard input parameter; force server-derived tenant | `security.tenant_tamper.detected` |
| Unrestricted SQL generation attempt (e.g. raw text SQL) | Activity Interface | Reject invocation; throw `ERR_UNRESTRICTED_SQL_FORBIDDEN` | `agent.unrestricted_sql.attempted` |
| DDL / DML injection attempt (e.g. `; DROP TABLE ...`) | SQL Parameterizer + DB Role | Engine syntax reject + permission denied | `database.unauthorized_ddl.attempted` |
| Query execution timeout (> 5,000 ms) | DB Engine / Driver | Abort query; return `ERR_QUERY_TIMEOUT` | `analytics.query.timeout` |
| Time leakage attempt (`event_time > :as_of_time`) | Query Validator | Reject query; return `ERR_TEMPORAL_LEAKAGE` | `data.temporal_leakage.attempted` |

---

## 6. Verification and Test Suite Mapping

All controls must be verified by automated tests in `tests/security/` and `tests/analytics/`:
- `test_sql_capability_catalog_allowlist.py`: Validates all 7 registered capabilities accept valid parameters and reject unknown parameters.
- `test_sql_read_only_enforcement.py`: Injects `INSERT`, `UPDATE`, `DELETE`, `DROP` into every capability parameter and verifies rejection.
- `test_sql_tenant_isolation_negative.py`: Executes queries with mismatched tenant contexts and verifies zero rows returned or immediate rejection (`INV-TEN-001`).
- `test_sql_time_travel_anti_leakage.py`: Injects future events and verifies `:as_of_time` filters out future data (`INV-DATA-001`).
- `test_sql_execution_correctness.py`: Compares capability results against known seeded data ground truth; enforces >= 0.95 semantic correctness (`NFR-AI-004`).
