# TASK-AR-030 — Rebuild Evidence Index with Real Artifact References

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 18
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: EVIDENCE-REBUILD
FEATURE: EVIDENCE-INDEX-REBUILD
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-003, AR-029
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Rebuild `execution/evidence/EVIDENCE-INDEX.md` with honest, empirical verification statuses: ensure packages are labeled `VERIFIED` only if a validated `manifest.json` and physical raw artifact files exist on disk; ensure the hash column binds to actual raw artifact SHA-256 digests; add a dedicated `Manifest Path` column to the Master Evidence Index Table; and replace hardcoded, unmeasured test numbers with references to `execution/evidence/TEST-COLLECTION-MANIFEST.txt`.

BUSINESS RATIONALE: Zero-trust audit findings P0-GOV-001 and P2-TEST-001 proved that `EVIDENCE-INDEX.md` contained unsupported `VERIFIED / PASS` designations for evidence packages lacking raw machine execution outputs and cited contradictory test counts across governance files. Maintaining unverified green claims directly violates INV-REL-002 and the AC-014 Anti-Fabrication Invariant. Updating the index creates a verifiable audit trail tied to cryptographic digests and real disk artifacts.

ARCHITECTURAL OWNER: SRE Lead, Compliance Lead

ARCHITECTURAL CONTEXT: INV-REL-002 (production acceptance never granted on documentation alone), AC-014 (anti-fabrication invariant), DEFINITION-OF-DONE.md §Stage D.

## Canonical specification references

- `execution/evidence/EVIDENCE-INDEX.md`
- `execution/evidence/TEST-COLLECTION-MANIFEST.txt`
- `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json`
- `scripts/validate-evidence-manifest.py`
- `AGENTS.md#anti-fabrication-invariant-ac-014`
- `execution/DEFINITION-OF-DONE.md#stage-d-evidence-complete`

If references conflict, return BLOCKED.

## Preconditions

- AR-003 PASS (`execution/evidence/TEST-COLLECTION-MANIFEST.txt` exists and provides collected test counts).
- AR-029 PASS (`execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json` and `scripts/validate-evidence-manifest.py` exist).
- `execution/evidence/EVIDENCE-INDEX.md` exists.

## Change boundary

READ_SET:
- `execution/evidence/EVIDENCE-INDEX.md`
- `execution/evidence/TEST-COLLECTION-MANIFEST.txt`
- `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json`
- `scripts/validate-evidence-manifest.py`
- `execution/evidence/`

WRITE_SET:
- `execution/evidence/EVIDENCE-INDEX.md`

CREATE: NONE

MODIFY:
- `execution/evidence/EVIDENCE-INDEX.md` — Add `Manifest Path` column to Master Evidence Index Table; adjust each row's status so only packages with on-disk manifests and raw artifacts are marked `VERIFIED` (all others demoted to `SIMULATED / PENDING_*` or `CLAIMED / PENDING_EVIDENCE_REBUILD`); update hash column to reference raw artifact digests; update summary section to reference `TEST-COLLECTION-MANIFEST.txt`.

DO_NOT_MODIFY:
- `execution/evidence/TEST-COLLECTION-MANIFEST.txt`
- `scripts/validate-evidence-manifest.py`
- `tasks/**`
- Any source code files
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 1 file modified (`execution/evidence/EVIDENCE-INDEX.md`).

## Symbol-level contract

MUST EXPORT/DEFINE:
In `execution/evidence/EVIDENCE-INDEX.md`:
- Updated Master Evidence Index Table containing columns:
  `| Evidence ID | Evidence Type | Requirements Covered | Source Test Suite | Test Date | Environment | Owner | Manifest Path | Raw Artifact / SHA-256 Hash | Status | Expiry / Review | Document Link | Blocking Impact |`
- Evidence status rule: status containing `VERIFIED` requires a non-empty `Manifest Path` pointing to an existing `manifest.json` and valid raw artifact file on disk.
- Summary section referencing `TEST-COLLECTION-MANIFEST.txt` for test count metrics.

MUST NOT:
- Mark any row as `VERIFIED` or `VERIFIED / PASS` if its `Manifest Path` is missing or its raw artifact files do not exist on disk.
- Retain hardcoded test counts that conflict with `TEST-COLLECTION-MANIFEST.txt`.
- Remove existing historical evidence rows or alter requirement mapping keys.

## Input/output and validation

