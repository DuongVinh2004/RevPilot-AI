# TASK-AR-027 — CI Pipeline Gates — Mypy, Docker, Terraform, Integration

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 0
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IAC-CICD
FEATURE: CI-GATES
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 18/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-028
UNLOCKS: AR-026

## Objective and rationale

OBJECTIVE: Add real CI pipeline gates to `.github/workflows/ci.yml`: execute mypy type checking (not just install), enforce `npm ci` (not `npm install`), add terraform format/validate gate, add `pip-audit` security vulnerability scanning, and add `pytest --collect-only` test collection verification.

BUSINESS RATIONALE: Zero-trust audit finding P1-SCM-001 demonstrated that CI pipeline configurations were incomplete or permissive: mypy was installed in step dependencies but never executed, dependency installation risks non-reproducible resolution if npm install is used over npm ci, infrastructure Terraform manifests in `infra/` were unvalidated in CI, and Python dependencies were not audited for known CVEs. Establishing strict, deterministic CI gates prevents silent type rot, configuration divergence, vulnerable packages, and broken test collections from merging into main.

ARCHITECTURAL OWNER: SRE Lead, DevOps Lead

ARCHITECTURAL CONTEXT: INV-REL-002 (deterministic build integrity), AC-014 (anti-fabrication invariant), DEFINITION-OF-DONE.md §Stage B and §Stage D.

## Canonical specification references

- `.github/workflows/ci.yml`
- `execution/DEFINITION-OF-DONE.md#stage-b-build-and-typecheck-clean`
- `execution/DEFINITION-OF-DONE.md#stage-c-validation-complete`
- `AGENTS.md#anti-fabrication-invariant-ac-014`

If references conflict, return BLOCKED.

## Preconditions

- AR-028 PASS (dependency locks and pinning verified across Python and Node).
- `.github/workflows/ci.yml` exists in repository root.
- Terraform manifests exist in `infra/environments/staging/`.
- `requirements.lock` exists with pinned dependencies.

## Change boundary

READ_SET:
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `requirements.lock`
- `apps/web/package.json`
- `infra/environments/staging/versions.tf`

WRITE_SET:
- `.github/workflows/ci.yml`

CREATE: NONE

MODIFY:
- `.github/workflows/ci.yml` — Add dedicated `mypy` typecheck step in backend job, add `pip-audit` dependency vulnerability step, add `pytest --collect-only` step, ensure `npm ci` is enforced in frontend job, and add `infra-check` job executing `terraform fmt -check` and `terraform validate`.

DO_NOT_MODIFY:
- `pyproject.toml`
- `requirements.lock`
- `apps/**`
- `infra/**`
- `packages/**`
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 1 file modified (`.github/workflows/ci.yml`) with 5 verifiable CI gates added or enforced.

## Symbol-level contract

MUST EXPORT/DEFINE:
In `.github/workflows/ci.yml`:
- Dedicated step running `mypy packages/backend/src apps/api` (or `mypy .` per `pyproject.toml`) under Python job.
- Step running `pip-audit` (or `pip audit`) against `requirements.lock`.
- Step running `pytest --collect-only -q` to verify hermetic test collection integrity.
- Frontend step executing `npm ci` strictly (never `npm install`).
- Infrastructure job or step executing `terraform fmt -check` and `terraform validate` within `infra/environments/staging`.

MUST NOT:
- Add `continue-on-error: true` or `|| true` to suppress gate failures.
- Remove or weaken existing `ruff check` or `pytest` steps.
- Introduce unpinned third-party GitHub Actions (all actions must pin major version `@v4` / `@v5` or commit hash).

## Input/output and validation

