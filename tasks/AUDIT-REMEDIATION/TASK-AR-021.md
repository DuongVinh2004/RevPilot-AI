# TASK-AR-021 — Investigation Temporal Workflow — Real Start, Durable State, Error Propagation

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 7
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: DOMAIN-EXECUTION
FEATURE: INVESTIGATION-TEMPORAL
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-017..020,022
DEPENDS_ON: AR-006
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Replace empty `pass` statement in try block and exception swallowing at `apps/api/routers/investigations.py` lines 73-80 with real Temporal workflow start logic. Propagate HTTP 503 when workflow start fails. Update `GET /investigations/{investigation_id}` (lines 90-113) to return HTTP 404 when `investigation_repo` is None or when the record is not found.

BUSINESS RATIONALE: Zero-trust audit finding P1-WF-001 identified that `create_investigation` contained an empty `pass` in its Temporal try/except block, swallowing all exceptions silently and returning HTTP 202 without initiating workflow orchestration. Furthermore, `get_investigation` returned static mock payloads with status `COMPLETED` when `investigation_repo` was None, masking orchestration failures and giving false visibility into phantom investigations. Removing swallows and enforcing 404/503 behavior guarantees durable lifecycle visibility (INV-WF-001) and transparent failure reporting.

ARCHITECTURAL OWNER: Workflow Engine Lead, Backend Lead

ARCHITECTURAL CONTEXT: INV-WF-001 (Durable orchestration guarantee), docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md, docs/26-api/API-STANDARDS.md §6.

## Canonical specification references

- `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md#investigation-workflow`
- `docs/26-api/API-STANDARDS.md#61-launch-investigation-workflow-api`
- `docs/26-api/API-STANDARDS.md#error-handling`
- `execution/DEFINITION-OF-DONE.md`

If references conflict, return BLOCKED.

## Preconditions

- AR-006 PASS (Readiness probe dependency-aware).
- `apps/api/routers/investigations.py` exists with `create_investigation` and `get_investigation`.
- `revpilot.modules.investigation.workflows` exports `InvestigationWorkflow`, `InvestigationWorkflowInput`, and `INVESTIGATION_WORKFLOW_QUEUE`.

## Change boundary

READ_SET:
- `apps/api/routers/investigations.py`
- `packages/backend/src/revpilot/modules/investigation/workflows/investigation_workflow.py`
- `packages/backend/src/revpilot/modules/investigation/workflows/signals.py`
- `tests/contract/test_phase_03_exit_gate.py`

WRITE_SET:
- `apps/api/routers/investigations.py`
- `tests/integration/test_investigation_temporal.py`

CREATE:
- `tests/integration/test_investigation_temporal.py`

MODIFY:
- `apps/api/routers/investigations.py` —
  - Lines 73-81: Replace empty `pass` and bare `except Exception: pass`. Import `InvestigationWorkflow`, `InvestigationWorkflowInput`, `INVESTIGATION_WORKFLOW_QUEUE`. When `temporal_client` is configured on `request.app.state`, construct input and await `temporal_client.start_workflow(...)`. On exception, log via `logger.error(..., exc_info=True)` and raise `HTTPException(status_code=503, detail="Failed to start investigation workflow")`.
  - Lines 90-113: In `get_investigation`, remove hardcoded fallback mock object returned when `repo is None`. Raise `NotFoundError(f"Investigation '{investigation_id}' not found.")` when repo is None or when record is not found in repo.

DO_NOT_MODIFY:
- `packages/backend/src/revpilot/modules/investigation/workflows/*`
- `apps/api/routers/causal.py`
- `apps/api/routers/admin.py`
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 2 endpoints updated in `apps/api/routers/investigations.py`, 1 new integration test suite (`tests/integration/test_investigation_temporal.py`).

## Symbol-level contract

MUST EXPORT/DEFINE:

Modified workflow initiation in `create_investigation` (`apps/api/routers/investigations.py`):
```python
temporal_client = getattr(request.app.state, "temporal_client", None)
if temporal_client is not None:
    try:
        from revpilot.modules.investigation.workflows import (
            InvestigationWorkflow,
            InvestigationWorkflowInput,
            INVESTIGATION_WORKFLOW_QUEUE,
        )
        wf_input = InvestigationWorkflowInput(
            tenant_id=str(tenant.tenant_id),
            investigation_id=inv_id,
            anomaly_id=payload.anomaly_id,
            metric_name=payload.metric_name,
            cost_budget_usd=payload.cost_budget_usd,
            time_budget_seconds=payload.time_budget_seconds,
        )
        await temporal_client.start_workflow(
            InvestigationWorkflow.run,
            wf_input,
            id=workflow_id,
            task_queue=INVESTIGATION_WORKFLOW_QUEUE,
        )
    except Exception as exc:
        logger.error(
            "Temporal workflow start failed for investigation %s (workflow_id=%s): %s",
            inv_id,
            workflow_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to start investigation workflow",
        )
```

