# Observability Specification (Canonical Telemetry and Correlation Contract)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Operational Metrics, Tracing, and Logging (Rails 3–5 Integration)
Owner: SRE + Platform Architecture
Traceability: `NFR-OBS-001`, `NFR-OBS-002`, `NFR-PRV-001`, `INV-SEC-001`, `INV-REL-001`, `ADR-0010`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Observability Baseline and Architecture

RevPilot utilizes OpenTelemetry (OTel) standard APIs and a vendor-neutral Collector boundary for traces, metrics, and structured logs (`ADR-0010`). Operational telemetry is completely separate from immutable compliance audit logs (`docs/22-billing/AUDIT-LOG-SPEC.md`).

### Foundational Invariants
1. `NFR-OBS-001`: 100% of requests and investigations carry trace, correlation, causation, and artifact version references.
2. `NFR-OBS-002`: Security, policy, approval, and action events are sampled at 100% (never discarded by probabilistic sampling).
3. `NFR-PRV-001`: Zero (0) raw credentials or unredacted PII in operational telemetry.
4. `INV-REL-001`: Degraded telemetry systems must not compromise core security controls or bypass isolation.

---

## 2. Standard Context and Correlation Attributes

Every trace span and structured log record across the HTTP API, background workers, database queries, and tool gateway must carry standard attributes:

```text
Attribute Key               Type      Description
-------------------------   -------   -------------------------------------------------
revpilot.tenant_id          string    Opaque Tenant identifier (e.g. ten_01h7...)
revpilot.principal_id       string    Authenticated actor PrincipalId (e.g. usr_..., svc_...)
revpilot.principal_type     string    user, service_account, agent, system
revpilot.correlation_id     string    End-to-end request correlation UUID
revpilot.causation_id       string    ID of immediate parent event / span
revpilot.investigation_id   string    Investigation aggregate ID (when in investigation context)
revpilot.task_id            string    Workflow or subagent task ID
revpilot.delegation_id      string    Active delegation token ID (if agent execution)
revpilot.is_system          boolean   True if executing under platform privileged context
```

---

## 3. Required Control Plane Signals (Rails 3–5)

### 3.1. Authentication Metrics (Rail 3)
- `identity.auth.attempts_total`: Counter by `status` (success, failure), `principal_type`.
- `identity.auth.failures_total`: Counter by `failure_reason` (`expired`, `invalid_signature`, `missing_tenant`, `revoked`).
- `identity.auth.duration_seconds`: Histogram measuring token validation latency.

### 3.2. Authorization Metrics (Rail 4)
- `identity.authz.evaluations_total`: Counter by `decision` (`allow`, `deny`), `resource`, `action`.
- `identity.authz.denials_total`: Counter by `role`, `permission`, `reason`.
- `identity.delegations.active`: Gauge of active, unexpired delegation tokens.
- `identity.break_glass.invocations_total`: Counter of emergency break-glass usages (alert trigger).

### 3.3. Persistence & Isolation Metrics (Rail 5)
- `database.rls.session_set_total`: Counter of successful `SET LOCAL revpilot.current_tenant_id` executions.
- `database.rls.violations_total`: Counter of SQL RLS check violations (P0 alert).
- `database.query.duration_seconds`: Histogram by table and operation type.
- `database.connection_pool.active`: Gauge of checked-out database connections.

---

## 4. Privacy, Masking, and Redaction Rules

1. **Telemetry Redaction Interceptor**: Structured log formatters automatically mask sensitive values matching standard credential patterns (JWT signatures, bearer tokens, passwords, private keys).
2. **Cardinality Bounding**: Telemetry attributes must not include dynamic user-generated content (e.g. email subject lines, file names, raw prompts, SQL queries containing literal values).
3. **Trace Sanitization**: Span names and tags must use static template names (e.g. `GET /api/v1/tenants/{id}` instead of literal ID values).

---

## 5. Phase 07 Operational Signals (Tenancy, Connectors, and Quotas)

### 5.1. Tenant Lifecycle & Quota Metrics
- `tenancy.lifecycle.status_gauge`: Gauge of tenants by state (`ACTIVE`, `SUSPENDED`, `LEGAL_HOLD`, `DELETING`).
- `finops.quota.utilization_ratio`: Gauge of current usage vs limit (0.0 - 1.0) by `tenant_id`, `dimension`.
- `finops.quota.throttled_total`: Counter of 429 rejections by `tenant_id`, `dimension`.
- `finops.spend.reserved_usd`: Gauge of active in-flight spend reservations.

### 5.2. Connector & Ingestion Signals
- `connector.sync.duration_seconds`: Histogram of sync execution times by `provider`, `sync_mode`.
- `connector.sync.lag_seconds`: Gauge of ingestion lag behind upstream source timestamps.
- `connector.status_gauge`: Gauge of connector instances by `provider`, `status` (`ACTIVE`, `AUTH_EXPIRED`, etc.).
- `connector.webhooks.received_total`: Counter by `provider`, `status` (`accepted`, `signature_invalid`, `replayed`).
- `connector.quarantine.records_active`: Gauge of un-reconciled records in `connector_quarantine`.
- `connector.schema_drift.events_total`: Counter by `provider`, `drift_type` (`breaking`, `additive`).

---

## 6. Synthetic Probe and Latency Evaluation Harness

### 6.1. Synthetic Blackbox Probe Endpoints
RevPilot exposes standardized probe endpoints for external blackbox monitoring and synthetic canary probes:
- `GET /healthz`: Shallow liveness probe returning HTTP 200 `{"status": "ok"}` within <= 50ms.
- `GET /api/v1/healthz/deep`: Deep synthetic probe verifying database read connectivity, OTel collector availability, and in-memory authorization cache status.

### 6.2. Prometheus Recording Rules for NFR-LAT-001 (P95 Latency < 500ms)
```yaml
groups:
  - name: revpilot_sli_rules
    rules:
      - record: revpilot:http_request_duration_seconds:p95_15m
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[15m])) by (le, tenant_id))
      - record: revpilot:http_request_duration_seconds:p95_30d
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[30d])) by (le))
```

### 6.3. Multi-Window Error Budget Burn Rate Alerts for NFR-AVL-001 (>= 99.9% Availability)
Based on Google SRE multiwindow multi-burn-rate alerting standards:
- **Critical Alert (1h / 2% budget burn)**: Burn rate > 14.4 over 1 hour window:
  ```promql
  (
    sum(rate(http_requests_total{status=~"5.."}[1h])) 
    / 
    sum(rate(http_requests_total[1h]))
  ) > (14.4 * 0.001)
  ```
- **Warning Alert (6h / 5% budget burn)**: Burn rate > 6.0 over 6 hour window:
  ```promql
  (
    sum(rate(http_requests_total{status=~"5.."}[6h])) 
    / 
    sum(rate(http_requests_total[6h]))
  ) > (6.0 * 0.001)
  ```

