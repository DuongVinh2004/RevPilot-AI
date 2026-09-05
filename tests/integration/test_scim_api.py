"""
RevPilot AI — Integration Tests for SCIM 2.0 API Gateway (RFC 7643 / RFC 7644)
Conforms to docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §4.1 and INV-IAM-001.
"""

from __future__ import annotations
from typing import Any
import pytest


@pytest.fixture
def client() -> Any:
    """Fixture providing initialized FastAPI test client without preloading at collection time."""
    from fastapi.testclient import TestClient
    from apps.api.main import app
    return TestClient(app)


def test_scim_api_user_lifecycle(client: Any):
    headers = {"Authorization": "Bearer token_usr_admin_001_tnt_dev_001"}
    tenant_id = "tnt_dev_001"

    # 1. Create User via SCIM POST
    create_payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "operator.jane@example.com",
        "displayName": "Jane Operator",
        "emails": [{"value": "operator.jane@example.com", "primary": True}],
        "roles": ["OPERATOR"],
        "active": True,
    }

    res_post = client.post(f"/scim/v2/{tenant_id}/Users", json=create_payload, headers=headers)
    assert res_post.status_code == 201
    user_data = res_post.json()
    user_id = user_data["id"]
    assert user_data["userName"] == "operator.jane@example.com"
    assert user_data["active"] is True

    # 2. Duplicate User Creation -> 409 Conflict (uniqueness)
    res_dup = client.post(f"/scim/v2/{tenant_id}/Users", json=create_payload, headers=headers)
    assert res_dup.status_code == 409
    error_detail = res_dup.json()["detail"]
    assert error_detail["scimType"] == "uniqueness"

    # 3. Get User by ID
    res_get = client.get(f"/scim/v2/{tenant_id}/Users/{user_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == user_id

    # 4. List Users via SCIM ListResponse
    res_list = client.get(f"/scim/v2/{tenant_id}/Users", headers=headers)
    assert res_list.status_code == 200
    list_body = res_list.json()
    assert list_body["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    assert list_body["totalResults"] >= 1
    matching = [u for u in list_body["Resources"] if u["id"] == user_id]
    assert len(matching) == 1

    # 5. Patch User -> Rapid Deprovisioning (active = False)
    patch_payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {"op": "replace", "path": "active", "value": False},
        ],
    }
    res_patch = client.patch(f"/scim/v2/{tenant_id}/Users/{user_id}", json=patch_payload, headers=headers)
    assert res_patch.status_code == 200
    assert res_patch.json()["active"] is False

    # 6. Delete User -> 204 No Content
    res_del = client.delete(f"/scim/v2/{tenant_id}/Users/{user_id}", headers=headers)
    assert res_del.status_code == 204


def test_scim_api_groups_sync(client: Any):
    headers = {"Authorization": "Bearer token_usr_admin_001_tnt_dev_001"}
    tenant_id = "tnt_dev_001"

    # 1. Sync / Create Group
    group_payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": "SecurityOps",
        "members": [{"value": "usr_001"}, {"value": "usr_002"}],
    }
    res_post = client.post(f"/scim/v2/{tenant_id}/Groups", json=group_payload, headers=headers)
    assert res_post.status_code == 201
    group_data = res_post.json()
    assert group_data["displayName"] == "SecurityOps"
    assert len(group_data["members"]) == 2

    # 2. List Groups
    res_list = client.get(f"/scim/v2/{tenant_id}/Groups", headers=headers)
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    matching = [g for g in list_data["Resources"] if g["displayName"] == "SecurityOps"]
    assert len(matching) == 1
