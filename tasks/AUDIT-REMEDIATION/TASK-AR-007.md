# TASK-AR-007 — SCIM Bearer Authentication and Server-Side Tenant Binding

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 16
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IDENTITY-BOUNDARY
FEATURE: SCIM-AUTH
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-005
UNLOCKS: AR-008

## Objective and rationale

OBJECTIVE: Replace SCIM token string parsing in `apps/api/routers/scim.py` `verify_scim_bearer` function with credential repository lookup. Map token to tenant server-side. Reject if path `tenant_id` differs from credential tenant.

BUSINESS RATIONALE: Finding P0-SEC-002 proved SCIM endpoints accept arbitrary tokens via string parsing without cryptographic verification or persistence lookup. An attacker could provision/deprovision users in any tenant by crafting a token with the target tenant prefix.

ARCHITECTURAL OWNER: Security Architect, Identity Lead

ARCHITECTURAL CONTEXT: INV-IAM-001 (boundary verification), INV-TEN-001 (server-derived tenant), INV-TEN-002 (untrusted headers discarded).

## Canonical specification references

- `docs/14-iam/IAM-SPEC.md#scim-provisioning`
- `docs/14-iam/IAM-SPEC.md#credential-lifecycle`
- `AGENTS.md#3-strict-prohibitions` (zero unauthorized external mutations)

If references conflict, return BLOCKED.

## Preconditions

- AR-005 PASS (auth fail-closed verified).
- `apps/api/routers/scim.py` exists with `verify_scim_bearer` function.

## Change boundary

READ_SET:
- `apps/api/routers/scim.py` (full file, 271 lines)
- `packages/backend/src/revpilot/modules/identity/` (existing models and ports)
- `packages/backend/src/revpilot/shared/identifiers.py`
- `packages/backend/src/revpilot/shared/errors.py`

WRITE_SET:
- `apps/api/routers/scim.py`
- `packages/backend/src/revpilot/modules/identity/ports/scim_credential.py`
- `packages/backend/src/revpilot/modules/identity/domain/scim_credential.py`

CREATE:
- `packages/backend/src/revpilot/modules/identity/ports/scim_credential.py`
- `packages/backend/src/revpilot/modules/identity/domain/scim_credential.py`

MODIFY:
- `apps/api/routers/scim.py` — Lines 38-80 (`verify_scim_bearer`): Replace string parsing with `ScimCredentialPort.verify(token_hash)`.

DO_NOT_MODIFY:
- `apps/api/middleware/authentication.py`
- `apps/api/main.py`
- `packages/backend/src/revpilot/modules/identity/domain/models.py`

EXPECTED CHANGE SET:
- 2 new files (port interface + domain model).
- 1 modified file (scim.py verify function).

## Symbol-level contract

MUST EXPORT/DEFINE:

`packages/backend/src/revpilot/modules/identity/domain/scim_credential.py`:
```python
@dataclass(frozen=True, slots=True)
class ScimCredential:
    credential_id: str
    tenant_id: TenantId
    scopes: frozenset[str]
    expires_at: datetime
    created_at: datetime
    rotated_from: str | None  # previous credential_id if rotated
    is_active: bool
```

`packages/backend/src/revpilot/modules/identity/ports/scim_credential.py`:
```python
class ScimCredentialPort(Protocol):
    async def verify(self, token_hash: str) -> ScimCredential | None:
        """Look up credential by SHA-256 hash of raw token. Returns None if not found or inactive."""
        ...
```

Modified `verify_scim_bearer` in `apps/api/routers/scim.py`:
- Hash incoming token: `token_hash = hashlib.sha256(raw_token.encode()).hexdigest()`
- Look up: `credential = await scim_credential_port.verify(token_hash)`
- If `credential is None` → raise HTTPException 401 `SCIM_TOKEN_INVALID`
- If `credential.expires_at < datetime.now(timezone.utc)` → raise HTTPException 401 `SCIM_TOKEN_EXPIRED`
- If `str(credential.tenant_id) != tenant_id` (path param) → raise HTTPException 403 `SCIM_TENANT_MISMATCH`
- If `not credential.is_active` → raise HTTPException 401 `SCIM_TOKEN_REVOKED`
- Attach `credential` to `request.state.scim_credential`

MUST NOT:
- Parse token string to extract tenant/principal information.
- Trust path `tenant_id` as authoritative without server-side verification.
- Store raw tokens (only hashes).
- Accept expired or inactive credentials.

## Input/output and validation

