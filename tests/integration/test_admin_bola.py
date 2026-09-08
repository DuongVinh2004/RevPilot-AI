"""
RevPilot AI — Integration Tests for Admin Export Tenant Binding / BOLA Prevention (TASK-AR-024)
Enforces INV-TEN-002 (strict tenant isolation) and AC-AR-024-01/02.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest


@pytest.fixture
def bola_test_client():
    from fastapi.testclient import TestClient
    from apps.api.main import app

    tenant_alpha = "tnt_alpha_corp"
    tenant_beta = "tnt_beta_adversary"

    # Issue token for tenant admin of Alpha Corp
    token_tenant_admin = "token_usr_tenant_admin_alpha"
    app.state.auth_adapter.issue_test_token(
        token_tenant_admin,
        sub="usr_tenant_admin_alpha",
        tenant_id=tenant_alpha,
        roles=frozenset(["TENANT_ADMIN"]),
    )

    # Issue token for system admin
    token_sys_admin = "token_usr_sys_admin_global"
    app.state.auth_adapter.issue_test_token(
        token_sys_admin,
        sub="usr_sys_admin_global",
        tenant_id="tnt_system_admin",
        roles=frozenset(["SYSTEM_ADMIN", "ADMIN"]),
    )

    # Ensure mock tenant_repo is present
    mock_repo = MagicMock()
    app.state.tenant_repo = mock_repo

    client = TestClient(app)
    yield client, token_tenant_admin, token_sys_admin, tenant_alpha, tenant_beta

    if hasattr(app.state, "tenant_repo"):
        delattr(app.state, "tenant_repo")


def test_tenant_admin_export_own_tenant_succeeds(bola_test_client):
    """Tenant admin exporting their own tenant returns HTTP 202."""
    client, token_tenant_admin, _, tenant_alpha, _ = bola_test_client
    res = client.post(
        f"/api/v1/admin/tenants/{tenant_alpha}/exports",
        headers={"Authorization": f"Bearer {token_tenant_admin}"},
    )
    assert res.status_code == 202
    data = res.json()
    assert data["tenant_id"] == tenant_alpha
    assert data["status"] == "EXPORTING"
    assert "export_id" in data


def test_tenant_admin_export_other_tenant_returns_403(bola_test_client):
    """AC-AR-024-01: Tenant admin exporting another tenant's data returns HTTP 403 with CROSS_TENANT_ACCESS_FORBIDDEN."""
    client, token_tenant_admin, _, _, tenant_beta = bola_test_client
    res = client.post(
        f"/api/v1/admin/tenants/{tenant_beta}/exports",
        headers={"Authorization": f"Bearer {token_tenant_admin}"},
    )
    assert res.status_code == 403
    data = res.json()
    assert "detail" in data
    assert data["detail"]["code"] == "CROSS_TENANT_ACCESS_FORBIDDEN"
    assert "Tenant admin cannot export data belonging to another tenant" in data["detail"]["message"]


def test_system_admin_export_any_tenant_succeeds(bola_test_client):
    """System admin exporting any tenant returns HTTP 202."""
    client, _, token_sys_admin, _, tenant_beta = bola_test_client
    res = client.post(
        f"/api/v1/admin/tenants/{tenant_beta}/exports",
        headers={"Authorization": f"Bearer {token_sys_admin}"},
    )
    assert res.status_code == 202
    data = res.json()
    assert data["tenant_id"] == tenant_beta
    assert data["status"] == "EXPORTING"
    assert "export_id" in data


def test_unauthenticated_export_returns_401(bola_test_client):
    """Missing token returns HTTP 401 Unauthorized."""
    client, _, _, tenant_alpha, _ = bola_test_client
    res = client.post(f"/api/v1/admin/tenants/{tenant_alpha}/exports")
    assert res.status_code == 401
