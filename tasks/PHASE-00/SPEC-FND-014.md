# SPEC-FND-014 — Reconcile foundation risk register

TASK_ID: SPEC-FND-014  
TITLE: Reconcile foundation risk register  
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
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
DEPENDS_ON: SPEC-FND-003, SPEC-FND-008, SPEC-ADR-001, SPEC-ADR-002, SPEC-ADR-003, SPEC-ADR-004, SPEC-ADR-005, SPEC-ADR-006, SPEC-ADR-007, SPEC-ADR-008, SPEC-ADR-009, SPEC-ADR-010, SPEC-ADR-011  
UNLOCKS: SPEC-FND-016  
PARALLEL_SAFE: YES — disjoint write set.

## Objective and boundary

Link existing risks to their E01 mitigations and add only material foundation gaps. OUTPUT/WRITE/MODIFY: `execution/RISK-REGISTER.md`. READ: workload, invariants, ADRs, threat model. PROHIBITED WRITE: all other files.

## Required content

Preserve `RISK-001..012`. Add mitigation/evidence links and risks for unaccepted ADRs, unknown production provider/cloud/legal inputs, and lack of Git/tooling only if not already covered. Do not downgrade risk due proposed controls; implementation evidence is absent.

## Verification and acceptance

COMMAND: `rg -n "RISK-001|RISK-012|ADR-|UNKNOWN|Proposed|evidence" execution/RISK-REGISTER.md`. PASS only if all legacy IDs remain, new IDs are unique, treatments link to canonical artifacts, and no proposed control is called implemented.

## Expected report

Task/status, modified file, verification, added/preserved risk counts, deviations.
