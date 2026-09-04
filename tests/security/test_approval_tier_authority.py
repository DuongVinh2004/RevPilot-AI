"""
RevPilot AI — Security Tests for Tiered Approval Authority and Separation of Duties
Specification: docs/14-iam/IAM-SPEC.md §7
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 2, §4
Conforms to INV-ACT-003, AC-008:
  - Tier-1 approver attempting to approve $300 action is blocked.
  - Proposer cannot self-approve actions > $250.00 (Separation of duties).
"""

from __future__ import annotations
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.context import PrincipalContext


@pytest.fixture(autouse=True)
def _isolate_approval_modules():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.approval"):
            sys.modules.pop(mod, None)


@pytest.fixture
def policy_module():
    import revpilot.modules.approval.policy as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_corp")


def test_tier_1_approver_spend_limit_enforced(policy_module, sample_tenant):
    """
    Tier-1 approver has max spend limit $250.00.
    Approving $200 succeeds; approving $300 is blocked.
    """
    verifier = policy_module.AuthorityVerifier()

    tier1_principal = PrincipalContext(
        principal_id=PrincipalId("usr_tier1_operator"),
        tenant_id=sample_tenant,
        permissions=frozenset({"approval:tier_1"}),
    )

    # 1. Action cost $200.00 (Tier 1 requirement) -> Allowed
    assert verifier.verify_approver_authority(
        principal=tier1_principal,
        cost_usd=Decimal("200.00"),
        required_tier=policy_module.ApprovalTier.TIER_1_OPERATIONAL,
    ) is True

    # 2. Action cost $300.00 -> Blocked (exceeds $250 ceiling)
    assert verifier.verify_approver_authority(
        principal=tier1_principal,
        cost_usd=Decimal("300.00"),
        required_tier=policy_module.ApprovalTier.TIER_1_OPERATIONAL,
    ) is False


def test_tier_2_and_tier_3_authority_limits(policy_module, sample_tenant):
    """
    Tier-2 has max spend $1,000.00; Tier-3 has max spend $10,000.00.
    Actions exceeding $10,000.00 require special policy exceptions and are blocked.
    """
    verifier = policy_module.AuthorityVerifier()

    tier2_principal = PrincipalContext(
        principal_id=PrincipalId("usr_tier2_director"),
        tenant_id=sample_tenant,
        permissions=frozenset({"approval:tier_2"}),
    )
    tier3_principal = PrincipalContext(
        principal_id=PrincipalId("usr_tier3_vp"),
        tenant_id=sample_tenant,
        permissions=frozenset({"approval:tier_3"}),
    )

    # Tier-2: $800 allowed, $1,500 blocked
    assert verifier.verify_approver_authority(
        tier2_principal, Decimal("800.00"), policy_module.ApprovalTier.TIER_2_TACTICAL
    ) is True
    assert verifier.verify_approver_authority(
        tier2_principal, Decimal("1500.00"), policy_module.ApprovalTier.TIER_2_TACTICAL
    ) is False

    # Tier-3: $5,000 allowed, $12,000 blocked (> $10,000 hard ceiling)
    assert verifier.verify_approver_authority(
        tier3_principal, Decimal("5000.00"), policy_module.ApprovalTier.TIER_3_EXECUTIVE
    ) is True
    assert verifier.verify_approver_authority(
        tier3_principal, Decimal("12000.00"), policy_module.ApprovalTier.TIER_3_EXECUTIVE
    ) is False


def test_separation_of_duties_proposer_disqualification(policy_module):
    """
    Proposer cannot act as sole approver for action spend > $250.00.
    For small actions <= $250.00, self-approval is permitted under Tier-1 authority.
    """
    verifier = policy_module.AuthorityVerifier()

    proposer = "usr_proposer_123"

    # Self-approval on $150 action is permitted (<= $250)
    assert verifier.check_separation_of_duties(
        proposer_id=proposer,
        approver_id=proposer,
        cost_usd=Decimal("150.00"),
    ) is True

    # Self-approval on $500 action is blocked (> $250)
    assert verifier.check_separation_of_duties(
        proposer_id=proposer,
        approver_id=proposer,
        cost_usd=Decimal("500.00"),
    ) is False

    # Different approver is permitted
    assert verifier.check_separation_of_duties(
        proposer_id=proposer,
        approver_id="usr_distinct_approver",
        cost_usd=Decimal("500.00"),
    ) is True
