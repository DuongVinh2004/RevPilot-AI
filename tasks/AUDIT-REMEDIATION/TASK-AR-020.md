# TASK-AR-020 — Claim Verification — Real Artifact Dereference and ACL Validation

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 11
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: DOMAIN-EXECUTION
FEATURE: CLAIM-VERIFY-REAL
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-017..019,021,022
DEPENDS_ON: AR-006
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Claim verification at `causal.py` lines 97-113 must dereference evidence artifacts, validate existence/tenant/span. Return VERIFIED only when ALL references are valid; return UNVERIFIED when any reference is missing or belongs to another tenant.

BUSINESS RATIONALE: Zero-trust audit finding P1-DOM-001 showed that `/claims/verify` evaluated validity solely using `len(payload.evidence_references) > 0` without dereferencing referenced artifacts, without checking tenant ACL boundaries, and without validating citation spans. This enables hallucinated or cross-tenant artifacts to be marked VERIFIED, directly violating INV-AI-001 (ungrounded claim rejection) and INV-TEN-001 (strict tenant isolation).

ARCHITECTURAL OWNER: Causal AI Lead, Security Architect

ARCHITECTURAL CONTEXT: INV-AI-001 (Ungrounded claim rejection), INV-TEN-001 (Tenant isolation), docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md, docs/26-api/API-STANDARDS.md §7.3.

## Canonical specification references

- `docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md#gate-unsupported-claims`
- `docs/26-api/API-STANDARDS.md#73-deterministic-claim-verification-api`
- `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md`
- `execution/DEFINITION-OF-DONE.md`

If references conflict, return BLOCKED.

## Preconditions

- AR-006 PASS (Readiness probe dependency-aware).
- `apps/api/routers/causal.py` exists with `verify_claim` endpoint.
- `apps/api/middleware/authentication.py` provides `get_current_tenant` dependency.

## Change boundary

READ_SET:
- `apps/api/routers/causal.py`
- `packages/backend/src/revpilot/modules/retrieval/adapters/postgres_evidence_repository.py`
- `tests/integration/test_domain_routes.py`
- `tests/ai-evals/test_unsupported_claim_rejection.py`

WRITE_SET:
- `apps/api/routers/causal.py`
- `tests/integration/test_claim_verification.py`

CREATE:
- `tests/integration/test_claim_verification.py`

MODIFY:
- `apps/api/routers/causal.py` — Lines 97-113: Update `verify_claim` to accept `request: Request`. For each evidence reference in `payload.evidence_references`, dereference from evidence repository / artifact storage. Verify artifact exists, matches `str(tenant.tenant_id)`, and contains a non-empty `citation_span`. Set `verifier_status = "VERIFIED"` only when all references satisfy validation rules; return `UNVERIFIED` with reason when any reference is missing or from another tenant; return `NEED_MORE_EVIDENCE` when no references provided.

DO_NOT_MODIFY:
- `apps/api/routers/investigations.py`
- `apps/api/routers/admin.py`
- `apps/api/middleware/*`
- `packages/backend/src/revpilot/modules/retrieval/*`
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 1 router endpoint updated (`apps/api/routers/causal.py`), 1 new integration test suite (`tests/integration/test_claim_verification.py`).

## Symbol-level contract

MUST EXPORT/DEFINE:

Modified endpoint in `apps/api/routers/causal.py`:
```python
@router.post("/claims/verify")
async def verify_claim(
    payload: ClaimVerificationRequest,
    request: Request,
    tenant: TenantContext = Depends(get_current_tenant),
) -> dict[str, Any]:
    ...
```

Response payload fields:
- `statement: str`
- `epistemic_category: str`
- `verifier_status: str` — Value in `{"VERIFIED", "UNVERIFIED", "NEED_MORE_EVIDENCE"}`
- `evidence_cited_count: int`
- `citation_spans_valid: bool`
- `temporal_leakage_detected: bool`
- `rejection_reason: str | None`

MUST NOT:
- Mark claims `VERIFIED` when referenced evidence artifact does not exist.
- Mark claims `VERIFIED` when referenced evidence belongs to a different tenant.
- Mark claims `VERIFIED` when evidence lacks valid citation spans.
- Throw 500 on missing or invalid evidence references (must return 200 with `UNVERIFIED` verdict).

