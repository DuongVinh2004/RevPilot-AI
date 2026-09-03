# Implementation Standards

Status: Proposed v0.2

Normative companion: `execution/MICRO-TASK-RAIL-SYSTEM.md`. If this file conflicts with that companion, execution stops and the conflict is resolved by the planning/architecture owner.

## Planning hierarchy

The only permitted hierarchy is `INITIATIVE -> PHASE -> EPIC -> FEATURE -> MICRO-TASK`. Only a `MICRO-TASK` with readiness score at least 18/20 may enter `execution/EXECUTOR-QUEUE.md`. Critical security, tenant-isolation, credential, approval, billing, or external-action tasks require 20/20. An epic, feature, wildcard task, or task that still permits an architectural choice must never be sent to Antigravity.

## Agent task contract

Every micro-task file must include the complete contract in `tasks/TASK-TEMPLATE.md`. Relevant fields may not be omitted; irrelevant fields are explicitly `NOT APPLICABLE` with a reason. Required metadata includes TYPE, STATUS, COMPLEXITY, REASONING_LOAD, READINESS_SCORE, NEW_ARCHITECTURAL_DECISIONS_ALLOWED, DEPENDS_ON, UNLOCKS, PARALLEL_SAFE, READ_SET, WRITE_SET, CREATE, MODIFY, DO_NOT_MODIFY, canonical spec anchors, exported symbols, inputs/outputs, error/security/data/API/event/Temporal/agent/model/RAG contracts as applicable, pre/postconditions, exact verification commands, binary acceptance criteria, and the executor result format.

Tasks list exact repository-relative files; no globs, broad directories, or unbounded refactors. Preferred size is one focused concern, 1–3 source files, and one test file or tightly related test set. An implementation agent may implement, test, debug, and locally refactor inside the declared write set. It may not change architecture, dependencies, security/tenancy semantics, acceptance criteria, public contracts, or business meaning. If a specified design is infeasible, it stops and returns the blocked/deviation contract defined in the rail system. No dependent task starts while a rail is RED.

## Two-stage generation

Stage A creates micro-tasked specification work. Stage B generates implementation micro-tasks only from accepted canonical specifications. Stage B cannot run ahead of Stage A. Exact source paths and symbols are unresolved until the canonical repository structure is accepted; any task lacking them remains outside the executor queue.

## Complexity and reasoning

- `XS`: one tiny schema, test, or configuration concern.
- `S`: one isolated implementation concern.
- `M`: one implementation plus tightly coupled tests.
- `L`: rare, single bounded concern; planner review required.
- `XL`: prohibited; split before execution.

`REASONING_LOAD` is LOW, MEDIUM, or HIGH. Executor tasks should be LOW/MEDIUM. HIGH requires decomposition or a stronger prescriptive contract. `NEW_ARCHITECTURAL_DECISIONS_ALLOWED` is always `0` for executable work.

## Readiness gate

Score each dimension 0–2: objective, dependencies, file boundary, contracts, failure behavior, security/tenancy, testability, verification, acceptance criteria, and reasoning independence. The score and rationale are planner-owned. A task below threshold is `DRAFT` or `BLOCKED`, never executable.

## Engineering invariants

- Tenant context is a typed server-created value, not a request string propagated by convention.
- Domain modules expose contracts; cross-module database access is prohibited unless documented.
- LLM/model/tool outputs are schema-validated untrusted inputs.
- Money uses explicit currency and decimal/fixed-point representation; timestamps are UTC with business timezone metadata.
- Every mutation has idempotency behavior and audit semantics.
- Every asynchronous boundary has correlation/causation IDs, retry class, timeout, dead-letter/reconciliation behavior, and compatibility version.
- Logs exclude credentials and minimize PII. Errors return stable codes and safe messages.
- Feature flags cannot weaken authorization or audit controls.

## Verification order

Format/lint -> unit -> module integration -> contract -> data/model/AI eval -> end-to-end -> security/tenant -> recovery/idempotency -> performance as proportional to risk. Verification commands must be exact and non-destructive. A passing test with missing required coverage is not acceptance.

## Change-boundary rule

Before execution, compare the repository with the task's preconditions and expected change set. After execution, report every created/modified file and reject unexplained writes. Shared write sets make tasks non-parallel-safe unless an explicit coordination contract says otherwise. Opportunistic cleanup, dependency upgrades, mass renames, infrastructure additions, and unrelated refactors are prohibited.
