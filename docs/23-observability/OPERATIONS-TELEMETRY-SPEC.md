# Operations Telemetry, SLO, and Alerting Specification

Status: Accepted
Initiative: REVPILOT
Phase: Phase 08 — Production Readiness, Release Governance & Operational Evidence
Owner Role: SRE Lead & Observability Engineer
Approver: Dương Vinh
Last Reviewed Date: 2026-09-03
Traceability: `NFR-OBS-001..002`, `NFR-AVL-001`, `NFR-PRV-001`, `INV-SEC-001`, `INV-REL-001`, `INV-TEN-001..003`, `ADR-0010`

---

## 1. Purpose
Defines the operational observability architecture, Service Level Indicators (SLIs), Service Level Objectives (SLOs), error budgets, alert severity classifications, paging policies, and tenant-safe telemetry boundaries for RevPilot AI.

## 2. Scope
Covers all production runtime telemetry (metrics, distributed traces, structured operational logs) emitted by API services, background workers, Temporal workflows, database connection pools, agent execution nodes, and connector ingestion pipelines.

## 3. Non-Goals
- Replacing immutable compliance audit logging (`docs/22-billing/AUDIT-LOG-SPEC.md`).
- Storing unredacted user payloads, prompt contents, or customer PII in telemetry stores.
- Generating uncalibrated alert noise for benign transient retries.

## 4. Normative Requirements
1. Every SLI must be calculated from raw telemetry counters or histograms over sliding time windows.
2. Production SLO values below are design targets only — not yet measured.
3. Telemetry labels must be strictly cardinality-bounded.
4. Alerts must route to distinct on-call tiers based on severity.
5. All logs and traces must scrub credentials and customer PII before export.

## 5. Architectural Invariants
- `NFR-OBS-001`: 100% of requests and investigations carry trace, correlation, causation, and artifact version references.
- `NFR-OBS-002`: Security, authorization, and action events are sampled at 100% (zero sampling drop).
- `NFR-PRV-001`: Zero credentials, tokens, or PII in operational logs or traces.
- `INV-TEN-001`: Telemetry dashboards and queries must support tenant-partitioned filtering without cross-tenant aggregation leaks.

## 6. Interfaces and Contracts
- OpenTelemetry Collector: OTLP/gRPC on port 4317.
- Metric Exporter: Prometheus standard pull endpoint `/metrics`.
- Tracing Exporter: W3C TraceContext headers (`traceparent`, `tracestate`).
- Log Formatter: Structured JSON with mandatory standard correlation envelope.

---

## 7. Service Level Objectives (SLOs) and Error Budgets

> [!IMPORTANT]
> Design targets only — not yet measured in production. Targets will be calibrated upon completion of Phase 08 soak and load testing.

