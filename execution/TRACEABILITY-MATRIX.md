# Foundation Traceability Matrix

Status: Accepted v0.3 — E05 reconciliation complete. Every cell references accepted canonical artifacts, exact invariant IDs, exact specification task IDs, exact acceptance criteria IDs, and spec-defined verification categories. No TBD, wildcard, or legacy broad planning ID remains. Implementation micro-task IDs and individual API endpoint/event/test IDs are correctly deferred to Stage B (post-Rail 0 GREEN).

## Top-level business requirement trace

| Business requirement | Functional/security requirement | Component/module | Contract specification | Stage B scope | Verification category | Acceptance |
|---|---|---|---|---|---|---|
| `BR-001` | `FR-DET-001..003`, `FR-INV-001..004` | investigations, analytics, evidence, retrieval (MODULE-BOUNDARIES.md) | `SPEC-WF-001` → TEMPORAL-WORKFLOW-SPEC.md, `SPEC-AI-001` → AI-ARCHITECTURE.md, `SPEC-AGT-001` → MULTI-AGENT-SPEC.md, `SPEC-API-001` → API-STANDARDS.md, `SPEC-EVT-001` → EVENT-CONTRACTS.md | DEFERRED_STAGE_B: Investigation workflow, detector, metric APIs/events/tests. Owning specs: SPEC-WF-001, SPEC-AI-001, SPEC-AGT-001, SPEC-ML-001, SPEC-DAT-001. Phases: 01–03 | `SPEC-QA-001` → TEST-STRATEGY.md §seeded-backtest, §workflow-recovery; `SPEC-EVL-001` → EVALUATION-FRAMEWORK.md §RCA-suite, §agent-suite | `AC-001`, `AC-002`, `AC-003` |
| `BR-002` | `FR-ML-002..004`, `FR-DEC-001`, `FR-LRN-001` | ml, decisions, analytics (MODULE-BOUNDARIES.md) | `SPEC-ML-001` → ML-SYSTEM-SPEC.md, `SPEC-CAU-001` → CAUSAL-INFERENCE-SPEC.md, `SPEC-DEC-001` → DECISION-ENGINE-SPEC.md, `SPEC-EVL-001` → EVALUATION-FRAMEWORK.md, `SPEC-API-001` → API-STANDARDS.md, `SPEC-EVT-001` → EVENT-CONTRACTS.md | DEFERRED_STAGE_B: ML artifact, causal study, decision optimizer APIs/events/tests. Owning specs: SPEC-ML-001, SPEC-CAU-001, SPEC-DEC-001, SPEC-SYN-001. Phases: 04–05 | `SPEC-EVL-001` → EVALUATION-FRAMEWORK.md §calibration-suite, §uplift-suite, §causal-suite; `SPEC-QA-001` → TEST-STRATEGY.md §property-tests | `AC-006`, `AC-007`, `AC-014` |
| `BR-003` | `FR-EVD-001..003`, `FR-RCA-001..002`, `FR-ACT-001..004` | evidence, retrieval, actions, approvals, policy (MODULE-BOUNDARIES.md) | `SPEC-RAG-001` → RAG-SPEC.md, `SPEC-ACT-001` → TOOL-GATEWAY-SPEC.md, `SPEC-SEC-001` → SECURITY-ARCHITECTURE.md, `SPEC-IAM-001` → IAM-SPEC.md, `SPEC-API-001` → API-STANDARDS.md, `SPEC-EVT-001` → EVENT-CONTRACTS.md | DEFERRED_STAGE_B: Evidence, RAG, policy, approval, action gateway APIs/events/tests. Owning specs: SPEC-RAG-001, SPEC-ACT-001, SPEC-SEC-001, SPEC-IAM-001. Phases: 03–06 | `SPEC-EVL-001` → EVALUATION-FRAMEWORK.md §retrieval-suite, §citation-suite; `SPEC-QA-001` → TEST-STRATEGY.md §tamper-replay-suite, §action-idempotency-suite | `AC-004`, `AC-005`, `AC-008`, `AC-009` |
| `BR-004` | `FR-CTL-001..003`, `SEC-001..010` | tenancy, identity, audit, actions, all modules (MODULE-BOUNDARIES.md) | `SPEC-TEN-001` → MULTI-TENANCY-SPEC.md, `SPEC-IAM-001` → IAM-SPEC.md, `SPEC-SEC-001` → SECURITY-ARCHITECTURE.md, `SPEC-ACT-001` → TOOL-GATEWAY-SPEC.md, `SPEC-AUD-001` → AUDIT-LOG-SPEC.md, `SPEC-DB-001` → DATABASE-SCHEMA.md, `SPEC-DG-001` → DATA-GOVERNANCE.md, `SPEC-API-001` → API-STANDARDS.md, `SPEC-EVT-001` → EVENT-CONTRACTS.md | DEFERRED_STAGE_B: Tenant context, IAM, RLS, audit, deletion/export APIs/events/tests. Owning specs: SPEC-TEN-001, SPEC-IAM-001, SPEC-SEC-001, SPEC-DB-001, SPEC-DG-001. Phases: 00 (Rail 0 bootstrap) –07 | `SPEC-QA-001` → TEST-STRATEGY.md §cross-tenant-negative-matrix, §authorization-matrix, §deletion-export-suite; `SPEC-SRE-001` → SRE-SPEC.md §dependency-outage-matrix | `AC-010`, Production DoD |
| `BR-005` | `FR-LRN-001..002`, `NFR-AI-001`, `NFR-COST-001` | ml, usage, billing, audit (MODULE-BOUNDARIES.md) | `SPEC-AIG-001` → AI-GOVERNANCE.md, `SPEC-REL-001` → MODEL-RELEASE-PROCESS.md, `SPEC-FIN-001` → FINOPS-SPEC.md, `SPEC-BIL-001` → BILLING-SPEC.md, `SPEC-OBS-001` → OBSERVABILITY-SPEC.md, `SPEC-API-001` → API-STANDARDS.md, `SPEC-EVT-001` → EVENT-CONTRACTS.md | DEFERRED_STAGE_B: Outcome, governance, release gate, metering APIs/events/tests. Owning specs: SPEC-AIG-001, SPEC-REL-001, SPEC-FIN-001, SPEC-BIL-001. Phases: 06–08 | `SPEC-EVL-001` → EVALUATION-FRAMEWORK.md §release-gate-suite; `SPEC-QA-001` → TEST-STRATEGY.md §metering-reconciliation-suite | `AC-011`, `AC-012` |

