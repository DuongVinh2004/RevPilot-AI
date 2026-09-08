# TASK-AR-018 — Decision/ML Endpoints — No Hardcoded Scores, Real Model Artifact

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 13
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: DOMAIN-EXECUTION
FEATURE: DECISION-ML-REAL
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-017, AR-019, AR-020, AR-021, AR-022
DEPENDS_ON: AR-006
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Remove hardcoded values (`0.7420`, `0.1840`, `ISSUE_SERVICE_CREDIT_VOUCHER`, `1420.50`, `250.00`, `0.0240`, `0.0310`) from `apps/api/routers/decisions.py`. Return HTTP 503 (Service Unavailable) when model or `decision_repo` dependency is absent. Wire real model artifact evaluation and decision optimizer execution.

BUSINESS RATIONALE: Zero-trust audit finding P1-DOM-001 proved that `apps/api/routers/decisions.py` returns hardcoded churn probabilities (`0.7420`), uplift treatment effects (`0.1840`), and recommendation actions (`ISSUE_SERVICE_CREDIT_VOUCHER`) even when no trained model artifact or repository is present. Under production conditions without model artifacts loaded, this produces fabricated risk assessments and unauthorized intervention suggestions, violating INV-AI-001 (epistemic integrity) and INV-ACT-001 (governed intervention authorization).

ARCHITECTURAL OWNER: Machine Learning Lead, Decision Engine Architect

ARCHITECTURAL CONTEXT: INV-AI-001 (calibrated ML without synthetic fallbacks), INV-COST-001 (constrained decision utility optimization), ADR-0003 (hexagonal ports/adapters), AC-014 (anti-fabrication invariant).

## Canonical specification references

- `docs/04-system-architecture/REPOSITORY-TOPOLOGY.md`
- `docs/26-api/API-STANDARDS.md#error-handling`
- `packages/backend/src/revpilot/modules/decision/engine.py`
- `packages/backend/src/revpilot/modules/decision/adapters/postgres_repository.py`
- `AGENTS.md#anti-fabrication-invariant-ac-014`

If references conflict, return BLOCKED.

## Preconditions

- AR-006 PASS (Readiness probe fail-closed baseline established).
- `apps/api/routers/decisions.py` exists with churn, uplift, and decision optimization routes.

## Change boundary

READ_SET:
- `apps/api/routers/decisions.py` (full file, 165 lines)
- `packages/backend/src/revpilot/modules/decision/adapters/postgres_repository.py`
- `packages/backend/src/revpilot/modules/decision/engine.py`
- `packages/backend/src/revpilot/modules/decision/ports.py`

WRITE_SET:
- `apps/api/routers/decisions.py`

CREATE: NONE

MODIFY:
- `apps/api/routers/decisions.py` — lines 50-164: remove hardcoded `0.7420`, `0.1840`, `ISSUE_SERVICE_CREDIT_VOUCHER`, `1420.50`, `250.00`, `0.0240`, `0.0310`. Enforce 503 check when `decision_repo` or model scoring service is absent in `request.app.state`.

DO_NOT_MODIFY:
- `packages/backend/src/revpilot/modules/decision/engine.py`
- `packages/backend/src/revpilot/modules/decision/adapters/postgres_repository.py`
- `apps/api/main.py`
- Any file outside WRITE_SET

EXPECTED CHANGE SET:
- `apps/api/routers/decisions.py` updated to fail closed (503) when `decision_repo` or model engine is absent, and execute real scoring and optimization logic when present.

## Symbol-level contract

