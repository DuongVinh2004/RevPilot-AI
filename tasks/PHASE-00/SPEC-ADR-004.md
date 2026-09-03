# SPEC-ADR-004 — Decide primary relational persistence

TASK_ID: SPEC-ADR-004  
TITLE: Decide primary relational persistence  
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
COMPLEXITY: S  
REASONING_LOAD: MEDIUM  
READINESS_SCORE: 20/20  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 1  
DEPENDS_ON: SPEC-FND-001, SPEC-FND-003  
UNLOCKS: SPEC-ADR-005, SPEC-ADR-006, SPEC-ADR-007  
PARALLEL_SAFE: YES.

## Objective and change boundary

Select the authoritative transactional persistence baseline. OUTPUT/WRITE/CREATE: `docs/31-adr/ADR-0004-primary-relational-persistence.md`. READ: domain model, workload assumptions, system architecture. PROHIBITED WRITE: all other files.

## Decision envelope

INPUT FACTS: relational aggregates, RLS, outbox, audit metadata, transactional consistency. LOCKED: investigation/action state needs a transactional source of truth. RESOLVE: PostgreSQL versus alternative relational/document stores and separation from derived indexes. MUST NOT REOPEN: tenant enforcement or evidence versioning.

## Required content and controls

Select PostgreSQL. State transactional ownership, migration/backup implications, extension policy, connection isolation, and triggers for read replicas/partitioning/dedicated databases. Compare MySQL and document-store-first. Do not conflate PostgreSQL with object/vector/search stores.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0004|PostgreSQL|source of truth|Alternatives|RLS|outbox|Revisit Triggers" docs/31-adr/ADR-0004-primary-relational-persistence.md`. PASS only if authoritative data scope and alternatives/triggers are explicit.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
