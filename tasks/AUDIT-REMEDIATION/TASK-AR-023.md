# TASK-AR-023 — Webhook Signature HMAC Verification — Raw Bytes, Constant-Time Compare

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 16
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: SECURITY-HARDENING
FEATURE: WEBHOOK-HMAC
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-024
DEPENDS_ON: AR-005
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Remove hardcoded fallback secret `whsec_default_secret_2026` from `apps/api/routers/connectors.py`. Enforce HMAC-SHA256 verification using raw request payload bytes and `hmac.compare_digest`. Enforce anti-replay defenses via event ID deduplication (HTTP 409) and timestamp window skew tolerance (HTTP 401).

BUSINESS RATIONALE: Audit finding P1-SEC-003 revealed that `apps/api/routers/connectors.py` fell back to a static testing secret (`whsec_default_secret_2026`) when `WEBHOOK_SIGNING_SECRET` was absent in test/dev modes. Such hardcoded secrets in production codebases risk accidental deployment or credential bypass. Additionally, duplicate webhook deliveries must fail with 409 Conflict rather than proceeding to execution, and timestamp skew outside the 300s window must fail closed with 401 Unauthorized to protect against replay attacks.

ARCHITECTURAL OWNER: Security Architect

ARCHITECTURAL CONTEXT: INV-SEC-001 (cryptographic verification at untrusted boundaries), INV-REL-001 (anti-replay and idempotent ingestion), `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §4, `docs/26-api/API-STANDARDS.md` §10.7.

## Canonical specification references

- `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md#4-inbound-webhook-ingestion`
- `docs/26-api/API-STANDARDS.md#107-webhook-signature-verification`
- `packages/backend/src/revpilot/modules/connectors/ingestion/webhook.py`
- `AGENTS.md#3-strict-prohibitions`

If references conflict, return BLOCKED.

## Preconditions

- AR-005 PASS (authentication adapter fail-closed in place).
- `apps/api/routers/connectors.py` exists with `receive_webhook` endpoint.
- `packages/backend/src/revpilot/modules/connectors/ingestion/webhook.py` contains `WebhookVerifier`, `InvalidWebhookSignatureError`, and `TimestampSkewError`.

## Change boundary

READ_SET:
- `apps/api/routers/connectors.py` (full file)
- `packages/backend/src/revpilot/modules/connectors/ingestion/webhook.py` (full file)
- `tests/integration/` (test patterns)

WRITE_SET:
- `apps/api/routers/connectors.py`
- `tests/integration/test_webhook_signature.py`

CREATE:
- `tests/integration/test_webhook_signature.py`

MODIFY:
- `apps/api/routers/connectors.py` — lines 93-154:
  - Eliminate fallback string `whsec_default_secret_2026`. If `WEBHOOK_SIGNING_SECRET` is unset, return HTTP 500 `CONFIG_ERROR`.
  - Ensure verification uses raw request body bytes with `hmac.compare_digest`.
  - Map `TimestampSkewError` to HTTP 401 Unauthorized (`TIMESTAMP_SKEW`).
  - When `inbox.ingest_webhook_event` returns `is_duplicate=True` or a duplicate event ID is detected, raise HTTP 409 Conflict (`DUPLICATE_WEBHOOK_EVENT`).

DO_NOT_MODIFY:
- `apps/api/main.py`
- `apps/api/middleware/*`
- `packages/backend/src/revpilot/modules/identity/*`
- Any file outside WRITE_SET

EXPECTED CHANGE SET:
- 1 modified router file removing fallback secret and adding anti-replay duplicate handling.
- 1 new integration test file with 6 test cases.

## Symbol-level contract

MUST EXPORT/DEFINE:
- `apps/api/routers/connectors.py`:
  - `receive_webhook(connector_id, request, x_signature, x_timestamp, x_event_id, tenant)`:
    - Verifies raw bytes against HMAC signature using constant-time comparison (`hmac.compare_digest`).
    - Unset `WEBHOOK_SIGNING_SECRET` → HTTP 500 (`CONFIG_ERROR`). Zero fallback secret literals.
    - Missing `X-Signature-SHA256` → HTTP 401 (`MISSING_WEBHOOK_SIGNATURE`).
    - Tampered payload body or forged signature → HTTP 401 (`INVALID_SIGNATURE`).
    - Timestamp skew > 300s (5 min) → HTTP 401 (`TIMESTAMP_SKEW`).
    - Replayed / duplicate event ID → HTTP 409 (`DUPLICATE_WEBHOOK_EVENT`).
    - Valid fresh request → HTTP 202 (`ACCEPTED`).
