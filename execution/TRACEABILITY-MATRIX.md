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

## Control Plane Rails 3–5 Traceability Matrix

> [!IMPORTANT]
> **Rail 4 Status**: `TASK-R04-001` through `TASK-R04-004` have completed with 100% tests passing (`PASS`, 273/273 total backend tests pass). Rail 4 is `GREEN`. Rails 5–18 remain LOCKED. Lineage rows below represent planned Stage B targets and admitted task contracts. No code, test, security, or release claim is made.

| Requirement / Invariant / NFR / SEC | Canonical Specification | Rail Task | Exact Test Category | Acceptance Criterion | Rail Exit Gate |
|---|---|---|---|---|---|
| `INV-TEN-001` | `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §4.2, `docs/27-database/DATABASE-SCHEMA.md` §5 | `TASK-R05-001`, `TASK-R05-002`, `TASK-R05-004` | `tests/security/test_persistence_isolation_negative.py` §rls-session-isolation | `AC-R05-001-01`, `AC-R05-002-03`, `AC-R05-004-01` | Rail 5 Exit Gate |
| `INV-TEN-002` | `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §2.2, `docs/14-iam/IAM-SPEC.md` §2.4 | `TASK-R03-001`, `TASK-R03-003`, `TASK-R03-004` | `tests/security/test_authentication_negative.py` §server-derived-context | `AC-R03-001-04`, `AC-R03-003-05`, `AC-R03-004-06` | Rail 3 Exit Gate |
| `INV-TEN-003` | `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §5, `docs/14-iam/IAM-SPEC.md` §3.6 | `TASK-R03-001`, `TASK-R04-003`, `TASK-R04-004`, `TASK-R05-002` | `tests/security/test_authorization_delegation_negative.py` §break-glass-human-only | `AC-R03-001-04`, `AC-R04-003-01`, `AC-R04-004-07`, `AC-R05-002-02` | Rail 4 Exit Gate |
| `INV-IAM-001` | `docs/14-iam/IAM-SPEC.md` §2.3, §3.1 | `TASK-R03-001`, `TASK-R03-002`, `TASK-R04-001`, `TASK-R04-003`, `TASK-R04-004` | `tests/security/test_authorization_delegation_negative.py` §deny-by-default | `AC-R03-001-03`, `AC-R03-002-01`, `AC-R04-001-02`, `AC-R04-003-04`, `AC-R04-004-02` | Rail 4 Exit Gate |
| `INV-IAM-002` | `docs/14-iam/IAM-SPEC.md` §3.5 | `TASK-R04-002`, `TASK-R04-003`, `TASK-R04-004` | `tests/security/test_authorization_delegation_negative.py` §delegation-scope-containment | `AC-R04-002-03`, `AC-R04-003-05`, `AC-R04-004-03` | Rail 4 Exit Gate |
| `INV-SEC-001` | `docs/14-iam/IAM-SPEC.md` §2.5, §3.5, `docs/15-security/SECURITY-ARCHITECTURE.md` §2 | `TASK-R03-001`, `TASK-R03-003`, `TASK-R04-002` | `tests/security/test_authentication_negative.py` §no-raw-secrets | `AC-R03-001-02`, `AC-R03-003-01`, `AC-R04-002-02` | Rail 3 Exit Gate |
| `INV-SEC-002` | `docs/14-iam/IAM-SPEC.md` §1, `docs/15-security/SECURITY-ARCHITECTURE.md` §2 | `TASK-R04-001`, `TASK-R04-003` | `tests/security/test_authorization_delegation_negative.py` §untrusted-content-neutralization | `AC-R04-001-01`, `AC-R04-003-03` | Rail 4 Exit Gate |
| `INV-SEC-003` | `docs/15-security/SECURITY-ARCHITECTURE.md` §2 | `TASK-R04-002`, `TASK-R04-003` | `tests/contract/test_authorization_contracts.py` §capability-boundaries | `AC-R04-002-01`, `AC-R04-003-05` | Rail 4 Exit Gate |
| `INV-AUD-001` | `docs/22-billing/AUDIT-LOG-SPEC.md` §2, `docs/14-iam/IAM-SPEC.md` §4.1 | `TASK-R03-002`, `TASK-R03-003`, `TASK-R04-003` | `tests/contract/test_identity_auth_contracts.py` §audit-event-emission | `AC-R03-002-03`, `AC-R03-003-03`, `AC-R04-003-01` | Rail 3 Exit Gate |
| `INV-AUD-002` | `docs/22-billing/AUDIT-LOG-SPEC.md` §4 | `TASK-R03-001`, `TASK-R04-001` | `tests/security/test_authentication_negative.py` §audit-redaction-no-secrets | `AC-R03-001-02`, `AC-R04-001-04` | Rail 3 Exit Gate |
| `INV-REL-001` | `docs/14-iam/IAM-SPEC.md` §3.7, `docs/29-testing/TEST-STRATEGY.md` §3 | `TASK-R03-002`, `TASK-R04-003`, `TASK-R04-004`, `TASK-R05-002` | `tests/security/test_authorization_delegation_negative.py` §policy-uncertainty-fail-closed | `AC-R03-002-01`, `AC-R04-003-04`, `AC-R04-004-10`, `AC-R05-002-03` | Rail 4 Exit Gate |
| `INV-REL-002` | `execution/MICRO-TASK-RAIL-SYSTEM.md` §rail-sequence | `TASK-R03-004`, `TASK-R04-004`, `TASK-R05-004` | `execution/task-graph.json` §sequential-rail-gates | `AC-R03-004-08`, `AC-R04-004-08`, `AC-R05-004-07` | Control Plane Gate |
| `INV-DATA-001` | `docs/27-database/DATABASE-SCHEMA.md` §1 | `TASK-R05-003`, `TASK-R05-004` | `tests/security/test_persistence_isolation_negative.py` §migration-compatibility | `AC-R05-003-01`, `AC-R05-004-06` | Rail 5 Exit Gate |
| `INV-DATA-002` | `docs/04-system-architecture/MODULE-BOUNDARIES.md` §data-ownership-rules, `docs/27-database/DATABASE-SCHEMA.md` §3 | `TASK-R05-001` | `packages/backend/tests/shared/test_persistence_contracts.py` §single-module-ownership | `AC-R05-001-03`, `AC-R05-001-04` | Rail 5 Exit Gate |
| `NFR-SEC-001` | `docs/03-requirements/NFR-BASELINE.md` §13, `docs/15-security/SECURITY-ARCHITECTURE.md` §2 | `TASK-R04-002`, `TASK-R04-004` | `tests/security/test_authorization_delegation_negative.py` §zero-unauthorized-actions | `AC-R04-002-02`, `AC-R04-004-04` | Rail 4 Exit Gate |
| `NFR-SEC-002` | `docs/03-requirements/NFR-BASELINE.md` §14, `docs/31-adr/ADR-0009-secrets-and-keys.md` | `TASK-R03-001`, `TASK-R04-002` | `tests/security/test_authentication_negative.py` §zero-reusable-secrets | `AC-R03-001-02`, `AC-R04-002-02` | Rail 3 Exit Gate |
| `NFR-REL-001` | `docs/03-requirements/NFR-BASELINE.md` §22 | `TASK-R05-002`, `TASK-R05-003` | `tests/contract/test_persistence_contracts.py` §transaction-safety | `AC-R05-002-04`, `AC-R05-003-04` | Rail 5 Exit Gate |
| `NFR-REL-002` | `docs/03-requirements/NFR-BASELINE.md` §23, `docs/29-testing/TEST-STRATEGY.md` §3 | `TASK-R04-003`, `TASK-R04-004` | `tests/security/test_authorization_delegation_negative.py` §outage-writes-blocked | `AC-R04-003-04`, `AC-R04-004-10` | Rail 4 Exit Gate |
| `NFR-TEN-001` | `docs/03-requirements/NFR-BASELINE.md` §25, `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §1 | `TASK-R05-003`, `TASK-R05-004` | `tests/security/test_persistence_isolation_negative.py` §zero-leakage-suite | `AC-R05-003-05`, `AC-R05-004-02`, `AC-R05-004-03` | Rail 5 Exit Gate |
| `NFR-TEN-002` | `docs/03-requirements/NFR-BASELINE.md` §26, `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §7 | `TASK-R05-002`, `TASK-R05-004` | `tests/security/test_persistence_isolation_negative.py` §degraded-isolation-holds | `AC-R05-002-03`, `AC-R05-004-01` | Rail 5 Exit Gate |
| `NFR-AUD-001` | `docs/03-requirements/NFR-BASELINE.md` §27, `docs/22-billing/AUDIT-LOG-SPEC.md` §1 | `TASK-R03-003`, `TASK-R04-003` | `tests/contract/test_identity_auth_contracts.py` §audit-event-integrity | `AC-R03-003-03`, `AC-R04-003-01` | Rail 3 Exit Gate |
| `SEC-001` | `docs/03-requirements/INVARIANT-REGISTRY.md` §40, `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` | `TASK-R05-001`, `TASK-R05-002`, `TASK-R05-004` | `tests/security/test_persistence_isolation_negative.py` §tenant-isolation | `AC-R05-001-01`, `AC-R05-002-03`, `AC-R05-004-02` | Rail 5 Exit Gate |
| `SEC-002` | `docs/03-requirements/INVARIANT-REGISTRY.md` §41, `docs/14-iam/IAM-SPEC.md` §3.5 | `TASK-R04-002`, `TASK-R04-004` | `tests/security/test_authorization_delegation_negative.py` §agent-credential-isolation | `AC-R04-002-02`, `AC-R04-004-04` | Rail 4 Exit Gate |
| `SEC-003` | `docs/03-requirements/INVARIANT-REGISTRY.md` §42, `docs/14-iam/IAM-SPEC.md` §3.1 | `TASK-R03-002`, `TASK-R04-003`, `TASK-R04-004` | `tests/security/test_authorization_delegation_negative.py` §capability-authorization | `AC-R03-002-01`, `AC-R04-003-04`, `AC-R04-004-02` | Rail 4 Exit Gate |
| `SEC-004` | `docs/03-requirements/INVARIANT-REGISTRY.md` §43, `docs/15-security/SECURITY-ARCHITECTURE.md` §2 | `TASK-R04-001`, `TASK-R04-003` | `tests/security/test_authorization_delegation_negative.py` §untrusted-content-no-authority | `AC-R04-001-01`, `AC-R04-003-03` | Rail 4 Exit Gate |
| `SEC-005` | `docs/03-requirements/INVARIANT-REGISTRY.md` §44, `docs/14-iam/IAM-SPEC.md` §3.5 | `TASK-R04-002`, `TASK-R04-004` | `tests/security/test_authorization_delegation_negative.py` §agent-approval-prohibition | `AC-R04-002-02`, `AC-R04-004-04` | Rail 4 Exit Gate |
| `SEC-006` | `docs/03-requirements/INVARIANT-REGISTRY.md` §45, `docs/26-api/API-STANDARDS.md` §4 | `TASK-R05-001`, `TASK-R05-002` | `tests/contract/test_persistence_contracts.py` §idempotent-persistence | `AC-R05-001-02`, `AC-R05-002-01` | Rail 5 Exit Gate |
| `SEC-007` | `docs/03-requirements/INVARIANT-REGISTRY.md` §46, `docs/29-testing/TEST-STRATEGY.md` §3 | `TASK-R04-003`, `TASK-R04-004` | `tests/security/test_authorization_delegation_negative.py` §fail-closed-uncertainty | `AC-R04-003-04`, `AC-R04-004-10` | Rail 4 Exit Gate |
| `SEC-008` | `docs/03-requirements/INVARIANT-REGISTRY.md` §47, `docs/27-database/DATABASE-SCHEMA.md` §8 | `TASK-R05-003`, `TASK-R05-004` | `tests/security/test_persistence_isolation_negative.py` §versioned-migrations | `AC-R05-003-01`, `AC-R05-004-06` | Rail 5 Exit Gate |
| `SEC-009` | `docs/03-requirements/INVARIANT-REGISTRY.md` §48, `docs/22-billing/AUDIT-LOG-SPEC.md` §1 | `TASK-R03-003`, `TASK-R04-003` | `tests/contract/test_identity_auth_contracts.py` §immutable-audit-logging | `AC-R03-003-03`, `AC-R04-003-01` | Rail 3 Exit Gate |
| `SEC-010` | `docs/03-requirements/INVARIANT-REGISTRY.md` §49, `docs/14-iam/IAM-SPEC.md` §3.5 | `TASK-R04-002`, `TASK-R04-004` | `tests/security/test_authorization_delegation_negative.py` §hard-blast-limits | `AC-R04-002-01`, `AC-R04-004-06` | Rail 4 Exit Gate |

---

## Phase 01 — Canonical Data and Synthetic Benchmark Traceability Matrix

| Business Requirement | Data Entity / Metric | Canonical Specification | Phase 01 Task | Exact Test Category | Acceptance Criterion | Phase 01 Exit Gate |
|---|---|---|---|---|---|---|
| `BR-001` | `Order`, `Shipment`, `cancellation_rate` | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §4.2, `docs/07-data-platform/METRIC-REGISTRY.md` §2.1 | `TASK-P01-001`, `TASK-P01-002`, `TASK-P01-006` | `TC-P01-013` (`test_metric_semantics.py`) | `AC-001`, `AC-002`, `AC-P01-006-03` | Phase 01 Exit Gate |
| `BR-002` | `Customer`, `ContractClause`, `revenue_at_risk`, `customer_churn_rate` | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §4.1, `docs/07-data-platform/METRIC-REGISTRY.md` §2.2, §2.6, `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §6.5 | `TASK-P01-002`, `TASK-P01-004` | `TC-P01-016` (`test_scenario_injection.py`) | `AC-006`, `AC-P01-004-01` | Phase 01 Exit Gate |
| `BR-003` | `SupportTicket`, `MaintenanceEvent`, `Contract` | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §4.5, §4.6, §4.7 | `TASK-P01-001`, `TASK-P01-003` | `TC-P01-003` (`test_canonical_schema.py`), `TC-P01-010` (`test_effective_date_contracts.py`) | `AC-001`, `AC-P01-001-01` | Phase 01 Exit Gate |
| `BR-004` | All Canonical Entities, `ten_alpha`, `ten_beta` | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §1, `docs/27-database/DATABASE-SCHEMA.md` §10–15 | `TASK-P01-001`, `TASK-P01-003` | `TC-P01-006` (`test_synthetic_tenant_isolation.py`) | `AC-010`, `AC-P01-003-03` | Phase 01 Exit Gate |
| `BR-005` | `manifest.json`, `GroundTruthIncident` | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §3, `docs/20-evaluation/EVALUATION-FRAMEWORK.md` §2 | `TASK-P01-003`, `TASK-P01-004`, `TASK-P01-006` | `TC-P01-001` (`test_seed_reproducibility.py`), `TC-P01-002` (`test_manifest_hashes.py`) | `AC-001`, `AC-014`, `AC-P01-006-01` | Phase 01 Exit Gate |
| `FR-DET-001` | `cancellation_rate` (`METRIC-001`) .. `ticket_volume` (`METRIC-009`) | `docs/07-data-platform/METRIC-REGISTRY.md` §2 | `TASK-P01-002` | `TC-P01-013` (`test_metric_semantics.py`) | `AC-002`, `AC-P01-002-01` | Phase 01 Exit Gate |
| `FR-DET-002` | `cancellation_rate` baseline & injected disruption | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §6.3 | `TASK-P01-004` | `TC-P01-016` (`test_scenario_injection.py`) | `AC-002`, `AC-P01-004-01` | Phase 01 Exit Gate |
| `FR-DET-003` | `Order.dedup_key`, `Shipment.dedup_key` | `docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md` §3.6 | `TASK-P01-005` | `TC-P01-012` (`test_duplicate_idempotency.py`) | `AC-P01-005-01` | Phase 01 Exit Gate |
| `FR-INV-001` | `Order`, `Shipment`, `SupportTicket` snapshot | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §4 | `TASK-P01-001` | `TC-P01-003` (`test_canonical_schema.py`) | `AC-001`, `AC-P01-001-01` | Phase 01 Exit Gate |
| `FR-INV-002` | Canonical Read Models | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §2 | `TASK-P01-001` | `TC-P01-003` (`test_canonical_schema.py`) | `AC-P01-001-01` | Phase 01 Exit Gate |
| `FR-INV-003` | `raw_quarantine` Replay Engine | `docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md` §5 | `TASK-P01-005` | `TC-P01-011` (`test_late_arrival_replay.py`) | `AC-P01-005-03` | Phase 01 Exit Gate |
| `FR-INV-004` | Metric Allowed Dimensions & Filters | `docs/07-data-platform/METRIC-REGISTRY.md` §2 | `TASK-P01-002` | `TC-P01-013` (`test_metric_semantics.py`) | `AC-P01-002-02` | Phase 01 Exit Gate |
| `FR-ML-001` | Train/Val/Test Chronological Splits | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §5.1 | `TASK-P01-003` | `TC-P01-008` (`test_temporal_leakage.py`) | `AC-001`, `AC-P01-003-01` | Phase 01 Exit Gate |
| `FR-ML-002` | `customer_churn_rate` (`METRIC-006`) | `docs/07-data-platform/METRIC-REGISTRY.md` §2.6 | `TASK-P01-002` | `TC-P01-013` (`test_metric_semantics.py`) | `AC-P01-002-01` | Phase 01 Exit Gate |
| `FR-ML-003` | True Treatment Effect vs Churn Prob | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §6.5 | `TASK-P01-004` | `TC-P01-016` (`test_scenario_injection.py`) | `AC-006`, `AC-P01-004-01` | Phase 01 Exit Gate |
| `FR-ML-004` | Midwest Truck Incident True ATE `+0.0660` | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §6.5 | `TASK-P01-004` | `TC-P01-016` (`test_scenario_injection.py`) | `AC-006`, `AC-P01-004-01` | Phase 01 Exit Gate |
| `FR-LRN-001` | `Order.cancelled_at`, Status Horizons | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §4.2 | `TASK-P01-001` | `TC-P01-003` (`test_canonical_schema.py`) | `AC-001`, `AC-P01-001-02` | Phase 01 Exit Gate |
| `FR-LRN-002` | Ground-Truth Schema Air-Gap | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §7, `docs/20-evaluation/EVALUATION-FRAMEWORK.md` §3.2 | `TASK-P01-004`, `TASK-P01-006` | `TC-P01-007` (`test_ground_truth_airgap.py`) | `AC-001`, `AC-P01-006-02` | Phase 01 Exit Gate |
| `INV-TEN-001`| All Canonical Entities `tenant_id` | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §1, §3 | `TASK-P01-001` | `TC-P01-003` (`test_canonical_schema.py`), `TC-P01-006` (`test_synthetic_tenant_isolation.py`) | `AC-010`, `AC-P01-001-01` | Phase 01 Exit Gate |
| `INV-TEN-002`| Entity Validation Server-Side Tenant | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §1 | `TASK-P01-001`, `TASK-P01-005` | `TC-P01-004` (`test_range_checks.py`), `TC-P01-014` (`test_quarantine_pipeline.py`) | `AC-010`, `AC-P01-005-04` | Phase 01 Exit Gate |
| `INV-TEN-003`| Explicit Context / Null Tenant Reject| `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §1 | `TASK-P01-001` | `TC-P01-003` (`test_canonical_schema.py`) | `AC-010`, `AC-P01-001-01` | Phase 01 Exit Gate |
| `INV-DATA-001`| Versioned Metrics & `as_of` Watermark | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §3, `docs/07-data-platform/METRIC-REGISTRY.md` §1 | `TASK-P01-002`, `TASK-P01-003` | `TC-P01-008` (`test_temporal_leakage.py`), `TC-P01-009` (`test_feature_leakage.py`) | `AC-001`, `AC-002`, `AC-P01-002-04` | Phase 01 Exit Gate |
| `INV-DATA-002`| Authoritative Canonical & Lineage | `docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md` §4 | `TASK-P01-005` | `TC-P01-015` (`test_lineage_traceability.py`) | `AC-001`, `AC-P01-005-02` | Phase 01 Exit Gate |
| `INV-REL-001`| Quarantine Fail-Closed on Invalid | `docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md` §3 | `TASK-P01-005` | `TC-P01-014` (`test_quarantine_pipeline.py`) | `AC-P01-005-01` | Phase 01 Exit Gate |
| `INV-REL-002`| Phase 01 Exit Gate Verification | `docs/29-testing/TEST-STRATEGY.md` §5 | `TASK-P01-006` | `TC-P01-018` (`test_profile_generation.py`) | `AC-P01-006-05` | Phase 01 Exit Gate |
| `NFR-TEN-001`| Zero Cross-Tenant Leakage | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §4 | `TASK-P01-003` | `TC-P01-006` (`test_synthetic_tenant_isolation.py`) | `AC-010`, `AC-P01-003-03` | Phase 01 Exit Gate |
| `NFR-TEN-002`| Composite Keys & Isolation Integrity | `docs/27-database/DATABASE-SCHEMA.md` §10–13 | `TASK-P01-001` | `TC-P01-006` (`test_synthetic_tenant_isolation.py`) | `AC-010`, `AC-P01-001-01` | Phase 01 Exit Gate |
| `NFR-AI-002` | Midwest Truck Incident True Labels | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §6 | `TASK-P01-004` | `TC-P01-016` (`test_scenario_injection.py`) | `AC-001`, `AC-P01-004-01` | Phase 01 Exit Gate |
| `NFR-AI-003` | Document URI & Digest on Contract | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §4.7 | `TASK-P01-001` | `TC-P01-010` (`test_effective_date_contracts.py`) | `AC-005`, `AC-P01-001-01` | Phase 01 Exit Gate |
| `NFR-AI-004` | Strict SQL / Metric Dimensions | `docs/07-data-platform/METRIC-REGISTRY.md` §2 | `TASK-P01-002` | `TC-P01-013` (`test_metric_semantics.py`) | `AC-002`, `AC-P01-002-02` | Phase 01 Exit Gate |
| `NFR-AI-005` | Churn Rate Metric Semantics | `docs/07-data-platform/METRIC-REGISTRY.md` §2.6 | `TASK-P01-002` | `TC-P01-013` (`test_metric_semantics.py`) | `AC-P01-002-01` | Phase 01 Exit Gate |
| `NFR-AI-006` | Injected Counterfactual Control Cohort| `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §6.5 | `TASK-P01-004` | `TC-P01-017` (`test_control_population.py`) | `AC-006`, `AC-P01-004-02` | Phase 01 Exit Gate |
| `NFR-AI-007` | Synthetic Causal Estimand Error <=0.05| `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §6.5 | `TASK-P01-004` | `TC-P01-016` (`test_scenario_injection.py`) | `AC-006`, `AC-P01-004-01` | Phase 01 Exit Gate |
| `NFR-OBS-001`| `lineage_trace_id` Envelope on Entities| `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §3 | `TASK-P01-001`, `TASK-P01-005` | `TC-P01-015` (`test_lineage_traceability.py`) | `AC-P01-005-01` | Phase 01 Exit Gate |
| `NFR-OBS-002`| 100% Security Audit on Tenant Mismatch | `docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md` §3.5 | `TASK-P01-005` | `TC-P01-014` (`test_quarantine_pipeline.py`) | `AC-P01-005-04` | Phase 01 Exit Gate |
| `NFR-PRV-001`| PII Classification and Masking | `docs/07-data-platform/CANONICAL-DATA-MODEL.md` §4.1 | `TASK-P01-001` | `TC-P01-003` (`test_canonical_schema.py`) | `AC-P01-001-01` | Phase 01 Exit Gate |
| `NFR-AUD-001`| Lineage Log & Payload SHA-256 Hashes | `docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md` §4 | `TASK-P01-005` | `TC-P01-015` (`test_lineage_traceability.py`) | `AC-P01-005-01` | Phase 01 Exit Gate |
| `AC-001` | Seeded Benchmark Reproducibility | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §3 | `TASK-P01-003`, `TASK-P01-006` | `TC-P01-001` (`test_seed_reproducibility.py`), `TC-P01-002` (`test_manifest_hashes.py`) | `AC-P01-003-01`, `AC-P01-006-01` | Phase 01 Exit Gate |
| `AC-002` | Anomaly Detection Metric Reporting | `docs/07-data-platform/METRIC-REGISTRY.md` §2.1 | `TASK-P01-002` | `TC-P01-013` (`test_metric_semantics.py`) | `AC-P01-002-02` | Phase 01 Exit Gate |
| `AC-006` | Causal Estimand & Assumptions Stated | `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` §6.5 | `TASK-P01-004` | `TC-P01-016` (`test_scenario_injection.py`) | `AC-P01-004-01` | Phase 01 Exit Gate |
| `AC-014` | Distinct Measured vs Target Discipline | `docs/20-evaluation/EVALUATION-FRAMEWORK.md` §1 | `TASK-P01-006` | `TC-P01-002` (`test_manifest_hashes.py`), `TC-P01-018` (`test_profile_generation.py`) | `AC-P01-006-05` | Phase 01 Exit Gate |