INPUT: Existing `.github/workflows/ci.yml`.
OUTPUT: Hardened `.github/workflows/ci.yml` incorporating all 5 CI gates.
INVALID INPUT: Permissive error swallowing (`continue-on-error: true`) or YAML syntax errors → BLOCKED.
VALIDATION RULES:
1. Every gate step must fail the CI run if any error or violation is detected.
2. YAML syntax must pass validation without warnings.
3. Steps must reference pinned tools and local paths correctly.
STATE TRANSITIONS: NOT APPLICABLE — workflow configuration only.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `ERR_GATE_MYPY_FAILED` | Static typecheck failure | N/A | yes | Type check failed during CI gate | yes | `ci_gate_failures_total{gate="mypy"}` |
| `ERR_GATE_AUDIT_FAILED` | CVE detected in dependencies | N/A | yes | Dependency vulnerability scan failed | yes | `ci_gate_failures_total{gate="pip_audit"}` |
| `ERR_GATE_TF_INVALID` | Malformed or invalid Terraform | N/A | yes | Terraform validation gate failed | yes | `ci_gate_failures_total{gate="terraform"}` |
| `ERR_GATE_NPM_CI_FAILED` | Frontend lockfile mismatch | N/A | yes | npm ci failed to resolve dependencies | yes | `ci_gate_failures_total{gate="npm_ci"}` |
| `ERR_GATE_COLLECT_FAILED` | Pytest collection error | N/A | yes | Test collection gate failed | yes | `ci_gate_failures_total{gate="pytest_collect"}` |

## Security contract

AUTHENTICATION: GitHub Actions standard repository GITHUB_TOKEN permissions (read-only for pull requests).
AUTHORIZATION: Restricted to CI workflow runners.
TENANT: NOT APPLICABLE.
PII: PROHIBITED — no test payloads or logs containing PII in CI outputs.
SECRET ACCESS: CI gates run with zero access to production secrets; local mocks only.
EXTERNAL ACTION: PROHIBITED — gate steps must not emit unauthorized outbound webhooks or telemetry.
DEFAULT: DENY — all gate steps fail closed on any non-zero exit code.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE — no database schema changes.
API CONTRACT: NOT APPLICABLE — no HTTP API changes.
EVENT CONTRACT: NOT APPLICABLE — no event schema changes.
TEMPORAL CONTRACT: NOT APPLICABLE — no workflow changes.
AGENT CONTRACT: NOT APPLICABLE — no agent changes.
MODEL CONTRACT: NOT APPLICABLE — no model changes.
RAG CONTRACT: NOT APPLICABLE — no RAG changes.

## Operational behavior

RETRY: CI workflow retry handled by GitHub Actions runner on transient infrastructure failures.
TIMEOUT: Each CI job bounded by 15-minute job timeout.
IDEMPOTENCY: Idempotent — deterministic gate evaluation given identical git tree.
LOGGING: Standard GitHub Actions step log streaming.
METRICS: Workflow step pass/fail metrics recorded in GitHub Actions run history.
FAILURE BEHAVIOR: Any gate failure halts pipeline progression and marks commit status check as failed.
ROLLBACK/COMPENSATION: Git revert on `.github/workflows/ci.yml`.

## Implementation requirements

1. Read `.github/workflows/ci.yml` completely.
2. In `backend-test` job:
   - Verify `pip-audit` is installed during dependency installation step (`pip install ruff mypy pytest pip-audit`).
   - Add step: `name: Typecheck with Mypy` executing `mypy packages/backend/src apps/api` (or `mypy .`).
   - Add step: `name: Audit Python Dependencies` executing `pip-audit -r requirements.lock`.
   - Add step: `name: Verify Pytest Collection` executing `python -m pytest --collect-only -q`.
3. In `frontend-check` job:
   - Ensure dependency step uses `run: npm ci` with `cache: "npm"` and `cache-dependency-path: apps/web/package-lock.json`.
4. Add `infra-check` job:
   - Target: `runs-on: ubuntu-latest`.
   - Steps: Checkout, Setup Terraform (`hashicorp/setup-terraform@v3`), `terraform fmt -check` and `terraform -chdir=infra/environments/staging init -backend=false && terraform -chdir=infra/environments/staging validate`.
