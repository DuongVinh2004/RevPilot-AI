"""
RevPilot AI — TC-P07-015: SCIM Rapid Deprovisioning & Session Revocation Test
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §4.2
Conforms to INV-IAM-001, INV-TEN-002, and NFR-SEC-001.
"""

import time
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.modules.iam.scim import (
    ScimProvisioningService,
    ScimEndpoints,
    ScimConflictError,
    ScimUserNotFoundError,
)


def test_scim_user_lifecycle_conflict_and_rapid_deprovisioning():
    """
    TC-P07-015: SCIM 2.0 provisioning rejects duplicate users with 409 SCIM_CONFLICT.
    User deprovisioning immediately terminates active sessions within 1000ms (INV-IAM-001).
    """
    active_sessions: dict[str, str] = {}

    def mock_session_revoker(tenant_id: TenantId, user_id: str) -> None:
        # Invalidate active session tokens for user
        tokens_to_remove = [tok for tok, uid in active_sessions.items() if uid == user_id]
        for tok in tokens_to_remove:
            del active_sessions[tok]

    scim_service = ScimProvisioningService(session_revoker=mock_session_revoker)
    endpoints = ScimEndpoints(service=scim_service)
    tenant_id = TenantId.generate()

    # 1. Provision New User via SCIM REST Endpoint: 201 Created
    user_payload = {
        "userName": "alice.analyst@enterprise.com",
        "emails": [{"value": "alice.analyst@enterprise.com", "primary": True}],
        "active": True,
        "roles": ["analyst"],
    }
    status_code, user_resp = endpoints.post_user(tenant_id, user_payload)
    assert status_code == 201
    user_id = user_resp["id"]
    assert user_id.startswith("usr_")
    assert user_resp["active"] is True

    # Register an active user session token
    user_token = f"sess_token_{user_id}"
    active_sessions[user_token] = user_id
    assert user_token in active_sessions

    # 2. Duplicate Username Rejection: 409 Conflict (SCIM_CONFLICT)
    dup_status, dup_resp = endpoints.post_user(tenant_id, user_payload)
    assert dup_status == 409
    assert dup_resp["status"] == "409"
    assert dup_resp["scimType"] == "uniqueness"

    # 3. Rapid Deprovisioning via SCIM PATCH: active = False
    start = time.perf_counter()
    patch_payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "replace", "path": "active", "value": False}],
    }
    patch_status, patch_resp = endpoints.patch_user(tenant_id, user_id, patch_payload)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # Invariants: 200 OK, active is False, session terminated in < 1000ms
    assert patch_status == 200
    assert patch_resp["active"] is False
    assert elapsed_ms < 1000.0, f"Deprovisioning latency {elapsed_ms}ms exceeded 1000ms budget!"

    # Active session revoked immediately (INV-IAM-001)
    assert user_token not in active_sessions
    assert scim_service.is_user_active(tenant_id, user_id) is False

    # 4. Group Sync updates member roles
    scim_service.sync_group_members(
        tenant_id=tenant_id,
        group_id="SecOps_Admins",
        member_ids=[user_id],
        role_binding="tenant_admin",
    )
    user_record = scim_service._users[str(tenant_id)][user_id]
    assert "tenant_admin" in user_record.roles
