"""
RevPilot AI — TC-P07-008: Cascade Deletion Propagation Test
Specification: docs/18-data-governance/DATA-GOVERNANCE.md §4
Specification: docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md §3.9
Conforms to INV-TEN-001, INV-ACT-003, and NFR-REC-001.
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
    TenantCascadeDeletionSaga,
    DeletionIncompleteError,
)


@pytest.mark.asyncio
async def test_cascade_deletion_purges_all_10_stores_and_issues_certificate():
    """
    TC-P07-008: Deletion saga cascades across all 10 persistent and projected stores,
    enforcing dual human approval and issuing an immutable DeletionCertificate.
    """
    repo = InMemoryTenantRepository()
    svc = TenantService(query_port=repo, command_port=repo)
    saga = TenantCascadeDeletionSaga(tenant_service=svc)

    org = svc.create_organization("Zeta Global")
    target_tid = TenantId.generate()

    req = TenantProvisioningRequest(
        request_id=UUIDv7.generate(),
        organization_id=org.id,
        name="Zeta Freight",
        admin_email="admin@zeta.com",
        tier=SubscriptionTier.SHARED,
        tenant_id=target_tid,
    )
    svc.provision_tenant_idempotent(req)
    svc.activate_tenant(target_tid)
    svc.suspend_tenant(target_tid, reason="CONTRACT_TERMINATED")

    # 1. Rejects single-approver deletion (INV-ACT-003)
    with pytest.raises(ValidationError) as exc_info:
        await saga.execute_cascade_deletion(
            tenant_id=target_tid,
            dual_approvers=["usr_admin_1"],
        )
    assert "dual human approval" in exc_info.value.message.lower()

    # 2. Rejects if subsystem fails (e.g. vector store)
    with pytest.raises(DeletionIncompleteError) as exc_info:
        await saga.execute_cascade_deletion(
            tenant_id=target_tid,
            dual_approvers=["usr_admin_1", "usr_admin_2"],
            simulate_step_failure="purge_vector_embeddings",
        )
    assert exc_info.value.code == "DELETION_INCOMPLETE"
    assert svc.get_tenant(target_tid).status == TenantStatus.DELETION_STAGED

    # 3. Successful full 10-store cascade deletion with dual approval
    certificate = await saga.execute_cascade_deletion(
        tenant_id=target_tid,
        dual_approvers=["usr_admin_1", "usr_compliance_lead"],
    )

    assert certificate.tenant_id == target_tid
    assert len(certificate.purged_partitions) == 10
    assert len(certificate.deletion_digest_sha256) == 64
    assert certificate.dual_approvers == ["usr_admin_1", "usr_compliance_lead"]

    # Verify terminal status in tenancy store
    deleted_tenant = svc.get_tenant(target_tid)
    assert deleted_tenant.status == TenantStatus.DELETED
    assert deleted_tenant.is_active() is False

    # Ingress and context generation are strictly barred
    with pytest.raises(Exception):
        deleted_tenant.to_context()
