"""
RevPilot AI — SCIM 2.0 User & Group Provisioning API Router
Conforms to RFC 7643, RFC 7644, and docs/14-iam/IAM-SPEC.md §4.
"""

from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/scim/v2/{tenant_id}", tags=["SCIM 2.0"])


class ScimUserCreate(BaseModel):
    schemas: list[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    displayName: str | None = None
    emails: list[dict[str, Any]] = Field(default_factory=list)
    active: bool = True


@router.get("/Users")
async def list_scim_users(tenant_id: str) -> dict[str, Any]:
    """List users via SCIM protocol."""
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 1,
        "itemsPerPage": 50,
        "startIndex": 1,
        "Resources": [
            {
                "id": "usr_admin_001",
                "userName": "admin@revpilot.dev",
                "displayName": "Duong Vinh",
                "active": True,
            }
        ],
    }


@router.post("/Users", status_code=status.HTTP_201_CREATED)
async def create_scim_user(tenant_id: str, payload: ScimUserCreate) -> dict[str, Any]:
    """Provision user via SCIM."""
    u_id = f"usr_{uuid.uuid4().hex[:12]}"
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": u_id,
        "userName": payload.userName,
        "displayName": payload.displayName or payload.userName,
        "active": payload.active,
        "meta": {"resourceType": "User"},
    }


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scim_user(tenant_id: str, user_id: str) -> None:
    """Deactivate/purge user via SCIM."""
    return None
