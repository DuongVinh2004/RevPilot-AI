# TASK-AR-008 — SCIM Persistence Adapter — Real User/Group CRUD with Repository

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 16
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IDENTITY-BOUNDARY
FEATURE: SCIM-PERSISTENCE
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-007
UNLOCKS: AR-009

## Objective and rationale

OBJECTIVE: Replace in-memory dictionary SCIM storage with persistence adapter implementing `ScimUserRepository` port. POST creates real records, DELETE soft-deletes (active=false), GET reads from persistence, and duplicate externalId returns 409.

BUSINESS RATIONALE: Finding P0-SEC-002 proved SCIM endpoints use in-memory dicts (`_users`, `_groups`) that are lost on restart, return hardcoded `usr_admin_001`, and do not perform real provisioning/deprovisioning. Identity provisioning without persistence means users created via IdP sync disappear on deployment.

ARCHITECTURAL OWNER: Identity Lead, Platform Architect

ARCHITECTURAL CONTEXT: INV-TEN-001 (tenant isolation), ADR-0003 (hexagonal ports/adapters), ADR-0005 (PostgreSQL persistence).

## Canonical specification references

- `docs/14-iam/IAM-SPEC.md#scim-provisioning`
- `docs/27-database/DATABASE-SCHEMA.md` (if SCIM tables defined)
- RFC 7644 (SCIM 2.0 Protocol)

If references conflict, return BLOCKED.

## Preconditions

- AR-007 PASS (SCIM auth and tenant binding in place).
- `ScimCredentialPort` and `ScimCredential` domain model exist.

## Change boundary

READ_SET:
- `apps/api/routers/scim.py` (full file)
- `packages/backend/src/revpilot/modules/identity/` (existing adapters and ports)
- `packages/backend/src/revpilot/modules/tenancy/adapters/` (reference PostgreSQL adapter pattern)

WRITE_SET:
- `apps/api/routers/scim.py`
- `packages/backend/src/revpilot/modules/identity/ports/scim_repository.py`
- `packages/backend/src/revpilot/modules/identity/adapters/scim_repository.py`

CREATE:
- `packages/backend/src/revpilot/modules/identity/ports/scim_repository.py`
- `packages/backend/src/revpilot/modules/identity/adapters/scim_repository.py`

MODIFY:
- `apps/api/routers/scim.py` — Replace in-memory dict operations with repository port calls.

DO_NOT_MODIFY:
- `apps/api/middleware/*`
- `apps/api/main.py` (adapter wiring is a separate concern)
- `packages/backend/src/revpilot/modules/identity/domain/models.py`

EXPECTED CHANGE SET: 2 new files (port + adapter), 1 modified (scim.py routes).

## Symbol-level contract

MUST EXPORT/DEFINE:

`packages/backend/src/revpilot/modules/identity/ports/scim_repository.py`:
```python
class ScimUserRepositoryPort(Protocol):
    async def create_user(self, tenant_id: TenantId, user_data: dict) -> dict: ...
    async def get_user(self, tenant_id: TenantId, user_id: str) -> dict | None: ...
    async def list_users(self, tenant_id: TenantId, start_index: int, count: int, filter_expr: str | None) -> tuple[list[dict], int]: ...
    async def update_user(self, tenant_id: TenantId, user_id: str, patch_ops: list[dict]) -> dict | None: ...
    async def delete_user(self, tenant_id: TenantId, user_id: str) -> bool: ...
    async def get_user_by_external_id(self, tenant_id: TenantId, external_id: str) -> dict | None: ...
```

`packages/backend/src/revpilot/modules/identity/adapters/scim_repository.py`:
- `InMemoryScimUserRepository` implementing `ScimUserRepositoryPort`.
- Uses tenant-scoped dict: `dict[str, dict[str, dict]]` keyed by `(tenant_id, user_id)`.
- `create_user`: Generate UUID, check externalId uniqueness within tenant, store.
- `delete_user`: Set `active=false`, preserve record (soft-delete).
- `get_user_by_external_id`: Lookup within tenant scope.
- `list_users`: Support `startIndex`, `count`, basic `userName eq "..."` filter.

Modified SCIM routes in `apps/api/routers/scim.py`:
- `list_scim_users`: Call `repo.list_users(tenant_id, ...)` instead of reading `_users` dict.
- `create_scim_user`: Call `repo.create_user(...)`. Check `repo.get_user_by_external_id(...)` first → 409 if exists.
- `get_scim_user`: Call `repo.get_user(...)` → 404 if None.
- `delete_scim_user`: Call `repo.delete_user(...)` → 204 on success, 404 if not found.
- `patch_scim_user`: Call `repo.update_user(...)` → 404 if not found.
- Remove hardcoded `usr_admin_001` response.

MUST NOT:
- Use global mutable state (module-level dicts).
- Return hardcoded users.
- Allow cross-tenant user visibility.
- Hard-delete users (must soft-delete).

