# TASK-AR-015 — Tool Gateway Provider Adapter Interface — Replace Mock in Production Path

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 15
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: APPROVAL-ACTION
FEATURE: PROVIDER-ADAPTER
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-014
UNLOCKS: AR-016

## Objective and rationale

OBJECTIVE: `gateway.py` must call provider adapter via port interface, not `MockProviderAdapter`. Mock forbidden when `ENVIRONMENT!=test`. Digest verify uses `verify_approval_digest`, not length check.

BUSINESS RATIONALE: Zero-trust audit finding P1-ACT-002 identified that `ActionCapabilityGateway` directly instantiates and executes `MockProviderAdapter` regardless of runtime environment, and Gate 2 validates approval digests solely through a superficial length check (`len(req.approval_digest) == 64`). In production, this allows mocked executions without real side effects to masquerade as valid completions in the audit ledger, and allows action dispatches with arbitrary 64-character strings without cryptographic signature verification against the sealed approval record (violating INV-ACT-001, INV-ACT-002, and AC-008).

ARCHITECTURAL OWNER: Tool Gateway Lead, Security Architect

ARCHITECTURAL CONTEXT: INV-ACT-001 (audited action dispatch), INV-ACT-002 (cryptographic approval sealing), INV-SEC-001 (fail-closed boundaries), AC-008, AC-009, ADR-0009.

## Canonical specification references

- `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md#provider-adapters`
- `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md#approval-digest-verification`
- `AGENTS.md#3-strict-prohibitions`
- `execution/DEFINITION-OF-DONE.md`

If references conflict, return BLOCKED.

## Preconditions

- AR-014 PASS (Action Saga & Reconciliation boundary verified).
- `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py` exists.
- `packages/backend/src/revpilot/modules/approval/digest.py` exists and exports `verify_approval_digest` and `ApprovalArtifact`.

## Change boundary

READ_SET:
- `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py`
- `packages/backend/src/revpilot/modules/tool_gateway/action/mock_adapter.py`
- `packages/backend/src/revpilot/modules/approval/digest.py`
- `tests/contract/test_phase_06_exit_gate.py`

WRITE_SET:
- `packages/backend/src/revpilot/modules/tool_gateway/ports/provider_adapter.py`
- `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py`
- `tests/unit/test_tool_gateway_provider_adapter.py`

CREATE:
- `packages/backend/src/revpilot/modules/tool_gateway/ports/provider_adapter.py`
- `tests/unit/test_tool_gateway_provider_adapter.py`

MODIFY:
- `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py`:
  - Replace `mock_adapter` constructor parameter and attribute with `provider_adapter: ProviderAdapterPort`.
  - Add runtime environment validation: forbid `MockProviderAdapter` when `ENVIRONMENT != "test"` (e.g. `ENVIRONMENT == "production"`), raising `GatewayError(code="ERR_MOCK_PROVIDER_FORBIDDEN", ...)` fail-closed.
  - Lines 165–173 (Gate 2): Replace `len(req.approval_digest) != 64` length check with cryptographic verification via `verify_approval_digest`.
  - Lines 236–243 (Gate 7): Invoke `self.provider_adapter.execute(...)` instead of `self.mock_adapter.execute(...)`.

DO_NOT_MODIFY:
- `packages/backend/src/revpilot/modules/tool_gateway/action/credential_broker.py`
- `packages/backend/src/revpilot/modules/approval/service.py`
- `apps/api/routers/approvals.py`
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 2 new files, 1 modified file.

## Symbol-level contract

MUST EXPORT/DEFINE:

`packages/backend/src/revpilot/modules/tool_gateway/ports/provider_adapter.py`:
```python
from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, ConfigDict, Field
from revpilot.modules.tool_gateway.action.credential_broker import EphemeralCredential, GatewayError
from revpilot.shared.results import Result

class ProviderResponse(BaseModel):
    """Normalized response payload returned by external or mock provider adapters."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    http_status_code: int = Field(ge=100, le=599, default=200)
    provider_tx_id: str = Field(min_length=1)
    response_payload: dict[str, Any]
    duration_ms: int = Field(ge=0, default=0)

@runtime_checkable
class ProviderAdapterPort(Protocol):
    """Authoritative port contract for external action dispatch adapters."""

    def execute(
        self,
        intent_id: str,
        action_type: str,
        target_entities: list[str],
        payload: dict[str, Any],
        credential: EphemeralCredential,
    ) -> Result[ProviderResponse, GatewayError]:
        ...
```

`packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py`:
```python
class ActionCapabilityGateway:
    def __init__(
        self,
        credential_broker: CredentialBroker | None = None,
        provider_adapter: ProviderAdapterPort | None = None,
        default_provider: str = "mock_logistics_v1",
        environment: str | None = None,
    ) -> None:
        ...
```

