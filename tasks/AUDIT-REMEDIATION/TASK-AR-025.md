# TASK-AR-025 — Metrics Endpoint Real Instrumentation

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 17
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: SECURITY-HARDENING
FEATURE: METRICS-REAL
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-006
UNLOCKS: AR-029

## Objective and rationale

OBJECTIVE: Replace hardcoded static `/metrics` payload in `apps/api/main.py` with dynamic, real in-memory HTTP request instrumentation conforming to Prometheus exposition format 0.0.4, or fail closed with HTTP 501 when unconfigured. Eliminate hardcoded static counter `revpilot_http_requests_total{status="200"} 0`.

BUSINESS RATIONALE: Audit finding P1-REL-001 identified that the `/metrics` operational endpoint returned a static, hardcoded string asserting zero total requests regardless of traffic volume. Hardcoded metrics provide false telemetry to monitoring and alerting infrastructure (e.g., Prometheus/Grafana), masking traffic patterns and system failures in violation of INV-REL-001 (observability integrity) and AC-014 (anti-fabrication invariant).

ARCHITECTURAL OWNER: SRE Lead / Observability Architect

ARCHITECTURAL CONTEXT: INV-REL-001 (production reliability and honest telemetry), AC-014 (anti-fabrication), `docs/22-operations/OBSERVABILITY-SPEC.md` §3, `docs/26-api/API-STANDARDS.md` §11.

## Canonical specification references

- `docs/22-operations/RUNBOOK.md#health-checks`
- `docs/26-api/API-STANDARDS.md#11-observability-endpoints`
- `execution/DEFINITION-OF-DONE.md`
- `AGENTS.md#3-strict-prohibitions`

If references conflict, return BLOCKED.

## Preconditions

- AR-006 PASS (readiness probe dependency-aware health checks active).
- `apps/api/main.py` exists with `/metrics` route.
- FastAPI application initializes with state management.

## Change boundary

READ_SET:
- `apps/api/main.py` (full file)
- `tests/integration/test_readiness_probe.py` (if exists)

WRITE_SET:
- `apps/api/main.py`
- `tests/integration/test_metrics_endpoint.py`

CREATE:
- `tests/integration/test_metrics_endpoint.py`

MODIFY:
- `apps/api/main.py` — lines 288-300:
  - Add request counter tracking mechanism (e.g., application state counter initialized at startup or lightweight middleware recording request counts by status code).
  - Update `prometheus_metrics` endpoint to dynamically generate Prometheus exposition text with real tracked counts.
  - Remove all hardcoded static `} 0\n` values.

DO_NOT_MODIFY:
- `apps/api/routers/*`
- `apps/api/middleware/authentication.py`
- `packages/backend/*`
- Any file outside WRITE_SET

EXPECTED CHANGE SET:
- 1 modified API application entry file with dynamic metric counter generation.
- 1 new integration test file verifying metrics exposition and counter increments.

## Symbol-level contract

MUST EXPORT/DEFINE:
- `apps/api/main.py`:
  - Request tracking mechanism on `app.state` or middleware:
    - Increments request counter for each processed HTTP request.
  - `prometheus_metrics(request: Request) -> Response`:
    - Content-Type: `text/plain; version=0.0.4`.
    - Outputs `# HELP revpilot_http_requests_total Total HTTP requests received`.
    - Outputs `# TYPE revpilot_http_requests_total counter`.
    - Emits actual counter value: `revpilot_http_requests_total{status="200"} <N>`.
    - Outputs `# HELP revpilot_up System availability indicator`.
    - Outputs `# TYPE revpilot_up gauge`.
    - Emits `revpilot_up 1`.
- `tests/integration/test_metrics_endpoint.py`:
  - `test_metrics_endpoint_status_and_content_type()`: Verifies HTTP 200 and text/plain; version=0.0.4.
  - `test_metrics_counter_increments_after_requests()`: Sends 5 requests to `/health/live` and verifies counter > 0.
  - `test_metrics_has_no_hardcoded_zero_counter()`: Verifies response contains dynamic non-zero count after traffic.

MUST NOT:
- Return hardcoded static string containing `revpilot_http_requests_total{status="200"} 0` regardless of traffic.
- Introduce external heavyweight C-extension dependencies unless already present in `pyproject.toml`.
- Expose PII, tokens, or database credentials in metrics labels.

## Input/output and validation

INPUT: HTTP GET to `/metrics`.
OUTPUT: HTTP 200 response with `media_type="text/plain; version=0.0.4"` containing standard Prometheus metrics text.
INVALID INPUT: NOT APPLICABLE — GET endpoint without body.
VALIDATION RULES: Real counter must increment with each HTTP request served by the application.
STATE TRANSITIONS: In-memory counter monotonically increases with incoming requests.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `NOT_IMPLEMENTED` | Metrics subsystem disabled | 501 | no | Metrics instrumentation not configured | no | N/A |
| `INTERNAL_ERROR` | Error formatting metric output | 500 | yes | Failed to generate metrics | yes | `metric_generation_errors_total` |

## Security contract

