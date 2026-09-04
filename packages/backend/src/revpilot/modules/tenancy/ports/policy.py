"""
RevPilot AI — Tenant Context Policy
Enforces INV-TEN-001, INV-TEN-002, and INV-TEN-003 at the tenant execution boundary.
"""

from __future__ import annotations

from revpilot.shared.identifiers import TenantId
from revpilot.shared.context import TenantContext, PrincipalContext, SecurityContext
from revpilot.shared.errors import TenancyViolationError
from revpilot.modules.tenancy.domain.models import Tenant


class TenantContextPolicy:
    """
    Authoritative policy verifying tenant context validity, fail-closed isolation,
    and cross-tenant access permissions.
    """

    @classmethod
    def validate_context(cls, context: TenantContext) -> None:
        """
        Verify tenant context is structurally valid and in active state.
        Fails closed on missing, inactive, or malformed contexts (INV-TEN-002).
        """
        if not isinstance(context, TenantContext):
            raise TenancyViolationError(
                f"Expected TenantContext instance, got {type(context).__name__}",
                details={"provided_type": type(context).__name__},
            )
        if not context.is_active:
            raise TenancyViolationError(
                f"TenantContext for '{context.tenant_id}' is marked inactive",
                details={"tenant_id": str(context.tenant_id), "is_active": False},
            )

    @classmethod
    def authorize_tenant_access(
        cls, principal: PrincipalContext, target_tenant_id: TenantId
    ) -> None:
        """
        Enforce cross-tenant access boundary (INV-TEN-001, INV-TEN-003).
        System principals are authorized across tenants.
        Non-system principals must strictly match target_tenant_id.
        """
        if not isinstance(principal, PrincipalContext):
            raise TenancyViolationError(
                f"Expected PrincipalContext, got {type(principal).__name__}",
                details={"provided_type": type(principal).__name__},
            )
        if not isinstance(target_tenant_id, TenantId):
            raise TenancyViolationError(
                f"Expected TenantId, got {type(target_tenant_id).__name__}",
                details={"provided_type": type(target_tenant_id).__name__},
            )

        if principal.is_system:
            # System principal authorized for cross-tenant operations (INV-TEN-003)
            return

        if principal.tenant_id is None:
            raise TenancyViolationError(
                f"Principal '{principal.principal_id}' has no tenant association (INV-TEN-003)",
                details={"principal_id": str(principal.principal_id)},
            )

        if principal.tenant_id != target_tenant_id:
            raise TenancyViolationError(
                f"Cross-tenant access forbidden: Principal '{principal.principal_id}' "
                f"from tenant '{principal.tenant_id}' attempted access to tenant '{target_tenant_id}' (INV-TEN-001)",
                details={
                    "principal_id": str(principal.principal_id),
                    "principal_tenant": str(principal.tenant_id),
                    "target_tenant": str(target_tenant_id),
                },
            )

    @classmethod
    def resolve_security_context(
        cls, tenant: Tenant, principal: PrincipalContext
    ) -> SecurityContext:
        """
        Safely construct a unified SecurityContext binding Tenant and Principal.
        Fails closed if tenant is not active or if cross-tenant violation occurs.
        """
        if not isinstance(tenant, Tenant):
            raise TenancyViolationError(
                f"Expected Tenant aggregate, got {type(tenant).__name__}",
                details={"provided_type": type(tenant).__name__},
            )

        # Enforce cross-tenant authorization
        cls.authorize_tenant_access(principal, tenant.id)

        # Inactive tenant fails closed (INV-TEN-001)
        if not tenant.is_active():
            raise TenancyViolationError(
                f"Cannot resolve SecurityContext: tenant '{tenant.id}' is in status '{tenant.status.value}'",
                details={"tenant_id": str(tenant.id), "status": tenant.status.value},
            )

        tenant_ctx = tenant.to_context()
        return SecurityContext.create(tenant=tenant_ctx, principal=principal)
