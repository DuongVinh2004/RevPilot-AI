# TASK-AR-013 — Approval Verification Chain — Tenant, Expiry, Tier, Self-Approval, Digest

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 14
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: APPROVAL-ACTION
FEATURE: APPROVAL-VERIFY-CHAIN
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-012
UNLOCKS: AR-014

## Objective and rationale

OBJECTIVE: Enforce strict 7-condition verification chains on both `grant_approval` (`POST /approvals/{approval_id}/approve`) and `dispatch_action` (`POST /actions/dispatch`) endpoints in `apps/api/routers/approvals.py`. Eliminate hardcoded fallback mock approval record `appr_01h8x9m2k4p8` from `list_pending_approvals` (`GET /approvals`).

BUSINESS RATIONALE: Zero-trust audit finding P0-ACT-001 revealed critical security gaps in the approval-action lifecycle:
1. `grant_approval` only enforced an in-memory check for Separation of Duties (requester != approver), bypassing verification for record existence, tenant isolation, pending status, expiry TTL, tier authority limits, and cryptographic payload digest match.
2. `dispatch_action` checked kill switches and recorded intents without verifying that the referenced approval existed, was in `APPROVED` status, belonged to the calling tenant, was unexpired, matched the sealed cryptographic payload digest, or adhered to the active policy version.
3. `list_pending_approvals` leaked a hardcoded mock record (`appr_01h8x9m2k4p8`) whenever `approval_repo` was None, violating tenant isolation invariants (`INV-TEN-001`) and the anti-fabrication invariant (`AC-014`).
Remediating these gaps enforces fail-closed state machines and protects downstream external systems from unauthorized mutations (`INV-ACT-001`).

ARCHITECTURAL OWNER: Action Gateway Lead, Security Architect

ARCHITECTURAL CONTEXT: `INV-ACT-001` (Zero Unauthorized Mutation), `INV-ACT-002` (Cryptographic Digest Binding), `INV-ACT-003` (Zero Agent Self-Approval & Separation of Duties), `INV-TEN-001` (Zero Cross-Tenant Leakage), `AC-008` (Six-Point Continuous Revalidation), `AC-014` (Anti-Fabrication Invariant), `ADR-0012` (Action Approval Autonomy Boundary), `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md`.

## Canonical specification references

- `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md#11-non-negotiable-invariants` (§1.1 Invariant 1: Cryptographic Digest Binding; §1.1 Invariant 2: Strict Human-in-the-Loop Authority; §1.1 Invariant 3: Six-Point Continuous Revalidation; §5.2 Blast-Radius Ceilings and Approval Tiers)
- `docs/14-iam/IAM-SPEC.md#71-approval-tiers-and-spend-ceilings`
- `docs/14-iam/IAM-SPEC.md#72-separation-of-duties-and-human-in-the-loop-guarantees`
- `docs/26-api/API-STANDARDS.md#9-action-gateway-and-approval-endpoints`
- `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md`
- `AGENTS.md#anti-fabrication-invariant-ac-014`

If references conflict, return BLOCKED.

## Preconditions

- AR-012 PASS (Approval repository and models established).
- `apps/api/routers/approvals.py` exists.
- In-memory approval storage and repository adapter interfaces support query by ID, tenant scoping, and state transitions.
- Pytest environment operational (`python -m pytest tests/ -q` runs cleanly).

## Change boundary

READ_SET:
- `apps/api/routers/approvals.py` (full file, 263 lines)
- `packages/backend/src/revpilot/modules/approval/domain.py`
- `packages/backend/src/revpilot/modules/approval/policy/authority.py`
- `packages/backend/src/revpilot/modules/approval/policy/revalidation.py`
- `packages/backend/src/revpilot/shared/errors.py`
- `packages/backend/src/revpilot/shared/context.py`

WRITE_SET:
- `apps/api/routers/approvals.py`

CREATE: NONE