## Stage B deferral rule

Implementation micro-task IDs, individual API endpoint IDs (e.g., `POST /api/v1/investigations`), individual event type IDs (e.g., `investigation.created.v1`), and individual test case IDs (e.g., `TEST-TEN-001`) are Stage B artifacts. Stage B is generated only after Rail 0 is GREEN, per `execution/MICRO-TASK-RAIL-SYSTEM.md` §two-stage-generation. This deferral is intentional and bounded: each `DEFERRED_STAGE_B` cell above names the owning canonical specifications and target phases. The deferral is not permission to infer behavior. A CI documentation check at Stage B entry will reject orphan IDs, duplicate/reused IDs, undefined dependencies, cycles, missing reverse links, and task acceptance criteria that do not map to a requirement.

## Traceability closure rule

Before Stage B micro-task generation for any phase, every P0 row in that phase's scope must have: exact accepted contract specification references (column 4 above — DONE), exact Stage B scope declaration with owning specs and target phase (column 5 above — DONE), exact spec-anchored verification categories (column 6 above — DONE), and exact acceptance criteria IDs (column 7 above — DONE). Individual API/event/test IDs are then generated as part of Stage B decomposition and wired into a per-phase traceability extension table.

## Phase 00 E01 foundation trace

| Requirement/invariant family | Canonical architecture/decision artifact | Exact Stage A task | E02–E04 resolution |
|---|---|---|---|
| `BR-001`, `FR-INV-001..004`, `NFR-REL-001` | ADR-0002, ADR-0003, SYSTEM-BOUNDARIES.md, MODULE-BOUNDARIES.md, DEPENDENCY-RULES.md | `SPEC-ADR-002`, `SPEC-ADR-003`, `SPEC-FND-002`, `SPEC-FND-005`, `SPEC-FND-006` | Resolved: `SPEC-WF-001` (workflow), `SPEC-AI-001` (AI arch), `SPEC-AGT-001` (agents) — all PASS |
| `BR-002`, `FR-ML-001..004`, `FR-DEC-001` | WORKLOAD-ASSUMPTIONS.md, NFR-BASELINE.md, ADR-0011 | `SPEC-FND-003`, `SPEC-FND-009`, `SPEC-ADR-011` | Resolved: `SPEC-ML-001` (ML), `SPEC-CAU-001` (causal), `SPEC-DEC-001` (decision) — all PASS |
| `BR-003`, `FR-EVD-001..003`, `FR-RCA-001..002`, `FR-ACT-001..004` | SYSTEM-BOUNDARIES.md, INVARIANT-REGISTRY.md, ADR-0002/0003/0006/0009/0010 | `SPEC-FND-002`, `SPEC-FND-008`, `SPEC-ADR-002`, `SPEC-ADR-003`, `SPEC-ADR-006`, `SPEC-ADR-009`, `SPEC-ADR-010` | Resolved: `SPEC-RAG-001` (RAG), `SPEC-ACT-001` (actions), `SPEC-SEC-001` (security) — all PASS |
| `BR-004`, `FR-CTL-001..003`, `SEC-001..010`, `AC-010` | ADR-0004/0005/0009, REPOSITORY-TOPOLOGY.md, MODULE-BOUNDARIES.md, DEPENDENCY-RULES.md, `INV-TEN-001..003`, `INV-IAM-001..002`, `INV-SEC-001..003` | `SPEC-ADR-004`, `SPEC-ADR-005`, `SPEC-ADR-009`, `SPEC-FND-004`, `SPEC-FND-005`, `SPEC-FND-006`, `SPEC-FND-007`, `SPEC-FND-008` | Resolved: `SPEC-TEN-001` (tenancy), `SPEC-IAM-001` (IAM), `SPEC-SEC-001` (security), `SPEC-DB-001` (database), `SPEC-DG-001` (governance) — all PASS |
| `BR-005`, `FR-LRN-001..002`, `NFR-AI-001`, `NFR-COST-001` | NFR-BASELINE.md, INVARIANT-REGISTRY.md, WORKLOAD-ASSUMPTIONS.md, ADR-0007/0010/0011 | `SPEC-FND-003`, `SPEC-FND-008`, `SPEC-FND-009`, `SPEC-ADR-007`, `SPEC-ADR-010`, `SPEC-ADR-011` | Resolved: `SPEC-AIG-001` (governance), `SPEC-REL-001` (release), `SPEC-FIN-001` (FinOps), `SPEC-BIL-001` (billing) — all PASS |

