"""
Unit tests for Tenancy Ports and Tenant Context Policy.
Verifies AC-R02-002-01 through AC-R02-002-05.
"""

import pytest
from revpilot.shared.identifiers import TenantId, OrganizationId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext, PrincipalContext, SecurityContext
from revpilot.shared.errors import TenancyViolationError
from revpilot.modules.tenancy.domain import (
    TenantStatus,
    SubscriptionTier,
    Entitlement,
    Organization,
    Tenant,
)
from revpilot.modules.tenancy.ports import (
    TenantQueryPort,
    TenantCommandPort,
    TenantContextPolicy,
)


class DummyTenantRepository(TenantQueryPort, TenantCommandPort):
    """Mock repository satisfying both Query and Command ports."""

    def __init__(self) -> None:
        self.tenants: dict[TenantId, Tenant] = {}
        self.orgs: dict[OrganizationId, Organization] = {}

    def get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        return self.tenants.get(tenant_id)

    def get_by_organization(self, organization_id: OrganizationId) -> list[Tenant]:
        return [t for t in self.tenants.values() if t.organization_id == organization_id]

    def get_organization_by_id(self, organization_id: OrganizationId) -> Organization | None:
        return self.orgs.get(organization_id)

    def exists(self, tenant_id: TenantId) -> bool:
        return tenant_id in self.tenants

    def save_tenant(self, tenant: Tenant) -> None:
        self.tenants[tenant.id] = tenant

    def save_organization(self, organization: Organization) -> None:
        self.orgs[organization.id] = organization

    def update_status(
        self, tenant_id: TenantId, status: TenantStatus, reason: str | None = None
    ) -> Tenant:
        tenant = self.tenants[tenant_id]
        if status == TenantStatus.ACTIVE:
            tenant.activate()
        elif status == TenantStatus.SUSPENDED:
            tenant.suspend(reason or "Suspended")
        elif status == TenantStatus.DEACTIVATED:
            tenant.deactivate()
        return tenant


def test_ports_protocol_conformance() -> None:
    repo = DummyTenantRepository()
    assert isinstance(repo, TenantQueryPort)
    assert isinstance(repo, TenantCommandPort)


def test_validate_context_success_and_failures() -> None:
    t_id = TenantId.generate()
    org_id = OrganizationId.generate()
    valid_ctx = TenantContext(tenant_id=t_id, organization_id=org_id, is_active=True)

    # Valid active context passes
    TenantContextPolicy.validate_context(valid_ctx)

    # Invalid type fails closed
    with pytest.raises(TenancyViolationError):
        TenantContextPolicy.validate_context("not_a_context")  # type: ignore


def test_authorize_tenant_access_user_principal() -> None:
    t_a = TenantId.generate()
    t_b = TenantId.generate()
    u_a = PrincipalId.generate()

    user_a = PrincipalContext(principal_id=u_a, tenant_id=t_a)

    # Same tenant access allowed
    TenantContextPolicy.authorize_tenant_access(user_a, t_a)

    # Cross-tenant access denied (INV-TEN-001)
    with pytest.raises(TenancyViolationError) as exc:
        TenantContextPolicy.authorize_tenant_access(user_a, t_b)
    assert "Cross-tenant access forbidden" in str(exc.value)


def test_authorize_tenant_access_system_principal() -> None:
    t_a = TenantId.generate()
    sys_principal = PrincipalContext(
        principal_id=PrincipalId.generate(),
        tenant_id=None,
        is_system=True,
    )

    # System principal permitted across arbitrary tenants (INV-TEN-003)
    TenantContextPolicy.authorize_tenant_access(sys_principal, t_a)


def test_authorize_tenant_access_type_safety() -> None:
    t_a = TenantId.generate()
    with pytest.raises(TenancyViolationError):
        TenantContextPolicy.authorize_tenant_access("invalid", t_a)  # type: ignore

    user = PrincipalContext(principal_id=PrincipalId.generate(), tenant_id=t_a)
    with pytest.raises(TenancyViolationError):
        TenantContextPolicy.authorize_tenant_access(user, "invalid_id")  # type: ignore


def test_resolve_security_context_success_for_matching_user() -> None:
    t_id = TenantId.generate()
    org_id = OrganizationId.generate()
    now = UtcDateTime.now()
    tenant = Tenant(
        id=t_id,
        organization_id=org_id,
        name="Acme Prod",
        status=TenantStatus.ACTIVE,
        tier=SubscriptionTier.SHARED,
        entitlement=Entitlement(tier=SubscriptionTier.SHARED),
        created_at=now,
        updated_at=now,
    )
    principal = PrincipalContext(principal_id=PrincipalId.generate(), tenant_id=t_id)

    sec_ctx = TenantContextPolicy.resolve_security_context(tenant, principal)
    assert isinstance(sec_ctx, SecurityContext)
    assert sec_ctx.tenant.tenant_id == t_id
    assert sec_ctx.principal.principal_id == principal.principal_id


def test_resolve_security_context_cross_tenant_rejected() -> None:
    t_id_1 = TenantId.generate()
    t_id_2 = TenantId.generate()
    org_id = OrganizationId.generate()
    now = UtcDateTime.now()
    tenant = Tenant(
        id=t_id_1,
        organization_id=org_id,
        name="Tenant 1",
        status=TenantStatus.ACTIVE,
        tier=SubscriptionTier.SHARED,
        entitlement=Entitlement(tier=SubscriptionTier.SHARED),
        created_at=now,
        updated_at=now,
    )
    # Principal belongs to Tenant 2
    foreign_principal = PrincipalContext(
        principal_id=PrincipalId.generate(), tenant_id=t_id_2
    )

    with pytest.raises(TenancyViolationError):
        TenantContextPolicy.resolve_security_context(tenant, foreign_principal)


def test_resolve_security_context_inactive_tenant_rejected() -> None:
    t_id = TenantId.generate()
    org_id = OrganizationId.generate()
    now = UtcDateTime.now()
    tenant = Tenant(
        id=t_id,
        organization_id=org_id,
        name="Tenant Suspended",
        status=TenantStatus.SUSPENDED,
        tier=SubscriptionTier.SHARED,
        entitlement=Entitlement(tier=SubscriptionTier.SHARED),
        created_at=now,
        updated_at=now,
        suspension_reason="Overdue invoice",
    )
    principal = PrincipalContext(principal_id=PrincipalId.generate(), tenant_id=t_id)

    with pytest.raises(TenancyViolationError) as exc:
        TenantContextPolicy.resolve_security_context(tenant, principal)
    assert "is in status 'suspended'" in str(exc.value)
