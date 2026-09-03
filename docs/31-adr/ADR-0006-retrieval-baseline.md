# ADR-0006 — Retrieval Baseline

Status: Accepted  
Date: 2026-09-03  
Owner: AI/Data Architecture  
Approver: Dương Vinh

## Context

MVP needs lexical and dense retrieval, metadata/tenant/effective-date filtering, reranking, evidence attribution, and citation verification. Initial-commercial assumption is 10M chunks; separate search systems would increase synchronization and tenant-policy surfaces before benchmarks prove need.

## Decision

Use PostgreSQL full-text search plus pgvector behind a RevPilot `RetrievalPort` for MVP and initial pilots. Retrieve lexical and vector candidates independently, fuse deterministically, apply mandatory tenant/ACL/effective-date filters in data access, optionally rerank, and return immutable Evidence references. Keep Qdrant and OpenSearch as separately evaluated future projections.

## Decision Drivers

Small operational footprint, transactional metadata proximity, hybrid baseline, tenant enforcement, rebuildability, `FR-EVD-001..003`.

## Alternatives

- Qdrant now: strong vector features but another synchronized isolation/operations surface.
- OpenSearch now: strong lexical/search features but unnecessary cluster cost for current evidence.
- Qdrant + OpenSearch now: rejected as premature dual infrastructure.

## Why Selected

It provides a benchmarkable hybrid baseline without preventing future dedicated indexes through the RetrievalPort.

## Pros

Simpler consistency/backup/local development, shared tenant policy, fewer failure modes.

## Cons

Vector/search load may interfere with OLTP; advanced search/vector features may be limited; large corpus scaling requires evidence.

## Consequences

Index builds are versioned/rebuildable. PostgreSQL authority does not remove post-retrieval authorization/citation checks. Retrieval benchmarks must include ACL/effective-date and tenant-negative cases.

## Risks

OLTP degradation or poor relevance. Mitigate with query budgets, replicas/separation triggers, benchmark gates.

## Security Impact

Every query includes trusted Tenant scope and policy filters; returned candidates are revalidated before model context.

## Tenancy Impact

Shared indexes use Tenant-aware keys/filters; dedicated vector partitions/stores follow ADR-0005 triggers.

## Operational Impact

Monitor per-stage p50/p95, candidate counts, recall, index lag, PostgreSQL CPU/I/O, and tenant contribution.

## Cost Impact

Avoids two clusters initially; future migration/reindex cost is accepted and planned via immutable index manifests.

## Implementation Implications

No provider-specific types escape retrieval infrastructure. Fusion/reranking algorithms and limits are versioned in RAG spec.

## Revisit Triggers

Evaluate Qdrant when corpus exceeds the validated PostgreSQL vector baseline (initial planning threshold 10M total chunks or 20M for one isolated tenant), vector p95 exceeds the accepted target for three 7-day windows after tuning, or required vector filtering/sharding cannot be met. Evaluate OpenSearch when lexical p95/recall/highlighting/language analysis fails release targets for three benchmark/release cycles or faceting/large-scale text search becomes mandatory. Separate retrieval workload if it consumes >30% PostgreSQL CPU/I/O and causes OLTP SLO breach. Adoption requires operational owner and migration benchmark.

## Affected Requirements

`FR-EVD-001..003`, `FR-RCA-001`, `SEC-001`, `SEC-004`, `AC-005`.

## Affected Specs

RAG, data architecture, multi-tenancy, evaluation, database, observability.
