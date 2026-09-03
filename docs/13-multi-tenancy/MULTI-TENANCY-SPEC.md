# Multi-Tenancy Contract

Status: Proposed v0.1 — E03 specification output

`TenantId` is an opaque immutable identifier. `TenantContext` is server-created from authenticated membership and contains tenant, isolation tier, authorization reference, correlation metadata and expiry; it cannot be null, client supplied or model supplied. Every tenant-owned repository, cache key, object prefix, event/outbox/inbox record, retrieval filter, workflow input, connector reference, audit event, export and telemetry access requires this context.

Shared tier uses PostgreSQL `tenant_id`, composite tenant-scoped constraints and RLS. Connections set context transactionally and clear it on release. Enterprise/Regulated tiers follow ADR-0005 promotion triggers; tier migration needs approved compatibility, validation, rollback and audit plan. Platform operations use a distinct time-bound audited privileged context. Provisioning creates isolation resources and quotas before activation; suspension/deletion/export propagates to all stores and projections.

Missing, malformed, expired or mismatched context fails closed. Required negative tests cover A/B reads, writes, cache, event, retrieval, object, connectors, logs, backup/export and workers. Traceability: `INV-TEN-001..003`, `NFR-TEN-001..002`, ADR-0005.