## Input/output and validation

INPUT: HTTP POST `/api/v1/claims/verify` with JSON body:
```json
{
  "statement": "Carrier SLA penalty increased churn by 14%",
  "epistemic_category": "CAUSAL_ESTIMATE",
  "evidence_references": ["evd_001", "evd_002"]
}
```

OUTPUT: HTTP 200 with JSON payload:
```json
{
  "statement": "Carrier SLA penalty increased churn by 14%",
  "epistemic_category": "CAUSAL_ESTIMATE",
  "verifier_status": "VERIFIED",
  "evidence_cited_count": 2,
  "citation_spans_valid": true,
  "temporal_leakage_detected": false,
  "rejection_reason": null
}
```

INVALID INPUT:
- Empty `evidence_references` → `verifier_status: "NEED_MORE_EVIDENCE"`, `citation_spans_valid: false`.
- Unknown artifact reference → `verifier_status: "UNVERIFIED"`, `rejection_reason: "Evidence artifact '...' not found"`.
- Cross-tenant artifact reference → `verifier_status: "UNVERIFIED"`, `rejection_reason: "Access denied to evidence artifact '...' for tenant"`.
- Missing or malformed citation span → `verifier_status: "UNVERIFIED"`, `rejection_reason: "Invalid citation span in evidence '...'"`.

STATE TRANSITIONS: None (pure deterministic verification query).

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `VALIDATION_ERROR` | Malformed JSON or missing required fields | 400 | no | Invalid request payload schema | yes | validation_failed_total |
| `UNAUTHORIZED` | Missing or invalid Bearer token | 401 | no | Invalid or expired token | yes | auth_failed_total |
| `FORBIDDEN` | Missing required tenant context | 403 | no | Tenant context required | yes | auth_denied_total |

## Security contract

AUTHENTICATION: Required (Bearer token via `get_current_tenant`).
AUTHORIZATION: Any authenticated tenant user with `investigation:read` or domain role.
TENANT: Strictly isolated. Every referenced artifact must match `tenant.tenant_id`. Cross-tenant artifact references must fail verification with `UNVERIFIED`.
PII: Evidence content and statement logged per audit rules with token masking.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED (read-only artifact evaluation).
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE — no table migrations.
API CONTRACT: `POST /api/v1/claims/verify` conforming to docs/26-api/API-STANDARDS.md §7.3.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: Enforces INV-AI-001 by guaranteeing 0 ungrounded claims verified.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: Evidence references validated against evidence repository records.

## Operational behavior

RETRY: Client may retry immediately with updated evidence references.
TIMEOUT: Verification evaluation timeout < 1 second.
IDEMPOTENCY: Query endpoint is read-only and idempotent.
LOGGING: Log claim verification requests and rejection reasons at INFO level.
METRICS: Record verification verdict (`claim_verification_verdicts_total{status="..."}`).
FAILURE BEHAVIOR: Repository unavailable or reference missing evaluates fail-closed to `UNVERIFIED`.
ROLLBACK/COMPENSATION: Git revert to previous commit.

## Implementation requirements

1. In `apps/api/routers/causal.py`:
   - Inject `request: Request` into `verify_claim`.
   - Inspect `evidence_repo = getattr(request.app.state, "evidence_repo", None)`.
   - Support fallback artifact lookup in `request.app.state.evidence_store` or seeded test dictionary to maintain hermetic test isolation and avoid breaking `tests/integration/test_domain_routes.py`.
   - If `len(payload.evidence_references) == 0`:
     Return `verifier_status="NEED_MORE_EVIDENCE"`, `citation_spans_valid=False`, `rejection_reason=None`.
   - For each ref in `payload.evidence_references`:
     - Retrieve record from repository or test artifact store.
     - If record is None: return `verifier_status="UNVERIFIED"`, `citation_spans_valid=False`, `rejection_reason=f"Evidence artifact '{ref}' not found"`.
     - If record tenant does not match caller tenant: return `verifier_status="UNVERIFIED"`, `citation_spans_valid=False`, `rejection_reason=f"Evidence artifact '{ref}' does not belong to tenant"`.
     - If citation span is absent or empty: return `verifier_status="UNVERIFIED"`, `citation_spans_valid=False`, `rejection_reason=f"Evidence artifact '{ref}' has invalid citation span"`.
   - If all references pass: return `verifier_status="VERIFIED"`, `citation_spans_valid=True`, `rejection_reason=None`.
