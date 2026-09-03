# SPEC-FND-008 — Create foundational invariant registry

TASK_ID: SPEC-FND-008  
TITLE: Create foundational invariant registry  
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
READINESS_SCORE: 20/20 — every readiness dimension is 2/2  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
DEPENDS_ON: SPEC-FND-001, SPEC-FND-002, SPEC-ADR-002, SPEC-ADR-005, SPEC-ADR-009  
UNLOCKS: SPEC-FND-009, SPEC-FND-013  
PARALLEL_SAFE: YES — after dependencies, unique write set.

## Objective and why this exists

Create a human/machine-readable registry of foundational invariants with owners, impacts, enforcement, and future proof tests.

## Canonical output and change boundary

CANONICAL OUTPUT / WRITE_SET / CREATE: `docs/03-requirements/INVARIANT-REGISTRY.md`.  
READ_SET: glossary, SRS, system boundaries, threat model, relevant ADRs, acceptance criteria.  
PROHIBITED_WRITE_SET: every other file.  
SPEC REFERENCES: `SEC-001..010`, root product invariant, architecture acceptance criteria.

## Decision envelope

INPUT FACTS: tenant isolation, deny-by-default, no agent secrets, Tool Gateway-only effects, approval binding, idempotency/reconciliation, durable workflow, evidence verification, cost limits, safe logging.  
DECISIONS LOCKED: these are non-negotiable and cannot be feature-flag-disabled.  
QUESTIONS TO RESOLVE: stable invariant IDs, owner, scope, rationale, violation impact, enforcement point, test/evidence, fail behavior.  
MUST NOT REOPEN: whether invariants apply.

## Required content and controls

Include `INV-TEN`, `INV-IAM`, `INV-SEC`, `INV-ACT`, `INV-WF`, `INV-AI`, `INV-EVD`, `INV-DATA`, `INV-AUD`, `INV-COST`, `INV-PRV`, and `INV-REL` families. Distinguish design evidence from future implementation evidence.

## Verification and binary acceptance

COMMAND: `rg -n "INV-(TEN|IAM|SEC|ACT|WF|AI|EVD|DATA|AUD|COST|PRV|REL)-" docs/03-requirements/INVARIANT-REGISTRY.md`. Expected exit 0.  
PASS only if every security objective and product invariant maps to at least one registry row, each row contains all required fields, and no row claims implementation proof.

## Expected report format

Task/status, output, verification, invariant count, trace coverage, acceptance, deviations, unlocked IDs.