INPUT: Current `execution/evidence/EVIDENCE-INDEX.md` and evidence artifacts in `execution/evidence/`.
OUTPUT: Updated `execution/evidence/EVIDENCE-INDEX.md` strictly aligned with on-disk artifacts.
INVALID INPUT: Any row claiming `VERIFIED` without physical manifest and raw artifacts → BLOCKED.
VALIDATION RULES:
1. Every row where `Status` contains `VERIFIED` must have a non-empty `Manifest Path`.
2. The file at `Manifest Path` must exist and pass manifest validation.
3. Every raw artifact listed in `raw_artifact_paths` of that manifest must exist on disk.
4. Summary section must link to `TEST-COLLECTION-MANIFEST.txt`.
STATE TRANSITIONS: Packages lacking raw artifacts transition from `VERIFIED / PASS` → `CLAIMED / PENDING_EVIDENCE_REBUILD` or `SIMULATED / PENDING_*`.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `ERR_UNVERIFIED_STATUS` | Row marked VERIFIED lacks raw artifacts | N/A | no | Evidence row marked VERIFIED without on-disk raw artifacts | yes | `evidence_audit_errors{code="ERR_UNVERIFIED_STATUS"}` |
| `ERR_MISSING_MANIFEST_PATH` | VERIFIED row lacks Manifest Path | N/A | no | VERIFIED evidence package missing Manifest Path column value | yes | `evidence_audit_errors{code="ERR_MISSING_MANIFEST_PATH"}` |
| `ERR_MISSING_TEST_MANIFEST_REF`| Summary lacks TEST-COLLECTION-MANIFEST ref | N/A | no | Evidence index summary missing test collection manifest link | yes | `evidence_audit_errors{code="ERR_MISSING_TEST_REF"}` |

## Security contract

AUTHENTICATION: NOT APPLICABLE.
AUTHORIZATION: Repository write access.
TENANT: NOT APPLICABLE.
PII: PROHIBITED.
SECRET ACCESS: PROHIBITED.
EXTERNAL ACTION: PROHIBITED.
DEFAULT: DENY — unbacked evidence claims rejected.

## Specialized contracts

DATA CONTRACT: NOT APPLICABLE — markdown table schema only.
API CONTRACT: NOT APPLICABLE.
EVENT CONTRACT: NOT APPLICABLE.
TEMPORAL CONTRACT: NOT APPLICABLE.
AGENT CONTRACT: Enforces AC-014 (anti-fabrication).
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: NOT APPLICABLE.
TIMEOUT: Execution bounded to < 5 seconds.
IDEMPOTENCY: Idempotent — multiple applications of table update produce identical output.
LOGGING: NOT APPLICABLE.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: Verification script exits 1 if any unbacked VERIFIED claim is detected.
ROLLBACK/COMPENSATION: Git checkout / revert on `execution/evidence/EVIDENCE-INDEX.md`.

## Implementation requirements

1. Read `execution/evidence/EVIDENCE-INDEX.md`.
2. Inspect the repository for existing evidence manifests and raw log files under `execution/evidence/`.
3. Add `Manifest Path` column to the Master Evidence Index Table header and separator row.
4. For each evidence row:
   - Check if a valid `manifest.json` exists for that package.
   - If `manifest.json` exists and its `raw_artifact_paths` exist on disk, populate `Manifest Path` (e.g. `execution/evidence/<ID>/manifest.json`) and raw artifact hash, keeping or setting status to `VERIFIED`.
   - If `manifest.json` or raw artifacts do NOT exist on disk, set `Manifest Path` to `NONE / PENDING` and update `Status` to `SIMULATED / PENDING_DRILL (AC-014)` or `CLAIMED / PENDING_EVIDENCE_REBUILD`.
   - Update `Blocking Impact` accordingly (`BLOCKED` or `CONDITIONAL`).
5. In Section 3 (Evidence Status Summary), add explicit reference:
   `Authoritative test suite counts are tracked in [TEST-COLLECTION-MANIFEST.txt](TEST-COLLECTION-MANIFEST.txt).`
6. Run verification script to guarantee no false-green verification claims remain.

## Tests and evaluations

TESTS REQUIRED:
- Verification script asserting:
  1. All rows with `VERIFIED` status have valid manifest files and on-disk raw artifacts.
  2. No rows without raw artifacts have status `VERIFIED` or `VERIFIED / PASS`.
  3. `TEST-COLLECTION-MANIFEST.txt` is referenced in `EVIDENCE-INDEX.md`.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "
import pathlib, sys, json

index_path = pathlib.Path('execution/evidence/EVIDENCE-INDEX.md')
if not index_path.exists():
    print('FAIL: EVIDENCE-INDEX.md missing')
    sys.exit(1)

content = index_path.read_text(encoding='utf-8')
lines = content.splitlines()

# 1. Verify Manifest Path column exists in table header
table_header = None
for line in lines:
    if '| Evidence ID |' in line and '| Manifest Path |' in line:
        table_header = line
        break

if not table_header:
    print('FAIL: Manifest Path column missing from table header')
    sys.exit(1)
print('PASS: Table has Manifest Path column')

# 2. Parse table rows and verify VERIFIED criteria
fail = False
verified_count = 0
header_cols = [c.strip() for c in table_header.split('|')[1:-1]]
manifest_idx = header_cols.index('Manifest Path')
status_idx = header_cols.index('Status')

