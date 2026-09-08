# TASK-AR-029 — Evidence Package Standard Template and Manifest Schema

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 18
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: EVIDENCE-REBUILD
FEATURE: EVIDENCE-TEMPLATE
COMPLEXITY: S
REASONING_LOAD: LOW
READINESS_SCORE: 20/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-016, AR-009, AR-025
UNLOCKS: AR-030

## Objective and rationale

OBJECTIVE: Create a standardized evidence package directory structure and canonical `manifest.json` schema containing exactly 11 required fields (`criterion_ids`, `raw_artifact_paths`, `sha256_hashes`, `run_id`, `timestamps`, `environment_id`, `command`, `tool_versions`, `owner`, `reviewer`, `conclusion`), accompanying documentation in `README.md`, and an automated offline validator in `scripts/validate-evidence-manifest.py`.

BUSINESS RATIONALE: Zero-trust audit finding P0-GOV-001 proved that evidence packages across the repository lacked raw machine artifacts, uniform provenance metadata, and cryptographic integrity verification. This enabled simulated test runs to be relabeled as verified production evidence without empirical backing. Establishing a standard evidence package template with machine-enforced schema validation guarantees that all future verification artifacts are auditable, tamper-evident, and compliant with INV-REL-002 and AC-014.

ARCHITECTURAL OWNER: SRE Lead, Compliance Architect

ARCHITECTURAL CONTEXT: INV-REL-002 (production acceptance never granted on documentation alone), AC-014 (anti-fabrication invariant), DEFINITION-OF-DONE.md §Stage D.

## Canonical specification references

- `execution/DEFINITION-OF-DONE.md#stage-d-evidence-complete`
- `execution/evidence/EVIDENCE-INDEX.md`
- `AGENTS.md#anti-fabrication-invariant-ac-014`
- RFC 7946 / JSON Schema Draft 2020-12

If references conflict, return BLOCKED.

## Preconditions

- AR-016 PASS (Approval/Action negative test matrix complete).
- AR-009 PASS (SCIM negative test matrix complete).
- AR-025 PASS (Drill/recovery test baseline established).
- Directory `execution/evidence/` exists.

## Change boundary

READ_SET:
- `execution/evidence/EVIDENCE-INDEX.md`
- `execution/DEFINITION-OF-DONE.md`
- `AGENTS.md`

WRITE_SET:
- `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json`
- `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/README.md`
- `scripts/validate-evidence-manifest.py`

CREATE:
- `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json`
- `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/README.md`
- `scripts/validate-evidence-manifest.py`

MODIFY: NONE

DO_NOT_MODIFY:
- `execution/evidence/EVIDENCE-INDEX.md` (reserved for AR-030)
- `tests/**`
- Any file outside WRITE_SET

EXPECTED CHANGE SET: 3 new files created: template manifest, template documentation, and validation script.

## Symbol-level contract

MUST EXPORT/DEFINE:
1. `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json`: JSON document containing exact 11 top-level keys:
   - `criterion_ids`: list of strings (acceptance criterion IDs, e.g. `["AC-AR-001-01"]`)
   - `raw_artifact_paths`: list of strings (paths to raw machine logs/outputs relative to package directory)
   - `sha256_hashes`: object mapping each relative raw artifact path to its 64-char lowercase hex SHA-256 digest
   - `run_id`: string uniquely identifying execution run
   - `timestamps`: object containing `started_at` (ISO-8601 string) and `completed_at` (ISO-8601 string)
   - `environment_id`: string identifying execution environment (e.g., `local-hermetic`, `staging-k8s`)
   - `command`: string representing exact shell command executed
   - `tool_versions`: object mapping tool names to version strings (e.g. `{"python": "3.12.0", "pytest": "9.1.1"}`)
   - `owner`: string designating primary engineer/producer
   - `reviewer`: string designating auditor/reviewer
   - `conclusion`: string enum (`PASS` | `FAIL` | `INCONCLUSIVE`)

2. `scripts/validate-evidence-manifest.py`: CLI script:
   - CLI args: `--manifest <path>` (required), `--check-artifacts` (optional flag, default false for template), `--template` (validates schema conformance of template)
   - Exits 0 if valid; exits 1 with actionable errors on stdout/stderr if any field is missing, misconfigured, or if artifact hashes mismatch.

MUST NOT:
- Omit any of the 11 canonical fields from the manifest schema.
- Allow placeholder strings (e.g. `TODO`, `TBD`, `FIXME`) in completed manifests.
- Import non-standard Python dependencies in `scripts/validate-evidence-manifest.py`.

