# ADR-0005 — Tenant Isolation Baseline and Tiers

Status: Accepted  
Date: 2026-09-03  
Owner: Security Architecture + Data Architecture  
Approver: Dương Vinh

## Context

RevPilot processes commercially sensitive customer, revenue, contract, and action data. One physical deployment may serve multiple tenants, but isolation requirements and economics differ across SMB, Enterprise, and Regulated customers.

## Decision

Baseline SMB isolation uses shared PostgreSQL tables with mandatory `tenant_id`, tenant-scoped composite constraints, server-derived Tenant context, and RLS as the data enforcement layer. Enterprise may use a dedicated database and vector partition. Regulated may use a dedicated database/cluster, encryption key, and region. Isolation applies equally to caches, events, object storage, search/vector, features, model/eval data, Agent memory, logs, analytics, backups, and exports.

## Decision Drivers

`SEC-001`, cost proportionality, defense in depth, restore/residency/key boundaries, controlled migration path.

## Alternatives

- Database-per-tenant for all: strongest simple boundary but rejected as default due provisioning/operations cost.
- Application filters only: rejected because it lacks independent data-layer enforcement.
- Shared schema without composite tenant keys: rejected because references can cross tenants accidentally.

## Why Selected

Tiering provides strong enforceable baseline isolation and a clear escalation path without universal dedicated cost.

## Pros

Efficient baseline, RLS defense, contractual tier flexibility, explicit migration triggers.

## Cons

RLS/context mistakes remain critical; restore/export/deletion are harder in shared storage; tier migration is complex.

## Consequences

Tenant resolution fails closed. Background jobs/workflows/tools carry trusted Tenant context. Platform break-glass paths are separate, audited, time-bound, and never available to Agents.

## Risks

Cross-store leakage and noisy neighbors. Mitigate with isolation matrices, static/runtime checks, per-tenant quotas, and dedicated-tier triggers.

## Security Impact

Cross-tenant access is a Critical-class design failure. Negative tests cover every data/capability surface and backup/export path.

## Tenancy Impact

This ADR defines the three tiers and their migration direction; detailed provisioning/deletion/export semantics live in the tenancy spec.

## Operational Impact

Dedicated tiers increase provisioning, migration, backup, monitoring, and incident complexity.

## Cost Impact

Shared tier amortizes cost; dedicated tiers require entitlement and billing that covers isolated resources.

## Implementation Implications

Tenant context cannot be optional in tenant-owned repositories. Connection/session context must be set and cleared safely. Cache/event/object keys and partitions include trusted Tenant identity.

## Revisit Triggers

Promote a tenant when required by signed residency/key/isolation contract; shared restore/RPO cannot satisfy its contract; its 7-day p95 resource share exceeds 20% of shared capacity or causes two SLO-impacting noisy-neighbor events; corpus/throughput reaches dedicated retrieval thresholds; or risk review requires a separate blast radius. Database/cluster/region promotion requires migration and rollback plans.

## Affected Requirements

`BR-004`, `FR-CTL-001..003`, `FR-EVD-001..003`, `SEC-001..005`, `AC-010`.

## Affected Specs

Multi-tenancy, IAM, database, RAG, data governance, connectors, audit, billing, deployment.
