# TASK-AR-002 — Create AUDIT-BASELINE Artifact with Provenance and Tool Versions

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 0
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: GOVERNANCE-BASELINE
FEATURE: AUDIT-BASELINE
COMPLEXITY: XS
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-001, AR-003
DEPENDS_ON: NONE
UNLOCKS: AR-004

## Objective and rationale

OBJECTIVE: Create `execution/AUDIT-BASELINE.md` documenting the exact commit SHA, timestamp, tool versions, blocked checks, and Python/Node runtime versions at the time of the zero-trust audit.

BUSINESS RATIONALE: Finding P0-GOV-001 requires an immutable provenance record establishing what was and was not verified during the audit. Without this baseline, future remediation tasks cannot reference the exact starting point.

ARCHITECTURAL OWNER: Documentation Engineer

ARCHITECTURAL CONTEXT: AGENTS.md §Historical Immutability, DEFINITION-OF-DONE.md §Stage A.

## Canonical specification references

- `AGENTS.md#4-documentation--metadata-governance`
- `execution/DEFINITION-OF-DONE.md#stage-a-documentation-content-complete`

If references conflict, return BLOCKED.

## Preconditions

- Git repository is initialized and HEAD is known.
- Python and Node.js are available in PATH for version detection.

## Change boundary

READ_SET:
- `.git/HEAD`
- `pyproject.toml`
- `package.json`

WRITE_SET:
- `execution/AUDIT-BASELINE.md`

CREATE:
- `execution/AUDIT-BASELINE.md`

MODIFY: NONE

DO_NOT_MODIFY:
- Any existing file

EXPECTED CHANGE SET: One new file `execution/AUDIT-BASELINE.md` containing provenance metadata.

## Symbol-level contract

MUST EXPORT/DEFINE: No code symbols. Documentation artifact only.

MUST NOT: Modify existing files. Fabricate tool versions. Run destructive commands.

## Input/output and validation

INPUT: Git HEAD, Python version, Node version, tool availability checks.
OUTPUT: Markdown file with structured provenance table.
INVALID INPUT: Git not initialized → BLOCKED.
VALIDATION RULES: Commit SHA must be 40 hex characters. Tool versions must be from actual runtime output.
STATE TRANSITIONS: NOT APPLICABLE.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| NOT APPLICABLE | Documentation-only task | N/A | N/A | N/A | N/A | N/A |

## Security contract

AUTHENTICATION: NOT APPLICABLE.
AUTHORIZATION: Repository write access.
TENANT: NOT APPLICABLE.
PII: PROHIBITED.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE — no data schema changes.
API CONTRACT: NOT APPLICABLE — no API changes.
EVENT CONTRACT: NOT APPLICABLE — no events.
TEMPORAL CONTRACT: NOT APPLICABLE — no workflows.
AGENT CONTRACT: NOT APPLICABLE — no agent changes.
MODEL CONTRACT: NOT APPLICABLE — no model changes.
RAG CONTRACT: NOT APPLICABLE — no RAG changes.

## Operational behavior

RETRY: NOT APPLICABLE.
TIMEOUT: NOT APPLICABLE.
IDEMPOTENCY: Idempotent — regenerating baseline overwrites with same content if inputs unchanged.
LOGGING: NOT APPLICABLE.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: Git unavailable → BLOCKED.
ROLLBACK/COMPENSATION: Delete created file.

## Implementation requirements

1. Capture `git rev-parse HEAD` output.
2. Capture `python --version` output.
3. Capture `node --version` output.
4. Check availability of: pytest, ruff, mypy, docker, terraform, psql, temporal (each: `which <tool>` or `where <tool>`).
5. Create `execution/AUDIT-BASELINE.md` with:
   - Header: `# Audit Baseline Record`
   - Metadata: Date, Audit commit SHA, Branch, Auditor scope.
   - Table: Tool | Version/Path | Status (AVAILABLE/BLOCKED).
   - Blocked checks list from audit report.
   - Python version, Node version.
   - Statement: "This baseline is immutable. Updates require a new baseline file with supersession link."

## Tests and evaluations

TESTS REQUIRED:
- File exists at `execution/AUDIT-BASELINE.md`.
- File contains commit SHA `80eb4cbfdbba5011a1815e8d617033d8cad6ccb9`.
- File contains tool status table with at least 7 rows.
- File contains Python version string.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "
import pathlib, sys
f = pathlib.Path('execution/AUDIT-BASELINE.md')
if not f.exists():
    print('FAIL: file missing'); sys.exit(1)
text = f.read_text(encoding='utf-8')
checks = [
    ('80eb4cb' in text, 'contains audit commit SHA'),
    ('AVAILABLE' in text or 'BLOCKED' in text, 'contains tool status'),
    ('Python' in text, 'contains Python version'),
    ('Audit Baseline' in text, 'contains header'),
]
for ok, desc in checks:
    status = 'PASS' if ok else 'FAIL'
    print(f'{status}: {desc}')
    if not ok:
        sys.exit(1)
print('ALL CHECKS PASS')
"
```

EXPECTED: exit code 0 and output `ALL CHECKS PASS`.

## Binary acceptance criteria

- `AC-AR-002-01`: PASS only if `execution/AUDIT-BASELINE.md` exists and contains commit SHA `80eb4cbfdbba5011a1815e8d617033d8cad6ccb9`.
- `AC-AR-002-02`: PASS only if file contains tool status table with at least 7 rows (pytest, ruff, mypy, docker, terraform, psql, temporal) each marked AVAILABLE or BLOCKED.
- `AC-AR-002-03`: PASS only if file contains Python version output and Node version output from runtime.

## Postconditions

- `execution/AUDIT-BASELINE.md` exists with complete provenance.
- No existing files modified.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Single file creation with exact content |
| Dependency clarity | 2 | No upstream dependencies |
| File boundary clarity | 2 | One CREATE path, no MODIFY |
| Contract clarity | 2 | Content structure fully specified |
| Failure behavior | 2 | Git unavailable → BLOCKED |
| Security/tenancy | 2 | Documentation-only, no runtime impact |
| Testability | 2 | Content verification script |
| Verification | 2 | Single python command, exit 0 |
| Acceptance criteria | 2 | 3 machine-verifiable criteria |
| Reasoning independence | 2 | No architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Modify any existing file.
- Fabricate tool versions or availability status.

## Required executor report

```text
TASK TASK-AR-002 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: execution/AUDIT-BASELINE.md
FILES MODIFIED: NONE
UNEXPECTED FILES: NONE
TESTS: <verification script output>
COMMANDS AND EXIT CODES: <command> → <exit code>
ACCEPTANCE: AC-AR-002-01: PASS|FAIL, AC-AR-002-02: PASS|FAIL, AC-AR-002-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-004
```
