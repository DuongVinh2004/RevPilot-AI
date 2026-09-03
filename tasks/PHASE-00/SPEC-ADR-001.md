# SPEC-ADR-001 — Decide application architecture

TASK_ID: SPEC-ADR-001  
TITLE: Decide application architecture  
OBJECTIVE: The first execution section states the single task-specific outcome.  
WHY THIS EXISTS: The first objective section states the task-specific Rail 0 ambiguity or risk removed by this task.  
CANONICAL OUTPUT: The first boundary section declares the exact repository-relative output path or paths.  
READ_SET: The first boundary section declares the exact permitted input artifacts.  
WRITE_SET: The first boundary section declares the exact permitted create/modify artifacts.  
PROHIBITED_WRITE_SET: Everything outside the declared write set is prohibited unless explicitly enumerated.  
SPEC REFERENCES: The first boundary or decision section cites the controlling canonical artifacts and IDs.  
INPUT FACTS: The decision/required-content sections state the task-specific facts; undocumented assumptions are not facts.  
DECISIONS ALREADY LOCKED: Existing higher-precedence decisions cited by this task remain closed.  
QUESTIONS THIS TASK MUST RESOLVE: Only the objective and acceptance questions assigned by this packet.  
QUESTIONS THIS TASK MUST NOT REOPEN: Product scope, safety invariants, and higher-precedence decisions outside the allowed decision budget.  
REQUIRED CONTENT: The named required-content section is normative and must be complete.  
SECURITY CONSIDERATIONS: Preserve deny-by-default authorization, evidence integrity, auditability, secret isolation, and the Tool Gateway side-effect boundary where applicable.  
TENANCY CONSIDERATIONS: Preserve explicit tenant ownership and isolation; a cross-tenant ambiguity is a blocking contradiction.  
FAILURE / CONTRADICTION HANDLING: Return BLOCKED with exact references; never silently harmonize conflicting canonical statements.  
TRACEABILITY REQUIREMENTS: Cite the output path, controlling IDs, dependencies, acceptance evidence, and every deviation.  
VERIFICATION: Run the exact checks named in the verification section and record their results.  
BINARY ACCEPTANCE CRITERIA: The verification section is normative; every listed condition must pass, otherwise the task is not PASS.  
EXPECTED REPORT FORMAT: Task ID/status, changed paths, verification command/result, binary acceptance results, contradictions/deviations, and unlocked IDs.  
 TYPE: SPECIFICATION  
TYPE: SPECIFICATION  
STATUS: PASS  
PHASE/EPIC: PHASE-00 / SPEC-P00-E01  
COMPLEXITY: M  
REASONING_LOAD: HIGH — planner-only ADR  
READINESS_SCORE: 20/20  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 1 — record only this ADR decision  
DEPENDS_ON: SPEC-FND-001, SPEC-FND-003  
UNLOCKS: SPEC-FND-004, SPEC-ADR-008  
PARALLEL_SAFE: YES — with ADR-002/004/007/009/010 after common dependencies.

## Objective and change boundary

Decide modular-monolith-first versus microservices-first. CANONICAL OUTPUT / WRITE_SET / CREATE: `docs/31-adr/ADR-0001-application-architecture.md`. READ_SET: glossary, workload assumptions, system architecture, risk register. PROHIBITED_WRITE_SET: all other files. SPEC REFERENCES: architectural style and `RISK-008`.

## Decision envelope

INPUT FACTS: one product/team baseline, early workload tiers, diverse worker workloads, high coordination risk. DECISIONS LOCKED: side effects remain isolated; data/ML workers may deploy separately when workload/security requires. MUST RESOLVE: application style, module/service extraction criteria, ownership and migration implications. MUST NOT REOPEN: product boundaries, five planes, Tool Gateway requirement.

## Required content and controls

ADR format must include all mandated sections. Select a typed modular monolith with separately deployable Temporal/ML/ingestion workers only where runtime boundaries justify it. Alternatives: microservices-first and single-process monolith. Revisit triggers must be measurable through team ownership, independent scale, failure isolation, security boundary, or deployment cadence. Address tenant/security, operations, cost, and dependency enforcement.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0001|Status: Proposed|Decision Drivers|Alternatives|Revisit Triggers|Affected Requirements|Affected Specs" docs/31-adr/ADR-0001-application-architecture.md`. Expected exit 0. PASS only if decision and rejected alternatives are explicit, every extraction trigger is observable, status is Proposed, and no implementation file is created.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