AUTHENTICATION: NOT REQUIRED for operational metrics endpoint (scraped by internal Prometheus collector).
AUTHORIZATION: Infrastructure network boundary isolation (Zone 2/3 private network access).
TENANT: System-level aggregated metric — NO tenant identifiers or per-tenant PII exposed.
PII: PROHIBITED — strictly disallowed in Prometheus labels or metric values.
SECRET ACCESS: PROHIBITED — no credentials in metrics output.
EXTERNAL ACTION: PROHIBITED — read-only in-memory counter aggregation.
DEFAULT: ALLOW for infrastructure probes on internal interface.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE.
API CONTRACT: Conforms to Prometheus Exposition Format version 0.0.4.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: Scraped periodically on 15s-30s intervals by Prometheus collector.
TIMEOUT: Endpoint execution < 5ms.
IDEMPOTENCY: GET is read-only (observes cumulative state).
LOGGING: Do not log routine scrape requests to prevent log volume saturation.
METRICS: Self-instrumenting endpoint.
FAILURE BEHAVIOR: Returns HTTP 501 if instrumentation disabled or 500 on internal formatting error.
ROLLBACK/COMPENSATION: Revert changes to `apps/api/main.py` and delete test file.

## Implementation requirements

1. In `apps/api/main.py`, initialize request counters on application state, e.g. `api_app.state.request_count_200 = 0` (or a dictionary of status counters).
2. Add a lightweight middleware or response hook to increment request counters for served requests.
3. In `prometheus_metrics(request: Request)`:
   - Read dynamic count from `request.app.state`.
   - Format metric payload with the live count value:
     ```python
     count_200 = getattr(request.app.state, "request_count_200", 0)
     metrics_payload = (
         "# HELP revpilot_http_requests_total Total HTTP requests received\n"
         "# TYPE revpilot_http_requests_total counter\n"
         f'revpilot_http_requests_total{{status="200"}} {count_200}\n'
         "# HELP revpilot_up System availability indicator\n"
         "# TYPE revpilot_up gauge\n"
         "revpilot_up 1\n"
     )
     ```
4. Verify no hardcoded `} 0\n` remains in the codebase.
5. Create `tests/integration/test_metrics_endpoint.py`:
   - Send 5 requests to `/health/live`.
   - Send GET to `/metrics`.
   - Assert `revpilot_http_requests_total{status="200"}` has value >= 5.
6. Run full test suite to guarantee zero regression.

## Tests and evaluations

TESTS REQUIRED:
- Integration tests in `tests/integration/test_metrics_endpoint.py`.
- Regression check: `pytest tests/ -q` exits 0.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Dynamic string formatting < 1ms per scrape.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
grep -rn "} 0" apps/api/main.py || true && python -m pytest tests/integration/test_metrics_endpoint.py -v && python -m pytest tests/ -q
```

EXPECTED:
- `grep` finds zero occurrences of hardcoded `} 0` in `apps/api/main.py`.
- `pytest tests/integration/test_metrics_endpoint.py` exits 0.
- Full pytest suite exits 0.

## Binary acceptance criteria

- `AC-AR-025-01`: PASS only if GET `/metrics` after making 5 HTTP requests reflects `revpilot_http_requests_total` count greater than 0 matching observed requests.
- `AC-AR-025-02`: PASS only if `grep -rn "} 0" apps/api/main.py` returns 0 matches.
- `AC-AR-025-03`: PASS only if `python -m pytest tests/integration/test_metrics_endpoint.py` passes with exit code 0.

## Postconditions

- `/metrics` endpoint delivers dynamic Prometheus metrics based on actual traffic.
- Hardcoded static `revpilot_http_requests_total{status="200"} 0` string eliminated.
- Test coverage validates counter increments following HTTP request activity.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Replace static metrics string with dynamic in-memory request counter |
| Dependency clarity | 2 | Clear dependency: AR-006 |
| File boundary clarity | 2 | Modifies only `apps/api/main.py` lines 288-300; creates 1 test file |
| Contract clarity | 2 | Conforms to Prometheus exposition format 0.0.4 with exact metric names |
| Failure behavior | 2 | Clean 501 or 500 failure behavior specified |
| Security/tenancy | 2 | System-level metric with no PII, no secrets, no tenant leakage |
| Testability | 2 | Integration tests with 5 sequential requests asserting count > 0 |
| Verification | 2 | Offline hermetic grep and pytest commands |
| Acceptance criteria | 2 | 3 binary machine-verifiable criteria |
| Reasoning independence | 2 | Complete design specified; no new architectural decisions |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Retain any hardcoded `} 0` metric string in `apps/api/main.py`.
- Introduce unauthorized third-party libraries into `pyproject.toml`.
- Expose tenant names, IDs, or principal information in Prometheus metric tags.
- Modify files outside the explicit WRITE_SET.

## Required executor report

```text
TASK TASK-AR-025 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_metrics_endpoint.py
FILES MODIFIED: apps/api/main.py
UNEXPECTED FILES: NONE
TESTS: metrics endpoint integration tests PASS, full suite PASS
COMMANDS AND EXIT CODES: grep → 0 matches, pytest metrics tests → 0, pytest full → 0
ACCEPTANCE: AC-AR-025-01: PASS|FAIL, AC-AR-025-02: PASS|FAIL, AC-AR-025-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-029
```
