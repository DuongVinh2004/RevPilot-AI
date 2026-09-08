# TASK-AR-004 — Enforce Startup Dependency Contract — Fail-Closed on Missing Required Services

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 3
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IDENTITY-BOUNDARY
FEATURE: STARTUP-FAILCLOSED
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-001, AR-002
UNLOCKS: AR-005

## Objective and rationale

OBJECTIVE: Modify `apps/api/main.py` lifespan so that `DATABASE_URL` is required when `ENVIRONMENT != "test"`. If missing or pool init fails, process exits with code 1 instead of continuing startup.

BUSINESS RATIONALE: Finding P0-SEC-001 proved that when DATABASE_URL is missing or pool init fails, the API gateway continues startup with pool=None, causing auth adapter to be None, which opens the authentication fail-open path. Fail-closed startup prevents this entire failure cascade.

ARCHITECTURAL OWNER: Platform Architect

ARCHITECTURAL CONTEXT: INV-SEC-001 (boundary verification), INV-TEN-001 (server-derived context), ADR-0003 (hexagonal architecture — external adapter failures must not degrade security invariants).

## Canonical specification references

- `docs/14-iam/IAM-SPEC.md#authentication-boundary`
- `AGENTS.md#1-core-operating-directives` (fail-closed principle)
- `execution/DEFINITION-OF-DONE.md#stage-b-implementation-complete`

If references conflict, return BLOCKED.

## Preconditions

- AR-001 PASS (governance docs relabeled, so references are consistent).
- AR-002 PASS (audit baseline exists for provenance).
- `apps/api/main.py` exists with lifespan function.
- Current lifespan catches all exceptions during pool init and continues.

## Change boundary

READ_SET:
- `apps/api/main.py` (full file)
- `apps/api/middleware/authentication.py` (to understand downstream impact)
- `pyproject.toml` (to verify no conflicting startup hooks)

WRITE_SET:
- `apps/api/main.py`

CREATE:
- `tests/integration/test_startup_failclosed.py`

MODIFY:
- `apps/api/main.py` — Lines 55-64: Replace permissive startup with fail-closed contract.

DO_NOT_MODIFY:
- `apps/api/middleware/authentication.py`
- `apps/api/routers/*`
- `packages/*`
- Any file outside WRITE_SET and CREATE

EXPECTED CHANGE SET:
- `apps/api/main.py`: Lines 55-64 modified to add ENVIRONMENT check and SystemExit on failure.
- `tests/integration/test_startup_failclosed.py`: New file with 4 test cases.

## Symbol-level contract

MUST EXPORT/DEFINE:
- Modified `lifespan(app)` async context manager in `apps/api/main.py`:
  - Read `ENVIRONMENT` from `os.getenv("ENVIRONMENT", "production")`.
  - If `ENVIRONMENT` not in `{"production", "staging", "test"}`: `raise SystemExit("Unknown ENVIRONMENT value")`.
  - If `ENVIRONMENT != "test"` and `DATABASE_URL` is None/empty: `raise SystemExit("DATABASE_URL is required for non-test environments")`.
  - If `ENVIRONMENT != "test"` and `create_database_pool()` raises: `raise SystemExit(f"Database initialization failed: {exc}")` (do not catch silently).
  - If `ENVIRONMENT == "test"`: skip database pool init, proceed with in-memory adapters.

MUST NOT:
- Catch and swallow database init exceptions in production/staging.
- Allow startup to succeed with pool=None in production/staging.
- Change test behavior (tests must still pass without DATABASE_URL).

## Input/output and validation

INPUT: Environment variables `ENVIRONMENT`, `DATABASE_URL`.
OUTPUT: Process startup success or SystemExit.
INVALID INPUT: `ENVIRONMENT` not in allowed set → SystemExit. Missing `DATABASE_URL` in production → SystemExit.
VALIDATION RULES: `ENVIRONMENT` must be one of `production`, `staging`, `test`. `DATABASE_URL` must be non-empty string when required.
STATE TRANSITIONS: NOT APPLICABLE — startup is one-shot.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `STARTUP_FAILED` | DATABASE_URL missing in production | SystemExit(1) | no | Process does not start | yes (stderr) | N/A |
| `STARTUP_FAILED` | Database pool init exception | SystemExit(1) | no | Process does not start | yes (stderr) | N/A |
| `STARTUP_FAILED` | Unknown ENVIRONMENT value | SystemExit(1) | no | Process does not start | yes (stderr) | N/A |

## Security contract

