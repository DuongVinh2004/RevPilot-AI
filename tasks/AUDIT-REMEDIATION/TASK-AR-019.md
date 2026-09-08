# TASK-AR-019 — Causal Study Endpoints — No Hardcoded Estimates, Real Estimator

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 12
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: DOMAIN-EXECUTION
FEATURE: CAUSAL-REAL
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-017, AR-018, AR-020, AR-021, AR-022
DEPENDS_ON: AR-006
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Remove hardcoded values (`0.0660`, `0.00012`, `0.0152`, `0.0362`, `0.0958`) from `apps/api/routers/causal.py`. GET `/causal/studies/{study_id}` with `repo=None` must return HTTP 404 instead of returning a synthetic `COMPLETED` fallback study. In `/claims/verify`, verify cited evidence references against persisted evidence artifacts, returning `UNVERIFIED` if any referenced artifact is non-existent.

BUSINESS RATIONALE: Zero-trust audit finding P1-DOM-001 proved that `apps/api/routers/causal.py` returns hardcoded treatment effect point estimates (`0.0660`) and p-values (`0.00012`) when `causal_repo` is uninitialized, and creates synthetic `COMPLETED` study records on GET requests. Furthermore, `/claims/verify` marked claims as `VERIFIED` solely based on whether the input array length was non-zero (`len(evidence_references) > 0`) without verifying if the evidence IDs exist in `evidence_repo`. This violates INV-AI-001 (epistemic grounding) and AC-014 (anti-fabrication invariant).

ARCHITECTURAL OWNER: Causal Inference Lead, AI Governance Architect

ARCHITECTURAL CONTEXT: INV-AI-001 (causal epistemic grounding), ADR-0003 (hexagonal ports/adapters), AC-014 (anti-fabrication invariant).

## Canonical specification references

- `docs/04-system-architecture/REPOSITORY-TOPOLOGY.md`
- `docs/26-api/API-STANDARDS.md#error-handling`
- `packages/backend/src/revpilot/modules/causal/adapters/postgres_repository.py`
- `packages/backend/src/revpilot/modules/causal/estimators.py`
- `AGENTS.md#anti-fabrication-invariant-ac-014`

If references conflict, return BLOCKED.

## Preconditions

- AR-006 PASS (Readiness probe fail-closed baseline established).
- `apps/api/routers/causal.py` exists with study creation, retrieval, and claim verification routes.

## Change boundary

READ_SET:
- `apps/api/routers/causal.py` (full file, 114 lines)
- `packages/backend/src/revpilot/modules/causal/adapters/postgres_repository.py`
- `packages/backend/src/revpilot/modules/causal/estimators.py`
- `packages/backend/src/revpilot/modules/retrieval/adapters/postgres_evidence_repository.py`
- `tests/integration/test_domain_routes.py`

WRITE_SET:
- `apps/api/routers/causal.py`

CREATE: NONE

MODIFY:
- `apps/api/routers/causal.py` — lines 45-113: Remove hardcoded `0.0660`, `0.00012`, and associated static floats. Return 503 on study creation when `causal_repo` is absent. Return 404 on GET study when `causal_repo` is absent or study not found (eliminate COMPLETED fallback). In `verify_claim`, check evidence references against `evidence_repo` from `request.app.state` and return `UNVERIFIED` if any referenced artifact does not exist.

DO_NOT_MODIFY:
- `packages/backend/src/revpilot/modules/causal/*`
- `apps/api/main.py`
- Any file outside WRITE_SET

EXPECTED CHANGE SET:
- `apps/api/routers/causal.py` updated to remove hardcoded causal values, fail closed (404/503) on missing repository, and ground claim verification in persisted evidence artifacts.

## Symbol-level contract