MODIFY:
- `apps/api/routers/approvals.py`:
  - `list_pending_approvals` (`GET /approvals`):
    - Remove hardcoded mock approval `appr_01h8x9m2k4p8`.
    - If `repo is not None`, retrieve items via `await repo.list_pending(tenant)`.
    - If `repo is None`, retrieve items from `request.app.state._pending_approvals_cache`, filtering items where `record.get("tenant_id") == str(tenant.tenant_id)` and `record.get("status") == "PENDING"`. If none found, return `{"items": [], "count": 0}`.
    - Guarantee zero occurrences of string `appr_01h8x9m2k4p8` in the file.
  - `grant_approval` (`POST /approvals/{approval_id}/approve`):
    - Enforce sequential 7-condition verification chain:
      1. Record exists: Retrieve record from `approval_repo` or `_pending_approvals_cache`. If not found, raise `NotFoundError` (HTTP 404).
      2. Tenant match: Assert `record.tenant_id == str(tenant.tenant_id)`. If mismatch, raise `AuthorizationError` (HTTP 403).
      3. Status == PENDING: Assert `record.status == "PENDING"`. If already approved, rejected, expired, etc., raise `HTTPException(status_code=409, detail="Approval request is not in PENDING status")` (HTTP 409).
      4. Not expired: Check `record.expiry_time > datetime.now(timezone.utc)`. If expired, update status to EXPIRED and raise `HTTPException(status_code=410, detail="Approval request has expired")` (HTTP 410).
      5. Separation of Duties (requester != approver): Assert `record.requester_principal_id != str(principal.principal_id)`. If identical, raise `AuthorizationError` (HTTP 403).
      6. Tier authority: Validate approver principal's tier meets or exceeds `record.required_approval_tier` and spend ceiling. If insufficient, raise `AuthorizationError` (HTTP 403).
      7. Digest match: If `payload.expected_payload_digest` is provided, assert it matches `record.payload_digest`. If mismatch, raise `HTTPException(status_code=409, detail="Payload digest mismatch")` (HTTP 409).
    - If all 7 conditions pass: update record status to `APPROVED`, record approver principal ID and timestamp, persist to repo/cache, and return HTTP 200 response.
  - `dispatch_action` (`POST /actions/dispatch`):
    - Enforce sequential 7-condition verification chain:
      1. Record exists: Look up approval record by `payload.approval_id`. If not found, raise `NotFoundError` (HTTP 404).
      2. Status == APPROVED: Assert `record.status == "APPROVED"`. If in PENDING, REJECTED, etc., raise `HTTPException(status_code=409, detail="Action dispatch rejected: approval record is not in APPROVED status")` (HTTP 409).
      3. Tenant match: Assert `record.tenant_id == str(tenant.tenant_id)`. If mismatch, raise `AuthorizationError` (HTTP 403).
      4. Not expired: Check `record.expiry_time > datetime.now(timezone.utc)`. If expired, raise `HTTPException(status_code=410, detail="Action dispatch rejected: approval request has expired")` (HTTP 410).
      5. Digest match: Verify payload digest or record digest matches expectation. If tampered or altered, raise `HTTPException(status_code=409, detail="Action dispatch rejected: payload digest mismatch")` (HTTP 409).
      6. Kill switch: Check if global, tenant, or capability kill switch is active via `killswitch_repo`. If engaged, raise `AuthorizationError("Action dispatch blocked: Emergency kill switch is actively engaged.")` (HTTP 403).
      7. Policy version: Verify `record.policy_digest` or active policy version remains current. If invalidated, raise `HTTPException(status_code=409, detail="Action dispatch rejected: policy version mismatch")` (HTTP 409).

DO_NOT_MODIFY:
- `apps/api/middleware/*`
- `packages/backend/src/revpilot/modules/*`
- `tests/*` (do not weaken or skip existing tests)
- Any file outside `apps/api/routers/approvals.py`

EXPECTED CHANGE SET: Exactly 1 file modified (`apps/api/routers/approvals.py`). Approximately 70-110 lines modified/added to integrate 7-step verification pipelines on approve and dispatch endpoints, plus clean removal of hardcoded mock.

## Symbol-level contract

MUST EXPORT/DEFINE:

Modified endpoints in `apps/api/routers/approvals.py`:
- `list_pending_approvals(request: Request, tenant: TenantContext = Depends(get_current_tenant)) -> dict[str, Any]`
  Returns `{"items": list[dict[str, Any]], "count": int}` without hardcoded mock items.
