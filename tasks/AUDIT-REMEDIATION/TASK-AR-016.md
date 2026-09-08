# TASK-AR-016 — Approval/Action Negative Test Matrix

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 14
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: APPROVAL-ACTION
FEATURE: APPROVAL-NEGATIVE-TESTS
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: NONE
DEPENDS_ON: AR-015
UNLOCKS: AR-029

## Objective and rationale

OBJECTIVE: Create test suite with 15 negative test cases covering all approval/action bypass scenarios.

BUSINESS RATIONALE: Zero-trust audit finding P0-ACT-001 proved that approval and action dispatch paths lacked a comprehensive negative test matrix verifying boundary enforcement against bypass attempts. Missing negative test coverage permits subtle security regressions in tenant isolation, separation of duties, approval state transitions, cryptographic digest binding, and kill-switch engagement to escape detection, violating INV-ACT-001, INV-ACT-002, INV-ACT-003, and INV-TEN-002.

ARCHITECTURAL OWNER: Security Architect, QA Lead

ARCHITECTURAL CONTEXT: INV-ACT-001 (zero unauthorized mutations), INV-ACT-002 (cryptographic approval sealing), INV-ACT-003 (zero self-approval / Separation of Duties), INV-TEN-002 (strict tenant isolation), AC-008, AC-009, DEFINITION-OF-DONE.md §Stage D.

## Canonical specification references

- `docs/14-iam/IAM-SPEC.md#approval-lifecycle`
- `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md`
- `docs/26-api/API-STANDARDS.md`
- `AGENTS.md#3-strict-prohibitions`
- `execution/DEFINITION-OF-DONE.md`

If references conflict, return BLOCKED.

## Preconditions

- AR-015 PASS (Tool Gateway provider adapter port interface and digest verification complete).
- FastAPI application in `apps/api/main.py` boots and mounts approval/action router.
- `tests/integration/` directory exists.

## Change boundary

READ_SET:
- `apps/api/routers/approvals.py`
- `packages/backend/src/revpilot/modules/approval/digest.py`
- `packages/backend/src/revpilot/modules/approval/state_machine.py`
- `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py`
- `tests/integration/test_domain_routes.py`

WRITE_SET:
- `tests/integration/test_approval_action_negative.py`

CREATE:
- `tests/integration/test_approval_action_negative.py`

MODIFY: NONE

DO_NOT_MODIFY:
- `apps/api/routers/approvals.py`
- `packages/backend/src/revpilot/modules/approval/`
- `packages/backend/src/revpilot/modules/tool_gateway/`
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 1 new integration test file containing 15 automated negative test cases.

## Symbol-level contract

MUST EXPORT/DEFINE:

In `tests/integration/test_approval_action_negative.py`:
- `test_01_approve_unknown_id_returns_404()`: Approve non-existent approval ID returns 404 Not Found.
- `test_02_approve_already_approved_returns_409()`: Re-approving already APPROVED request returns 409 Conflict.
- `test_03_approve_expired_returns_410()`: Approving an expired approval request returns 410 Gone.
- `test_04_self_approve_returns_403()`: Requester principal attempting to approve own request returns 403 Forbidden (Separation of Duties).
- `test_05_approve_wrong_tenant_returns_403()`: Approver from tenant B attempting to approve tenant A request returns 403 Forbidden.
- `test_06_dispatch_pending_returns_409()`: Dispatching approval still in PENDING status returns 409 Conflict.
- `test_07_dispatch_rejected_returns_409()`: Dispatching REJECTED approval returns 409 Conflict.
- `test_08_dispatch_expired_approved_returns_410()`: Dispatching APPROVED request whose expiry has elapsed returns 410 Gone.
- `test_09_dispatch_wrong_tenant_returns_403()`: Dispatching with tenant context mismatched from approval tenant returns 403 Forbidden.
- `test_10_dispatch_digest_mismatch_returns_409()`: Dispatching with payload digest differing from approved sealed digest returns 409 Conflict.
- `test_11_dispatch_duplicate_idempotency_returns_409()`: Replaying dispatch with same idempotency key for conflicting payload returns 409 Conflict.
- `test_12_dispatch_kill_switch_active_returns_503()`: Dispatching action while global or tenant kill switch is engaged returns 503 Service Unavailable.
- `test_13_dry_run_causes_no_state_change()`: POST `/actions/dry-run` executes simulation and verifies 0 state mutations in approval/ledger records.
- `test_14_provider_failure_records_provider_failed()`: Simulated upstream provider failure produces 502/500 and records `PROVIDER_FAILED` in action ledger.
- `test_15_kill_switch_race_fails_closed()`: Concurrent dispatch attempt initiated during kill switch activation window fails closed with 503.

