# SPEC-ADR-003 — Decide agent orchestration boundary

TASK_ID: SPEC-ADR-003  
TITLE: Decide agent orchestration boundary  
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
DEPENDS_ON: SPEC-FND-002, SPEC-ADR-002  
UNLOCKS: SPEC-FND-005, SPEC-ADR-011  
PARALLEL_SAFE: NO.

## Objective and change boundary

Define exactly where the agent runtime begins/ends and select its baseline orchestration approach. OUTPUT/WRITE/CREATE: `docs/31-adr/ADR-0003-agent-orchestration-boundary.md`. READ: system boundaries, durable ADR, system architecture, SRS. PROHIBITED WRITE: all other files.

## Decision envelope

INPUT FACTS: dynamic typed DAG, parallel read tasks, budgets, verification; Temporal owns durable state. LOCKED: agent has capabilities not credentials; writes remain outside agent runtime. RESOLVE: LangGraph versus custom runtime, persistence boundary, schemas, failure/escalation and abstraction seam. MUST NOT REOPEN: Temporal ownership or Tool Gateway path.

## Required content and controls

Select LangGraph behind a RevPilot-owned typed `AgentRuntime` port for reasoning subgraphs, with ephemeral/checkpoint-assist state only; Temporal remains authoritative. Compare custom DAG and framework-only orchestration. Define triggers to replace LangGraph if replay/version/eval/budget/tool restrictions cannot be enforced or abstraction leakage becomes material.

## Verification and acceptance

COMMAND: `rg -n "^# ADR-0003|LangGraph|AgentRuntime|Temporal|credential|Tool Gateway|Revisit Triggers" docs/31-adr/ADR-0003-agent-orchestration-boundary.md`. PASS only if ownership, allowed/denied capabilities, selected approach and triggers are deterministic.

## Expected report

Task/status, file, decision, verification, acceptance, deviations, unlocked IDs.