- `grant_approval(approval_id: str, payload: ApprovalDecisionRequest, request: Request, tenant: TenantContext = Depends(get_current_tenant), principal: PrincipalContext = Depends(require_human_approval_authority("TIER_1"))) -> dict[str, Any]`
  Executes 7-step verification: exists (404), tenant match (403), status==PENDING (409), not expired (410), requester!=approver (403), tier authority (403), digest match (409). Returns `{"approval_id": str, "status": "APPROVED", "approver_principal_id": str, "signed_at": str}`.
- `dispatch_action(payload: ActionDispatchPayload, request: Request, tenant: TenantContext = Depends(get_current_tenant), principal: PrincipalContext = Depends(require_roles("OPERATOR", "SYSTEM_ADMIN"))) -> dict[str, Any]`
  Executes 7-step verification: exists (404), status==APPROVED (409), tenant match (403), not expired (410), digest match (409), kill switch clear (403), policy version current (409). Returns `{"intent_id": str, "approval_id": str, "status": "EXECUTING", "idempotency_key": str}` with HTTP 202.

MUST NOT:
- Permit approval of unknown approval ID.
- Permit approval across tenant boundaries.
- Permit self-approval by original requester.
- Permit approval when status is not PENDING.
- Permit approval when record expiry TTL has elapsed.
- Permit approval when approver tier is insufficient.
- Permit approval when expected digest fails verification.
- Permit dispatch when approval is not in APPROVED status.
- Permit dispatch when approval record is expired.
- Permit dispatch when payload digest has changed or mismatched.
- Permit dispatch when record belongs to a different tenant.
- Permit dispatch when emergency kill switch is active.
- Return hardcoded fallback record `appr_01h8x9m2k4p8` or any fabricated approval ID.

## Input/output and validation

INPUT:
- `POST /approvals/{approval_id}/approve`: `approval_id: str`, `payload: ApprovalDecisionRequest` (`expected_payload_digest: str | None`, `reason: str | None`), authenticated tenant and principal contexts.
- `POST /actions/dispatch`: `payload: ActionDispatchPayload` (`approval_id: str`, `idempotency_key: str`), authenticated tenant and principal contexts.
- `GET /approvals`: Authenticated tenant context.

OUTPUT:
- `POST /approvals/{approval_id}/approve`: HTTP 200 JSON with approval status and approver principal metadata.
- `POST /actions/dispatch`: HTTP 202 JSON with intent ID, approval ID, execution status, idempotency key.
- `GET /approvals`: HTTP 200 JSON with filtered items array and count.

INVALID INPUT:
- Unknown `approval_id` → HTTP 404 NOT FOUND.
- Cross-tenant approval or dispatch → HTTP 403 FORBIDDEN.
- Self-approval attempt → HTTP 403 FORBIDDEN.
- Insufficient approval tier → HTTP 403 FORBIDDEN.
- Active kill switch during dispatch → HTTP 403 FORBIDDEN.
- Non-PENDING approval attempt or non-APPROVED dispatch attempt → HTTP 409 CONFLICT.
- Tampered payload or digest mismatch → HTTP 409 CONFLICT.
- Expired approval on approval or dispatch → HTTP 410 GONE.

VALIDATION RULES:
- Expiration check: `record.expiry_time > datetime.now(timezone.utc)`.
- Tenant check: `str(record.tenant_id) == str(tenant.tenant_id)`.
- Separation of Duties check: `record.requester_principal_id != str(principal.principal_id)`.
- Status checks: `record.status == "PENDING"` for approval, `record.status == "APPROVED"` for dispatch.
- Digest checks: SHA-256 match between client provided/computed digest and sealed record digest.

