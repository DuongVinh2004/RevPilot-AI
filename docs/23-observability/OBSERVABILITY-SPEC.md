# Observability Contract

Status: Proposed v0.1 — E03 specification output

Use OpenTelemetry APIs and a vendor-neutral Collector boundary. Required correlation fields are opaque tenant ID, principal reference, correlation/causation, investigation/run/workflow/activity/agent/tool/action IDs and relevant artifact versions. Required signals: API, workflow, agent/model, retrieval, data-quality, policy/approval/action, connector, cost and security controls.

Operational logs, metrics and traces are distinct from immutable audit and evaluation records. Prompts, credentials, raw sensitive evidence and chain-of-thought are prohibited by default. Security/policy/approval/action events are unsampled; other sampling cannot sever required lineage. Metrics name bounded labels only and avoid high-cardinality customer content.

Telemetry backend choice is deferred per ADR-0010. Alert owners cover unsafe denial/fail-closed violations, cross-tenant anomaly, audit gap, budget breach, workflow recovery and SLO breach. Traceability: `NFR-OBS-001..002`, `NFR-PRV-001`, ADR-0010.