All E01 downstream blockers are resolved by E02–E04 accepted specification outputs. No E01 trace terminates in an implementation micro-task; that absence is correct while `execution/EXECUTOR-QUEUE.md` is empty.

## Stage A E02–E04 contract closure

| Requirement/invariant family | Canonical specification outputs | Exact Stage A tasks | Spec-defined verification category |
|---|---|---|---|
| `INV-AI-001`, `INV-AI-002`, `NFR-AI-001`, `NFR-AI-002`, `NFR-AI-003`, `NFR-AI-004`, `NFR-AI-005`, `NFR-AI-006`, `NFR-AI-007` | AI-ARCHITECTURE.md, MULTI-AGENT-SPEC.md, ML-SYSTEM-SPEC.md, RAG-SPEC.md, CAUSAL-INFERENCE-SPEC.md, DECISION-ENGINE-SPEC.md, AI-GOVERNANCE.md, EVALUATION-FRAMEWORK.md, MODEL-RELEASE-PROCESS.md | `SPEC-AI-001`, `SPEC-AGT-001`, `SPEC-ML-001`, `SPEC-RAG-001`, `SPEC-CAU-001`, `SPEC-DEC-001`, `SPEC-AIG-001`, `SPEC-EVL-001`, `SPEC-REL-001` | SPEC-EVL-001 §artifact-manifest-test, SPEC-ML-001 §leakage-gate, SPEC-RAG-001 §retrieval-eval, SPEC-EVL-001 §RCA-benchmark, SPEC-ML-001 §calibration-gate, SPEC-CAU-001 §effect-error-gate, SPEC-REL-001 §release-gate-checklist |
| `INV-WF-001`, `INV-WF-002`, `INV-TEN-001`, `INV-TEN-002`, `INV-TEN-003`, `INV-IAM-001`, `INV-IAM-002`, `INV-ACT-001`, `INV-ACT-002`, `INV-ACT-003`, `INV-ACT-004`, `INV-AUD-001`, `INV-AUD-002`, `INV-COST-001`, `INV-REL-001`, `INV-REL-002` | TEMPORAL-WORKFLOW-SPEC.md, MULTI-TENANCY-SPEC.md, IAM-SPEC.md, SECURITY-ARCHITECTURE.md, TOOL-GATEWAY-SPEC.md, DATA-GOVERNANCE.md, FINOPS-SPEC.md, BILLING-SPEC.md, AUDIT-LOG-SPEC.md, OBSERVABILITY-SPEC.md, SRE-SPEC.md, DR-PLAN.md, COMPLIANCE-READINESS.md | `SPEC-WF-001`, `SPEC-TEN-001`, `SPEC-IAM-001`, `SPEC-SEC-001`, `SPEC-ACT-001`, `SPEC-DG-001`, `SPEC-FIN-001`, `SPEC-BIL-001`, `SPEC-AUD-001`, `SPEC-OBS-001`, `SPEC-SRE-001`, `SPEC-DR-001`, `SPEC-CMP-001` | SPEC-TEN-001 §cross-store-negative-matrix, SPEC-IAM-001 §authorization-delegation-matrix, SPEC-ACT-001 §idempotency-crash-suite, SPEC-AUD-001 §completeness-integrity-test, SPEC-FIN-001 §budget-boundary-test, SPEC-SRE-001 §dependency-outage-matrix, SPEC-DR-001 §DR-exercise |
| `INV-DATA-001`, `INV-DATA-002`, `INV-EVD-001`, `INV-EVD-002`, `INV-SEC-003`, `INV-PRV-001` | DATA-ARCHITECTURE.md, CONNECTOR-PLATFORM-SPEC.md, API-STANDARDS.md, EVENT-CONTRACTS.md, DATABASE-SCHEMA.md, FRONTEND-SPEC.md, TEST-STRATEGY.md, DEPLOYMENT-ARCHITECTURE.md, SYNTHETIC-DATASET-SPEC.md | `SPEC-DAT-001`, `SPEC-CON-001`, `SPEC-API-001`, `SPEC-EVT-001`, `SPEC-DB-001`, `SPEC-UX-001`, `SPEC-QA-001`, `SPEC-DEP-001`, `SPEC-SYN-001` | SPEC-DAT-001 §data-quality-reconciliation, SPEC-EVT-001 §event-contract-replay-test, SPEC-DB-001 §migration-compatibility-test, SPEC-UX-001 §accessibility-test, SPEC-SYN-001 §deterministic-fixture-hash, SPEC-CON-001 §connector-negative-suite |

