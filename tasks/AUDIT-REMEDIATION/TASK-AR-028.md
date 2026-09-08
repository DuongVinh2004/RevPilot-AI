# TASK-AR-028 — Dependency Lock and Reproducibility — Constraints, Lockfiles, Pinning

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 0
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IAC-CICD
FEATURE: DEPENDENCY-LOCK
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: NONE
DEPENDS_ON: NONE
UNLOCKS: AR-027

## Objective and rationale

OBJECTIVE: Verify and enforce deterministic dependency reproducibility across Python and Node ecosystems: confirm `requirements.lock` contains exclusively exact `==` pinned versions with zero floating ranges, verify `package-lock.json` exists in repository root and `apps/web/`, align `pyproject.toml` constraints if needed, and verify `npm ci` executes with exit code 0.

BUSINESS RATIONALE: Zero-trust audit finding P1-SCM-001 identified risks of dependency divergence, unpinned transitive requirements, and non-reproducible local/CI builds. Floating dependency ranges or missing lockfile synchronization permit unreviewed third-party code changes to introduce breaking API changes, supply-chain vulnerabilities, or inconsistent runtime behaviors, violating INV-REL-002 and AC-014.

ARCHITECTURAL OWNER: SRE Lead, DevOps Lead

ARCHITECTURAL CONTEXT: INV-REL-002 (deterministic build integrity), AC-014 (anti-fabrication invariant), DEFINITION-OF-DONE.md §Stage B.

## Canonical specification references

- `requirements.lock`
- `pyproject.toml`
- `package.json`
- `package-lock.json`
- `apps/web/package.json`
- `apps/web/package-lock.json`
- `execution/DEFINITION-OF-DONE.md#stage-b-build-and-typecheck-clean`
- `AGENTS.md#anti-fabrication-invariant-ac-014`

If references conflict, return BLOCKED.

## Preconditions

- Python 3.12 available in environment.
- Node.js (>= 20) and npm (>= 10) available in environment.
- `requirements.lock` exists in repository root.
- `apps/web/` workspace exists.

## Change boundary

READ_SET:
- `requirements.lock`
- `pyproject.toml`
- `package.json`
- `package-lock.json`
- `apps/web/package.json`
- `apps/web/package-lock.json`

WRITE_SET:
- `pyproject.toml`
- `requirements.lock`
- `package-lock.json`
- `apps/web/package-lock.json`

CREATE: NONE

MODIFY:
- `pyproject.toml` — Ensure dependency specifications and build-system declarations align with pinned locks (if modifications needed).
- `requirements.lock` — Ensure every single requirement line uses strict `==` pinning without loose comparison operators (`>=`, `<=`, `~=`).
- `package-lock.json` / `apps/web/package-lock.json` — Ensure lockfiles are consistent with `package.json` manifests and resolve cleanly via `npm ci`.

DO_NOT_MODIFY:
- Any Python source code files in `packages/` or `apps/`
- Any frontend source code files in `apps/web/src/`
- `.github/workflows/ci.yml` (reserved for AR-027)
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 0 to 2 configuration/lock files adjusted to maintain strict version pinning.

## Symbol-level contract

MUST EXPORT/DEFINE:
- `requirements.lock`: Pure pinned requirement specification where every line matches regex `^[a-zA-Z0-9_\-\.]+==[a-zA-Z0-9_\-\.\+]+$`.
- `package-lock.json` and `apps/web/package-lock.json`: Valid JSON documents containing `lockfileVersion: 3` (or 2) and deterministic package integrity hashes.

MUST NOT:
- Permit floating version ranges (e.g., `*`, `>=`, `~=`, `^`) in `requirements.lock`.
- Delete `package-lock.json` or use `npm install` in a manner that modifies lockfiles arbitrarily.
- Introduce unpinned dependencies in `pyproject.toml`.

## Input/output and validation

INPUT: Existing `requirements.lock`, `pyproject.toml`, `package.json`, `package-lock.json`.
OUTPUT: Validated, deterministic dependency lock state.
INVALID INPUT: Unpinned requirements or out-of-sync lockfile causing `npm ci` failure → BLOCKED.
VALIDATION RULES:
1. Every dependency line in `requirements.lock` must contain `==`.
2. `package-lock.json` must be present and parseable as valid JSON.
3. `npm ci` in `apps/web` must complete with exit code 0.
STATE TRANSITIONS: NOT APPLICABLE.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `ERR_UNPINNED_DEP` | Dependency lacks `==` pin | N/A | no | Unpinned package detected in lockfile | yes | `build_reproducibility_errors{code="ERR_UNPINNED_DEP"}` |
| `ERR_MISSING_LOCKFILE` | Required lockfile missing | N/A | no | Lockfile missing from expected path | yes | `build_reproducibility_errors{code="ERR_MISSING_LOCKFILE"}` |
| `ERR_NPM_CI_FAILED` | npm ci exits non-zero | N/A | yes | npm ci failed to reproduce node_modules | yes | `build_reproducibility_errors{code="ERR_NPM_CI_FAILED"}` |

## Security contract

AUTHENTICATION: NOT APPLICABLE.
AUTHORIZATION: Repository write access.
TENANT: NOT APPLICABLE.
PII: PROHIBITED.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: Dependency resolution commands access registered upstream package registries (PyPI, npmjs.org) only.
DEFAULT: DENY — unpinned dependencies rejected.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE — no database schema changes.
API CONTRACT: NOT APPLICABLE — no API changes.
EVENT CONTRACT: NOT APPLICABLE — no events.
TEMPORAL CONTRACT: NOT APPLICABLE — no workflows.
AGENT CONTRACT: NOT APPLICABLE — no agent changes.
MODEL CONTRACT: NOT APPLICABLE — no model changes.
RAG CONTRACT: NOT APPLICABLE — no RAG changes.

