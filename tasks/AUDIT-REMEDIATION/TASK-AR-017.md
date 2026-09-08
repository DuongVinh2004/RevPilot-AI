# TASK-AR-017 — Analytics Endpoints — 503 When Dependency Missing, Real Query Path

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 10
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: DOMAIN-EXECUTION
FEATURE: ANALYTICS-REAL
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-018, AR-019, AR-020, AR-021, AR-022
DEPENDS_ON: AR-006
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Remove hardcoded values (100.0, 75.4, -24.6, 5.2, 0.7820, 0.782) from `apps/api/routers/analytics.py`. When repository (`anomaly_repo`) or query engine dependency is absent (`None`), fail-closed by returning HTTP 503 (Service Unavailable) instead of returning synthetic/mocked responses. Wire real repository execution path for anomaly detection and anomaly retrieval.

BUSINESS RATIONALE: Zero-trust audit finding P1-DOM-001 proved that `apps/api/routers/analytics.py` returns hardcoded metric series (`100.0`, `75.4`), synthetic anomaly actual/expected values (`-24.6`, `5.2`), and hardcoded anomaly scores (`0.7820`) when underlying query engine or database repositories are uninitialized. This violates INV-REL-001 (fail-closed dependency health) and AC-014 (anti-fabrication invariant) by presenting fabricated analytics data as valid production responses.

ARCHITECTURAL OWNER: Analytics Domain Lead, Backend API Architect

ARCHITECTURAL CONTEXT: INV-REL-001 (dependency fail-closed), INV-TEN-001 (tenant-isolated data operations), ADR-0003 (hexagonal architecture), AC-014 (anti-fabrication invariant).

## Canonical specification references

- `docs/04-system-architecture/REPOSITORY-TOPOLOGY.md`
- `docs/26-api/API-STANDARDS.md#error-handling`
- `execution/DEFINITION-OF-DONE.md#stage-c-code-complete`
- `AGENTS.md#anti-fabrication-invariant-ac-014`

If references conflict, return BLOCKED.

## Preconditions

- AR-006 PASS (Readiness probe and dependency health baseline established).
- `apps/api/routers/analytics.py` exists and contains `query_metric`, `detect_anomalies`, `list_anomalies`, `get_anomaly_detail`, and `transition_anomaly`.

## Change boundary

READ_SET:
- `apps/api/routers/analytics.py` (full file, 187 lines)
- `packages/backend/src/revpilot/modules/analytics/adapters/postgres_repository.py`
- `packages/backend/src/revpilot/modules/analytics/detectors/stl.py`
- `tests/integration/test_domain_routes.py`

WRITE_SET:
- `apps/api/routers/analytics.py`

CREATE: NONE

MODIFY:
- `apps/api/routers/analytics.py` — lines 44-100 (and fallback paths lines 117-131, 149-166, 178-186) to remove hardcoded values (100.0, 75.4, -24.6, 5.2, 0.7820), enforce 503 checks when dependencies are missing, and operate strictly via repository/query engine.

DO_NOT_MODIFY:
- `apps/api/main.py`
- `apps/api/middleware/*`
- `packages/backend/src/revpilot/modules/analytics/adapters/postgres_repository.py`
- Any file outside WRITE_SET

EXPECTED CHANGE SET:
- Modified router endpoints in `apps/api/routers/analytics.py` raising HTTPException 503 when `anomaly_repo` / query engine is None, and removing hardcoded series/values.

## Symbol-level contract

MUST EXPORT/DEFINE:
- In `apps/api/routers/analytics.py`:
  - `query_metric(payload, tenant, request)`:
    - Inspect query engine or repository dependency from `request.app.state` (e.g. `metric_service` or `anomaly_repo`). If absent (`None`), raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Analytics query engine unavailable")`.
    - MUST NOT return hardcoded values `100.0` or `75.4`.
  - `detect_anomalies(payload, request, tenant, principal)`:
    - Get `repo = getattr(request.app.state, "anomaly_repo", None)`. If `repo is None`: raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Anomaly detection repository unavailable")`.
    - When `repo` is present: execute real anomaly detection and persistence, saving and returning dynamic detector results from the repository or detector rather than hardcoded `-24.6`, `5.2`, or `0.7820`.
  - `list_anomalies(request, status_filter, severity_filter, limit, offset, tenant)`:
    - If `repo is None`: raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Anomaly repository unavailable")`. Remove hardcoded fallback item with `-24.6`, `5.2`, `0.782`.
  - `get_anomaly_detail(anomaly_id, request, tenant)`:
    - If `repo is None`: raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Anomaly repository unavailable")`. Remove hardcoded fallback with `-24.6`, `5.2`, `0.782`.
  - `transition_anomaly(anomaly_id, payload, request, tenant, principal)`:
    - If `repo is None`: raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Anomaly repository unavailable")`.