STATE TRANSITIONS:
- `PENDING` → `APPROVED` (via `POST /approvals/{approval_id}/approve`)
- `PENDING` → `REJECTED` (via `POST /approvals/{approval_id}/reject`)
- `PENDING` → `EXPIRED` (upon TTL lapse detected during evaluation)
- `APPROVED` → `EXECUTING` (via `POST /actions/dispatch`)

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `ERR_APPROVAL_NOT_FOUND` | Approval ID not present in repository or cache | 404 | no | Approval request not found | yes | `approval_lookup_failures_total{reason="not_found"}` |
| `ERR_CROSS_TENANT_ACCESS` | Tenant ID does not match approval record owner | 403 | no | Cross-tenant access forbidden | yes | `tenant_isolation_violations_total{endpoint="approvals"}` |
| `ERR_SEPARATION_OF_DUTIES` | Requester principal attempts to approve own request | 403 | no | Separation of Duties violation: requester cannot approve own action request | yes | `security_violations_total{type="sod"}` |
| `ERR_INSUFFICIENT_TIER` | Approver tier is lower than required approval tier | 403 | no | Principal lacks required approval tier authority | yes | `authorization_denials_total{reason="insufficient_tier"}` |
| `ERR_INVALID_APPROVAL_STATE` | Transition requested from incompatible state (e.g. approving APPROVED or dispatching PENDING) | 409 | no | Approval request is not in valid state for operation | yes | `approval_state_conflict_total` |
| `ERR_APPROVAL_EXPIRED` | Approval request exceeded TTL (>24h) | 410 | no | Approval request has expired | yes | `approval_expired_total` |
| `ERR_PAYLOAD_DIGEST_MISMATCH` | Provided or calculated digest does not match sealed digest | 409 | no | Action payload digest mismatch — tampering detected | yes | `security_violations_total{type="digest_mismatch"}` |
| `ERR_KILL_SWITCH_ACTIVE` | Active global, tenant, or capability kill switch engaged | 403 | no | Action dispatch blocked: Emergency kill switch is actively engaged | yes | `kill_switch_blocks_total` |
| `ERR_POLICY_VERSION_MISMATCH` | Sealed policy digest differs from active policy version | 409 | no | Action dispatch rejected: policy version mismatch | yes | `policy_revalidation_failures_total` |

## Security contract

AUTHENTICATION: Requires authenticated Bearer token via `get_current_tenant` and `get_current_principal`. Unauthenticated requests return HTTP 401.
AUTHORIZATION:
- `POST /approvals/{approval_id}/approve`: Requires human approval authority (`require_human_approval_authority("TIER_1")`). Agent delegate roles strictly rejected (`INV-ACT-003`). Separation of duties strictly enforced (requester != approver).
- `POST /actions/dispatch`: Requires `OPERATOR` or `SYSTEM_ADMIN` role (`require_roles("OPERATOR", "SYSTEM_ADMIN")`).
TENANT: Multi-tenant boundary enforced (`INV-TEN-001`). Approval records scoped to authenticated `tenant_id`. Cross-tenant lookup or action dispatch fails closed with HTTP 403.
PII: PROHIBITED in error messages and logs. Action payloads containing PII must not leak into unauthenticated logs.
SECRET ACCESS: PROHIBITED. Credentials and secrets must not be logged or returned in approval responses.
EXTERNAL ACTION: Governed mutation gate (`INV-ACT-001`). No physical mutation is dispatched unless all 7 verification checkpoints pass.
DEFAULT: DENY — any missing check, unhandled condition, or mismatched identifier results in fail-closed rejection.

## Specialized contracts

DATA CONTRACT: Approval record schema conforms to `ApprovalRequestRecord` (`APPROVAL-ACTION-LOOP-SPEC.md §3.1`). Fields: `id`, `decision_id`, `action_type`, `target_entity_refs`, `payload_digest`, `policy_digest`, `estimated_cost_usd`, `required_approval_tier`, `status`, `expiry_time`, `correlation_id`, `requester_principal_id`.
API CONTRACT: Conforms to `docs/26-api/API-STANDARDS.md §9` for Action Gateway and Approval Endpoints. Status codes: 200 OK (approve), 202 ACCEPTED (dispatch), 403 FORBIDDEN (auth/tenant/tier/sod), 404 NOT FOUND, 409 CONFLICT (state/digest/policy), 410 GONE (expired).
EVENT CONTRACT: Dispatch initiation logs structured intent to `action_ledger_repo` before executing external side effects.
TEMPORAL CONTRACT: NOT APPLICABLE — synchronous verification chain preceding workflow activity scheduling.
AGENT CONTRACT: Enforces `INV-ACT-003` — agent principals, planners, and automated workers are strictly barred from approving actions or signing approval requests.
MODEL CONTRACT: NOT APPLICABLE — deterministic cryptographic and authorization logic; no ML models invoked.
RAG CONTRACT: NOT APPLICABLE — no retrieval augmented generation in approval verification chain.

## Operational behavior

