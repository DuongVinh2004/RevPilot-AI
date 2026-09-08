"""
RevPilot AI — Integration Test: Startup Fail-Closed Dependency Contract
Conforms to:
- TASK-AR-004
- docs/14-iam/IAM-SPEC.md#authentication-boundary
- AGENTS.md#1-core-operating-directives
- INV-SEC-001, INV-TEN-001, ADR-0003
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(ROOT / "packages" / "backend" / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest


@pytest.mark.asyncio
async def test_startup_fails_without_database_url_in_production(monkeypatch):
    """AC-AR-004-01: ENVIRONMENT=production without DATABASE_URL must exit non-zero."""
    from apps.api.main import app, lifespan
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        async with lifespan(app):
            pass
    assert "DATABASE_URL is required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_startup_fails_with_invalid_database_url(monkeypatch):
    """AC-AR-004-02: ENVIRONMENT=production with invalid DATABASE_URL must exit non-zero."""
    from apps.api.main import app, lifespan
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid_user:invalid_pass@127.0.0.1:59999/db")

    with pytest.raises(SystemExit) as exc_info:
        async with lifespan(app):
            pass
    assert "Database initialization failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_startup_succeeds_in_test_without_database_url(monkeypatch):
    """AC-AR-004-03: ENVIRONMENT=test without DATABASE_URL starts successfully."""
    from apps.api.main import app, lifespan
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    async with lifespan(app):
        assert getattr(app.state, "auth_adapter", None) is not None


@pytest.mark.asyncio
async def test_startup_fails_with_unknown_environment(monkeypatch):
    """AC-AR-004-01/02: Unknown ENVIRONMENT value must exit non-zero."""
    from apps.api.main import app, lifespan
    monkeypatch.setenv("ENVIRONMENT", "unknown_env_value")

    with pytest.raises(SystemExit) as exc_info:
        async with lifespan(app):
            pass
    assert "Unknown ENVIRONMENT value" in str(exc_info.value)
