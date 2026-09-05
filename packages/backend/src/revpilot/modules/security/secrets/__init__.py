"""
RevPilot AI — Secret Lifecycle, Workload Identity & Key Rotation
Specification: docs/15-security/SECURITY-ARCHITECTURE.md §7, ADR-0009
Conforms to INV-SEC-001, INV-TEN-001, and INV-REL-001.
"""

from revpilot.modules.security.secrets.envelope import (
    EnvelopeDecryptionError,
    EnvelopeEncryptedSecret,
    EnvelopeEncryptionService,
)
from revpilot.modules.security.secrets.broker import (
    BrokerUnavailableError,
    CredentialBroker,
    EphemeralProviderToken,
    RotationValidationFailedError,
    ScopeExpansionDeniedError,
    SecretAccessDeniedError,
    SecretBrokerPort,
    SecretExpiredError,
    SecretLifecycleStatus,
    SecretNotFoundError,
    SecretRecord,
    SecretReference,
    SecretRevokedError,
    SecretSecurityError,
)
from revpilot.modules.security.secrets.rotation import (
    RotationSession,
    RotationStatus,
    SecretRotationService,
)

__all__ = [
    "BrokerUnavailableError",
    "CredentialBroker",
    "EnvelopeDecryptionError",
    "EnvelopeEncryptedSecret",
    "EnvelopeEncryptionService",
    "EphemeralProviderToken",
    "RotationSession",
    "RotationStatus",
    "RotationValidationFailedError",
    "ScopeExpansionDeniedError",
    "SecretAccessDeniedError",
    "SecretBrokerPort",
    "SecretExpiredError",
    "SecretLifecycleStatus",
    "SecretNotFoundError",
    "SecretRecord",
    "SecretReference",
    "SecretRevokedError",
    "SecretRotationService",
    "SecretSecurityError",
]
