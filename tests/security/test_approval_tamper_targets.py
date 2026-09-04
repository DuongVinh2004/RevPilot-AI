"""
RevPilot AI — Security Tests for Approval Target Tampering Rejection
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 1
Conforms to INV-ACT-002, AC-008: Altering target_entity_refs invalidates digest
and immediately halts approval with ERR_APPROVAL_DIGEST_MISMATCH.
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
async def test_tampered_target_entity_refs_rejected(approval_module, sample_tenant):
    """
    Adding, removing, or modifying target entity references changes the digest
    and halts approval.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    original_targets = ["order_alpha_01", "order_alpha_02"]
    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="REROUTE_SHIPMENT",
        target_customer_id="cust_001",
        target_entity_refs=original_targets,
        action_payload={"hub": "HUB_CHICAGO"},
        estimated_cost_usd=Decimal("75.00"),
    )

    # 1. Adversary injects extra unauthorized target
    tampered_targets = ["order_alpha_01", "order_alpha_02", "order_unauthorized_99"]
    tampered_rec = rec.model_copy(update={"target_entity_refs": tampered_targets})
    await repo.update(tampered_rec)

    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.grant_approval(
            tenant_id=sample_tenant,
            approval_id=rec.approval_id,
            approver_principal_id="usr_ops_lead",
            approver_tier=1,
            expected_digest=rec.payload_digest,
            is_human=True,
        )
    assert exc_info.value.code == "ERR_APPROVAL_DIGEST_MISMATCH"


@pytest.mark.asyncio
async def test_swapped_target_entity_refs_rejected(approval_module, sample_tenant):
    """
    Swapping one target for another is immediately caught by digest check.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="REROUTE_SHIPMENT",
        target_customer_id="cust_001",
        target_entity_refs=["target_legitimate"],
        action_payload={"hub": "HUB_CHICAGO"},
        estimated_cost_usd=Decimal("75.00"),
    )

    tampered_rec = rec.model_copy(update={"target_entity_refs": ["target_adversary"]})
    await repo.update(tampered_rec)

    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.grant_approval(
            tenant_id=sample_tenant,
            approval_id=rec.approval_id,
            approver_principal_id="usr_ops_lead",
            approver_tier=1,
            expected_digest=rec.payload_digest,
            is_human=True,
        )
    assert exc_info.value.code == "ERR_APPROVAL_DIGEST_MISMATCH"
