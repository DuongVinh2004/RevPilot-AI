# SPEC-ADR-008 — Decide deployment baseline

TASK_ID: SPEC-ADR-008  
TITLE: Decide deployment baseline  
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
DEPENDS_ON: SPEC-FND-003, SPEC-ADR-001  
UNLOCKS: SPEC-FND-014  
PARALLEL_SAFE: YES.

## Objective and change boundary

Decide container/deployment baseline and Kubernetes adoption triggers. OUTPUT/WRITE/CREATE: `docs/31-adr/ADR-0008-deployment-baseline.md`. READ: workload assumptions, application architecture ADR, roadmap, SRE risks. PROHIBITED WRITE: all other files.

## Decision envelope

INPUT FACTS: local development and initial commercial deployment; no multi-region/mesh requirement. LOCKED: Kubernetes deferred. RESOLVE: local/pilot baseline, environment parity, scaling/failure/ownership triggers. MUST NOT REOPEN: no infrastructure implementation in Stage A.

## Required content and controls

Select OCI containers, local composition for development, and provider-neutral managed container execution for initial commercial deployments, with managed data services. Compare Kubernetes-first and VM deployment. Trigger Kubernetes on measured independent scaling/scheduling/network-policy/availability needs plus operational staffing; provider selection remains separately owned.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0008|OCI|local|managed container|Kubernetes|operational ownership|Revisit Triggers" docs/31-adr/ADR-0008-deployment-baseline.md`. PASS only if Kubernetes remains deferred and adoption requires measurable need and ownership.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
