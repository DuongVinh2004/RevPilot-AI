"""
RevPilot AI — Tenant and Principal Context Primitives
Immutable security and tenancy envelopes enforcing INV-TEN-001, INV-TEN-002, INV-TEN-003, and INV-IAM-001.
"""

from __future__ import annotations
from dataclasses import dataclass

from revpilot.shared.identifiers import TenantId, PrincipalId, OrganizationId
from revpilot.shared.errors import TenancyViolationError, AuthorizationError


@dataclass(frozen=True, slots=True)
class TenantContext:
    """
    Immutable verified tenant execution context.
    Must be server-derived from authenticated claims (INV-TEN-002).
    """
    tenant_id: TenantId
    organization_id: OrganizationId
    tier: str = "growth"
    is_active: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, TenantId):
            raise TypeError(f"tenant_id must be a TenantId instance, got {type(self.tenant_id).__name__}")
        if not isinstance(self.organization_id, OrganizationId):
            raise TypeError(f"organization_id must be an OrganizationId instance, got {type(self.organization_id).__name__}")
        if not self.tier or not isinstance(self.tier, str):
            raise ValueError("tier must be a non-empty string")
        if not self.is_active:
            raise TenancyViolationError(
                f"Tenant '{self.tenant_id}' is deactivated or suspended",
                details={"tenant_id": str(self.tenant_id), "is_active": False},
            )

    def to_dict(self) -> dict[str, str | bool]:
        """Serialize tenant context metadata."""
        return {
            "tenant_id": str(self.tenant_id),
            "organization_id": str(self.organization_id),
            "tier": self.tier,
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return f"TenantContext(tenant_id={self.tenant_id!r}, org_id={self.organization_id!r}, tier={self.tier!r})"


@dataclass(frozen=True, slots=True)
class PrincipalContext:
    """
    Immutable verified caller context (user, service, or delegated agent).
    Enforces deny-by-default role and permission checks (INV-IAM-001).
    """
    principal_id: PrincipalId
    tenant_id: TenantId | None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    is_system: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.principal_id, PrincipalId):
            raise TypeError(f"principal_id must be PrincipalId, got {type(self.principal_id).__name__}")
        # Invariant: Global/platform operations use explicit privileged context, never tenant = null for users (INV-TEN-003)
        if not self.is_system and self.tenant_id is None:
            raise TenancyViolationError(
                "Non-system principal requires explicit tenant_id (INV-TEN-003). Null tenant rejected.",
                details={"principal_id": str(self.principal_id)},
            )
        if self.tenant_id is not None and not isinstance(self.tenant_id, TenantId):
            raise TypeError(f"tenant_id must be TenantId or None, got {type(self.tenant_id).__name__}")

    def has_role(self, role: str) -> bool:
        """Check if principal possesses specified role (case-insensitive)."""
        return role.lower() in (r.lower() for r in self.roles)

    def has_permission(self, permission: str) -> bool:
        """Check if principal possesses specified permission (case-insensitive)."""
        return permission.lower() in (p.lower() for p in self.permissions)

    def require_permission(self, permission: str) -> None:
        """Enforce required permission, raising AuthorizationError if absent (deny-by-default)."""
        if not self.has_permission(permission):
            raise AuthorizationError(
                f"Principal '{self.principal_id}' lacks required permission '{permission}'",
                details={"principal_id": str(self.principal_id), "required_permission": permission},
            )

    def __repr__(self) -> str:
        return (
            f"PrincipalContext(id={self.principal_id!r}, tenant={self.tenant_id!r}, "
            f"system={self.is_system}, roles={sorted(self.roles)})"
        )


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """
    Unified execution security envelope binding TenantContext and PrincipalContext.
    Verifies tenant isolation invariant (principal belongs to tenant).
    """
    tenant: TenantContext
    principal: PrincipalContext

    def __post_init__(self) -> None:
        if not isinstance(self.tenant, TenantContext):
            raise TypeError(f"tenant must be TenantContext, got {type(self.tenant).__name__}")
        if not isinstance(self.principal, PrincipalContext):
            raise TypeError(f"principal must be PrincipalContext, got {type(self.principal).__name__}")

        # Invariant: principal tenant must match execution tenant unless system actor
        if not self.principal.is_system and self.principal.tenant_id != self.tenant.tenant_id:
            raise TenancyViolationError(
                f"Cross-tenant context mismatch: Principal tenant '{self.principal.tenant_id}' "
                f"does not match execution tenant '{self.tenant.tenant_id}' (INV-TEN-001).",
                details={
                    "principal_tenant": str(self.principal.tenant_id),
                    "execution_tenant": str(self.tenant.tenant_id),
                },
            )

    @classmethod
    def create(cls, tenant: TenantContext, principal: PrincipalContext) -> SecurityContext:
        """Factory creating and validating unified security context."""
        return cls(tenant=tenant, principal=principal)