No Stage A trace terminates in an implementation micro-task. Implementation micro-task IDs, individual API endpoint IDs, individual event type IDs, and individual test case IDs are Stage B artifacts generated after Rail 0 is GREEN.

## Invariant coverage verification

Every invariant in `docs/03-requirements/INVARIANT-REGISTRY.md` is referenced by at least one row in the E02–E04 contract closure table above:

| Invariant ID | Referenced in row | Owning spec task |
|---|---|---|
| `INV-TEN-001` | Row 2 | `SPEC-TEN-001` |
| `INV-TEN-002` | Row 2 | `SPEC-TEN-001` |
| `INV-TEN-003` | Row 2 | `SPEC-TEN-001` |
| `INV-IAM-001` | Row 2 | `SPEC-IAM-001` |
| `INV-IAM-002` | Row 2 | `SPEC-IAM-001` |
| `INV-SEC-001` | Row 2 | `SPEC-SEC-001` |
| `INV-SEC-002` | Row 2 | `SPEC-SEC-001` |
| `INV-SEC-003` | Row 3 | `SPEC-SEC-001`, `SPEC-CON-001` |
| `INV-ACT-001` | Row 2 | `SPEC-ACT-001` |
| `INV-ACT-002` | Row 2 | `SPEC-ACT-001` |
| `INV-ACT-003` | Row 2 | `SPEC-ACT-001` |
| `INV-ACT-004` | Row 2 | `SPEC-ACT-001` |
| `INV-WF-001` | Row 2 | `SPEC-WF-001` |
| `INV-WF-002` | Row 2 | `SPEC-WF-001` |
| `INV-AI-001` | Row 1 | `SPEC-AI-001`, `SPEC-EVL-001` |
| `INV-AI-002` | Row 1 | `SPEC-AIG-001`, `SPEC-REL-001` |
| `INV-EVD-001` | Row 3 | `SPEC-RAG-001`, `SPEC-DAT-001` |
| `INV-EVD-002` | Row 3 | `SPEC-RAG-001` |
| `INV-DATA-001` | Row 3 | `SPEC-DAT-001`, `SPEC-SYN-001` |
| `INV-DATA-002` | Row 3 | `SPEC-DAT-001` |
| `INV-AUD-001` | Row 2 | `SPEC-AUD-001` |
| `INV-AUD-002` | Row 2 | `SPEC-AUD-001` |
| `INV-COST-001` | Row 2 | `SPEC-FIN-001` |
| `INV-PRV-001` | Row 3 | `SPEC-DG-001` |
| `INV-REL-001` | Row 2 | `SPEC-SRE-001` |
| `INV-REL-002` | Row 2 | `SPEC-SRE-001` |