RETRY: Client operations are non-retryable on 400, 403, 404, 409, 410 errors without correcting state.
TIMEOUT: Endpoint evaluation executes in < 50ms (in-memory/indexed cache validation).
IDEMPOTENCY:
- Dispatch requires `idempotency_key` in `ActionDispatchPayload` and records intent in action ledger.
- Multiple approve calls on an already APPROVED record return HTTP 409 CONFLICT (fail-closed state machine).
LOGGING: All verification failures emit structured audit logs with `correlation_id`, `tenant_id`, `principal_id`, `approval_id`, and `failure_reason` without PII.
METRICS: Record counters for `approval_lookup_failures_total`, `tenant_isolation_violations_total`, `security_violations_total`, and `approval_expired_total`.
FAILURE BEHAVIOR: Fail-closed on all 7 verification steps. Any single failed check terminates evaluation immediately and returns designated HTTP error code.
ROLLBACK/COMPENSATION: Git revert to previous commit. In-memory state remains unmodified when any validation checkpoint fails.

## Implementation requirements

1. Inspect `apps/api/routers/approvals.py` lines 100-235.
2. In `list_pending_approvals` (`GET /approvals`):
   - Remove the fallback mock list containing `appr_01h8x9m2k4p8`.
   - If `repo is None`, filter `request.app.state._pending_approvals_cache` by `tenant_id == str(tenant.tenant_id)` and `status == "PENDING"`. Return `{"items": items, "count": len(items)}`.
   - Verify string `appr_01h8x9m2k4p8` is completely deleted.
3. In `grant_approval` (`POST /approvals/{approval_id}/approve`):
   - Retrieve approval record from `repo` or `_pending_approvals_cache`.
   - Check 1: Record exists. If not found, raise `NotFoundError` (HTTP 404).
   - Check 2: Tenant match (`record.get("tenant_id") == str(tenant.tenant_id)` or `record.tenant_id`). If mismatch, raise `AuthorizationError` (HTTP 403).
   - Check 3: Status == PENDING. If not PENDING, raise `HTTPException(status_code=409, detail="Approval request is not in PENDING status")`.
   - Check 4: Not expired. Compare `record.get("expiry_time")` with `datetime.now(timezone.utc)`. If expired, update status to EXPIRED and raise `HTTPException(status_code=410, detail="Approval request has expired")`.
   - Check 5: Separation of duties. Compare `record.get("requester_principal_id")` with `str(principal.principal_id)`. If matching, raise `AuthorizationError` (HTTP 403).
   - Check 6: Tier authority. Verify `principal` approval tier satisfies `record.get("required_approval_tier")` and spend limit. If insufficient, raise `AuthorizationError` (HTTP 403).
   - Check 7: Digest match. If `payload.expected_payload_digest` provided, compare with `record.get("payload_digest")`. If mismatch, raise `HTTPException(status_code=409, detail="Payload digest mismatch")`.
   - Transition record status to `APPROVED`, record approver ID and timestamp.
4. In `dispatch_action` (`POST /actions/dispatch`):
   - Check 1: Record exists. Look up `payload.approval_id` in repo or cache. If not found, raise `NotFoundError` (HTTP 404).
   - Check 2: Status == APPROVED. If status != `APPROVED` (e.g. `PENDING`), raise `HTTPException(status_code=409, detail="Action dispatch rejected: approval record is not in APPROVED status")`.
   - Check 3: Tenant match. Compare record tenant with `str(tenant.tenant_id)`. If mismatch, raise `AuthorizationError` (HTTP 403).
   - Check 4: Not expired. Compare `record.get("expiry_time")` with `datetime.now(timezone.utc)`. If expired, raise `HTTPException(status_code=410, detail="Action dispatch rejected: approval request has expired")`.
   - Check 5: Digest match. Verify payload digest against sealed record digest. If altered, raise `HTTPException(status_code=409, detail="Action dispatch rejected: payload digest mismatch")`.
   - Check 6: Kill switch. Evaluate `killswitch_repo` for GLOBAL and TENANT kill switches. If active, raise `AuthorizationError` (HTTP 403).
   - Check 7: Policy version. Check `record.get("policy_digest")` or policy version validity. If mismatched, raise `HTTPException(status_code=409, detail="Action dispatch rejected: policy version mismatch")`.
   - Dispatch to ledger if all 7 checks pass.
5. Run full test suite: `python -m pytest tests/ -q`.

