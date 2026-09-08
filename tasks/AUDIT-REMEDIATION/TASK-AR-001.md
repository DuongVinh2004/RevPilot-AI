# TASK-AR-001 — Relabel Evidence and Acceptance Documents to Reflect Actual Verification State

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 18
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: GOVERNANCE-BASELINE
FEATURE: EVIDENCE-RELABEL
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: YES
PARALLEL_WITH: AR-002, AR-003
DEPENDS_ON: NONE
UNLOCKS: AR-004, AR-011

## Objective and rationale

OBJECTIVE: Change status labels in 4 governance files from unqualified VERIFIED/PASS/ACCEPTED/GREEN to CLAIMED/SIMULATED/PENDING/CONDITIONAL reflecting actual evidence state.

BUSINESS RATIONALE: Zero-trust audit (2026-09-08) finding P0-GOV-001 proved that production acceptance reports, evidence index, rail status and go-live reports contain claims contradicted by simulation-based test harnesses. Maintaining false-green status violates AC-014 Anti-Fabrication Invariant and blocks honest go-live assessment.

ARCHITECTURAL OWNER: Documentation Engineer, SRE Lead

ARCHITECTURAL CONTEXT: INV-REL-002 (production acceptance never granted on documentation alone), AC-014 (anti-fabrication invariant), DEFINITION-OF-DONE.md §Stage D.

## Canonical specification references

- `execution/DEFINITION-OF-DONE.md#stage-d-evidence-complete`
- `execution/PRODUCTION-ACCEPTANCE-REPORT.md`
- `execution/evidence/EVIDENCE-INDEX.md`
- `execution/RAIL-STATUS.md`
- `execution/GO-LIVE-READINESS-REPORT.md`
- `AGENTS.md#anti-fabrication-invariant-ac-014`

If references conflict, return BLOCKED.

## Preconditions

- All 4 target files exist in `execution/` directory.
- Current file content has been read (READ_SET inspected) to identify exact lines requiring relabeling.
- No concurrent modifications to the same files by other tasks.

## Change boundary

READ_SET:
- `execution/PRODUCTION-ACCEPTANCE-REPORT.md`
- `execution/evidence/EVIDENCE-INDEX.md`
- `execution/RAIL-STATUS.md`
- `execution/GO-LIVE-READINESS-REPORT.md`
- `execution/DEFINITION-OF-DONE.md`
- `AGENTS.md`

WRITE_SET:
- `execution/PRODUCTION-ACCEPTANCE-REPORT.md`
- `execution/evidence/EVIDENCE-INDEX.md`
- `execution/RAIL-STATUS.md`
- `execution/GO-LIVE-READINESS-REPORT.md`

CREATE: NONE

MODIFY:
- `execution/PRODUCTION-ACCEPTANCE-REPORT.md` — Ensure status line reflects `NOT_ACCEPTED / TECHNICAL DEBT & INFRASTRUCTURE DRILLS PENDING (AC-014)`. Verify each acceptance criterion row has correct evaluation result matching its evidence type (SIMULATED → REJECTED/SIMULATED, unit-only → CONDITIONAL).
- `execution/evidence/EVIDENCE-INDEX.md` — Ensure header status contains `Demoted per AC-014 Invariant`. Each evidence package with SIMULATED test harness marked as `SIMULATED / PENDING_*` not `VERIFIED / PASS`.
- `execution/RAIL-STATUS.md` — Add qualifier `(UNIT/CONTRACT TESTS ONLY — NOT PRODUCTION EMPIRICAL)` to evidence column for rails whose evidence packages are SIMULATED.
- `execution/GO-LIVE-READINESS-REPORT.md` — Add CAUTION banner: `> [!CAUTION]\n> This report was generated from unit/contract test evidence only. Production empirical validation pending per AC-014.`

DO_NOT_MODIFY:
- `execution/DEFINITION-OF-DONE.md`
- `AGENTS.md`
- `execution/EXECUTOR-QUEUE.md`
- Any file outside WRITE_SET

EXPECTED CHANGE SET: Status labels and qualifier text in 4 files. No structural changes to tables or sections.

## Symbol-level contract

MUST EXPORT/DEFINE: No code symbols. This task modifies documentation only.

MUST NOT: Create new files. Change table structure. Remove existing content. Add claims about production readiness. Alter evidence SHA-256 hashes.

## Input/output and validation

INPUT: Current content of 4 governance files.
OUTPUT: Updated content with corrected status labels.
INVALID INPUT: Files missing from expected paths → BLOCKED.
VALIDATION RULES: Every evidence package marked SIMULATED in EVIDENCE-INDEX.md must have matching status in PRODUCTION-ACCEPTANCE-REPORT.md. No unqualified "PRODUCTION READY" or "ACCEPTED" without SIMULATED/CONDITIONAL/PENDING qualifier.
STATE TRANSITIONS: NOT APPLICABLE — documentation-only task.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| NOT APPLICABLE | Documentation-only task | N/A | N/A | N/A | N/A | N/A |