MUST NOT:
- Mock out security checks or assert tautologies (e.g. `assert True`).
- Skip, ignore, or xfail any of the 15 negative tests.
- Modify production router logic or error handlers to weaken validation contracts.

## Input/output and validation

INPUT: HTTP test requests submitted to `/api/v1/approvals` and `/api/v1/actions` routes using `fastapi.testclient.TestClient`.
OUTPUT: HTTP status codes and JSON error response structures.
INVALID INPUT: Missing auth token or invalid tenant headers → 401/403.
VALIDATION RULES:
1. Every negative test must assert the exact expected HTTP status code.
2. Every test verifying error payloads must assert specific error codes/messages.
3. Every test verifying state changes must verify database/cache persistence directly.
STATE TRANSITIONS:
- PENDING → APPROVED (valid)
- APPROVED → APPROVED (invalid, returns 409)
- EXPIRED → APPROVED (invalid, returns 410)
- PENDING → DISPATCHING (invalid, returns 409)
- REJECTED → DISPATCHING (invalid, returns 409)

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `ERR_NOT_FOUND` | Target approval ID not found | 404 | no | Approval request not found | yes | `revpilot_api_errors_total{code="ERR_NOT_FOUND"}` |
| `ERR_STATE_CONFLICT` | Invalid approval/dispatch state transition | 409 | no | Invalid approval state transition | yes | `revpilot_api_errors_total{code="ERR_STATE_CONFLICT"}` |
| `ERR_APPROVAL_EXPIRED` | Approval request has expired | 410 | no | Approval request has expired | yes | `revpilot_api_errors_total{code="ERR_APPROVAL_EXPIRED"}` |
| `ERR_AUTHORIZATION_FAILED` | SoD violation or cross-tenant access | 403 | no | Authorization denied | yes | `revpilot_api_errors_total{code="ERR_AUTHORIZATION_FAILED"}` |
| `ERR_APPROVAL_DIGEST_MISMATCH` | Action payload digest tampered | 409 | no | Action dispatch approval digest mismatch | yes | `revpilot_api_errors_total{code="ERR_APPROVAL_DIGEST_MISMATCH"}` |
| `ERR_IDEMPOTENCY_CONFLICT` | Duplicate idempotency key conflict | 409 | no | Idempotency key already used with different parameters | yes | `revpilot_api_errors_total{code="ERR_IDEMPOTENCY_CONFLICT"}` |
| `ERR_KILL_SWITCH_ENGAGED` | Emergency kill switch engaged | 503 | yes | Emergency kill switch engaged | yes | `revpilot_api_errors_total{code="ERR_KILL_SWITCH_ENGAGED"}` |
| `ERR_PROVIDER_EXECUTION_FAILED` | Provider execution returned failure | 502 | yes | External provider action execution failed | yes | `revpilot_api_errors_total{code="ERR_PROVIDER_EXECUTION_FAILED"}` |

## Security contract

AUTHENTICATION: All test requests authenticate via mock JWT bearer tokens issued through test auth adapter.
AUTHORIZATION: Enforces role-based authority (`OPERATOR`, `SYSTEM_ADMIN`, `ANALYST`) and Separation of Duties.
TENANT: Tenant isolation rigorously verified; cross-tenant approvals and dispatches fail closed with 403 Forbidden.
PII: PROHIBITED — test fixture data uses synthetic identifiers only (`tnt_test_001`, `usr_test_001`).
SECRET ACCESS: PROHIBITED — no live API keys or external secrets used in test suite.
EXTERNAL ACTION: PROHIBITED — external network calls disabled; zero outbound socket traffic permitted.
DEFAULT: DENY — all bypass attempts must fail closed.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE — test-only task.
API CONTRACT: Conforms to FastAPI route definitions in `apps/api/routers/approvals.py`.
EVENT CONTRACT: NOT APPLICABLE — tests assert HTTP response codes and ledger states.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: Enforces INV-ACT-003 (agents cannot self-approve or dispatch unapproved actions).
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: NOT APPLICABLE — test cases are deterministic and hermetic.
TIMEOUT: Total test suite execution bounded to < 10 seconds.
IDEMPOTENCY: Test fixtures reset in-memory caches and test databases between tests.
LOGGING: Standard pytest output and test client logs.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: Any negative test failure immediately flags security regression and fails CI build.
ROLLBACK/COMPENSATION: NOT APPLICABLE.