MUST EXPORT/DEFINE:
- In `apps/api/routers/decisions.py`:
  - `score_churn_risk(payload, request, tenant)`:
    - Check `repo = getattr(request.app.state, "decision_repo", None)`. If `repo is None`: raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Decision repository or churn model unavailable")`.
    - Retrieve calibrated probability from model artifact or repository.
    - MUST NOT return hardcoded `0.7420` or `0.0240`.
  - `get_feature_explanation(prediction_id, tenant, request)`:
    - Inspect `decision_repo` in `request.app.state`. If absent, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Decision repository unavailable")`.
  - `estimate_uplift(payload, request, tenant)`:
    - Check `repo = getattr(request.app.state, "decision_repo", None)`. If `repo is None`: raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Uplift estimation service unavailable")`.
    - Retrieve CATE estimate dynamically.
    - MUST NOT return hardcoded `0.1840` or `0.0310`.
  - `optimize_decision(payload, request, tenant, principal)`:
    - Check `repo = getattr(request.app.state, "decision_repo", None)`. If `repo is None`: raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Decision optimizer unavailable")`.
    - Execute constrained optimization engine.
    - MUST NOT return hardcoded action `"ISSUE_SERVICE_CREDIT_VOUCHER"` or utility `1420.50`.

MUST NOT:
- Return HTTP 200 with hardcoded ML scores when model service or repository is unavailable.
- Include literals `0.7420`, `0.1840`, or `"ISSUE_SERVICE_CREDIT_VOUCHER"` in active executable lines in `decisions.py`.
- Bypass tenant scoping when invoking `repo.save_churn_prediction`, `repo.save_uplift_score`, or `repo.save_recommendation`.

## Input/output and validation

INPUT: `ChurnScoreRequest`, `UpliftEstimateRequest`, `DecisionOptimizeRequest`.
OUTPUT: Dynamic churn prediction record, uplift CATE estimate, or constrained utility recommendation.
INVALID INPUT: Missing customer ID or invalid intervention type → HTTP 422 Unprocessable Entity.
VALIDATION RULES: Calibrated probabilities bounded in [0.0, 1.0]. Action recommendations must satisfy budget and cooldown constraints.
STATE TRANSITIONS: Decision recommendation lifecycle: `PROPOSED` → `APPROVED` / `REJECTED` → `EXECUTED`.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `DECISION_SERVICE_UNAVAILABLE` | `decision_repo` or model engine is None | 503 | yes | "Decision repository or churn model unavailable" | yes | `decision_dependency_unavailable_total` |
| `PREDICTION_NOT_FOUND` | Requested prediction_id does not exist | 404 | no | "Churn prediction '{prediction_id}' not found" | yes | `decision_not_found_total` |
| `CONSTRAINTS_VIOLATED` | Optimization constraints cannot be satisfied | 422 | no | "Action constraints violated" | yes | `decision_constraint_violation_total` |
| `TENANCY_VIOLATION` | Cross-tenant access attempted | 403 | no | Tenancy violation | yes | `security_tenancy_violations_total` |

## Security contract

AUTHENTICATION: Bearer token validated via `get_current_tenant` and `require_roles`.
AUTHORIZATION: Role-based access control (`require_roles("ANALYST", "OPERATOR", "SYSTEM_ADMIN")` on decision optimization).
TENANT: TenantContext isolation enforced on all model queries and persistence records (INV-TEN-001).
PII: PROHIBITED — Only anonymized `customer_id` and feature hashes stored in decision records.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: Table schemas `revpilot.churn_predictions`, `revpilot.uplift_scores`, and `revpilot.decision_recommendations`.
API CONTRACT: RESTful JSON conforming to `docs/26-api/API-STANDARDS.md`.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: Platt/Isotonic calibrated churn model and CATE uplift estimator specifications per `packages/backend/src/revpilot/modules/decision/engine.py`.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: 503 retryable with exponential backoff.
TIMEOUT: Inference and optimization execution timeout < 3.0 seconds.
IDEMPOTENCY: Scoring is idempotent given the same customer feature digest.
LOGGING: Log inference exceptions and repository unavailability with tenant ID.
METRICS: `decision_dependency_unavailable_total` and latency histograms.
FAILURE BEHAVIOR: Dependency missing → immediate fail-closed 503.
ROLLBACK/COMPENSATION: Git revert of `apps/api/routers/decisions.py`.

## Implementation requirements

