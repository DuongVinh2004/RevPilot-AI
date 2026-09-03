# Database Schema Contract

Status: Proposed v0.1 — E04 specification output

PostgreSQL owns RevPilot transactional aggregates; each table has exactly one module owner. Tenant-owned tables require non-null `tenant_id`, tenant-scoped composite unique/foreign-key constraints, RLS policy and repository method accepting TenantContext. Cross-module access uses ports/projections, not direct tables. Source records and derived projections remain distinct.

Logical schema families are tenancy/identity, investigation/evidence, retrieval metadata, model/eval, decision/policy/approval/actions, connectors/data lineage, outbox/inbox, audit, usage/billing. IDs are opaque, money is decimal plus ISO currency, timestamps are UTC plus business timezone/as-of where relevant. Migrations are expand/contract with compatibility window, backfill verification/recovery and no destructive change without separately authorized recovery plan.

RLS session context is set/cleared transactionally; null/invalid context denies tenant access. Required tests cover composite-key/RLS A/B negatives, migration compatibility and projection reconciliation. Traceability: `INV-TEN-001`, `INV-DATA-001..002`, ADR-0004/0005.