MUST EXPORT/DEFINE:
- In `apps/api/routers/causal.py`:
  - `create_causal_study(payload, request, tenant, principal)`:
    - Check `repo = getattr(request.app.state, "causal_repo", None)`. If `repo is None`: raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Causal repository unavailable")`.
    - Compute dynamic estimation or initialize study state via causal estimator service.
    - MUST NOT return hardcoded `0.0660` or `0.00012`.
  - `get_causal_study(study_id, request, tenant)`:
    - Check `repo = getattr(request.app.state, "causal_repo", None)`.
    - If `repo is None`: raise `NotFoundError(f"Causal study '{study_id}' not found.")` (yielding HTTP 404).
    - If repo is present, retrieve study; if None, raise `NotFoundError`.
    - MUST NOT return synthetic dictionary with `point_estimate: 0.0660` and `status: COMPLETED` when repo is None.
  - `verify_claim(payload, request, tenant)`:
    - Check `evidence_repo = getattr(request.app.state, "evidence_repo", None)`.
    - If `evidence_repo is None` or if any referenced ID in `payload.evidence_references` does not exist in `evidence_repo`: return `verifier_status: "UNVERIFIED"`.
    - Only return `verifier_status: "VERIFIED"` if all referenced evidence items exist and are validated.

MUST NOT:
- Return `point_estimate: 0.0660` or `p_value: 0.00012` as static hardcoded literals in active code.
- Return HTTP 200 with fake study when `causal_repo` is absent.
- Return `VERIFIED` for claims with non-existent or fabricated evidence references.
- Bypass tenant scoping in `causal_repo` or `evidence_repo` lookups.

## Input/output and validation

INPUT: `CausalStudyRequest`, `study_id` path parameter, `ClaimVerificationRequest`.
OUTPUT: Causal study report or verified claim verdict.
INVALID INPUT: Empty claim statement or non-existent variables → HTTP 422 Unprocessable Entity.
VALIDATION RULES: Treatment and outcome variables must differ. p-values bounded in [0.0, 1.0]. Evidence references must resolve to persisted records.
STATE TRANSITIONS: Study states: `REQUESTED` → `ESTIMATING` → `COMPLETED` / `FAILED`.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `CAUSAL_NOT_FOUND` | Study ID not found or `causal_repo` is None on GET | 404 | no | "Causal study '{study_id}' not found." | yes | `causal_study_not_found_total` |
| `CAUSAL_SERVICE_UNAVAILABLE` | `causal_repo` is None on POST create | 503 | yes | "Causal repository unavailable" | yes | `causal_dependency_unavailable_total` |
| `CLAIM_UNVERIFIED` | Referenced evidence ID does not exist | 200 (payload verdict) | no | `{"verifier_status": "UNVERIFIED"}` | yes | `causal_claim_unverified_total` |
| `TENANCY_VIOLATION` | Cross-tenant study access attempted | 403 | no | Tenancy violation | yes | `security_tenancy_violations_total` |

## Security contract

AUTHENTICATION: Bearer token validated via `get_current_tenant` and `require_roles`.
AUTHORIZATION: Role enforcement (`require_roles("ANALYST", "OPERATOR", "SYSTEM_ADMIN")` for study creation).
TENANT: TenantContext isolation enforced on study creation, study retrieval, and evidence lookup (INV-TEN-001).
PII: PROHIBITED — No raw customer PII in causal study estimands or claims.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: Table schema `revpilot.causal_studies` per `packages/backend/src/revpilot/modules/causal/adapters/postgres_repository.py`.
API CONTRACT: RESTful JSON conforming to `docs/26-api/API-STANDARDS.md`.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: AIPW/Doubly Robust causal estimators, E-value sensitivity analysis.
RAG CONTRACT: Claim verification grounds statements in retrieved evidence items from `evidence_repo`.

## Operational behavior

RETRY: 503 retryable with exponential backoff.
TIMEOUT: Causal study computation < 10.0 seconds. Claim verification < 500ms.
IDEMPOTENCY: Deterministic estimation using reproducibility seed.
LOGGING: Log claim verification failures and unverified citations.
METRICS: `causal_study_not_found_total` and `causal_claim_unverified_total`.
FAILURE BEHAVIOR: Missing study or missing repo on GET → 404. Missing repo on POST → 503. Non-existent evidence → UNVERIFIED.
ROLLBACK/COMPENSATION: Git revert of `apps/api/routers/causal.py`.

## Implementation requirements

