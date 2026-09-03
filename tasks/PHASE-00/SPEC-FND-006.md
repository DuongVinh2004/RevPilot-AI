# SPEC-FND-006 — Define enforceable dependency rules

TASK_ID: SPEC-FND-006  
TITLE: Define enforceable dependency rules  
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
REASONING_LOAD: MEDIUM  
READINESS_SCORE: 19/20 — exact lint tool remains 1/2 until repository bootstrap  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
DEPENDS_ON: SPEC-FND-005  
UNLOCKS: SPEC-FND-014  
PARALLEL_SAFE: NO.

## Objective and why this exists

Define dependency directions and forbidden edges so module boundaries are enforceable later.

## Canonical output and change boundary

CANONICAL OUTPUT / WRITE_SET / CREATE: `docs/04-system-architecture/DEPENDENCY-RULES.md`.  
READ_SET: repository topology, module boundaries, system boundaries, ADR-0001, ADR-0003.  
PROHIBITED_WRITE_SET: all other files.  
SPEC REFERENCES: `docs/04-system-architecture/MODULE-BOUNDARIES.md`.

## Decision envelope

INPUT FACTS: presentation -> application -> domain; infrastructure implements ports; cross-module access uses published contracts.  
DECISIONS LOCKED: no business logic in controllers, no direct agent external calls, no credentials in agent runtime, no tenant bypass.  
QUESTIONS TO RESOLVE: allowed layer/module edges, event/port usage, lint/test enforcement candidates.  
MUST NOT REOPEN: module ownership.

## Required content and controls

Provide layer rule matrix, inter-module dependency matrix, forbidden examples, event/transaction boundaries, and future automated enforcement approach. Undefined edges are forbidden. Fail build on detected circular/forbidden dependencies once tooling exists.

## Verification and binary acceptance

COMMAND: `rg -n "Presentation|Application|Domain|Infrastructure|FORBIDDEN|circular|tenant|credential|Tool Gateway|enforcement" docs/04-system-architecture/DEPENDENCY-RULES.md`. Expected exit 0.  
PASS only if every allowed direction is explicit, required forbidden edges are named, and at least one enforceable check is proposed per rule class without choosing unapproved tooling.

## Expected report format

Task/status, output, verification, rule counts, acceptance, deviations, unlocked IDs.