AUTHENTICATION: This task prevents auth bypass by ensuring auth adapter is always initialized in production.
AUTHORIZATION: NOT APPLICABLE at startup level.
TENANT: Ensures tenant context infrastructure (database) is always available.
PII: PROHIBITED.
SECRET ACCESS: DATABASE_URL is a secret — must not be logged in full.
EXTERNAL ACTION: Database connection attempt during startup.
DEFAULT: DENY — unknown environment or missing dependency = fail.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE.
API CONTRACT: NOT APPLICABLE — startup behavior, not API endpoint.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: Container orchestrator (ECS/K8s) handles restart on exit code 1.
TIMEOUT: Database connection timeout from pool config (default 30s).
IDEMPOTENCY: Startup is idempotent — same env vars produce same result.
LOGGING: Log `"FATAL: DATABASE_URL is required"` at CRITICAL level. Do NOT log the actual DATABASE_URL value.
METRICS: NOT APPLICABLE at startup.
FAILURE BEHAVIOR: Any required dependency failure → SystemExit(1). Container orchestrator restarts.
ROLLBACK/COMPENSATION: Revert `apps/api/main.py` to previous version.

## Implementation requirements

1. Read `apps/api/main.py` completely.
2. Modify `lifespan()` function (lines 50-64):
   ```python
   env = os.getenv("ENVIRONMENT", "production")
   if env not in ("production", "staging", "test"):
       raise SystemExit(f"Unknown ENVIRONMENT value: {env!r}")
   
   db_url = os.getenv("DATABASE_URL")
   pool = None
   
   if env == "test":
       logger.info("Test environment: skipping database pool initialization")
   else:
       if not db_url:
           raise SystemExit("FATAL: DATABASE_URL is required for non-test environments")
       try:
           from revpilot.infrastructure.database import create_database_pool
           pool = await create_database_pool(db_url, min_size=2, max_size=10)
           app.state.db_pool = pool
           logger.info("Database pool initialized successfully")
       except Exception as exc:
           raise SystemExit(f"FATAL: Database initialization failed: {exc}") from exc
   ```
3. Create `tests/integration/test_startup_failclosed.py` with 4 test cases:
   - `test_startup_fails_without_database_url_in_production`: Set ENVIRONMENT=production, no DATABASE_URL → assert SystemExit.
   - `test_startup_fails_with_invalid_database_url`: Set ENVIRONMENT=production, DATABASE_URL=invalid → assert SystemExit.
   - `test_startup_succeeds_in_test_without_database_url`: Set ENVIRONMENT=test → no SystemExit.
   - `test_startup_fails_with_unknown_environment`: Set ENVIRONMENT=unknown → assert SystemExit.
4. Verify existing test suite still passes with `python -m pytest tests/ -q`.

## Tests and evaluations

TESTS REQUIRED:
- 4 positive/negative test cases in `tests/integration/test_startup_failclosed.py`.
- Full regression: `python -m pytest tests/ -q` exit 0.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Startup failure must occur within 5 seconds.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -m pytest tests/integration/test_startup_failclosed.py -v && python -m pytest tests/ -q
```

EXPECTED: exit code 0, all tests pass.

## Binary acceptance criteria

- `AC-AR-004-01`: PASS only if process with `ENVIRONMENT=production` and no `DATABASE_URL` exits with non-zero code within 5 seconds.
- `AC-AR-004-02`: PASS only if process with `ENVIRONMENT=production` and `DATABASE_URL=invalid://` exits with non-zero code.
- `AC-AR-004-03`: PASS only if process with `ENVIRONMENT=test` and no `DATABASE_URL` starts successfully.
- `AC-AR-004-04`: PASS only if `python -m pytest tests/ -q` exits 0 (no regression).

## Postconditions

- `apps/api/main.py` lifespan fails closed on missing/invalid DATABASE_URL.
- `tests/integration/test_startup_failclosed.py` exists with 4 passing tests.
- Full test suite passes.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Single function modification with exact behavior |
| Dependency clarity | 2 | AR-001, AR-002 are documentation-only prerequisites |
| File boundary clarity | 2 | 1 MODIFY, 1 CREATE, exact paths |
| Contract clarity | 2 | Exact code change specified |
| Failure behavior | 2 | SystemExit on every failure path |
| Security/tenancy | 2 | Prevents auth cascade failure |
| Testability | 2 | 4 test cases with clear assertions |
| Verification | 2 | pytest command, exit 0 |
| Acceptance criteria | 2 | 4 machine-verifiable criteria |
| Reasoning independence | 2 | No architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Catch and swallow database init exceptions.
- Log DATABASE_URL value.
- Modify authentication middleware.

## Required executor report

```text
TASK TASK-AR-004 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: tests/integration/test_startup_failclosed.py
FILES MODIFIED: apps/api/main.py
UNEXPECTED FILES: NONE
TESTS: 4 startup tests PASS, full suite PASS
COMMANDS AND EXIT CODES: pytest tests/integration/test_startup_failclosed.py -v → 0, pytest tests/ -q → 0
ACCEPTANCE: AC-AR-004-01: PASS|FAIL, AC-AR-004-02: PASS|FAIL, AC-AR-004-03: PASS|FAIL, AC-AR-004-04: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-005
```
