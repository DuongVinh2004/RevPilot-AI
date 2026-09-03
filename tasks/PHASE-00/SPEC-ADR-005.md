# SPEC-ADR-005 — Decide tenant-isolation baseline and tiers

TASK_ID: SPEC-ADR-005  
TITLE: Decide tenant-isolation baseline and tiers  
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
REASONING_LOAD: HIGH — planner-only security ADR  
READINESS_SCORE: 20/20  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 1  
DEPENDS_ON: SPEC-FND-002, SPEC-FND-003, SPEC-ADR-004  
UNLOCKS: SPEC-ADR-006, SPEC-FND-008  
PARALLEL_SAFE: NO.

## Objective and change boundary

Select shared, dedicated, and regulated tenant isolation tiers. OUTPUT/WRITE/CREATE: `docs/31-adr/ADR-0005-tenant-isolation.md`. READ: system boundaries, workload assumptions, threat model, PostgreSQL ADR, `SEC-001`, `FR-CTL-001`. PROHIBITED WRITE: all other files.

## Decision envelope

INPUT FACTS: shared PostgreSQL+RLS baseline; dedicated schema/database/cluster possible. LOCKED: tenant context is server-derived; cross-tenant leakage zero tolerance. RESOLVE: tier rules and measurable promotion triggers for schema/database/region/key isolation. MUST NOT REOPEN: whether isolation is required.

## Required content and controls

Select shared PostgreSQL tables with RLS/composite tenant keys for baseline, dedicated database/vector partition for justified enterprise cases, dedicated cluster/key/region for regulated requirements. Cover caches, indexes, events, object storage, features, logs, exports. Include noisy-neighbor, contract/regulation, restore, residency and key-boundary triggers.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0005|shared|RLS|dedicated database|dedicated cluster|region|SEC-001|Revisit Triggers" docs/31-adr/ADR-0005-tenant-isolation.md`. PASS only if critical isolation decision is complete, fail-closed, testable, Proposed, and all tier triggers are explicit.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