for i, line in enumerate(lines, 1):
    if not line.startswith('|') or '---|---' in line or '| Evidence ID |' in line:
        continue
    cols = [c.strip() for c in line.split('|')[1:-1]]
    if len(cols) != len(header_cols):
        continue
    ev_id = cols[0]
    status = cols[status_idx]
    m_path_str = cols[manifest_idx]

    if 'VERIFIED' in status.upper():
        verified_count += 1
        if m_path_str in ('', 'NONE', 'PENDING', '-'):
            print(f'FAIL: {ev_id} on line {i} marked VERIFIED but has no Manifest Path')
            fail = True
            continue
        m_file = pathlib.Path(m_path_str)
        if not m_file.exists():
            print(f'FAIL: {ev_id} manifest not found at {m_path_str}')
            fail = True
            continue
        try:
            m_data = json.loads(m_file.read_text(encoding='utf-8'))
            raw_paths = m_data.get('raw_artifact_paths', [])
            if not raw_paths:
                print(f'FAIL: {ev_id} manifest has empty raw_artifact_paths')
                fail = True
                continue
            for rp in raw_paths:
                artifact_file = m_file.parent / rp
                if not artifact_file.exists():
                    print(f'FAIL: {ev_id} raw artifact {artifact_file} does not exist')
                    fail = True
        except Exception as e:
            print(f'FAIL: {ev_id} manifest read error: {e}')
            fail = True

if fail:
    sys.exit(1)
print(f'PASS: AC-AR-030-01 & AC-AR-030-02: {verified_count} VERIFIED packages all have verified on-disk manifests and raw artifacts')

# 3. Check reference to TEST-COLLECTION-MANIFEST.txt
if 'TEST-COLLECTION-MANIFEST.txt' not in content:
    print('FAIL: EVIDENCE-INDEX.md does not reference TEST-COLLECTION-MANIFEST.txt')
    sys.exit(1)
print('PASS: AC-AR-030-03: test count references TEST-COLLECTION-MANIFEST.txt')

print('ALL EVIDENCE INDEX CHECKS PASS')
"
```

EXPECTED: exit code 0 and output `ALL EVIDENCE INDEX CHECKS PASS`.

## Binary acceptance criteria

- `AC-AR-030-01`: PASS only if every row in `execution/evidence/EVIDENCE-INDEX.md` with `VERIFIED` in its Status column has a `Manifest Path` pointing to an existing `manifest.json` file containing non-empty `raw_artifact_paths`.
- `AC-AR-030-02`: PASS only if no evidence package in `execution/evidence/EVIDENCE-INDEX.md` is marked with `VERIFIED` status without its referenced raw artifact files physically existing on disk.
- `AC-AR-030-03`: PASS only if `execution/evidence/EVIDENCE-INDEX.md` explicitly references `TEST-COLLECTION-MANIFEST.txt` for authoritative test counts.

## Postconditions

- `execution/evidence/EVIDENCE-INDEX.md` contains honest, verifiable evidence statuses.
- `Manifest Path` column added to Master Evidence Index Table.
- Test counts reference `TEST-COLLECTION-MANIFEST.txt`.
- Verification script exits 0.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Concrete objective: rebuild table with manifest paths and real artifact statuses |
| Dependency clarity | 2 | Dependencies AR-003 and AR-029 defined; terminal task (UNLOCKS: NONE) |
| File boundary clarity | 2 | Single file in WRITE_SET (`execution/evidence/EVIDENCE-INDEX.md`) |
| Contract clarity | 2 | Column specification, status transition rules, and verification checks fully defined |
| Failure behavior | 2 | Any unbacked VERIFIED status fails verification script with exit 1 |
| Security/tenancy | 2 | Eliminates false-green governance claims per AC-014 and INV-REL-002 |
| Testability | 2 | Hermetic script checks table columns, manifest existence, and raw artifact paths |
| Verification | 2 | Single python command, exit 0 |
| Acceptance criteria | 2 | 3 machine-verifiable criteria |
| Reasoning independence | 2 | Status assignment strictly governed by physical filesystem artifact existence |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Leave unqualified `VERIFIED` status on any package lacking on-disk raw artifacts and manifests.
- Use fabricated or mock SHA-256 hashes.
- Introduce hardcoded test numbers conflicting with `TEST-COLLECTION-MANIFEST.txt`.

## Required executor report

```text
TASK TASK-AR-030 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: NONE
FILES MODIFIED: execution/evidence/EVIDENCE-INDEX.md
UNEXPECTED FILES: NONE
TESTS: <verification script output>
COMMANDS AND EXIT CODES: <command> → <exit code>
ACCEPTANCE: AC-AR-030-01: PASS|FAIL, AC-AR-030-02: PASS|FAIL, AC-AR-030-03: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: NONE (Milestone Complete)
```
