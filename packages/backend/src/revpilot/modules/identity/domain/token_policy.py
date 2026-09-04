"""
RevPilot AI — Token and Session Validation Policies
Enforces fail-closed token claims validation, clock skew bounds, session lifecycle,
and provenance verification for identity authentication (Rail 3).
Conforms to INV-IAM-001, INV-TEN-002, INV-TEN-003, and INV-REL-001.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import hmac

from revpilot.modules.identity.domain.models import VerifiedClaimsToken
from revpilot.shared.errors import (
    AuthenticationError,
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


_SESSION_PROVENANCE_SALT = b"revpilot-session-evidence-provenance-salt-2026"


def _compute_session_provenance(
    session_id: str,
    is_active: bool,
    is_revoked: bool,
    issued_at_iso: str,
    expires_at_iso: str,
) -> str:
    """Compute HMAC cryptographic provenance signature for VerifiedSessionEvidence."""
    msg = f"{session_id}:{is_active}:{is_revoked}:{issued_at_iso}:{expires_at_iso}".encode("utf-8")
    return hmac.new(_SESSION_PROVENANCE_SALT, msg, hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class VerifiedSessionEvidence:
    """
    Immutable typed evidence object representing verified session state.
    Carries cryptographic provenance proof; never accepts bare caller-supplied booleans.
    """
    session_id: str
    is_active: bool
    is_revoked: bool
    issued_at: UtcDateTime
    expires_at: UtcDateTime
    _provenance_signature: str

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValidationError("session_id must be non-empty str")
        if not isinstance(self.is_active, bool):
            raise TypeError("is_active must be bool")
        if not isinstance(self.is_revoked, bool):
            raise TypeError("is_revoked must be bool")
        if not isinstance(self.issued_at, UtcDateTime):
            raise TypeError(f"issued_at must be UtcDateTime, got {type(self.issued_at).__name__}")
        if not isinstance(self.expires_at, UtcDateTime):
            raise TypeError(f"expires_at must be UtcDateTime, got {type(self.expires_at).__name__}")
        if not isinstance(self._provenance_signature, str):
            raise TypeError("provenance signature must be str")

        if self.expires_at.value <= self.issued_at.value:
            raise ValidationError("expires_at must be strictly after issued_at")

        expected_sig = _compute_session_provenance(
            self.session_id.strip(),
            self.is_active,
            self.is_revoked,
            self.issued_at.isoformat(),
            self.expires_at.isoformat(),
        )
        if not hmac.compare_digest(self._provenance_signature, expected_sig):
            raise AuthenticationError(
                "Invalid session evidence provenance signature; cannot construct VerifiedSessionEvidence from unverified payload"
            )

    @classmethod
    def issue(
        cls,
        *,
        session_id: str,
        is_active: bool,
        is_revoked: bool,
        issued_at: UtcDateTime,
        expires_at: UtcDateTime,
    ) -> VerifiedSessionEvidence:
        """Internal trusted factory for session evidence with cryptographic provenance."""
        sid = session_id.strip()
        sig = _compute_session_provenance(
            sid,
            is_active,
            is_revoked,
            issued_at.isoformat(),
            expires_at.isoformat(),
        )
        return cls(
            session_id=sid,
            is_active=is_active,
            is_revoked=is_revoked,
            issued_at=issued_at,
            expires_at=expires_at,
            _provenance_signature=sig,
        )

    def is_valid(self, as_of: UtcDateTime | None = None) -> bool:
        """Return True if session is active, unrevoked, within lifetime, and provenance matches."""
        if not self.is_active or self.is_revoked:
            return False
        check_time = as_of or UtcDateTime.now()
        if check_time.value < self.issued_at.value or check_time.value > self.expires_at.value:
            return False
        expected_sig = _compute_session_provenance(
            self.session_id,
            self.is_active,
            self.is_revoked,
            self.issued_at.isoformat(),
            self.expires_at.isoformat(),
        )
        return hmac.compare_digest(self._provenance_signature, expected_sig)


@dataclass(frozen=True, slots=True)
class SessionPolicy:
    """
    Domain policy enforcing session validity and revocation rules using typed VerifiedSessionEvidence.
    Bare caller booleans are never accepted as trust anchors.
    """

    def validate_session_evidence(
        self,
        evidence: VerifiedSessionEvidence,
        as_of: UtcDateTime | None = None,
    ) -> None:
        """
        Validate session state from verified evidence.
        Fails closed with AuthenticationError if session is revoked, inactive, expired, or invalid.
        """
        if not isinstance(evidence, VerifiedSessionEvidence):
            raise TypeError(
                f"validate_session_evidence requires VerifiedSessionEvidence, got {type(evidence).__name__}"
            )

        check_time = as_of or UtcDateTime.now()
        if not isinstance(check_time, UtcDateTime):
            raise TypeError(f"as_of must be UtcDateTime, got {type(check_time).__name__}")

        if evidence.is_revoked:
            raise AuthenticationError("Token or session has been revoked")

        if not evidence.is_active:
            raise AuthenticationError("Token or session has been revoked")

        if check_time.value > evidence.expires_at.value:
            raise AuthenticationError("Token or session has been revoked")

        if check_time.value < evidence.issued_at.value:
            raise AuthenticationError("Token or session has been revoked")


@dataclass(frozen=True, slots=True)
class TokenValidationPolicy:
    """
    Domain policy evaluating claims constraints (issuer, audience, clock skew, tenant binding)
    on cryptographically verified tokens.
    """
    expected_issuer: str = "revpilot-idp"
    expected_audience: str = "revpilot-api"
    clock_skew_seconds: int = 60

    def __post_init__(self) -> None:
        if not isinstance(self.expected_issuer, str) or not self.expected_issuer.strip():
            raise ValidationError("expected_issuer must be non-empty str")
        if not isinstance(self.expected_audience, str) or not self.expected_audience.strip():
            raise ValidationError("expected_audience must be non-empty str")
        if not isinstance(self.clock_skew_seconds, int):
            raise ValidationError(
                f"clock_skew_seconds must be int, got {type(self.clock_skew_seconds).__name__}"
            )
        if self.clock_skew_seconds < 0 or self.clock_skew_seconds > 60:
            raise ValidationError(
                f"clock_skew_seconds must be between 0 and 60, got {self.clock_skew_seconds}"
            )

    def validate_verified_token(
        self,
        verified_token: VerifiedClaimsToken,
        as_of: UtcDateTime | None = None,
    ) -> None:
        """
        Validate verified claims against configured policy constraints.
        Requires strictly typed VerifiedClaimsToken; raw AuthTokenClaims are rejected.
        """
        if not isinstance(verified_token, VerifiedClaimsToken):
            raise TypeError(
                f"validate_verified_token requires VerifiedClaimsToken, got {type(verified_token).__name__}"
            )

        claims = verified_token.claims
        check_time = as_of or UtcDateTime.now()
        if not isinstance(check_time, UtcDateTime):
            raise TypeError(f"as_of must be UtcDateTime, got {type(check_time).__name__}")

        # Issuer validation
        if claims.iss != self.expected_issuer or verified_token.verified_issuer != self.expected_issuer:
            raise AuthenticationError(
                f"Invalid token issuer: expected '{self.expected_issuer}', got '{claims.iss}'"
            )

        # Audience validation
        if claims.aud != self.expected_audience or verified_token.verified_audience != self.expected_audience:
            raise AuthenticationError(
                f"Invalid token audience: expected '{self.expected_audience}', got '{claims.aud}'"
            )

        # Expiration with bounded clock skew
        skew = timedelta(seconds=self.clock_skew_seconds)
        if check_time.value >= claims.exp.value + skew:
            raise AuthenticationError("Token has expired")

        # Not-before check with bounded clock skew
        if claims.nbf is not None and check_time.value < claims.nbf.value - skew:
            raise AuthenticationError("Token not yet active")

        # Tenant binding enforcement (INV-TEN-003)
        if claims.tenant_id is None or not str(claims.tenant_id).strip():
            raise TenancyViolationError("Principal lacks required tenant association")

        try:
            TenantId(claims.tenant_id)
        except (TypeError, ValueError) as e:
            raise TenancyViolationError(
                f"Invalid tenant_id in verified token claims: {claims.tenant_id}"
            ) from e
