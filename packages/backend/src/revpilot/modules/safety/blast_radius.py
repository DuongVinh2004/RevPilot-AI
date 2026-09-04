"""
RevPilot AI — Blast Radius and Spend Limit Enforcement
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §5.2
Specification: docs/21-finops/FINOPS-SPEC.md §3
Conforms to NFR-COST-001, AC-008, and INV-ACT-001.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any

from revpilot.modules.approval.policy.authority import (
    ApprovalTier,
    TIER_1_MAX_SPEND,
    TIER_2_MAX_SPEND,
    TIER_3_MAX_SPEND,
)
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Failure, Result, Success

MAX_AFFECTED_ENTITIES: int = 500

TIER_SPEND_CEILINGS: dict[int, Decimal] = {
    ApprovalTier.TIER_1_OPERATIONAL.value: TIER_1_MAX_SPEND,
    ApprovalTier.TIER_2_TACTICAL.value: TIER_2_MAX_SPEND,
    ApprovalTier.TIER_3_EXECUTIVE.value: TIER_3_MAX_SPEND,
}


class BlastRadiusExceededError(DomainError):
    """Execution aborted due to exceeding blast radius entity count or tier spend ceiling."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="ERR_BLAST_RADIUS_EXCEEDED",
            message=message,
            details=details,
            retryable=False,
        )


class BlastRadiusLimiter:
    """
    Enforces physical cohort size limits and per-action spend ceilings.
    Fails closed before gateway dispatch occurs.
    """

    def __init__(
        self,
        max_entities: int = MAX_AFFECTED_ENTITIES,
        tier_ceilings: dict[int, Decimal] | None = None,
    ) -> None:
        self.max_entities = max_entities
        self.tier_ceilings = tier_ceilings or TIER_SPEND_CEILINGS

    def check_limits(
        self,
        target_count: int,
        estimated_cost_usd: Decimal,
        tier: int,
    ) -> Result[None, BlastRadiusExceededError]:
        """
        Validate that action target count and estimated spend do not breach safety ceilings.
        Fails closed on any constraint breach.
        """
        # 1. Target entity count constraints
        if target_count < 0:
            return Failure(
                BlastRadiusExceededError(
                    f"Target count cannot be negative: {target_count}",
                    details={"target_count": target_count},
                )
            )

        if target_count > self.max_entities:
            return Failure(
                BlastRadiusExceededError(
                    f"Target cohort size {target_count} exceeds blast radius ceiling of {self.max_entities} entities",
                    details={
                        "target_count": target_count,
                        "max_allowed": self.max_entities,
                    },
                )
            )

        # 2. Tier validation
        if tier not in self.tier_ceilings:
            return Failure(
                BlastRadiusExceededError(
                    f"Invalid or unauthorized approval tier: {tier}. Must be one of {list(self.tier_ceilings.keys())}",
                    details={"tier": tier, "allowed_tiers": list(self.tier_ceilings.keys())},
                )
            )

        # 3. Spend ceiling constraints
        if estimated_cost_usd < Decimal("0.00"):
            return Failure(
                BlastRadiusExceededError(
                    f"Estimated cost cannot be negative: {estimated_cost_usd}",
                    details={"estimated_cost_usd": str(estimated_cost_usd)},
                )
            )

        max_spend = self.tier_ceilings[tier]
        if estimated_cost_usd > max_spend:
            return Failure(
                BlastRadiusExceededError(
                    f"Estimated cost {estimated_cost_usd} USD exceeds Tier {tier} spend ceiling of {max_spend} USD",
                    details={
                        "estimated_cost_usd": str(estimated_cost_usd),
                        "max_spend": str(max_spend),
                        "tier": tier,
                    },
                )
            )

        return Success(None)