## Input/output and validation

INPUT: SCIM 2.0 JSON payloads (Users, Groups resources).
OUTPUT: SCIM 2.0 JSON responses with proper `schemas`, `id`, `meta` fields.
INVALID INPUT: Missing required fields → 400. Duplicate externalId → 409. Non-existent user → 404.
VALIDATION RULES: `userName` required. `externalId` unique per tenant. `id` is server-generated UUID.
STATE TRANSITIONS: Created (active=true) → Deactivated (active=false). Deactivated users can be re-created with same externalId (new UUID).

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `SCIM_USER_NOT_FOUND` | GET/PATCH/DELETE non-existent user | 404 | no | User not found | yes | `scim_errors{type="not_found"}` |
| `SCIM_DUPLICATE_USER` | POST with existing externalId | 409 | no | User with externalId already exists | yes | `scim_errors{type="duplicate"}` |
| `SCIM_INVALID_PAYLOAD` | Missing required fields | 400 | no | Invalid SCIM payload | yes | `scim_errors{type="invalid"}` |
| `SCIM_REPO_UNAVAILABLE` | Repository not configured | 503 | yes | SCIM service unavailable | yes | `scim_errors{type="unavailable"}` |

## Security contract

AUTHENTICATION: Handled by `verify_scim_bearer` (AR-007).
AUTHORIZATION: Credential scopes checked per operation.
TENANT: All operations scoped to credential's verified tenant_id. Cross-tenant access impossible.
PII: User records may contain PII (name, email). Audit logs must not contain full PII.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED — persistence only.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: SCIM User resource schema per RFC 7644.
API CONTRACT: SCIM 2.0 REST endpoints unchanged in URL structure.
EVENT CONTRACT: NOT APPLICABLE (future: provisioning events).
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: NOT APPLICABLE.
TIMEOUT: Repository operations < 5 seconds.
IDEMPOTENCY: POST with same externalId → 409 (idempotent detection). DELETE is idempotent.
LOGGING: `scim.user.created`, `scim.user.deactivated`, `scim.user.updated` structured events.
METRICS: `scim_operations{type, tenant}` counter.
FAILURE BEHAVIOR: Repository unavailable → 503.
ROLLBACK/COMPENSATION: NOT APPLICABLE for in-memory adapter.

## Implementation requirements

1. Create port interface `ScimUserRepositoryPort` with 6 methods.
2. Create `InMemoryScimUserRepository` implementing the port.
3. Modify all SCIM user routes to use repository port.
4. Remove all references to `_users` dict and hardcoded `usr_admin_001`.
5. Add 503 response when repository not available on app.state.

## Tests and evaluations

TESTS REQUIRED:
- Unit tests for `InMemoryScimUserRepository` CRUD operations.
- Integration tests deferred to AR-009.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE for in-memory adapter.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "from revpilot.modules.identity.ports.scim_repository import ScimUserRepositoryPort; print('PASS')" && python -c "from revpilot.modules.identity.adapters.scim_repository import InMemoryScimUserRepository; print('PASS')" && python -m pytest tests/ -q
```

EXPECTED: exit code 0.

## Binary acceptance criteria

- `AC-AR-008-01`: PASS only if POST `/scim/v2/{tid}/Users` creates user and GET returns same user.
- `AC-AR-008-02`: PASS only if DELETE sets user `active=false` and GET returns `active: false`.
- `AC-AR-008-03`: PASS only if POST duplicate `externalId` within same tenant → 409.
- `AC-AR-008-04`: PASS only if GET `/scim/v2/{tid}/Users` does not return hardcoded `usr_admin_001`.
- `AC-AR-008-05`: PASS only if SCIM filter `userName eq "..."` returns matching users only.

## Postconditions

- SCIM routes use repository port, not in-memory dicts.
- No hardcoded users in responses.
- Full test suite passes.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Replace dict with repository CRUD |
| Dependency clarity | 2 | Single upstream: AR-007 |
| File boundary clarity | 2 | 2 CREATE, 1 MODIFY |
| Contract clarity | 2 | Port protocol and adapter fully specified |
| Failure behavior | 2 | Repo unavailable → 503, not found → 404 |
| Security/tenancy | 2 | Tenant-scoped operations |
| Testability | 2 | 5 acceptance criteria |
| Verification | 2 | Import + pytest |
| Acceptance criteria | 2 | 5 machine-verifiable criteria |
| Reasoning independence | 2 | No architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Use global mutable state.
- Hard-delete users.
- Return hardcoded user records.

## Required executor report

```text
TASK TASK-AR-008 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: scim_repository.py (ports), scim_repository.py (adapters)
FILES MODIFIED: apps/api/routers/scim.py
UNEXPECTED FILES: NONE
TESTS: imports PASS, full suite PASS
COMMANDS AND EXIT CODES: import checks → 0, pytest → 0
ACCEPTANCE: AC-AR-008-01..05: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-009
```
