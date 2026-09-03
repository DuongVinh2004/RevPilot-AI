# Documentation map and governance

Status: Foundation and E02–E04 specification pack v0.4 — ADR authority review recorded; E05 blocked; Rail 0 remains RED.

## Reading order

1. `00-executive/EXECUTIVE-VISION.md`
2. `01-product/PRD.md`
3. `02-domain/BUSINESS-DOMAIN-MODEL.md`
4. `03-requirements/SRS.md`
5. `04-system-architecture/SYSTEM-ARCHITECTURE.md`
6. `15-security/THREAT-MODEL.md`
7. `execution/MASTER-ROADMAP.md`
8. `execution/DEPENDENCY-GRAPH.md`
9. `execution/TRACEABILITY-MATRIX.md`
10. `execution/MICRO-TASK-RAIL-SYSTEM.md`
11. `execution/EXECUTOR-QUEUE.md`
12. `00-executive/GLOSSARY.md`
13. `00-executive/SPECIFICATION-PRECEDENCE.md`
14. `03-requirements/WORKLOAD-ASSUMPTIONS.md`
15. `03-requirements/INVARIANT-REGISTRY.md`
16. `03-requirements/NFR-BASELINE.md`
17. `04-system-architecture/SYSTEM-BOUNDARIES.md`
18. `04-system-architecture/REPOSITORY-TOPOLOGY.md`
19. `04-system-architecture/MODULE-BOUNDARIES.md`
20. `04-system-architecture/DEPENDENCY-RULES.md`
21. `31-adr/ADR-0001-application-architecture.md` through `ADR-0011-ai-provider-abstraction.md`

## Planned specification tree

The canonical tree is `docs/00-executive` through `docs/31-adr`, plus `execution/` and `tasks/PHASE-00` onward. A document is not considered complete merely because its path exists. Document status is one of `Proposed`, `Accepted`, `Superseded`, or `Deferred`; accepted documents include owner, approver, version, and last-reviewed date. All 11 ADRs were individually accepted by Dương Vinh on 2026-09-03; this does not make Rail 0 GREEN.

| Area | Canonical deliverable | Foundation status |
|---|---|---|
| Executive | `00-executive/EXECUTIVE-VISION.md` | Proposed v0.1 |
| Product | `01-product/PRD.md` | Proposed v0.1 |
| Domain | `02-domain/BUSINESS-DOMAIN-MODEL.md` | Proposed v0.1 |
| Requirements | `03-requirements/SRS.md` | Proposed v0.1 |
| System architecture | `04-system-architecture/SYSTEM-ARCHITECTURE.md` | Proposed v0.1 |
| AI through deployment | `05-ai-architecture` … `30-deployment` | Planned by roadmap |
| Foundation decisions | `31-adr/ADR-0001` … `ADR-0011` | Accepted individually on 2026-09-03; see authority review |
| Execution | `execution/*` | Foundation files present |
| Agent tasks | `tasks/PHASE-*` | Created phase-by-phase after specifications are accepted |

## Canonical ID namespaces

- Business outcomes: `BR-###`.
- Functional requirements: `FR-<DOMAIN>-###`.
- Non-functional requirements: `NFR-<QUALITY>-###`.
- Security invariants: `SEC-###`.
- Architecture decisions: `ADR-####`.
- APIs and events: `API-###`, `EVT-###`.
- Acceptance criteria and tests: `AC-###`, `TEST-###`.
- Planning objects retain their declared IDs. New executable implementation micro-tasks use stable domain IDs such as `TEN-001`, `IAM-001`, `RAG-001`, `WF-001`, `AGT-001`, `ML-001`, `CAUSAL-001`, `ACT-001`, `CONN-001`, `FIN-001`, `BILL-001`, `OBS-001`, and `SRE-001`. Specification micro-tasks use `SPEC-<DOMAIN>-###`. IDs are globally unique in their object type and never reused.

IDs are immutable. Removed items are marked superseded; IDs are never reused.

## Change rules

- Architectural behavior changes require an ADR and updates to the traceability matrix.
- Security, tenancy, money movement, action semantics, or audit changes require explicit owner review.
- No document may claim SOC 2, ISO 27001, GDPR, or other certification; it may only describe readiness controls.
- Benchmark documents separate target values from measured values. Unknown values remain `TBD`; fabricated results are prohibited.
- AI reasoning traces expose evidence, decisions, tool outcomes, confidence, and policy results—not hidden chain-of-thought.
- Only micro-tasks with `NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0` and readiness score at least 18/20 may enter the executor queue; critical tenant/security/financial/action work requires 20/20.