MUST NOT:
- Return HTTP 200 or 201 with mock data when database/repository dependency is absent.
- Contain floating point literals `100.0`, `75.4`, `-24.6`, `5.2`, or `0.782` in active Python code.
- Bypass tenant scoping when invoking `repo.save_anomaly` or `repo.list_anomalies`.

## Input/output and validation

INPUT: `MetricQueryRequest`, `AnomalyDetectRequest`, `AnomalyTransitionRequest`, and query parameters for list/detail.
OUTPUT: Dynamic JSON metric time series or anomaly detection/lifecycle result.
INVALID INPUT: Missing required request fields → HTTP 422 Unprocessable Entity.
VALIDATION RULES: Observation window start must be before observation window end. Repository must be verified before executing query.
STATE TRANSITIONS: Anomaly states: `DETECTED` → `INVESTIGATING` → `MITIGATED` / `RESOLVED` / `FALSE_POSITIVE`.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `DEPENDENCY_UNAVAILABLE` | `anomaly_repo` or query service is None | 503 | yes | "Anomaly detection repository unavailable" | yes | `analytics_dependency_unavailable_total` |
| `ANOMALY_NOT_FOUND` | Requested anomaly_id does not exist in tenant boundary | 404 | no | "Anomaly '{anomaly_id}' not found in tenant boundary." | yes | `analytics_not_found_total` |
| `INVALID_WINDOW` | observation_window_start >= observation_window_end | 422 | no | Invalid observation window | no | N/A |
| `TENANCY_VIOLATION` | Cross-tenant access attempted | 403 | no | Tenancy violation | yes | `security_tenancy_violations_total` |

## Security contract

AUTHENTICATION: Bearer token validated via `get_current_tenant` and `require_roles`.
AUTHORIZATION: Role-based access control (`ANALYST`, `OPERATOR`, `SYSTEM_ADMIN` required for detect and transition).
TENANT: Explicit `TenantContext` isolation on all database and repository operations (INV-TEN-001).
PII: PROHIBITED — Metrics and anomalies contain aggregations and identifiers; no raw customer PII.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: Table `revpilot.anomaly_records` schema compliance per `packages/backend/src/revpilot/modules/analytics/adapters/postgres_repository.py`.
API CONTRACT: RESTful JSON conforming to `docs/26-api/API-STANDARDS.md`.
EVENT CONTRACT: NOT APPLICABLE — router endpoints do not publish outbox events directly.
TEMPORAL CONTRACT: NOT APPLICABLE — workflows not scheduled directly from router.
AGENT CONTRACT: NOT APPLICABLE — no agent changes.
MODEL CONTRACT: STL residual detector parameters conforming to `packages/backend/src/revpilot/modules/analytics/detectors/stl.py`.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: Client may retry on 503 with exponential backoff.
TIMEOUT: Query execution timeout 5.0 seconds.
IDEMPOTENCY: Query operations are idempotent (GET/POST query). Anomaly detection generates reproducible hash.
LOGGING: Structured logging on 503 dependency errors: `logger.error("Analytics repository unavailable for tenant %s", tenant.tenant_id)`.
METRICS: `analytics_dependency_unavailable_total` incremented on 503 errors.
FAILURE BEHAVIOR: Dependency missing → immediate fail-closed 503.
ROLLBACK/COMPENSATION: Git revert of `apps/api/routers/analytics.py`.

## Implementation requirements

1. In `apps/api/routers/analytics.py`:
   - Update `query_metric`: inspect `request.app.state` for query engine or repository. If absent, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Analytics query engine unavailable")`. Remove hardcoded series values `100.0` and `75.4`.
   - Update `detect_anomalies`: check `repo = getattr(request.app.state, "anomaly_repo", None)`. If `repo is None`, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Anomaly detection repository unavailable")`.
   - In `detect_anomalies` with repo present: compute dynamic anomaly actual/expected values and score from detector or input, removing hardcoded `-24.6`, `5.2`, `0.7820`.
   - In `list_anomalies`, `get_anomaly_detail`, `transition_anomaly`: check `repo = getattr(request.app.state, "anomaly_repo", None)`. If `repo is None`, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Anomaly repository unavailable")`. Remove all fallback mock dictionary payloads containing `-24.6`, `5.2`, `0.782`.