- `tests/integration/test_webhook_signature.py`:
  - `test_valid_signature_returns_202()`: Correct HMAC signature + valid timestamp returns HTTP 202.
  - `test_tampered_body_returns_401()`: Payload modified after signing returns HTTP 401.
  - `test_wrong_secret_returns_401()`: Payload signed with incorrect secret returns HTTP 401.
  - `test_missing_signature_returns_401()`: Request without X-Signature-SHA256 header returns HTTP 401.
  - `test_replay_duplicate_event_returns_409()`: Second webhook request with identical event ID returns HTTP 409.
  - `test_timestamp_skew_exceeding_window_returns_401()`: Webhook timestamp skewed > 300s into past/future returns HTTP 401.

MUST NOT:
- Contain `whsec_default_secret_2026` or any fallback signing secret string.
- Compare HMAC signatures using non-constant-time operators (`==` or `!=`).
- Accept replayed duplicate event IDs as fresh events.

## Input/output and validation

INPUT: HTTP POST to `/api/v1/connectors/{connector_id}/webhooks` with headers:
- `X-Signature-SHA256`: Hexadecimal HMAC-SHA256 string (optional `sha256=` prefix allowed).
- `X-Timestamp`: Unix epoch seconds string.
- `X-Event-ID`: Unique event identifier string.
- Body: Raw JSON bytes.
OUTPUT: JSON response:
- Success: HTTP 202 `{"status": "ACCEPTED", "inbox_id": "...", "is_duplicate": false}`.
- Duplicate: HTTP 409 `{"detail": {"code": "DUPLICATE_WEBHOOK_EVENT", "message": "..."}}`.
- Error: HTTP 401 `{"detail": {"code": "...", "message": "..."}}`.
INVALID INPUT: Missing signature → 401; mismatched signature → 401; timestamp skew > 300s → 401; duplicate event ID → 409.
VALIDATION RULES: Signature computed strictly over `t={timestamp}.{raw_body}` using HMAC-SHA256.
STATE TRANSITIONS: Ingestion into connector inbox table/state; transition to DUPLICATE on replay.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `MISSING_WEBHOOK_SIGNATURE` | Missing X-Signature-SHA256 header | 401 | no | Missing required X-Signature-SHA256 header | yes | `webhook_verify_failures_total{reason="missing_sig"}` |
| `INVALID_SIGNATURE` | HMAC verification mismatch or tampered body | 401 | no | Invalid webhook signature | yes | `webhook_verify_failures_total{reason="bad_sig"}` |
| `TIMESTAMP_SKEW` | Timestamp skew > 300 seconds | 401 | no | Webhook timestamp out of bounds | yes | `webhook_verify_failures_total{reason="skew"}` |
| `DUPLICATE_WEBHOOK_EVENT` | Replayed duplicate event ID | 409 | no | Webhook event has already been processed | yes | `webhook_duplicates_total` |
| `EMPTY_PAYLOAD` | Request body length is 0 | 400 | no | Webhook request body cannot be empty | no | `webhook_verify_failures_total{reason="empty"}` |
| `CONFIG_ERROR` | WEBHOOK_SIGNING_SECRET not configured | 500 | no | WEBHOOK_SIGNING_SECRET is not configured | yes | `webhook_config_errors_total` |

## Security contract

AUTHENTICATION: Cryptographic HMAC-SHA256 over raw request payload and timestamp header.
AUTHORIZATION: Connector tenant scope verified via tenant context binding.
TENANT: Ingested events strictly scoped to connector tenant.
PII: PROHIBITED — raw bodies in audit logs must be hashed/redacted.
SECRET ACCESS: `WEBHOOK_SIGNING_SECRET` read strictly from environment or secure vault.
EXTERNAL ACTION: PROHIBITED during signature verification phase.
DEFAULT: DENY — missing secret, missing signature, mismatched digest, or stale timestamp must fail closed.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE.
API CONTRACT: Conforms to `docs/26-api/API-STANDARDS.md` §10.7 for inbound webhook signatures.
EVENT CONTRACT: Anti-replay idempotent inbox ingestion adhering to `CONNECTOR-PLATFORM-SPEC.md` §4.
TEMPORAL CONTRACT: Maximum timestamp skew tolerance window: 300 seconds (5 minutes).
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: Upstream webhook providers retry on 5xx; 401/409 are terminal non-retryable responses.
TIMEOUT: Signature evaluation < 10ms.
IDEMPOTENCY: Replay of identical event ID returns HTTP 409 Conflict.
LOGGING: Log security verification rejections with client IP and connector ID (never log secret or raw secret).
METRICS: Increment `webhook_verify_failures_total` and `webhook_duplicates_total`.
FAILURE BEHAVIOR: Fail closed on all validation errors (401/409/500).
ROLLBACK/COMPENSATION: Revert changes to `apps/api/routers/connectors.py` and delete test file.

