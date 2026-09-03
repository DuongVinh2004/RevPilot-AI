# SPEC-ADR-007 — Decide messaging and event baseline

TASK_ID: SPEC-ADR-007  
TITLE: Decide messaging and event baseline  
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
DEPENDS_ON: SPEC-FND-003, SPEC-ADR-004  
UNLOCKS: SPEC-FND-014  
PARALLEL_SAFE: YES — with ADR-006.

## Objective and change boundary

Decide the pre-Kafka event delivery pattern and Kafka adoption triggers. OUTPUT/WRITE/CREATE: `docs/31-adr/ADR-0007-messaging-event-baseline.md`. READ: workload assumptions, PostgreSQL ADR, system architecture/data consistency. PROHIBITED WRITE: all other files.

## Decision envelope

INPUT FACTS: transactional events require consistency; initial-commercial event rate is moderate; replay/fan-out may grow. LOCKED: outbox first; consumers at-least-once/idempotent. RESOLVE: dispatcher/consumer baseline, durability/order/retry/DLQ, Kafka trigger. MUST NOT REOPEN: event versioning or idempotency.

## Required content and controls

Select PostgreSQL transactional outbox plus bounded background dispatcher and consumer inbox/dedup for MVP/pilot. Compare Kafka-first and managed queue. Trigger Kafka on sustained throughput/backlog, multiple independent consumer groups, long replay retention, partitioned ordering, connector ecosystem, and staffed operations—not aspiration.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0007|transactional outbox|dispatcher|at-least-once|Kafka|consumer|replay|Revisit Triggers" docs/31-adr/ADR-0007-messaging-event-baseline.md`. PASS only if the event baseline and numeric/observable adoption triggers are explicit.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
