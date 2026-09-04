"""
Comprehensive Cross-Tenant Isolation Negative Matrix Tests.
Verifies INV-TEN-001, INV-TEN-002, and INV-TEN-003 fail-closed execution semantics.
Conforms to MULTI-TENANCY-SPEC.md, ADR-0005, and MICRO-TASK-RAIL-SYSTEM.md §rail-sequence.
"""

import pytest
from revpilot.shared.identifiers import TenantId, OrganizationId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext, PrincipalContext, SecurityContext
from revpilot.shared.errors import (
    NotFoundError,
    ValidationError,
    TenancyViolationError,
)
from revpilot.modules.tenancy import (
    TenantStatus,
    SubscriptionTier,
    Entitlement,
    Organization,
    Tenant,
    InMemoryTenantRepository,
    TenantService,
    TenantContextPolicy,
)


@pytest.fixture
def repo() -> InMemoryTenantRepository:
    return InMemoryTenantRepository()


@pytest.fixture
def service(repo: InMemoryTenantRepository) -> TenantService:
    return TenantService(query_port=repo, command_port=repo)


# ==============================================================================
# MATRIX 1: Malformed and Missing Identifiers Fail Closed
# ==============================================================================

@pytest.mark.parametrize(
    "invalid_id",
    [
        "",
        "   ",
        "tnt_with spaces",
        "tnt_special!@#$",
        "tnt_semi;colon",
        "tnt_drop'table",
        "without_prefix_12345",
        "tnt_" + ("a" * 70),  # Exceeds max length
    ],
)
def test_negative_malformed_tenant_id_fails_closed(invalid_id: str) -> None:
    with pytest.raises(ValueError):
        TenantId(invalid_id)


@pytest.mark.parametrize(
    "invalid_type",
    [
        None,
        12345,
        12.34,
        ["tnt_12345"],
        {"id": "tnt_12345"},
    ],
)
def test_negative_type_error_tenant_id(invalid_type: object) -> None:
    with pytest.raises(TypeError):
        TenantId(invalid_type)  # type: ignore


def test_negative_type_confusion_identifiers() -> None:
    """Ensure PrincipalId cannot be used as TenantId."""
    p_id = PrincipalId.generate()
    with pytest.raises(TypeError):
        Tenant(
            id=p_id,  # type: ignore
            organization_id=OrganizationId.generate(),
            name="Confused",
            status=TenantStatus.ACTIVE,
            tier=SubscriptionTier.SHARED,
            entitlement=Entitlement(tier=SubscriptionTier.SHARED),
            created_at=UtcDateTime.now(),
            updated_at=UtcDateTime.now(),
        )


# ==============================================================================
# MATRIX 2: Tenant Lifecycle Inactive States Fail Closed (INV-TEN-001)
# ==============================================================================

def test_negative_provisioning_tenant_fails_closed(service: TenantService) -> None:
    org = service.create_organization("Org 1")
    t = service.provision_tenant(organization_id=org.id, name="Provisioning Tenant")

    assert t.status == TenantStatus.PROVISIONING
    with pytest.raises(TenancyViolationError) as exc:
        service.resolve_tenant_context(t.id)
    assert "not active" in str(exc.value) or "provisioning" in str(exc.value)


def test_negative_suspended_tenant_fails_closed(service: TenantService) -> None:
    org = service.create_organization("Org 2")
    t = service.provision_tenant(organization_id=org.id, name="Suspended Tenant")
    service.activate_tenant(t.id)
    service.suspend_tenant(t.id, reason="Sanctions compliance check")

    with pytest.raises(TenancyViolationError) as exc:
        service.resolve_tenant_context(t.id)
    assert "suspended" in str(exc.value)


def test_negative_deactivated_tenant_fails_closed(service: TenantService) -> None:
    org = service.create_organization("Org 3")
    t = service.provision_tenant(organization_id=org.id, name="Deactivated Tenant")
    service.activate_tenant(t.id)
    service.deactivate_tenant(t.id)

    with pytest.raises(TenancyViolationError) as exc:
        service.resolve_tenant_context(t.id)
    assert "deactivated" in str(exc.value)


