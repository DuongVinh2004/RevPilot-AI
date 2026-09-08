# TASK-AR-006 — Readiness Probe Dependency-Aware — Return 503 When Required Service Unhealthy

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 17
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IDENTITY-BOUNDARY
FEATURE: READINESS-FAILCLOSED
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-005
UNLOCKS: AR-017, AR-018, AR-019, AR-020, AR-021, AR-022, AR-025

## Objective and rationale

OBJECTIVE: Modify `/health/ready` endpoint in `apps/api/main.py` to perform real dependency health checks (database SELECT 1, auth_adapter presence, optional temporal_client) and return HTTP 503 when any required dependency is unhealthy. Modify `/metrics` endpoint to remove hardcoded Prometheus payload.

BUSINESS RATIONALE: Finding P1-REL-001 proved that readiness probe defaults `database`, `cache`, and `temporal` to `ok` when pool is None, and `/metrics` returns static counters with 0 request count. Container orchestrators rely on readiness probes to route traffic — false-green readiness sends traffic to an unhealthy instance.

ARCHITECTURAL OWNER: SRE Lead

ARCHITECTURAL CONTEXT: NFR-REL-001 (readiness semantics), INV-REL-001 (production reliability), ADR-0008 (container orchestration).

## Canonical specification references

- `docs/22-operations/RUNBOOK.md#health-checks` (if exists)
- `execution/DEFINITION-OF-DONE.md#stage-e-production-accepted`

If references conflict, return BLOCKED.

## Preconditions

- AR-005 PASS (auth adapter fail-closed ensures adapter is present in production).
- `apps/api/main.py` exists with `/health/ready` and `/metrics` endpoints.

## Change boundary

READ_SET:
- `apps/api/main.py` (full file)
- `pyproject.toml` (check if prometheus_client is a dependency)

WRITE_SET:
- `apps/api/main.py`
- `tests/integration/test_readiness_probe.py`

CREATE:
- `tests/integration/test_readiness_probe.py`

MODIFY:
- `apps/api/main.py` — Lines 260-300: Readiness probe and metrics endpoint.

DO_NOT_MODIFY:
- `apps/api/middleware/*`
- `apps/api/routers/*`
- `packages/*`

EXPECTED CHANGE SET:
- `apps/api/main.py`: Readiness probe does real checks, metrics endpoint returns 501 or real instrumentation.
- New test file with 5 test cases.

## Symbol-level contract

MUST EXPORT/DEFINE:
- Modified `readiness_probe(request)` in `apps/api/main.py`:
  - Check `db_pool = getattr(request.app.state, "db_pool", None)`. If None → component `database: degraded`.
  - If pool exists: `await pool.execute("SELECT 1")` wrapped in try/except. Exception → `database: degraded`.
  - Check `auth_adapter = getattr(request.app.state, "auth_adapter", None)`. If None → `auth: degraded`.
  - Check `temporal_client = getattr(request.app.state, "temporal_client", None)`. If None → `temporal: not_configured` (warning, not blocking for MVP).
  - If any REQUIRED dependency (database, auth) is degraded → return `JSONResponse(status_code=503, content={"status": "not_ready", "checks": {...}})`.
  - If all required healthy → return `{"status": "ready", "checks": {...}}`.
- Modified or replaced `/metrics` endpoint:
  - Remove hardcoded `revpilot_http_requests_total{...} 0` and `revpilot_up 1`.
  - Return `JSONResponse(status_code=501, content={"error": "Metrics instrumentation not configured"})` until prometheus_client is integrated.

