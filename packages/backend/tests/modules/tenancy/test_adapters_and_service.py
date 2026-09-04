"""
Unit tests for InMemoryTenantRepository and TenantService.
Verifies AC-R02-003-01 through AC-R02-003-06.
"""

import pytest
from revpilot.shared.identifiers import TenantId, OrganizationId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext, PrincipalContext, SecurityContext
from revpilot.shared.errors import NotFoundError, TenancyViolationError
from revpilot.modules.tenancy import (
    TenantStatus,
    SubscriptionTier,
    Entitlement,
    Organization,
    Tenant,
    InMemoryTenantRepository,
    TenantService,
)


@pytest.fixture
def repo() -> InMemoryTenantRepository:
    return InMemoryTenantRepository()


@pytest.fixture
def service(repo: InMemoryTenantRepository) -> TenantService:
    return TenantService(query_port=repo, command_port=repo)


def test_repository_save_and_retrieve_organization(repo: InMemoryTenantRepository) -> None:
    org_id = OrganizationId.generate()
    org = Organization(id=org_id, name="Test Org", created_at=UtcDateTime.now())
    repo.save_organization(org)

    retrieved = repo.get_organization_by_id(org_id)
    assert retrieved is not None
    assert retrieved.id == org_id
    assert retrieved.name == "Test Org"

    missing = repo.get_organization_by_id(OrganizationId.generate())
    assert missing is None


def test_repository_save_and_retrieve_tenant(repo: InMemoryTenantRepository) -> None:
    t_id = TenantId.generate()
    org_id = OrganizationId.generate()
    now = UtcDateTime.now()
    tenant = Tenant(
        id=t_id,
        organization_id=org_id,
        name="Tenant One",
        status=TenantStatus.PROVISIONING,
        tier=SubscriptionTier.SHARED,
        entitlement=Entitlement(tier=SubscriptionTier.SHARED),
        created_at=now,
        updated_at=now,
    )
    repo.save_tenant(tenant)

    assert repo.exists(t_id) is True
    assert repo.exists(TenantId.generate()) is False

    retrieved = repo.get_by_id(t_id)
    assert retrieved is not None
    assert retrieved.id == t_id

    tenants_in_org = repo.get_by_organization(org_id)
    assert len(tenants_in_org) == 1
    assert tenants_in_org[0].id == t_id


def test_repository_update_status_not_found(repo: InMemoryTenantRepository) -> None:
    with pytest.raises(NotFoundError):
        repo.update_status(TenantId.generate(), TenantStatus.ACTIVE)


def test_service_organization_and_tenant_lifecycle(service: TenantService) -> None:
    # 1. Create Org
    org = service.create_organization(name="Enterprise Global")
    assert org.name == "Enterprise Global"

    # 2. Provision Tenant
    tenant = service.provision_tenant(
        organization_id=org.id,
        name="Enterprise Tenant EU",
        tier=SubscriptionTier.ENTERPRISE,
    )
    assert tenant.status == TenantStatus.PROVISIONING
    assert tenant.tier == SubscriptionTier.ENTERPRISE

    # 3. Provisioning tenant cannot yield active context
    with pytest.raises(TenancyViolationError):
        service.resolve_tenant_context(tenant.id)

    # 4. Activate Tenant
    activated = service.activate_tenant(tenant.id)
    assert activated.status == TenantStatus.ACTIVE
    assert activated.is_active() is True

    # 5. Resolve active context
    ctx = service.resolve_tenant_context(tenant.id)
    assert isinstance(ctx, TenantContext)
    assert ctx.tenant_id == tenant.id
    assert ctx.tier == "enterprise"

    # 6. Suspend Tenant
    suspended = service.suspend_tenant(tenant.id, reason="Billing delinquency")
    assert suspended.status == TenantStatus.SUSPENDED
    assert suspended.suspension_reason == "Billing delinquency"

    # 7. Suspended tenant cannot yield context
    with pytest.raises(TenancyViolationError):
        service.resolve_tenant_context(tenant.id)

    # 8. Deactivate Tenant
    deactivated = service.deactivate_tenant(tenant.id)
    assert deactivated.status == TenantStatus.DEACTIVATED

    # 9. Deactivated tenant cannot yield context
    with pytest.raises(TenancyViolationError):
        service.resolve_tenant_context(tenant.id)


def test_service_provision_fails_on_missing_organization(service: TenantService) -> None:
    missing_org_id = OrganizationId.generate()
    with pytest.raises(NotFoundError):
        service.provision_tenant(
            organization_id=missing_org_id,
            name="Orphan Tenant",
        )


def test_service_resolve_security_context_cross_tenant_enforcement(
    service: TenantService,
) -> None:
    org = service.create_organization(name="Multi-Org")
    t1 = service.provision_tenant(organization_id=org.id, name="Tenant 1")
    t2 = service.provision_tenant(organization_id=org.id, name="Tenant 2")

    service.activate_tenant(t1.id)
    service.activate_tenant(t2.id)

    user1 = PrincipalContext(principal_id=PrincipalId.generate(), tenant_id=t1.id)
    user2 = PrincipalContext(principal_id=PrincipalId.generate(), tenant_id=t2.id)
    sys_admin = PrincipalContext(
        principal_id=PrincipalId.generate(), tenant_id=None, is_system=True
    )

    # Authorized: User 1 accessing Tenant 1
    sec_ctx1 = service.resolve_security_context(t1.id, user1)
    assert isinstance(sec_ctx1, SecurityContext)
    assert sec_ctx1.tenant.tenant_id == t1.id

    # Forbidden: User 2 accessing Tenant 1 (Cross-tenant breach INV-TEN-001)
    with pytest.raises(TenancyViolationError):
        service.resolve_security_context(t1.id, user2)

    # Authorized: System Principal accessing Tenant 1 (INV-TEN-003)
    sys_ctx = service.resolve_security_context(t1.id, sys_admin)
    assert isinstance(sys_ctx, SecurityContext)
    assert sys_ctx.principal.is_system is True