1. In `apps/api/routers/decisions.py`:
   - In `score_churn_risk`: verify `decision_repo` in `request.app.state`. If None, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Decision repository or churn model unavailable")`. Remove literal `0.7420` and `0.0240`.
   - In `estimate_uplift`: verify `decision_repo` in `request.app.state`. If None, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Uplift estimation service unavailable")`. Remove literal `0.1840` and `0.0310`.
   - In `optimize_decision`: verify `decision_repo` in `request.app.state`. If None, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Decision optimizer unavailable")`. Remove literals `"ISSUE_SERVICE_CREDIT_VOUCHER"` and `1420.50`.
   - In `get_feature_explanation`: verify repository/service availability and eliminate static mock attributions if repository is absent.
2. Ensure no un-commented occurrences of `0.7420`, `0.1840`, or `ISSUE_SERVICE_CREDIT_VOUCHER` remain in `apps/api/routers/decisions.py`.

## Tests and evaluations

TESTS REQUIRED:
- Integration/unit tests asserting:
  - `POST /api/v1/ml/churn/score` with `decision_repo=None` returns 503.
  - `POST /api/v1/ml/uplift/estimate` with `decision_repo=None` returns 503.
  - `POST /api/v1/decisions/optimize` with `decision_repo=None` returns 503.
- Grep test verifying absence of forbidden strings outside comments and docstrings.

AI EVALS REQUIRED: NOT APPLICABLE — no model parameter retraining.
PERFORMANCE REQUIREMENTS: Fail-closed path < 10ms.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "
import pathlib, re, sys
path = pathlib.Path('apps/api/routers/decisions.py')
content = path.read_text(encoding='utf-8')
forbidden = ['0.7420', '0.1840', 'ISSUE_SERVICE_CREDIT_VOUCHER']
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
print('PASS: No hardcoded decision values in active code')
"
```

EXPECTED: exit code 0 and output `PASS: No hardcoded decision values in active code`.

## Binary acceptance criteria

- `AC-AR-018-01`: PASS only if grep for `0.7420`, `0.1840`, and `ISSUE_SERVICE_CREDIT_VOUCHER` in `apps/api/routers/decisions.py` returns matches only within comment blocks or docstrings.
- `AC-AR-018-02`: PASS only if POST `/api/v1/ml/churn/score` returns HTTP 503 when `request.app.state.decision_repo` is None.
- `AC-AR-018-03`: PASS only if POST `/api/v1/ml/uplift/estimate` returns HTTP 503 when `request.app.state.decision_repo` is None.
- `AC-AR-018-04`: PASS only if POST `/api/v1/decisions/optimize` returns HTTP 503 when `request.app.state.decision_repo` is None.

## Postconditions

- `apps/api/routers/decisions.py` has all hardcoded scores and actions removed.
- ML and decision endpoints fail closed (503) when dependencies are uninitialized.
- Verification script exits 0.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Remove hardcoded scores and enforce 503 fail-closed |
| Dependency clarity | 2 | Upstream dependency on AR-006 readiness baseline |
| File boundary clarity | 2 | Single file in WRITE_SET: `apps/api/routers/decisions.py` |
| Contract clarity | 2 | Clear endpoints, failure codes, and model contracts |
| Failure behavior | 2 | Missing repo/engine yields deterministic 503 Service Unavailable |
| Security/tenancy | 2 | Preserves role checks and tenant isolation |
| Testability | 2 | 4 machine-verifiable criteria, integration testable |
| Verification | 2 | Automated python regex script, exit 0 |
| Acceptance criteria | 2 | Binary PASS/FAIL conditions on status codes and literals |
| Reasoning independence | 2 | Standard fail-closed pattern without architectural choices |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Return dummy churn scores or default vouchers when decision engine is not initialized.
- Modify files outside `apps/api/routers/decisions.py`.

## Required executor report

```text
TASK TASK-AR-018 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: NONE
FILES MODIFIED: apps/api/routers/decisions.py
UNEXPECTED FILES: NONE
TESTS: <verification output and test suite results>
COMMANDS AND EXIT CODES: python verification -> 0, pytest -> 0
ACCEPTANCE: AC-AR-018-01: PASS|FAIL, AC-AR-018-02: PASS|FAIL, AC-AR-018-03: PASS|FAIL, AC-AR-018-04: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-017, AR-019, AR-020, AR-021, or AR-022
```