2. Ensure no active code in `apps/api/routers/analytics.py` contains the literal values `100.0`, `75.4`, `-24.6`, `5.2`, or `0.782`.

## Tests and evaluations

TESTS REQUIRED:
- Integration/unit tests asserting:
  - `POST /api/v1/analytics/metrics/query` with query engine None returns 503.
  - `POST /api/v1/analytics/anomalies/detect` with `anomaly_repo=None` returns 503.
  - `POST /api/v1/analytics/anomalies/detect` with `anomaly_repo` present returns 201 with dynamic data from repository.
  - `GET /api/v1/analytics/anomalies` with `anomaly_repo=None` returns 503.
  - `GET /api/v1/analytics/anomalies/{id}` with `anomaly_repo=None` returns 503.
- Grep test verifying absence of forbidden floating point literals in active code.

AI EVALS REQUIRED: NOT APPLICABLE — no AI model evaluation.
PERFORMANCE REQUIREMENTS: Response time < 200ms when healthy, < 10ms on 503 fail-closed.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "
import pathlib, re, sys
path = pathlib.Path('apps/api/routers/analytics.py')
content = path.read_text(encoding='utf-8')
forbidden = ['100.0', '75.4', '-24.6', '5.2', '0.782']
errors = []
for idx, line in enumerate(content.splitlines(), 1):
    stripped = line.strip()
    if stripped.startswith('#'):
        continue
    for target in forbidden:
        if re.search(r'(?<![0-9a-zA-Z_])' + re.escape(target) + r'(?![0-9a-zA-Z_])', stripped):
            errors.append(f'Line {idx}: forbidden literal {target} found: {stripped}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('PASS: No hardcoded analytics values in active code')
"
```

EXPECTED: exit code 0 and output `PASS: No hardcoded analytics values in active code`.

## Binary acceptance criteria

- `AC-AR-017-01`: PASS only if `query_metric` in `apps/api/routers/analytics.py` contains no hardcoded `100.0` or `75.4` literals in active code lines.
- `AC-AR-017-02`: PASS only if POST `/api/v1/analytics/anomalies/detect` with `anomaly_repo=None` returns HTTP 503.
- `AC-AR-017-03`: PASS only if POST `/api/v1/analytics/anomalies/detect` with `anomaly_repo` present returns anomaly data generated from the repository.
- `AC-AR-017-04`: PASS only if GET `/api/v1/analytics/anomalies` with `anomaly_repo=None` returns HTTP 503 instead of a synthetic fallback list.

## Postconditions

- `apps/api/routers/analytics.py` has all hardcoded values removed.
- Analytics endpoints return HTTP 503 when underlying repositories are uninitialized.
- Verification script exits 0.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Remove hardcoded values and enforce 503 fail-closed on missing dependencies |
| Dependency clarity | 2 | Clear dependency on AR-006 readiness baseline |
| File boundary clarity | 2 | Single file in WRITE_SET: `apps/api/routers/analytics.py` |
| Contract clarity | 2 | Exact endpoint behavior, status codes, and error envelopes specified |
| Failure behavior | 2 | Missing repo/engine yields deterministic 503 Service Unavailable |
| Security/tenancy | 2 | Preserves role checks and tenant isolation |
| Testability | 2 | 4 machine-verifiable criteria, integration testable |
| Verification | 2 | Automated python regex script, exit 0 |
| Acceptance criteria | 2 | Binary PASS/FAIL conditions on status codes and literals |
| Reasoning independence | 2 | Implementation follows standard fail-closed pattern without architectural choices |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Add synthetic mock fallbacks in router code for production path.
- Return HTTP 200 or 201 with fake anomaly records when database dependencies are missing.
- Modify files outside `apps/api/routers/analytics.py`.

## Required executor report

```text
TASK TASK-AR-017 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: NONE
FILES MODIFIED: apps/api/routers/analytics.py
UNEXPECTED FILES: NONE
TESTS: <verification output and test suite results>
COMMANDS AND EXIT CODES: python verification -> 0, pytest -> 0
ACCEPTANCE: AC-AR-017-01: PASS|FAIL, AC-AR-017-02: PASS|FAIL, AC-AR-017-03: PASS|FAIL, AC-AR-017-04: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-018, AR-019, AR-020, AR-021, or AR-022
```
