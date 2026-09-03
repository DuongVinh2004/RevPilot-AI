# Deployment Architecture Contract

Status: Proposed v0.1 — E04 specification output

Baseline packages API, web, workflow, ingestion and ML workers as OCI containers; local development uses composition. Initial commercial target is provider-neutral managed containers with managed PostgreSQL, object storage, identity, secrets and supported Temporal. Provider/environment is UNKNOWN. Kubernetes, service mesh and active-active multi-region are deferred per ADR-0008.

Configuration is validated non-secret schema; secrets use workload identity/managed store and never repository files. Deployment verifies contract compatibility, schema/event migration plan, artifact release eligibility, tenant-safe telemetry, rollback and health/readiness behavior. Rollback preserves forward-written data; stateful changes use expand/contract and reconciliation. Environment promotion does not enable real adapters without separate action authority.

Traceability: ADR-0008/0009, `NFR-AVL-*`, `NFR-REC-001`, `INV-REL-001`.
