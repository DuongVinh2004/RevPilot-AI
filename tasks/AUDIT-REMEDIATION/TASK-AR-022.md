# TASK-AR-022 — Admin Operations — Real Persistence for Provision/Export/Delete

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 2
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: DOMAIN-EXECUTION
FEATURE: ADMIN-PERSISTENCE
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-017..021
DEPENDS_ON: AR-006
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Admin provision, export, and delete operations in `apps/api/routers/admin.py` lines 34-96 must interact with the real tenant repository. When `tenant_repo` is absent, endpoints must fail-closed with HTTP 503. The export endpoint must enforce cross-tenant authorization: a `TENANT_ADMIN` is restricted to exporting their own tenant (`principal.tenant_id == path.tenant_id`) and receives HTTP 403 on mismatch, while `SYSTEM_ADMIN` is permitted to export any tenant.

BUSINESS RATIONALE: Zero-trust audit findings P1-DOM-001 and P1-TEN-001 established that `provision_tenant`, `export_tenant_data`, and `cascade_delete_tenant` returned mock JSON dictionaries without persisting tenant boundaries to PostgreSQL, without checking repository readiness, and without verifying caller tenant ownership in export requests. This allowed unauthenticated or unauthorized cross-tenant export dispatches violating INV-TEN-001 (tenant boundary isolation) and created ghost tenants unrecorded in the system of record.

ARCHITECTURAL OWNER: Platform Architect, Tenancy Lead

ARCHITECTURAL CONTEXT: INV-TEN-001 (Strict Tenant Isolation), INV-TEN-002 (Tenant Lifecycle Auditability), ADR-0004 (Tenant Aggregate Persistence), docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md, docs/26-api/API-STANDARDS.md §10.

## Canonical specification references

- `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md#tenant-provisioning`
- `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md#tenant-export-gdpr`
- `docs/26-api/API-STANDARDS.md#101-provision-tenant-api`
- `docs/26-api/API-STANDARDS.md#103-export-tenant-data-api`
- `execution/DEFINITION-OF-DONE.md`

If references conflict, return BLOCKED.

## Preconditions

- AR-006 PASS (Readiness probe dependency-aware).
- `apps/api/routers/admin.py` exists with `/admin/tenants` endpoints.
- `revpilot.modules.tenancy.domain.models` exports `Tenant`, `TenantStatus`, `SubscriptionTier`, `Entitlement`.
- `revpilot.shared.identifiers` exports `TenantId`, `OrganizationId`.

## Change boundary

READ_SET:
- `apps/api/routers/admin.py`
- `packages/backend/src/revpilot/modules/tenancy/adapters/postgres_repository.py`
- `packages/backend/src/revpilot/modules/tenancy/domain/models.py`
- `apps/api/middleware/authorization.py`

WRITE_SET:
- `apps/api/routers/admin.py`
- `tests/integration/test_admin_persistence.py`

CREATE:
- `tests/integration/test_admin_persistence.py`

MODIFY:
- `apps/api/routers/admin.py` — Lines 34-96:
  - `provision_tenant`: Check `repo = getattr(request.app.state, "tenant_repo", None)`. If None, raise HTTP 503. Otherwise, construct and persist `Tenant` entity via `repo.async_save_tenant(...)`.
  - `export_tenant_data`: Accept `request: Request`. Check `repo = getattr(request.app.state, "tenant_repo", None)`. If None, raise HTTP 503. If caller does not possess `SYSTEM_ADMIN` role and `str(principal.tenant_id) != tenant_id`, raise HTTP 403 (`AuthorizationError` / 403 Forbidden).
  - `cascade_delete_tenant`: Accept `request: Request`. Check `repo = getattr(request.app.state, "tenant_repo", None)`. If None, raise HTTP 503.

DO_NOT_MODIFY:
- `packages/backend/src/revpilot/modules/tenancy/*`
- `apps/api/routers/causal.py`
- `apps/api/routers/investigations.py`
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 3 endpoints modified in `apps/api/routers/admin.py`, 1 new integration test file (`tests/integration/test_admin_persistence.py`).

## Symbol-level contract

MUST EXPORT/DEFINE:

Modified endpoint signatures in `apps/api/routers/admin.py`:
```python
@router.post("/tenants", status_code=status.HTTP_201_CREATED)
async def provision_tenant(
    payload: TenantProvisionRequest,
    request: Request,
    principal: PrincipalContext = Depends(require_system_admin()),
) -> dict[str, Any]:
    repo = getattr(request.app.state, "tenant_repo", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tenant repository unavailable",
        )
    ...
```

```python
@router.post("/tenants/{tenant_id}/exports", status_code=status.HTTP_202_ACCEPTED)
async def export_tenant_data(
    tenant_id: str,
    request: Request,
    principal: PrincipalContext = Depends(require_roles("TENANT_ADMIN", "SYSTEM_ADMIN")),
) -> dict[str, Any]:
    repo = getattr(request.app.state, "tenant_repo", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tenant repository unavailable",
        )
    if "SYSTEM_ADMIN" not in principal.roles:
        if str(principal.tenant_id) != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant admin of tenant '{principal.tenant_id}' cannot export data for tenant '{tenant_id}'",
            )
    ...
```

