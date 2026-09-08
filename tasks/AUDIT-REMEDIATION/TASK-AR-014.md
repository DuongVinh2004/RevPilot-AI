# TASK-AR-014 — Dispatch Creates Real Intent and Binds to Tool Gateway

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 15
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: APPROVAL-ACTION
FEATURE: DISPATCH-GATEWAY-BIND
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-013
UNLOCKS: AR-015

## Objective and rationale

OBJECTIVE: Dispatch endpoint must (1) load approval record, (2) create ActionIntent with idempotency key, (3) call gateway.dispatch(intent), (4) update approval state to DISPATCHING, (5) return response based on gateway result.

BUSINESS RATIONALE: Finding P0-ACT-001 proved that `/actions/dispatch` returned a hardcoded `"status": "EXECUTING"` response before verifying the approval record, without enforcing kill-switch 503 semantics, without checking idempotency conflicts, without executing actual Tool Gateway dispatch, and without updating the approval state to DISPATCHING/SUCCEEDED/PROVIDER_FAILED. Binding dispatch directly to the Tool Gateway with strict precondition checks ensures zero unverified executions (INV-ACT-001) and accurate state reflection.

ARCHITECTURAL OWNER: Security Architect, Backend Lead

ARCHITECTURAL CONTEXT: INV-ACT-001 (Zero Unauthorized Mutation), INV-ACT-002 (Approval Digest Binding), INV-SEC-001 (Gateway Egress Containment), AC-008 (Approval Verification), AC-009 (Action Dispatch Loop).

## Canonical specification references

- `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md#action-dispatch-protocol`
- `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md#dispatch-gate`
- `docs/26-api/API-STANDARDS.md#error-handling`
- `AGENTS.md#3-strict-prohibitions`

If references conflict, return BLOCKED.

## Preconditions

- AR-012 PASS (Approval state machine exists with states PENDING, APPROVED, DISPATCHING, SUCCEEDED, PROVIDER_FAILED).
- AR-013 PASS (Action intent domain repository and idempotency validation available).
- `apps/api/routers/approvals.py` exists with `/actions/dispatch` endpoint.
- `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py` exists with `ActionCapabilityGateway.dispatch_action`.

## Change boundary

READ_SET:
- `apps/api/routers/approvals.py`
- `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py`
- `packages/backend/src/revpilot/modules/approval/state_machine.py`
- `packages/backend/src/revpilot/modules/action/domain.py`
- `packages/backend/src/revpilot/shared/errors.py`

WRITE_SET:
- `apps/api/routers/approvals.py`
- `tests/integration/test_action_dispatch_gateway.py`

CREATE:
- `tests/integration/test_action_dispatch_gateway.py`

MODIFY:
- `apps/api/routers/approvals.py` — Replace lines 200-234 (`dispatch_action`) with real workflow:
  1. Check emergency kill switch (`GLOBAL` or `TENANT`); if active, raise HTTP 503 (`status.HTTP_503_SERVICE_UNAVAILABLE`).
  2. Load approval record from repository/cache; if not found, raise 404 (`NotFoundError`); if not in `APPROVED` state, raise 409 (`ConflictError`).
  3. Validate or record `ActionIntent` with `idempotency_key`; if duplicate idempotency key detected with conflicting payload/state, raise 409 (`ConcurrencyError` / `ConflictError`) or return existing intent result.
  4. Transition approval state to `DISPATCHING` via state machine.
  5. Construct `ActionCapabilityRequest` and call `gateway.dispatch_action(...)`.
  6. On gateway failure / provider error, transition approval state to `PROVIDER_FAILED` and raise HTTP 502 (`status.HTTP_502_BAD_GATEWAY` with error details).
  7. On gateway success, transition approval state to `SUCCEEDED` (or retain `DISPATCHING`/`EXECUTING` as appropriate) and return HTTP 202 payload with `"status": "EXECUTING"`.

