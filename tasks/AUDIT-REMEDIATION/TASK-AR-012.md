# TASK-AR-012 — Implement Approval State Machine with Atomic Transitions

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 14
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: APPROVAL-ACTION
FEATURE: APPROVAL-STATE-MACHINE
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-011
UNLOCKS: AR-013

## Objective and rationale

OBJECTIVE: Create approval state machine with states PENDING, APPROVED, REJECTED, DISPATCHING, SUCCEEDED, PROVIDER_FAILED, EXPIRED, CANCELLED. Only valid transitions permitted. Every transition records audit event.

BUSINESS RATIONALE: Finding P0-ACT-001 showed approval can go from unknown to APPROVED without state validation. A formal state machine prevents illegal transitions.

ARCHITECTURAL OWNER: Security Architect

ARCHITECTURAL CONTEXT: INV-ACT-001, INV-ACT-003 (zero self-approval).

## Canonical specification references

- `docs/14-iam/IAM-SPEC.md#approval-lifecycle`
- `AGENTS.md#3-strict-prohibitions`

If references conflict, return BLOCKED.

## Preconditions

- AR-011 PASS.

## Change boundary

READ_SET:
- `apps/api/routers/approvals.py`
- `packages/backend/src/revpilot/modules/approval/`

WRITE_SET:
- `packages/backend/src/revpilot/modules/approval/state_machine.py`
- `apps/api/routers/approvals.py`
- `tests/unit/test_approval_state_machine.py`

CREATE:
- `packages/backend/src/revpilot/modules/approval/state_machine.py`
- `tests/unit/test_approval_state_machine.py`

MODIFY:
- `apps/api/routers/approvals.py` — Approve/reject endpoints use state machine.

DO_NOT_MODIFY:
- `packages/backend/src/revpilot/modules/tool_gateway/`
- `apps/api/middleware/`

EXPECTED CHANGE SET: 2 new files, 1 modified.

## Symbol-level contract

MUST EXPORT/DEFINE:

`packages/backend/src/revpilot/modules/approval/state_machine.py`:
```python
class ApprovalState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHING = "DISPATCHING"
    SUCCEEDED = "SUCCEEDED"
    PROVIDER_FAILED = "PROVIDER_FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

VALID_TRANSITIONS: dict[ApprovalState, frozenset[ApprovalState]] = {
    ApprovalState.PENDING: frozenset({ApprovalState.APPROVED, ApprovalState.REJECTED, ApprovalState.EXPIRED, ApprovalState.CANCELLED}),
    ApprovalState.APPROVED: frozenset({ApprovalState.DISPATCHING, ApprovalState.EXPIRED, ApprovalState.CANCELLED}),
    ApprovalState.DISPATCHING: frozenset({ApprovalState.SUCCEEDED, ApprovalState.PROVIDER_FAILED}),
    ApprovalState.REJECTED: frozenset(),
    ApprovalState.SUCCEEDED: frozenset(),
    ApprovalState.PROVIDER_FAILED: frozenset(),
    ApprovalState.EXPIRED: frozenset(),
    ApprovalState.CANCELLED: frozenset(),
}

@dataclass
class TransitionEvent:
    from_state: ApprovalState
    to_state: ApprovalState
    actor: str
    reason: str | None
    timestamp: datetime

def transition(current_state: ApprovalState, new_state: ApprovalState, actor: str, reason: str | None = None) -> Result[TransitionEvent, str]:
    """Attempt state transition. Returns Success(event) or Failure(reason)."""
```

MUST NOT:
- Allow transitions not in VALID_TRANSITIONS.
- Allow transitions from terminal states.

## Input/output and validation

INPUT: Current state, target state, actor, reason.
OUTPUT: TransitionEvent on success, error string on failure.
INVALID INPUT: Invalid transition → Failure.
VALIDATION RULES: new_state must be in VALID_TRANSITIONS[current_state].
STATE TRANSITIONS: See VALID_TRANSITIONS above.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `INVALID_TRANSITION` | State not in allowed set | 409 | no | Invalid state transition | yes | `approval_transition_errors` |

## Security contract

