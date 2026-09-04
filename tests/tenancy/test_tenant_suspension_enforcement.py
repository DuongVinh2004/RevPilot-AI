"""
RevPilot AI — TC-P07-004: Suspension Ingress Halting Test
Specification: docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md §3.4
Conforms to INV-TEN-001, INV-TEN-003, and INV-REL-001.
"""

import pytest

from revpilot.shared.identifiers import OrganizationId, TenantId, UUIDv7
from revpilot.modules.tenancy import (
    InMemoryTenantRepository,
    TenantService,
    TenantProvisioningRequest,
    SubscriptionTier,
    TenantStatus,
    TenantSuspendedError,
)


def test_tenant_suspension_halts_ingress_and_is_idempotent():
    """
    TC-P07-004: Suspension immediately blocks 100% of user API and webhook ingress traffic with 403.
    Re-suspending an already suspended tenant returns current status idempotently.
    """
    repo = InMemoryTenantRepository()
    svc = TenantService(query_port=repo, command_port=repo)

    org = svc.create_organization("Delta Corp")
    target_tid = TenantId.generate()

    req = TenantProvisioningRequest(
        request_id=UUIDv7.generate(),
        organization_id=org.id,
        name="Delta Operations",
        admin_email="admin@delta.com",
        tier=SubscriptionTier.SHARED,
        tenant_id=target_tid,
    )
    svc.provision_tenant_idempotent(req)
    svc.activate_tenant(target_tid)

    # Verify ingress allowed while ACTIVE
    svc.check_ingress_allowed(target_tid)

    # 1. Suspend tenant for security suspicion
    suspended = svc.suspend_tenant(target_tid, reason="SECURITY_BREACH_SUSPECTED")
    assert suspended.status == TenantStatus.SUSPENDED
    assert suspended.suspension_reason == "SECURITY_BREACH_SUSPECTED"

    # 2. Idempotency verification: suspending again returns suspended tenant
    suspended_again = svc.suspend_tenant(target_tid, reason="ADMIN_MANUAL")
    assert suspended_again.status == TenantStatus.SUSPENDED

    # 3. Ingress gating: raises TenantSuspendedError (HTTP 403)
    with pytest.raises(TenantSuspendedError) as exc_info:
        svc.check_ingress_allowed(target_tid)

    assert exc_info.value.code == "TENANT_SUSPENDED"
    assert "suspended" in exc_info.value.message.lower()

    # Context generation fails closed
    with pytest.raises(Exception):
        suspended.to_context()
