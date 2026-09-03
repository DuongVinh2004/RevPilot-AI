# SPEC-FND-011 — Reconcile canonical system architecture references

TASK_ID: SPEC-FND-011  
TITLE: Reconcile canonical system architecture references  
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
REASONING_LOAD: LOW  
READINESS_SCORE: 20/20  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
DEPENDS_ON: SPEC-FND-002, SPEC-FND-004, SPEC-FND-005, SPEC-FND-006, SPEC-ADR-001, SPEC-ADR-002, SPEC-ADR-003, SPEC-ADR-004, SPEC-ADR-005, SPEC-ADR-006, SPEC-ADR-007, SPEC-ADR-008, SPEC-ADR-009, SPEC-ADR-010, SPEC-ADR-011  
UNLOCKS: SPEC-FND-013, SPEC-FND-016  
PARALLEL_SAFE: YES — with SPEC-FND-010/012/014.

## Objective and boundary

Replace proposed technology ambiguity in the system architecture with canonical ADR/reference links. OUTPUT/WRITE/MODIFY: `docs/04-system-architecture/SYSTEM-ARCHITECTURE.md`. READ: all E01 architecture artifacts/ADRs. PROHIBITED WRITE: all other files.

## Decision envelope and required content

Preserve five planes and request flow. Add authoritative links to boundaries, workload, topology, modules, dependencies and ADRs; make status clear. LangGraph selection, outbox, pgvector/FTS, managed containers and other decisions must match ADR text. Do not mark ADRs Accepted. Unknown production provider/cloud remains UNKNOWN. Conflict returns BLOCKED.

## Verification and acceptance

COMMAND: `rg -n "ADR-0001|ADR-0011|SYSTEM-BOUNDARIES|REPOSITORY-TOPOLOGY|MODULE-BOUNDARIES|DEPENDENCY-RULES|WORKLOAD-ASSUMPTIONS" docs/04-system-architecture/SYSTEM-ARCHITECTURE.md`. PASS only if all references exist and no technology statement contradicts its ADR.

## Expected report

Task/status, modified file, verification, consistency result, deviations.
