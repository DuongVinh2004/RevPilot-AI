"""
RevPilot AI — Security Tests for Approval Replay and Self-Approval Protection
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 2, §3.1
Conforms to INV-ACT-003, AC-008:
  - Re-approving an already approved request raises ERR_ALREADY_USED.
  - Automated agents or service accounts attempting self-approval raise ERR_AGENT_SELF_APPROVAL.
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
async def test_replay_approval_rejected(approval_module, sample_tenant):
    """Attempting to approve an already approved request fails with ERR_ALREADY_USED."""
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="WAREHOUSE_RESCHEDULE",
        target_customer_id="cust_001",
        target_entity_refs=["wh_slot_10"],
        action_payload={"slot": 10},
        estimated_cost_usd=Decimal("20.00"),
    )

    # First approval succeeds
    await service.grant_approval(
        tenant_id=sample_tenant,
        approval_id=rec.approval_id,
        approver_principal_id="usr_ops_lead",
        approver_tier=1,
        expected_digest=rec.payload_digest,
        is_human=True,
    )

    # Replay attempt fails
    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.grant_approval(
            tenant_id=sample_tenant,
            approval_id=rec.approval_id,
            approver_principal_id="usr_adversary",
            approver_tier=1,
            expected_digest=rec.payload_digest,
            is_human=True,
        )
    assert exc_info.value.code == "ERR_ALREADY_USED"


@pytest.mark.asyncio
async def test_agent_self_approval_prohibited(approval_module, sample_tenant):
    """AI agents, automated planners, or service accounts cannot approve actions (INV-ACT-003)."""
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="WAREHOUSE_RESCHEDULE",
        target_customer_id="cust_001",
        target_entity_refs=["wh_slot_10"],
        action_payload={"slot": 10},
        estimated_cost_usd=Decimal("20.00"),
    )

    # Non-human principal attempting approval
    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.grant_approval(
            tenant_id=sample_tenant,
            approval_id=rec.approval_id,
            approver_principal_id="agent_planner_autonomous",
            approver_tier=3,
            expected_digest=rec.payload_digest,
            is_human=False,  # Automated agent!
        )
    assert exc_info.value.code == "ERR_AGENT_SELF_APPROVAL"
