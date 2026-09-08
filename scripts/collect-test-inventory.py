#!/usr/bin/env python3
"""
Standardize Test Count Source-of-Truth from pytest Collection Artifact.
Implements TASK-AR-003 (AC-014 Invariant Compliance).
"""

import sys
import re
import pathlib
import subprocess
from datetime import datetime, timezone


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent

    # 1. Capture commit SHA
    try:
        sha_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = sha_proc.stdout.strip()
    except Exception as e:
        print(f"Error getting git commit SHA: {e}", file=sys.stderr)
        return 1

    # 2. Capture python version
    python_version = sys.version.replace("\n", " ")

    # 3. Capture pytest version
    try:
        ver_proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        pytest_version = (ver_proc.stdout.strip() or ver_proc.stderr.strip()).splitlines()[0].strip()
    except Exception as e:
        print(f"Error getting pytest version: {e}", file=sys.stderr)
        return 1

    # 4. Run pytest collection
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    print(f"Executing: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"pytest collection failed with code {proc.returncode}:\n{proc.stderr}", file=sys.stderr)
        return proc.returncode

    stdout = proc.stdout
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        print("pytest collection output is empty", file=sys.stderr)
        return 1

    match = None
    for line in reversed(lines):
        m = re.search(r"(\d+)\s+tests?\s+collected", line)
        if m:
            match = m
            break

    if not match:
        print(f"Could not parse test count from output. Last line: {lines[-1]}", file=sys.stderr)
        return 1

    test_count = int(match.group(1))
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    manifest_dir = root / "execution" / "evidence"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "TEST-COLLECTION-MANIFEST.txt"

    header = [
        "==================================================",
        "RevPilot AI - Test Collection Manifest",
        "==================================================",
        f"Commit SHA:     {commit_sha}",
        f"Timestamp:      {timestamp}",
        f"Python Version: {python_version}",
        f"Pytest Version: {pytest_version}",
        f"Total Tests:    {test_count} tests collected",
        "==================================================",
        "",
        "--- Raw Pytest Collection Output ---",
        stdout.strip(),
        "",
    ]

    manifest_file.write_text("\n".join(header), encoding="utf-8")
    print(f"Manifest successfully generated at {manifest_file}")
    print(f"Result: {test_count} tests collected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
