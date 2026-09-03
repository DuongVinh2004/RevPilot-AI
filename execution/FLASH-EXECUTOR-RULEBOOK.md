# Gemini Flash Controlled Executor Rulebook

Status: Active  
Authority: Executor operating procedure. Subordinate to `docs/00-executive/SPECIFICATION-PRECEDENCE.md`, Accepted ADRs (ADR-0001..0011), Security Invariants (`INV-SEC-*`, `INV-TEN-*`, `INV-ACT-*`, etc.), Canonical Architecture Documents, and Canonical Task Graph (`execution/task-graph.json`).

## 1. Task Selection Rules

- Execute only one authorized task at a time.
- Select tasks only from the canonical queue/DAG (`execution/EXECUTOR-QUEUE.md` or approved DAG micro-task packet).
- Do not execute tasks merely because they seem useful.
- Do not execute blocked tasks.
- Do not bypass dependencies.
- Do not reopen completed tasks without authorization.

## 2. Read-Before-Write Rules

- Read all files in the task `READ_SET` completely before modifying any file.
- Confirm the task `WRITE_SET` and respect its exact repository-relative paths.
- Confirm the prohibited write set (`PROHIBITED_WRITE_SET`).
- Do not modify files outside the write set.
- Do not expand scope during execution.

## 3. Architecture Rules

- Do not make a new architectural decision (`NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0`).
- Do not select a different framework without authorization.
- Do not replace an Accepted ADR.
- Do not introduce an unapproved technology (no microservices, Kafka, Qdrant, OpenSearch, Kubernetes, Redis).
- Do not create a new module boundary.
- Do not create a new runtime service.
- Do not change tenant ownership semantics.

## 4. Evidence Rules

- Every claim must have verifiable machine evidence.
- Every successful command and its exact exit code must be recorded.
- Every failed command and its exact exit code must be recorded.
- A passing typecheck is not proof of functional correctness.
- A passing build is not proof of architectural compliance.
- A created file is not proof of task completion.
- Do not report `PASS` if any required acceptance condition is unverified.

## 5. Failure Rules

- Stop on ambiguity.
- Stop on contradiction.
- Stop on missing dependency.
- Stop on unauthorized scope expansion.
- Stop on destructive or irreversible operation.
- Stop if a required secret or environment value is missing.
- Stop if the expected toolchain cannot be verified.
- Never silently use a substitute.

## 6. Git Rules

- Do not initialize Git unless the selected canonical task explicitly authorizes it.
- Do not commit unless explicitly authorized by the selected task.
- Do not push.
- Do not create a pull request.
- Do not merge.
- Do not rebase.
- Do not reset.
- Do not stash.
- Do not alter `main`.

## 7. Communication Rules

The final report must distinguish and never collapse:
- `PASS`: All binary acceptance criteria objectively satisfied with recorded evidence.
- `PARTIAL`: Some acceptance criteria satisfied, but execution incomplete.
- `BLOCKED`: Precondition, dependency, or specification contradiction prevents execution.
- `NOT RUNNABLE`: Environment or prerequisite missing, preventing execution.
- `NOT VERIFIED`: Action taken but verification command could not run or prove completion.
