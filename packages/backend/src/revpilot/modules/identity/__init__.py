"""
RevPilot AI — Identity Module (Rail 3 & Rail 4)
"""

from revpilot.modules.identity.domain.models import (
    AuthTokenClaims,
    InMemoryTokenVerifier,
    Principal,
    PrincipalType,
    PrivilegedContext,
    ServiceAccountId,
    TokenVerificationPort,
    VerifiedClaimsToken,
    create_principal_from_verified_claims,
)

__all__ = [
    "AuthTokenClaims",
    "InMemoryTokenVerifier",
    "Principal",
    "PrincipalType",
    "PrivilegedContext",
    "ServiceAccountId",
    "TokenVerificationPort",
    "VerifiedClaimsToken",
    "create_principal_from_verified_claims",
]
