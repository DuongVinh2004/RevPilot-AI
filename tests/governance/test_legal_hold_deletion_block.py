"""
RevPilot AI — TC-P07-009: Legal Hold Deletion Block Test
Specification: docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md §3.6
Specification: docs/18-data-governance/DATA-GOVERNANCE.md §5
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
    TenantCascadeDeletionSaga,
    LegalHoldActiveError,
)


@pytest.mark.asyncio
async def test_legal_hold_deletion_block_fails_closed_with_409():
    """
    TC-P07-009: Deletion requests targeting a tenant under active legal hold
    must fail closed immediately with error LEGAL_HOLD_ACTIVE (HTTP 409 Conflict).
    Only upon authorized legal counsel release can deletion proceed.
    """
    repo = InMemoryTenantRepository()
    svc = TenantService(query_port=repo, command_port=repo)
    saga = TenantCascadeDeletionSaga(tenant_service=svc)

    org = svc.create_organization("Theta Compliance Corp")
    target_tid = TenantId.generate()

    req = TenantProvisioningRequest(
        request_id=UUIDv7.generate(),
        organization_id=org.id,
        name="Theta Regulated Tenant",
        admin_email="legal@theta.com",
        tier=SubscriptionTier.REGULATED,
        tenant_id=target_tid,
    )
    svc.provision_tenant_idempotent(req)
    svc.activate_tenant(target_tid)

    # 1. Apply formal Legal Hold
    matter_id = "MATTER-SEC-2026-0904"
    record = svc.apply_legal_hold(
        tenant_id=target_tid,
        matter_id=matter_id,
        justification="Subpoena civil litigation in Southern District",
        actor="compliance_officer_judy",
    )
    assert record.is_active is True
    assert svc.is_under_legal_hold(target_tid) is True
    assert svc.get_tenant(target_tid).status == TenantStatus.LEGAL_HOLD

    # 2. Deletion attempt while under legal hold MUST fail closed (409 Conflict)
    with pytest.raises(LegalHoldActiveError) as exc_info:
        await saga.execute_cascade_deletion(
            tenant_id=target_tid,
            dual_approvers=["admin_alice", "admin_bob"],
        )

    assert exc_info.value.code == "LEGAL_HOLD_ACTIVE"
    assert "409" in exc_info.value.message or "legal hold" in exc_info.value.message.lower()

    # Invariant: Tenant status remains LEGAL_HOLD, zero deletion steps executed
    assert svc.get_tenant(target_tid).status == TenantStatus.LEGAL_HOLD
    assert len(saga.issued_certificates) == 0

    # 3. Release Legal Hold upon formal legal release
    svc.release_legal_hold(
        tenant_id=target_tid,
        matter_id=matter_id,
        actor="general_counsel",
        restore_status=TenantStatus.SUSPENDED,
    )
    assert svc.is_under_legal_hold(target_tid) is False
    assert svc.get_tenant(target_tid).status == TenantStatus.SUSPENDED

    # 4. Deletion succeeds now that legal hold has been officially lifted
    cert = await saga.execute_cascade_deletion(
        tenant_id=target_tid,
        dual_approvers=["admin_alice", "admin_bob"],
    )
    assert cert.tenant_id == target_tid
    assert svc.get_tenant(target_tid).status == TenantStatus.DELETED