## Input/output and validation

INPUT: Path to a candidate `manifest.json`.
OUTPUT: Validation report printed to stdout and exit code 0 (PASS) or 1 (FAIL).
INVALID INPUT: Missing file, invalid JSON, missing fields among the 11 required, invalid timestamp format, invalid SHA-256 hash length, invalid conclusion enum value.
VALIDATION RULES:
1. Manifest must contain all 11 required top-level keys.
2. `criterion_ids` must be a non-empty array of strings.
3. `raw_artifact_paths` must be an array of strings.
4. `sha256_hashes` must be an object where every key exists in `raw_artifact_paths` and every value is a 64-character lowercase hexadecimal string (or placeholder for template mode).
5. `timestamps.started_at` and `timestamps.completed_at` must parse as ISO-8601 timestamps.
6. `conclusion` must match `^(PASS|FAIL|INCONCLUSIVE)$`.
STATE TRANSITIONS: NOT APPLICABLE.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `ERR_MANIFEST_MISSING_FIELD` | Manifest missing 1 of 11 required keys | N/A | no | Evidence manifest missing required field | yes | `evidence_validation_errors{code="ERR_MISSING_FIELD"}` |
| `ERR_MANIFEST_INVALID_JSON` | Syntax error parsing manifest.json | N/A | no | Evidence manifest contains invalid JSON | yes | `evidence_validation_errors{code="ERR_INVALID_JSON"}` |
| `ERR_ARTIFACT_HASH_MISMATCH` | Computed SHA-256 does not match recorded | N/A | no | Evidence artifact SHA-256 integrity mismatch | yes | `evidence_validation_errors{code="ERR_HASH_MISMATCH"}` |
| `ERR_INVALID_CONCLUSION` | Conclusion is not PASS/FAIL/INCONCLUSIVE | N/A | no | Invalid conclusion enum in evidence manifest | yes | `evidence_validation_errors{code="ERR_INVALID_CONCLUSION"}` |

## Security contract

AUTHENTICATION: NOT APPLICABLE.
AUTHORIZATION: Repository write access.
TENANT: NOT APPLICABLE.
PII: PROHIBITED — raw artifacts and manifests must never contain PII or unredacted customer data.
SECRET ACCESS: PROHIBITED — credentials and API keys must be scrubbed before hashing.
EXTERNAL ACTION: PROHIBITED — offline hermetic execution only.
DEFAULT: DENY — invalid or unverified manifests reject evidence verification.

## Specialized contracts

DATA CONTRACT: Defines strict JSON schema for evidence manifest files in `execution/evidence/**/manifest.json`.
API CONTRACT: NOT APPLICABLE — no HTTP endpoints.
EVENT CONTRACT: NOT APPLICABLE — no events.
TEMPORAL CONTRACT: NOT APPLICABLE — no workflows.
AGENT CONTRACT: Enforces AC-014: agents cannot declare acceptance without valid manifest.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: NOT APPLICABLE — local deterministic validation.
TIMEOUT: Execution bounded to < 5 seconds per manifest.
IDEMPOTENCY: Idempotent — repeated validation of unchanged files produces identical output and exit code.
LOGGING: Validation messages printed to stdout.
METRICS: NOT APPLICABLE.
FAILURE BEHAVIOR: Validator exits 1 on any schema violation or hash mismatch.
ROLLBACK/COMPENSATION: Delete created files.

## Implementation requirements

1. Create directory `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/`.
2. Create `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json` containing:
   - `criterion_ids`: `["AC-TEMPLATE-01"]`
   - `raw_artifact_paths`: `["raw_logs/console.log"]`
   - `sha256_hashes`: `{"raw_logs/console.log": "0000000000000000000000000000000000000000000000000000000000000000"}`
   - `run_id`: `"run-template-000"`
   - `timestamps`: `{"started_at": "2026-09-08T00:00:00Z", "completed_at": "2026-09-08T00:01:00Z"}`
   - `environment_id`: `"local-hermetic"`
   - `command`: `"python -m pytest ..."`
   - `tool_versions`: `{"python": "3.12.0", "pytest": "9.1.1"}`
   - `owner`: `"SRE Lead"`
   - `reviewer`: `"Security Architect"`
   - `conclusion`: `"PASS"`
3. Create `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/README.md`:
   - Document the lifecycle of an evidence package: capture, hash, manifest generation, review, index registration.
   - Explain each of the 11 fields and acceptable values.
