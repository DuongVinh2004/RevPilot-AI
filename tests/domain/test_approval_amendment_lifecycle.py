"""
RevPilot AI — Unit Tests for Approval Amendment and Supersession Lifecycle
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.1
Conforms to AC-008: Amending any action payload supersedes the original request,
generates a fresh PENDING request with recomputed digest, and requires fresh human approval.
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
async def test_approval_amendment_supersession(approval_module, sample_tenant):
    """
    Amending an approval request transitions the original to SUPERSEDED,
    creates a new PENDING request pointing to original via causation_id,
    and requires fresh human approval.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    initial_payload = {"service": "STANDARD_TRUCK", "rate_usd": 120}
    original = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_DISPATCH",
        target_customer_id="cust_001",
        target_entity_refs=["shipment_55"],
        action_payload=initial_payload,
        estimated_cost_usd=Decimal("120.00"),
    )

    # Amend the request with upgraded service and cost
    amended_payload = {"service": "EXPEDITED_AIR", "rate_usd": 280}
    superseded, fresh_req = await service.amend_request(
        tenant_id=sample_tenant,
        approval_id=original.approval_id,
        modifier_principal_id="usr_logistics_planner",
        new_payload=amended_payload,
        new_cost_usd=Decimal("280.00"),
    )

    # 1. Original record is now SUPERSEDED
    assert superseded.status == approval_module.ApprovalStatus.SUPERSEDED
    assert superseded.superseded_by == fresh_req.approval_id

    # 2. Attempting to approve superseded original fails
    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.grant_approval(
            tenant_id=sample_tenant,
            approval_id=original.approval_id,
            approver_principal_id="usr_director",
            approver_tier=2,
            expected_digest=original.payload_digest,
            is_human=True,
        )
    assert exc_info.value.code == "ERR_INVALID_APPROVAL_STATE"

    # 3. Fresh request is PENDING and has recomputed digest
    assert fresh_req.status == approval_module.ApprovalStatus.PENDING
    assert fresh_req.causation_id == original.approval_id
    assert fresh_req.estimated_cost_usd == Decimal("280.00")
    assert fresh_req.required_approval_tier == 2  # Cost > 250 -> Tier 2
    assert fresh_req.payload_digest != original.payload_digest

    # 4. Approving fresh request with correct new digest succeeds
    approved_fresh = await service.grant_approval(
        tenant_id=sample_tenant,
        approval_id=fresh_req.approval_id,
        approver_principal_id="usr_director",
        approver_tier=2,
        expected_digest=fresh_req.payload_digest,
        is_human=True,
    )
    assert approved_fresh.status == approval_module.ApprovalStatus.APPROVED
    assert approved_fresh.approver_principal_id == "usr_director"
