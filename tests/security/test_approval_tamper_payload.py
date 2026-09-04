"""
RevPilot AI — Security Tests for Approval Payload Tamper Rejection
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 1
Conforms to INV-ACT-002, AC-008: Any byte change in action_payload invalidates digest
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
async def test_tampered_payload_parameter_rejected(approval_module, sample_tenant):
    """
    Tampering with a single parameter in action_payload (e.g. discount amount 50 -> 500)
    causes ERR_APPROVAL_DIGEST_MISMATCH on grant_approval.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    original_payload = {"service_credit": 50, "voucher_code": "RET50"}
    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CUSTOMER_SERVICE_CREDIT",
        target_customer_id="cust_001",
        target_entity_refs=["acct_001"],
        action_payload=original_payload,
        estimated_cost_usd=Decimal("50.00"),
    )

    # Adversary directly tampers with storage payload
    tampered_payload = {"service_credit": 500, "voucher_code": "RET50"}
    tampered_rec = rec.model_copy(update={"action_payload": tampered_payload})
    await repo.update(tampered_rec)

    # Approver signs with original expected_digest
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
async def test_tampered_cost_rejected(approval_module, sample_tenant):
    """
    Tampering with estimated_cost_usd invalidates the digest and causes rejection.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CUSTOMER_SERVICE_CREDIT",
        target_customer_id="cust_001",
        target_entity_refs=["acct_001"],
        action_payload={"credit": 100},
        estimated_cost_usd=Decimal("100.00"),
    )

    # Tamper with cost
    tampered_rec = rec.model_copy(update={"estimated_cost_usd": Decimal("10.00")})
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
