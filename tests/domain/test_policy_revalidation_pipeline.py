"""
RevPilot AI — Unit Tests for 6-Point Continuous Policy Revalidation Pipeline
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 3, §4
Conforms to AC-008, INV-ACT-001..004, INV-COST-001, INV-SEC-003:
  - 6 lifecycle checkpoints revalidate policies.
  - Policy changes prior to dispatch fail with ERR_POLICY_STALE.
  - Active safety kill switch halts with ERR_KILL_SWITCH_ACTIVE.
  - Budget exhaustion halts with ERR_BUDGET_EXCEEDED.
"""

from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_approval_modules():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.approval"):
            sys.modules.pop(mod, None)


@pytest.fixture
def approval_module():
    import revpilot.modules.approval as mod
    return mod


@pytest.fixture
def policy_module():
    import revpilot.modules.approval.policy as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_corp")


@pytest.fixture
def tenant_ctx(sample_tenant) -> TenantContext:
    return TenantContext(
        tenant_id=sample_tenant,
        organization_id=OrganizationId("org_sample"),
    )


@pytest.mark.asyncio
async def test_six_point_revalidation_success(
    approval_module, policy_module, sample_tenant, tenant_ctx
):
    """
    Valid approval request successfully passes all 6 lifecycle checkpoints
    when conditions remain compliant.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)
    reval_service = policy_module.PolicyRevalidationService()

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_DISPATCH",
        target_customer_id="cust_001",
        target_entity_refs=["order_123"],
        action_payload={"service": "EXPRESS"},
        estimated_cost_usd=Decimal("150.00"),
        policy_rules="policy_v1",
    )

    checkpoints = [
        policy_module.RevalidationCheckpoint.PRE_CREATION,
        policy_module.RevalidationCheckpoint.ON_SUBMISSION,
        policy_module.RevalidationCheckpoint.ON_APPROVAL,
        policy_module.RevalidationCheckpoint.PRE_DRY_RUN,
        policy_module.RevalidationCheckpoint.PRE_DISPATCH,
        policy_module.RevalidationCheckpoint.POST_RESULT,
    ]

    for cp in checkpoints:
        res = await reval_service.revalidate(
            ctx=tenant_ctx,
            approval=rec,
            checkpoint=cp,
            current_policy_digest=rec.policy_digest,
            is_kill_switch_active=False,
            budget_remaining_usd=Decimal("1000.00"),
        )
        assert res.is_success, f"Failed at checkpoint {cp}: {res.unwrap_error()}"


@pytest.mark.asyncio
async def test_stale_policy_fails_pre_dispatch_revalidation(
    approval_module, policy_module, sample_tenant, tenant_ctx
):
    """
    If active policy changes between approval and dispatch,
    pre-dispatch revalidation rejects with ERR_POLICY_STALE (AC-008).
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)
    reval_service = policy_module.PolicyRevalidationService()

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_DISPATCH",
        target_customer_id="cust_001",
        target_entity_refs=["order_123"],
        action_payload={"service": "EXPRESS"},
        estimated_cost_usd=Decimal("150.00"),
        policy_rules="policy_v1",
    )

    # Policy was updated in governance registry to policy_v2
    new_policy_digest = approval_module.ApprovalDigestHasher.compute_policy_digest("policy_v2_updated")

    res = await reval_service.revalidate(
        ctx=tenant_ctx,
        approval=rec,
        checkpoint=policy_module.RevalidationCheckpoint.PRE_DISPATCH,
        current_policy_digest=new_policy_digest,
    )

    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_POLICY_STALE"


@pytest.mark.asyncio
async def test_kill_switch_and_budget_exhaustion_at_revalidation(
    approval_module, policy_module, sample_tenant, tenant_ctx
):
    """
    Active kill-switch or depleted budget immediately halts revalidation.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)
    reval_service = policy_module.PolicyRevalidationService()

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_DISPATCH",
        target_customer_id="cust_001",
        target_entity_refs=["order_123"],
        action_payload={"service": "EXPRESS"},
        estimated_cost_usd=Decimal("150.00"),
        policy_rules="policy_v1",
    )

    # 1. Kill-switch activated
    res_kill = await reval_service.revalidate(
        ctx=tenant_ctx,
        approval=rec,
        checkpoint=policy_module.RevalidationCheckpoint.PRE_DISPATCH,
        is_kill_switch_active=True,
    )
    assert res_kill.is_failure
    assert res_kill.unwrap_error().code == "ERR_KILL_SWITCH_ACTIVE"

    # 2. Budget exhausted ($100 remaining < $150 estimated cost)
    res_budget = await reval_service.revalidate(
        ctx=tenant_ctx,
        approval=rec,
        checkpoint=policy_module.RevalidationCheckpoint.PRE_DISPATCH,
        budget_remaining_usd=Decimal("100.00"),
    )
    assert res_budget.is_failure
    assert res_budget.unwrap_error().code == "ERR_BUDGET_EXCEEDED"