| Service / Capability | Service Level Indicator (SLI) | SLO Target (30-Day Window) | Error Budget (30-Day) | Measurement Methodology | Dashboard Owner |
|---|---|---|---|---|---|
| **API Availability** | Successful HTTP responses (non-5xx) / Total requests | $\ge 99.0\%$ | 7.2 hours downtime | `sum(rate(http_requests_total{status!~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | API Gateway Team |
| **API Latency (Read)** | P95 latency of GET endpoints | $\le 800\text{ms}$ | 5% tail budget | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{method="GET"}[5m])) by (le))` | Platform SRE Team |
| **API Latency (Mutate)** | P95 latency of POST/PUT/DELETE endpoints | $\le 1500\text{ms}$ | 5% tail budget | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{method!="GET"}[5m])) by (le))` | Platform SRE Team |
| **Workflow Execution** | Successful workflow completions without unhandled crash | $\ge 99.5\%$ | 0.5% failure | `sum(rate(temporal_workflow_completed_total[1h])) / sum(rate(temporal_workflow_started_total[1h]))` | Workflow Team |
| **Connector Sync Success**| Scheduled sync runs completed without AUTH_EXPIRED or FATAL | $\ge 98.0\%$ | 2.0% failure | `sum(rate(connector_sync_success_total[1h])) / sum(rate(connector_sync_runs_total[1h]))` | Integrations Team |
| **Webhook Ingestion Delay**| Time from external webhook delivery to transactional inbox | $\le 2000\text{ms}$ (P99) | 1% tail budget | `histogram_quantile(0.99, sum(rate(connector_webhook_delay_seconds_bucket[5m])) by (le))` | Integrations Team |
| **AI Inference Latency** | Model invocation roundtrip latency (P90) | $\le 8.0\text{s}$ | 10% tail budget | `histogram_quantile(0.90, sum(rate(ai_inference_duration_seconds_bucket[15m])) by (le))` | AI Platform Team |
| **Evidence Freshness** | Lag between primary source event and search projection | $\le 15\text{min}$ (P95) | 5% tail budget | `histogram_quantile(0.95, sum(rate(evidence_projection_lag_seconds_bucket[15m])) by (le))` | Data Platform Team |
| **Audit Delivery Integrity**| Audit events successfully written to hash chain | $= 100.0\%$ | 0 events lost | `sum(rate(audit_events_dropped_total[1h])) == 0` | Security SRE Team |
| **Tenant Isolation Breaches**| Unsanctioned cross-tenant data access attempts | $= 0$ events | 0 tolerance | `sum(rate(database_rls_violations_total[1m])) == 0` | SecOps Team |

---

## 8. Alert Severity Classification and Paging Policy

| Severity | Definition | Response SLA | Paging Policy | Notification Channel | Escalation Target |
|---|---|---|---|---|---|
| **P0 (Emergency)** | Critical customer outage, data isolation breach, kill-switch failure, audit pipeline failure | $< 15\text{min}$ | 24/7 Phone / PagerDuty wake-up | Primary SRE On-Call + SecOps On-Call | Head of Engineering + SRE Lead |
| **P1 (Critical)** | Core capability degraded ($\ge 5\%$ error budget burn), connector platform stalled, major IdP outage | $< 30\text{min}$ | PagerDuty on-call alert | SRE On-Call + Owning Subsystem Lead | Principal Architect |
| **P2 (Major)** | Non-blocking service degradation, elevated retry rate, quota synchronization lag, single-tenant issue | $< 2\text{hours}$ | Business hours email + Slack | Slack `#alerts-p2` + Domain Team Lead | Engineering Manager |
| **P3 (Minor)** | Low-priority warning, minor schema drift quarantined, non-urgent provider discrepancy | $< 24\text{hours}$ | Ticket generated in Jira/Linear | Slack `#alerts-p3` + Daily Standup | Domain On-Call |
| **P4 (Informational)**| Routine operational event (tenant provisioned, secret rotated, DR drill completed) | No action | Logged to telemetry sink | Slack `#ops-activity` | None |

---

## 9. Cardinality Controls and Sensitive Data Redaction

### 9.1 Cardinality Protection Rules
To prevent metric explosion and runaway telemetry storage costs:
1. **Allowed Dimensions**: `tenant_id` (low cardinality pilot), `service_name`, `status_code`, `method`, `endpoint_template` (e.g. `/api/v1/tenants/:id`), `error_code`.
2. **Prohibited Dimensions**: User IDs, correlation IDs, email addresses, resource names, raw prompt texts, or dynamic SQL queries.
3. **Metric Relabeling**: High-cardinality attributes in spans are stripped before histogram metric extraction.

### 9.2 PII and Credential Scrubbing Pipeline
- An OpenTelemetry Collector transform processor parses all span attributes and log bodies against credential patterns:
  - Regex `(?i)(bearer\s+[a-z0-9\-\._~\+\/]+=*)` $\to$ `[REDACTED_BEARER_TOKEN]`
  - Regex `(?i)(password|secret|api_key|token)[\"']?\s*[:=]\s*[\"']?([^\"'\s]+)` $\to$ `$1: [REDACTED]`
  - Regex `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b` $\to$ `[REDACTED_EMAIL]`

---

## 10. Alert Fatigue Controls
1. **Hysteresis and Flap Damping**: Alerts must remain in breaching state for $\ge 3$ consecutive evaluation periods before firing.
2. **Inhibition Rules**: High-level alerts suppress child alerts (e.g. `PostgreSqlDown` suppresses `QueryTimeout` alerts).
3. **Weekly Alert Audit**: SRE team reviews any alert that fires $> 10$ times/week without an incident ticket; misconfigured alerts are recalibrated or removed.

## 11. Acceptance Criteria
1. `AC-TEL-01`: 100% of production SLIs are defined with PromQL/log metric formulas and mapped to owning dashboards.
2. `AC-TEL-02`: PII scrubbing processor demonstrated to redact 100% of injected test credentials and emails.