2. Seed default valid references (`evd_001`, `evd_002` with valid spans for `tnt_dev_001`) in `apps/api/main.py` test setup or local router store so existing integration tests in `test_domain_routes.py` pass without breakage.
3. Create `tests/integration/test_claim_verification.py` with 5 tests:
   - `test_claim_verify_all_valid`: All references exist, correct tenant, valid span → `VERIFIED`.
   - `test_claim_verify_nonexistent_artifact`: Reference to non-existent ID → `UNVERIFIED`.
   - `test_claim_verify_cross_tenant_artifact`: Reference belonging to other tenant → `UNVERIFIED`.
   - `test_claim_verify_empty_references`: Empty reference list → `NEED_MORE_EVIDENCE`.
   - `test_claim_verify_invalid_citation_span`: Reference with empty span → `UNVERIFIED`.

## Tests and evaluations

TESTS REQUIRED:
- `tests/integration/test_claim_verification.py` (5 tests).
- `tests/integration/test_domain_routes.py` (existing regression).

AI EVALS REQUIRED:
- `tests/ai-evals/test_unsupported_claim_rejection.py` must continue passing.

PERFORMANCE REQUIREMENTS: Single verification request completes in < 50ms.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/integration/test_claim_verification.py tests/integration/test_domain_routes.py -v
```

EXPECTED: exit code 0, all claim verification tests pass, full suite green.

## Binary acceptance criteria

- `AC-AR-020-01`: PASS only if claim verification with non-existent artifact reference returns HTTP 200 with `verifier_status == "UNVERIFIED"`.
- `AC-AR-020-02`: PASS only if claim verification with artifact reference belonging to another tenant returns HTTP 200 with `verifier_status == "UNVERIFIED"`.
- `AC-AR-020-03`: PASS only if claim verification with all valid references belonging to caller tenant returns HTTP 200 with `verifier_status == "VERIFIED"`.
- `AC-AR-020-04`: PASS only if claim verification with empty evidence references returns HTTP 200 with `verifier_status == "NEED_MORE_EVIDENCE"`.
- `AC-AR-020-05`: PASS only if `python -m pytest tests/integration/test_claim_verification.py -v` exits 0 with 5/5 pass.

## Postconditions

- Claim verification endpoint validates artifact existence, tenant ownership, and citation spans.
- 0 ungrounded claims can be verified without valid dereferenced artifacts.
- No regression in existing domain routes.
- Verification command exits 0.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Real artifact dereference and ACL validation specified unambiguously |
| Dependency clarity | 2 | Depends on AR-006; unblocks domain execution |
| File boundary clarity | 2 | 1 MODIFY (`causal.py`), 1 CREATE (`test_claim_verification.py`) |
| Contract clarity | 2 | Complete schema, verdict values, and rejection reasons specified |
| Failure behavior | 2 | Fail-closed to UNVERIFIED for any invalid/missing reference |
| Security/tenancy | 2 | Tenant boundary isolation explicitly enforced |
| Testability | 2 | 5 concrete integration test scenarios |
| Verification | 2 | Single offline hermetic pytest command |
| Acceptance criteria | 2 | 5 binary machine-verifiable criteria |
| Reasoning independence | 2 | Exact algorithmic rules provided; zero architectural leeway |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Return `VERIFIED` when any referenced artifact is missing or unverified.
- Allow cross-tenant evidence references to be evaluated without isolation check.
- Return HTTP 500 when artifact is not found (must return structured 200 verdict).

## Required executor report

```text
TASK TASK-AR-020 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_claim_verification.py
FILES MODIFIED: apps/api/routers/causal.py
UNEXPECTED FILES: NONE
TESTS: 5 claim verification tests PASS, domain routes PASS
COMMANDS AND EXIT CODES: pytest claim verification → 0
ACCEPTANCE: AC-AR-020-01: PASS|FAIL, AC-AR-020-02: PASS|FAIL, AC-AR-020-03: PASS|FAIL, AC-AR-020-04: PASS|FAIL, AC-AR-020-05: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-021 or AR-022
```
