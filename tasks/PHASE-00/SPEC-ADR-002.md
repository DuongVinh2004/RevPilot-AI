# SPEC-ADR-002 — Decide durable execution ownership

TASK_ID: SPEC-ADR-002  
TITLE: Decide durable execution ownership  
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
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 1  
DEPENDS_ON: SPEC-FND-001, SPEC-FND-003  
UNLOCKS: SPEC-ADR-003, SPEC-FND-008  
PARALLEL_SAFE: YES.

## Objective and change boundary

Decide ownership of multi-day, retryable, approval-waiting business workflows. OUTPUT/WRITE/CREATE: `docs/31-adr/ADR-0002-durable-execution.md`. READ: glossary, system architecture, SRS, workload assumptions, `FR-INV-003`, `NFR-REL-001`. PROHIBITED WRITE: all other files.

## Decision envelope

INPUT FACTS: workflows wait for approval, survive process loss, and must prevent duplicate effects. LOCKED: Temporal is outer workflow; agent runtime does not own durable business state. RESOLVE: Temporal responsibilities, activity boundary, determinism/versioning, alternatives and triggers. MUST NOT REOPEN: direct in-memory-only durable state.

## Required content and controls

Select Temporal for durable business orchestration; isolate nondeterminism and model/tool calls in activities. Compare database state machine/queue orchestration and agent-runtime persistence. Include timeout/retry/cancellation/compensation implications and provider operational risk. Revisit only on proven unmet requirement or unacceptable operational constraint, not preference.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0002|Temporal|determin|activit|Alternatives|Revisit Triggers|FR-INV-003|NFR-REL-001" docs/31-adr/ADR-0002-durable-execution.md`. PASS only if ownership boundary and failure semantics are explicit, status Proposed, and no runtime code exists.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