---

## Phase 02 — Detection and Analytics Traceability Matrix

| Requirement / Invariant / NFR / AC | Metric / Data / Detector Contract | Canonical Specification | Phase 02 Task | Exact Test Category | Acceptance Criterion | Phase 02 Exit Gate |
|---|---|---|---|---|---|---|
| `BR-001` | `MetricService`, `StlResidualDetector` | `docs/07-data-platform/METRIC-SERVICE-SPEC.md` §2, `docs/02-domain/ANOMALY-DOMAIN-SPEC.md` §2 | `TASK-P02-001`, `TASK-P02-003`, `TASK-P02-006` | `TC-P02-010` (`test_detector_stl_residual.py`) | `AC-002`, `AC-P02-003-01` | Phase 02 Exit Gate |
| `FR-DET-001` | Versioned Metric Query Engine | `docs/07-data-platform/METRIC-SERVICE-SPEC.md` §2 | `TASK-P02-001` | `TC-P02-001` (`test_metric_service_queries.py`) | `AC-002`, `AC-P02-001-01` | Phase 02 Exit Gate |
| `FR-DET-002` | `StlResidualDetector`, Prediction Intervals | `docs/20-evaluation/ANOMALY-BENCHMARK-PROTOCOL.md` §2 | `TASK-P02-002`, `TASK-P02-003` | `TC-P02-009` (`test_interval_calibration.py`), `TC-P02-010` (`test_detector_stl_residual.py`) | `AC-002`, `AC-P02-003-01` | Phase 02 Exit Gate |
| `FR-DET-003` | Anomaly Idempotency & Outbox Dedup | `docs/26-api/API-STANDARDS.md` §5.2, `docs/26-api/EVENT-CONTRACTS.md` §4 | `TASK-P02-005` | `TC-P02-023` (`test_anomaly_event_contracts.py`) | `AC-P02-005-01` | Phase 02 Exit Gate |
| `FR-DET-004` | Multi-Dimensional Segment Drill-Down | `docs/02-domain/ANOMALY-LOCALIZATION-SPEC.md` §2 | `TASK-P02-004` | `TC-P02-016` (`test_dimension_drilldown.py`), `TC-P02-017` (`test_hierarchical_drilldown.py`) | `AC-002`, `AC-P02-004-01` | Phase 02 Exit Gate |
| `FR-DET-005` | 7-State Anomaly Lifecycle State Machine | `docs/02-domain/ANOMALY-DOMAIN-SPEC.md` §4 | `TASK-P02-005` | `TC-P02-019` (`test_anomaly_lifecycle.py`), `TC-P02-020` (`test_anomaly_invariants.py`) | `AC-P02-005-01`, `AC-P02-005-02` | Phase 02 Exit Gate |
| `FR-DET-006` | Small-Sample Noise Suppression ($d_k \ge 30$) | `docs/02-domain/ANOMALY-LOCALIZATION-SPEC.md` §2.2 | `TASK-P02-004` | `TC-P02-018` (`test_noise_suppression.py`) | `AC-P02-004-03` | Phase 02 Exit Gate |
| `FR-INV-004` | Registry Dimension Allowlists | `docs/07-data-platform/METRIC-SERVICE-SPEC.md` §1, §4 | `TASK-P02-001`, `TASK-P02-004` | `TC-P02-004` (`test_metric_dimension_filter.py`) | `AC-P02-001-04` | Phase 02 Exit Gate |
| `FR-ML-001` | Rolling Time-Split Backtest Harness | `docs/20-evaluation/ANOMALY-BENCHMARK-PROTOCOL.md` §4 | `TASK-P02-003` | `TC-P02-013` (`test_rolling_timesplit_backtest.py`) | `AC-001`, `AC-P02-003-03` | Phase 02 Exit Gate |
| `INV-TEN-001`| All `Anomaly` and `MetricService` Queries | `docs/02-domain/ANOMALY-DOMAIN-SPEC.md` §2, `docs/07-data-platform/METRIC-SERVICE-SPEC.md` §1 | `TASK-P02-001`, `TASK-P02-005` | `TC-P02-005` (`test_metric_tenant_isolation.py`) | `AC-010`, `AC-P02-001-01` | Phase 02 Exit Gate |
| `INV-TEN-002`| Server-Derived `TenantContext` Injection | `docs/26-api/API-STANDARDS.md` §2 | `TASK-P02-001` | `TC-P02-005` (`test_metric_tenant_isolation.py`) | `AC-010`, `AC-P02-001-01` | Phase 02 Exit Gate |
| `INV-TEN-003`| Explicit Context / Null Tenant Reject | `docs/07-data-platform/METRIC-SERVICE-SPEC.md` §1 | `TASK-P02-001` | `TC-P02-005` (`test_metric_tenant_isolation.py`) | `AC-010`, `AC-P02-001-01` | Phase 02 Exit Gate |
| `INV-DATA-001`| Strict As-Of Cut-Off Anti-Leakage | `docs/07-data-platform/METRIC-SERVICE-SPEC.md` §1, `docs/20-evaluation/ANOMALY-BENCHMARK-PROTOCOL.md` §1 | `TASK-P02-001`, `TASK-P02-003` | `TC-P02-003` (`test_metric_as_of_watermark.py`), `TC-P02-013` (`test_rolling_timesplit_backtest.py`) | `AC-001`, `AC-002`, `AC-P02-003-03` | Phase 02 Exit Gate |
| `INV-DATA-002`| Late-Event Reconciliation & Supersession | `docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md` §7 | `TASK-P02-005` | `TC-P02-021` (`test_late_event_recomputation.py`), `TC-P02-022` (`test_anomaly_supersession.py`) | `AC-001`, `AC-P02-005-03` | Phase 02 Exit Gate |
| `INV-REL-001`| Deterministic Baseline Fallback | `docs/08-ml-platform/ML-SYSTEM-SPEC.md` §1 | `TASK-P02-002` | `TC-P02-006` (`test_baseline_seasonal_naive.py`) | `AC-P02-002-04` | Phase 02 Exit Gate |
| `INV-REL-002`| Phase 02 Exit-Gate Sequential Verification | `docs/29-testing/TEST-STRATEGY.md` §7 | `TASK-P02-006` | `TC-P02-024` (`test_phase_02_exit_gate.py`) | `AC-P02-006-05` | Phase 02 Exit Gate |
| `INV-AI-001` | Non-Causal Localization Invariant | `docs/02-domain/ANOMALY-DOMAIN-SPEC.md` §1.1, `docs/02-domain/ANOMALY-LOCALIZATION-SPEC.md` §1 | `TASK-P02-004` | `TC-P02-016` (`test_dimension_drilldown.py`) | `AC-002`, `AC-P02-004-04` | Phase 02 Exit Gate |
| `NFR-TEN-001`| Zero Cross-Tenant Leakage in Metrics/Anomalies | `docs/27-database/DATABASE-SCHEMA.md` §17 | `TASK-P02-001`, `TASK-P02-005` | `TC-P02-005` (`test_metric_tenant_isolation.py`) | `AC-010`, `AC-P02-001-01` | Phase 02 Exit Gate |
| `NFR-TEN-002`| Composite Keys & Isolation Under Load | `docs/27-database/DATABASE-SCHEMA.md` §17 | `TASK-P02-005` | `TC-P02-005` (`test_metric_tenant_isolation.py`) | `AC-010`, `AC-P02-005-01` | Phase 02 Exit Gate |
| `NFR-AI-002` | Localization Accuracy >= 0.85 on True Scope | `docs/02-domain/ANOMALY-LOCALIZATION-SPEC.md` §2 | `TASK-P02-004` | `TC-P02-016` (`test_dimension_drilldown.py`) | `AC-001`, `AC-P02-004-01` | Phase 02 Exit Gate |
| `NFR-AI-004` | Exact SQL / Metric Evaluation Correctness | `docs/07-data-platform/METRIC-SERVICE-SPEC.md` §2 | `TASK-P02-001` | `TC-P02-001` (`test_metric_service_queries.py`) | `AC-002`, `AC-P02-001-01` | Phase 02 Exit Gate |
| `NFR-OBS-001`| Distributed Trace & Correlation Propagation | `docs/26-api/API-STANDARDS.md` §5 | `TASK-P02-001`, `TASK-P02-005` | `TC-P02-023` (`test_anomaly_event_contracts.py`) | `AC-P02-005-01` | Phase 02 Exit Gate |
| `NFR-OBS-002`| 100% Audit Logging of State Transitions | `docs/27-database/DATABASE-SCHEMA.md` §17 | `TASK-P02-005` | `TC-P02-020` (`test_anomaly_invariants.py`) | `AC-P02-005-04` | Phase 02 Exit Gate |
| `NFR-PRV-001`| Aggregated Dimensions Without Raw PII | `docs/07-data-platform/METRIC-SERVICE-SPEC.md` §1 | `TASK-P02-001` | `TC-P02-001` (`test_metric_service_queries.py`) | `AC-P02-001-01` | Phase 02 Exit Gate |
| `AC-001` | Seeded Benchmark Reproducibility | `docs/20-evaluation/ANOMALY-BENCHMARK-PROTOCOL.md` §4 | `TASK-P02-003`, `TASK-P02-006` | `TC-P02-013` (`test_rolling_timesplit_backtest.py`) | `AC-P02-003-03`, `AC-P02-006-01` | Phase 02 Exit Gate |
| `AC-002` | Detection Reporting Intervals, Score, Watermark| `docs/02-domain/ANOMALY-DOMAIN-SPEC.md` §2 | `TASK-P02-003`, `TASK-P02-006` | `TC-P02-010` (`test_detector_stl_residual.py`) | `AC-P02-003-01`, `AC-P02-006-01` | Phase 02 Exit Gate |
| `AC-014` | Distinct Measured vs Target Discipline | `docs/20-evaluation/ANOMALY-BENCHMARK-PROTOCOL.md` §1 | `TASK-P02-003`, `TASK-P02-006` | `TC-P02-013` (`test_rolling_timesplit_backtest.py`), `TC-P02-024` (`test_phase_02_exit_gate.py`) | `AC-P02-006-05` | Phase 02 Exit Gate |

