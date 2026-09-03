# ADR Authority Review — 2026-09-03

Status: Recorded individual authority review; E05 remains BLOCKED.

Authority: Dương Vinh  
Review basis: specification precedence, invariant registry, workload assumptions, NFR baseline, system/module/dependency boundaries, E02–E04 outputs, and cross-ADR consistency.

## Decisions

| ADR | Title | Current | Recommended | Decision | Contradictions / unknowns | Rail 0 impact |
|---|---|---|---|---|---|---|
| ADR-0001 | Application Architecture | Proposed | Accepted | Modular monolith first; extraction requires measurable triggers. | None; provider remains open. | Does not alone open Rail 0 |
| ADR-0002 | Durable Execution | Proposed | Accepted | Temporal owns durable workflow state; nondeterministic work is in Activities. | None. | Does not alone open Rail 0 |
| ADR-0003 | Agent Orchestration Boundary | Proposed | Accepted | Typed AgentRuntime/LangGraph boundary; no credentials, authority, or side effects. | None. | Does not alone open Rail 0 |
| ADR-0004 | Primary Relational Persistence | Proposed | Accepted | PostgreSQL owns transactional aggregates and outbox; derived stores are rebuildable. | None. | Does not alone open Rail 0 |
| ADR-0005 | Tenant Isolation | Proposed | Accepted | Shared PostgreSQL + RLS baseline with dedicated-tier triggers. | Legal/residency profile remains unknown. | Does not alone open Rail 0 |
| ADR-0006 | Retrieval Baseline | Proposed | Accepted | PostgreSQL FTS + pgvector; Qdrant/OpenSearch require measurable triggers. | None. | Does not alone open Rail 0 |
| ADR-0007 | Messaging/Event Baseline | Proposed | Accepted | Transactional outbox, bounded dispatcher, inbox/dedup, at-least-once delivery. | None. | Does not alone open Rail 0 |
| ADR-0008 | Deployment Baseline | Proposed | Accepted | OCI + managed containers; Kubernetes deferred by trigger. | Commercial provider/environment unknown. | Does not alone open Rail 0 |
| ADR-0009 | Secrets and Keys | Proposed | Accepted | Managed secret service/workload identity; short-lived brokered credentials; agents see references/results only. | Provider/CMEK choice remains open. | Does not alone open Rail 0 |
| ADR-0010 | Observability Baseline | Proposed | Accepted | OpenTelemetry APIs/Collector; audit and operational telemetry remain separate. | Backend/retention profile remains open. | Does not alone open Rail 0 |
| ADR-0011 | AI Provider Abstraction | Proposed | Accepted | RevPilot-owned Model Gateway with provider adapters and schema/cost/data controls. | Production provider and residency terms remain open. | Does not alone open Rail 0 |

## Structural and consistency result

All 11 ADRs contain ID, title, status, date, owner, context, decision, drivers, alternatives, rationale, pros, cons, consequences, risks, security, tenancy, operations, cost, implementation, measurable revisit triggers, requirements, and specification references. Each remains consistent with the accepted precedence rules and E02–E04 contracts. No Architecture Deviation Request is required.

## E05 preflight result

E02, E03 and E04 are `PASS`; all ADR decisions are resolved; all 31 detailed specification outputs exist; and no E05 write-set conflict was found. E05 is nevertheless `BLOCKED` because its acceptance requires exact downstream API/event/test links and a closed P0 traceability matrix, while `execution/TRACEABILITY-MATRIX.md` still contains `TBD`, wildcard, and legacy broad implementation references. E05 also requires a final cross-document reconciliation that must not claim implementation evidence.

The minimum unblock is to define and admit the E05 reconciliation task after the exact traceability closure policy is satisfied. No E05 leaf task was created or executed, and the implementation executor queue remains empty.
