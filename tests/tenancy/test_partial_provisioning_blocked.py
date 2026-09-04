"""
RevPilot AI — TC-P07-002: Partial Provisioning Rejection Test
Specification: docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md §3.2
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
    PartialProvisioningError,
)


def test_partial_provisioning_failure_rolls_back_and_marks_provision_failed():
    """
    TC-P07-002: When resource allocation fails at any step (e.g. S3 object prefix or vector collection),
    allocated resources are rolled back, tenant state transitions to PROVISION_FAILED,
    and activation remains strictly prohibited.
    """
    repo = InMemoryTenantRepository()
    svc = TenantService(query_port=repo, command_port=repo)

    org = svc.create_organization("Beta Logistics")
    failed_tid = TenantId.generate()

    req = TenantProvisioningRequest(
        request_id=UUIDv7.generate(),
        organization_id=org.id,
        name="Beta Fleet",
        admin_email="fleet@beta.com",
        tier=SubscriptionTier.SHARED,
        tenant_id=failed_tid,
        idempotency_key=f"idemp_fail_{failed_tid}",
    )

    # Simulate failure at S3 bucket prefix creation step
    with pytest.raises(PartialProvisioningError) as exc_info:
        svc.provision_tenant_idempotent(req, simulate_step_failure="s3_object_prefix")

    assert exc_info.value.code == "PARTIAL_PROVISIONING_BLOCKED"
    assert "s3_object_prefix" in exc_info.value.message

    # Verify repository state: Tenant exists in PROVISION_FAILED, cannot be activated
    persisted = svc.get_tenant(failed_tid)
    assert persisted.status == TenantStatus.PROVISION_FAILED
    assert len(svc._allocated_resources[str(failed_tid)]) == 0  # Resources completely cleaned up

    # Fail-closed invariant: Context derivation or activation fails closed
    with pytest.raises(Exception):
        persisted.to_context()
