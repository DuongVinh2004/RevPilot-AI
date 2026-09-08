# TASK-AR-005 — Remove Authentication Adapter Fallback — Fail-Closed When Adapter Unavailable

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 3
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IDENTITY-BOUNDARY
FEATURE: AUTH-FAILCLOSED
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-004
UNLOCKS: AR-006, AR-007, AR-010, AR-011, AR-023, AR-024

## Objective and rationale

OBJECTIVE: Verify and ensure that `apps/api/middleware/authentication.py` raises `AuthenticationError` when `auth_adapter is None`, with no fallback token parser. Create 8 negative integration tests proving the fail-closed behavior.

BUSINESS RATIONALE: Finding P0-SEC-001 identified that if auth_adapter is None (due to missing database), a Bearer token with suitable structure could be parsed into a principal with OPERATOR/ANALYST roles. Post-commit `ecb45c9`, the middleware already has fail-closed behavior at lines 50-54. This task verifies that behavior and adds comprehensive negative tests to prevent regression.

ARCHITECTURAL OWNER: Security Architect

ARCHITECTURAL CONTEXT: INV-IAM-001 (boundary JWT verification), INV-TEN-002 (server-derived context), INV-SEC-001 (cryptographic token verification).

## Canonical specification references

- `docs/14-iam/IAM-SPEC.md#authentication-boundary`
- `docs/14-iam/IAM-SPEC.md#negative-test-matrix`
- `AGENTS.md#1-core-operating-directives`

If references conflict, return BLOCKED.

## Preconditions

- AR-004 PASS (startup fail-closed ensures adapter is always present in production).
- `apps/api/middleware/authentication.py` exists with `get_current_principal` function.
- Current code at lines 50-54 raises `AuthenticationError` when `auth_adapter is None`.

## Change boundary

READ_SET:
- `apps/api/middleware/authentication.py` (full file, 111 lines)
- `apps/api/main.py` (to understand app factory and test setup)
- `tests/` (to understand existing test patterns)

WRITE_SET:
- `apps/api/middleware/authentication.py` (verify, potentially no changes needed)
- `tests/integration/test_auth_failclosed_negative.py`

CREATE:
- `tests/integration/test_auth_failclosed_negative.py`

MODIFY:
- `apps/api/middleware/authentication.py` — ONLY if fallback parser code still exists. Based on latest source review (lines 49-54), code already raises AuthenticationError when adapter is None. If no changes needed, document as "verified, no modification required".

DO_NOT_MODIFY:
- `apps/api/main.py`
- `apps/api/routers/*`
- `packages/backend/src/revpilot/modules/identity/*`

EXPECTED CHANGE SET:
- 1 new test file with 8 test cases.
- 0 or minimal changes to authentication.py (verification pass).

## Symbol-level contract

MUST EXPORT/DEFINE:
- `tests/integration/test_auth_failclosed_negative.py`:
  - `test_empty_token_returns_401()` — No Authorization header → 401.
  - `test_random_token_returns_401()` — `Bearer random_garbage_xyz` → 401.
  - `test_malformed_token_returns_401()` — `Bearer not-a-valid-token-format` → 401.
  - `test_expired_token_returns_401()` — Token with expired claims → 401.
  - `test_revoked_token_returns_401()` — Token marked revoked in adapter → 401.
  - `test_no_adapter_valid_looking_token_returns_401()` — auth_adapter=None + token that looks like `usr_xxx_tnt_yyy` → 401 (NOT 200 with roles).
  - `test_dev_principal_header_ignored_in_production()` — X-Dev-Principal header with ENVIRONMENT=production → ignored, still 401 without valid token.
  - `test_dev_tenant_header_ignored_in_production()` — X-Dev-Tenant header with ENVIRONMENT=production → ignored, still 401.

MUST NOT:
- Add any fallback authentication path.
- Create dev bypass in production mode.
- Modify existing passing tests.

## Input/output and validation

INPUT: HTTP requests with various Authorization header values.
OUTPUT: HTTP 401 responses for all invalid/missing tokens.
INVALID INPUT: Any token not verified by auth adapter → 401.
VALIDATION RULES: All 8 test scenarios must return exactly HTTP 401.
STATE TRANSITIONS: NOT APPLICABLE.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `AUTH_MISSING` | No Bearer token | 401 | no | Authentication token missing or invalid | yes | `auth_failures_total{reason="missing"}` |
| `AUTH_INVALID` | Token verification fails | 401 | no | Authentication token missing or invalid | yes | `auth_failures_total{reason="invalid"}` |
| `AUTH_UNAVAILABLE` | Auth adapter is None | 401 | no | Authentication service is unavailable | yes | `auth_failures_total{reason="unavailable"}` |

