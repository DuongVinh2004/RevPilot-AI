# TASK-AR-009 — SCIM Negative Test Matrix — Cross-Tenant, Replay, Deprovision

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 16
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IDENTITY-BOUNDARY
FEATURE: SCIM-NEGATIVE-TESTS
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-008
UNLOCKS: AR-029

## Objective and rationale

OBJECTIVE: Create comprehensive SCIM negative test suite with 12 test cases covering cross-tenant isolation, token lifecycle, deprovisioning, duplicate handling, pagination and disabled tenant scenarios.

BUSINESS RATIONALE: Finding P0-SEC-002 requires proving SCIM boundary enforcement through negative tests. Without these tests, future changes could silently reintroduce cross-tenant access or bypass credential verification.

ARCHITECTURAL OWNER: Security Architect

ARCHITECTURAL CONTEXT: INV-TEN-001 (zero cross-tenant leakage), INV-IAM-001 (boundary verification).

## Canonical specification references

- `docs/14-iam/IAM-SPEC.md#negative-test-matrix`
- RFC 7644 (SCIM 2.0 Protocol)

If references conflict, return BLOCKED.

## Preconditions

- AR-008 PASS (SCIM persistence adapter exists).
- SCIM routes use `ScimUserRepositoryPort` and `ScimCredentialPort`.

## Change boundary

READ_SET:
- `apps/api/routers/scim.py`
- `packages/backend/src/revpilot/modules/identity/`
- `tests/` (existing test patterns)

WRITE_SET:
- `tests/integration/test_scim_negative_matrix.py`

CREATE:
- `tests/integration/test_scim_negative_matrix.py`

MODIFY: NONE

DO_NOT_MODIFY:
- `apps/api/routers/scim.py`
- `packages/*`
- Any source code files

EXPECTED CHANGE SET: 1 new test file with 12 test cases.

## Symbol-level contract

MUST EXPORT/DEFINE:

`tests/integration/test_scim_negative_matrix.py`:

```python
def test_cross_tenant_token_a_path_b_returns_403(): ...
def test_expired_token_returns_401(): ...
def test_missing_token_returns_401(): ...
def test_invalid_unknown_token_returns_401(): ...
def test_deactivated_user_get_returns_inactive(): ...
def test_duplicate_external_id_returns_409(): ...
def test_delete_then_recreate_same_external_id_new_uuid(): ...
def test_list_users_tenant_a_excludes_tenant_b(): ...
def test_patch_user_other_tenant_returns_403_or_404(): ...
def test_pagination_total_results_consistent(): ...
def test_disabled_tenant_returns_403(): ...
def test_rotated_credential_old_token_returns_401(): ...
```

Each test uses FastAPI TestClient with test application factory.
Fixtures create 2 tenants (A, B) with separate SCIM credentials.

MUST NOT:
- Modify source code.
- Skip or xfail any test.
- Use production credentials.

## Input/output and validation

INPUT: HTTP requests to SCIM endpoints with various auth/tenant combinations.
OUTPUT: HTTP status codes (401, 403, 404, 409, 200, 201, 204).
INVALID INPUT: N/A — tests validate server-side rejection.
VALIDATION RULES: Each test asserts exact HTTP status code.
STATE TRANSITIONS: NOT APPLICABLE.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| NOT APPLICABLE | Test file, no production errors | N/A | N/A | N/A | N/A | N/A |

## Security contract

AUTHENTICATION: Tests verify authentication enforcement.
AUTHORIZATION: Tests verify authorization enforcement.
TENANT: Tests verify tenant isolation.
PII: Test data only — no real PII.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE — test file.
API CONTRACT: NOT APPLICABLE — test file.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: NOT APPLICABLE.
TIMEOUT: Each test < 5 seconds.
IDEMPOTENCY: Tests are idempotent.
LOGGING: NOT APPLICABLE.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: Any test failure → task FAIL.
ROLLBACK/COMPENSATION: Delete test file.

## Implementation requirements

1. Create test file with pytest fixtures for 2-tenant setup.
2. Implement 12 test cases as specified in symbol contract.
3. Each test must be independent (no ordering dependency between tests).
4. Use `@pytest.mark.integration` marker.

## Tests and evaluations

TESTS REQUIRED: 12 test cases all passing.
AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/integration/test_scim_negative_matrix.py -v
```

EXPECTED: exit code 0, 12/12 tests pass.

## Binary acceptance criteria

- `AC-AR-009-01`: PASS only if `python -m pytest tests/integration/test_scim_negative_matrix.py -v` exits 0 with 12/12 pass.

## Postconditions

- `tests/integration/test_scim_negative_matrix.py` exists with 12 passing tests.
- No source code modified.
- Full test suite passes.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | 12 test cases fully specified |
| Dependency clarity | 2 | Single upstream: AR-008 |
| File boundary clarity | 2 | 1 CREATE, 0 MODIFY |
| Contract clarity | 2 | Each test function named and behavior specified |
| Failure behavior | 2 | Any test fail → task FAIL |
| Security/tenancy | 2 | Tests verify security invariants |
| Testability | 2 | Test file IS the deliverable |
| Verification | 2 | pytest -v, exit 0 |
| Acceptance criteria | 2 | 1 machine-verifiable criterion (12/12 pass) |
| Reasoning independence | 2 | No architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Modify source code.
- Skip or xfail tests.

## Required executor report

```text
TASK TASK-AR-009 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_scim_negative_matrix.py
FILES MODIFIED: NONE
UNEXPECTED FILES: NONE
TESTS: 12/12 SCIM negative tests PASS
COMMANDS AND EXIT CODES: pytest scim tests → 0
ACCEPTANCE: AC-AR-009-01: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-029
```