---

## Phase 03 — Governed Evidence and Investigation Traceability Matrix

| Requirement / Invariant / NFR / AC | Contract / Component | Canonical Specification | Phase 03 Task | Exact Test Category | Acceptance Criterion | Phase 03 Exit Gate |
|---|---|---|---|---|---|---|
| `BR-001` | Investigation Workflow & Root-Cause | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §1 | `TASK-P03-001`, `TASK-P03-002`, `TASK-P03-008` | `TC-P03-001` (`test_investigation_domain.py`), `TC-P03-024` (`test_phase_03_exit_gate.py`) | `AC-003`, `AC-P03-008-01` | Phase 03 Exit Gate |
| `FR-INV-001` | Typed, Budgeted Investigation DAG | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §2.1, §4 | `TASK-P03-006` | `TC-P03-018` (`test_planner_dag_validation.py`) | `AC-003`, `AC-P03-006-01` | Phase 03 Exit Gate |
| `FR-INV-002` | Parallel Read-Only Activity Dispatch | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §5 | `TASK-P03-002` | `TC-P03-001` (`test_investigation_domain.py`) | `AC-003`, `AC-P03-002-01` | Phase 03 Exit Gate |
| `FR-INV-003` | Checkpoint, Retry, Cancel, Pause/Resume | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §6, §7 | `TASK-P03-002` | `TC-P03-004` (`test_recovery_worker_loss_zero_loss.py`), `TC-P03-005` (`test_investigation_signals_queries.py`) | `AC-003`, `AC-P03-002-01` | Phase 03 Exit Gate |
| `FR-INV-004` | Registered Dimension Drill-Down (No Raw SQL)| `docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md` §1, §2 | `TASK-P03-003` | `TC-P03-006` (`test_sql_capability_catalog_allowlist.py`), `TC-P03-007` (`test_sql_read_only_enforcement.py`) | `AC-004`, `AC-P03-003-01` | Phase 03 Exit Gate |
| `FR-EVD-001` | Evidence Provenance, ACL, Time, Digest | `docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md` §2 | `TASK-P03-004` | `TC-P03-010` (`test_evidence_record_schema.py`) | `AC-005`, `AC-P03-004-01` | Phase 03 Exit Gate |
| `FR-EVD-002` | Hybrid Retrieval & Citation Verification | `docs/09-rag/RAG-SPEC.md` §2 | `TASK-P03-005` | `TC-P03-013` (`test_rag_hybrid_retrieval.py`), `TC-P03-014` (`test_rag_citation_precision.py`) | `AC-005`, `AC-P03-005-01` | Phase 03 Exit Gate |
| `FR-EVD-003` | Rejection of Superseded / Out-of-Scope SLA | `docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md` §4 | `TASK-P03-004` | `TC-P03-012` (`test_evidence_effective_date.py`) | `AC-005`, `AC-P03-004-02` | Phase 03 Exit Gate |
| `FR-RCA-001` | Ranked Hypotheses with Evidence Support | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §2.3, §6 | `TASK-P03-006` | `TC-P03-019` (`test_unsupported_claim_rejection.py`), `TC-P03-020` (`test_contradiction_detection.py`) | `AC-004`, `AC-P03-006-02` | Phase 03 Exit Gate |
| `FR-RCA-002` | Fallback to NEED_MORE_EVIDENCE | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §6 | `TASK-P03-006` | `TC-P03-021` (`test_need_more_evidence_fallback.py`) | `AC-004`, `AC-P03-006-02` | Phase 03 Exit Gate |
| `FR-CTL-001` | Trusted Server-Derived Tenant Context | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §1, `docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md` §1 | `TASK-P03-001`, `TASK-P03-003` | `TC-P03-008` (`test_sql_tenant_isolation_negative.py`) | `AC-010`, `AC-P03-003-02` | Phase 03 Exit Gate |
| `INV-WF-001` | Durable Workflow State in Temporal/DB | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §1 | `TASK-P03-002` | `TC-P03-004` (`test_recovery_worker_loss_zero_loss.py`) | `AC-003`, `AC-P03-002-02` | Phase 03 Exit Gate |
| `INV-WF-002` | Deterministic Workflow Code & Replay | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §8 | `TASK-P03-002` | `TC-P03-003` (`test_investigation_workflow_replay.py`) | `AC-003`, `AC-P03-002-02` | Phase 03 Exit Gate |
| `INV-EVD-001`| Immutable Evidence Provenance & Digest | `docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md` §1 | `TASK-P03-004` | `TC-P03-010` (`test_evidence_record_schema.py`) | `AC-005`, `AC-P03-004-01` | Phase 03 Exit Gate |
| `INV-EVD-002`| Rejection of Superseded Evidence | `docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md` §4 | `TASK-P03-004` | `TC-P03-012` (`test_evidence_effective_date.py`) | `AC-005`, `AC-P03-004-02` | Phase 03 Exit Gate |
| `INV-AI-001` | Zero Unsupported Claims in Hypotheses | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §1, §6 | `TASK-P03-006` | `TC-P03-019` (`test_unsupported_claim_rejection.py`) | `AC-004`, `AC-P03-006-02` | Phase 03 Exit Gate |
| `INV-AI-002` | Investigation Manifest Version References | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §5.8 | `TASK-P03-001`, `TASK-P03-002` | `TC-P03-002` (`test_investigation_manifest_budget.py`) | `AC-011`, `AC-P03-001-01` | Phase 03 Exit Gate |
| `INV-TEN-001`| Physical & Logical Tenant Isolation | `docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md` §1, `docs/09-rag/RAG-SPEC.md` §2 | `TASK-P03-003`, `TASK-P03-004`, `TASK-P03-005` | `TC-P03-008` (`test_sql_tenant_isolation_negative.py`), `TC-P03-011` (`test_evidence_tenant_isolation.py`) | `AC-010`, `AC-P03-003-02` | Phase 03 Exit Gate |
| `INV-TEN-002`| Server-Derived Tenant Context | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §1 | `TASK-P03-001`, `TASK-P03-003` | `TC-P03-008` (`test_sql_tenant_isolation_negative.py`) | `AC-010`, `AC-P03-001-01` | Phase 03 Exit Gate |
| `INV-TEN-003`| Explicit Privileged Context (No Null Tenant)| `docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md` §1 | `TASK-P03-003` | `TC-P03-008` (`test_sql_tenant_isolation_negative.py`) | `AC-010`, `AC-P03-003-02` | Phase 03 Exit Gate |
| `INV-IAM-001`| Deny-By-Default Server-Side Auth | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §3 | `TASK-P03-003`, `TASK-P03-005` | `TC-P03-006` (`test_sql_capability_catalog_allowlist.py`) | `AC-005`, `AC-P03-003-01` | Phase 03 Exit Gate |
| `INV-IAM-002`| Delegated Agent Identity Scoping | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §1 | `TASK-P03-006` | `TC-P03-018` (`test_planner_dag_validation.py`) | `AC-003`, `AC-P03-006-01` | Phase 03 Exit Gate |
| `INV-SEC-001`| Agent Zero Credential Possession | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §1 | `TASK-P03-006` | `TC-P03-022` (`test_phase03_mutation_barrier.py`) | `AC-008`, `AC-P03-006-01` | Phase 03 Exit Gate |
| `INV-SEC-002`| Documents & Tickets Untrusted Content | `docs/06-agent-platform/TICKET-INTELLIGENCE-SPEC.md` §1, `docs/09-rag/RAG-SPEC.md` §4 | `TASK-P03-005`, `TASK-P03-007` | `TC-P03-015` (`test_rag_prompt_injection_defense.py`), `TC-P03-017` (`test_ticket_prompt_injection.py`) | `AC-005`, `AC-P03-007-02` | Phase 03 Exit Gate |
| `INV-SEC-003`| Registered Tool Schemas (No Free Egress) | `docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md` §1 | `TASK-P03-003` | `TC-P03-006` (`test_sql_capability_catalog_allowlist.py`) | `AC-004`, `AC-P03-003-01` | Phase 03 Exit Gate |
| `INV-DATA-001`| Temporal Anti-Leakage on Queries/Evidence | `docs/18-data-governance/DATA-GOVERNANCE.md` §3 | `TASK-P03-003`, `TASK-P03-004` | `TC-P03-009` (`test_sql_time_travel_anti_leakage.py`), `TC-P03-012` (`test_evidence_effective_date.py`) | `AC-001`, `AC-P03-003-01` | Phase 03 Exit Gate |
| `INV-DATA-002`| Source Precedence & Rebuildable Indexes | `docs/18-data-governance/DATA-GOVERNANCE.md` §3 | `TASK-P03-005` | `TC-P03-013` (`test_rag_hybrid_retrieval.py`) | `AC-005`, `AC-P03-005-01` | Phase 03 Exit Gate |
| `INV-AUD-001`| Immutable Security Audit Events | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §7.3 | `TASK-P03-001`, `TASK-P03-002` | `TC-P03-001` (`test_investigation_domain.py`) | `AC-012`, `AC-P03-001-01` | Phase 03 Exit Gate |
| `INV-AUD-002`| Audit Privacy (No PII/Secrets Archiving) | `docs/18-data-governance/DATA-GOVERNANCE.md` §1 | `TASK-P03-001`, `TASK-P03-007` | `TC-P03-016` (`test_ticket_dlp_redaction.py`) | `AC-012`, `AC-P03-007-01` | Phase 03 Exit Gate |
| `INV-COST-001`| FinOps Investigation Budget Enforcement | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §5 | `TASK-P03-001`, `TASK-P03-006` | `TC-P03-002` (`test_investigation_manifest_budget.py`) | `AC-012`, `AC-P03-001-02` | Phase 03 Exit Gate |
| `INV-PRV-001`| Purpose Limitation & PII Redaction | `docs/06-agent-platform/TICKET-INTELLIGENCE-SPEC.md` §3 | `TASK-P03-007` | `TC-P03-016` (`test_ticket_dlp_redaction.py`) | `AC-010`, `AC-P03-007-01` | Phase 03 Exit Gate |
| `INV-REL-001`| Fail-Closed on Auth/Security Flaw | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §7.3 | `TASK-P03-002` | `TC-P03-001` (`test_investigation_domain.py`) | `AC-003`, `AC-P03-002-01` | Phase 03 Exit Gate |
| `INV-REL-002`| Phase 03 Exit Gate Sequential Verification | `docs/29-testing/TEST-STRATEGY.md` §8 | `TASK-P03-008` | `TC-P03-024` (`test_phase_03_exit_gate.py`) | `AC-P03-008-01`, `AC-P03-008-02` | Phase 03 Exit Gate |
| `NFR-DUR-001`| Zero State Loss Across Worker Kill | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §1 | `TASK-P03-002` | `TC-P03-004` (`test_recovery_worker_loss_zero_loss.py`) | `AC-003`, `AC-P03-002-02` | Phase 03 Exit Gate |
| `NFR-REL-001`| Workflow Resumes Within 5 min | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §7 | `TASK-P03-002` | `TC-P03-004` (`test_recovery_worker_loss_zero_loss.py`) | `AC-003`, `AC-P03-002-02` | Phase 03 Exit Gate |
| `NFR-REL-002`| 100% External Mutations Blocked | `docs/15-security/SECURITY-ARCHITECTURE.md` §5 | `TASK-P03-003`, `TASK-P03-008` | `TC-P03-022` (`test_phase03_mutation_barrier.py`) | `AC-008`, `AC-P03-008-02` | Phase 03 Exit Gate |
| `NFR-TEN-001`| Zero Cross-Tenant Read/Write/Retrieval Leakage| `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` | `TASK-P03-003`, `TASK-P03-005` | `TC-P03-008` (`test_sql_tenant_isolation_negative.py`), `TC-P03-011` (`test_evidence_tenant_isolation.py`) | `AC-010`, `AC-P03-008-02` | Phase 03 Exit Gate |
| `NFR-TEN-002`| Tenant Isolation Holds Under Concurrency | `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` | `TASK-P03-008` | `TC-P03-024` (`test_phase_03_exit_gate.py`) | `AC-010`, `AC-P03-008-02` | Phase 03 Exit Gate |
| `NFR-AI-001` | 100% Artifacts Version-Referenced | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §5.8 | `TASK-P03-001` | `TC-P03-002` (`test_investigation_manifest_budget.py`) | `AC-011`, `AC-P03-001-01` | Phase 03 Exit Gate |
| `NFR-AI-002` | RCA Top-1 >= 0.80, Top-3 >= 0.95 | `docs/20-evaluation/INVESTIGATION-BENCHMARK-PROTOCOL.md` §2 | `TASK-P03-008` | `TC-P03-024` (`test_phase_03_exit_gate.py`) | `AC-004`, `AC-P03-008-01` | Phase 03 Exit Gate |
| `NFR-AI-003` | Recall@10 >=0.90, Citation Precision >=0.95 | `docs/09-rag/RAG-SPEC.md` §5 | `TASK-P03-005` | `TC-P03-013` (`test_rag_hybrid_retrieval.py`), `TC-P03-014` (`test_rag_citation_precision.py`) | `AC-005`, `AC-P03-005-01` | Phase 03 Exit Gate |
| `NFR-AI-004` | SQL Correctness >= 0.95, Unauthorized = 0 | `docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md` §1 | `TASK-P03-003` | `TC-P03-006` (`test_sql_capability_catalog_allowlist.py`) | `AC-004`, `AC-P03-003-01` | Phase 03 Exit Gate |
| `NFR-COST-001`| COGS Target <= $2.00, Hard Ceiling <= $5.00 | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §5 | `TASK-P03-001`, `TASK-P03-006` | `TC-P03-002` (`test_investigation_manifest_budget.py`) | `AC-012`, `AC-P03-001-02` | Phase 03 Exit Gate |
| `NFR-OBS-001`| Trace/Correlation/Causation ID Propagation | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §3 | `TASK-P03-001`, `TASK-P03-002` | `TC-P03-001` (`test_investigation_domain.py`) | `AC-012`, `AC-P03-001-01` | Phase 03 Exit Gate |
| `NFR-OBS-002`| 100% Sampling of Security Events | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §5 | `TASK-P03-003`, `TASK-P03-008` | `TC-P03-022` (`test_phase03_mutation_barrier.py`) | `AC-012`, `AC-P03-008-02` | Phase 03 Exit Gate |
| `NFR-PRV-001`| Secrets = 0, PII Masked/Redacted | `docs/06-agent-platform/TICKET-INTELLIGENCE-SPEC.md` §3 | `TASK-P03-007` | `TC-P03-016` (`test_ticket_dlp_redaction.py`) | `AC-010`, `AC-P03-007-01` | Phase 03 Exit Gate |
| `AC-003` | Typed DAG, Budgeted, Replayable, Cancellable| `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §4 | `TASK-P03-002`, `TASK-P03-006` | `TC-P03-003` (`test_investigation_workflow_replay.py`), `TC-P03-005` (`test_investigation_signals_queries.py`) | `AC-P03-002-01`, `AC-P03-006-01` | Phase 03 Exit Gate |
| `AC-004` | Every Hypothesis Links Supporting/Contradicting Evidence | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §6 | `TASK-P03-006` | `TC-P03-019` (`test_unsupported_claim_rejection.py`), `TC-P03-020` (`test_contradiction_detection.py`) | `AC-P03-006-02` | Phase 03 Exit Gate |
| `AC-005` | Retrieved Evidence Satisfies Tenant, ACL, Version, Dates | `docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md` §4, `docs/09-rag/RAG-SPEC.md` §2 | `TASK-P03-004`, `TASK-P03-005` | `TC-P03-011` (`test_evidence_tenant_isolation.py`), `TC-P03-012` (`test_evidence_effective_date.py`) | `AC-P03-004-02`, `AC-P03-005-01` | Phase 03 Exit Gate |
| `AC-013` | UI/API Exposes Decisions/Evidence Without Hidden CoT | `docs/06-agent-platform/MULTI-AGENT-SPEC.md` §1 | `TASK-P03-006` | `TC-P03-023` (`test_suppress_chain_of_thought.py`) | `AC-P03-006-01` | Phase 03 Exit Gate |

---

## Phase 04 — Hypothesis, Causal Analysis, and Verification Traceability Matrix

| Requirement / Invariant / NFR / AC | Contract / Component | Canonical Specification | Phase 04 Task | Exact Test Category | Acceptance Criterion | Phase 04 Exit Gate |
|---|---|---|---|---|---|---|
| `BR-001` | Competing Root Causes & Causal Attribution | `docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md` §1 | `TASK-P04-001`, `TASK-P04-005` | `TC-P04-003` (`test_competing_hypothesis_ranking.py`) | `AC-004`, `AC-P04-005-01` | Phase 04 Exit Gate |
| `BR-002` | Intervention Sizing & Loss Prevention | `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md` §1 | `TASK-P04-003`, `TASK-P04-004` | `TC-P04-016` (`test_causal_aipw_estimator.py`) | `AC-006`, `AC-P04-004-01` | Phase 04 Exit Gate |
| `FR-RCA-001` | Multi-Hypothesis Ranking & Decoy Refutation | `docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md` §3 | `TASK-P04-001`, `TASK-P04-005` | `TC-P04-003` (`test_competing_hypothesis_ranking.py`), `TC-P04-004` (`test_decoy_hypothesis_refutation.py`) | `AC-004`, `AC-P04-001-01` | Phase 04 Exit Gate |
| `FR-RCA-002` | Fallback to NEED_MORE_EVIDENCE on Gaps | `docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md` §3 | `TASK-P04-001`, `TASK-P04-002` | `TC-P04-005` (`test_need_more_evidence_fallback.py`) | `AC-004`, `AC-P04-001-02` | Phase 04 Exit Gate |
| `FR-ML-003` | Causal Feature Audit & Collider Exclusion | `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md` §2 | `TASK-P04-003` | `TC-P04-014` (`test_causal_collider_rejection.py`) | `AC-006`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `FR-ML-004` | Causal Estimand & AIPW Estimation | `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md` §2, §4 | `TASK-P04-003`, `TASK-P04-004` | `TC-P04-016` (`test_causal_aipw_estimator.py`), `TC-P04-019` (`test_causal_synthetic_ate_benchmark.py`) | `AC-006`, `AC-P04-004-01` | Phase 04 Exit Gate |
| `FR-EVD-001` | Evidence Provenance Binding in Hypotheses | `docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md` §2 | `TASK-P04-001`, `TASK-P04-002` | `TC-P04-002` (`test_hypothesis_evidence_binding.py`) | `AC-004`, `AC-P04-001-01` | Phase 04 Exit Gate |
| `FR-EVD-002` | Citation Span Match in Verified Claims | `docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md` §3 | `TASK-P04-002` | `TC-P04-008` (`test_claim_citation_match.py`) | `AC-004`, `AC-P04-002-01` | Phase 04 Exit Gate |
| `FR-EVD-003` | Rejection of Expired/Superseded Evidence | `docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md` §3 | `TASK-P04-002` | `TC-P04-009` (`test_unprovenanced_evidence_rejection.py`) | `AC-004`, `AC-P04-002-01` | Phase 04 Exit Gate |
| `INV-TEN-001`| Physical & Logical Isolation in Studies | `docs/15-security/SECURITY-ARCHITECTURE.md` §6 | `TASK-P04-001`, `TASK-P04-003` | `TC-P04-006` (`test_hypothesis_tenant_isolation.py`) | `AC-010`, `AC-P04-001-01` | Phase 04 Exit Gate |
| `INV-TEN-002`| Server-Derived Tenant Context Injection | `docs/15-security/SECURITY-ARCHITECTURE.md` §6 | `TASK-P04-003`, `TASK-P04-006` | `TC-P04-006` (`test_hypothesis_tenant_isolation.py`) | `AC-010`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `INV-TEN-003`| Explicit Context (Null Tenant Rejection) | `docs/15-security/SECURITY-ARCHITECTURE.md` §6 | `TASK-P04-003` | `TC-P04-006` (`test_hypothesis_tenant_isolation.py`) | `AC-010`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `INV-IAM-001`| Deny-By-Default Scope on Causal APIs | `docs/26-api/API-STANDARDS.md` §7 | `TASK-P04-003` | `TC-P04-013` (`test_causal_study_contract.py`) | `AC-008`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `INV-IAM-002`| Principal Context Audit Logging | `docs/26-api/API-STANDARDS.md` §7 | `TASK-P04-001`, `TASK-P04-003` | `TC-P04-001` (`test_hypothesis_domain.py`) | `AC-008`, `AC-P04-001-01` | Phase 04 Exit Gate |
| `INV-EVD-001`| Immutable Evidence Reference & Digest | `docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md` §2 | `TASK-P04-001`, `TASK-P04-002` | `TC-P04-009` (`test_unprovenanced_evidence_rejection.py`) | `AC-004`, `AC-P04-002-01` | Phase 04 Exit Gate |
| `INV-EVD-002`| Rejection of Superseded Clauses in Claims | `docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md` §3 | `TASK-P04-002` | `TC-P04-009` (`test_unprovenanced_evidence_rejection.py`) | `AC-004`, `AC-P04-002-01` | Phase 04 Exit Gate |
| `INV-DATA-001`| Temporal Anti-Leakage in Causal Covariates | `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md` §1 | `TASK-P04-002`, `TASK-P04-003` | `TC-P04-012` (`test_claim_temporal_leakage.py`), `TC-P04-014` (`test_causal_collider_rejection.py`) | `AC-001`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `INV-DATA-002`| Deterministic Dataset Snapshots for Replay | `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md` §2 | `TASK-P04-004`, `TASK-P04-006` | `TC-P04-022` (`test_causal_study_replay.py`) | `AC-001`, `AC-P04-006-01` | Phase 04 Exit Gate |
| `INV-AI-001` | Zero Unsupported Claims in Verified Hypotheses| `docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md` §1 | `TASK-P04-001`, `TASK-P04-002` | `TC-P04-008` (`test_claim_citation_match.py`), `TC-P04-010` (`test_correlation_causation_rejection.py`) | `AC-004`, `AC-P04-002-01` | Phase 04 Exit Gate |
| `INV-AI-002` | Study & Hypothesis Manifest Version Hashes | `docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md` §2 | `TASK-P04-001`, `TASK-P04-003` | `TC-P04-001` (`test_hypothesis_domain.py`), `TC-P04-013` (`test_causal_study_contract.py`) | `AC-011`, `AC-P04-001-01` | Phase 04 Exit Gate |
| `INV-AUD-001`| Immutable Outbox Domain Events | `docs/26-api/EVENT-CONTRACTS.md` §6 | `TASK-P04-003`, `TASK-P04-006` | `TC-P04-013` (`test_causal_study_contract.py`) | `AC-012`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `INV-AUD-002`| Audit Privacy (No Raw Token/PII Archiving)| `docs/15-security/SECURITY-ARCHITECTURE.md` §6 | `TASK-P04-003` | `TC-P04-013` (`test_causal_study_contract.py`) | `AC-012`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `INV-PRV-001`| Direct Identifiers Barred from Covariates | `docs/15-security/SECURITY-ARCHITECTURE.md` §6 | `TASK-P04-003` | `TC-P04-013` (`test_causal_study_contract.py`) | `AC-010`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `INV-REL-001`| Fail-Closed on Overlap & Security Flaws | `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md` §1 | `TASK-P04-004` | `TC-P04-015` (`test_causal_overlap_diagnostics.py`) | `AC-006`, `AC-P04-004-01` | Phase 04 Exit Gate |
| `INV-REL-002`| Phase 04 Exit Gate Sequential Verification | `docs/29-testing/TEST-STRATEGY.md` §9 | `TASK-P04-006` | `TC-P04-024` (`test_phase_04_exit_gate.py`) | `AC-P04-006-01`, `AC-P04-006-02` | Phase 04 Exit Gate |
| `NFR-AI-001` | 100% Artifacts Formally Version-Bound | `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md` §2 | `TASK-P04-003` | `TC-P04-013` (`test_causal_study_contract.py`) | `AC-011`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `NFR-AI-002` | RCA Top-1 >= 0.80, Top-3 >= 0.95 | `docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md` §3 | `TASK-P04-005` | `TC-P04-003` (`test_competing_hypothesis_ranking.py`) | `AC-004`, `AC-P04-005-01` | Phase 04 Exit Gate |
| `NFR-AI-007` | Synthetic Causal ATE Error <= 0.05 | `docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md` §3 | `TASK-P04-004`, `TASK-P04-005` | `TC-P04-019` (`test_causal_synthetic_ate_benchmark.py`) | `AC-006`, `AC-P04-005-01` | Phase 04 Exit Gate |
| `NFR-DUR-001`| Deterministic Bitwise Replay of Studies | `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md` §2 | `TASK-P04-006` | `TC-P04-022` (`test_causal_study_replay.py`) | `AC-001`, `AC-P04-006-01` | Phase 04 Exit Gate |
| `NFR-OBS-001`| Distributed Trace ID Propagation | `docs/26-api/API-STANDARDS.md` §7 | `TASK-P04-001`, `TASK-P04-003` | `TC-P04-001` (`test_hypothesis_domain.py`) | `AC-012`, `AC-P04-001-01` | Phase 04 Exit Gate |
| `NFR-OBS-002`| 100% Audit Logging of Verification Decisions| `docs/27-database/DATABASE-SCHEMA.md` §18 | `TASK-P04-002`, `TASK-P04-006` | `TC-P04-008` (`test_claim_citation_match.py`) | `AC-012`, `AC-P04-002-01` | Phase 04 Exit Gate |
| `NFR-PRV-001`| Masked Covariate Matrices (0 PII) | `docs/15-security/SECURITY-ARCHITECTURE.md` §6 | `TASK-P04-003` | `TC-P04-013` (`test_causal_study_contract.py`) | `AC-010`, `AC-P04-003-01` | Phase 04 Exit Gate |
| `NFR-TEN-001`| Zero Cross-Tenant Read/Write/Estimate Leakage| `docs/15-security/SECURITY-ARCHITECTURE.md` §6 | `TASK-P04-001`, `TASK-P04-003` | `TC-P04-006` (`test_hypothesis_tenant_isolation.py`) | `AC-010`, `AC-P04-006-01` | Phase 04 Exit Gate |
| `NFR-TEN-002`| Tenant Isolation Holds Under Concurrent Load | `docs/15-security/SECURITY-ARCHITECTURE.md` §6 | `TASK-P04-006` | `TC-P04-024` (`test_phase_04_exit_gate.py`) | `AC-010`, `AC-P04-006-01` | Phase 04 Exit Gate |
| `AC-004` | Every Hypothesis Links Supporting/Contradicting Evidence | `docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md` §2 | `TASK-P04-001`, `TASK-P04-002` | `TC-P04-002` (`test_hypothesis_evidence_binding.py`), `TC-P04-008` (`test_claim_citation_match.py`) | `AC-P04-001-01`, `AC-P04-002-01` | Phase 04 Exit Gate |
| `AC-006` | Estimand, SUTVA, Overlap, Uncertainty, Sensitivity Stated | `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md` §3 | `TASK-P04-003`, `TASK-P04-004` | `TC-P04-015` (`test_causal_overlap_diagnostics.py`), `TC-P04-018` (`test_causal_sensitivity_bounds.py`) | `AC-P04-003-01`, `AC-P04-004-01` | Phase 04 Exit Gate |
| `AC-014` | Distinct Measured vs Target Discipline | `docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md` §1 | `TASK-P04-005`, `TASK-P04-006` | `TC-P04-019` (`test_causal_synthetic_ate_benchmark.py`), `TC-P04-020` (`test_ground_truth_airgap_isolation.py`) | `AC-P04-005-01`, `AC-P04-006-02` | Phase 04 Exit Gate |

---

## Phase 05 — Churn, Uplift, and Decision Optimization Traceability Matrix

| Requirement / Invariant / NFR / AC | Contract / Component | Canonical Specification | Phase 05 Task | Exact Test Category | Acceptance Criterion | Phase 05 Exit Gate |
|---|---|---|---|---|---|---|
| `BR-002` | Intervention Sizing & Loss Prevention | `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md` §1 | `TASK-P05-003`, `TASK-P05-005` | `TC-P05-011` (`test_uplift_qini_benchmark.py`), `TC-P05-019` (`test_expected_utility_optimizer.py`) | `AC-007`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `BR-005` | Multi-Level Intervention Playbooks | `docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md` §1 | `TASK-P05-004`, `TASK-P05-005` | `TC-P05-014` (`test_budget_constraint_evaluation.py`) | `AC-007`, `AC-P05-004-01` | Phase 05 Exit Gate |
| `FR-ML-002` | Churn Probability Calibration | `docs/08-ml-platform/ML-SYSTEM-SPEC.md` §5.2 | `TASK-P05-001` | `TC-P05-002` (`test_probability_calibration.py`), `TC-P05-003` (`test_churn_ece_benchmark.py`) | `NFR-AI-005`, `AC-P05-001-01` | Phase 05 Exit Gate |
| `FR-ML-003` | Causal Decoupling from Baseline Risk | `docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md` §1.1 | `TASK-P05-003` | `TC-P05-009` (`test_uplift_score_contract.py`), `TC-P05-012` (`test_uplift_negative_effect_detection.py`) | `AC-006`, `AC-P05-003-01` | Phase 05 Exit Gate |
| `FR-ML-004` | Causal Estimand & Uplift Optimization | `docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md` §2 | `TASK-P05-003` | `TC-P05-011` (`test_uplift_qini_benchmark.py`) | `NFR-AI-006`, `AC-P05-003-01` | Phase 05 Exit Gate |
| `FR-DEC-001`| Constrained Decision Optimizer | `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md` §2, §3 | `TASK-P05-005` | `TC-P05-018` (`test_decision_pipeline_ordering.py`), `TC-P05-019` (`test_expected_utility_optimizer.py`) | `AC-007`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `INV-TEN-001`| Physical & Logical Isolation | `docs/27-database/DATABASE-SCHEMA.md` §19 | `TASK-P05-001`, `TASK-P05-004`, `TASK-P05-005` | `TC-P05-014` (`test_budget_constraint_evaluation.py`) | `AC-010`, `AC-P05-004-01` | Phase 05 Exit Gate |
| `INV-TEN-002`| Server-Derived Tenant Context | `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md` §2 | `TASK-P05-004`, `TASK-P05-005` | `TC-P05-018` (`test_decision_pipeline_ordering.py`) | `AC-010`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `INV-TEN-003`| Explicit Context (Null Rejection) | `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md` §2 | `TASK-P05-004` | `TC-P05-017` (`test_constraint_fail_closed.py`) | `AC-010`, `AC-P05-004-01` | Phase 05 Exit Gate |
| `INV-IAM-001`| Deny-By-Default Scope on APIs | `docs/26-api/API-STANDARDS.md` §8 | `TASK-P05-005` | `TC-P05-018` (`test_decision_pipeline_ordering.py`) | `AC-008`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `INV-IAM-002`| Principal Context Audit Logging | `docs/26-api/API-STANDARDS.md` §8 | `TASK-P05-001`, `TASK-P05-005` | `TC-P05-018` (`test_decision_pipeline_ordering.py`) | `AC-008`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `INV-AI-001` | Zero Unsupported / SHAP Claims | `docs/08-ml-platform/ML-SYSTEM-SPEC.md` §6.1 | `TASK-P05-002` | `TC-P05-007` (`test_shap_causation_rejection.py`) | `AC-004`, `AC-P05-002-01` | Phase 05 Exit Gate |
| `INV-AI-002` | Model & Decision Digest Hashes | `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md` §4 | `TASK-P05-001`, `TASK-P05-005` | `TC-P05-023` (`test_decision_digest_replay.py`) | `AC-011`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `INV-DATA-001`| Temporal Anti-Leakage in Features | `docs/08-ml-platform/ML-SYSTEM-SPEC.md` §5.1 | `TASK-P05-001` | `TC-P05-005` (`test_churn_temporal_leakage.py`) | `AC-001`, `AC-P05-001-01` | Phase 05 Exit Gate |
| `INV-DATA-002`| Deterministic Snapshot Replay | `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md` §4 | `TASK-P05-005`, `TASK-P05-006` | `TC-P05-023` (`test_decision_digest_replay.py`) | `AC-001`, `AC-P05-006-01` | Phase 05 Exit Gate |
| `INV-COST-001`| Daily Budget Ledger Inviolability | `docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md` §1.1 | `TASK-P05-004`, `TASK-P05-005` | `TC-P05-013` (`test_budget_ledger_concurrency.py`), `TC-P05-014` (`test_budget_constraint_evaluation.py`) | `NFR-COST-001`, `AC-P05-004-01` | Phase 05 Exit Gate |
| `INV-AUD-001`| Immutable Outbox Domain Events | `docs/26-api/EVENT-CONTRACTS.md` §7 | `TASK-P05-005` | `TC-P05-018` (`test_decision_pipeline_ordering.py`) | `AC-012`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `INV-AUD-002`| Audit Privacy (No Raw PII/Tokens) | `docs/15-security/SECURITY-ARCHITECTURE.md` §6 | `TASK-P05-002`, `TASK-P05-006` | `TC-P05-008` (`test_shap_pii_redaction.py`) | `AC-012`, `AC-P05-002-01` | Phase 05 Exit Gate |
| `INV-PRV-001`| Direct Identifiers Barred from Features| `docs/08-ml-platform/ML-SYSTEM-SPEC.md` §6.2 | `TASK-P05-002`, `TASK-P05-006` | `TC-P05-008` (`test_shap_pii_redaction.py`) | `AC-010`, `AC-P05-002-01` | Phase 05 Exit Gate |
| `INV-REL-001`| Fail-Closed on Constraint Flaws | `docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md` §1.1 | `TASK-P05-004` | `TC-P05-017` (`test_constraint_fail_closed.py`) | `AC-007`, `AC-P05-004-01` | Phase 05 Exit Gate |
| `INV-REL-002`| Phase 05 Exit Gate Sequential Verif | `docs/29-testing/TEST-STRATEGY.md` §10 | `TASK-P05-007` | `TC-P05-024` (`test_phase_05_exit_gate.py`) | `AC-P05-007-01` | Phase 05 Exit Gate |
| `NFR-AI-001` | 100% Artifacts Formally Version-Bound | `docs/19-ai-governance/AI-GOVERNANCE.md` §4 | `TASK-P05-001`, `TASK-P05-006` | `TC-P05-001` (`test_churn_model_contract.py`), `TC-P05-023` (`test_decision_digest_replay.py`) | `AC-011`, `AC-P05-006-01` | Phase 05 Exit Gate |
| `NFR-AI-005` | Churn Calibration ECE <= 0.05 | `docs/08-ml-platform/ML-SYSTEM-SPEC.md` §5.2 | `TASK-P05-001` | `TC-P05-003` (`test_churn_ece_benchmark.py`) | `NFR-AI-005`, `AC-P05-001-01` | Phase 05 Exit Gate |
| `NFR-AI-006` | Uplift Qini > 0.20 (Beats Random) | `docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md` §4 | `TASK-P05-003` | `TC-P05-011` (`test_uplift_qini_benchmark.py`) | `NFR-AI-006`, `AC-P05-003-01` | Phase 05 Exit Gate |
| `NFR-AI-007` | CATE Estimation Error <= 0.04 | `docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md` §4 | `TASK-P05-003` | `TC-P05-009` (`test_uplift_score_contract.py`) | `NFR-AI-007`, `AC-P05-003-01` | Phase 05 Exit Gate |
| `NFR-COST-001`| Zero Budget Overdraft Violations | `docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md` §1.1 | `TASK-P05-004`, `TASK-P05-005` | `TC-P05-013` (`test_budget_ledger_concurrency.py`), `TC-P05-014` (`test_budget_constraint_evaluation.py`) | `NFR-COST-001`, `AC-P05-004-01` | Phase 05 Exit Gate |
| `NFR-OBS-001`| Distributed Trace ID Propagation | `docs/26-api/API-STANDARDS.md` §8 | `TASK-P05-005` | `TC-P05-018` (`test_decision_pipeline_ordering.py`) | `AC-012`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `NFR-OBS-002`| 100% Audit Logging of Decisions | `docs/27-database/DATABASE-SCHEMA.md` §19 | `TASK-P05-005` | `TC-P05-018` (`test_decision_pipeline_ordering.py`) | `AC-012`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `NFR-PRV-001`| Masked Features & Redacted Explanations| `docs/08-ml-platform/ML-SYSTEM-SPEC.md` §6.2 | `TASK-P05-002`, `TASK-P05-006` | `TC-P05-008` (`test_shap_pii_redaction.py`) | `AC-010`, `AC-P05-002-01` | Phase 05 Exit Gate |
| `NFR-TEN-001`| Zero Cross-Tenant Read/Write Leakage | `docs/27-database/DATABASE-SCHEMA.md` §19 | `TASK-P05-001`, `TASK-P05-004` | `TC-P05-014` (`test_budget_constraint_evaluation.py`) | `AC-010`, `AC-P05-004-01` | Phase 05 Exit Gate |
| `NFR-TEN-002`| Tenant Isolation Under Concurrent Load| `docs/27-database/DATABASE-SCHEMA.md` §19 | `TASK-P05-004`, `TASK-P05-007` | `TC-P05-024` (`test_phase_05_exit_gate.py`) | `AC-010`, `AC-P05-007-01` | Phase 05 Exit Gate |
| `AC-006` | Uplift Overlap, SUTVA, and Bounds Stated | `docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md` §1 | `TASK-P05-003` | `TC-P05-010` (`test_uplift_overlap_diagnostics.py`) | `AC-006`, `AC-P05-003-01` | Phase 05 Exit Gate |
| `AC-007` | Hard Constraints Precede Utility Ranking | `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md` §1.1 | `TASK-P05-004`, `TASK-P05-005` | `TC-P05-018` (`test_decision_pipeline_ordering.py`) | `AC-007`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `AC-011` | Version-Bound Model & Decision Artifacts | `docs/19-ai-governance/AI-GOVERNANCE.md` §4 | `TASK-P05-001`, `TASK-P05-006` | `TC-P05-023` (`test_decision_digest_replay.py`) | `AC-011`, `AC-P05-006-01` | Phase 05 Exit Gate |
| `AC-012` | Full Provenance Linkage in Decisions | `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md` §4 | `TASK-P05-005` | `TC-P05-018` (`test_decision_pipeline_ordering.py`) | `AC-012`, `AC-P05-005-01` | Phase 05 Exit Gate |
| `AC-014` | Distinct Measured vs Target Discipline | `docs/11-decision-intelligence/FAIRNESS-SLICE-EVALUATION.md` §1 | `TASK-P05-006`, `TASK-P05-007` | `TC-P05-022` (`test_fairness_slice_evaluation.py`), `TC-P05-024` (`test_phase_05_exit_gate.py`) | `AC-014`, `AC-P05-007-01` | Phase 05 Exit Gate |

---

## Phase 06 — Approval and Safe Action Loop Traceability Matrix

| Canonical ID | Requirement Summary | Canonical Spec Source | Task Implementation | Automated Test / Eval Verification | Acceptance Invariant | Verification Gate |
|---|---|---|---|---|---|---|
| `FR-ACT-001` | Human Approval Request Creation | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §3.1 | `TASK-P06-001` | `TC-P06-001` (`test_approval_request_creation.py`) | `AC-008`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `FR-ACT-002` | Tiered Approval Authority & Signing | `docs/14-iam/IAM-SPEC.md` §7.1 | `TASK-P06-002` | `TC-P06-007` (`test_approval_tier_authority.py`) | `AC-008`, `AC-P06-002-01` | Phase 06 Exit Gate |
| `FR-ACT-003` | Action Dry-Run Simulation Mode | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.3 | `TASK-P06-003` | `TC-P06-012` (`test_dry_run_parity.py`), `TC-P06-013` (`test_dry_run_zero_side_effect.py`) | `AC-009`, `AC-P06-003-01` | Phase 06 Exit Gate |
| `FR-ACT-004` | Tool Gateway Governed Action Dispatch | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.1 | `TASK-P06-004` | `TC-P06-014` (`test_action_intent_idempotency.py`), `TC-P06-015` (`test_action_ledger_progression.py`) | `AC-008`, `AC-P06-004-01` | Phase 06 Exit Gate |
| `FR-CTL-001` | Continuous Multi-Point Policy Revalidation | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `TASK-P06-002` | `TC-P06-011` (`test_policy_revalidation_pipeline.py`) | `AC-008`, `AC-P06-002-01` | Phase 06 Exit Gate |
| `FR-CTL-002` | Multi-Tier Safety Kill Switches | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §5.1 | `TASK-P06-005` | `TC-P06-019` (`test_kill_switch_propagation.py`) | `INV-REL-001`, `AC-P06-005-01` | Phase 06 Exit Gate |
| `FR-CTL-003` | Saga Rollback and Compensation Protocol | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §10.1 | `TASK-P06-006` | `TC-P06-021` (`test_saga_compensation_flow.py`) | `AC-008`, `AC-P06-006-01` | Phase 06 Exit Gate |
| `FR-LRN-001` | Realized Action Outcome & ROI Capture | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §2 | `TASK-P06-007` | `TC-P06-026` (`test_action_outcome_measurement.py`) | `AC-014`, `AC-P06-007-01` | Phase 06 Exit Gate |
| `INV-ACT-001` | Strict Action Barrier (Mock Only) | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.1 | `TASK-P06-003`, `TASK-P06-004` | `TC-P06-013` (`test_dry_run_zero_side_effect.py`) | `INV-ACT-001`, `AC-P06-004-01` | Phase 06 Exit Gate |
| `INV-ACT-002` | Cryptographic Digest Binding | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `TASK-P06-001` | `TC-P06-002` (`test_approval_tamper_payload.py`), `TC-P06-003` (`test_approval_tamper_targets.py`) | `AC-008`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `INV-ACT-003` | Human-in-the-Loop / Agent Self-Appr Bar | `docs/14-iam/IAM-SPEC.md` §7.2 | `TASK-P06-002` | `TC-P06-009` (`test_agent_self_approval_block.py`) | `INV-ACT-003`, `AC-P06-002-01` | Phase 06 Exit Gate |
| `INV-ACT-004` | Immutable Action Ledger | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §3.3 | `TASK-P06-003` | `TC-P06-015` (`test_action_ledger_progression.py`) | `AC-008`, `AC-P06-003-01` | Phase 06 Exit Gate |
| `INV-IAM-001` | Valid Principal Context Binding | `docs/14-iam/IAM-SPEC.md` §7.1 | `TASK-P06-001`, `TASK-P06-002` | `TC-P06-007` (`test_approval_tier_authority.py`) | `INV-IAM-001`, `AC-P06-002-01` | Phase 06 Exit Gate |
| `INV-IAM-002` | Principal Identity Propagation | `docs/26-api/API-STANDARDS.md` §9 | `TASK-P06-001`, `TASK-P06-004` | `TC-P06-001` (`test_approval_request_creation.py`) | `INV-IAM-002`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `INV-TEN-001` | Strict Tenant Isolation in Approvals | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `TASK-P06-001`, `TASK-P06-002` | `TC-P06-008` (`test_approval_tenant_isolation.py`) | `INV-TEN-001`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `INV-TEN-002` | Tenant Context in Action Intents | `docs/27-database/DATABASE-SCHEMA.md` §20 | `TASK-P06-003` | `TC-P06-014` (`test_action_intent_idempotency.py`) | `INV-TEN-002`, `AC-P06-003-01` | Phase 06 Exit Gate |
| `INV-TEN-003` | Tenant-Scoped Ingestion & Storage | `docs/27-database/DATABASE-SCHEMA.md` §20 | `TASK-P06-003`, `TASK-P06-007` | `TC-P06-015` (`test_action_ledger_progression.py`) | `INV-TEN-003`, `AC-P06-003-01` | Phase 06 Exit Gate |
| `INV-WF-001` | Durable Saga Workflow Execution | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §10.1 | `TASK-P06-006` | `TC-P06-027` (`test_action_workflow_crash_recovery.py`) | `INV-WF-001`, `AC-P06-006-01` | Phase 06 Exit Gate |
| `INV-WF-002` | Deterministic Workflow Replay | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §10.1 | `TASK-P06-006` | `TC-P06-027` (`test_action_workflow_crash_recovery.py`) | `INV-WF-002`, `AC-P06-006-01` | Phase 06 Exit Gate |
| `INV-SEC-001` | Direct Agent Egress Barred | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.2 | `TASK-P06-004` | `TC-P06-018` (`test_agent_egress_containment.py`) | `INV-SEC-001`, `AC-P06-004-01` | Phase 06 Exit Gate |
| `INV-SEC-002` | Credential Broker Ephemeral Scoping | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.2 | `TASK-P06-004` | `TC-P06-016` (`test_credential_broker_scoping.py`) | `SEC-002`, `AC-P06-004-01` | Phase 06 Exit Gate |
| `INV-SEC-003` | Static Capability Whitelist | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.1 | `TASK-P06-004` | `TC-P06-018` (`test_agent_egress_containment.py`) | `SEC-003`, `AC-P06-004-01` | Phase 06 Exit Gate |
| `INV-AUD-001` | 100% Unsampled Audit Trail | `docs/22-billing/AUDIT-LOG-SPEC.md` §2 | `TASK-P06-007` | `TC-P06-025` (`test_action_event_contracts.py`) | `AC-012`, `AC-P06-007-01` | Phase 06 Exit Gate |
| `INV-AUD-002` | Secrets Scrubbed from Audit | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.2 | `TASK-P06-004`, `TASK-P06-007` | `TC-P06-017` (`test_scrub_secrets_from_ledger.py`) | `AC-012`, `AC-P06-004-01` | Phase 06 Exit Gate |
| `INV-COST-001`| Atomic Budget Reservation | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §3.1 | `TASK-P06-001`, `TASK-P06-005` | `TC-P06-020` (`test_blast_radius_enforcement.py`) | `NFR-COST-001`, `AC-P06-005-01` | Phase 06 Exit Gate |
| `INV-PRV-001`| PII Redaction in Approval Payloads | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §3.1 | `TASK-P06-001` | `TC-P06-001` (`test_approval_request_creation.py`) | `AC-010`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `INV-REL-001`| Rapid Kill Switch Propagation (< 500ms) | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §5.1 | `TASK-P06-005` | `TC-P06-019` (`test_kill_switch_propagation.py`) | `INV-REL-001`, `AC-P06-005-01` | Phase 06 Exit Gate |
| `INV-REL-002`| Phase 06 Composite Gate Exit | `docs/29-testing/TEST-STRATEGY.md` §11 | `TASK-P06-008` | `TC-P06-028` (`test_phase_06_exit_gate.py`) | `AC-P06-008-01` | Phase 06 Exit Gate |
| `NFR-SEC-001`| Strict Tenancy & Cryptographic Hashes | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `TASK-P06-001` | `TC-P06-002` (`test_approval_tamper_payload.py`) | `AC-008`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `NFR-SEC-002`| Zero Reusable Credential Exposure | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.2 | `TASK-P06-004` | `TC-P06-016` (`test_credential_broker_scoping.py`) | `SEC-002`, `AC-P06-004-01` | Phase 06 Exit Gate |
| `NFR-DUR-001`| Zero Action State Loss on Crash | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §10.1 | `TASK-P06-006`, `TASK-P06-008` | `TC-P06-027` (`test_action_workflow_crash_recovery.py`) | `NFR-DUR-001`, `AC-P06-008-01` | Phase 06 Exit Gate |
| `NFR-REL-001`| Zero Blind Retries on UNKNOWN | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §4.1 | `TASK-P06-006` | `TC-P06-023` (`test_unknown_blind_retry_prohibit.py`), `TC-P06-024` (`test_unknown_provider_reconciliation.py`) | `NFR-REL-001`, `AC-P06-006-01` | Phase 06 Exit Gate |
| `NFR-REL-002`| Idempotency Scope Integrity | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §3.2 | `TASK-P06-003` | `TC-P06-014` (`test_action_intent_idempotency.py`) | `NFR-REL-002`, `AC-P06-003-01` | Phase 06 Exit Gate |
| `NFR-TEN-001`| Zero Tenant Leakage in Approvals | `docs/27-database/DATABASE-SCHEMA.md` §20 | `TASK-P06-001`, `TASK-P06-003` | `TC-P06-008` (`test_approval_tenant_isolation.py`) | `AC-010`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `NFR-TEN-002`| Tenant Isolation Under Dispatch Load | `docs/27-database/DATABASE-SCHEMA.md` §20 | `TASK-P06-004`, `TASK-P06-008` | `TC-P06-028` (`test_phase_06_exit_gate.py`) | `AC-010`, `AC-P06-008-01` | Phase 06 Exit Gate |
| `NFR-AUD-001`| Immutable Audit History | `docs/22-billing/AUDIT-LOG-SPEC.md` §2 | `TASK-P06-007` | `TC-P06-025` (`test_action_event_contracts.py`) | `AC-012`, `AC-P06-007-01` | Phase 06 Exit Gate |
| `NFR-COST-001`| Zero Unallocated Spend Exceedance | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §5.2 | `TASK-P06-005` | `TC-P06-020` (`test_blast_radius_enforcement.py`) | `NFR-COST-001`, `AC-P06-005-01` | Phase 06 Exit Gate |
| `NFR-COST-002`| Cost Attribution by Action Intent | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §2 | `TASK-P06-007` | `TC-P06-026` (`test_action_outcome_measurement.py`) | `NFR-COST-002`, `AC-P06-007-01` | Phase 06 Exit Gate |
| `NFR-OBS-001`| Trace Context Linked Action Lifecycle | `docs/26-api/API-STANDARDS.md` §9 | `TASK-P06-004`, `TASK-P06-007` | `TC-P06-015` (`test_action_ledger_progression.py`) | `AC-012`, `AC-P06-004-01` | Phase 06 Exit Gate |
| `NFR-OBS-002`| Observability Dashboard Metrics | `docs/23-observability/OBSERVABILITY-SPEC.md` §2 | `TASK-P06-007` | `TC-P06-025` (`test_action_event_contracts.py`) | `AC-012`, `AC-P06-007-01` | Phase 06 Exit Gate |
| `NFR-PRV-001`| Masked Customer Identifiers in Ledger | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.2 | `TASK-P06-003`, `TASK-P06-004` | `TC-P06-017` (`test_scrub_secrets_from_ledger.py`) | `AC-010`, `AC-P06-003-01` | Phase 06 Exit Gate |
| `AC-008` | Cryptographic Digest & Human Signing | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `TASK-P06-001`, `TASK-P06-002` | `TC-P06-002` (`test_approval_tamper_payload.py`), `TC-P06-009` (`test_agent_self_approval_block.py`) | `AC-008`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `AC-009` | Dry-Run Parity & Mock Safe Dispatch | `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.3 | `TASK-P06-003`, `TASK-P06-004` | `TC-P06-012` (`test_dry_run_parity.py`), `TC-P06-013` (`test_dry_run_zero_side_effect.py`) | `AC-009`, `AC-P06-003-01` | Phase 06 Exit Gate |
| `AC-010` | Hard Tenant & Privacy Boundaries | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `TASK-P06-001`, `TASK-P06-004` | `TC-P06-008` (`test_approval_tenant_isolation.py`), `TC-P06-017` (`test_scrub_secrets_from_ledger.py`) | `AC-010`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `AC-011` | Version-Bound Action Artifacts | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §3.1 | `TASK-P06-001` | `TC-P06-001` (`test_approval_request_creation.py`) | `AC-011`, `AC-P06-001-01` | Phase 06 Exit Gate |
| `AC-012` | Full Provenance Linkage in Action Ledger | `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §3.3 | `TASK-P06-003`, `TASK-P06-007` | `TC-P06-015` (`test_action_ledger_progression.py`), `TC-P06-025` (`test_action_event_contracts.py`) | `AC-012`, `AC-P06-003-01` | Phase 06 Exit Gate |
| `AC-013` | Deterministic Saga Compensation on Failure | `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §10.1 | `TASK-P06-006` | `TC-P06-021` (`test_saga_compensation_flow.py`) | `AC-013`, `AC-P06-006-01` | Phase 06 Exit Gate |

