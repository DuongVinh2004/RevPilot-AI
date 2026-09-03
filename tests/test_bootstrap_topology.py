import re
import sys
from pathlib import Path
import tomllib


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_DIRECTORIES = [
    "apps/api",
    "apps/web",
    "apps/workflow-worker",
    "apps/ingestion-worker",
    "apps/ml-worker",
    "packages/backend/src/revpilot/shared",
    "packages/backend/src/revpilot/modules",
    "packages/backend/tests",
    "packages/contracts",
    "packages/web-client",
    "tests/contract",
    "tests/integration",
    "tests/e2e",
    "tests/security",
    "tests/tenancy",
    "tests/recovery",
    "tests/performance",
    "tests/ai-evals",
    "config/schemas",
    "config/examples",
    "infra/local",
    "infra/environments",
    "infra/policies",
    "scripts",
    "generated",
]

ROOT_MANIFESTS = [
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    "pyproject.toml",
    "package.json",
    "config/examples/env.example",
]

FORBIDDEN_SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",
    r"ghp_[a-zA-Z0-9]{36,}",
    r"AKIA[0-9A-Z]{16}",
    r"(?i)password\s*=\s*['\"][^'\"]+['\"]",
]


def test_python_runtime_version():
    """Verify runtime Python version is at least 3.12."""
    assert sys.version_info >= (3, 12), (
        f"Python 3.12+ required, current is {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )


def test_canonical_directories_exist():
    """Verify all canonical directories defined in REPOSITORY-TOPOLOGY.md exist."""
    for rel_dir in CANONICAL_DIRECTORIES:
        target_path = WORKSPACE_ROOT / rel_dir
        assert target_path.exists(), f"Missing required directory: {rel_dir}"
        assert target_path.is_dir(), f"Expected directory but found file: {rel_dir}"


def test_root_manifests_exist():
    """Verify all root manifests and configs exist."""
    for rel_manifest in ROOT_MANIFESTS:
        target_path = WORKSPACE_ROOT / rel_manifest
        assert target_path.exists(), f"Missing required manifest file: {rel_manifest}"
        assert target_path.is_file(), f"Expected file: {rel_manifest}"


def test_pyproject_toml_configuration():
    """Verify pyproject.toml exists and requires Python >= 3.12."""
    pyproject_path = WORKSPACE_ROOT / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml not found"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project_meta = data.get("project", {})
    requires_python = project_meta.get("requires-python", "")
    assert requires_python == ">=3.12", f"Unexpected requires-python: {requires_python}"
    assert project_meta.get("name") == "revpilot-backend"


def test_env_example_contains_no_secrets():
    """Verify config/examples/env.example contains safe placeholders and no real secrets."""
    env_example_path = WORKSPACE_ROOT / "config/examples/env.example"
    assert env_example_path.exists(), "config/examples/env.example not found"

    content = env_example_path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        assert not matches, f"Forbidden secret pattern matched in env.example: {matches}"

    assert "ACTION_EXECUTION_MODE=dry_run" in content
    assert "placeholder_dev_pw" in content