INPUT: HTTP request with `Authorization: Bearer <token>` header, path parameter `tenant_id`.
OUTPUT: Request proceeds with verified `ScimCredential` on `request.state`, or HTTP 401/403 error.
INVALID INPUT: Missing/invalid/expired/wrong-tenant token → 401 or 403.
VALIDATION RULES: Token must resolve to active, non-expired credential whose tenant matches path.
STATE TRANSITIONS: NOT APPLICABLE.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `SCIM_TOKEN_MISSING` | No Authorization header | 401 | no | SCIM bearer token required | yes | `scim_auth_failures{reason="missing"}` |
| `SCIM_TOKEN_INVALID` | Token hash not found in repo | 401 | no | Invalid SCIM credential | yes | `scim_auth_failures{reason="invalid"}` |
| `SCIM_TOKEN_EXPIRED` | Credential past expires_at | 401 | no | SCIM credential expired | yes | `scim_auth_failures{reason="expired"}` |
| `SCIM_TOKEN_REVOKED` | Credential is_active=false | 401 | no | SCIM credential revoked | yes | `scim_auth_failures{reason="revoked"}` |
| `SCIM_TENANT_MISMATCH` | credential.tenant_id != path tenant_id | 403 | no | Credential does not authorize this tenant | yes | `scim_auth_failures{reason="tenant_mismatch"}` |

## Security contract

AUTHENTICATION: SCIM bearer token verified via credential repository hash lookup.
AUTHORIZATION: Credential scopes checked (future: AR-008 enforces operation-level scopes).
TENANT: Server-derived from credential, not from path parameter. Path parameter is input to be validated against credential.
PII: PROHIBITED — do not log raw tokens.
SECRET ACCESS: Token hash stored, not raw token.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY — any verification failure → reject.

## Specialized contracts

DATA CONTRACT: `ScimCredential` domain model — immutable frozen dataclass.
API CONTRACT: SCIM 2.0 endpoints unchanged in URL structure; authentication behavior changed.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: NOT APPLICABLE — authentication is not retried automatically.
TIMEOUT: Credential lookup < 1 second.
IDEMPOTENCY: Authentication check is idempotent.
LOGGING: Log auth failures with tenant_id and credential_id (not raw token). Structured event: `scim.auth.failed`.
METRICS: `scim_auth_failures{reason}` counter.
FAILURE BEHAVIOR: Credential repo unavailable → 401 (fail-closed, not 500).
ROLLBACK/COMPENSATION: Revert scim.py changes.

## Implementation requirements

1. Create `packages/backend/src/revpilot/modules/identity/domain/scim_credential.py` with `ScimCredential` dataclass.
2. Create `packages/backend/src/revpilot/modules/identity/ports/scim_credential.py` with `ScimCredentialPort` protocol.
3. Modify `apps/api/routers/scim.py` `verify_scim_bearer` (lines 38-80):
   - Get `scim_credential_port` from `request.app.state`.
   - If port is None → raise 401 (service unavailable).
   - Hash token with SHA-256.
   - Lookup credential.
   - Validate: exists, active, not expired, tenant matches path.
4. Ensure all SCIM routes still use `dependencies=[Depends(verify_scim_bearer)]`.

## Tests and evaluations

TESTS REQUIRED:
- Unit tests for `ScimCredential` construction.
- Integration tests deferred to AR-009 (SCIM negative matrix).

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Auth check < 1 second.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "from revpilot.modules.identity.domain.scim_credential import ScimCredential; print('PASS: ScimCredential importable')" && python -c "from revpilot.modules.identity.ports.scim_credential import ScimCredentialPort; print('PASS: ScimCredentialPort importable')" && python -m pytest tests/ -q
```

EXPECTED: exit code 0, both imports succeed, full suite passes.

## Binary acceptance criteria

- `AC-AR-007-01`: PASS only if SCIM request without Bearer token → 401.
- `AC-AR-007-02`: PASS only if SCIM request with token not in credential repository → 401.
- `AC-AR-007-03`: PASS only if SCIM request with valid token but `path.tenant_id != credential.tenant_id` → 403.
- `AC-AR-007-04`: PASS only if SCIM request with expired token → 401.
- `AC-AR-007-05`: PASS only if SCIM request with valid, matching token → request proceeds.

## Postconditions

- `ScimCredential` domain model and `ScimCredentialPort` protocol exist.
- `verify_scim_bearer` uses credential repository, not string parsing.
- Full test suite passes.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Replace string parsing with repo lookup |
| Dependency clarity | 2 | Single upstream: AR-005 |
| File boundary clarity | 2 | 2 CREATE, 1 MODIFY |
| Contract clarity | 2 | Exact dataclass and protocol specified |
| Failure behavior | 2 | Every invalid credential → 401/403 |
| Security/tenancy | 2 | Core SCIM security remediation |
| Testability | 2 | 5 acceptance criteria, tests in AR-009 |
| Verification | 2 | Import checks + pytest |
| Acceptance criteria | 2 | 5 machine-verifiable criteria |
| Reasoning independence | 2 | No architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Parse token strings to extract tenant information.
- Store raw tokens.
- Trust path parameters as authoritative.

## Required executor report

```text
TASK TASK-AR-007 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: scim_credential.py (domain), scim_credential.py (ports)
FILES MODIFIED: apps/api/routers/scim.py
UNEXPECTED FILES: NONE
TESTS: imports PASS, full suite PASS
COMMANDS AND EXIT CODES: import checks → 0, pytest → 0
ACCEPTANCE: AC-AR-007-01..05: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-008
```
