"""
RevPilot AI — Formal Claim Classification and Deterministic Verifier Module
Specification: docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md
"""

from revpilot.modules.verifier.domain import (
    ClaimCategory,
    ClaimVerifierStatus,
    VerifiedClaim,
)
from revpilot.modules.verifier.engine import (
    verify_claim,
    verify_hypothesis_claims,
)
from revpilot.modules.verifier.rules import (
    check_citation_span,
    check_correlation_causation_fallacy,
    check_temporal_leakage,
)

__all__ = [
    "ClaimCategory",
    "ClaimVerifierStatus",
    "VerifiedClaim",
    "verify_claim",
    "verify_hypothesis_claims",
    "check_citation_span",
    "check_correlation_causation_fallacy",
    "check_temporal_leakage",
]
