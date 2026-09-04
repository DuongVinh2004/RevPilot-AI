"""
RevPilot AI — OIDC Identity Federation Submodule
Public exports for OpenID Connect integration, validation, and session management.
"""

from revpilot.modules.iam.oidc.jwks import (
    JwksClient,
    create_signed_jwt,
)
from revpilot.modules.iam.oidc.validator import (
    OidcValidator,
    OidcValidationError,
    TokenExpiredError,
    InvalidSignatureError,
    IssuerMismatchError,
    TokenReplayError,
)
from revpilot.modules.iam.oidc.adapter import (
    OidcClaimMapping,
    OidcTenantConfiguration,
    OidcAuthRequest,
    OidcSessionCookie,
    OidcSessionManager,
)

__all__ = [
    # JWKS
    "JwksClient",
    "create_signed_jwt",
    # Validator & Errors
    "OidcValidator",
    "OidcValidationError",
    "TokenExpiredError",
    "InvalidSignatureError",
    "IssuerMismatchError",
    "TokenReplayError",
    # Adapter & Configuration
    "OidcClaimMapping",
    "OidcTenantConfiguration",
    "OidcAuthRequest",
    "OidcSessionCookie",
    "OidcSessionManager",
]
