"""
RevPilot AI — SCIM Negative Test Matrix (12 Cases)
Conforms to TASK-AR-009, docs/14-iam/IAM-SPEC.md, RFC 7644, and INV-TEN-001.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import pytest


@pytest.fixture
def scim_test_env() -> dict[str, Any]:
    """Test fixture initializing test app with 2 tenants, separate credentials, and repositories."""
    from fastapi.testclient import TestClient
    from apps.api.main import app
    from revpilot.modules.identity.adapters.scim_credential import InMemoryScimCredentialAdapter
    from revpilot.modules.identity.adapters.scim_repository import InMemoryScimUserRepository

    cred_adapter = InMemoryScimCredentialAdapter()
    user_repo = InMemoryScimUserRepository()

    # Tenant A
    cred_adapter.register_credential(
        raw_token="token_scim_tnt_a",
        tenant_id="tnt_scim_a",
        credential_id="cred_scim_a",
    )
    # Tenant B
    cred_adapter.register_credential(
        raw_token="token_scim_tnt_b",
        tenant_id="tnt_scim_b",
        credential_id="cred_scim_b",
    )
    # Expired token
    cred_adapter.register_credential(
        raw_token="token_scim_expired",
        tenant_id="tnt_scim_a",
        credential_id="cred_scim_expired",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    # Revoked / rotated token
    cred_adapter.register_credential(
        raw_token="token_scim_revoked",
        tenant_id="tnt_scim_a",
        credential_id="cred_scim_revoked",
        is_active=False,
    )

    app.state.scim_credential_port = cred_adapter
    app.state.scim_user_repo = user_repo
    app.state.disabled_tenants = set()

    client = TestClient(app)
    return {
        "client": client,
        "cred_adapter": cred_adapter,
        "user_repo": user_repo,
        "app": app,
        "token_a": "token_scim_tnt_a",
        "token_b": "token_scim_tnt_b",
        "tenant_a": "tnt_scim_a",
        "tenant_b": "tnt_scim_b",
        "token_expired": "token_scim_expired",
        "token_revoked": "token_scim_revoked",
    }


@pytest.mark.integration
def test_cross_tenant_token_a_path_b_returns_403(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers = {"Authorization": f"Bearer {scim_test_env['token_a']}"}
    res = client.get(f"/scim/v2/{scim_test_env['tenant_b']}/Users", headers=headers)
    assert res.status_code == 403
    assert "Tenant boundary violation" in res.json()["detail"]["detail"]


@pytest.mark.integration
def test_expired_token_returns_401(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers = {"Authorization": f"Bearer {scim_test_env['token_expired']}"}
    res = client.get(f"/scim/v2/{scim_test_env['tenant_a']}/Users", headers=headers)
    assert res.status_code == 401
    assert "SCIM credential expired" in res.json()["detail"]["detail"]


@pytest.mark.integration
def test_missing_token_returns_401(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    res = client.get(f"/scim/v2/{scim_test_env['tenant_a']}/Users")
    assert res.status_code == 401
    assert "Missing or invalid SCIM Bearer token" in res.json()["detail"]["detail"]


@pytest.mark.integration
def test_invalid_unknown_token_returns_401(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers = {"Authorization": "Bearer token_nonexistent_random_value_12345"}
    res = client.get(f"/scim/v2/{scim_test_env['tenant_a']}/Users", headers=headers)
    assert res.status_code == 401
    assert "Invalid SCIM credential" in res.json()["detail"]["detail"]


@pytest.mark.integration
def test_deactivated_user_get_returns_inactive(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers = {"Authorization": f"Bearer {scim_test_env['token_a']}"}
    tenant_a = scim_test_env["tenant_a"]

    # Create user
    res_post = client.post(
        f"/scim/v2/{tenant_a}/Users",
        json={"userName": "deact.test@example.com"},
        headers=headers,
    )
    assert res_post.status_code == 201
    user_id = res_post.json()["id"]

    # Delete (soft-delete) user
    res_del = client.delete(f"/scim/v2/{tenant_a}/Users/{user_id}", headers=headers)
    assert res_del.status_code == 204

    # GET user returns active: False
    res_get = client.get(f"/scim/v2/{tenant_a}/Users/{user_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["active"] is False


@pytest.mark.integration
def test_duplicate_external_id_returns_409(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers = {"Authorization": f"Bearer {scim_test_env['token_a']}"}
    tenant_a = scim_test_env["tenant_a"]

    # Create user with externalId
    res1 = client.post(
        f"/scim/v2/{tenant_a}/Users",
        json={"userName": "dup1@example.com", "externalId": "ext_duplicate_001"},
        headers=headers,
    )
    assert res1.status_code == 201

    # Attempt duplicate externalId
    res2 = client.post(
        f"/scim/v2/{tenant_a}/Users",
        json={"userName": "dup2@example.com", "externalId": "ext_duplicate_001"},
        headers=headers,
    )
    assert res2.status_code == 409
    assert res2.json()["detail"]["scimType"] == "uniqueness"


@pytest.mark.integration
def test_delete_then_recreate_same_external_id_new_uuid(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers = {"Authorization": f"Bearer {scim_test_env['token_a']}"}
    tenant_a = scim_test_env["tenant_a"]

    # Create first user
    res1 = client.post(
        f"/scim/v2/{tenant_a}/Users",
        json={"userName": "recreate1@example.com", "externalId": "ext_recreate_001"},
        headers=headers,
    )
    assert res1.status_code == 201
    id1 = res1.json()["id"]

    # Deactivate / delete first user
    res_del = client.delete(f"/scim/v2/{tenant_a}/Users/{id1}", headers=headers)
    assert res_del.status_code == 204

    # Re-create user with same externalId
    res2 = client.post(
        f"/scim/v2/{tenant_a}/Users",
        json={"userName": "recreate2@example.com", "externalId": "ext_recreate_001"},
        headers=headers,
    )
    assert res2.status_code == 201
    id2 = res2.json()["id"]

    assert id1 != id2
    # Verify old user is inactive, new user is active
    get1 = client.get(f"/scim/v2/{tenant_a}/Users/{id1}", headers=headers)
    assert get1.status_code == 200
    assert get1.json()["active"] is False

    get2 = client.get(f"/scim/v2/{tenant_a}/Users/{id2}", headers=headers)
    assert get2.status_code == 200
    assert get2.json()["active"] is True


@pytest.mark.integration
def test_list_users_tenant_a_excludes_tenant_b(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers_a = {"Authorization": f"Bearer {scim_test_env['token_a']}"}
    headers_b = {"Authorization": f"Bearer {scim_test_env['token_b']}"}
    tenant_a = scim_test_env["tenant_a"]
    tenant_b = scim_test_env["tenant_b"]

    # Create user in tenant A
    client.post(f"/scim/v2/{tenant_a}/Users", json={"userName": "user_a@example.com"}, headers=headers_a)
    # Create user in tenant B
    client.post(f"/scim/v2/{tenant_b}/Users", json={"userName": "user_b@example.com"}, headers=headers_b)

    # List tenant A
    res_a = client.get(f"/scim/v2/{tenant_a}/Users", headers=headers_a)
    assert res_a.status_code == 200
    users_a = [u["userName"] for u in res_a.json()["Resources"]]
    assert "user_a@example.com" in users_a
    assert "user_b@example.com" not in users_a

    # List tenant B
    res_b = client.get(f"/scim/v2/{tenant_b}/Users", headers=headers_b)
    assert res_b.status_code == 200
    users_b = [u["userName"] for u in res_b.json()["Resources"]]
    assert "user_b@example.com" in users_b
    assert "user_a@example.com" not in users_b


@pytest.mark.integration
def test_patch_user_other_tenant_returns_403_or_404(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers_a = {"Authorization": f"Bearer {scim_test_env['token_a']}"}
    headers_b = {"Authorization": f"Bearer {scim_test_env['token_b']}"}
    tenant_a = scim_test_env["tenant_a"]
    tenant_b = scim_test_env["tenant_b"]

    # Create user in tenant B
    res_b = client.post(f"/scim/v2/{tenant_b}/Users", json={"userName": "target_b@example.com"}, headers=headers_b)
    user_b_id = res_b.json()["id"]

    patch_payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "replace", "path": "active", "value": False}],
    }

    # Attempt 1: Token A accessing Tenant B route -> 403 Forbidden
    res_cross_path = client.patch(f"/scim/v2/{tenant_b}/Users/{user_b_id}", json=patch_payload, headers=headers_a)
    assert res_cross_path.status_code == 403

    # Attempt 2: Token A accessing Tenant A route with Tenant B's user_id -> 404 Not Found
    res_cross_id = client.patch(f"/scim/v2/{tenant_a}/Users/{user_b_id}", json=patch_payload, headers=headers_a)
    assert res_cross_id.status_code == 404


@pytest.mark.integration
def test_pagination_total_results_consistent(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers = {"Authorization": f"Bearer {scim_test_env['token_a']}"}
    tenant_a = scim_test_env["tenant_a"]

    # Create 5 users
    for i in range(5):
        client.post(f"/scim/v2/{tenant_a}/Users", json={"userName": f"page_user_{i}@example.com"}, headers=headers)

    # Page 1 (items 1-2)
    p1 = client.get(f"/scim/v2/{tenant_a}/Users?startIndex=1&count=2", headers=headers).json()
    assert p1["totalResults"] == 5
    assert len(p1["Resources"]) == 2

    # Page 2 (items 3-4)
    p2 = client.get(f"/scim/v2/{tenant_a}/Users?startIndex=3&count=2", headers=headers).json()
    assert p2["totalResults"] == 5
    assert len(p2["Resources"]) == 2

    # Page 3 (item 5)
    p3 = client.get(f"/scim/v2/{tenant_a}/Users?startIndex=5&count=2", headers=headers).json()
    assert p3["totalResults"] == 5
    assert len(p3["Resources"]) == 1


@pytest.mark.integration
def test_disabled_tenant_returns_403(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers = {"Authorization": f"Bearer {scim_test_env['token_a']}"}
    tenant_a = scim_test_env["tenant_a"]

    # Mark tenant as disabled
    scim_test_env["app"].state.disabled_tenants.add(tenant_a)
    try:
        res = client.get(f"/scim/v2/{tenant_a}/Users", headers=headers)
        assert res.status_code == 403
        assert "disabled" in res.json()["detail"]["detail"].lower()
    finally:
        scim_test_env["app"].state.disabled_tenants.discard(tenant_a)


@pytest.mark.integration
def test_rotated_credential_old_token_returns_401(scim_test_env: dict[str, Any]) -> None:
    client = scim_test_env["client"]
    headers = {"Authorization": f"Bearer {scim_test_env['token_revoked']}"}
    res = client.get(f"/scim/v2/{scim_test_env['tenant_a']}/Users", headers=headers)
    assert res.status_code == 401
    assert "SCIM credential revoked" in res.json()["detail"]["detail"]
