# TASK-AR-024 — Admin Export Tenant Binding — BOLA Prevention

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 4
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: SECURITY-HARDENING
FEATURE: ADMIN-BOLA
COMPLEXITY: XS
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-023
DEPENDS_ON: AR-005
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Add tenant binding guard to `export_tenant_data` endpoint in `apps/api/routers/admin.py` to prevent Broken Object Level Authorization (BOLA). Restrict `TENANT_ADMIN` to exporting only their own tenant data while allowing `SYSTEM_ADMIN` global export access.

BUSINESS RATIONALE: Audit finding P1-TEN-001 identified a BOLA vulnerability where any caller possessing the `TENANT_ADMIN` role could initiate a tenant data export (GDPR / SOC2 data dump) for arbitrary tenant IDs specified in the path URL. Without validating that the authenticated principal's tenant binding matches the path parameter `tenant_id`, malicious or compromised tenant administrators could extract sensitive cross-tenant data, directly violating tenant isolation invariant INV-TEN-002 and OWASP API Security Top 10 (API1:2023).

ARCHITECTURAL OWNER: Security Architect

ARCHITECTURAL CONTEXT: INV-TEN-002 (strict server-derived tenant isolation), INV-IAM-001 (role-based and attribute-based access control), `docs/14-iam/IAM-SPEC.md` §3, `docs/26-api/API-STANDARDS.md` §5.

## Canonical specification references

- `docs/14-iam/IAM-SPEC.md#tenant-isolation-boundary`
- `docs/26-api/API-STANDARDS.md#5-tenant-context-enforcement`
- `AGENTS.md#3-strict-prohibitions`
- `execution/DEFINITION-OF-DONE.md`

If references conflict, return BLOCKED.

## Preconditions

- AR-005 PASS (authentication adapter fail-closed in place).
- `apps/api/routers/admin.py` exists with `export_tenant_data` endpoint.
- `apps/api/middleware/authorization.py` provides `require_roles`.

## Change boundary

READ_SET:
- `apps/api/routers/admin.py` (full file)
- `apps/api/middleware/authorization.py` (roles and principal context definitions)
- `packages/backend/src/revpilot/shared/context.py` (PrincipalContext structure)

WRITE_SET:
- `apps/api/routers/admin.py`
- `tests/integration/test_admin_bola.py`

CREATE:
- `tests/integration/test_admin_bola.py`

MODIFY:
- `apps/api/routers/admin.py` — lines 71-83:
  - Add tenant validation check inside `export_tenant_data`:
    - If caller lacks `SYSTEM_ADMIN` role: verify `str(principal.tenant_id) == tenant_id` (or `principal.tenant_id.value == tenant_id`).
    - If mismatched, raise `HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "CROSS_TENANT_ACCESS_FORBIDDEN", "message": "Tenant admin cannot export data belonging to another tenant"})`.

DO_NOT_MODIFY:
- `apps/api/main.py`
- `apps/api/middleware/*`
- `packages/backend/src/revpilot/modules/*`
- Any file outside WRITE_SET

EXPECTED CHANGE SET:
- 1 router file modified with tenant binding guard.
- 1 new integration test file with 4 test cases.

## Symbol-level contract

MUST EXPORT/DEFINE:
- `apps/api/routers/admin.py`:
  - `export_tenant_data(tenant_id: str, principal: PrincipalContext)`:
    - Verifies role authorization via `Depends(require_roles("TENANT_ADMIN", "SYSTEM_ADMIN"))`.
    - If `SYSTEM_ADMIN` in `principal.roles`, permits export of any `tenant_id`.
    - If `SYSTEM_ADMIN` not in `principal.roles`, verifies `principal.tenant_id` matches `tenant_id`.
    - Returns HTTP 202 Accepted on authorized export.
    - Raises HTTP 403 Forbidden on tenant mismatch.
- `tests/integration/test_admin_bola.py`:
  - `test_tenant_admin_export_own_tenant_succeeds()`: `TENANT_ADMIN` exporting matching tenant ID returns HTTP 202.
  - `test_tenant_admin_export_other_tenant_returns_403()`: `TENANT_ADMIN` attempting export of different tenant ID returns HTTP 403.
  - `test_system_admin_export_any_tenant_succeeds()`: `SYSTEM_ADMIN` exporting arbitrary tenant ID returns HTTP 202.
  - `test_unauthenticated_export_returns_401()`: Unauthenticated request to export endpoint returns HTTP 401.

MUST NOT:
- Permit `TENANT_ADMIN` to export data from any tenant other than their own.
- Bypass tenant check through query parameters or custom headers.
- Return 200/202 when tenant IDs mismatch for non-system administrators.

## Input/output and validation

INPUT: HTTP POST to `/api/v1/admin/tenants/{tenant_id}/exports` with Bearer token.
OUTPUT: HTTP 202 `{"export_id": "exp_...", "tenant_id": "...", "status": "EXPORTING", "created_at": "..."}`.
INVALID INPUT:
- Request with mismatched tenant ID by TENANT_ADMIN → HTTP 403 Forbidden.
- Unauthenticated request → HTTP 401 Unauthorized.
VALIDATION RULES: Principal tenant ID equality check against path parameter `tenant_id`.
STATE TRANSITIONS: Enqueues tenant export job if authorized.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `CROSS_TENANT_ACCESS_FORBIDDEN` | TENANT_ADMIN exports other tenant ID | 403 | no | Tenant admin cannot export data belonging to another tenant | yes | `admin_bola_rejections_total` |
| `UNAUTHORIZED` | Missing or invalid authentication token | 401 | no | Authentication token missing or invalid | yes | `auth_failures_total` |
| `FORBIDDEN` | Principal lacks TENANT_ADMIN or SYSTEM_ADMIN | 403 | no | Insufficient permissions for requested operation | yes | `authz_failures_total` |

