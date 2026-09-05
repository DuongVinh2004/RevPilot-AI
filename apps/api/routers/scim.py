"""
RevPilot AI — SCIM 2.0 User & Group Provisioning API Router
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §4.1, docs/26-api/API-STANDARDS.md §10.5
Conforms to RFC 7643, RFC 7644, and INV-IAM-001.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from revpilot.modules.iam.scim.endpoints import ScimEndpoints
from revpilot.modules.iam.scim.service import ScimProvisioningService
from revpilot.shared.identifiers import TenantId

router = APIRouter(prefix="/scim/v2/{tenant_id}", tags=["SCIM 2.0"])


def get_scim_endpoints(request: Request) -> ScimEndpoints:
    service = getattr(request.app.state, "scim_service", None)
    if service is None:
        auth_adapter = getattr(request.app.state, "auth_adapter", None)

        def session_revoker(tenant_id: TenantId, user_id: str) -> None:
            if auth_adapter and hasattr(auth_adapter, "revoke_session"):
                auth_adapter.revoke_session(f"{tenant_id}:{user_id}")

        service = ScimProvisioningService(session_revoker=session_revoker)
        request.app.state.scim_service = service

    endpoints = getattr(request.app.state, "scim_endpoints", None)
    if endpoints is None or endpoints.service is not service:
        endpoints = ScimEndpoints(service=service)
        request.app.state.scim_endpoints = endpoints

    return endpoints


def verify_scim_bearer(authorization: str = Header(None)) -> str:
    """Validate SCIM bearer authorization token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "status": "401",
                "detail": "Missing or invalid SCIM Bearer token",
            },
        )
    return authorization.split("Bearer ")[1].strip()


class ScimUserCreatePayload(BaseModel):
    schemas: list[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    displayName: str | None = None
    emails: list[dict[str, Any]] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    active: bool = True


class ScimPatchOperation(BaseModel):
    op: str
    path: str | None = None
    value: Any = None


class ScimPatchPayload(BaseModel):
    schemas: list[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    Operations: list[dict[str, Any]]


class ScimGroupCreatePayload(BaseModel):
    schemas: list[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    displayName: str
    members: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/Users")
async def list_scim_users(
    tenant_id: str,
    request: Request,
    start_index: int = 1,
    count: int = 100,
    _: str = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    """List users via SCIM 2.0 ListResponse."""
    endpoints = get_scim_endpoints(request)
    tenant_key = str(TenantId(tenant_id))
    user_store = endpoints.service._users.get(tenant_key, {})
    all_users = list(user_store.values())

    resources = []
    for u in all_users:
        resources.append({
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": u.id,
            "userName": u.userName,
            "emails": [{"value": u.email, "primary": True}],
            "active": u.active,
            "roles": list(u.roles),
            "meta": {
                "resourceType": "User",
                "created": u.created_at.isoformat(),
                "lastModified": u.updated_at.isoformat(),
                "version": f'W/"{u.version}"',
            },
        })

    # Slice pagination
    paginated = resources[start_index - 1 : start_index - 1 + count]

    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(resources),
        "itemsPerPage": count,
        "startIndex": start_index,
        "Resources": paginated,
    }


@router.post("/Users", status_code=status.HTTP_201_CREATED)
async def create_scim_user(
    tenant_id: str,
    payload: ScimUserCreatePayload,
    request: Request,
    response: Response,
    _: str = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    """Provision a new user via SCIM 2.0."""
    endpoints = get_scim_endpoints(request)
    status_code, body = endpoints.post_user(TenantId(tenant_id), payload.model_dump())
    if status_code != 201:
        raise HTTPException(status_code=status_code, detail=body)
    response.status_code = status.HTTP_201_CREATED
    return body


@router.get("/Users/{user_id}")
async def get_scim_user(
    tenant_id: str,
    user_id: str,
    request: Request,
    _: str = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    """Retrieve user details by ID."""
    endpoints = get_scim_endpoints(request)
    status_code, body = endpoints.get_user(TenantId(tenant_id), user_id)
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=body)
    return body


@router.patch("/Users/{user_id}")
async def patch_scim_user(
    tenant_id: str,
    user_id: str,
    payload: ScimPatchPayload,
    request: Request,
    _: str = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    """Execute partial update (e.g. rapid deprovisioning active=false)."""
    endpoints = get_scim_endpoints(request)
    status_code, body = endpoints.patch_user(TenantId(tenant_id), user_id, payload.model_dump())
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=body)
    return body


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scim_user(
    tenant_id: str,
    user_id: str,
    request: Request,
    _: str = Header(None, alias="Authorization"),
) -> Response:
    """Deactivate and purge user via SCIM 2.0."""
    endpoints = get_scim_endpoints(request)
    status_code, body = endpoints.delete_user(TenantId(tenant_id), user_id)
    if status_code not in (200, 204):
        raise HTTPException(status_code=status_code, detail=body or {})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/Groups")
async def list_scim_groups(
    tenant_id: str,
    request: Request,
    _: str = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    """List groups via SCIM protocol."""
    endpoints = get_scim_endpoints(request)
    tenant_key = str(TenantId(tenant_id))
    group_store = endpoints.service._groups.get(tenant_key, {})
    resources = []
    for g in group_store.values():
        resources.append({
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "id": g.id,
            "displayName": g.displayName,
            "members": [{"value": m} for m in g.members],
            "meta": {"resourceType": "Group"},
        })

    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(resources),
        "itemsPerPage": 100,
        "startIndex": 1,
        "Resources": resources,
    }


@router.post("/Groups", status_code=status.HTTP_201_CREATED)
async def create_scim_group(
    tenant_id: str,
    payload: ScimGroupCreatePayload,
    request: Request,
    _: str = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    """Create or sync group membership via SCIM."""
    endpoints = get_scim_endpoints(request)
    member_ids = [m.get("value") for m in payload.members if m.get("value")]
    group_record = endpoints.service.sync_group_members(
        TenantId(tenant_id), payload.displayName, member_ids
    )
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "id": group_record.id,
        "displayName": group_record.displayName,
        "members": [{"value": m} for m in group_record.members],
        "meta": {"resourceType": "Group"},
    }
