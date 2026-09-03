# SPEC-FND-010 — Reconcile SRS foundation references

TASK_ID: SPEC-FND-010  
TITLE: Reconcile SRS foundation references  
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
DEPENDS_ON: SPEC-FND-003, SPEC-FND-008, SPEC-FND-009  
UNLOCKS: SPEC-FND-013, SPEC-FND-016  
PARALLEL_SAFE: YES — with SPEC-FND-011/012/014; disjoint write sets.

## Objective and why this exists

Make SRS point to the canonical workload, NFR, and invariant documents without duplicating or contradicting their values.

## Canonical output and boundary

CANONICAL OUTPUT / WRITE_SET / MODIFY: `docs/03-requirements/SRS.md`. READ_SET: workload assumptions, NFR baseline, invariant registry, SRS. PROHIBITED_WRITE_SET: all other files. SPEC REFERENCES: canonical precedence.

## Decision envelope and required content

INPUT FACTS: current SRS contains an old inline performance-assumption paragraph. LOCKED: IDs remain unchanged; canonical detailed values live in new files. MUST RESOLVE: replace duplicate assumptions with normative references and classification rule. MUST NOT REOPEN: requirement semantics/priority. Security/tenancy failures stay fail-closed. Contradictions return BLOCKED.

## Verification and acceptance

COMMAND: `rg -n "WORKLOAD-ASSUMPTIONS.md|NFR-BASELINE.md|INVARIANT-REGISTRY.md|measured" docs/03-requirements/SRS.md`. PASS only if links exist, inline figures are no longer competing canonical values, all original requirement IDs remain, and only SRS changes.

## Expected report

Task/status, modified file, verification, preserved-ID result, acceptance/deviations.