## Security contract

AUTHENTICATION: Enforced via `get_current_principal` dependency.
AUTHORIZATION: Role check enforces `TENANT_ADMIN` or `SYSTEM_ADMIN`.
TENANT: Strict tenant context binding: path parameter `tenant_id` must match `principal.tenant_id` for tenant administrators.
PII: PROHIBITED — export job initialization does not return customer data in response body.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: Triggers export job pipeline only when tenant isolation check succeeds.
DEFAULT: DENY — non-system administrators cannot access cross-tenant objects.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE.
API CONTRACT: Conforms to `docs/26-api/API-STANDARDS.md` §5 and §12.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: Non-retryable on 403 / 401 client rejections.
TIMEOUT: Guard evaluation < 1ms.
IDEMPOTENCY: Idempotent job generation endpoint.
LOGGING: Security audit log emitted on cross-tenant access violation with principal ID, claimed tenant, and target tenant.
METRICS: Increment `admin_bola_rejections_total`.
FAILURE BEHAVIOR: Fail closed with HTTP 403.
ROLLBACK/COMPENSATION: Revert changes to `apps/api/routers/admin.py` and remove test file.

## Implementation requirements

1. Inspect `apps/api/routers/admin.py` lines 71-83.
2. In `export_tenant_data`:
   ```python
   is_system_admin = "SYSTEM_ADMIN" in principal.roles
   principal_tenant = principal.tenant_id.value if hasattr(principal.tenant_id, "value") else str(principal.tenant_id)
   if not is_system_admin and principal_tenant != tenant_id:
       raise HTTPException(
           status_code=status.HTTP_403_FORBIDDEN,
           detail={
               "code": "CROSS_TENANT_ACCESS_FORBIDDEN",
               "message": "Tenant admin cannot export data belonging to another tenant",
           },
       )
   ```
3. Create `tests/integration/test_admin_bola.py` using FastAPI TestClient to test:
   - Tenant admin exporting their own tenant returns HTTP 202.
   - Tenant admin exporting another tenant returns HTTP 403.
   - System admin exporting any tenant returns HTTP 202.
   - Missing token returns HTTP 401.
4. Run test suite to verify no regressions.

## Tests and evaluations

TESTS REQUIRED:
- 4 integration test cases in `tests/integration/test_admin_bola.py`.
- Regression check: `pytest tests/ -q` exits 0.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: BOLA guard evaluation adds < 0.5ms latency.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/integration/test_admin_bola.py -v && python -m pytest tests/ -q
```

EXPECTED:
- `pytest tests/integration/test_admin_bola.py` exits 0 with 4 passed.
- Full pytest suite exits 0.

## Binary acceptance criteria

- `AC-AR-024-01`: PASS only if TENANT_ADMIN attempting to export another tenant's data returns HTTP 403 Forbidden with detail error code `CROSS_TENANT_ACCESS_FORBIDDEN`.
- `AC-AR-024-02`: PASS only if `python -m pytest tests/integration/test_admin_bola.py` executes 4 tests and all 4 pass with exit code 0.

## Postconditions

- `export_tenant_data` endpoint strictly enforces tenant isolation against BOLA attacks.
- Cross-tenant export requests by tenant admins fail closed with HTTP 403 Forbidden.
- System admins maintain cross-tenant operational export capabilities.
- 4 integration test cases passing with zero regressions.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Clear objective: prevent BOLA on admin tenant export |
| Dependency clarity | 2 | Single dependency: AR-005 |
| File boundary clarity | 2 | Exactly 1 router file modified (lines 71-83) and 1 test file created |
| Contract clarity | 2 | Precise role and tenant match logic defined with explicit HTTP status codes |
| Failure behavior | 2 | Explicit fail-closed 403 on mismatch, 401 on unauthenticated |
| Security/tenancy | 2 | Core tenant isolation security invariant enforcement (INV-TEN-002) |
| Testability | 2 | 4 specific test cases with clear role/tenant combinations |
| Verification | 2 | Deterministic pytest test runner verification |
| Acceptance criteria | 2 | 2 machine-verifiable criteria |
| Reasoning independence | 2 | Complete implementation pattern given; no architecture decisions needed |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Allow `TENANT_ADMIN` to access cross-tenant data under any condition.
- Rely on client-supplied headers for tenant verification.
- Modify authorization models or database schemas.
- Touch files outside the explicit WRITE_SET.

## Required executor report

```text
TASK TASK-AR-024 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_admin_bola.py
FILES MODIFIED: apps/api/routers/admin.py
UNEXPECTED FILES: NONE
TESTS: 4 admin BOLA prevention tests PASS, full suite PASS
COMMANDS AND EXIT CODES: pytest admin bola tests → 0, pytest full → 0
ACCEPTANCE: AC-AR-024-01: PASS|FAIL, AC-AR-024-02: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: NONE
```
