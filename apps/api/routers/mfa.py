"""
RevPilot AI — Multi-Factor Authentication (MFA) API Router
Specification: docs/14-iam/IAM-SPEC.md §8, ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.api.middleware.authentication import get_current_principal, get_current_tenant
from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.modules.identity.mfa import MfaManager, MfaError

router = APIRouter(prefix="/auth/mfa", tags=["MFA"])


def get_mfa_manager(request: Request) -> MfaManager:
    manager = getattr(request.app.state, "mfa_manager", None)
    if manager is None:
        cache = getattr(request.app.state, "redis_client", None)
        manager = MfaManager(cache=cache)
        request.app.state.mfa_manager = manager
    return manager


class VerifyCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class RecoveryCodeRequest(BaseModel):
    code: str = Field(min_length=8)


@router.get("/status")
async def get_mfa_status(
    principal: PrincipalContext = Depends(get_current_principal),
    mfa_mgr: MfaManager = Depends(get_mfa_manager),
) -> dict[str, Any]:
    """Check MFA enrollment status for current authenticated principal."""
    p_id = str(principal.principal_id)
    enabled = mfa_mgr.is_mfa_enabled(p_id)
    return {
        "principal_id": p_id,
        "mfa_enabled": enabled,
    }


@router.post("/totp/setup", status_code=status.HTTP_200_OK)
async def setup_totp(
    principal: PrincipalContext = Depends(get_current_principal),
    mfa_mgr: MfaManager = Depends(get_mfa_manager),
) -> dict[str, Any]:
    """Initiate TOTP setup by generating secret and provisioning URI."""
    p_id = str(principal.principal_id)
    account_name = f"{p_id}@revpilot.internal"
    res = mfa_mgr.initiate_totp_setup(p_id, account_name)
    return {
        "principal_id": p_id,
        "secret": res["secret"],
        "provisioning_uri": res["provisioning_uri"],
    }


@router.post("/totp/activate", status_code=status.HTTP_200_OK)
async def activate_totp(
    payload: VerifyCodeRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    mfa_mgr: MfaManager = Depends(get_mfa_manager),
) -> dict[str, Any]:
    """Verify first TOTP code to confirm authenticator and issue recovery codes."""
    p_id = str(principal.principal_id)
    try:
        recovery_codes = mfa_mgr.activate_totp(p_id, payload.code)
        return {
            "principal_id": p_id,
            "status": "ACTIVATED",
            "recovery_codes": recovery_codes,
        }
    except MfaError as err:
        raise HTTPException(status_code=err.http_status, detail={"code": err.code, "message": err.message})


@router.post("/totp/verify", status_code=status.HTTP_200_OK)
async def verify_totp(
    payload: VerifyCodeRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    mfa_mgr: MfaManager = Depends(get_mfa_manager),
) -> dict[str, Any]:
    """Verify a TOTP code during session step-up or break-glass authentication."""
    p_id = str(principal.principal_id)
    try:
        mfa_mgr.verify_totp(p_id, payload.code)
        return {
            "principal_id": p_id,
            "verified": True,
        }
    except MfaError as err:
        raise HTTPException(status_code=err.http_status, detail={"code": err.code, "message": err.message})


@router.post("/recovery/consume", status_code=status.HTTP_200_OK)
async def consume_recovery_code(
    payload: RecoveryCodeRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    mfa_mgr: MfaManager = Depends(get_mfa_manager),
) -> dict[str, Any]:
    """Consume single-use recovery code when authenticator is unavailable."""
    p_id = str(principal.principal_id)
    try:
        mfa_mgr.consume_recovery_code(p_id, payload.code)
        return {
            "principal_id": p_id,
            "verified": True,
            "message": "Recovery code successfully consumed",
        }
    except MfaError as err:
        raise HTTPException(status_code=err.http_status, detail={"code": err.code, "message": err.message})
