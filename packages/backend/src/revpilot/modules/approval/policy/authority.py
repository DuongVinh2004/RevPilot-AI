"""
RevPilot AI — Tiered Approval Authority and Separation of Duties
Specification: docs/14-iam/IAM-SPEC.md §7
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 2, §4
Conforms to INV-ACT-003, AC-008, and ADR-0002.
"""

from __future__ import annotations
from decimal import Decimal
from enum import IntEnum

from revpilot.shared.context import PrincipalContext
from revpilot.modules.approval.domain import ApprovalError


class ApprovalTier(IntEnum):
    """Tiered authority levels and financial thresholds for action authorization."""
    TIER_1_OPERATIONAL = 1  # <= $250.00 USD
    TIER_2_TACTICAL = 2     # <= $1,000.00 USD
    TIER_3_EXECUTIVE = 3    # <= $10,000.00 USD


TIER_1_MAX_SPEND = Decimal("250.00")
TIER_2_MAX_SPEND = Decimal("1000.00")
TIER_3_MAX_SPEND = Decimal("10000.00")


class AuthorityVerifier:
    """Evaluates principal credentials, roles, and spend limits against action requirements."""

    @staticmethod
    def is_agent_principal(principal: PrincipalContext) -> bool:
        """
        Check whether principal is an automated AI agent or delegate.
        AI agents are strictly forbidden from approving actions (INV-ACT-003).
        """
        if principal.has_role("agent_delegate"):
            return True
        pid_str = str(principal.principal_id).lower()
        if "agent" in pid_str or "bot" in pid_str or pid_str.startswith("usr_agent") or pid_str.startswith("usr_bot"):
            return True
        return False

    @classmethod
    def get_principal_tier(cls, principal: PrincipalContext) -> int:
        """
        Resolve highest approval tier granted to the principal based on permissions.
        """
        if cls.is_agent_principal(principal):
            return 0  # Agents have zero approval tier
        if principal.has_permission("approval:tier_3") or principal.has_role("platform_admin"):
            return ApprovalTier.TIER_3_EXECUTIVE
        if principal.has_permission("approval:tier_2") or principal.has_role("tenant_admin"):
            return ApprovalTier.TIER_2_TACTICAL
        if principal.has_permission("approval:tier_1") or principal.has_role("operator"):
            return ApprovalTier.TIER_1_OPERATIONAL
        return 0

    @classmethod
    def verify_approver_authority(
        cls,
        principal: PrincipalContext,
        cost_usd: Decimal,
        required_tier: int,
    ) -> bool:
        """
        Verify that principal is a human with sufficient tier and spend limit.
        Fails closed on agents, tier deficiency, or spend ceiling excess.
        """
        # 1. Agent exclusion (INV-ACT-003)
        if cls.is_agent_principal(principal):
            return False

        # 2. Hard absolute ceiling ($10,000.00 max spend)
        if cost_usd > TIER_3_MAX_SPEND:
            return False

        # 3. Principal tier check
        principal_tier = cls.get_principal_tier(principal)
        if principal_tier < required_tier:
            return False

        # 4. Spend ceiling per tier
        if principal_tier == ApprovalTier.TIER_1_OPERATIONAL and cost_usd > TIER_1_MAX_SPEND:
            return False
        if principal_tier == ApprovalTier.TIER_2_TACTICAL and cost_usd > TIER_2_MAX_SPEND:
            return False

        return True

    @staticmethod
    def check_separation_of_duties(
        proposer_id: str, approver_id: str, cost_usd: Decimal
    ) -> bool:
        """
        Enforce dual authorization / separation of duties:
        Proposer cannot sign as sole approver if spend > $250.00 USD.
        """
        if proposer_id.strip() == approver_id.strip() and cost_usd > TIER_1_MAX_SPEND:
            return False
        return True