DO_NOT_MODIFY:
- `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py`
- `apps/api/middleware/*`
- `packages/backend/src/revpilot/shared/errors.py`
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 1 router endpoint rewritten (`apps/api/routers/approvals.py`), 1 new integration test file (`tests/integration/test_action_dispatch_gateway.py`).

## Symbol-level contract

MUST EXPORT/DEFINE:

Modified `dispatch_action` endpoint in `apps/api/routers/approvals.py`:
```python
@router.post("/actions/dispatch", status_code=status.HTTP_202_ACCEPTED)
async def dispatch_action(
    payload: ActionDispatchPayload,
    request: Request,
    tenant: TenantContext = Depends(get_current_tenant),
    principal: PrincipalContext = Depends(require_roles("OPERATOR", "SYSTEM_ADMIN")),
) -> dict[str, Any]:
    ...
```

MUST NOT:
- Return `"status": "EXECUTING"` prior to executing gateway dispatch.
- Return 403 when kill switch is engaged (must return 503 Service Unavailable).
- Allow dispatch of unapproved, expired, or rejected approval records.
- Allow duplicate dispatch with different payload or conflicting idempotency key.
- Mask gateway execution failure as success.

## Input/output and validation

INPUT:
- `payload: ActionDispatchPayload` (`approval_id: str`, `idempotency_key: str`).
- `tenant: TenantContext` from header/auth context.
- `principal: PrincipalContext` with `OPERATOR` or `SYSTEM_ADMIN` role.
- Gateway and repository instances on `request.app.state`.

OUTPUT:
- Success (HTTP 202):
  ```json
  {
    "intent_id": "...",
    "approval_id": "...",
    "status": "EXECUTING",
    "idempotency_key": "...",
    "ledger_id": "..."
  }
  ```
- Duplicate dispatch with identical idempotency key: Returns existing intent response or HTTP 409 conflict.

INVALID INPUT:
- Missing or malformed payload fields → HTTP 422 / 400.
- Approval ID not found → HTTP 404 (`NotFoundError`).
- Approval record not in `APPROVED` status → HTTP 409 (`ConflictError`).
- Active kill switch (GLOBAL or TENANT) → HTTP 503 (`HTTPException(status_code=503, detail=...)`).
- Gateway dispatch error / provider failure → HTTP 502 (`HTTPException(status_code=502, detail=...)`).

STATE TRANSITIONS:
- Approval record: `APPROVED` → `DISPATCHING` → `SUCCEEDED` (on gateway success) or `PROVIDER_FAILED` (on gateway failure).

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `KILL_SWITCH_ACTIVE` | Emergency halt kill switch active | 503 | yes | Action dispatch temporarily unavailable: Emergency kill switch engaged | yes | `action_dispatch_killswitch_blocked_total` |
| `APPROVAL_NOT_FOUND` | `approval_id` does not exist | 404 | no | Approval record not found | yes | `action_dispatch_not_found_total` |
| `INVALID_APPROVAL_STATE` | Approval record not in APPROVED state | 409 | no | Approval must be in APPROVED state to dispatch | yes | `action_dispatch_invalid_state_total` |
| `IDEMPOTENCY_CONFLICT` | Duplicate idempotency key with conflicting intent | 409 | no | Action intent idempotency conflict | yes | `action_dispatch_idempotency_conflict_total` |
| `PROVIDER_FAILED` | Gateway dispatch fails or provider returns error | 502 | yes | Downstream provider execution failed | yes | `action_dispatch_provider_error_total` |

## Security contract

