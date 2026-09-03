# SPEC-ADR-010 — Decide observability baseline

TASK_ID: SPEC-ADR-010  
TITLE: Decide observability baseline  
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
READINESS_SCORE: 20/20  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 1  
DEPENDS_ON: SPEC-FND-002, SPEC-FND-003  
UNLOCKS: SPEC-FND-009  
PARALLEL_SAFE: YES.

## Objective and change boundary

Define minimum traces, metrics, logs, AI attribution, and redaction baseline. OUTPUT/WRITE/CREATE: `docs/31-adr/ADR-0010-observability-baseline.md`. READ: boundaries, workload assumptions, threat model, `NFR-OBS-001`, `NFR-PRV-001`. PROHIBITED WRITE: all other files.

## Decision envelope

INPUT FACTS: cross-plane investigations require correlation; raw prompts/evidence may contain PII/secrets. LOCKED: OpenTelemetry, structured logs, no chain-of-thought, safe logging. RESOLVE: telemetry standard, collectors/backends boundary, required identifiers, sampling/redaction and outage behavior. MUST NOT REOPEN: audit versus operational trace separation.

## Required content and controls

Select OpenTelemetry semantic instrumentation and vendor-neutral collector/export; structured application logs/metrics/traces; separate AI eval/artifact metadata. Compare direct vendor SDK and logs-only. Define mandatory correlation fields, forbidden payloads, cardinality budgets, security event sampling prohibition, local baseline and backend revisit triggers.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0010|OpenTelemetry|structured|redact|PII|cardinality|sampling|chain-of-thought|Revisit Triggers" docs/31-adr/ADR-0010-observability-baseline.md`. PASS only if minimum signals and prohibited data are explicit and backend lock-in is avoided.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
