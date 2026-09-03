# ADR-0007 — Messaging and Event Baseline

Status: Accepted  
Date: 2026-09-03  
Owner: Data/Platform Architecture  
Approver: Dương Vinh

## Context

RevPilot needs reliable domain/integration events, but INITIAL COMMERCIAL assumes 100 events/s sustained with burst to 500 and does not yet require many independent replay consumers. Kafka-first would add a cluster, schema operations, partition choices, and failure modes before they are justified.

## Decision

Use a PostgreSQL transactional outbox written atomically with aggregate changes, a bounded dispatcher, and consumer inbox/deduplication for MVP/initial pilots. Delivery is at-least-once. Ordering is defined only per aggregate key. Consumers are idempotent and use retry classes plus quarantine/dead-letter state. Introduce Kafka only through a superseding ADR after triggers are met.

## Decision Drivers

Transactional consistency, moderate initial throughput, replayability, low operations burden, `FR-DET-003`, `NFR-REL-001`.

## Alternatives

- Kafka-first: capable but rejected as premature infrastructure.
- Managed queue only: useful for work delivery but lacks the chosen transactional event and replay model by itself.
- Direct synchronous fan-out: rejected due coupling and partial failure.

## Why Selected

The outbox provides a deterministic reliable baseline using the existing transactional system while keeping an event envelope compatible with later brokers.

## Pros

Atomic publication intent, simple local operation, clear deduplication, lower cost.

## Cons

Limited throughput/retention/fan-out, database polling/load, custom dispatcher/inbox behavior.

## Consequences

Events use versioned envelopes, Tenant/correlation/causation/idempotency fields, and bounded payloads. Outbox records are not the immutable audit log.

## Risks

Backlog growth, poison events, duplicate delivery, hot aggregate ordering. Mitigate with lag alerts, quarantine, replay tools, partitioned dispatcher, and idempotent consumers.

## Security Impact

Consumers authorize Tenant context independently; event payloads are minimized and do not carry credentials.

## Tenancy Impact

Tenant is mandatory in event/inbox/outbox keys and broker ACL design if Kafka is later adopted.

## Operational Impact

Monitor oldest-unpublished age, dispatch rate/failures, inbox duplicates, quarantine count, and per-tenant backlog.

## Cost Impact

Uses PostgreSQL/worker capacity initially; later broker cost is introduced only with demonstrated value.

## Implementation Implications

Outbox insert shares the domain transaction. Dispatcher retries never replay the business transaction. Compatibility rules precede producer/consumer implementation.

## Revisit Triggers

Evaluate Kafka if any persists after tuning: >100 events/s for 15 minutes on 10 days/month or bursts >500/s create oldest-event lag >60 s; three or more independent consumer groups require replay beyond outbox retention; required replay retention exceeds 7 days; partitioned ordering across high-volume connector streams is mandatory; connector ecosystem requires Kafka-native integration; or database event workload consumes >15% CPU/I/O and affects OLTP SLO. Adoption requires named operations owner, schema governance, tenant ACL, DR, and cost plan.

## Affected Requirements

`FR-DET-003`, `FR-INV-002..003`, `FR-LRN-001`, `FR-CTL-001`, `NFR-REL-001`, `SEC-001`.

## Affected Specs

Event contracts, data architecture, connectors, observability, SRE, database.