## Security contract

AUTHENTICATION: This task IS the authentication enforcement verification.
AUTHORIZATION: NOT APPLICABLE — testing pre-authorization layer.
TENANT: Ensures no tenant context leaks from unverified tokens.
PII: PROHIBITED — test tokens must not contain real PII.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY — every undefined token state → 401.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE.
API CONTRACT: NOT APPLICABLE — testing middleware, not endpoint.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: NOT APPLICABLE — test suite.
TIMEOUT: Each test case < 5 seconds.
IDEMPOTENCY: Tests are idempotent.
LOGGING: NOT APPLICABLE.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: Any test failure → task FAIL.
ROLLBACK/COMPENSATION: Delete test file, revert any auth middleware changes.

## Implementation requirements

1. Read `apps/api/middleware/authentication.py` completely.
2. Verify lines 49-54 contain fail-closed behavior:
   ```python
   if auth_adapter is None:
       raise AuthenticationError(
           "Authentication service is unavailable",
           details={"error": "auth_adapter_unavailable"},
       )
   ```
3. Verify NO fallback parser exists after this block (no `else` branch that splits tokens).
4. Search for strings: `fallback`, `Bearer.*split`, `self_assign.*role`, `OPERATOR.*ANALYST` — must return 0 matches.
5. Create `tests/integration/test_auth_failclosed_negative.py` with 8 test cases using FastAPI TestClient.
6. Run full test suite to verify no regression.

## Tests and evaluations

TESTS REQUIRED:
- 8 negative test cases in `tests/integration/test_auth_failclosed_negative.py`.
- Full regression: `python -m pytest tests/ -q` exit 0.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
grep -n "fallback\|Bearer.*split\|self_assign.*role\|OPERATOR.*ANALYST" apps/api/middleware/authentication.py || true && python -m pytest tests/integration/test_auth_failclosed_negative.py -v && python -m pytest tests/ -q
```

EXPECTED: grep returns 0 matches, pytest exits 0 with 8/8 auth tests pass and full suite pass.

## Binary acceptance criteria

- `AC-AR-005-01`: PASS only if `grep -c "fallback\|Bearer.*split\|self_assign.*role\|OPERATOR.*ANALYST" apps/api/middleware/authentication.py` returns 0.
- `AC-AR-005-02`: PASS only if 8 negative test cases in `test_auth_failclosed_negative.py` all pass.
- `AC-AR-005-03`: PASS only if `python -m pytest tests/ -q` exits 0 (full suite, no regression).

## Postconditions

- `apps/api/middleware/authentication.py` has no fallback token parser.
- `tests/integration/test_auth_failclosed_negative.py` exists with 8 passing tests.
- Full test suite passes.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Verify fail-closed + add 8 tests |
| Dependency clarity | 2 | Single upstream: AR-004 |
| File boundary clarity | 2 | 1 verify/modify, 1 CREATE |
| Contract clarity | 2 | 8 test cases fully specified |
| Failure behavior | 2 | Every invalid token → 401 |
| Security/tenancy | 2 | Core authentication security task |
| Testability | 2 | 8 concrete test scenarios |
| Verification | 2 | grep + pytest, exit 0 |
| Acceptance criteria | 2 | 3 machine-verifiable criteria |
| Reasoning independence | 2 | No architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Add any fallback authentication path.
- Modify existing passing tests.
- Create dev bypass in production.

## Required executor report

```text
TASK TASK-AR-005 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_auth_failclosed_negative.py
FILES MODIFIED: apps/api/middleware/authentication.py (if changes needed) or NONE
UNEXPECTED FILES: NONE
TESTS: 8 auth negative tests PASS, full suite PASS
COMMANDS AND EXIT CODES: grep → 0 matches, pytest auth tests → 0, pytest full → 0
ACCEPTANCE: AC-AR-005-01: PASS|FAIL, AC-AR-005-02: PASS|FAIL, AC-AR-005-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-006 or AR-007 or AR-010 or AR-011
```
