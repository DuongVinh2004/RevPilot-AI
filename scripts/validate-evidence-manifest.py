#!/usr/bin/env python3
"""
scripts/validate-evidence-manifest.py — Offline hermetic validator for evidence package manifests.
Enforces INV-REL-002 and Anti-Fabrication Invariant AC-014.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

REQUIRED_FIELDS = [
    "criterion_ids",
    "raw_artifact_paths",
    "sha256_hashes",
    "run_id",
    "timestamps",
    "environment_id",
    "command",
    "tool_versions",
    "owner",
    "reviewer",
    "conclusion",
]

ISO8601_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
SHA256_REGEX = re.compile(r"^[0-9a-f]{64}$")
VALID_CONCLUSIONS = {"PASS", "FAIL", "INCONCLUSIVE"}
FORBIDDEN_PLACEHOLDERS = {"TODO", "TBD", "FIXME"}


def validate_manifest(manifest_path: Path, template_mode: bool = False, check_artifacts: bool = False) -> list[str]:
    errors = []

    if not manifest_path.exists():
        return [f"ERR_MANIFEST_MISSING: File not found: {manifest_path}"]

    try:
        content = manifest_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return [f"ERR_MANIFEST_INVALID_JSON: Failed to parse JSON: {exc}"]
    except Exception as exc:
        return [f"ERR_MANIFEST_READ_FAILED: {exc}"]

    if not isinstance(data, dict):
        return ["ERR_MANIFEST_NOT_OBJECT: Top-level manifest must be a JSON object"]

    # 1. Check all 11 required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"ERR_MANIFEST_MISSING_FIELD: Missing required field '{field}'")

    if errors:
        return errors

    # Check for forbidden placeholders in non-template mode
    if not template_mode:
        for k, v in data.items():
            str_repr = json.dumps(v)
            for placeholder in FORBIDDEN_PLACEHOLDERS:
                if placeholder in str_repr:
                    errors.append(f"ERR_FORBIDDEN_PLACEHOLDER: Field '{k}' contains placeholder '{placeholder}'")

    # 2. criterion_ids
    criterion_ids = data.get("criterion_ids")
    if not isinstance(criterion_ids, list) or len(criterion_ids) == 0:
        errors.append("ERR_INVALID_CRITERION_IDS: 'criterion_ids' must be a non-empty list of strings")
    elif not all(isinstance(c, str) and c.strip() for c in criterion_ids):
        errors.append("ERR_INVALID_CRITERION_IDS: All items in 'criterion_ids' must be non-empty strings")

    # 3. raw_artifact_paths
    raw_artifact_paths = data.get("raw_artifact_paths")
    if not isinstance(raw_artifact_paths, list):
        errors.append("ERR_INVALID_RAW_ARTIFACT_PATHS: 'raw_artifact_paths' must be a list of strings")
    elif not all(isinstance(p, str) for p in raw_artifact_paths):
        errors.append("ERR_INVALID_RAW_ARTIFACT_PATHS: All items in 'raw_artifact_paths' must be strings")

    # 4. sha256_hashes
    sha256_hashes = data.get("sha256_hashes")
    if not isinstance(sha256_hashes, dict):
        errors.append("ERR_INVALID_SHA256_HASHES: 'sha256_hashes' must be an object/dict")
    else:
        for k, v in sha256_hashes.items():
            if not isinstance(v, str) or not SHA256_REGEX.match(v):
                errors.append(
                    f"ERR_INVALID_SHA256_HASH: Hash for '{k}' must be a 64-character lowercase hex string"
                )

    # 5. timestamps
    timestamps = data.get("timestamps")
    if not isinstance(timestamps, dict):
        errors.append("ERR_INVALID_TIMESTAMPS: 'timestamps' must be an object with 'started_at' and 'completed_at'")
    else:
        started_at = timestamps.get("started_at")
        completed_at = timestamps.get("completed_at")
        if not isinstance(started_at, str) or not ISO8601_REGEX.match(started_at):
            errors.append(f"ERR_INVALID_TIMESTAMP: 'timestamps.started_at' ({started_at!r}) must be ISO-8601 formatted")
        if not isinstance(completed_at, str) or not ISO8601_REGEX.match(completed_at):
            errors.append(f"ERR_INVALID_TIMESTAMP: 'timestamps.completed_at' ({completed_at!r}) must be ISO-8601 formatted")

    # 6. run_id, environment_id, command, owner, reviewer
    for str_field in ["run_id", "environment_id", "command", "owner", "reviewer"]:
        val = data.get(str_field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"ERR_INVALID_FIELD: '{str_field}' must be a non-empty string")

    # 7. tool_versions
    tool_versions = data.get("tool_versions")
    if not isinstance(tool_versions, dict):
        errors.append("ERR_INVALID_TOOL_VERSIONS: 'tool_versions' must be an object")

    # 8. conclusion
    conclusion = data.get("conclusion")
    if conclusion not in VALID_CONCLUSIONS:
        errors.append(
            f"ERR_INVALID_CONCLUSION: 'conclusion' must be one of {sorted(VALID_CONCLUSIONS)}, got {conclusion!r}"
        )

    # 9. check_artifacts if requested
    if check_artifacts and isinstance(raw_artifact_paths, list):
        base_dir = manifest_path.parent
        for rel_path in raw_artifact_paths:
            artifact_file = base_dir / rel_path
            if not artifact_file.exists():
                errors.append(f"ERR_ARTIFACT_NOT_FOUND: Raw artifact '{rel_path}' not found at {artifact_file}")
                continue
            if isinstance(sha256_hashes, dict):
                expected_hash = sha256_hashes.get(rel_path)
                if not expected_hash:
                    errors.append(f"ERR_MISSING_HASH: No hash recorded for artifact '{rel_path}'")
                    continue
                computed_hash = hashlib.sha256(artifact_file.read_bytes()).hexdigest().lower()
                if computed_hash != expected_hash.lower():
                    errors.append(
                        f"ERR_ARTIFACT_HASH_MISMATCH: Artifact '{rel_path}' expected hash {expected_hash} but computed {computed_hash}"
                    )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Evidence Package Manifest Schema & Artifacts")
    parser.add_argument("--manifest", required=True, help="Path to manifest.json file")
    parser.add_argument(
        "--check-artifacts",
        action="store_true",
        default=False,
        help="Check existence and SHA-256 hashes of physical artifacts",
    )
    parser.add_argument(
        "--template",
        action="store_true",
        default=False,
        help="Validate manifest in template mode (allows template fixture values)",
    )

    args = parser.parse_args()
    manifest_path = Path(args.manifest)

    errors = validate_manifest(
        manifest_path=manifest_path,
        template_mode=args.template,
        check_artifacts=args.check_artifacts,
    )

    if errors:
        print(f"FAIL: Evidence manifest validation failed for {manifest_path}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print(f"PASS: Evidence manifest {manifest_path} is valid.")
    sys.exit(0)


if __name__ == "__main__":
    main()