def test_negative_terminal_deactivation_cannot_be_reopened(service: TenantService) -> None:
    org = service.create_organization("Org 4")
    t = service.provision_tenant(organization_id=org.id, name="Terminal Tenant")
    service.activate_tenant(t.id)
    service.deactivate_tenant(t.id)

    with pytest.raises(ValidationError) as exc:
        service.activate_tenant(t.id)
    assert "terminal state" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        service.suspend_tenant(t.id, reason="Cannot suspend dead tenant")
    assert "terminal state" in str(exc.value)


# ==============================================================================
# MATRIX 3: Cross-Tenant Negative Matrix (Tenant A vs Tenant B) (INV-TEN-001)
# ==============================================================================

def test_negative_cross_tenant_access_denied(service: TenantService) -> None:
    org = service.create_organization("Enterprise Multi-Tenant")
    tenant_a = service.provision_tenant(organization_id=org.id, name="Tenant Alpha")
    tenant_b = service.provision_tenant(organization_id=org.id, name="Tenant Beta")

    service.activate_tenant(tenant_a.id)
    service.activate_tenant(tenant_b.id)

    user_alpha = PrincipalContext(principal_id=PrincipalId.generate(), tenant_id=tenant_a.id)
    user_beta = PrincipalContext(principal_id=PrincipalId.generate(), tenant_id=tenant_b.id)

    # 1. User Alpha attempting to resolve Tenant Beta context -> FAILS CLOSED
    with pytest.raises(TenancyViolationError) as exc:
        service.resolve_security_context(tenant_b.id, user_alpha)
    assert "Cross-tenant access forbidden" in str(exc.value)
    assert str(tenant_a.id) in str(exc.value)
    assert str(tenant_b.id) in str(exc.value)

    # 2. User Beta attempting to resolve Tenant Alpha context -> FAILS CLOSED
    with pytest.raises(TenancyViolationError) as exc:
        service.resolve_security_context(tenant_a.id, user_beta)
    assert "Cross-tenant access forbidden" in str(exc.value)

    # 3. Direct SecurityContext cross-tenant mismatch -> FAILS CLOSED
    ctx_a = service.resolve_tenant_context(tenant_a.id)
    with pytest.raises(TenancyViolationError) as exc:
        SecurityContext(tenant=ctx_a, principal=user_beta)
    assert "Cross-tenant context mismatch" in str(exc.value)


# ==============================================================================
# MATRIX 4: Null Tenant & Break-Glass System Privileges (INV-TEN-003)
# ==============================================================================

def test_negative_non_system_principal_null_tenant_fails_closed() -> None:
    """Non-system principal cannot have null tenant_id (INV-TEN-003)."""
    with pytest.raises(TenancyViolationError) as exc:
        PrincipalContext(
            principal_id=PrincipalId.generate(),
            tenant_id=None,
            is_system=False,
        )
    assert "INV-TEN-003" in str(exc.value)


def test_positive_system_principal_authorized_cross_tenant(service: TenantService) -> None:
    """Platform system principal allowed audited access across tenants (INV-TEN-003)."""
    org = service.create_organization("Platform Ops Org")
    tenant = service.provision_tenant(organization_id=org.id, name="Monitored Tenant")
    service.activate_tenant(tenant.id)

    system_ops = PrincipalContext(
        principal_id=PrincipalId.generate(),
        tenant_id=None,
        is_system=True,
    )

    sec_ctx = service.resolve_security_context(tenant.id, system_ops)
    assert sec_ctx.principal.is_system is True
    assert sec_ctx.tenant.tenant_id == tenant.id


# ==============================================================================
# MATRIX 5: Missing and Non-Existent Resources
# ==============================================================================

def test_negative_non_existent_tenant_lookup(service: TenantService) -> None:
    random_id = TenantId.generate()
    with pytest.raises(NotFoundError):
        service.get_tenant(random_id)

    with pytest.raises(NotFoundError):
        service.resolve_tenant_context(random_id)


def test_negative_tenant_context_policy_validation() -> None:
    with pytest.raises(TenancyViolationError):
        TenantContextPolicy.validate_context("invalid_object")  # type: ignore
