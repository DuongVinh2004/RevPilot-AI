# SPEC-ADR-011 — Decide AI provider abstraction

TASK_ID: SPEC-ADR-011  
TITLE: Decide AI provider abstraction  
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
READINESS_SCORE: 19/20 — production provider remains an owned UNKNOWN  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 1  
DEPENDS_ON: SPEC-FND-003, SPEC-ADR-003  
UNLOCKS: SPEC-FND-014  
PARALLEL_SAFE: YES.

## Objective and change boundary

Define a minimal hosted/local model-provider seam without premature universal abstraction. OUTPUT/WRITE/CREATE: `docs/31-adr/ADR-0011-ai-provider-abstraction.md`. READ: workload assumptions, agent boundary ADR, system boundaries, cost/security NFRs. PROHIBITED WRITE: all other files.

## Decision envelope

INPUT FACTS: tests need deterministic fake provider; deployments may use hosted or local models; exact production provider is unknown. LOCKED: models have no tool authority; requests/responses are version/cost/trace governed. RESOLVE: internal port, capability declaration, error/usage normalization, feature escape hatch, provider-selection blocker. MUST NOT REOPEN: agent/runtime or Tool Gateway boundaries.

## Required content and controls

Select a small RevPilot-owned model gateway interface with provider adapters and explicit capability metadata; avoid a lowest-common-denominator mega-interface. Require deterministic fake for tests. Production adapter choice remains `UNKNOWN` and blocks only its adapter task. Compare direct provider SDK coupling and external model gateway. Define timeout/retry, data residency, retention, cost and local-serving revisit triggers.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0011|model gateway|adapter|capabilit|deterministic fake|UNKNOWN|timeout|retention|Revisit Triggers" docs/31-adr/ADR-0011-ai-provider-abstraction.md`. PASS only if the interface boundary is deterministic without pretending a production provider was selected.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
