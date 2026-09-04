"""
RevPilot AI — Approval Policy and Revalidation Submodule
Specification: docs/14-iam/IAM-SPEC.md §7
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1, §4
"""

from revpilot.modules.approval.policy.authority import (
    ApprovalTier,
    AuthorityVerifier,
    TIER_1_MAX_SPEND,
    TIER_2_MAX_SPEND,
    TIER_3_MAX_SPEND,
)
from revpilot.modules.approval.policy.revalidation import (
    RevalidationCheckpoint,
    PolicyViolationError,
    PolicyRevalidationService,
)

__all__ = [
    "ApprovalTier",
    "AuthorityVerifier",
    "TIER_1_MAX_SPEND",
    "TIER_2_MAX_SPEND",
    "TIER_3_MAX_SPEND",
    "RevalidationCheckpoint",
    "PolicyViolationError",
    "PolicyRevalidationService",
]