## Operational behavior

RETRY: Dependency downloads retryable on network failure.
TIMEOUT: `npm ci` operation bounded by 180-second timeout.
IDEMPOTENCY: Idempotent — multiple runs of `npm ci` and lock verification yield identical tree state.
LOGGING: Package installation progress and validation outputs.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: Non-zero exit on unpinned packages or lock divergence halts build.
ROLLBACK/COMPENSATION: Git checkout / revert to restore previous lock state.

## Implementation requirements

1. Read `requirements.lock`. Verify every non-empty line (excluding comments) has `==`. If any entry is unpinned or uses `>=`/`~=`, lock it to an exact pinned version.
2. Verify `pyproject.toml` dependency declarations are valid and compatible with `requirements.lock`.
3. Verify `package-lock.json` exists at repository root and at `apps/web/package-lock.json`.
4. In `apps/web`, run `npm ci` (or `npm ci --dry-run`) to verify that the lockfile is fully synchronized with `package.json` and installs cleanly.
5. If running at root with workspace dependencies, verify root `package-lock.json` consistency.
6. Verify all acceptance criteria with hermetic non-destructive script.

## Tests and evaluations

TESTS REQUIRED:
- Verification script asserting:
  1. All non-comment lines in `requirements.lock` use `==`.
  2. `package-lock.json` exists in root and in `apps/web/`.
  3. `npm ci` command exits 0 in `apps/web/`.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "
import pathlib, sys, subprocess

# 1. Check requirements.lock
req_path = pathlib.Path('requirements.lock')
if not req_path.exists():
    print('FAIL: requirements.lock missing')
    sys.exit(1)

unpinned = []
lines = req_path.read_text(encoding='utf-8').splitlines()
for i, line in enumerate(lines, 1):
    s = line.strip()
    if not s or s.startswith('#'):
        continue
    if '==' not in s or '>=' in s or '<=' in s or '~=' in s:
        unpinned.append((i, s))

if unpinned:
    print(f'FAIL: Unpinned entries in requirements.lock: {unpinned}')
    sys.exit(1)
print('PASS: AC-AR-028-01: requirements.lock has == pins')

# 2. Check package-lock.json
root_pkg_lock = pathlib.Path('package-lock.json')
web_pkg_lock = pathlib.Path('apps/web/package-lock.json')
if not root_pkg_lock.exists() and not web_pkg_lock.exists():
    print('FAIL: package-lock.json missing')
    sys.exit(1)
print('PASS: AC-AR-028-02: package-lock.json exists')

# 3. Check npm ci
cmd = ['npm', 'ci', '--dry-run']
target_cwd = 'apps/web' if web_pkg_lock.exists() else '.'
res = subprocess.run(cmd, cwd=target_cwd, capture_output=True, text=True, shell=True)
if res.returncode != 0:
    print(f'FAIL: npm ci exited {res.returncode}: {res.stderr}')
    sys.exit(1)
print('PASS: AC-AR-028-03: npm ci exits 0')

print('ALL DEPENDENCY LOCK CHECKS PASS')
"
```

EXPECTED: exit code 0 and output `ALL DEPENDENCY LOCK CHECKS PASS`.

## Binary acceptance criteria

- `AC-AR-028-01`: PASS only if every non-empty, non-comment line in `requirements.lock` contains an exact `==` pinned version.
- `AC-AR-028-02`: PASS only if `package-lock.json` exists in `apps/web/` or repository root with valid JSON content.
- `AC-AR-028-03`: PASS only if `npm ci` (or `npm ci --dry-run`) executes with exit code 0.

## Postconditions

- All Python dependencies in `requirements.lock` are strictly pinned with `==`.
- Node package lockfiles verified present, parseable, and consistent.
- `npm ci` verified working cleanly.
- Unblocks AR-027.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Concrete objective: verify pins, lockfile presence, and npm ci |
| Dependency clarity | 2 | Zero upstream dependencies; unblocks AR-027 |
| File boundary clarity | 2 | Exact lockfiles and configuration files specified in boundary |
| Contract clarity | 2 | Pinned syntax regex and npm ci exit code contract fully defined |
| Failure behavior | 2 | Unpinned dependency or lockfile divergence fails verification |
| Security/tenancy | 2 | Secures supply chain against drifting and unpinned transitive packages |
| Testability | 2 | Direct script execution checking lines and running npm ci |
| Verification | 2 | Single hermetic python command, exit 0 |
| Acceptance criteria | 2 | 3 machine-verifiable criteria |
| Reasoning independence | 2 | Mechanical verification and lock pinning, zero open architectural choices |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Relax pinned versions to floating version ranges.
- Delete lockfiles to regenerate from unconstrained dependencies.
- Remove packages without approval.

## Required executor report

```text
TASK TASK-AR-028 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: NONE
FILES MODIFIED: <list or NONE>
UNEXPECTED FILES: NONE
TESTS: <verification script output>
COMMANDS AND EXIT CODES: <command> → <exit code>
ACCEPTANCE: AC-AR-028-01: PASS|FAIL, AC-AR-028-02: PASS|FAIL, AC-AR-028-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-027
```
