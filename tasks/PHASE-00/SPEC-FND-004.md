# SPEC-FND-004 — Define canonical repository topology

TASK_ID: SPEC-FND-004  
TITLE: Define canonical repository topology  
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
READINESS_SCORE: 19/20 — implementation-path existence remains 1/2 until bootstrap; all other dimensions 2/2  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
DEPENDS_ON: SPEC-FND-001, SPEC-ADR-001  
UNLOCKS: SPEC-FND-005  
PARALLEL_SAFE: YES — with unrelated ADR tasks; unique write set.

## Objective and why this exists

Define the future modular-monolith repository paths so Stage B can later name exact files without creating source code now.

## Canonical output and change boundary

CANONICAL OUTPUT / WRITE_SET / CREATE: `docs/04-system-architecture/REPOSITORY-TOPOLOGY.md`.  
READ_SET: glossary, `docs/04-system-architecture/SYSTEM-ARCHITECTURE.md`, `docs/31-adr/ADR-0001-application-architecture.md`.  
PROHIBITED_WRITE_SET: all other paths; creating application/package/infrastructure directories is forbidden.  
SPEC REFERENCES: ADR-0001 decision and implementation implications.

## Decision envelope

INPUT FACTS: Python/FastAPI backend, TypeScript/Next.js web, modular monolith, separate workload workers where justified.  
DECISIONS LOCKED: no microservices-first, no application code in this pass.  
QUESTIONS TO RESOLVE: exact future top-level paths, owner, allowed dependencies, prohibited dependencies, generated artifacts and test/config/script locations.  
MUST NOT REOPEN: framework or service-extraction decisions.

## Required content and controls

Specify a project-specific tree for `apps`, backend modules, web, workers, shared contracts, tests, infrastructure declarations, scripts, configuration, generated artifacts, docs/execution/tasks. Prevent secrets, generated output, and cross-module persistence access in the wrong areas.

## Verification and binary acceptance

COMMAND: `rg -n "^## |Purpose|Owner|Allowed dependencies|Prohibited dependencies|apps/|packages/|tests/|infra/|generated" docs/04-system-architecture/REPOSITORY-TOPOLOGY.md`. Expected exit 0.  
PASS only if every top-level area has purpose/owner/dependency rules, exact future paths are documented, no source directory is created, and topology matches ADR-0001.

## Expected report format

Task/status, output, verification, acceptance, unresolved bootstrap facts, deviations, unlocked IDs.
