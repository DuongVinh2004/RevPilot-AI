# SPEC-FND-007 — Define specification authority and precedence

TASK_ID: SPEC-FND-007  
TITLE: Define specification authority and precedence  
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
READINESS_SCORE: 20/20 — every readiness dimension is 2/2  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
DEPENDS_ON: NONE  
UNLOCKS: SPEC-FND-014  
PARALLEL_SAFE: YES — with SPEC-FND-001.

## Objective and why this exists

Create a single conflict-resolution and ownership order that prevents tasks/comments from overriding architecture or security.

## Canonical output and change boundary

CANONICAL OUTPUT / WRITE_SET / CREATE: `docs/00-executive/SPECIFICATION-PRECEDENCE.md`.  
READ_SET: `docs/README.md`, implementation standards, rail system, task template.  
PROHIBITED_WRITE_SET: all other files.  
SPEC REFERENCES: documentation change rules and Architecture Deviation Protocol.

## Decision envelope

INPUT FACTS: user/system authority is external to repository; repository documents can conflict; accepted ADRs are immutable history.  
DECISIONS LOCKED: micro-task never silently overrides accepted architecture/security; conflicts block work.  
QUESTIONS TO RESOLVE: normative order, scope-specific precedence, status/version effect, conflict workflow, owner/approver matrix.  
MUST NOT REOPEN: rail admission thresholds.

## Required content and controls

Differentiate external governing instructions, accepted security invariants, accepted ADRs, canonical specs, feature specs, API/event schemas, task packets, code comments, and generated docs. Define Proposed/Accepted/Deferred/Superseded semantics and deviation workflow.

## Verification and binary acceptance

COMMAND: `rg -n "Authority|Accepted ADR|security invariant|canonical specification|micro-task|BLOCKED|Architecture Deviation" docs/00-executive/SPECIFICATION-PRECEDENCE.md`. Expected exit 0.  
PASS only if authority order is total for relevant artifacts, status/scope conflicts are resolved deterministically, and micro-task/code comments cannot override higher authority.

## Expected report format

Task/status, output, verification, acceptance, deviations, unlocked IDs.