5. Verify YAML formatting and valid syntax.
6. Verify no gate step contains `continue-on-error: true`.

## Tests and evaluations

TESTS REQUIRED:
- Verification script must parse `.github/workflows/ci.yml` and assert presence of all 5 gates (`mypy`, `npm ci`, `terraform validate`, `pip-audit`, `pytest --collect-only`).
- Verification script must assert absence of `continue-on-error: true` on gate steps.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Total CI execution overhead added < 90 seconds.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "
import pathlib, sys, yaml

workflow_path = pathlib.Path('.github/workflows/ci.yml')
if not workflow_path.exists():
    print('FAIL: .github/workflows/ci.yml does not exist')
    sys.exit(1)

content = workflow_path.read_text(encoding='utf-8')
data = yaml.safe_load(content)

raw = content.lower()
checks = [
    ('mypy' in raw and 'run:' in raw, 'CI has mypy run step'),
    ('npm ci' in raw, 'npm ci enforced in CI'),
    ('terraform' in raw and 'validate' in raw, 'terraform validate in CI'),
    ('pip-audit' in raw or 'pip audit' in raw, 'pip audit in CI'),
    ('collect-only' in raw, 'pytest --collect-only in CI'),
    ('continue-on-error: true' not in raw, 'no continue-on-error on gates'),
]

fail = False
for ok, desc in checks:
    status = 'PASS' if ok else 'FAIL'
    print(f'{status}: {desc}')
    if not ok:
        fail = True

if fail:
    sys.exit(1)
print('PASS: All CI pipeline gates verified')
"
```

EXPECTED: exit code 0 and output `PASS: All CI pipeline gates verified`.

## Binary acceptance criteria

- `AC-AR-027-01`: PASS only if `.github/workflows/ci.yml` contains a step executing `mypy` that fails the job on type errors without `continue-on-error: true`.
- `AC-AR-027-02`: PASS only if `.github/workflows/ci.yml` enforces `npm ci` for frontend dependency installation.
- `AC-AR-027-03`: PASS only if `.github/workflows/ci.yml` contains a step or job executing `terraform validate`.
- `AC-AR-027-04`: PASS only if `.github/workflows/ci.yml` contains a step executing `pip-audit` or `pip audit`.

## Postconditions

- `.github/workflows/ci.yml` enforces mypy, npm ci, terraform validate, pip audit, and pytest collection.
- No source code or infrastructure definitions modified.
- Verification script exits 0.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Exact 5 CI gates defined with explicit step commands |
| Dependency clarity | 2 | Depends on AR-028, unblocks AR-026 |
| File boundary clarity | 2 | Single file in WRITE_SET (`.github/workflows/ci.yml`) |
| Contract clarity | 2 | Workflow step contracts and fail-closed criteria fully specified |
| Failure behavior | 2 | Any step failure breaks pipeline fail-closed |
| Security/tenancy | 2 | Integrates pip-audit vulnerability scanning and terraform linting |
| Testability | 1 | Schema and content verifiable hermetically; full GitHub Actions execution requires remote runner |
| Verification | 2 | Hermetic Python YAML verification script, exit 0 |
| Acceptance criteria | 2 | 4 machine-verifiable criteria |
| Reasoning independence | 1 | CI job dependency sequencing and action pinning require DevOps domain awareness |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Add `continue-on-error: true` or `|| true` to suppress CI gate failures.
- Use `npm install` instead of `npm ci`.
- Remove existing lint or test steps.

## Required executor report

```text
TASK TASK-AR-027 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: NONE
FILES MODIFIED: .github/workflows/ci.yml
UNEXPECTED FILES: NONE
TESTS: <verification script output>
COMMANDS AND EXIT CODES: <command> → <exit code>
ACCEPTANCE: AC-AR-027-01: PASS|FAIL, AC-AR-027-02: PASS|FAIL, AC-AR-027-03: PASS|FAIL, AC-AR-027-04: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-026
```
