"""
RevPilot AI — In-Memory Authentication Adapter (Rail 3)
Test-safe, provider-neutral implementation of AuthenticationPort.
Enforces fail-closed token verification, verified boundary, and typed session evidence.
Conforms to INV-IAM-001, INV-TEN-002, INV-TEN-003, INV-SEC-001, and INV-REL-001.
"""

from __future__ import annotations
import hashlib
from typing import Mapping

from revpilot.modules.identity.domain.models import (
    AuthTokenClaims,
    VerifiedClaimsToken,
)
from revpilot.modules.identity.domain.token_policy import VerifiedSessionEvidence
from revpilot.modules.identity.ports.authentication import AuthenticationPort
from revpilot.shared.errors import (
    AuthenticationError,
    ValidationError,
)
from revpilot.shared.temporal import UtcDateTime


class InMemoryAuthAdapter(AuthenticationPort):
    """
    Test-safe, provider-neutral in-memory adapter implementing AuthenticationPort.
    Strictly isolated from external networks, remote IdPs, or cloud services.
    Enforces verified cryptographic boundary by returning VerifiedClaimsToken and
    immutable VerifiedSessionEvidence with cryptographic provenance.
    """

    def __init__(
        self,
        *,
        tokens: Mapping[str, VerifiedClaimsToken] | None = None,
        sessions: Mapping[str, VerifiedSessionEvidence] | None = None,
        revoked_sessions: set[str] | None = None,
    ) -> None:
        self._tokens: dict[str, VerifiedClaimsToken] = (
            dict(tokens) if tokens is not None else {}
        )
        self._sessions: dict[str, VerifiedSessionEvidence] = (
            dict(sessions) if sessions is not None else {}
        )
        self._revoked_sessions: set[str] = (
            set(revoked_sessions) if revoked_sessions is not None else set()
        )

    def verify_token(
        self,
        token: str,
        *,
        expected_issuer: str = "revpilot-idp",
        expected_audience: str = "revpilot-api",
        as_of: UtcDateTime | None = None,
    ) -> VerifiedClaimsToken:
        """
        Cryptographically verify token presence and alignment.
        Returns VerifiedClaimsToken or raises AuthenticationError on verification failure.
        """
        if not isinstance(token, str) or not token.strip():
            raise AuthenticationError("Token must be a non-empty string")

        tok_clean = token.strip()
        if tok_clean not in self._tokens:
            raise AuthenticationError("Invalid token signature or token unknown")

        verified = self._tokens[tok_clean]

        # Issuer check
        if (
            verified.claims.iss != expected_issuer
            or verified.verified_issuer != expected_issuer
        ):
            raise AuthenticationError(
                f"Issuer mismatch: expected '{expected_issuer}', got '{verified.claims.iss}'"
            )

        # Audience check
        if (
            verified.claims.aud != expected_audience
            or verified.verified_audience != expected_audience
        ):
            raise AuthenticationError(
                f"Audience mismatch: expected '{expected_audience}', got '{verified.claims.aud}'"
            )

        # Check session revocation
        if verified.session_id in self._revoked_sessions:
            raise AuthenticationError("Token or session has been revoked")

        return verified

    def revoke_session(self, session_id: str) -> None:
        """Mark session_id as revoked in internal store."""
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValidationError("session_id must be a non-empty string")

        sid = session_id.strip()
        self._revoked_sessions.add(sid)

        # Update evidence in session ledger if present
        if sid in self._sessions:
            ev = self._sessions[sid]
            self._sessions[sid] = VerifiedSessionEvidence.issue(
                session_id=ev.session_id,
                is_active=ev.is_active,
                is_revoked=True,
                issued_at=ev.issued_at,
                expires_at=ev.expires_at,
            )

    def get_session_evidence(
        self,
        session_id: str,
        as_of: UtcDateTime | None = None,
    ) -> VerifiedSessionEvidence:
        """
        Retrieve provenance-bound session evidence.
        Raises AuthenticationError if session is unknown or revoked.
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValidationError("session_id must be a non-empty string")

        sid = session_id.strip()

        if sid in self._revoked_sessions:
            if sid in self._sessions:
                return self._sessions[sid]
            raise AuthenticationError("Token or session has been revoked")

        if sid not in self._sessions:
            raise AuthenticationError(f"Session '{sid}' not found or unverified")

        return self._sessions[sid]

    def register_token(
        self,
        token_string: str,
        verified_token: VerifiedClaimsToken,
        session_evidence: VerifiedSessionEvidence | None = None,
    ) -> None:
        """
        Test helper to register a verified token and its associated session evidence.
        Never accepts bare caller booleans or untyped dictionaries.
        """
        if not isinstance(token_string, str) or not token_string.strip():
            raise ValidationError("token_string must be a non-empty string")
        if not isinstance(verified_token, VerifiedClaimsToken):
            raise TypeError(
                f"verified_token must be VerifiedClaimsToken, got {type(verified_token).__name__}"
            )

        sid = verified_token.session_id
        if session_evidence is not None:
            if not isinstance(session_evidence, VerifiedSessionEvidence):
                raise TypeError(
                    f"session_evidence must be VerifiedSessionEvidence, got {type(session_evidence).__name__}"
                )
            ev = session_evidence
        else:
            # Issue default active, unrevoked session evidence
            now = UtcDateTime.now()
            exp = UtcDateTime.from_iso("2099-01-01T00:00:00Z")
            ev = VerifiedSessionEvidence.issue(
                session_id=sid,
                is_active=True,
                is_revoked=False,
                issued_at=now,
                expires_at=exp,
            )

        self._tokens[token_string.strip()] = verified_token
        self._sessions[sid] = ev

    def register_session(self, session_evidence: VerifiedSessionEvidence) -> None:
        """Test helper to register explicit VerifiedSessionEvidence."""
        if not isinstance(session_evidence, VerifiedSessionEvidence):
            raise TypeError(
                f"session_evidence must be VerifiedSessionEvidence, got {type(session_evidence).__name__}"
            )
        self._sessions[session_evidence.session_id] = session_evidence

    def issue_test_token(
        self,
        token_string: str,
        *,
        sub: str = "usr_test_user",
        tenant_id: str = "tnt_test_tenant",
        roles: frozenset[str] | list[str] | None = None,
        permissions: frozenset[str] | list[str] | None = None,
        session_id: str = "sess_test_123",
        iss: str = "revpilot-idp",
        aud: str = "revpilot-api",
        exp: UtcDateTime | None = None,
        iat: UtcDateTime | None = None,
        nbf: UtcDateTime | None = None,
        email: str | None = "test@example.com",
        jti: str | None = "jti_test_123",
        is_session_active: bool = True,
        is_session_revoked: bool = False,
        session_expires_at: UtcDateTime | None = None,
    ) -> tuple[VerifiedClaimsToken, VerifiedSessionEvidence]:
        """
        Convenience factory to construct valid signed test tokens and register them.
        Computes valid cryptographic provenance internally.
        """
        now = UtcDateTime.now()
        issued_at = iat or now
        expires_at = exp or UtcDateTime.from_iso("2099-01-01T00:00:00Z")
        sess_exp = session_expires_at or expires_at

        claims = AuthTokenClaims(
            sub=sub,
            iss=iss,
            aud=aud,
            exp=expires_at,
            iat=issued_at,
            nbf=nbf,
            tenant_id=tenant_id,
            roles=frozenset(roles) if roles is not None else frozenset(),
            permissions=frozenset(permissions) if permissions is not None else frozenset(),
            email=email,
            jti=jti,
        )

        sig_fp = hashlib.sha256(token_string.encode("utf-8")).hexdigest()[:16]
        verified_token = VerifiedClaimsToken.issue(
            claims=claims,
            verified_issuer=iss,
            verified_audience=aud,
            session_id=session_id,
            signature_fingerprint=sig_fp,
            verified_at=now,
        )

        session_evidence = VerifiedSessionEvidence.issue(
            session_id=session_id,
            is_active=is_session_active,
            is_revoked=is_session_revoked,
            issued_at=issued_at,
            expires_at=sess_exp,
        )

        self.register_token(
            token_string=token_string,
            verified_token=verified_token,
            session_evidence=session_evidence,
        )
        if is_session_revoked:
            self._revoked_sessions.add(session_id)

        return verified_token, session_evidence