Coverage: 26/26 invariants traced. Zero orphans.

## NFR coverage verification

Every P0 NFR in `docs/03-requirements/NFR-BASELINE.md` maps to at least one owning specification:

| NFR ID | Owning spec |
|---|---|
| `NFR-SEC-001` | `SPEC-ACT-001`, `SPEC-SEC-001` |
| `NFR-SEC-002` | `SPEC-SEC-001` |
| `NFR-DUR-001` | `SPEC-WF-001` |
| `NFR-REL-001` | `SPEC-WF-001`, `SPEC-SRE-001` |
| `NFR-REL-002` | `SPEC-SRE-001`, `SPEC-SEC-001` |
| `NFR-TEN-001` | `SPEC-TEN-001` |
| `NFR-TEN-002` | `SPEC-TEN-001` |
| `NFR-AUD-001` | `SPEC-AUD-001` |
| `NFR-COST-001` | `SPEC-FIN-001` |
| `NFR-PRV-001` | `SPEC-DG-001`, `SPEC-OBS-001` |
| `NFR-OBS-001` | `SPEC-OBS-001` |
| `NFR-OBS-002` | `SPEC-OBS-001` |
| `NFR-AI-001` | `SPEC-AIG-001`, `SPEC-REL-001` |
| `NFR-AI-002` | `SPEC-EVL-001` |
| `NFR-AI-003` | `SPEC-RAG-001`, `SPEC-EVL-001` |
| `NFR-AI-004` | `SPEC-EVL-001` |

Coverage: 16/16 P0 NFRs traced. P1–P3 NFRs (`NFR-AVL-001..002`, `NFR-LAT-001..002`, `NFR-THR-001..002`, `NFR-REC-001`, `NFR-COST-002`, `NFR-PRV-002`, `NFR-AI-005..007`) are traced through their owning specs but are not P0 release-blocking gates.
