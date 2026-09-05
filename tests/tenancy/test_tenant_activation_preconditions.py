"""
RevPilot AI — TC-P07-003: Activation Precondition Check Test
Specification: docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md §3.3
Conforms to INV-TEN-001, INV-TEN-002, and NFR-TEN-001.
"""

import pytest

from revpilot.shared.identifiers import OrganizationId, TenantId, UUIDv7
from revpilot.modules.tenancy import (
    InMemoryTenantRepository,
    TenantService,
    TenantProvisioningRequest,
    SubscriptionTier,
    TenantStatus,
    IsolationVerificationFailedError,
)


def test_tenant_activation_preconditions_enforced():
    """
    TC-P07-003: Tenant cannot transition to ACTIVE if any isolation probe fails (TEST-TEN-001..011).
    Activation succeeds only when isolation probes evaluate 100% PASS.
    """
    repo = InMemoryTenantRepository()
    svc = TenantService(query_port=repo, command_port=repo)

    org = svc.create_organization("Global Carrier Group")
    target_tid = TenantId.generate()

    req = TenantProvisioningRequest(
        request_id=UUIDv7.generate(),
        organization_id=org.id,
        name="Carrier Air",
        admin_email="carrier@gcg.com",
        tier=SubscriptionTier.ENTERPRISE,
        tenant_id=target_tid,
    )
    svc.provision_tenant_idempotent(req)

    # 1. Probes fail (e.g. cross-tenant vector leak detected)
    def failing_probe_runner(tid):
        return {
            "TEST-TEN-001_RLS_STORAGE": True,
            "TEST-TEN-004_REDIS_NAMESPACING": True,
            "TEST-TEN-007_VECTOR_CROSS_TENANT_LEAK": False,  # Failed!
        }

    with pytest.raises(IsolationVerificationFailedError) as exc_info:
        svc.activate_tenant_with_preconditions(target_tid, probe_runner=failing_probe_runner)

    assert exc_info.value.code == "ISOLATION_VERIFICATION_FAILED"
    persisted = svc.get_tenant(target_tid)
    assert persisted.status == TenantStatus.ACTIVATING  # Remained in activating, not active

    # 2. Probes pass 100%
    def passing_probe_runner(tid):
        return {
            "TEST-TEN-001_RLS_STORAGE": True,
            "TEST-TEN-004_REDIS_NAMESPACING": True,
            "TEST-TEN-007_VECTOR_CROSS_TENANT_LEAK": True,
            "TEST-TEN-011_AUDIT_PARTITION_ISOLATION": True,
        }

    activated_tenant = svc.activate_tenant_with_preconditions(target_tid, probe_runner=passing_probe_runner)
    assert activated_tenant.status == TenantStatus.ACTIVE
    assert activated_tenant.is_active() is True

    # Now valid TenantContext can be generated
    ctx = activated_tenant.to_context()
    assert ctx.tenant_id == target_tid
    assert ctx.is_active is True