```python
@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_202_ACCEPTED)
async def cascade_delete_tenant(
    tenant_id: str,
    request: Request,
    principal: PrincipalContext = Depends(require_system_admin()),
) -> dict[str, Any]:
    repo = getattr(request.app.state, "tenant_repo", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tenant repository unavailable",
        )
    ...
```

MUST NOT:
- Allow `provision_tenant` to succeed when `tenant_repo` is None.
- Allow `export_tenant_data` to succeed when `tenant_repo` is None.
- Allow `cascade_delete_tenant` to succeed when `tenant_repo` is None.
- Allow `TENANT_ADMIN` to export data for any `tenant_id` other than their own.
- Bypass tenant isolation checks for non-`SYSTEM_ADMIN` principals.

## Input/output and validation

INPUT:
- POST `/api/v1/admin/tenants`: `{"name": "Acme Corp", "slug": "acme", "tier": "ENTERPRISE", "admin_email": "admin@acme.com"}`
- POST `/api/v1/admin/tenants/{tenant_id}/exports`
- DELETE `/api/v1/admin/tenants/{tenant_id}`

OUTPUT:
- POST `/admin/tenants` 201: `{"tenant_id": "tnt_...", "name": "...", "slug": "...", "status": "ACTIVE", "created_at": "..."}`
- POST `/admin/tenants/{tenant_id}/exports` 202: `{"export_id": "exp_...", "tenant_id": "...", "status": "EXPORTING", "created_at": "..."}`
- DELETE `/admin/tenants/{tenant_id}` 202: `{"deletion_job_id": "del_...", "tenant_id": "...", "status": "DELETING"}`

INVALID INPUT:
- `tenant_repo` missing/None → HTTP 503 Service Unavailable.
- `TENANT_ADMIN` requesting export for different `tenant_id` → HTTP 403 Forbidden.
- Non-system admin calling `/admin/tenants` (provision) or `DELETE` → HTTP 403 Forbidden.

STATE TRANSITIONS:
- Provision: Creates and persists active Tenant in database.
- Export: Creates async export job record scoped to tenant.
- Delete: Initiates cascade deletion saga in database.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `SERVICE_UNAVAILABLE` | Tenant repository None / disconnected | 503 | yes | Tenant repository unavailable | yes | admin_repo_unavailable_total |
| `AUTHORIZATION_DENIED` | TENANT_ADMIN accessing another tenant | 403 | no | Tenant admin cannot export data for another tenant | yes | auth_denied_total |
| `AUTHORIZATION_DENIED` | Non-admin calling admin endpoint | 403 | no | Sufficient administrative role required | yes | auth_denied_total |
| `VALIDATION_ERROR` | Malformed tenant request | 400 | no | Invalid request payload schema | yes | validation_failed_total |

## Security contract

AUTHENTICATION: Required (Bearer token via `get_current_tenant` / `require_roles`).
AUTHORIZATION:
- `provision_tenant`: `SYSTEM_ADMIN` only.
- `cascade_delete_tenant`: `SYSTEM_ADMIN` only.
- `export_tenant_data`: `SYSTEM_ADMIN` or `TENANT_ADMIN`.
TENANT: Multi-tenant ACL boundary strictly enforced. `TENANT_ADMIN` can only export data for `principal.tenant_id`. Cross-tenant export strictly forbidden.
PII: Export audit logs mask PII; tenant provisioning records admin email in compliance boundary.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: Database writes and async deletion/export scheduling.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: Persists to `revpilot.tenants` table matching schema in `001_initial_tenancy_schema.py`.
API CONTRACT: Conforms to docs/26-api/API-STANDARDS.md §10.1 and §10.3.
EVENT CONTRACT: Tenant lifecycle events recorded in audit log.
TEMPORAL CONTRACT: Cascade delete schedules durable saga workflow.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: Client retries on 503 with exponential backoff.
TIMEOUT: Provisioning and export dispatch < 2 seconds.
IDEMPOTENCY: Provisioning slug unique constraint; export generates unique export job ID.
LOGGING: Log all provisioning, export, and delete attempts at INFO/WARN level with correlation ID.
METRICS: Track `tenant_provision_total`, `tenant_export_total`, `tenant_delete_total`.
FAILURE BEHAVIOR: Fail-closed; return 503 when repository is unavailable.
ROLLBACK/COMPENSATION: Database transaction rollback on persistence failure.

## Implementation requirements