---

## Phase 07 — Multi-Tenant Pilot, Connectors, and Tenant Operations Traceability Matrix

| Canonical ID | Requirement Summary | Canonical Spec Source | Task Implementation | Automated Test / Eval Verification | Acceptance Invariant | Verification Gate |
|---|---|---|---|---|---|---|
| `BR-004` | Operate Safely Across Tenants | `docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md` §1 | `TASK-P07-001`, `TASK-P07-008` | `TC-P07-006` (`test_cross_tenant_isolation_matrix.py`) | `INV-TEN-001`, `AC-P07-008-01` | Phase 07 Exit Gate |
| `BR-005` | Governed Operational Outcomes | `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §1 | `TASK-P07-005`, `TASK-P07-007` | `TC-P07-023` (`test_usage_attribution_integrity.py`) | `INV-COST-001`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `FR-CTL-001` | Propagate Trusted Tenant Context | `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §4 | `TASK-P07-001`, `TASK-P07-002` | `TC-P07-006` (`test_cross_tenant_isolation_matrix.py`) | `INV-TEN-002`, `AC-P07-001-01` | Phase 07 Exit Gate |
| `FR-CTL-002` | Multi-Dimensional Cost Attribution | `docs/21-finops/FINOPS-SPEC.md` §1.1 | `TASK-P07-007` | `TC-P07-023` (`test_usage_attribution_integrity.py`) | `NFR-COST-002`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `FR-CTL-003` | Tenant Lifecycle & No Orphan Data | `docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md` §3 | `TASK-P07-001` | `TC-P07-008` (`test_cascade_deletion_propagation.py`) | `INV-TEN-001`, `AC-P07-001-02` | Phase 07 Exit Gate |
| `FR-ACT-001` | Tool Gateway Governed Side Effects | `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §1.1 | `TASK-P07-004`, `TASK-P07-005` | `TC-P07-016` (`test_connector_secret_scrubbing.py`) | `INV-SEC-003`, `AC-P07-005-01` | Phase 07 Exit Gate |
| `FR-ACT-002` | Approval Digest Binding | `docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §4.2 | `TASK-P07-003` | `TC-P07-015` (`test_scim_deprovisioning_revocation.py`) | `INV-ACT-003`, `AC-P07-003-02` | Phase 07 Exit Gate |
| `FR-ACT-003` | Connector Idempotency & Rate Limits | `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §4 | `TASK-P07-005`, `TASK-P07-006` | `TC-P07-019` (`test_webhook_replay_deduplication.py`) | `NFR-REL-002`, `AC-P07-006-02` | Phase 07 Exit Gate |
| `FR-ACT-004` | Non-Reversible Action Isolation | `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §7 | `TASK-P07-005` | `TC-P07-017` (`test_connector_auth_expiry_handling.py`) | `INV-ACT-001`, `AC-P07-005-02` | Phase 07 Exit Gate |
| `FR-LRN-001` | Usage & Metering Horizon Capture | `docs/21-finops/FINOPS-SPEC.md` §3 | `TASK-P07-007` | `TC-P07-024` (`test_cost_reconciliation_protocol.py`) | `NFR-COST-002`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `FR-LRN-002` | Governed Release of Pilot Tenancy | `docs/24-sre/PILOT-ONBOARDING-AND-RECOVERY-SPEC.md` §1 | `TASK-P07-008` | `TC-P07-028` (`test_phase_07_exit_gate.py`) | `INV-REL-002`, `AC-P07-008-01` | Phase 07 Exit Gate |
| `INV-TEN-001` | Physical & Logical Storage Boundary | `docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md` §1.1 | `TASK-P07-001`, `TASK-P07-008` | `TC-P07-006` (`test_cross_tenant_isolation_matrix.py`) | `INV-TEN-001`, `AC-P07-008-01` | Phase 07 Exit Gate |
| `INV-TEN-002` | Server-Derived Identity Context | `docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §1.1 | `TASK-P07-002`, `TASK-P07-003` | `TC-P07-012` (`test_oidc_issuer_audience_mismatch.py`) | `INV-TEN-002`, `AC-P07-002-01` | Phase 07 Exit Gate |
| `INV-TEN-003` | Fail-Closed Privileged Operations | `docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md` §1.1 | `TASK-P07-001` | `TC-P07-002` (`test_partial_provisioning_blocked.py`) | `INV-TEN-003`, `AC-P07-001-01` | Phase 07 Exit Gate |
| `INV-IAM-001` | Deny-by-Default Boundary Auth | `docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §1.1 | `TASK-P07-002`, `TASK-P07-003` | `TC-P07-010` (`test_oidc_token_expiration.py`) | `INV-IAM-001`, `AC-P07-002-01` | Phase 07 Exit Gate |
| `INV-IAM-002` | Scoped Delegations Only | `docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §1.1 | `TASK-P07-002` | `TC-P07-013` (`test_oidc_token_replay.py`) | `INV-IAM-002`, `AC-P07-002-02` | Phase 07 Exit Gate |
| `INV-SEC-001` | Zero Raw Secrets in Agent Runtime | `docs/15-security/SECURITY-ARCHITECTURE.md` §7.1 | `TASK-P07-004` | `TC-P07-016` (`test_connector_secret_scrubbing.py`) | `INV-SEC-001`, `AC-P07-004-01` | Phase 07 Exit Gate |
| `INV-SEC-002` | Untrusted External Input Shield | `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §4.1 | `TASK-P07-006` | `TC-P07-018` (`test_webhook_signature_verification.py`) | `INV-SEC-002`, `AC-P07-006-01` | Phase 07 Exit Gate |
| `INV-SEC-003` | Connectors Read-Only; Egress Guard | `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §1.1 | `TASK-P07-005` | `TC-P07-017` (`test_connector_auth_expiry_handling.py`) | `INV-SEC-003`, `AC-P07-005-01` | Phase 07 Exit Gate |
| `INV-DATA-001` | Temporal Consistency (:as_of_time)| `docs/18-data-governance/DATA-GOVERNANCE.md` §1.1 | `TASK-P07-006` | `TC-P07-020` (`test_webhook_out_of_order_resolution.py`) | `INV-DATA-001`, `AC-P07-006-02` | Phase 07 Exit Gate |
| `INV-DATA-002` | Source System Authority & Quarantine| `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §1.1 | `TASK-P07-006` | `TC-P07-021` (`test_schema_drift_quarantine.py`) | `INV-DATA-002`, `AC-P07-006-02` | Phase 07 Exit Gate |
| `INV-AUD-001` | 100% Unsampled Operational Audit | `docs/22-billing/AUDIT-LOG-SPEC.md` §2.1 | `TASK-P07-007` | `TC-P07-025` (`test_audit_hash_chain_integrity.py`) | `INV-AUD-001`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `INV-AUD-002` | Privacy Redacted Audit Trails | `docs/18-data-governance/DATA-GOVERNANCE.md` §1.1 | `TASK-P07-007` | `TC-P07-025` (`test_audit_hash_chain_integrity.py`) | `INV-AUD-002`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `INV-COST-001` | Atomic Quota Spend Reservation | `docs/21-finops/FINOPS-SPEC.md` §1.1 | `TASK-P07-007` | `TC-P07-022` (`test_quota_atomic_reservation_race.py`) | `INV-COST-001`, `AC-P07-007-01` | Phase 07 Exit Gate |
| `INV-PRV-001` | PII Masking and Data Minimization | `docs/18-data-governance/DATA-GOVERNANCE.md` §2.1 | `TASK-P07-001`, `TASK-P07-007` | `TC-P07-007` (`test_tenant_export_isolation.py`) | `INV-PRV-001`, `AC-P07-001-02` | Phase 07 Exit Gate |
| `INV-REL-001` | Fail-Closed on Uncertainty | `docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md` §1.1 | `TASK-P07-004`, `TASK-P07-008` | `TC-P07-026` (`test_dependency_outage_fail_closed.py`) | `INV-REL-001`, `AC-P07-004-02` | Phase 07 Exit Gate |
| `INV-REL-002` | Composite Gate & Pilot Rehearsal | `docs/24-sre/PILOT-ONBOARDING-AND-RECOVERY-SPEC.md` §4 | `TASK-P07-008` | `TC-P07-028` (`test_phase_07_exit_gate.py`) | `INV-REL-002`, `AC-P07-008-01` | Phase 07 Exit Gate |
| `NFR-SEC-001` | Cryptographic Verification Standards | `docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §2.2 | `TASK-P07-002`, `TASK-P07-003` | `TC-P07-011` (`test_oidc_jwks_rotation.py`), `TC-P07-014` (`test_saml_signature_verification.py`) | `NFR-SEC-001`, `AC-P07-002-01` | Phase 07 Exit Gate |
| `NFR-SEC-002` | Zero Reusable Secret Exposure | `docs/15-security/SECURITY-ARCHITECTURE.md` §7.1 | `TASK-P07-004` | `TC-P07-016` (`test_connector_secret_scrubbing.py`) | `NFR-SEC-002`, `AC-P07-004-01` | Phase 07 Exit Gate |
| `NFR-REC-001` | RPO <= 5m and RTO <= 30m Recovery | `docs/24-sre/DR-PLAN.md` §1 | `TASK-P07-008` | `TC-P07-027` (`test_pilot_disaster_recovery_restore.py`) | `NFR-REC-001`, `AC-P07-008-02` | Phase 07 Exit Gate |
| `NFR-TEN-001` | Zero Cross-Tenant Data Leakage | `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §1.1 | `TASK-P07-001`, `TASK-P07-008` | `TC-P07-006` (`test_cross_tenant_isolation_matrix.py`) | `NFR-TEN-001`, `AC-P07-008-01` | Phase 07 Exit Gate |
| `NFR-TEN-002` | Isolation Preserved Under Peak Load| `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §1.1 | `TASK-P07-008` | `TC-P07-006` (`test_cross_tenant_isolation_matrix.py`) | `NFR-TEN-002`, `AC-P07-008-01` | Phase 07 Exit Gate |
| `NFR-AUD-001` | Immutable Cryptographic Audit Log | `docs/22-billing/AUDIT-LOG-SPEC.md` §1 | `TASK-P07-007` | `TC-P07-025` (`test_audit_hash_chain_integrity.py`) | `NFR-AUD-001`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `NFR-COST-001` | Zero Unallocated Spend Exceedance | `docs/21-finops/FINOPS-SPEC.md` §1.1 | `TASK-P07-007` | `TC-P07-022` (`test_quota_atomic_reservation_race.py`) | `NFR-COST-001`, `AC-P07-007-01` | Phase 07 Exit Gate |
| `NFR-COST-002` | >=99.5% Cost Attribution Precision | `docs/21-finops/FINOPS-SPEC.md` §1.1 | `TASK-P07-007` | `TC-P07-024` (`test_cost_reconciliation_protocol.py`) | `NFR-COST-002`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `NFR-OBS-001` | End-to-End Correlation Attributes | `docs/23-observability/OBSERVABILITY-SPEC.md` §2 | `TASK-P07-007` | `TC-P07-023` (`test_usage_attribution_integrity.py`) | `NFR-OBS-001`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `NFR-OBS-002` | 100% Audit Logging of Operations | `docs/23-observability/OBSERVABILITY-SPEC.md` §1 | `TASK-P07-007` | `TC-P07-025` (`test_audit_hash_chain_integrity.py`) | `NFR-OBS-002`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `NFR-PRV-001` | PII Masking and Secret Redaction | `docs/18-data-governance/DATA-GOVERNANCE.md` §2.1 | `TASK-P07-001`, `TASK-P07-007` | `TC-P07-007` (`test_tenant_export_isolation.py`) | `NFR-PRV-001`, `AC-P07-001-02` | Phase 07 Exit Gate |
| `NFR-PRV-002` | Explicit UNKNOWN for Retention/Residency| `docs/25-compliance/COMPLIANCE-READINESS.md` §1 | `TASK-P07-001` | `TC-P07-009` (`test_legal_hold_deletion_block.py`) | `NFR-PRV-002`, `AC-P07-001-02` | Phase 07 Exit Gate |
| `AC-009` | Dry-Run Parity & Mock Safe Connector | `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §1.1 | `TASK-P07-005` | `TC-P07-017` (`test_connector_auth_expiry_handling.py`) | `AC-009`, `AC-P07-005-01` | Phase 07 Exit Gate |
| `AC-010` | Hard Multi-Tenant Isolation Verification| `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §8 | `TASK-P07-001`, `TASK-P07-008` | `TC-P07-006` (`test_cross_tenant_isolation_matrix.py`) | `AC-010`, `AC-P07-008-01` | Phase 07 Exit Gate |
| `AC-011` | Version-Bound Connector Mappings | `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §2 | `TASK-P07-006` | `TC-P07-021` (`test_schema_drift_quarantine.py`) | `AC-011`, `AC-P07-006-02` | Phase 07 Exit Gate |
| `AC-012` | Full Provenance Linkage in Metering | `docs/21-finops/FINOPS-SPEC.md` §1.1 | `TASK-P07-007` | `TC-P07-023` (`test_usage_attribution_integrity.py`) | `AC-012`, `AC-P07-007-02` | Phase 07 Exit Gate |
| `Production Definition of Done`| Controlled Commercial Pilot Readiness Gate | `docs/24-sre/PILOT-ONBOARDING-AND-RECOVERY-SPEC.md` §1 | `TASK-P07-008` | `TC-P07-028` (`test_phase_07_exit_gate.py`) | `INV-REL-002`, `AC-P07-008-01` | Phase 07 Exit Gate |

