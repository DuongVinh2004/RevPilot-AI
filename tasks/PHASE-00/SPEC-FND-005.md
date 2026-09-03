# SPEC-FND-005 — Define modular-monolith module boundaries

TASK_ID: SPEC-FND-005  
TITLE: Define modular-monolith module boundaries  
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
COMPLEXITY: L  
REASONING_LOAD: HIGH — planner-only boundary design  
READINESS_SCORE: 18/20 — contracts and reasoning independence remain 1/2 pending detailed feature specs  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 1 — planner-only module ownership decision; never executor-queued  
DEPENDS_ON: SPEC-FND-002, SPEC-FND-004, SPEC-ADR-003  
UNLOCKS: SPEC-FND-006  
PARALLEL_SAFE: NO — consumes topology and agent boundary decisions.

## Objective and why this exists

Create one initial module ownership map without turning every capability into a runtime service.

## Canonical output and change boundary

CANONICAL OUTPUT / WRITE_SET / CREATE: `docs/04-system-architecture/MODULE-BOUNDARIES.md`.  
READ_SET: glossary, system boundaries, repository topology, system architecture, ADR-0001, ADR-0003.  
PROHIBITED_WRITE_SET: all other files.  
SPEC REFERENCES: plane boundaries, bounded contexts, agent orchestration ADR.

## Decision envelope

INPUT FACTS: candidate modules are identity, tenancy, investigations, evidence, analytics, retrieval, ML, decisions, policy, approvals, actions, connectors, audit, usage, billing, administration.  
DECISIONS LOCKED: logical modules do not imply deployables; Tool Gateway/action boundary and data ownership remain enforced.  
QUESTIONS TO RESOLVE: responsibility, data ownership, public ports, allowed/forbidden dependencies, events, and extraction candidacy.  
MUST NOT REOPEN: microservices-first or direct cross-module table access.

## Required content and controls

For each module define responsibility, owned data, public application/domain ports, produced/consumed events, allowed dependencies, forbidden dependencies, tenant enforcement role, security owner, and potential service-extraction trigger. Identify shared-kernel contents and keep it minimal.

## Verification and binary acceptance

COMMAND: `rg -n "Identity|Tenancy|Investigations|Evidence|Analytics|Retrieval|ML|Decisions|Policy|Approvals|Actions|Connectors|Audit|Usage|Billing|Administration" docs/04-system-architecture/MODULE-BOUNDARIES.md`. Expected exit 0.  
PASS only if all candidates are resolved, each data set has one owner, agent/action/credential boundaries remain intact, and no circular dependency is prescribed.

## Expected report format

Task/status, output, verification, accepted module count, unresolved contracts, acceptance, deviations, unlocked IDs.