MUST NOT:
- Return 200 from readiness when database or auth_adapter is unavailable.
- Return hardcoded metric values.
- Add prometheus_client as dependency (that's a separate task if needed).

## Input/output and validation

INPUT: HTTP GET `/health/ready`, `/metrics`.
OUTPUT: JSON with status and per-component check results.
INVALID INPUT: NOT APPLICABLE — GET endpoints.
VALIDATION RULES: 200 only if all required dependencies healthy. 503 otherwise.
STATE TRANSITIONS: NOT APPLICABLE.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `NOT_READY` | Database pool None or SELECT 1 fails | 503 | yes | `{"status": "not_ready", "checks": {...}}` | no | N/A |
| `NOT_READY` | Auth adapter None | 503 | yes | `{"status": "not_ready", "checks": {...}}` | no | N/A |
| `NOT_IMPLEMENTED` | Metrics not configured | 501 | no | Metrics instrumentation not configured | no | N/A |

## Security contract

AUTHENTICATION: NOT REQUIRED for health/ready (infrastructure probe).
AUTHORIZATION: NOT REQUIRED.
TENANT: NOT APPLICABLE.
PII: PROHIBITED — health checks must not expose connection strings or secrets.
SECRET ACCESS: PROHIBITED — do not log or return DATABASE_URL.
EXTERNAL ACTION: Database SELECT 1 (read-only, no side effect).
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE.
API CONTRACT:
- `GET /health/ready` → 200 `{"status": "ready", "checks": {"database": "ok", "auth": "ok"}}` or 503 `{"status": "not_ready", "checks": {"database": "degraded", ...}}`.
- `GET /metrics` → 501 `{"error": "Metrics instrumentation not configured"}`.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: Orchestrator retries readiness automatically.
TIMEOUT: SELECT 1 timeout 5 seconds.
IDEMPOTENCY: GET endpoints are idempotent.
LOGGING: Log readiness check failures at WARNING level.
METRICS: NOT APPLICABLE until instrumentation configured.
FAILURE BEHAVIOR: Any required dependency failure → 503.
ROLLBACK/COMPENSATION: Revert `apps/api/main.py`.

## Implementation requirements

1. Read `apps/api/main.py` lines 254-300.
2. Replace readiness probe:
   ```python
   @api_app.get("/health/ready", tags=["Operations"])
   async def readiness_probe(request: Request) -> JSONResponse:
       checks = {}
       is_ready = True
       
       # Database check
       pool = getattr(request.app.state, "db_pool", None)
       if pool is None:
           checks["database"] = "degraded"
           is_ready = False
       else:
           try:
               async with pool.acquire() as conn:
                   await conn.execute("SELECT 1")
               checks["database"] = "ok"
           except Exception as exc:
               logger.warning("Readiness: database check failed: %s", exc)
               checks["database"] = "degraded"
               is_ready = False
       
       # Auth adapter check
       auth_adapter = getattr(request.app.state, "auth_adapter", None)
       if auth_adapter is None:
           checks["auth"] = "degraded"
           is_ready = False
       else:
           checks["auth"] = "ok"
       
       # Temporal check (optional for MVP)
       temporal = getattr(request.app.state, "temporal_client", None)
       checks["temporal"] = "ok" if temporal else "not_configured"
       
       status_code = 200 if is_ready else 503
       payload = {"status": "ready" if is_ready else "not_ready", "checks": checks}
       return JSONResponse(status_code=status_code, content=payload)
   ```
3. Replace metrics endpoint:
   ```python
   @api_app.get("/metrics", tags=["Operations"])
   async def metrics_endpoint() -> JSONResponse:
       return JSONResponse(
           status_code=501,
           content={"error": "Metrics instrumentation not configured. Integrate prometheus_client for real metrics."},
       )
   ```
4. Create `tests/integration/test_readiness_probe.py` with 5 tests:
   - `test_readiness_healthy`: Mock pool+adapter present → 200.
   - `test_readiness_no_pool`: pool=None → 503.
   - `test_readiness_pool_select_fails`: pool.execute raises → 503.
   - `test_readiness_no_auth_adapter`: adapter=None → 503.
   - `test_metrics_not_hardcoded`: `/metrics` response does not contain `revpilot_http_requests_total{method="POST",path="/api/v1/anomalies/detect",status="201"} 0`.

## Tests and evaluations

TESTS REQUIRED:
- 5 test cases in `tests/integration/test_readiness_probe.py`.
- Full regression: `python -m pytest tests/ -q` exit 0.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Readiness check < 5 seconds.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/integration/test_readiness_probe.py -v && python -m pytest tests/ -q
```

EXPECTED: exit code 0, 5/5 readiness tests pass, full suite passes.

## Binary acceptance criteria

- `AC-AR-006-01`: PASS only if readiness probe with `db_pool=None` returns HTTP 503.
- `AC-AR-006-02`: PASS only if readiness probe with `auth_adapter=None` returns HTTP 503.
- `AC-AR-006-03`: PASS only if `/metrics` response does not contain `revpilot_http_requests_total{method="POST",path="/api/v1/anomalies/detect",status="201"} 0`.
- `AC-AR-006-04`: PASS only if `python -m pytest tests/integration/test_readiness_probe.py -v` exits 0 with 5/5 pass.

## Postconditions

- `/health/ready` returns 503 when required dependencies unavailable.
- `/metrics` does not return hardcoded payload.
- 5 integration tests pass.
- Full test suite passes.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Two endpoint modifications with exact behavior |
| Dependency clarity | 2 | Single upstream: AR-005 |
| File boundary clarity | 2 | 1 MODIFY, 1 CREATE |
| Contract clarity | 2 | Exact response schemas specified |
| Failure behavior | 2 | Every unhealthy dependency → 503 |
| Security/tenancy | 2 | No secrets exposed in health checks |
| Testability | 2 | 5 concrete test scenarios |
| Verification | 2 | pytest command, exit 0 |
| Acceptance criteria | 2 | 4 machine-verifiable criteria |
| Reasoning independence | 2 | No architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Add prometheus_client dependency.
- Return 200 when required dependency is unavailable.
- Expose connection strings or secrets in health check responses.

## Required executor report

```text
TASK TASK-AR-006 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_readiness_probe.py
FILES MODIFIED: apps/api/main.py
UNEXPECTED FILES: NONE
TESTS: 5 readiness tests PASS, full suite PASS
COMMANDS AND EXIT CODES: pytest readiness tests → 0, pytest full → 0
ACCEPTANCE: AC-AR-006-01: PASS|FAIL, AC-AR-006-02: PASS|FAIL, AC-AR-006-03: PASS|FAIL, AC-AR-006-04: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-017..022 or AR-025
```