AUTHENTICATION: Requires valid bearer token via `get_current_tenant` and authentication middleware.
AUTHORIZATION: Restricted to `OPERATOR` or `SYSTEM_ADMIN` roles via `require_roles`.
TENANT: Strictly scoped to `tenant.tenant_id`. Cross-tenant approval dispatch rejected (`TenancyViolationError` / 403).
PII: PROHIBITED in intent payload digests and audit logs. All payloads scrubbed via gateway secret scrubber.
SECRET ACCESS: Ephemeral tokens managed solely by Tool Gateway `CredentialBroker`.
EXTERNAL ACTION: Governed exclusively through `ActionCapabilityGateway.dispatch_action`. Direct socket egress barred.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: Conforms to `ActionIntentRecord` and `ActionLedgerRecord` schemas in `revpilot.modules.action.domain`.
API CONTRACT: Modifies `/actions/dispatch` behavior to return 503 on kill switch, 502 on provider failure, 409 on state/idempotency conflict, and 202 on successful dispatch.
EVENT CONTRACT: NOT APPLICABLE — internal synchronous dispatch to Tool Gateway.
TEMPORAL CONTRACT: NOT APPLICABLE — workflow activities handled by Tool Gateway dispatch.
AGENT CONTRACT: NOT APPLICABLE — no agent prompts or models changed.
MODEL CONTRACT: NOT APPLICABLE — no AI models invoked.
RAG CONTRACT: NOT APPLICABLE — no retrieval augmented generation.

## Operational behavior

RETRY: Non-retryable on 404, 409; client may retry on 503 (kill switch deactivation) and 502 (transient provider failure) with backoff.
TIMEOUT: Gateway call bounded by 5000ms timeout.
IDEMPOTENCY: Governed by `idempotency_key` per `(tenant_id, idempotency_key)`. Duplicate dispatch returns existing execution result or 409.
LOGGING: Structured audit logging for all dispatch attempts including tenant_id, principal_id, approval_id, intent_id, idempotency_key, and dispatch result.
METRICS: Emits `action_dispatch_total{status, provider}`, `action_dispatch_latency_seconds`.
FAILURE BEHAVIOR: Fail-closed on missing dependencies, active kill switches, unapproved state, or gateway execution failure.
ROLLBACK/COMPENSATION: Gateway failure records `PROVIDER_ERROR` in ledger and transitions approval state to `PROVIDER_FAILED`.

## Implementation requirements

1. In `apps/api/routers/approvals.py`:
   - Inspect `request.app.state` for `killswitch_repo`. If kill switch is active for `GLOBAL` or current `TENANT`, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Action dispatch blocked: Emergency kill switch is actively engaged.")`.
   - Retrieve approval record from `request.app.state.approval_repo` (or `request.app.state._pending_approvals_cache`). If record is missing, raise `NotFoundError`.
   - Verify approval status is `APPROVED`. If not, raise `ConflictError("Approval is not in APPROVED state")`.
   - Check `request.app.state.action_ledger_repo` for existing intent matching `(tenant.tenant_id, payload.idempotency_key)`. If existing intent found:
     - If approval_id matches and already executed/executing, return existing result or raise `ConflictError` / 409 if parameters conflict.
   - Transition approval state from `APPROVED` to `DISPATCHING` using approval state machine.
   - Resolve `gateway` instance from `request.app.state.tool_gateway` (or construct `ActionCapabilityGateway` fallback).
   - Construct `ActionCapabilityRequest` using approval record details, approval digest, action_type, target entities, payload, and idempotency key.
   - Call `await gateway.dispatch_action(tenant, cap_request)` (or synchronous mock execution if gateway is synchronous).
   - If gateway returns `Failure` or ledger execution_status indicates `PROVIDER_ERROR`:
     - Update approval state to `PROVIDER_FAILED`.
     - Raise `HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"code": "PROVIDER_FAILED", "message": "Downstream provider execution failed"})`.
   - On gateway success:
     - Update approval state to `SUCCEEDED` (or maintain `EXECUTING`).
     - Return HTTP 202 Accepted response with `intent_id`, `approval_id`, `status: "EXECUTING"`, and `idempotency_key`.