1. In `apps/api/routers/causal.py`:
   - In `create_causal_study`: check `repo = getattr(request.app.state, "causal_repo", None)`. If None, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Causal repository unavailable")`. Remove literals `0.0660` and `0.00012`.
   - In `get_causal_study`: check `repo = getattr(request.app.state, "causal_repo", None)`. If None, raise `NotFoundError(f"Causal study '{study_id}' not found.")`. If repo is present, retrieve study and raise `NotFoundError` if not found. Remove the hardcoded fallback returning `status: "COMPLETED"` and `point_estimate: 0.0660`.
   - In `verify_claim`: check `evidence_repo = getattr(request.app.state, "evidence_repo", None)`. If `evidence_repo is None` or any referenced evidence ID is missing in `evidence_repo`, set `verifier_status = "UNVERIFIED"`.
2. Ensure no un-commented occurrences of `0.0660` or `0.00012` remain in `apps/api/routers/causal.py`.

## Tests and evaluations

TESTS REQUIRED:
- Integration/unit tests asserting:
  - `POST /api/v1/causal/studies` with `causal_repo=None` returns 503.
  - `GET /api/v1/causal/studies/{study_id}` with `causal_repo=None` returns 404.
  - `POST /api/v1/claims/verify` with non-existent evidence artifact reference returns `UNVERIFIED`.
- Grep test verifying absence of forbidden strings outside comments and docstrings.

AI EVALS REQUIRED: NOT APPLICABLE — no model parameter retraining.
PERFORMANCE REQUIREMENTS: Claim verification < 50ms.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "
import pathlib, re, sys
path = pathlib.Path('apps/api/routers/causal.py')
content = path.read_text(encoding='utf-8')
forbidden = ['0.0660', '0.00012']
errors = []
for idx, line in enumerate(content.splitlines(), 1):
    stripped = line.strip()
    if stripped.startswith('#'):
        continue
    for target in forbidden:
        if target in stripped:
            errors.append(f'Line {idx}: forbidden target {target} found in active code: {stripped}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('PASS: No hardcoded causal values in active code')
"
```

EXPECTED: exit code 0 and output `PASS: No hardcoded causal values in active code`.

## Binary acceptance criteria

- `AC-AR-019-01`: PASS only if grep for `0.0660` and `0.00012` in `apps/api/routers/causal.py` returns matches only within comment blocks or docstrings.
- `AC-AR-019-02`: PASS only if GET `/api/v1/causal/studies/{study_id}` returns HTTP 404 when `request.app.state.causal_repo` is None.
- `AC-AR-019-03`: PASS only if POST `/api/v1/claims/verify` with non-existent evidence artifact references returns `verifier_status` equal to `UNVERIFIED`.

## Postconditions

- `apps/api/routers/causal.py` has all hardcoded point estimates and p-values removed.
- GET study on missing repository returns 404 instead of fabricated COMPLETED study.
- Claims referencing non-existent evidence artifacts return UNVERIFIED.
- Verification script exits 0.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Remove hardcoded estimates, 404 on missing repo, UNVERIFIED on missing evidence |
| Dependency clarity | 2 | Upstream dependency on AR-006 readiness baseline |
| File boundary clarity | 2 | Single file in WRITE_SET: `apps/api/routers/causal.py` |
| Contract clarity | 2 | Clear endpoints, failure codes, and claim verifier behavior |
| Failure behavior | 2 | Missing repo yields 503 on write, 404 on read; missing evidence yields UNVERIFIED |
| Security/tenancy | 2 | Preserves role checks and tenant isolation |
| Testability | 2 | 3 machine-verifiable criteria, integration testable |
| Verification | 2 | Automated python regex script, exit 0 |
| Acceptance criteria | 2 | Binary PASS/FAIL conditions on status codes, verdicts, and literals |
| Reasoning independence | 2 | Standard fail-closed pattern without architectural choices |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Return fabricated completed causal studies on missing repository.
- Verify claims without checking evidence artifact persistence.
- Modify files outside `apps/api/routers/causal.py`.

## Required executor report

```text
TASK TASK-AR-019 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: NONE
FILES MODIFIED: apps/api/routers/causal.py
UNEXPECTED FILES: NONE
TESTS: <verification output and test suite results>
COMMANDS AND EXIT CODES: python verification -> 0, pytest -> 0
ACCEPTANCE: AC-AR-019-01: PASS|FAIL, AC-AR-019-02: PASS|FAIL, AC-AR-019-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-017, AR-018, AR-020, AR-021, or AR-022
```
