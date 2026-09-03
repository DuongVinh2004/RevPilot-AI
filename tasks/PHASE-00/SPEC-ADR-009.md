# SPEC-ADR-009 — Decide secrets baseline and evolution

TASK_ID: SPEC-ADR-009  
TITLE: Decide secrets baseline and evolution  
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
REASONING_LOAD: HIGH — planner-only security ADR  
READINESS_SCORE: 20/20  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 1  
DEPENDS_ON: SPEC-FND-002, SPEC-FND-003  
UNLOCKS: SPEC-FND-008  
PARALLEL_SAFE: YES.

## Objective and change boundary

Define development, pilot, and enterprise secret/key handling without selecting a cloud prematurely. OUTPUT/WRITE/CREATE: `docs/31-adr/ADR-0009-secrets-and-keys.md`. READ: system boundaries, workload assumptions, threat model, `SEC-002`. PROHIBITED WRITE: all other files.

## Decision envelope

INPUT FACTS: agents never see reusable provider secrets; provider cloud unknown. LOCKED: Credential Broker/Tool Gateway, short-lived credentials where supported, no committed secrets. RESOLVE: local injection, production managed store, workload identity, rotation/audit/CMEK evolution. MUST NOT REOPEN: agent credential prohibition.

## Required content and controls

Select process-environment injection from an uncommitted developer secret source for local only; managed secret/key service plus workload identity for commercial environments; brokered scoped credentials for tools. Compare self-hosted Vault and cloud-native stores. Define rotation, revocation, cache, audit, outage fail-closed, tenant key and CMEK triggers.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0009|local|uncommitted|managed secret|workload identity|short-lived|CMEK|fail closed|Revisit Triggers" docs/31-adr/ADR-0009-secrets-and-keys.md`. PASS only if no literal secret path/value is introduced and all environments have explicit controls.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
