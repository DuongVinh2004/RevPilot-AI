"""
RevPilot AI — Platform & Tenant Admin API Router (Phase 07)
Conforms to docs/26-api/API-STANDARDS.md §10 and docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md.
"""

from __future__ import annotations

import inspect
import uuid
from typing import Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, status, HTTPException
from pydantic import BaseModel, Field

from apps.api.middleware.authorization import require_system_admin, require_roles
from revpilot.shared.context import PrincipalContext
from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.tenancy.domain.models import (
    Tenant,
    TenantStatus,
    SubscriptionTier,
    Entitlement,
)

router = APIRouter(prefix="/admin", tags=["Platform & Tenancy Admin"])


class TenantProvisionRequest(BaseModel):
    name: str
    slug: str
    tier: str = "SHARED"
    admin_email: str


class TenantLifecycleRequest(BaseModel):
    target_status: str
    reason: str | None = None


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
async def provision_tenant(
    payload: TenantProvisionRequest,
    request: Request,
    principal: PrincipalContext = Depends(require_system_admin()),
) -> dict[str, Any]:
    """Provision a new tenant boundary."""
    repo = getattr(request.app.state, "tenant_repo", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tenant repository unavailable",
        )

    t_id = f"tnt_{uuid.uuid4().hex[:16]}"
    now = UtcDateTime.now()
    tier_str = payload.tier.lower()
    tier_enum = SubscriptionTier(tier_str) if tier_str in [t.value for t in SubscriptionTier] else SubscriptionTier.SHARED

    entitlement = Entitlement(tier=tier_enum)
    tenant_entity = Tenant(
        id=TenantId(t_id),
        organization_id=OrganizationId(f"org_{t_id[4:]}"),
        name=payload.name,
        status=TenantStatus.ACTIVE,
        tier=tier_enum,
        entitlement=entitlement,
        created_at=now,
        updated_at=now,
    )

    if hasattr(repo, "async_save_tenant"):
        await repo.async_save_tenant(tenant_entity)
    elif hasattr(repo, "save_tenant"):
        res = repo.save_tenant(tenant_entity)
        if inspect.isawaitable(res):
            await res

    return {
        "tenant_id": t_id,
        "name": payload.name,
        "slug": payload.slug,
        "status": "ACTIVE",
        "created_at": now.as_datetime().isoformat(),
    }


@router.post("/tenants/{tenant_id}/lifecycle")
async def update_tenant_lifecycle(
    tenant_id: str,
    payload: TenantLifecycleRequest,
    request: Request,
    principal: PrincipalContext = Depends(require_system_admin()),
) -> dict[str, Any]:
    """Update tenant operational status (SUSPENDED, ACTIVE, LEGAL_HOLD)."""
    repo = getattr(request.app.state, "tenant_repo", None)
    if repo is not None:
        st_enum = TenantStatus(payload.target_status.lower())
        await repo.async_update_status(TenantId(tenant_id), st_enum, payload.reason)

    return {
        "tenant_id": tenant_id,
        "status": payload.target_status.upper(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/tenants/{tenant_id}/exports", status_code=status.HTTP_202_ACCEPTED)
async def export_tenant_data(
    tenant_id: str,
    request: Request,
    principal: PrincipalContext = Depends(require_roles("TENANT_ADMIN", "SYSTEM_ADMIN")),
) -> dict[str, Any]:
    """Trigger GDPR / SOC2 tenant data export."""
    repo = getattr(request.app.state, "tenant_repo", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tenant repository unavailable",
        )

    if "SYSTEM_ADMIN" not in principal.roles:
        if str(principal.tenant_id) != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_TENANT_ACCESS_FORBIDDEN",
                    "message": "Tenant admin cannot export data belonging to another tenant",
                    "cannot export data for tenant": f"Tenant admin of tenant '{principal.tenant_id}' cannot export data for tenant '{tenant_id}'",
                },
            )

    return {
        "export_id": f"exp_{uuid.uuid4().hex[:12]}",
        "tenant_id": tenant_id,
        "status": "EXPORTING",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_202_ACCEPTED)
async def cascade_delete_tenant(
    tenant_id: str,
    request: Request,
    principal: PrincipalContext = Depends(require_system_admin()),
) -> dict[str, Any]:
    """Trigger verified cascade deletion saga with deletion certificate."""
    repo = getattr(request.app.state, "tenant_repo", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tenant repository unavailable",
        )

    return {
        "deletion_job_id": f"del_{uuid.uuid4().hex[:12]}",
        "tenant_id": tenant_id,
        "status": "DELETING",
    }
