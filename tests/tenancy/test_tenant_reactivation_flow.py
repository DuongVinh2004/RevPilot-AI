"""
RevPilot AI — TC-P07-005: Reactivation Verification Test
Specification: docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md §3.5
Conforms to INV-TEN-001, INV-TEN-002, and INV-REL-001.
"""

import pytest

from revpilot.shared.identifiers import OrganizationId, TenantId, UUIDv7
from revpilot.shared.errors import ValidationError
from revpilot.modules.tenancy import (
    InMemoryTenantRepository,
    TenantService,
    TenantProvisioningRequest,
    SubscriptionTier,
    TenantStatus,
)


def test_tenant_reactivation_flow_and_proof_validation():
    """
    TC-P07-005: Resolving suspension cause restores ACTIVE status with validated resolution proof.
    Reactivation fails closed if resolution proof is absent or whitespace.
    """
    repo = InMemoryTenantRepository()
    svc = TenantService(query_port=repo, command_port=repo)

    org = svc.create_organization("Epsilon Logistics")
    target_tid = TenantId.generate()

    req = TenantProvisioningRequest(
        request_id=UUIDv7.generate(),
        organization_id=org.id,
        name="Epsilon Freight",
        admin_email="billing@epsilon.com",
        tier=SubscriptionTier.SHARED,
        tenant_id=target_tid,
    )
    svc.provision_tenant_idempotent(req)
    svc.activate_tenant(target_tid)
    svc.suspend_tenant(target_tid, reason="PAYMENT_DEFAULT")

    # 1. Reject reactivation if proof is missing or whitespace
    with pytest.raises(ValidationError):
        svc.reactivate_tenant(target_tid, resolution_proof="")

    with pytest.raises(ValidationError):
        svc.reactivate_tenant(target_tid, resolution_proof="   ")

    # 2. Reactivate with valid payment clearance proof
    reactivated = svc.reactivate_tenant(
        target_tid,
        resolution_proof="INVOICE_PAID_REC_998822",
        actor="billing_admin",
    )
    assert reactivated.status == TenantStatus.ACTIVE
    assert reactivated.is_active() is True

    # Ingress traffic allowed again
    svc.check_ingress_allowed(target_tid)

    # 3. Idempotent reactivation call
    idemp_reactivated = svc.reactivate_tenant(
        target_tid,
        resolution_proof="INVOICE_PAID_REC_998822",
    )
    assert idemp_reactivated.status == TenantStatus.ACTIVE