MUST NOT:
- Allow `MockProviderAdapter` to be used when `ENVIRONMENT != "test"` (e.g., `ENVIRONMENT=production`).
- Rely on length check (`len(digest) == 64`) or regex check for approval digest verification.
- Bypass Gate 2 cryptographic verification.
- Remove secret scrubbing (Gate 6) or credential validation (Gate 5).

## Input/output and validation

INPUT: `ActionCapabilityRequest` submitted with tenant context, action parameters, and approval digest.
OUTPUT: `Result[ActionLedgerRecord, GatewayError]`.
INVALID INPUT:
- `MockProviderAdapter` supplied or defaulted when `ENVIRONMENT != "test"` → `Failure(GatewayError(code="ERR_MOCK_PROVIDER_FORBIDDEN"))`.
- `approval_digest` that does not match `verify_approval_digest(...)` → `Failure(GatewayError(code="ERR_APPROVAL_DIGEST_MISMATCH"))`.
VALIDATION RULES:
1. `provider_adapter` must satisfy `isinstance(adapter, ProviderAdapterPort)`.
2. When environment is not test (`os.getenv("ENVIRONMENT", "test").lower() != "test"`), any instance or subclass of `MockProviderAdapter` is rejected immediately.
3. Gate 2 verifies the digest cryptographically using `verify_approval_digest` in constant time via `hmac.compare_digest`.
STATE TRANSITIONS: Dispatches transition from preflight checks (Gates 1–6) to execution (Gate 7). Results in ledger record with `execution_status="SUCCESS"` or `execution_status="PROVIDER_ERROR"`.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `ERR_MOCK_PROVIDER_FORBIDDEN` | `MockProviderAdapter` configured in non-test environment | 500 | no | Mock provider adapter forbidden in production environment | yes | `revpilot_gateway_errors_total{code="ERR_MOCK_PROVIDER_FORBIDDEN"}` |
| `ERR_APPROVAL_DIGEST_MISMATCH` | Approval digest does not match sealed artifact | 409 | no | Action dispatch approval digest verification failed | yes | `revpilot_gateway_errors_total{code="ERR_APPROVAL_DIGEST_MISMATCH"}` |
| `ERR_TENANT_MISMATCH` | Context tenant != request tenant | 403 | no | Context tenant does not match request tenant | yes | `revpilot_gateway_errors_total{code="ERR_TENANT_MISMATCH"}` |
| `ERR_PROVIDER_EXECUTION_FAILED` | Upstream provider execution returns failure | 502 | yes | External provider action execution failed | yes | `revpilot_gateway_errors_total{code="ERR_PROVIDER_EXECUTION_FAILED"}` |

## Security contract

AUTHENTICATION: TenantContext and PrincipalContext mandatory on all dispatches.
AUTHORIZATION: Requires valid ephemeral credential issued by `CredentialBroker`.
TENANT: Strict tenant isolation; context tenant must equal request tenant (INV-TEN-002).
PII: Request and response payloads recursively scrubbed via `scrub_secrets` before logging or digest computation.
SECRET ACCESS: Ephemeral tokens scrubbed from logs and ledger records.
EXTERNAL ACTION: External network calls strictly confined to authorized `ProviderAdapterPort` implementations executing outside `agent_egress_barrier`.
DEFAULT: DENY — fail-closed on any validation failure or adapter violation.

## Specialized contracts

DATA CONTRACT: `ProviderResponse` schema with `http_status_code` (100–599), `provider_tx_id` (non-empty str), `response_payload` (dict), `duration_ms` (non-negative int).
API CONTRACT: NOT APPLICABLE — internal gateway port interface.
EVENT CONTRACT: NOT APPLICABLE — action events managed by `ActionOutcomeService`.
TEMPORAL CONTRACT: NOT APPLICABLE — saga orchestration managed by `SafeActionSagaWorkflow`.
AGENT CONTRACT: NOT APPLICABLE — agents prohibited from direct gateway provider invocation.
MODEL CONTRACT: NOT APPLICABLE — no AI models invoked in egress gateway.
RAG CONTRACT: NOT APPLICABLE — no retrieval index involved.

## Operational behavior

RETRY: Gateway dispatches are non-retryable at the gateway layer; retries managed by caller saga workflow with idempotency keys.
TIMEOUT: Ephemeral token validation enforces 15-minute expiration; adapter execution bounded by timeout configuration.
IDEMPOTENCY: Idempotency keys recorded in `ActionLedgerRecord` preventing duplicate provider execution.
LOGGING: Cryptographic digests recorded for request and response in ledger journal; raw secrets scrubbed.
METRICS: `revpilot_gateway_dispatches_total{status, provider}`, `revpilot_gateway_duration_seconds`.
FAILURE BEHAVIOR: Fail-closed; any gate check failure aborts pipeline before Gate 7 provider execution.
ROLLBACK/COMPENSATION: NOT APPLICABLE — compensation executed via saga workflow steps.

## Implementation requirements

