"""
RevPilot AI — Security Tests for Approval Multi-Tenant Isolation Airgap
Specification: docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.1
Conforms to INV-TEN-001..003: Strict tenant partition across all approval services.
"""

from __future__ import annotations
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext


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
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha_logistics")


@pytest.fixture
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta_adversary")


@pytest.mark.asyncio
async def test_cross_tenant_approval_and_amendment_blocked(
    approval_module, tenant_alpha, tenant_beta
):
    """
    Tenant Beta cannot view, approve, or amend approval requests belonging to Tenant Alpha.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    # Created under Tenant Alpha
    rec_alpha = await service.create_request(
        tenant_id=tenant_alpha,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_EXPEDITE",
        target_customer_id="cust_alpha_01",
        target_entity_refs=["ship_alpha_10"],
        action_payload={"priority": "HIGH"},
        estimated_cost_usd=Decimal("150.00"),
    )

    # 1. Tenant Beta attempting to grant approval is rejected with ERR_TENANT_MISMATCH
    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.grant_approval(
            tenant_id=tenant_beta,
            approval_id=rec_alpha.approval_id,
            approver_principal_id="usr_beta_admin",
            approver_tier=2,
            expected_digest=rec_alpha.payload_digest,
            is_human=True,
        )
    assert exc_info.value.code == "ERR_TENANT_MISMATCH"

    # 2. Tenant Beta attempting to amend request is rejected with ERR_TENANT_MISMATCH
    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.amend_request(
            tenant_id=tenant_beta,
            approval_id=rec_alpha.approval_id,
            modifier_principal_id="usr_beta_admin",
            new_payload={"priority": "MALICIOUS"},
        )
    assert exc_info.value.code == "ERR_TENANT_MISMATCH"


@pytest.mark.asyncio
async def test_cross_tenant_revalidation_fails_closed(
    approval_module, policy_module, tenant_alpha, tenant_beta
):
    """
    Revalidation pipeline rejects cross-tenant context with ERR_TENANT_MISMATCH.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)
    reval_service = policy_module.PolicyRevalidationService()

    rec_alpha = await service.create_request(
        tenant_id=tenant_alpha,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_EXPEDITE",
        target_customer_id="cust_alpha_01",
        target_entity_refs=["ship_alpha_10"],
        action_payload={"priority": "HIGH"},
        estimated_cost_usd=Decimal("150.00"),
    )

    # Adversary context under Tenant Beta
    ctx_beta = TenantContext(
        tenant_id=tenant_beta,
        organization_id=OrganizationId("org_beta"),
    )

    res = await reval_service.revalidate(
        ctx=ctx_beta,
        approval=rec_alpha,
        checkpoint=policy_module.RevalidationCheckpoint.PRE_DISPATCH,
    )

    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_TENANT_MISMATCH"
