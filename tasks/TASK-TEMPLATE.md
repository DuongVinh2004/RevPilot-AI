# <TASK-ID> — <TITLE>

TYPE: MICRO-TASK  
STATUS: DRAFT  
RAIL: <number/name>  
INITIATIVE: <ID>  
PHASE: <ID>  
EPIC: <ID>  
FEATURE: <ID>  
COMPLEXITY: XS | S | M | L  
REASONING_LOAD: LOW | MEDIUM | HIGH  
READINESS_SCORE: <0-20; per-dimension rationale below>  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: YES | NO  
PARALLEL_WITH: <IDs or NONE>  
DEPENDS_ON: <IDs or NONE>  
UNLOCKS: <IDs or NONE>

## Objective and rationale

OBJECTIVE: One observable primary change.  
BUSINESS RATIONALE: Why this change exists.  
ARCHITECTURAL OWNER: Owning module/component.  
ARCHITECTURAL CONTEXT: Only context required for this task.

## Canonical specification references

- `<exact/path.md#anchor>`

If references conflict, return BLOCKED.

## Preconditions

- Exact read-only checks, expected files/symbols/versions/migration state.

## Change boundary

READ_SET:

- `<exact path>`

WRITE_SET:

- `<exact path>`

CREATE:

- `<exact path or NONE>`

MODIFY:

- `<exact path or NONE>`

DO NOT MODIFY:

- `<exact paths>`

EXPECTED CHANGE SET: Exact created/modified paths and intended symbol-level changes.

## Symbol-level contract

MUST EXPORT/DEFINE: Exact symbols and signatures.  
MUST NOT: Forbidden responsibility/dependency/side effect.

## Input/output and validation

INPUT: Typed schema and valid example.  
OUTPUT: Typed schema and expected example.  
INVALID INPUT: Explicit cases.  
VALIDATION RULES: Exact rules and boundary values.  
STATE TRANSITIONS: Exact from/to states or `NOT APPLICABLE — reason`.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `<CODE>` | `<condition>` | `<value>` | yes/no | `<message>` | yes/no | `<metric>` |

## Security contract

AUTHENTICATION: required/not required and mechanism.  
AUTHORIZATION: exact permission/policy.  
TENANT: tenant/global behavior and enforcing layer.  
PII: allowed/prohibited and fields.  
SECRET ACCESS: allowed/prohibited and broker.  
EXTERNAL ACTION: allowed/prohibited.  
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: Exact schema/table/columns/keys/indexes/RLS/lifecycle, or `NOT APPLICABLE — reason`.  
API CONTRACT: Method/path/auth/request/response/errors/idempotency/audit/rate limit, or `NOT APPLICABLE — reason`.  
EVENT CONTRACT: Name/producer/consumer/version/partition/tenant/idempotency/order/retry/DLQ/retention/compatibility, or `NOT APPLICABLE — reason`.  
TEMPORAL CONTRACT: Workflow ID/name/types/activities/signals/queries/timers/retry/timeouts/cancellation/compensation/versioning, or `NOT APPLICABLE — reason`.  
AGENT CONTRACT: Responsibility/schemas/allowed-denied tools/model-tool-cost-time limits/retry/fallback/escalation/evidence/evals, or `NOT APPLICABLE — reason`.  
MODEL CONTRACT: Dataset/features/target/split/baseline/models/metrics/calibration/threshold/artifact/version/serving, or `NOT APPLICABLE — reason`.  
RAG CONTRACT: Entity/parser/chunk/index/retrieval/filter/fusion/rerank/citation/deletion/eval details, or `NOT APPLICABLE — reason`.

## Operational behavior

RETRY: Exact policy.  
TIMEOUT: Exact policy.  
IDEMPOTENCY: Key/scope/retention/replay response.  
LOGGING: Named structured events and prohibited data.  
METRICS: Exact metric names/labels and cardinality constraints.  
FAILURE BEHAVIOR: Detection, impact, recovery, prevention.  
ROLLBACK/COMPENSATION: Exact behavior or reason not applicable.

## Implementation requirements

1. Prescriptive steps within the allowed write set.

## Tests and evaluations

TESTS REQUIRED: Exact positive and negative cases/files.  
AI EVALS REQUIRED: Exact dataset/metric/threshold or `NOT APPLICABLE — reason`.  
PERFORMANCE REQUIREMENTS: Exact target/test or `NOT APPLICABLE — reason`.  
MIGRATION REQUIREMENTS: Exact migration/backfill/compatibility/recovery or `NOT APPLICABLE — reason`.

## Verification

COMMANDS:

```text
<exact non-destructive command>
```

EXPECTED: exit code 0 and exact observable output/condition.

## Binary acceptance criteria

- `AC-<TASK>-01`: PASS only if <machine-verifiable condition>.

## Postconditions

- Expected files/symbols/tests/migrations exist; forbidden files are unchanged.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 0 | |
| Dependency clarity | 0 | |
| File boundary clarity | 0 | |
| Contract clarity | 0 | |
| Failure behavior | 0 | |
| Security/tenancy | 0 | |
| Testability | 0 | |
| Verification | 0 | |
| Acceptance criteria | 0 | |
| Reasoning independence | 0 | |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.

## Required executor report

Use the exact result contract from `execution/MICRO-TASK-RAIL-SYSTEM.md#executor-success-report`.

