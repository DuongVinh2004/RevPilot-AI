"""
RevPilot AI — Inbound Authentication and Context Resolution Middleware
Enforces INV-TEN-002 (Server-derived context, untrusted headers discarded)
and INV-IAM-001 (Boundary JWT verification).
Conforms to docs/26-api/API-STANDARDS.md §1..§2.
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.errors import AuthenticationError, TenancyViolationError
from revpilot.shared.identifiers import TenantId, OrganizationId, PrincipalId
from revpilot.modules.identity.domain.models import VerifiedClaimsToken
from revpilot.modules.identity.ports.authentication import AuthenticationPort

logger = logging.getLogger("revpilot.api.auth")
security_scheme = HTTPBearer(auto_error=False)


def get_auth_adapter(request: Request) -> AuthenticationPort | None:
    """Retrieve application authentication adapter from app state."""
    return getattr(request.app.state, "auth_adapter", None)


async def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> PrincipalContext:
    """
    Validate Authorization Bearer token, extract verified claims,
    and attach server-derived PrincipalContext and TenantContext to request.state.
    Strictly discards untrusted client headers (INV-TEN-002).
    """
    # 1. Reject missing credentials
    if not credentials or not credentials.credentials:
        raise AuthenticationError(
            "Authentication token missing or invalid",
            details={"error": "missing_bearer_token"},
        )

    raw_token = credentials.credentials
    auth_adapter = get_auth_adapter(request)

    # 2. Verify token via AuthenticationPort (Fail-Closed)
    if auth_adapter is None:
        raise AuthenticationError(
            "Authentication service is unavailable",
            details={"error": "auth_adapter_unavailable"},
        )

    if hasattr(auth_adapter, "async_verify_token"):
        verified_token: VerifiedClaimsToken = await auth_adapter.async_verify_token(raw_token)
    else:
        verified_token = auth_adapter.verify_token(raw_token)
    claims = verified_token.claims

    # 3. Discard untrusted client headers; detect spoofing attempts (INV-TEN-002)
    untrusted_tenant = request.headers.get("X-Tenant-ID")
    if untrusted_tenant and claims.tenant_id and untrusted_tenant != claims.tenant_id:
        raise TenancyViolationError(
            f"Client-supplied X-Tenant-ID '{untrusted_tenant}' contradicts authenticated claim '{claims.tenant_id}'.",
            details={"client_header": untrusted_tenant, "token_claim": claims.tenant_id},
        )

    # 4. Construct server-derived immutable contexts
    tenant_id = TenantId(claims.tenant_id) if claims.tenant_id else None
    principal_id = PrincipalId(claims.sub)

    is_system = getattr(claims, "is_system", False) or "SYSTEM_ADMIN" in claims.roles

    principal_ctx = PrincipalContext(
        principal_id=principal_id,
        tenant_id=tenant_id,
        roles=claims.roles,
        permissions=claims.permissions,
        is_system=is_system,
    )

    tenant_ctx = None
    if tenant_id:
        tenant_ctx = TenantContext(
            tenant_id=tenant_id,
            organization_id=OrganizationId("org_default_001"),
            tier="enterprise",
            is_active=True,
        )

    request.state.principal_context = principal_ctx
    request.state.tenant_context = tenant_ctx

    return principal_ctx


def get_current_tenant(
    request: Request,
    principal: PrincipalContext = Depends(get_current_principal),
) -> TenantContext:
    """Retrieve validated TenantContext for tenant-scoped routes."""
    tenant_ctx = getattr(request.state, "tenant_context", None)
    if tenant_ctx is None:
        raise TenancyViolationError(
            "Tenant context is required to access this resource (INV-TEN-001).",
            details={"principal_id": str(principal.principal_id)},
        )
    return tenant_ctx