---

## Phase 08 — Production Readiness, Release Governance & Operational Evidence Traceability Matrix

| Canonical ID | Requirement Summary | Canonical Spec Source | Task Implementation | Automated Test / Eval Verification | Acceptance Invariant | Verification Gate |
|---|---|---|---|---|---|---|
| `INV-TEN-001` | Hard Persistence & Derived Isolation | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001`, `TASK-P08-006` | `TC-P08-001` (`test_rls_concurrency_isolation.py`) | `INV-TEN-001`, `AC-P08-006-02` | Phase 08 Exit Gate |
| `INV-TEN-002` | Server-Derived Context Binding | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-001` (`test_rls_concurrency_isolation.py`) | `INV-TEN-002`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-TEN-003` | Fail-Closed Privileged Operations | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-008` (`test_agent_privilege_escalation.py`)| `INV-TEN-003`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-IAM-001` | Deny-by-Default Boundary Auth | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-002` | `TC-P08-002` (`test_session_active_invalidation.py`)| `INV-IAM-001`, `AC-P08-002-01` | Phase 08 Exit Gate |
| `INV-IAM-002` | Scoped Agent Delegation ($\le 24$h)| `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-008` (`test_agent_privilege_escalation.py`)| `INV-IAM-002`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-SEC-001` | Zero Raw Secrets in Runtime/Logs | `docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md` §9 | `TASK-P08-002` | `TC-P08-011` (`test_audit_pii_redaction.py`) | `INV-SEC-001`, `AC-P08-002-01` | Phase 08 Exit Gate |
| `INV-SEC-002` | Untrusted External Input Shield | `docs/20-evaluation/MODEL-RELEASE-PROCESS.md` §5.1 | `TASK-P08-004` | `TC-P08-023` (`test_golden_set_regression.py`) | `INV-SEC-002`, `AC-P08-004-01` | Phase 08 Exit Gate |
| `INV-SEC-003` | Read-Only Connector Egress Guard | `docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md` §5.2 | `TASK-P08-001` | `TC-P08-004` (`test_connector_egress_wall.py`) | `INV-SEC-003`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-ACT-001` | Tool Gateway Governed Side Effects | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-004` (`test_connector_egress_wall.py`) | `INV-ACT-001`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-ACT-002` | Cryptographic Approval Digest | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-007` (`test_approval_digest_tampering.py`)| `INV-ACT-002`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-ACT-003` | Agent Self-Approval Strict Block | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-008` (`test_agent_privilege_escalation.py`)| `INV-ACT-003`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-ACT-004` | Immutable Action Ledger | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-009` (`test_ledger_immutability.py`) | `INV-ACT-004`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-WF-001` | Deterministic Temporal Replay | `docs/30-deployment/RELEASE-CANARY-ROLLBACK-SPEC.md` §5 | `TASK-P08-003` | `TC-P08-005` (`test_temporal_sigkill_recovery.py`)| `INV-WF-001`, `AC-P08-003-01` | Phase 08 Exit Gate |
| `INV-WF-002` | Deterministic Saga Compensation | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-006` (`test_saga_reverse_compensation.py`)| `INV-WF-002`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-AI-001` | Pinned Model/Prompt Registry | `docs/20-evaluation/MODEL-RELEASE-PROCESS.md` §4 | `TASK-P08-004` | `TC-P08-022` (`test_prompt_registry_pinning.py`) | `INV-AI-001`, `AC-P08-004-02` | Phase 08 Exit Gate |
| `INV-AI-002` | Citation for Numerical Claims | `docs/20-evaluation/MODEL-RELEASE-PROCESS.md` §5.2 | `TASK-P08-004` | `TC-P08-012` (`test_citation_provenance.py`) | `INV-AI-002`, `AC-P08-004-01` | Phase 08 Exit Gate |
| `INV-EVD-001` | End-to-End Evidence Provenance | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-004` | `TC-P08-012` (`test_citation_provenance.py`) | `INV-EVD-001`, `AC-P08-004-01` | Phase 08 Exit Gate |
| `INV-EVD-002` | Immutable Investigation DAG | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-009` (`test_ledger_immutability.py`) | `INV-EVD-002`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-DATA-001` | Temporal Consistency (:as_of_time)| `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-013` (`test_future_dated_record_block.py`)| `INV-DATA-001`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-DATA-002` | Source Authority & Quarantine | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-027` (`test_schema_drift_quarantine.py`) | `INV-DATA-002`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `INV-AUD-001` | 100% Unsampled Audit Logging | `docs/25-compliance/COMPLIANCE-EVIDENCE-RUNBOOK.md` §5 | `TASK-P08-007` | `TC-P08-010` (`test_audit_stream_zero_drop.py`) | `INV-AUD-001`, `AC-P08-007-01` | Phase 08 Exit Gate |
| `INV-AUD-002` | Privacy Redacted Audit Trails | `docs/25-compliance/COMPLIANCE-EVIDENCE-RUNBOOK.md` §5 | `TASK-P08-007` | `TC-P08-011` (`test_audit_pii_redaction.py`) | `INV-AUD-002`, `AC-P08-007-02` | Phase 08 Exit Gate |
| `INV-COST-001` | Atomic Quota Spend Reservation | `docs/21-finops/FINOPS-SPEC.md` §1.1 | `TASK-P08-008` | `TC-P08-020` (`test_spend_atomic_race.py`) | `INV-COST-001`, `AC-P08-008-01` | Phase 08 Exit Gate |
| `INV-PRV-001` | PII Masking & Minimization | `docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md` §9 | `TASK-P08-002` | `TC-P08-011` (`test_audit_pii_redaction.py`) | `INV-PRV-001`, `AC-P08-002-01` | Phase 08 Exit Gate |
| `INV-REL-001` | Fail-Closed on Uncertainty | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §5 | `TASK-P08-001`, `TASK-P08-006` | `TC-P08-018` (`test_kill_switch_propagation.py`) | `INV-REL-001`, `AC-P08-006-01` | Phase 08 Exit Gate |
| `INV-REL-002` | Composite Gate & Pilot Rehearsal | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §1..§11 | `TASK-P08-008` | `TC-P08-028` (`test_phase_08_exit_gate.py`) | `INV-REL-002`, `AC-P08-008-01` | Phase 08 Exit Gate |
| `NFR-SEC-001` | Cryptographic Verification | `docs/25-compliance/COMPLIANCE-EVIDENCE-RUNBOOK.md` §5 | `TASK-P08-007` | `TC-P08-002` (`test_session_active_invalidation.py`)| `NFR-SEC-001`, `AC-P08-007-01` | Phase 08 Exit Gate |
| `NFR-SEC-002` | Zero Reusable Secret Exposure | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-003` (`test_secret_zero_downtime_rotation.py`)| `NFR-SEC-002`, `AC-P08-001-01`| Phase 08 Exit Gate |
| `NFR-DUR-001` | Durability under Worker Crash | `docs/30-deployment/RELEASE-CANARY-ROLLBACK-SPEC.md` §5 | `TASK-P08-003` | `TC-P08-005` (`test_temporal_sigkill_recovery.py`)| `NFR-DUR-001`, `AC-P08-003-01` | Phase 08 Exit Gate |
| `NFR-REL-001` | Blind Retry Prohibited on UNKNOWN | `docs/24-sre/INCIDENT-RESPONSE-RUNBOOK.md` §5 | `TASK-P08-008` | `TC-P08-006` (`test_saga_reverse_compensation.py`)| `NFR-REL-001`, `AC-P08-008-01` | Phase 08 Exit Gate |
| `NFR-REL-002` | Idempotency Scope Integrity | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-026` (`test_webhook_replay_deduplication.py`)| `NFR-REL-002`, `AC-P08-001-01`| Phase 08 Exit Gate |
| `NFR-TEN-001` | Zero Cross-Tenant Data Leakage | `docs/24-sre/PRODUCTION-READINESS-GATE.md` §9 | `TASK-P08-001` | `TC-P08-001` (`test_rls_concurrency_isolation.py`)| `NFR-TEN-001`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `NFR-TEN-002` | Peak Concurrency Isolation | `docs/29-testing/TEST-STRATEGY.md` §13 | `TASK-P08-006` | `TC-P08-001` (`test_rls_concurrency_isolation.py`)| `NFR-TEN-002`, `AC-P08-006-02` | Phase 08 Exit Gate |
| `NFR-AUD-001` | Immutable Cryptographic Audit Log | `docs/25-compliance/COMPLIANCE-EVIDENCE-RUNBOOK.md` §5 | `TASK-P08-007` | `TC-P08-010` (`test_audit_stream_zero_drop.py`) | `NFR-AUD-001`, `AC-P08-007-01` | Phase 08 Exit Gate |
| `NFR-COST-001` | Zero Unallocated Spend Exceedance | `docs/21-finops/FINOPS-SPEC.md` §5.2 | `TASK-P08-008` | `TC-P08-020` (`test_spend_atomic_race.py`) | `NFR-COST-001`, `AC-P08-008-01` | Phase 08 Exit Gate |
| `NFR-COST-002` | Multi-Dimensional Attribution | `docs/21-finops/FINOPS-SPEC.md` §1.1 | `TASK-P08-008` | `TC-P08-021` (`test_multidim_attribution.py`) | `NFR-COST-002`, `AC-P08-008-01` | Phase 08 Exit Gate |
| `NFR-PRV-001` | Sensitive Data Redaction | `docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md` §9 | `TASK-P08-002` | `TC-P08-011` (`test_audit_pii_redaction.py`) | `NFR-PRV-001`, `AC-P08-002-01` | Phase 08 Exit Gate |
| `NFR-PRV-002` | Explicit UNKNOWN for Retention/Residency| `docs/25-compliance/COMPLIANCE-READINESS.md` §1 | `TASK-P08-001` | `TC-P08-015` (`test_legal_hold_rejection.py`) | `NFR-PRV-002`, `AC-P08-001-01` | Phase 08 Exit Gate |
| `NFR-OBS-001` | End-to-End Correlation Attributes | `docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md` §6 | `TASK-P08-002` | `TC-P08-016` (`test_trace_correlation.py`) | `NFR-OBS-001`, `AC-P08-002-01` | Phase 08 Exit Gate |
| `NFR-OBS-002` | 100% Audit Logging of Operations | `docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md` §5 | `TASK-P08-002` | `TC-P08-017` (`test_telemetry_pipeline.py`) | `NFR-OBS-002`, `AC-P08-002-01` | Phase 08 Exit Gate |
| `NFR-AI-001` | Model/Prompt Registry Pinning | `docs/20-evaluation/MODEL-RELEASE-PROCESS.md` §4 | `TASK-P08-004` | `TC-P08-022` (`test_prompt_registry_pinning.py`) | `NFR-AI-001`, `AC-P08-004-02` | Phase 08 Exit Gate |
| `NFR-AI-002..007`| Golden Set Evaluation Gates | `docs/20-evaluation/MODEL-RELEASE-PROCESS.md` §5 | `TASK-P08-004` | `TC-P08-023` (`test_golden_set_regression.py`) | `NFR-AI-002..007`, `AC-P08-004-01`| Phase 08 Exit Gate |
| `AC-001..014` | Complete Platform Acceptance Matrix | `execution/DEFINITION-OF-DONE.md` §4 | `TASK-P08-008` | `TC-P08-028` (`test_phase_08_exit_gate.py`) | `AC-001..014`, `AC-P08-008-01` | Phase 08 Exit Gate |
| `Production Definition of Done`| Certified Production Readiness | `execution/DEFINITION-OF-DONE.md` §4 | `TASK-P08-008` | `TC-P08-028` (`test_phase_08_exit_gate.py`) | `INV-REL-002`, `AC-P08-008-01` | Phase 08 Exit Gate |

---

### Detailed Requirement-to-Evidence Lineage Mapping

| Requirement / Invariant | Design Control | Implementation Artifact | Test / Validation Suite | Evidence Artifact Required | Owner | Current Status | Blocking Gap |
|---|---|---|---|---|---|---|---|
| `INV-TEN-001` | PostgreSQL RLS + schema partition | `packages/backend/src/revpilot/modules/tenancy` | `tests/load/test_rls_concurrency_isolation.py` | `evidence/test-rls-concurrency-isolation.xml` | Tenancy Lead | PLANNED | Rails 3–5, Phase 06 not GREEN |
| `INV-IAM-001` | OIDC PKCE + token skew check | `packages/backend/src/revpilot/modules/iam/oidc` | `tests/security/test_session_active_invalidation.py` | `evidence/test-session-active-invalidation.xml` | IAM Lead | PLANNED | Rail 4 GREEN (TASK-R04-001..004 PASS); Rail 5 LOCKED |
| `INV-SEC-001` | Credential Broker short-lived token | `packages/backend/src/revpilot/modules/security/secrets` | `tests/privacy/test_audit_pii_redaction.py` | `evidence/test-audit-pii-redaction.xml` | Security Lead | PLANNED | Secret store provider UNKNOWN |
| `INV-ACT-001` | Tool Gateway mediated dispatches | `packages/backend/src/revpilot/modules/tool_gateway` | `tests/security/test_connector_egress_wall.py` | `evidence/test-connector-egress-wall.xml` | Action Lead | PLANNED | Phase 06 implementation pending |
| `INV-WF-001` | Temporal durable workflow history | `packages/backend/src/revpilot/modules/workflows` | `tests/recovery/test_temporal_sigkill_recovery.py` | `evidence/test-temporal-sigkill-recovery.xml` | Workflow Lead | PLANNED | Temporal cluster setup pending |
| `INV-AI-001` | Cryptographic prompt digest pinning | `packages/backend/src/revpilot/modules/ai_governance` | `tests/ai/test_prompt_registry_digest_pinning.py` | `evidence/test-prompt-registry-digest.xml` | AI Lead | PLANNED | Model evaluation pending |
| `INV-DATA-001` | Temporal query boundary `:as_of_time`| `packages/backend/src/revpilot/modules/data_platform` | `tests/data/test_future_dated_record_block.py` | `evidence/test-future-dated-block.xml` | Data Lead | PLANNED | Phase 01–02 store execution |
| `INV-AUD-001` | SHA-256 hash-chained audit ledger | `packages/backend/src/revpilot/modules/audit` | `tests/security/test_audit_stream_zero_drop.py` | `evidence/test-audit-stream-zero-drop.xml` | Audit Lead | PLANNED | Audit sink configuration |
| `INV-COST-001` | Atomic spend reservation lock | `packages/backend/src/revpilot/modules/finops` | `tests/finops/test_spend_atomic_race_condition.py` | `evidence/test-spend-atomic-race.xml` | FinOps Lead | PLANNED | Quota manager implementation |
| `INV-REL-001` | Cluster-wide kill-switch propagation | `packages/backend/src/revpilot/modules/operations` | `tests/recovery/test_kill_switch_propagation.py` | `evidence/test-kill-switch-propagation.xml` | SRE Lead | PLANNED | Phase 06 kill-switch code |
| `NFR-REC-001` | Cold restore PITR RPO $\le 5$m, RTO $\le 30$m| `packages/backend/src/revpilot/modules/operations/dr` | `tests/recovery/test_cold_restore_rehearsal.py` | `evidence/test-cold-restore-rehearsal.xml` | Storage Lead | NOT EXECUTED | Staging DR exercise drill |
