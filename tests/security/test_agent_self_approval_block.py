"""
RevPilot AI — Security Tests for Agent Self-Approval Blocking
Specification: docs/14-iam/IAM-SPEC.md §7.2
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 2
Conforms to INV-ACT-003: AI agents, automated planners, and LLM evaluators
are strictly prohibited from approving actions or signing approval requests.
"""

from __future__ import annotations
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, PrincipalId, UUIDv7
from revpilot.shared.context import PrincipalContext


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


def test_agent_delegate_has_zero_approval_tier(policy_module, sample_tenant):
    """
    Principals bearing agent_delegate role have 0 approval tier regardless
    of assigned permissions (INV-ACT-003).
    """
    verifier = policy_module.AuthorityVerifier()

    agent_principal = PrincipalContext(
        principal_id=PrincipalId("usr_agent_investigator_v1"),
        tenant_id=sample_tenant,
        roles=frozenset({"agent_delegate"}),
        permissions=frozenset({"approval:tier_3"}),  # Attempted escalation
    )

    assert verifier.is_agent_principal(agent_principal) is True
    assert verifier.get_principal_tier(agent_principal) == 0
    assert verifier.verify_approver_authority(
        principal=agent_principal,
        cost_usd=Decimal("50.00"),
        required_tier=policy_module.ApprovalTier.TIER_1_OPERATIONAL,
    ) is False


@pytest.mark.asyncio
async def test_agent_calling_grant_approval_fails_closed(approval_module, sample_tenant):
    """
    Calling ApprovalService.grant_approval with is_human=False or agent identity
    raises ERR_AGENT_SELF_APPROVAL.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_DISPATCH",
        target_customer_id="cust_001",
        target_entity_refs=["order_01"],
        action_payload={"carrier": "mock"},
        estimated_cost_usd=Decimal("100.00"),
    )

    # Agent identity calling grant_approval
    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.grant_approval(
            tenant_id=sample_tenant,
            approval_id=rec.approval_id,
            approver_principal_id="agent_planner_daemon",
            approver_tier=2,
            expected_digest=rec.payload_digest,
            is_human=False,
        )
    assert exc_info.value.code == "ERR_AGENT_SELF_APPROVAL"
