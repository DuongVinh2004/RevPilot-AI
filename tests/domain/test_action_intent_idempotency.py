"""
RevPilot AI — Domain Tests for Action Intent Tenant-Scoped Idempotency
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.2
Conforms to INV-ACT-001: Idempotency keys are unique per (tenant_id, idempotency_key).
Duplicate submissions return existing intent without duplicate dispatch.
"""

from __future__ import annotations
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext


@pytest.fixture(autouse=True)
def _isolate_action_module():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.action") or mod.startswith("revpilot.modules.approval"):
            sys.modules.pop(mod, None)


@pytest.fixture
def action_module():
    import revpilot.modules.action as mod
    return mod


@pytest.fixture
def approval_module():
    import revpilot.modules.approval as mod
    return mod


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha_logistics")


@pytest.fixture
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta_adversary")


@pytest.mark.asyncio
async def test_action_intent_idempotency_deduplication(
    action_module, approval_module, tenant_alpha
):
    """
    Submitting duplicate intents with the same idempotency key
    returns the exact same original record.
    """
    intent_repo = action_module.InMemoryActionIntentRepository()
    ledger_repo = action_module.InMemoryActionLedgerRepository()
    service = action_module.ActionLedgerService(intent_repo, ledger_repo)

    approval_repo = approval_module.InMemoryApprovalRepository()
    approval_svc = approval_module.ApprovalService(approval_repo)

    ctx_alpha = TenantContext(
        tenant_id=tenant_alpha,
        organization_id=OrganizationId("org_alpha"),
    )

    # 1. Create and approve request
    app_rec = await approval_svc.create_request(
        tenant_id=tenant_alpha,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_EXPEDITE",
        target_customer_id="cust_001",
        target_entity_refs=["ship_01"],
        action_payload={"speed": "FAST"},
        estimated_cost_usd=Decimal("100.00"),
    )
    approved_rec = await approval_svc.grant_approval(
        tenant_id=tenant_alpha,
        approval_id=app_rec.approval_id,
        approver_principal_id="usr_manager",
        approver_tier=1,
        expected_digest=app_rec.payload_digest,
        is_human=True,
    )

    idempotency_key = "idemp_unique_dispatch_999"

    # 2. First submission
    intent1 = await service.create_intent(
        ctx=ctx_alpha,
        approval=approved_rec,
        idempotency_key=idempotency_key,
        classification=action_module.ActionClassification.REVERSIBLE,
    )

    # 3. Duplicate submission
    intent2 = await service.create_intent(
        ctx=ctx_alpha,
        approval=approved_rec,
        idempotency_key=idempotency_key,
        classification=action_module.ActionClassification.REVERSIBLE,
    )

    # Must return exact same intent ID
    assert intent1.intent_id == intent2.intent_id
    assert intent1.created_at == intent2.created_at


@pytest.mark.asyncio
async def test_unapproved_action_intent_fails_closed(
    action_module, approval_module, tenant_alpha
):
    """Live intent creation for an unapproved request raises ERR_APPROVAL_NOT_GRANTED."""
    intent_repo = action_module.InMemoryActionIntentRepository()
    ledger_repo = action_module.InMemoryActionLedgerRepository()
    service = action_module.ActionLedgerService(intent_repo, ledger_repo)

    approval_repo = approval_module.InMemoryApprovalRepository()
    approval_svc = approval_module.ApprovalService(approval_repo)

    ctx_alpha = TenantContext(
        tenant_id=tenant_alpha,
        organization_id=OrganizationId("org_alpha"),
    )

    unapproved_rec = await approval_svc.create_request(
        tenant_id=tenant_alpha,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_EXPEDITE",
        target_customer_id="cust_001",
        target_entity_refs=["ship_01"],
        action_payload={"speed": "FAST"},
        estimated_cost_usd=Decimal("100.00"),
    )

    with pytest.raises(action_module.ActionError) as exc_info:
        await service.create_intent(
            ctx=ctx_alpha,
            approval=unapproved_rec,
            idempotency_key="idemp_unapproved_attempt",
            classification=action_module.ActionClassification.REVERSIBLE,
            is_dry_run=False,
        )
    assert exc_info.value.code == "ERR_APPROVAL_NOT_GRANTED"