## Security contract

AUTHENTICATION: NOT APPLICABLE — documentation task.
AUTHORIZATION: Requires repository write access.
TENANT: NOT APPLICABLE.
PII: PROHIBITED — no PII in governance documents.
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

RETRY: NOT APPLICABLE — documentation task.
TIMEOUT: NOT APPLICABLE.
IDEMPOTENCY: Idempotent — running relabeling multiple times produces same result.
LOGGING: NOT APPLICABLE.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: If any target file is missing, return BLOCKED.
ROLLBACK/COMPENSATION: Git revert to previous commit.

## Implementation requirements

1. Read all 4 target files completely.
2. For `PRODUCTION-ACCEPTANCE-REPORT.md`: Verify line 4 contains `NOT_ACCEPTED`. If it still says `ACCEPTED` or `PRODUCTION READY` without qualifier, change to `NOT_ACCEPTED / TECHNICAL DEBT & INFRASTRUCTURE DRILLS PENDING (AC-014)`.
3. For `EVIDENCE-INDEX.md`: Verify line 4 contains `Demoted per AC-014 Invariant`. For each row where test suite is in-memory/mock/simulation, ensure Status column is `SIMULATED / PENDING_*`.
4. For `RAIL-STATUS.md`: For each rail where evidence is from unit/contract tests only (not staging/production), add qualifier `(UNIT/CONTRACT TESTS ONLY — NOT PRODUCTION EMPIRICAL)` to Evidence column.
5. For `GO-LIVE-READINESS-REPORT.md`: Add CAUTION banner at top of document after header.
6. Verify no unqualified production-ready claims remain.

## Tests and evaluations

TESTS REQUIRED:
- Verification script (see below) must exit 0.
- Manual review: grep for unqualified "PRODUCTION READY", "ACCEPTED.*PASS", "VERIFIED" without SIMULATED/CONDITIONAL/PENDING qualifier.

AI EVALS REQUIRED: NOT APPLICABLE — no AI model changes.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "
import re, sys, pathlib
files = [
    'execution/PRODUCTION-ACCEPTANCE-REPORT.md',
    'execution/evidence/EVIDENCE-INDEX.md',
    'execution/RAIL-STATUS.md',
    'execution/GO-LIVE-READINESS-REPORT.md',
]
pat = re.compile(r'(?:PRODUCTION.READY|ACCEPTED.*PASS)', re.IGNORECASE)
fail = False
for f in files:
    text = pathlib.Path(f).read_text(encoding='utf-8')
    for i, line in enumerate(text.splitlines(), 1):
        if pat.search(line) and 'SIMULATED' not in line and 'CONDITIONAL' not in line and 'PENDING' not in line and 'AC-014' not in line and 'NOT_ACCEPTED' not in line:
            print(f'FAIL: {f}:{i}: {line.strip()}')
            fail = True
if fail:
    sys.exit(1)
print('PASS: No unqualified production-ready claims found')
"
```

EXPECTED: exit code 0 and output `PASS: No unqualified production-ready claims found`.

## Binary acceptance criteria

- `AC-AR-001-01`: PASS only if no string matching `PRODUCTION.READY` or `ACCEPTED.*PASS` (case-insensitive) exists in the 4 target files without qualifier SIMULATED, CONDITIONAL, PENDING, AC-014, or NOT_ACCEPTED on the same line.
- `AC-AR-001-02`: PASS only if every evidence package with status SIMULATED in EVIDENCE-INDEX.md has matching non-ACCEPTED status in PRODUCTION-ACCEPTANCE-REPORT.md.
- `AC-AR-001-03`: PASS only if GO-LIVE-READINESS-REPORT.md contains `[!CAUTION]` banner referencing AC-014.

## Postconditions

- 4 governance files have corrected status labels.
- No new files created.
- No files outside WRITE_SET modified.
- Verification script exits 0.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Single observable change: relabel 4 files |
| Dependency clarity | 2 | No upstream dependencies |
| File boundary clarity | 2 | Exact 4 files in WRITE_SET, 6 in READ_SET |
| Contract clarity | 2 | Status label rules fully specified |
| Failure behavior | 2 | Missing file → BLOCKED |
| Security/tenancy | 2 | Documentation-only, no runtime impact |
| Testability | 2 | Verification script with exact regex |
| Verification | 2 | Single python command, exit 0 |
| Acceptance criteria | 2 | 3 machine-verifiable criteria |
| Reasoning independence | 2 | No architectural decisions required |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Change evidence SHA-256 hashes.
- Remove existing content or table rows.
- Add new claims about production readiness.

## Required executor report

```text
TASK TASK-AR-001 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: NONE
FILES MODIFIED: <list>
UNEXPECTED FILES: NONE
TESTS: <verification script output>
COMMANDS AND EXIT CODES: <command> → <exit code>
ACCEPTANCE: AC-AR-001-01: PASS|FAIL, AC-AR-001-02: PASS|FAIL, AC-AR-001-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-004 or AR-011
```
