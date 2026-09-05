# ADR-0004 — Primary Relational Persistence

Status: Accepted  
Date: 2026-09-03  
Owner: Data Architecture  
Approver: Dương Vinh
Version: v1.0

## Context

Tenant, investigation, approval, action, usage, and configuration aggregates require transactions, constraints, joins, migrations, RLS, and outbox consistency.

## Decision

Use PostgreSQL as the authoritative transactional store for RevPilot-owned aggregates and the transactional outbox. Derived retrieval indexes, object payloads, caches, model artifacts, and external systems remain separate and rebuildable/referenced.

## Decision Drivers

Relational integrity, transactions, RLS, mature operations, extension path for FTS/pgvector, outbox atomicity.

## Alternatives

- MySQL: viable but offers no compelling project-specific advantage over PostgreSQL/RLS baseline.
- Document-store-first: rejected because core aggregates and approval/action integrity are relational.
- Database-per-module from day one: rejected because current scale/ownership does not justify distributed transactions.

## Why Selected

It supports current correctness and tenancy requirements with the smallest operational footprint.

## Pros

Strong constraints/transactions, SQL analytics, RLS, backup ecosystem, consistent outbox.

## Cons

OLTP/analytics/vector contention must be measured; vertical scaling has limits; extensions add operational coupling.

## Consequences

Each table has one owning module. Cross-module reads use ports/projections. Migrations use expand/contract. Derived stores never grant authority absent PostgreSQL-owned policy context.

## Risks

Noisy workloads and connection exhaustion. Mitigate with pools, workload separation, query budgets, replicas/partitioning triggers.

## Security Impact

Least-privilege roles, TLS, encryption, RLS, audit, safe query interfaces, and backup access controls are mandatory.

## Tenancy Impact

Shared tier uses Tenant-scoped keys and RLS; dedicated tiers follow ADR-0005.

## Operational Impact

Requires migration, backup/restore, PITR, vacuum/index/connection monitoring, and tested recovery.

## Cost Impact

One managed relational platform minimizes early cost; dedicated/read workloads add cost on trigger.

## Implementation Implications

Use UUID/ordered opaque IDs per detailed schema, UTC timestamps, explicit currency, migration versioning, and transactionally written outbox events.

## Revisit Triggers

Add replicas/partitioning or workload stores when validated load at 120% target breaches accepted p95/availability for three windows after query/index tuning; vector/analytics workload consumes >30% database CPU/I/O and degrades OLTP SLO; tenant contract requires dedicated restore/key/region; or database size/maintenance exceeds validated operational envelope.

## Affected Requirements

`FR-DET-001..003`, `FR-CTL-001..003`, `FR-ACT-002..004`, `SEC-001`, `NFR-REL-001`.

## Affected Specs

Database schema, multi-tenancy, data architecture, event contracts, DR.
