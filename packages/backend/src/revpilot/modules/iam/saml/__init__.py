"""
RevPilot AI — SAML 2.0 Enterprise Federation Submodule
Public exports for SAML 2.0 ACS validation, certificate rotation, and claims mapping.
Conforms to docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §3.
"""

from revpilot.modules.iam.saml.validator import (
    SamlAcsValidator,
    SamlAssertionClaims,
    SamlValidationError,
    SamlSignatureInvalidError,
    SamlAssertionExpiredError,
    create_signed_saml_response,
)
from revpilot.modules.iam.saml.service import (
    SamlService,
    SamlTenantConfiguration,
)

__all__ = [
    "SamlAcsValidator",
    "SamlAssertionClaims",
    "SamlValidationError",
    "SamlSignatureInvalidError",
    "SamlAssertionExpiredError",
    "create_signed_saml_response",
    "SamlService",
    "SamlTenantConfiguration",
]