1. In `apps/api/routers/admin.py`:
   - Import `HTTPException` from `fastapi` and `TenantId`, `OrganizationId`, `SubscriptionTier`, `Entitlement`, `TenantStatus`, `Tenant`, `UtcDateTime`.
   - Update `provision_tenant`:
     - Retrieve `repo = getattr(request.app.state, "tenant_repo", None)`.
     - If repo is None, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tenant repository unavailable")`.
     - Construct `TenantId(t_id)` and `Tenant` entity, then `await repo.async_save_tenant(tenant)`.
   - Update `export_tenant_data`:
     - Add parameter `request: Request`.
     - Retrieve `repo = getattr(request.app.state, "tenant_repo", None)`.
     - If repo is None, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tenant repository unavailable")`.
     - Check: If `"SYSTEM_ADMIN" not in principal.roles`:
       If `str(principal.tenant_id) != tenant_id`, raise `HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant admin cannot export data for another tenant")`.
   - Update `cascade_delete_tenant`:
     - Add parameter `request: Request`.
     - Retrieve `repo = getattr(request.app.state, "tenant_repo", None)`.
     - If repo is None, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tenant repository unavailable")`.
2. Create `tests/integration/test_admin_persistence.py` with 5 tests:
   - `test_provision_tenant_repo_none_returns_503`: With `tenant_repo=None`, provisioning returns 503.
   - `test_provision_tenant_success_persists`: With mock `tenant_repo`, provisioning saves tenant and returns 201.
   - `test_export_tenant_repo_none_returns_503`: With `tenant_repo=None`, export returns 503.
   - `test_tenant_admin_export_other_tenant_returns_403`: `TENANT_ADMIN` exporting different tenant ID returns 403.
   - `test_system_admin_export_any_tenant_returns_202`: `SYSTEM_ADMIN` exporting any tenant ID returns 202.
   - `test_cascade_delete_repo_none_returns_503`: With `tenant_repo=None`, delete returns 503.

## Tests and evaluations

TESTS REQUIRED:
- `tests/integration/test_admin_persistence.py` (6 tests).

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Admin operations dispatch in < 150ms.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/integration/test_admin_persistence.py -v
```

EXPECTED: exit code 0, 6/6 admin persistence tests pass.

## Binary acceptance criteria

- `AC-AR-022-01`: PASS only if `POST /api/v1/admin/tenants` returns HTTP 503 when `tenant_repo` is None.
- `AC-AR-022-02`: PASS only if `POST /api/v1/admin/tenants/{tenant_id}/exports` by a `TENANT_ADMIN` whose `tenant_id` does not match the URL parameter returns HTTP 403.
- `AC-AR-022-03`: PASS only if `POST /api/v1/admin/tenants/{tenant_id}/exports` by a `SYSTEM_ADMIN` returns HTTP 202 regardless of the tenant ID in the URL.
- `AC-AR-022-04`: PASS only if `DELETE /api/v1/admin/tenants/{tenant_id}` returns HTTP 503 when `tenant_repo` is None.
- `AC-AR-022-05`: PASS only if `python -m pytest tests/integration/test_admin_persistence.py -v` exits 0 with all tests passing.

## Postconditions

- Admin provision, export, and delete operations fail-closed with HTTP 503 when repository is disconnected.
- Provisioning persists real tenant records to repository.
- Tenant isolation on data exports is enforced with HTTP 403 for unauthorized tenant admins.
- Verification command exits 0.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Real persistence, 503 fail-closed, and cross-tenant ACL rules explicitly specified |
| Dependency clarity | 2 | Depends on AR-006; clear tenancy aggregate integration |
| File boundary clarity | 2 | 1 MODIFY (`admin.py`), 1 CREATE (`test_admin_persistence.py`) |
| Contract clarity | 2 | Error codes, HTTP statuses, and input/output contracts fully documented |
| Failure behavior | 2 | Clear 503 fail-closed behavior when repo is absent |
| Security/tenancy | 2 | Cross-tenant export ACL checks explicitly defined and verified |
| Testability | 2 | 6 isolated test cases with mock repository and varying principal roles |
| Verification | 2 | Single offline hermetic pytest command |
| Acceptance criteria | 2 | 5 binary machine-verifiable criteria |
| Reasoning independence | 2 | Explicit control flow provided; zero architectural leeway |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Return 201/202 when `tenant_repo` is None.
- Allow `TENANT_ADMIN` to access or export data of other tenants.
- Hardcode static mock responses that bypass database persistence.

## Required executor report

```text
TASK TASK-AR-022 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_admin_persistence.py
FILES MODIFIED: apps/api/routers/admin.py
UNEXPECTED FILES: NONE
TESTS: 6 admin persistence tests PASS
COMMANDS AND EXIT CODES: pytest admin tests → 0
ACCEPTANCE: AC-AR-022-01: PASS|FAIL, AC-AR-022-02: PASS|FAIL, AC-AR-022-03: PASS|FAIL, AC-AR-022-04: PASS|FAIL, AC-AR-022-05: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: ALL DOMAIN-EXECUTION REMEDIATIONS COMPLETE
```
