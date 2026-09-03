# Antigravity Micro-Task Rail System

Status: Proposed v0.1  
Authority: Normative execution policy for RevPilot AI

## Purpose and invariant

The planning model absorbs architectural complexity. Antigravity receives one small, deterministic implementation packet at a time. An executable task is valid only when a competent fast coding model can complete it without making a behaviorally significant architectural decision.

`NEW_ARCHITECTURAL_DECISIONS_ALLOWED` MUST equal `0`.

If architecture, failure behavior, security, tenancy, contracts, tests, or acceptance must be inferred, the task is not ready.

## Hierarchy and lifecycle

```text
INITIATIVE
  PHASE
    EPIC
      FEATURE
        MICRO-TASK -> only this level may enter EXECUTOR-QUEUE
```

Micro-task status is one of:

- `DRAFT`: incomplete contract or score below threshold.
- `READY`: score threshold met, dependencies satisfied, and queued by planner.
- `IN_PROGRESS`: leased to one executor run.
- `PASS`: all binary acceptance conditions verified.
- `FAIL`: implementation or verification failed; rail is RED.
- `BLOCKED`: repository reality contradicts a precondition/specification.
- `SUPERSEDED`: retained historical ID with exact replacement IDs.

IDs are immutable and never reused.

## Rail sequence

| Rail | Scope | Entry gate | Exit gate |
|---|---|---|---|
| 0 | Repository and tooling foundation | Phase 00 specifications accepted | Build/test/typecheck/doc validation commands exist and pass |
| 1 | Core domain primitives | Rail 0 green | IDs, money, time, errors, tenant primitives pass contracts |
| 2 | Tenant context | Rail 1 green | Missing/malformed/unauthorized tenant fails closed |
| 3 | Authentication | Rail 2 green | Trusted principal creation and session/token negative tests pass |
| 4 | Authorization/delegation | Rail 3 green | RBAC/ABAC and agent delegation matrix pass |
| 5 | Persistence isolation | Rail 4 green | RLS and cross-tenant negative matrix pass |
| 6 | Investigation domain | Rail 5 green | State and evidence ownership invariants pass |
| 7 | Temporal foundation | Rail 6 green | Replay, retry, cancellation, pause/resume tests pass |
| 8 | Evidence system | Rails 6–7 green | Provenance/version/effective-date/ACL contracts pass |
| 9 | RAG foundation | Rail 8 green | Hybrid retrieval and cross-tenant/citation eval gates pass |
| 10 | Analytics and anomaly | Rail 6 green | Metric semantics and seeded backtest gates pass |
| 11 | Agent planning/verification | Rails 7–10 green | DAG/tool/budget/unsupported-claim evals pass |
| 12 | Causal/ML/uplift | Data and eval specs accepted | Calibration, leakage, causal/uplift gates pass |
| 13 | Decision intelligence | Rails 11–12 green | Hard constraints precede utility ranking |
| 14 | Policy and approval | Rails 4, 7, 13 green | Digest/tamper/replay/authority gates pass |
| 15 | Action safety/tool gateway | Rail 14 green | Dry-run, idempotency, unknown-result, blast and kill tests pass |
| 16 | Connectors/outcomes | Rails 5, 15 green | Auth expiry, webhook, drift, reconciliation tests pass |
| 17 | Observability/FinOps/audit | Cross-cutting foundations exist | Attribution, redaction, integrity, budget alerts pass |
| 18 | Production readiness | All required rails green | Production Definition of Done passes with evidence |

No task may build on a RED rail.

## Executor queue admission

A planner may add a task to `execution/EXECUTOR-QUEUE.md` only if:

1. TYPE is `MICRO-TASK` and STATUS becomes `READY`.
2. Readiness score is at least 18/20, or exactly 20/20 for critical security/tenant/financial/action work.
3. All dependencies name defined tasks in `PASS` status.
4. Canonical spec anchors are accepted and non-conflicting.
5. Exact create/modify/prohibited paths and write set are known.
6. Every relevant symbol, input/output, validation, error, authority, tenant, retry, timeout, idempotency, metric, log, test, command, expected output, and binary acceptance condition is defined.
7. Preconditions can be checked without mutation.
8. No required behavior is a TODO, skipped test, fake pass, or unspecified production mock.

The queue fails closed: absence from the queue means no authorization to execute.

## Parallelization

`PARALLEL_SAFE: YES` requires disjoint WRITE_SET values and no dependency edge between tasks. Shared READ_SET values are allowed. If repository inspection discovers a shared write or generated artifact, both tasks are removed from parallel execution until the planner resolves ordering.

## Preflight and postcondition

Preflight checks dependency status, exact files/symbols, dependency versions, expected migration/schema version, repository state, and canonical spec anchors. A mismatch returns BLOCKED before edits.

Postcondition checks exact file/symbol existence, required tests and typecheck, migration presence where applicable, no prohibited/unexpected writes, all binary acceptance conditions, and a clean handoff report. Unexpected changes are not silently accepted.

## Error, security, and side-effect defaults

- Undefined authorization, tenant, PII, secret, or external-action behavior means DENY/BLOCKED.
- Undefined retry behavior means no automatic retry for a side effect.
- Undefined timeout does not permit an infinite wait.
- An unknown provider outcome enters reconciliation and is not treated as success/failure or retried blindly.
- Failure-path tests are mandatory for authentication, authorization, tenancy, approval, action, idempotency, secrets, connectors, RAG access, and policy.

## Executor success report

```text
TASK <TASK-ID> RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED:
FILES MODIFIED:
UNEXPECTED FILES:
TESTS:
COMMANDS AND EXIT CODES:
ACCEPTANCE:
DEVIATIONS: NONE | <details>
NEXT TASK: <ID or NONE>
```

## Blocked task response

Return `BLOCKED` with violated assumption, exact file/symbol, canonical contract anchor, observed reality, expected reality, completed non-mutating checks, and one minimal architecture question. Do not improvise or start dependent work.

## Architecture deviation response

Return `ARCHITECTURE DEVIATION REQUEST` with current decision, observed problem, evidence, why the current spec cannot be implemented, minimum proposed change, rejected workarounds, affected task/spec/requirement/test IDs, security/tenant/API/data/migration/operations impact. Wait for an accepted ADR or spec correction.

## Two-stage generation

Stage A decomposes every remaining specification into documentation micro-tasks. Stage B is generated only after those specs are accepted. Stage B tasks use one file per micro-task and exact source paths/symbols. The final quality question is: “Can a moderate-reasoning executor implement this correctly without guessing?” If no, keep it out of the queue.