Modified record retrieval in `get_investigation` (`apps/api/routers/investigations.py`):
```python
@router.get("/{investigation_id}")
async def get_investigation(
    investigation_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Retrieve investigation status and summary."""
    repo = getattr(request.app.state, "investigation_repo", None)
    if repo is not None:
        res = await repo.get_by_id(tenant, investigation_id)
        if res:
            return res

    raise NotFoundError(f"Investigation '{investigation_id}' not found.")
```

MUST NOT:
- Contain empty `pass` in try or except blocks.
- Swallow exceptions without logging and propagating failure to caller.
- Return fake HTTP 200 mock objects when `investigation_repo` is None.
- Return 202 if Temporal workflow start fails when `temporal_client` is configured.

## Input/output and validation

INPUT:
- POST `/api/v1/investigations` with body:
  ```json
  {
    "anomaly_id": "anom_01h8x8a7b3c1",
    "metric_name": "Net MRR Expansion Rate",
    "time_budget_seconds": 180,
    "cost_budget_usd": 2.00
  }
  ```
- GET `/api/v1/investigations/{investigation_id}`

OUTPUT:
- POST 202: `{"investigation_id": "inv_...", "workflow_id": "tenant/.../investigation/...", "status": "INITIALIZING", "created_at": "..."}`
- GET 200: Investigation record dictionary
- GET 404: `{"error": {"code": "RESOURCE_NOT_FOUND", "message": "Investigation '...' not found"}}`
- POST 503: `{"detail": "Failed to start investigation workflow"}`

INVALID INPUT:
- Missing required fields → 400 Bad Request.
- Unauthenticated caller → 401 Unauthorized.
- Unauthorized role → 403 Forbidden.

STATE TRANSITIONS:
- POST 202: Investigation state enters INITIALIZING; Temporal workflow scheduled.
- Workflow execution failures: System returns 503 Service Unavailable immediately.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `RESOURCE_NOT_FOUND` | Investigation ID not found or repo None | 404 | no | Investigation '{id}' not found | yes | investigations_not_found_total |
| `SERVICE_UNAVAILABLE` | Temporal workflow start failed | 503 | yes | Failed to start investigation workflow | yes | workflow_start_failed_total |
| `VALIDATION_ERROR` | Invalid request schema | 400 | no | Invalid request payload schema | yes | validation_failed_total |
| `AUTHENTICATION_ERROR` | Missing or invalid auth | 401 | no | Invalid or expired token | yes | auth_failed_total |

## Security contract

AUTHENTICATION: Required (Bearer token via `get_current_tenant`).
AUTHORIZATION: Roles `ANALYST`, `OPERATOR`, `SYSTEM_ADMIN` required to launch investigations.
TENANT: Workflow ID contains tenant ID (`tenant/{tenant_id}/investigation/{inv_id}`) enforcing namespace partition. GET queries strictly scoped by `TenantContext`.
PII: Metric names and anomalies only; no customer PII in workflow initialization payload.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: Triggers internal Temporal workflow orchestration.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE.
API CONTRACT: Conforms to docs/26-api/API-STANDARDS.md §6.1.
EVENT CONTRACT: Broadcasts initialization event via `InvestigationEventBroadcaster`.
TEMPORAL CONTRACT: Invokes `InvestigationWorkflow.run` on `INVESTIGATION_WORKFLOW_QUEUE` with deterministic `workflow_id`.
AGENT CONTRACT: Enforces durable orchestration for autonomous multi-agent investigations.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: Client may retry on 503 (transient orchestrator failure).
TIMEOUT: Workflow dispatch timeout < 2 seconds.
IDEMPOTENCY: Workflow ID derived deterministically from tenant ID and unique investigation ID.
LOGGING: Failures logged via `logger.error` with stack trace and correlation context.
METRICS: Record `investigation_workflow_launches_total{status="success|failure"}`.
FAILURE BEHAVIOR: Fail-closed; return 503 on engine disconnect or workflow rejection.
ROLLBACK/COMPENSATION: Revert changes in `apps/api/routers/investigations.py`.

## Implementation requirements