4. Create `scripts/validate-evidence-manifest.py`:
   - Pure standard library Python script (`sys`, `os`, `json`, `hashlib`, `pathlib`, `re`, `argparse`).
   - Implement schema checks for all 11 fields.
   - In `--check-artifacts` mode: verify existence and SHA-256 hash of each referenced artifact.
   - In `--template` mode: verify schema structure and presence of all 11 fields.
5. Verify script exits 0 when run against `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json --template`.

## Tests and evaluations

TESTS REQUIRED:
- Python script testing `validate-evidence-manifest.py` against:
  1. Valid template manifest (must pass).
  2. Manifest missing required keys (must fail).
  3. Manifest with invalid conclusion value (must fail).

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: Validator executes in < 1 second.
MIGRATION REQUIREMENTS: NOT APPLICABLE.

## Verification

COMMANDS:

```text
python -c "
import subprocess, sys

# 1. Run validator on template
cmd = [sys.executable, 'scripts/validate-evidence-manifest.py', '--manifest', 'execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json', '--template']
res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode != 0:
    print(f'FAIL: Validator exited {res.returncode}: {res.stderr}')
    sys.exit(1)
print('PASS: AC-AR-029-02: validation script exits 0 on template')

# 2. Check 11 required fields directly
import json, pathlib
m_path = pathlib.Path('execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json')
data = json.loads(m_path.read_text(encoding='utf-8'))
required_fields = [
    'criterion_ids', 'raw_artifact_paths', 'sha256_hashes',
    'run_id', 'timestamps', 'environment_id', 'command',
    'tool_versions', 'owner', 'reviewer', 'conclusion'
]
missing = [f for f in required_fields if f not in data]
if missing:
    print(f'FAIL: Manifest missing fields: {missing}')
    sys.exit(1)
print(f'PASS: AC-AR-029-01: manifest schema has all 11 fields: {len(required_fields)}/11 verified')
print('ALL EVIDENCE TEMPLATE CHECKS PASS')
"
```

EXPECTED: exit code 0 and output `ALL EVIDENCE TEMPLATE CHECKS PASS`.

## Binary acceptance criteria

- `AC-AR-029-01`: PASS only if `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json` contains all 11 required fields: `criterion_ids`, `raw_artifact_paths`, `sha256_hashes`, `run_id`, `timestamps`, `environment_id`, `command`, `tool_versions`, `owner`, `reviewer`, `conclusion`.
- `AC-AR-029-02`: PASS only if `python scripts/validate-evidence-manifest.py --manifest execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json --template` exits with returncode 0.

## Postconditions

- Standard evidence package template available under `execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/`.
- Manifest validator script available under `scripts/validate-evidence-manifest.py`.
- Unblocks AR-030.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Concrete objective: create template manifest, doc, and validator script |
| Dependency clarity | 2 | Dependencies AR-016, AR-009, AR-025 defined; unblocks AR-030 |
| File boundary clarity | 2 | Exactly 3 CREATE paths, 0 MODIFY |
| Contract clarity | 2 | Exact 11 manifest fields, data types, and validator CLI flags specified |
| Failure behavior | 2 | Missing fields or malformed data immediately exit 1 |
| Security/tenancy | 2 | Cryptographic hash binding prevents fabricated evidence |
| Testability | 2 | Validator testable directly against template and synthetic invalid inputs |
| Verification | 2 | Hermetic python subprocess verification script, exit 0 |
| Acceptance criteria | 2 | 2 machine-verifiable criteria |
| Reasoning independence | 2 | Zero architectural choices; schema and fields explicitly prescribed |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Make architectural decisions, widen scope, refactor opportunistically, upgrade dependencies, or start unlocked work.
- Omit any of the 11 required fields from the manifest schema.
- Add third-party external dependencies for manifest validation.
- Modify `execution/evidence/EVIDENCE-INDEX.md` (reserved for AR-030).

## Required executor report

```text
TASK TASK-AR-029 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/manifest.json, execution/evidence/EVIDENCE-PACKAGE-TEMPLATE/README.md, scripts/validate-evidence-manifest.py
FILES MODIFIED: NONE
UNEXPECTED FILES: NONE
TESTS: <verification script output>
COMMANDS AND EXIT CODES: <command> → <exit code>
ACCEPTANCE: AC-AR-029-01: PASS|FAIL, AC-AR-029-02: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: AR-030
```