## Tests and evaluations

TESTS REQUIRED:
- Unit / integration tests validating each of the 7 check rejections on approve and dispatch endpoints.
- Regression suite: `python -m pytest tests/ -q` exit 0.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Approval and dispatch verification latency < 50ms overhead per call.
MIGRATION REQUIREMENTS: NOT APPLICABLE — no database schema migration.

## Verification

COMMANDS:

```text
python -c "
import sys
with open('apps/api/routers/approvals.py', 'r', encoding='utf-8') as f:
    content = f.read()
if 'appr_01h8x9m2k4p8' in content:
    print('FAIL: hardcoded mock approval ID still present')
    sys.exit(1)
print('PASS: No hardcoded fallback approval ID found')
" && python -m pytest tests/ -q
```

EXPECTED: exit code 0, no hardcoded fallback ID found, all tests pass.

## Binary acceptance criteria

- `AC-AR-013-01`: PASS only if POST `/approvals/{approval_id}/approve` with requester == approver returns HTTP 403.
- `AC-AR-013-02`: PASS only if POST `/approvals/{approval_id}/approve` with unknown approval ID returns HTTP 404.
- `AC-AR-013-03`: PASS only if POST `/actions/dispatch` referencing an approval in PENDING status returns HTTP 409.
- `AC-AR-013-04`: PASS only if POST `/actions/dispatch` referencing an expired approval returns HTTP 410.
- `AC-AR-013-05`: PASS only if POST `/actions/dispatch` referencing an altered payload or digest mismatch returns HTTP 409.
- `AC-AR-013-06`: PASS only if POST `/actions/dispatch` referencing an approval belonging to a different tenant returns HTTP 403.
- `AC-AR-013-07`: PASS only if `grep -r "appr_01h8x9m2k4p8" apps/api/routers/approvals.py` returns 0 matches.
- `AC-AR-013-08`: PASS only if `python -m pytest tests/ -q` exits 0 with zero failures.

## Postconditions

- `apps/api/routers/approvals.py` enforces 7-condition verification chain on `grant_approval`.
- `apps/api/routers/approvals.py` enforces 7-condition verification chain on `dispatch_action`.
- `apps/api/routers/approvals.py` contains zero occurrences of `appr_01h8x9m2k4p8`.
- Entire pytest test suite passes without regressions.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Explicit 7-step verification requirements for approve and dispatch plus mock removal |
| Dependency clarity | 2 | Clear single upstream dependency AR-012 |
| File boundary clarity | 2 | Single file WRITE_SET (`apps/api/routers/approvals.py`), zero CREATE |
| Contract clarity | 2 | Detailed 7-condition specification for each endpoint with precise HTTP status codes |
| Failure behavior | 2 | Exact error codes (403, 404, 409, 410) mapped to each failed condition |
| Security/tenancy | 2 | Direct enforcement of INV-ACT-001, INV-ACT-003, INV-TEN-001, and AC-008 |
| Testability | 2 | 8 machine-verifiable acceptance criteria verifiable via automated tests and grep |
| Verification | 2 | Hermetic offline command verifies mock removal and runs full pytest suite |
| Acceptance criteria | 2 | Binary pass/fail conditions with exact HTTP codes and zero-tolerance grep |
| Reasoning independence | 2 | Fully deterministic implementation requirements with zero architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Retain `appr_01h8x9m2k4p8` or create any new hardcoded mock approval IDs.
- Allow agent principals to approve requests or sign approval decisions.
- Allow dispatch of unapproved, expired, tampered, or cross-tenant actions.
- Modify files outside `apps/api/routers/approvals.py`.

## Required executor report

```text
TASK TASK-AR-013 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: NONE
FILES MODIFIED: apps/api/routers/approvals.py
UNEXPECTED FILES: NONE
TESTS: <N> passed, 0 failed
COMMANDS AND EXIT CODES: grep check → 0, pytest → 0
ACCEPTANCE: AC-AR-013-01: PASS|FAIL, AC-AR-013-02: PASS|FAIL, AC-AR-013-03: PASS|FAIL, AC-AR-013-04: PASS|FAIL, AC-AR-013-05: PASS|FAIL, AC-AR-013-06: PASS|FAIL, AC-AR-013-07: PASS|FAIL, AC-AR-013-08: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-014
```
