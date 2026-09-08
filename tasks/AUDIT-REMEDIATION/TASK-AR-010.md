# TASK-AR-010 — Frontend Dev Auth Guard — No Dev Headers or Default Tokens in Production Build

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 3
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IDENTITY-BOUNDARY
FEATURE: FRONTEND-DEV-GUARD
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-006, AR-007
DEPENDS_ON: AR-005
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Remove default dev token fallback from `apps/web/src/auth/token.ts` line 11 and add double guard for dev headers. Verify production build bundle does not contain dev tokens or dev header strings.

BUSINESS RATIONALE: Finding P1-FE-001 proved that `AuthManager.getToken()` returns `'dev_token_usr_admin_001_tnt_dev_001'` when localStorage is empty, and `getHeaders()` sends `X-Dev-Principal`/`X-Dev-Tenant` headers in dev mode. These must not appear in production builds.

ARCHITECTURAL OWNER: Frontend Lead

ARCHITECTURAL CONTEXT: INV-IAM-001 (boundary verification), INV-SEC-001 (no default credentials in production).

## Canonical specification references

- `docs/14-iam/IAM-SPEC.md#frontend-authentication`
- `docs/26-api/API-STANDARDS.md` (header standards)

If references conflict, return BLOCKED.

## Preconditions

- AR-005 PASS (backend auth fail-closed).
- `apps/web/src/auth/token.ts` exists.
- `npm run build` works from `apps/web/`.

## Change boundary

READ_SET:
- `apps/web/src/auth/token.ts` (full file, 41 lines)
- `apps/web/vite.config.ts`
- `apps/web/package.json`

WRITE_SET:
- `apps/web/src/auth/token.ts`

CREATE: NONE

MODIFY:
- `apps/web/src/auth/token.ts`:
  - Line 11: `getToken()` — Remove `|| 'dev_token_usr_admin_001_tnt_dev_001'` fallback. Return `localStorage.getItem(this.tokenKey)` which returns `null` when empty.
  - Lines 30-33: `getHeaders()` — Change condition from `if ((import.meta as any).env?.DEV)` to `if ((import.meta as any).env?.DEV && (import.meta as any).env?.VITE_ALLOW_DEV_AUTH === 'true')`. Double guard requires explicit opt-in.

DO_NOT_MODIFY:
- `apps/web/vite.config.ts` (no build config changes needed)
- `apps/api/*` (backend changes in AR-005)
- Other frontend source files

EXPECTED CHANGE SET: 2 line changes in token.ts.

## Symbol-level contract

MUST EXPORT/DEFINE:

Modified `AuthManager` class in `apps/web/src/auth/token.ts`:
```typescript
static getToken(): string | null {
    return localStorage.getItem(this.tokenKey);  // No fallback
}

static getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    };
    if ((import.meta as any).env?.DEV && (import.meta as any).env?.VITE_ALLOW_DEV_AUTH === 'true') {
        headers['X-Dev-Principal'] = this.getDevPrincipal();
        headers['X-Dev-Tenant'] = this.getDevTenant();
    }
    const token = this.getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}
```

MUST NOT:
- Add any default token or credential.
- Remove the dev auth capability entirely (still needed for local development with explicit opt-in).
- Change TypeScript types or exports.

## Input/output and validation

INPUT: localStorage state, Vite environment variables.
OUTPUT: Headers object with or without dev headers.
INVALID INPUT: NOT APPLICABLE.
VALIDATION RULES: Production build must tree-shake dev-only code paths. Dev headers only appear with double opt-in.
STATE TRANSITIONS: NOT APPLICABLE.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| NOT APPLICABLE | Frontend code change | N/A | N/A | N/A | N/A | N/A |

## Security contract

AUTHENTICATION: Removes default credentials from production.
AUTHORIZATION: NOT APPLICABLE.
TENANT: Removes default tenant from production.
PII: PROHIBITED.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY — no token = no auth header sent.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE.
API CONTRACT: NOT APPLICABLE.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: NOT APPLICABLE.
TIMEOUT: NOT APPLICABLE.
IDEMPOTENCY: NOT APPLICABLE.
LOGGING: NOT APPLICABLE.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: NOT APPLICABLE.
ROLLBACK/COMPENSATION: Revert token.ts.

## Implementation requirements

1. Read `apps/web/src/auth/token.ts`.
2. Line 11: Remove `|| 'dev_token_usr_admin_001_tnt_dev_001'` so `getToken()` returns `null` when localStorage empty.
3. Lines 30-33: Add `&& (import.meta as any).env?.VITE_ALLOW_DEV_AUTH === 'true'` condition.
4. Run `npm run build --prefix apps/web` to verify TypeScript compilation.
5. Grep production bundle for forbidden strings.

## Tests and evaluations

TESTS REQUIRED:
- Build succeeds: `npm run build --prefix apps/web` exit 0.
- Production bundle grep: No `dev_token_usr_admin_001`, `X-Dev-Principal`, `X-Dev-Tenant` in `apps/web/dist/`.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
npm run build --prefix apps/web && python -c "
import pathlib, sys
dist = pathlib.Path('apps/web/dist')
forbidden = ['dev_token_usr_admin_001', 'X-Dev-Principal', 'X-Dev-Tenant']
fail = False
for f in dist.rglob('*.js'):
    text = f.read_text(encoding='utf-8', errors='ignore')
    for s in forbidden:
        if s in text:
            print(f'FAIL: {f.name} contains {s!r}')
            fail = True
if fail:
    sys.exit(1)
print('PASS: No dev tokens or headers in production bundle')
"
```

EXPECTED: exit code 0, build succeeds, no forbidden strings in bundle.

## Binary acceptance criteria

- `AC-AR-010-01`: PASS only if `npm run build --prefix apps/web` output bundle (dist/) does not contain string `dev_token_usr_admin_001` or `X-Dev-Principal` or `X-Dev-Tenant`.
- `AC-AR-010-02`: PASS only if `getToken()` returns `null` when localStorage is empty (no fallback).
- `AC-AR-010-03`: PASS only if `npm run build --prefix apps/web` exits 0 (TypeScript compilation passes).

## Postconditions

- `token.ts` has no default dev token.
- Dev headers require double opt-in.
- Production bundle is clean.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | 2 line changes, exact before/after specified |
| Dependency clarity | 2 | Single upstream: AR-005 |
| File boundary clarity | 2 | 1 MODIFY, exact lines |
| Contract clarity | 2 | Exact TypeScript code specified |
| Failure behavior | 2 | No fallback = no auth header |
| Security/tenancy | 2 | Removes default credentials |
| Testability | 2 | Build + grep verification |
| Verification | 2 | npm build + python grep, exit 0 |
| Acceptance criteria | 2 | 3 machine-verifiable criteria |
| Reasoning independence | 2 | No architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Remove dev auth capability entirely.
- Change TypeScript types or exports.
- Modify backend files.

## Required executor report

```text
TASK TASK-AR-010 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: NONE
FILES MODIFIED: apps/web/src/auth/token.ts
UNEXPECTED FILES: NONE
TESTS: build PASS, bundle grep PASS
COMMANDS AND EXIT CODES: npm build → 0, grep → 0
ACCEPTANCE: AC-AR-010-01: PASS|FAIL, AC-AR-010-02: PASS|FAIL, AC-AR-010-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: NONE
```
