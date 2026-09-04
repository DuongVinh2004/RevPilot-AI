"""
RevPilot AI — SCIM 2.0 REST Endpoints Simulator
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §4.1
Conforms to RFC 7643 / RFC 7644.
"""

from __future__ import annotations
from typing import Any

from revpilot.shared.identifiers import TenantId
from revpilot.modules.iam.scim.service import (
    ScimProvisioningService,
    ScimConflictError,
    ScimUserNotFoundError,
)


class ScimEndpoints:
    """
    REST router simulating SCIM 2.0 protocol endpoints.
    Handles HTTP status codes, ETags, and JSON serialization.
    """

    def __init__(self, service: ScimProvisioningService) -> None:
        self.service = service

    def post_user(self, tenant_id: TenantId, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """POST /scim/v2/{tenant_id}/Users"""
        try:
            record = self.service.create_user(tenant_id, payload)
            return 201, {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "id": record.id,
                "userName": record.userName,
                "emails": [{"value": record.email, "primary": True}],
                "active": record.active,
                "roles": list(record.roles),
                "meta": {
                    "resourceType": "User",
                    "created": record.created_at.isoformat(),
                    "lastModified": record.updated_at.isoformat(),
                    "version": f'W/"{record.version}"',
                },
            }
        except ScimConflictError as err:
            return 409, {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "status": "409",
                "scimType": "uniqueness",
                "detail": err.message,
            }

    def get_user(self, tenant_id: TenantId, user_id: str) -> tuple[int, dict[str, Any]]:
        """GET /scim/v2/{tenant_id}/Users/{id}"""
        tenant_store = self.service._users.get(str(tenant_id), {})
        record = tenant_store.get(user_id)
        if record is None:
            return 404, {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "status": "404",
                "detail": f"User {user_id} not found",
            }
        return 200, {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": record.id,
            "userName": record.userName,
            "emails": [{"value": record.email, "primary": True}],
            "active": record.active,
            "roles": list(record.roles),
            "meta": {"version": f'W/"{record.version}"'},
        }

    def patch_user(
        self,
        tenant_id: TenantId,
        user_id: str,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        """PATCH /scim/v2/{tenant_id}/Users/{id}"""
        try:
            ops = payload.get("Operations", [])
            updated = self.service.update_user(tenant_id, user_id, ops)
            return 200, {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "id": updated.id,
                "userName": updated.userName,
                "active": updated.active,
                "meta": {"version": f'W/"{updated.version}"'},
            }
        except ScimUserNotFoundError as err:
            return 404, {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "status": "404",
                "detail": err.message,
            }

    def delete_user(self, tenant_id: TenantId, user_id: str) -> tuple[int, dict[str, Any] | None]:
        """DELETE /scim/v2/{tenant_id}/Users/{id}"""
        try:
            self.service.deprovision_user(tenant_id, user_id)
            return 204, None
        except ScimUserNotFoundError as err:
            return 404, {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "status": "404",
                "detail": err.message,
            }
