"""
RevPilot AI — Unit Tests for Approval Request Revocation
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.1
Conforms to AC-008: Approvals can be revoked prior to physical execution,
and revoked requests cannot be approved or dispatched.
"""

from __future__ import annotations
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7


@pytest.fixture(autouse=True)
def _isolate_approval_module():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.approval"):
            sys.modules.pop(mod, None)


@pytest.fixture
def approval_module():
    import revpilot.modules.approval as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_corp")


@pytest.mark.asyncio
async def test_pending_request_revocation(approval_module, sample_tenant):
    """Pending request can be revoked and subsequently rejected from approval."""
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="COURIER_EXPEDITE",
        target_customer_id="cust_001",
        target_entity_refs=["parcel_123"],
        action_payload={"fee": 30},
        estimated_cost_usd=Decimal("30.00"),
    )

    # Revoke pending request
    revoked = await service.revoke_approval(
        tenant_id=sample_tenant,
        approval_id=rec.approval_id,
        revoker_principal_id="usr_incident_commander",
        revocation_reason="Order cancelled by customer",
    )
    assert revoked.status == approval_module.ApprovalStatus.REVOKED
    assert revoked.revocation_reason == "Order cancelled by customer"

    # Attempting to approve revoked request fails closed
    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.grant_approval(
            tenant_id=sample_tenant,
            approval_id=rec.approval_id,
            approver_principal_id="usr_ops_lead",
            approver_tier=1,
            expected_digest=rec.payload_digest,
            is_human=True,
        )
    assert exc_info.value.code == "ERR_APPROVAL_REVOKED"


@pytest.mark.asyncio
async def test_approved_request_revocation_before_dispatch(approval_module, sample_tenant):
    """An approved request can be revoked before physical execution starts."""
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="COURIER_EXPEDITE",
        target_customer_id="cust_001",
        target_entity_refs=["parcel_123"],
        action_payload={"fee": 30},
        estimated_cost_usd=Decimal("30.00"),
    )

    approved = await service.grant_approval(
        tenant_id=sample_tenant,
        approval_id=rec.approval_id,
        approver_principal_id="usr_ops_lead",
        approver_tier=1,
        expected_digest=rec.payload_digest,
        is_human=True,
    )
    assert approved.status == approval_module.ApprovalStatus.APPROVED

    # Revoke before execution starts
    revoked = await service.revoke_approval(
        tenant_id=sample_tenant,
        approval_id=rec.approval_id,
        revoker_principal_id="usr_risk_lead",
        revocation_reason="Carrier network failure",
    )
    assert revoked.status == approval_module.ApprovalStatus.REVOKED