AUTHENTICATION: NOT APPLICABLE — internal module.
AUTHORIZATION: Actor identity recorded.
TENANT: NOT APPLICABLE — state machine is tenant-agnostic.
PII: PROHIBITED.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE — in-memory state machine logic, no schema modifications.
API CONTRACT: NOT APPLICABLE — router endpoints keep existing response schemas with added state validation.
EVENT CONTRACT: NOT APPLICABLE — no external event bus emissions.
TEMPORAL CONTRACT: NOT APPLICABLE — synchronous state transitions without workflow orchestration.
AGENT CONTRACT: NOT APPLICABLE — no agent interaction or prompt changes.
MODEL CONTRACT: NOT APPLICABLE — no AI model calls.
RAG CONTRACT: NOT APPLICABLE — no retrieval augmented generation.

## Operational behavior

RETRY: NOT APPLICABLE.
TIMEOUT: NOT APPLICABLE.
IDEMPOTENCY: Same transition attempt returns same result.
LOGGING: TransitionEvent contains audit data.
METRICS: `approval_transitions{from, to}` counter.
FAILURE BEHAVIOR: Invalid transition returns Failure, does not throw.
ROLLBACK/COMPENSATION: NOT APPLICABLE.

## Implementation requirements

1. Create `packages/backend/src/revpilot/modules/approval/state_machine.py` with ApprovalState, VALID_TRANSITIONS, TransitionEvent, transition().
2. Modify `apps/api/routers/approvals.py` approve endpoint to use `transition(PENDING, APPROVED, ...)`.
3. Modify `apps/api/routers/approvals.py` reject endpoint to use `transition(PENDING, REJECTED, ...)`.
4. Create 8 unit tests in `tests/unit/test_approval_state_machine.py`:
   - PENDING → APPROVED succeeds
   - PENDING → REJECTED succeeds
   - APPROVED → DISPATCHING succeeds
   - APPROVED → APPROVED fails (invalid)
   - SUCCEEDED → CANCELLED fails (terminal)
   - DISPATCHING → SUCCEEDED succeeds
   - DISPATCHING → PROVIDER_FAILED succeeds
   - TransitionEvent records actor and timestamp

## Tests and evaluations

TESTS REQUIRED:
- 8 unit tests in `tests/unit/test_approval_state_machine.py` covering all transition matrix conditions.
- Full regression suite: `python -m pytest tests/ -q`

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/unit/test_approval_state_machine.py -v && python -m pytest tests/ -q
```

EXPECTED: exit code 0.

## Binary acceptance criteria

- `AC-AR-012-01`: PASS only if `transition(PENDING, APPROVED)` succeeds.
- `AC-AR-012-02`: PASS only if `transition(APPROVED, APPROVED)` fails.
- `AC-AR-012-03`: PASS only if `transition(SUCCEEDED, CANCELLED)` fails.
- `AC-AR-012-04`: PASS only if every transition records (actor, from_state, to_state, timestamp).

## Postconditions

- State machine module exists.
- Approve/reject routes use state machine.
- 8 unit tests pass.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | State machine with exact transitions |
| Dependency clarity | 2 | AR-011 |
| File boundary clarity | 2 | 2 CREATE, 1 MODIFY |
| Contract clarity | 2 | Exact enum and transition map |
| Failure behavior | 2 | Invalid transition → Failure |
| Security/tenancy | 2 | Actor recorded |
| Testability | 2 | 8 tests specified |
| Verification | 2 | pytest, exit 0 |
| Acceptance criteria | 2 | 4 machine-verifiable |
| Reasoning independence | 2 | No architectural decisions |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Allow undefined transitions.
- Allow transitions from terminal states.
- Skip audit recording.
- Modify files outside WRITE_SET.

## Required executor report

```text
TASK TASK-AR-012 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: packages/backend/src/revpilot/modules/approval/state_machine.py, tests/unit/test_approval_state_machine.py
FILES MODIFIED: apps/api/routers/approvals.py
UNEXPECTED FILES: NONE
TESTS: 8 state machine tests PASS, full suite PASS
COMMANDS AND EXIT CODES: pytest unit → 0, pytest full → 0
ACCEPTANCE: AC-AR-012-01: PASS|FAIL, AC-AR-012-02: PASS|FAIL, AC-AR-012-03: PASS|FAIL, AC-AR-012-04: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-013
```
