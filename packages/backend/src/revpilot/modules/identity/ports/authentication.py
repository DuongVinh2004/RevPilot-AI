"""
RevPilot AI — Inbound Authentication Port Protocol
Defines the boundary contract for cryptographic token verification and session lifecycle (Rail 3).
Conforms to INV-IAM-001, INV-TEN-002, and INV-REL-001.
"""

from __future__ import annotations
from typing import Protocol, runtime_checkable

from revpilot.modules.identity.domain.models import VerifiedClaimsToken
from revpilot.modules.identity.domain.token_policy import VerifiedSessionEvidence
from revpilot.shared.temporal import UtcDateTime


@runtime_checkable
class AuthenticationPort(Protocol):
    """
    Inbound port protocol for token verification and session lifecycle.
    Enforces verified boundary by returning VerifiedClaimsToken, never raw Principal bypass.
    """

    def verify_token(
        self,
        token: str,
        *,
        expected_issuer: str = "revpilot-idp",
        expected_audience: str = "revpilot-api",
        as_of: UtcDateTime | None = None,
    ) -> VerifiedClaimsToken:
        """
        Cryptographically verify token and return trusted VerifiedClaimsToken evidence.
        Raises AuthenticationError or TenancyViolationError on verification failure.
        """
        ...

    def revoke_session(self, session_id: str) -> None:
        """Mark session_id as revoked in trusted session store/ledger."""
        ...

    def get_session_evidence(
        self,
        session_id: str,
        as_of: UtcDateTime | None = None,
    ) -> VerifiedSessionEvidence:
        """
        Retrieve provenance-bound session evidence for verification.
        Raises AuthenticationError if session unknown or revoked.
        """
        ...