## Implementation requirements

1. Open `apps/api/routers/connectors.py`.
2. Delete lines 96-99 referencing `whsec_default_secret_2026` and `is_test_env` fallback logic.
3. Require `os.getenv("WEBHOOK_SIGNING_SECRET")` directly; if empty or None, raise `HTTPException(status_code=500, detail={"code": "CONFIG_ERROR", "message": "WEBHOOK_SIGNING_SECRET is not configured"})`.
4. Ensure verification utilizes raw bytes and `hmac.compare_digest`.
5. Update exception handling for `TimestampSkewError` to return HTTP 401 Unauthorized (`TIMESTAMP_SKEW`).
6. In `receive_webhook`, verify `is_duplicate` status returned from inbox ingestion. If `is_duplicate` is True, raise `HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "DUPLICATE_WEBHOOK_EVENT", "message": "Webhook event has already been processed"})`.
7. Create `tests/integration/test_webhook_signature.py` containing 6 test cases verifying:
   - Valid signature → 202 Accepted.
   - Tampered payload body → 401 Unauthorized.
   - Wrong signing secret → 401 Unauthorized.
   - Missing signature header → 401 Unauthorized.
   - Duplicate event ID replay → 409 Conflict.
   - Timestamp skew > 300 seconds → 401 Unauthorized.
8. Execute verification commands and ensure 0 regression across entire test suite.

## Tests and evaluations

TESTS REQUIRED:
- 6 integration test cases in `tests/integration/test_webhook_signature.py`.
- Regression check: `pytest tests/ -q` exits 0.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Constant-time signature comparison execution < 1ms.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
grep -rn "whsec_default_secret" apps/ || true && python -m pytest tests/integration/test_webhook_signature.py -v && python -m pytest tests/ -q
```

EXPECTED:
- `grep` outputs 0 matches.
- `pytest tests/integration/test_webhook_signature.py` exits 0 with 6 passed.
- Full pytest suite exits 0.

## Binary acceptance criteria

- `AC-AR-023-01`: PASS only if `grep -rn "whsec_default_secret" apps/` returns 0 matches and exit code is non-zero (empty match).
- `AC-AR-023-02`: PASS only if a webhook request with a tampered body or invalid signature returns HTTP 401.
- `AC-AR-023-03`: PASS only if `python -m pytest tests/integration/test_webhook_signature.py` executes 6 tests and all 6 pass with exit code 0.

## Postconditions

- `whsec_default_secret_2026` completely removed from application code.
- Inbound webhooks enforce constant-time HMAC verification over raw bytes.
- Duplicate webhook submissions return HTTP 409 Conflict.
- Skewed timestamps (>300s) return HTTP 401 Unauthorized.
- Test suite passing with 6 dedicated test cases.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Clear objective: eliminate fallback secret, enforce raw bytes HMAC, anti-replay |
| Dependency clarity | 2 | Clear dependency: AR-005 |
| File boundary clarity | 2 | Exact lines in connectors.py and 1 new test file |
| Contract clarity | 2 | Precise HTTP status codes (202, 401, 409, 500) and headers defined |
| Failure behavior | 2 | Fail closed: 401 for bad sig/skew, 409 for duplicate, 500 for missing secret |
| Security/tenancy | 2 | Eliminates hardcoded credential vulnerability and prevents replay |
| Testability | 2 | 6 concrete integration test scenarios specified |
| Verification | 2 | Offline hermetic grep and pytest verification commands |
| Acceptance criteria | 2 | 3 binary machine-verifiable criteria |
| Reasoning independence | 2 | No architectural decisions required; pure remediation implementation |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Retain any default or fallback secret literal for development or testing.
- Use standard string equality (`==`) to compare HMAC digests.
- Allow replayed webhooks with identical event IDs to pass as 202 Accepted.
- Modify files outside the explicit WRITE_SET.

## Required executor report

```text
TASK TASK-AR-023 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_webhook_signature.py
FILES MODIFIED: apps/api/routers/connectors.py
UNEXPECTED FILES: NONE
TESTS: 6 webhook verification tests PASS, full suite PASS
COMMANDS AND EXIT CODES: grep → 0 matches, pytest webhook tests → 0, pytest full → 0
ACCEPTANCE: AC-AR-023-01: PASS|FAIL, AC-AR-023-02: PASS|FAIL, AC-AR-023-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-024
```