2. Create `tests/integration/test_action_dispatch_gateway.py` with integration tests validating all 5 acceptance criteria:
   - AC-AR-014-01: Gateway dispatch is called before returning `EXECUTING`.
   - AC-AR-014-02: Active kill switch returns 503.
   - AC-AR-014-03: Duplicate idempotency key returns 409 or existing result.
   - AC-AR-014-04: Gateway failure returns 502 with `PROVIDER_FAILED` state.
   - AC-AR-014-05: `"status": "EXECUTING"` returned only after gateway success.

## Tests and evaluations

TESTS REQUIRED:
- `tests/integration/test_action_dispatch_gateway.py` covering:
  - Test kill switch engaged triggers 503.
  - Test unapproved approval state triggers 409.
  - Test missing approval triggers 404.
  - Test duplicate idempotency key triggers 409 / idempotent return.
  - Test gateway failure triggers 502 and marks state PROVIDER_FAILED.
  - Test successful dispatch calls gateway.dispatch and returns 202 with EXECUTING.
- Full test suite: `python -m pytest tests/ -q`

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Dispatch pipeline sub-1000ms end-to-end.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/integration/test_action_dispatch_gateway.py -v && python -m pytest tests/ -q
```

EXPECTED: exit code 0.

## Binary acceptance criteria

- `AC-AR-014-01`: PASS only if `/actions/dispatch` invokes `gateway.dispatch_action` and does not return `EXECUTING` prior to gateway call.
- `AC-AR-014-02`: PASS only if `/actions/dispatch` returns HTTP status 503 when kill switch is engaged for GLOBAL or tenant scope.
- `AC-AR-014-03`: PASS only if duplicate dispatch with the same `(tenant_id, idempotency_key)` returns HTTP status 409 or the existing intent result without re-executing gateway dispatch.
- `AC-AR-014-04`: PASS only if gateway dispatch failure sets approval state to `PROVIDER_FAILED` and returns HTTP status 502.
- `AC-AR-014-05`: PASS only if response status is `"EXECUTING"` strictly after gateway dispatch succeeds.

## Postconditions

- `/actions/dispatch` binds real `ActionIntent` to `ActionCapabilityGateway`.
- Kill switch triggers 503 instead of 403.
- Approval state transitions to `DISPATCHING`, and subsequently to `SUCCEEDED` or `PROVIDER_FAILED`.
- All 5 acceptance criteria verified by integration tests.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | 5-step dispatch workflow precisely specified |
| Dependency clarity | 2 | Upstream AR-013 and downstream AR-015 clearly defined |
| File boundary clarity | 2 | Exact lines in approvals.py and single new test file |
| Contract clarity | 2 | Complete input, output, error, and status code specifications |
| Failure behavior | 2 | 503 on kill switch, 502 on gateway failure, 409 on conflict, 404 on missing record |
| Security/tenancy | 2 | Tenant scoping, role authorization, secret scrubbing, and egress containment enforced |
| Testability | 2 | 5 distinct acceptance test scenarios covering all branches |
| Verification | 2 | Single hermetic pytest command exiting 0 |
| Acceptance criteria | 2 | 5 binary machine-verifiable criteria |
| Reasoning independence | 2 | Zero new architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Return status `"EXECUTING"` prior to gateway execution.
- Return 403 when kill switch is active (must return 503).
- Permit dispatch for unapproved or non-existent approvals.
- Bypass Tool Gateway or egress containment barriers.
- Modify files outside WRITE_SET.

## Required executor report

```text
TASK TASK-AR-014 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_action_dispatch_gateway.py
FILES MODIFIED: apps/api/routers/approvals.py
UNEXPECTED FILES: NONE
TESTS: <test output>
COMMANDS AND EXIT CODES: python -m pytest tests/integration/test_action_dispatch_gateway.py -v → 0, python -m pytest tests/ -q → 0
ACCEPTANCE: AC-AR-014-01: PASS|FAIL, AC-AR-014-02: PASS|FAIL, AC-AR-014-03: PASS|FAIL, AC-AR-014-04: PASS|FAIL, AC-AR-014-05: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-015
```
