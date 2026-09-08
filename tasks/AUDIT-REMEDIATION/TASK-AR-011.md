# TASK-AR-011 — Implement Canonical Approval Digest with Stable JSON Serialization

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 14
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: APPROVAL-ACTION
FEATURE: CANONICAL-DIGEST
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-001, AR-005
UNLOCKS: AR-012

## Objective and rationale

OBJECTIVE: Replace `sha256(str(payload.payload))` in `apps/api/routers/approvals.py` with canonical JSON digest including 8 fields: tenant_id, action_type, target_entities, payload, policy_version, required_tier, expires_at, created_by.

BUSINESS RATIONALE: Finding P0-ACT-001 proved approval digest uses `str(dict)` which is non-deterministic (key order varies). A canonical digest prevents payload tampering between create and approve/dispatch.

ARCHITECTURAL OWNER: Security Architect
ARCHITECTURAL CONTEXT: INV-ACT-001 (zero unauthorized mutations), INV-ACT-002 (approval digest), AC-008.

## Canonical specification references
- `docs/14-iam/IAM-SPEC.md#approval-digest`
- `AGENTS.md#3-strict-prohibitions`

If references conflict, return BLOCKED.

## Preconditions
- AR-001 PASS, AR-005 PASS.
- `apps/api/routers/approvals.py` exists.

## Change boundary

READ_SET:
- `apps/api/routers/approvals.py` (full)
- `packages/backend/src/revpilot/modules/tool_gateway/action/gateway.py` (digest usage)

WRITE_SET:
- `packages/backend/src/revpilot/modules/approval/digest.py`
- `apps/api/routers/approvals.py`
- `tests/unit/test_approval_digest.py`

CREATE:
- `packages/backend/src/revpilot/modules/approval/__init__.py`
- `packages/backend/src/revpilot/modules/approval/digest.py`
- `tests/unit/test_approval_digest.py`

MODIFY:
- `apps/api/routers/approvals.py` — Replace str-based digest with canonical digest.

DO_NOT_MODIFY:
- `packages/backend/src/revpilot/modules/tool_gateway/`
- `apps/api/middleware/`

EXPECTED CHANGE SET: 2 new module files, 1 test file, 1 modified router.

## Symbol-level contract

MUST EXPORT/DEFINE:

`packages/backend/src/revpilot/modules/approval/digest.py`:
```python
@dataclass(frozen=True)
class ApprovalArtifact:
    tenant_id: str
    action_type: str
    target_entities: list[str]
    payload: dict
    policy_version: str
    required_tier: str
    expires_at: str  # ISO 8601
    created_by: str

def compute_approval_digest(artifact: ApprovalArtifact) -> str:
    """Canonical JSON: keys sorted recursively, no whitespace, UTF-8, SHA-256 hex."""
    ...

def verify_approval_digest(artifact: ApprovalArtifact, expected_digest: str) -> bool:
    """Constant-time comparison using hmac.compare_digest."""
    ...
```

MUST NOT: Use `str(dict)` or `repr()`. Use non-deterministic serialization. Skip any of the 8 fields.

## Input/output and validation

INPUT: ApprovalArtifact with 8 fields.
OUTPUT: 64-char hex SHA-256 digest.
INVALID INPUT: Missing fields → ValueError.
VALIDATION RULES: Deterministic — same input always same output. Any field change → different digest.
STATE TRANSITIONS: NOT APPLICABLE.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `DIGEST_FIELD_MISSING` | ApprovalArtifact missing required field | ValueError | no | Internal digest error | yes | N/A |

## Security contract

AUTHENTICATION: NOT APPLICABLE — internal module.
AUTHORIZATION: NOT APPLICABLE.
TENANT: tenant_id included in digest.
PII: PROHIBITED.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE.
API CONTRACT: NOT APPLICABLE — internal function.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: NOT APPLICABLE.
TIMEOUT: NOT APPLICABLE.
IDEMPOTENCY: Deterministic function.
LOGGING: NOT APPLICABLE.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: Missing field → raise ValueError.
ROLLBACK/COMPENSATION: NOT APPLICABLE.

## Implementation requirements

1. Create `packages/backend/src/revpilot/modules/approval/__init__.py` (empty).
2. Create `digest.py` with `ApprovalArtifact`, `compute_approval_digest`, `verify_approval_digest`.
3. Canonical JSON: `json.dumps(asdict(artifact), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')` → SHA-256 hex.
4. `verify_approval_digest` uses `hmac.compare_digest(computed, expected)`.
5. Modify `apps/api/routers/approvals.py` POST endpoint to use `compute_approval_digest`.
6. Create `tests/unit/test_approval_digest.py` with 6 tests:
   - Deterministic: same input → same digest.
   - Changed field → different digest.
   - All 8 fields included (remove each → different digest).
   - Constant-time compare.
   - Empty payload dict works.
   - Unicode payload works.

## Tests and evaluations

TESTS REQUIRED: 6 unit tests.
AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:
```text
python -m pytest tests/unit/test_approval_digest.py -v && python -m pytest tests/ -q
```
EXPECTED: exit code 0.

## Binary acceptance criteria

- `AC-AR-011-01`: PASS only if same input to `compute_approval_digest` always produces same output.
- `AC-AR-011-02`: PASS only if changing any field produces different digest.
- `AC-AR-011-03`: PASS only if `verify_approval_digest` uses `hmac.compare_digest`.
- `AC-AR-011-04`: PASS only if digest includes all 8 fields.

## Postconditions
- Approval module with digest functions exists.
- Router uses canonical digest.
- 6 unit tests pass.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Single module + router update |
| Dependency clarity | 2 | AR-001, AR-005 |
| File boundary clarity | 2 | 3 CREATE, 1 MODIFY |
| Contract clarity | 2 | Exact dataclass and functions |
| Failure behavior | 2 | Missing field → ValueError |
| Security/tenancy | 2 | Tamper detection |
| Testability | 2 | 6 unit tests specified |
| Verification | 2 | pytest, exit 0 |
| Acceptance criteria | 2 | 4 machine-verifiable |
| Reasoning independence | 2 | No architectural decisions |

## Definition of done
All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass.

## Do not
- Use `str(dict)` or non-deterministic serialization.
- Skip any of the 8 fields.
- Modify gateway code.

## Required executor report
```text
TASK TASK-AR-011 RESULT
STATUS: PASS | FAIL | BLOCKED
FILES CREATED: approval/__init__.py, approval/digest.py, test_approval_digest.py
FILES MODIFIED: apps/api/routers/approvals.py
UNEXPECTED FILES: NONE
TESTS: 6 digest tests PASS, full suite PASS
COMMANDS AND EXIT CODES: pytest → 0
ACCEPTANCE: AC-AR-011-01..04: PASS|FAIL
DEVIATIONS: NONE
NEXT TASK: AR-012
```
