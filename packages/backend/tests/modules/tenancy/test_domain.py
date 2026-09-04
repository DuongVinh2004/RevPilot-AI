"""
Unit tests for Tenancy Domain Models, Entities, and Lifecycle Transitions.
Verifies AC-R02-001-01 through AC-R02-001-05.
"""

import pytest
from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import ValidationError, TenancyViolationError
from revpilot.modules.tenancy.domain import (
    TenantStatus,
    SubscriptionTier,
    Entitlement,
    Organization,
    Tenant,
)


def test_tenant_status_enum_values() -> None:
    assert TenantStatus.PROVISIONING.value == "provisioning"
    assert TenantStatus.ACTIVE.value == "active"
    assert TenantStatus.SUSPENDED.value == "suspended"
    assert TenantStatus.DEACTIVATED.value == "deactivated"
    assert TenantStatus("active") == TenantStatus.ACTIVE


def test_subscription_tier_enum_values() -> None:
    assert SubscriptionTier.SHARED.value == "shared"
    assert SubscriptionTier.ENTERPRISE.value == "enterprise"
    assert SubscriptionTier.REGULATED.value == "regulated"
    assert SubscriptionTier("enterprise") == SubscriptionTier.ENTERPRISE


def test_entitlement_validation_and_features() -> None:
    ent = Entitlement(
        tier=SubscriptionTier.ENTERPRISE,
        max_seats=25,
        features=frozenset({"rag_search", "custom_connectors"}),
        quotas={"max_models": 10},
    )
    assert ent.tier == SubscriptionTier.ENTERPRISE
    assert ent.max_seats == 25
    assert ent.has_feature("RAG_SEARCH") is True
    assert ent.has_feature("custom_connectors") is True
    assert ent.has_feature("unknown_feature") is False
    assert ent.get_quota("max_models") == 10
    assert ent.get_quota("non_existent", default=42) == 42


def test_entitlement_rejects_invalid_inputs() -> None:
    with pytest.raises(TypeError):
        Entitlement(tier="invalid_tier", max_seats=5)  # type: ignore

    with pytest.raises(ValidationError):
        Entitlement(tier=SubscriptionTier.SHARED, max_seats=0)


def test_organization_validation() -> None:
    org_id = OrganizationId.generate()
    now = UtcDateTime.now()
    org = Organization(id=org_id, name="Acme Corp", created_at=now)
    assert org.id == org_id
    assert org.name == "Acme Corp"
    assert org.is_active is True

    with pytest.raises(ValidationError):
        Organization(id=org_id, name="   ", created_at=now)

    with pytest.raises(TypeError):
        Organization(id="not_an_id", name="Acme", created_at=now)  # type: ignore


def test_tenant_initialization_and_type_enforcement() -> None:
    tenant_id = TenantId.generate()
    org_id = OrganizationId.generate()
    now = UtcDateTime.now()
    ent = Entitlement(tier=SubscriptionTier.SHARED)

    tenant = Tenant(
        id=tenant_id,
        organization_id=org_id,
        name="Acme US",
        status=TenantStatus.PROVISIONING,
        tier=SubscriptionTier.SHARED,
        entitlement=ent,
        created_at=now,
        updated_at=now,
    )
    assert tenant.id == tenant_id
    assert tenant.status == TenantStatus.PROVISIONING
    assert tenant.is_active() is False

    with pytest.raises(ValidationError):
        Tenant(
            id=tenant_id,
            organization_id=org_id,
            name="",
            status=TenantStatus.PROVISIONING,
            tier=SubscriptionTier.SHARED,
            entitlement=ent,
            created_at=now,
            updated_at=now,
        )


def test_tenant_lifecycle_transitions() -> None:
    tenant = Tenant(
        id=TenantId.generate(),
        organization_id=OrganizationId.generate(),
        name="Test Tenant",
        status=TenantStatus.PROVISIONING,
        tier=SubscriptionTier.SHARED,
        entitlement=Entitlement(tier=SubscriptionTier.SHARED),
        created_at=UtcDateTime.now(),
        updated_at=UtcDateTime.now(),
    )

    # Transition from PROVISIONING -> ACTIVE
    tenant.activate()
    assert tenant.status == TenantStatus.ACTIVE
    assert tenant.is_active() is True
    assert tenant.suspension_reason is None

    # Transition from ACTIVE -> SUSPENDED
    tenant.suspend("Non-payment")
    assert tenant.status == TenantStatus.SUSPENDED
    assert tenant.is_active() is False
    assert tenant.suspension_reason == "Non-payment"

    # Reject empty suspension reason
    with pytest.raises(ValidationError):
        tenant.suspend("   ")

    # Transition from SUSPENDED -> ACTIVE
    tenant.activate()
    assert tenant.status == TenantStatus.ACTIVE
    assert tenant.is_active() is True
    assert tenant.suspension_reason is None

    # Transition to DEACTIVATED (terminal)
    tenant.deactivate()
    assert tenant.status == TenantStatus.DEACTIVATED
    assert tenant.is_active() is False

    # Cannot activate or suspend after deactivation
    with pytest.raises(ValidationError):
        tenant.activate()

    with pytest.raises(ValidationError):
        tenant.suspend("Attempted reactivate")


def test_tenant_to_context_fail_closed() -> None:
    tenant = Tenant(
        id=TenantId.generate(),
        organization_id=OrganizationId.generate(),
        name="Production Tenant",
        status=TenantStatus.PROVISIONING,
        tier=SubscriptionTier.ENTERPRISE,
        entitlement=Entitlement(tier=SubscriptionTier.ENTERPRISE),
        created_at=UtcDateTime.now(),
        updated_at=UtcDateTime.now(),
    )

    # Fails closed when PROVISIONING
    with pytest.raises(TenancyViolationError):
        tenant.to_context()

    # Succeeds when ACTIVE
    tenant.activate()
    ctx = tenant.to_context()
    assert isinstance(ctx, TenantContext)
    assert ctx.tenant_id == tenant.id
    assert ctx.organization_id == tenant.organization_id
    assert ctx.tier == "enterprise"
    assert ctx.is_active is True

    # Fails closed when SUSPENDED
    tenant.suspend("Security review")
    with pytest.raises(TenancyViolationError):
        tenant.to_context()

    # Fails closed when DEACTIVATED
    tenant.deactivate()
    with pytest.raises(TenancyViolationError):
        tenant.to_context()
