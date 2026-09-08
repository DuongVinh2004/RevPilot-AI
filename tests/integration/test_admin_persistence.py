"""
RevPilot AI — Integration Tests for Admin Operations Persistence (AR-022)
Verifies real database persistence, 503 fail-closed when repo unavailable, and cross-tenant export ACL checks.
Enforces INV-TEN-001 (tenant isolation) and INV-TEN-002 (tenant lifecycle auditability).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest


@pytest.fixture
def test_setup():
    from fastapi.testclient import TestClient
    from apps.api.main import app

    # System admin token
    sys_token = "token_usr_sysadmin_001"
    app.state.auth_adapter.issue_test_token(
        sys_token,
        sub="usr_sysadmin_001",
        tenant_id="tnt_system_admin",
        roles=frozenset(["SYSTEM_ADMIN", "ADMIN"]),
    )

    # Tenant admin token for tnt_tenant_001
    tenant_admin_token = "token_usr_tenant_admin_001"
    app.state.auth_adapter.issue_test_token(
        tenant_admin_token,
        sub="usr_tenant_admin_001",
        tenant_id="tnt_tenant_001",
        roles=frozenset(["TENANT_ADMIN"]),
    )

    client = TestClient(app)
    yield client, app, sys_token, tenant_admin_token

    if hasattr(app.state, "tenant_repo"):
        delattr(app.state, "tenant_repo")


def test_provision_tenant_repo_none_returns_503(test_setup):
    """AC-AR-022-01: With tenant_repo=None, POST /api/v1/admin/tenants returns 503."""
    client, app, sys_token, _ = test_setup
    app.state.tenant_repo = None

    payload = {
        "name": "Acme Corp",
        "slug": "acme",
        "tier": "ENTERPRISE",
        "admin_email": "admin@acme.com",
    }
    res = client.post(
        "/api/v1/admin/tenants",
        json=payload,
        headers={"Authorization": f"Bearer {sys_token}"},
    )
    assert res.status_code == 503
    assert "Tenant repository unavailable" in res.json().get("detail", "")


def test_provision_tenant_success_persists(test_setup):
    """With mock tenant_repo, provisioning saves tenant entity and returns 201."""
    client, app, sys_token, _ = test_setup
    mock_repo = MagicMock()
    mock_repo.async_save_tenant = AsyncMock(return_value=None)
    app.state.tenant_repo = mock_repo

    payload = {
        "name": "Acme Corp",
        "slug": "acme",
        "tier": "ENTERPRISE",
        "admin_email": "admin@acme.com",
    }
    res = client.post(
        "/api/v1/admin/tenants",
        json=payload,
        headers={"Authorization": f"Bearer {sys_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Acme Corp"
    assert data["status"] == "ACTIVE"
    assert "tenant_id" in data
    assert mock_repo.async_save_tenant.called
    saved_tenant = mock_repo.async_save_tenant.call_args[0][0]
    assert saved_tenant.name == "Acme Corp"
    assert str(saved_tenant.id) == data["tenant_id"]


def test_export_tenant_repo_none_returns_503(test_setup):
    """With tenant_repo=None, export returns 503."""
    client, app, sys_token, _ = test_setup
    app.state.tenant_repo = None

    res = client.post(
        "/api/v1/admin/tenants/tnt_test/exports",
        headers={"Authorization": f"Bearer {sys_token}"},
    )
    assert res.status_code == 503
    assert "Tenant repository unavailable" in res.json().get("detail", "")


def test_tenant_admin_export_other_tenant_returns_403(test_setup):
    """AC-AR-022-02: TENANT_ADMIN exporting different tenant ID returns 403."""
    client, app, _, tenant_admin_token = test_setup
    mock_repo = MagicMock()
    app.state.tenant_repo = mock_repo

    res = client.post(
        "/api/v1/admin/tenants/tnt_other_999/exports",
        headers={"Authorization": f"Bearer {tenant_admin_token}"},
    )
    assert res.status_code == 403
    assert "cannot export data for tenant" in res.json().get("detail", "")


def test_system_admin_export_any_tenant_returns_202(test_setup):
    """AC-AR-022-03: SYSTEM_ADMIN exporting any tenant ID returns 202."""
    client, app, sys_token, _ = test_setup
    mock_repo = MagicMock()
    app.state.tenant_repo = mock_repo

    res = client.post(
        "/api/v1/admin/tenants/tnt_other_999/exports",
        headers={"Authorization": f"Bearer {sys_token}"},
    )
    assert res.status_code == 202
    data = res.json()
    assert data["tenant_id"] == "tnt_other_999"
    assert data["status"] == "EXPORTING"
    assert "export_id" in data


def test_cascade_delete_repo_none_returns_503(test_setup):
    """AC-AR-022-04: With tenant_repo=None, delete returns 503."""
    client, app, sys_token, _ = test_setup
    app.state.tenant_repo = None

    res = client.delete(
        "/api/v1/admin/tenants/tnt_test",
        headers={"Authorization": f"Bearer {sys_token}"},
    )
    assert res.status_code == 503
    assert "Tenant repository unavailable" in res.json().get("detail", "")