## Implementation requirements

1. Create `tests/integration/test_approval_action_negative.py`.
2. Configure pytest fixtures:
   - `api_client`: TestClient initialized with FastAPI app and default operator token.
   - `auth_helper`: Helper to issue tokens for specific principals and tenants with custom roles.
   - `reset_approval_state`: Fixture to clear `_pending_approvals_cache`, `approval_repo`, and `action_ledger_repo` between test runs.
3. Implement the 15 negative tests:
   - Test 1: POST `/api/v1/approvals/appr_nonexistent/approve` → 404.
   - Test 2: Approve an already APPROVED request → 409.
   - Test 3: Create approval with past expiration, attempt approval → 410.
   - Test 4: Requester principal attempts to approve own request → 403 (SoD).
   - Test 5: Approver from `tnt_tenant_b` attempts to approve `tnt_tenant_a` request → 403.
   - Test 6: Attempt action dispatch on approval with status PENDING → 409.
   - Test 7: Attempt action dispatch on approval with status REJECTED → 409.
   - Test 8: Attempt action dispatch on approval with expired timestamp → 410.
   - Test 9: Dispatch action using context tenant mismatched from approval tenant → 403.
   - Test 10: Dispatch action where request digest != sealed approval digest → 409.
   - Test 11: Dispatch action with existing idempotency key and conflicting payload → 409.
   - Test 12: Engage kill switch, attempt dispatch → 503.
   - Test 13: Execute dry-run, verify 200 OK and 0 changes to approval/ledger state.
   - Test 14: Simulate provider execution failure, verify 502/500 and ledger status `PROVIDER_FAILED`.
   - Test 15: Simulate concurrent dispatch during kill switch activation window, verify fail-closed 503.
4. Verify all 15 tests execute cleanly with 0 warnings or errors.

## Tests and evaluations

TESTS REQUIRED:
- 15 integration negative tests in `tests/integration/test_approval_action_negative.py`.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Entire test suite executes in < 5 seconds.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/integration/test_approval_action_negative.py -v
```

EXPECTED: exit code 0, 15 passed, 0 failed, 0 skipped.

## Binary acceptance criteria

- `AC-AR-016-01`: PASS only if all 15 negative test cases in `tests/integration/test_approval_action_negative.py` pass without failures, errors, or skipped tests.

## Postconditions

- `tests/integration/test_approval_action_negative.py` is committed and automated.
- All 15 approval and action dispatch bypass scenarios are verified fail-closed.
- No production files outside WRITE_SET modified.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Exact 15 negative test cases enumerated with expected HTTP statuses |
| Dependency clarity | 2 | Depends on AR-015, unblocks AR-029 |
| File boundary clarity | 2 | 1 CREATE file, 0 MODIFY files |
| Contract clarity | 2 | HTTP routes, inputs, and expected response codes fully defined |
| Failure behavior | 2 | All negative scenarios assert explicit error codes and fail-closed behavior |
| Security/tenancy | 2 | Validates tenant isolation, SoD, approval expiration, and kill switch |
| Testability | 2 | Direct pytest execution via FastAPI TestClient |
| Verification | 2 | Single hermetic command: pytest exit 0 |
| Acceptance criteria | 2 | Single machine-verifiable criterion (15/15 pass) |
| Reasoning independence | 2 | Fully deterministic test matrix, 0 open decisions |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Use `assert True` or mock assertions that bypass actual endpoint execution.
- Mark any of the 15 tests as skipped or xfail.
- Modify production route handlers to fake test passes.

## Required executor report

```text
TASK TASK-AR-016 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_approval_action_negative.py
FILES MODIFIED: NONE
UNEXPECTED FILES: NONE
TESTS: 15 negative integration tests PASS
COMMANDS AND EXIT CODES: pytest tests/integration/test_approval_action_negative.py -v → 0
ACCEPTANCE: AC-AR-016-01: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-029
```
