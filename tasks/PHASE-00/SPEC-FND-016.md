# SPEC-FND-016 — Perform E01 consistency audit and Rail 0 assessment

TASK_ID: SPEC-FND-016  
TITLE: Perform E01 consistency audit and Rail 0 assessment  
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
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
DEPENDS_ON: SPEC-FND-006, SPEC-FND-007, SPEC-FND-008, SPEC-FND-009, SPEC-FND-010, SPEC-FND-011, SPEC-FND-012, SPEC-FND-013, SPEC-FND-014, SPEC-FND-015, SPEC-ADR-001, SPEC-ADR-002, SPEC-ADR-003, SPEC-ADR-004, SPEC-ADR-005, SPEC-ADR-006, SPEC-ADR-007, SPEC-ADR-008, SPEC-ADR-009, SPEC-ADR-010, SPEC-ADR-011  
UNLOCKS: SPEC-P00-E02, SPEC-P00-E03, SPEC-P00-E04 decomposition  
PARALLEL_SAFE: NO.

## Objective and boundary

Produce an evidence-based E01 consistency report and update Rail 0 without weakening gates. OUTPUT/WRITE: create `execution/RAIL-0-E01-CONSISTENCY-REPORT.md`; modify `execution/RAIL-STATUS.md`. READ: all canonical docs/ADRs/tasks/queues/graph. PROHIBITED WRITE: executor queue and application/infrastructure paths.

## Required content

Check terminology, IDs, ADRs, rails, technology, tenant/agent/workflow boundaries, topology, graph, traceability, risks, references, empty files/fences. Correcting unrelated documents requires a separate task; unresolved contradictions remain blockers. Rail 0 stays RED until all Foundation specs/ADRs are accepted, repository/tooling and verification commands exist, E02–E04/E05 finish, and no P0 contradiction remains.

## Verification and acceptance

COMMANDS: Markdown nonempty/fence check; JSON parse/unique/dependency/acyclic check; queue parity; reference existence; executor count 0. PASS only if report records exact evidence/blockers, Rail 0 remains accurate, and no implementation/Git/Antigravity action occurs.

## Expected report

Task/status, created/modified files, validation counts, Rail state/blockers, deviations, exact next legal tasks.