1. Create `packages/backend/src/revpilot/modules/tool_gateway/ports/provider_adapter.py` exporting `ProviderResponse` and runtime checkable `ProviderAdapterPort` protocol.
2. Update `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py`:
   - Import `ProviderAdapterPort` and `ProviderResponse` from ports.
   - Update `ActionCapabilityGateway.__init__` signature to accept `provider_adapter: ProviderAdapterPort | None = None` and `environment: str | None = None`.
   - In `__init__`, resolve environment via explicit argument or `os.getenv("ENVIRONMENT", "test")`.
   - If `environment != "test"` and (provider_adapter is None or isinstance(provider_adapter, MockProviderAdapter)), raise `GatewayError(code="ERR_MOCK_PROVIDER_FORBIDDEN", message="MockProviderAdapter is strictly forbidden in non-test environment (INV-ACT-001)")`.
   - In Gate 2 (lines 165–173), import and invoke `verify_approval_digest` from `revpilot.modules.approval.digest`. If digest verification fails, return `Failure(GatewayError(code="ERR_APPROVAL_DIGEST_MISMATCH", ...))`.
   - In Gate 7 (lines 236–243), invoke `self.provider_adapter.execute(...)`.
3. Create `tests/unit/test_tool_gateway_provider_adapter.py` with comprehensive unit tests:
   - Verify `ActionCapabilityGateway` constructor accepts `ProviderAdapterPort`.
   - Verify `MockProviderAdapter` in `ENVIRONMENT=production` raises or returns `ERR_MOCK_PROVIDER_FORBIDDEN`.
   - Verify real or dummy `ProviderAdapterPort` implementation succeeds in production environment.
   - Verify `MockProviderAdapter` operates normally in `ENVIRONMENT=test`.
   - Verify Gate 2 rejects invalid approval digest via `verify_approval_digest`.
   - Verify Gate 2 accepts valid approval digest via `verify_approval_digest`.
4. Ensure backward compatibility with existing tests in `tests/contract/test_phase_06_exit_gate.py`.

## Tests and evaluations

TESTS REQUIRED:
- Unit tests in `tests/unit/test_tool_gateway_provider_adapter.py` covering all 6 scenarios above.
- Regression tests in `tests/contract/test_phase_06_exit_gate.py` pass with 0 failures.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Gate 2 verification overhead < 1ms.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/unit/test_tool_gateway_provider_adapter.py -v && python -m pytest tests/contract/test_phase_06_exit_gate.py -q
```

EXPECTED: exit code 0, all unit tests pass, Phase 06 exit gate passes.

## Binary acceptance criteria

- `AC-AR-015-01`: PASS only if configuring or invoking `MockProviderAdapter` when `ENVIRONMENT=production` raises or returns `GatewayError` with code `ERR_MOCK_PROVIDER_FORBIDDEN`.
- `AC-AR-015-02`: PASS only if Gate 2 in `ActionCapabilityGateway.dispatch_action` verifies the approval digest using `verify_approval_digest` and rejects tampered or mismatched digests with `ERR_APPROVAL_DIGEST_MISMATCH`.
- `AC-AR-015-03`: PASS only if `ActionCapabilityGateway.__init__` accepts `provider_adapter: ProviderAdapterPort` and verifies the object satisfies the `ProviderAdapterPort` protocol.

## Postconditions

- `ProviderAdapterPort` is established as the canonical interface for tool gateway execution.
- Mock provider adapter is blocked when environment is not test.
- Cryptographic approval digest verification replaces length check in Gate 2.
- No unexpected files modified.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Concrete objective: introduce port, guard mock in production, wire verify_approval_digest |
| Dependency clarity | 2 | Depends on AR-014, unblocks AR-016 |
| File boundary clarity | 2 | 2 CREATE, 1 MODIFY with exact line targets |
| Contract clarity | 2 | Full protocol and method signatures defined |
| Failure behavior | 2 | Fail-closed with explicit error codes |
| Security/tenancy | 2 | Enforces INV-ACT-001, INV-ACT-002, and fail-closed egress boundaries |
| Testability | 2 | Unit test suite and contract test regression |
| Verification | 2 | Hermetic offline pytest command |
| Acceptance criteria | 2 | 3 machine-verifiable binary criteria |
| Reasoning independence | 2 | Fully specified, no open architectural decisions |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Allow MockProviderAdapter in production environments.
- Retain string length check as approval digest validation.
- Remove secret scrubbing or egress barrier enforcement.

## Required executor report

```text
TASK TASK-AR-015 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: packages/backend/src/revpilot/modules/tool_gateway/ports/provider_adapter.py, tests/unit/test_tool_gateway_provider_adapter.py
FILES MODIFIED: packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py
UNEXPECTED FILES: NONE
TESTS: unit tests PASS, contract regression PASS
COMMANDS AND EXIT CODES: pytest → 0
ACCEPTANCE: AC-AR-015-01: PASS|FAIL, AC-AR-015-02: PASS|FAIL, AC-AR-015-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-016
```