1. In `apps/api/routers/investigations.py`:
   - Add module logger: `logger = logging.getLogger(__name__)`.
   - Ensure imports: `from fastapi import HTTPException, status` and `from revpilot.shared.errors import NotFoundError`.
   - In `create_investigation`, inspect `temporal_client = getattr(request.app.state, "temporal_client", None)`.
   - When `temporal_client` is not None:
     - Instantiate `InvestigationWorkflowInput` with tenant ID, investigation ID, anomaly ID, metric name, budgets.
     - Await `temporal_client.start_workflow(InvestigationWorkflow.run, wf_input, id=workflow_id, task_queue=INVESTIGATION_WORKFLOW_QUEUE)`.
     - In `except Exception as exc`: log error with full stack trace and raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Failed to start investigation workflow: {str(exc)}")`.
   - In `get_investigation`, remove mock dictionary fallback on lines 104-113. If `repo is None` or `res is None`, raise `NotFoundError(f"Investigation '{investigation_id}' not found.")`.
2. Create `tests/integration/test_investigation_temporal.py` with 5 tests:
   - `test_investigation_no_pass_statement`: Static verification that `pass` does not appear in lines 70-85 of `apps/api/routers/investigations.py`.
   - `test_investigation_start_success`: With mock `temporal_client`, `POST /api/v1/investigations` returns 202 and `start_workflow` is called with expected parameters.
   - `test_investigation_start_failure_propagates_503`: With `temporal_client.start_workflow` raising an exception, `POST /api/v1/investigations` returns 503.
   - `test_investigation_get_repo_none_returns_404`: With `investigation_repo = None`, `GET /api/v1/investigations/inv_missing` returns 404.
   - `test_investigation_get_not_found_returns_404`: With `investigation_repo` returning None, `GET /api/v1/investigations/inv_not_exist` returns 404.

## Tests and evaluations

TESTS REQUIRED:
- `tests/integration/test_investigation_temporal.py` (5 tests).
- `tests/integration/test_domain_routes.py` (regression).

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Workflow dispatch latency < 100ms.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/integration/test_investigation_temporal.py tests/integration/test_domain_routes.py -v
```

EXPECTED: exit code 0, 5/5 temporal investigation tests pass, existing domain tests pass.

## Binary acceptance criteria

- `AC-AR-021-01`: PASS only if no empty `pass` statement exists in try/except blocks in `apps/api/routers/investigations.py`.
- `AC-AR-021-02`: PASS only if exceptions raised during Temporal workflow start are logged via `logger.error` or `logger.exception` and not silently swallowed.
- `AC-AR-021-03`: PASS only if `GET /api/v1/investigations/{investigation_id}` returns HTTP 404 when `investigation_repo` is None.
- `AC-AR-021-04`: PASS only if `POST /api/v1/investigations` returns HTTP 503 when `temporal_client.start_workflow` raises an exception.
- `AC-AR-021-05`: PASS only if `python -m pytest tests/integration/test_investigation_temporal.py -v` exits 0 with 5/5 pass.

## Postconditions

- Temporal workflows are actively dispatched when `temporal_client` is present.
- Workflow dispatch failures return HTTP 503 and log diagnostic errors.
- Unfound investigations and missing repositories return HTTP 404 rather than synthetic completed responses.
- Verification command exits 0.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Real workflow dispatch, error logging, and 404/503 status mapping explicitly stated |
| Dependency clarity | 2 | Depends on AR-006; clear workflows module integration |
| File boundary clarity | 2 | 1 MODIFY (`investigations.py`), 1 CREATE (`test_investigation_temporal.py`) |
| Contract clarity | 2 | Concrete error codes, status codes, and input/output contracts defined |
| Failure behavior | 2 | 503 on engine failure, 404 on missing entity, fail-closed throughout |
| Security/tenancy | 2 | Workflow ID and investigation query scoped by tenant |
| Testability | 2 | 5 isolated unit/integration test scenarios with mock Temporal client |
| Verification | 2 | Single offline hermetic pytest command |
| Acceptance criteria | 2 | 5 binary machine-verifiable criteria |
| Reasoning independence | 2 | Clear implementation code patterns; zero architectural ambiguity |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Use `pass` to ignore exceptions in workflow dispatch or data operations.
- Return fake `COMPLETED` payloads when repository has no data.
- Return 202 when Temporal workflow start fails.

## Required executor report

```text
TASK TASK-AR-021 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_investigation_temporal.py
FILES MODIFIED: apps/api/routers/investigations.py
UNEXPECTED FILES: NONE
TESTS: 5 temporal investigation tests PASS, domain routes PASS
COMMANDS AND EXIT CODES: pytest temporal tests → 0
ACCEPTANCE: AC-AR-021-01: PASS|FAIL, AC-AR-021-02: PASS|FAIL, AC-AR-021-03: PASS|FAIL, AC-AR-021-04: PASS|FAIL, AC-AR-021-05: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-020 or AR-022
```
