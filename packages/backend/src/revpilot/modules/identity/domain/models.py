"""
RevPilot AI — Identity Domain Models and Authentication Primitives
Canonical domain entities, claims value objects, privileged contexts, and ports (Rail 3).
Enforces INV-IAM-001, INV-TEN-002, INV-TEN-003, and INV-REL-001.
"""

from __future__ import annotations
import base64
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
import hashlib
import hmac
import json
from typing import Any, Protocol, runtime_checkable

from revpilot.shared.context import PrincipalContext
from revpilot.shared.errors import (
    AuthenticationError,
    AuthorizationError,
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.identifiers import EntityId, PrincipalId, TenantId
from revpilot.shared.temporal import UtcDateTime


_INTERNAL_PROVENANCE_SALT = b"revpilot-internal-identity-boundary-provenance-salt-2026"
_PLATFORM_AUTHORITY_SALT = b"revpilot-platform-privileged-authority-signature-2026"


def _compute_token_provenance(
    sub: str,
    iss: str,
    aud: str,
    session_id: str,
    sig_fp: str,
    verified_at_iso: str,
) -> str:
    """Compute HMAC cryptographic provenance proof for VerifiedClaimsToken."""
    msg = f"{sub}:{iss}:{aud}:{session_id}:{sig_fp}:{verified_at_iso}".encode("utf-8")
    return hmac.new(_INTERNAL_PROVENANCE_SALT, msg, hashlib.sha256).hexdigest()


def _compute_privileged_signature(
    principal_id_str: str,
    ticket_id: str,
    justification: str,
    issued_at_iso: str,
    expires_at_iso: str,
) -> str:
    """Compute HMAC platform authority signature for PrivilegedContext."""
    msg = f"{principal_id_str}:{ticket_id}:{justification}:{issued_at_iso}:{expires_at_iso}".encode("utf-8")
    return hmac.new(_PLATFORM_AUTHORITY_SALT, msg, hashlib.sha256).hexdigest()


class PrincipalType(str, Enum):
    """Enumeration of authenticated principal types."""
    USER = "user"                      # Human interactive user
    SERVICE_ACCOUNT = "service_account"# Machine-to-machine service principal
    AGENT = "agent"                    # Delegated AI agent actor
    SYSTEM = "system"                  # Internal platform maintenance worker


class ServiceAccountId(PrincipalId, prefix="svc_"):
    """Typed identifier for machine-to-machine service accounts."""
    pass


@dataclass(frozen=True, slots=True)
class AuthTokenClaims:
    """
    Normalized token claims value object extracted from incoming authentication assertions.
    Untrusted data structure; primitive caller booleans and is_system are strictly prohibited.
    """
    sub: str
    iss: str
    aud: str
    exp: UtcDateTime
    iat: UtcDateTime
    nbf: UtcDateTime | None = None
    tenant_id: str | None = None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    email: str | None = None
    jti: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sub, str):
            raise TypeError(f"sub must be str, got {type(self.sub).__name__}")
        sub_clean = self.sub.strip()
        if not sub_clean:
            raise ValidationError("sub cannot be empty or whitespace-only")
        if not (sub_clean.startswith("usr_") or sub_clean.startswith("svc_")):
            raise ValidationError(f"sub must start with 'usr_' or 'svc_', got '{self.sub}'")
        object.__setattr__(self, "sub", sub_clean)

        if not isinstance(self.iss, str):
            raise TypeError(f"iss must be str, got {type(self.iss).__name__}")
        iss_clean = self.iss.strip()
        if not iss_clean:
            raise ValidationError("iss cannot be empty or whitespace-only")
        object.__setattr__(self, "iss", iss_clean)

        if not isinstance(self.aud, str):
            raise TypeError(f"aud must be str, got {type(self.aud).__name__}")
        aud_clean = self.aud.strip()
        if not aud_clean:
            raise ValidationError("aud cannot be empty or whitespace-only")
        object.__setattr__(self, "aud", aud_clean)

        if not isinstance(self.exp, UtcDateTime):
            raise TypeError(f"exp must be UtcDateTime instance, got {type(self.exp).__name__}")

        if not isinstance(self.iat, UtcDateTime):
            raise TypeError(f"iat must be UtcDateTime instance, got {type(self.iat).__name__}")

        if self.nbf is not None and not isinstance(self.nbf, UtcDateTime):
            raise TypeError(f"nbf must be UtcDateTime or None, got {type(self.nbf).__name__}")

        if self.tenant_id is not None:
            if not isinstance(self.tenant_id, str):
                raise TypeError(f"tenant_id must be str or None, got {type(self.tenant_id).__name__}")
            tid_clean = self.tenant_id.strip()
            if not tid_clean:
                raise ValidationError("tenant_id cannot be empty or whitespace-only")
            object.__setattr__(self, "tenant_id", tid_clean)

        if not isinstance(self.roles, frozenset):
            object.__setattr__(self, "roles", frozenset(self.roles))

        if not isinstance(self.permissions, frozenset):
            object.__setattr__(self, "permissions", frozenset(self.permissions))

        if self.email is not None and not isinstance(self.email, str):
            raise TypeError(f"email must be str or None, got {type(self.email).__name__}")

        if self.jti is not None:
            if not isinstance(self.jti, str):
                raise TypeError(f"jti must be str or None, got {type(self.jti).__name__}")
            jti_clean = self.jti.strip()
            if not jti_clean:
                raise ValidationError("jti cannot be empty or whitespace-only")
            object.__setattr__(self, "jti", jti_clean)


@dataclass(frozen=True, slots=True)
class VerifiedClaimsToken:
    """
    Opaque immutable evidence object representing cryptographically verified token claims.
    Issued exclusively by the verified authentication boundary with valid provenance proof.
    """
    claims: AuthTokenClaims
    verified_issuer: str
    verified_audience: str
    session_id: str
    verified_at: UtcDateTime
    signature_fingerprint: str
    _provenance_token: str

    def __post_init__(self) -> None:
        if not isinstance(self.claims, AuthTokenClaims):
            raise TypeError(f"claims must be AuthTokenClaims, got {type(self.claims).__name__}")
        if not isinstance(self.verified_issuer, str) or not self.verified_issuer.strip():
            raise ValidationError("verified_issuer must be non-empty str")
        if not isinstance(self.verified_audience, str) or not self.verified_audience.strip():
            raise ValidationError("verified_audience must be non-empty str")
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValidationError("session_id must be non-empty str")
        if not isinstance(self.verified_at, UtcDateTime):
            raise TypeError(f"verified_at must be UtcDateTime, got {type(self.verified_at).__name__}")
        if not isinstance(self.signature_fingerprint, str) or not self.signature_fingerprint.strip():
            raise ValidationError("signature_fingerprint must be non-empty str")
        if not isinstance(self._provenance_token, str):
            raise TypeError("provenance token must be str")

        # Cryptographic provenance verification
        expected_prov = _compute_token_provenance(
            self.claims.sub,
            self.verified_issuer,
            self.verified_audience,
            self.session_id,
            self.signature_fingerprint,
            self.verified_at.isoformat(),
        )
        if not hmac.compare_digest(self._provenance_token, expected_prov):
            raise AuthenticationError(
                "Invalid claims token provenance proof; cannot construct VerifiedClaimsToken from unverified payload"
            )

    @classmethod
    def issue(
        cls,
        *,
        claims: AuthTokenClaims,
        verified_issuer: str,
        verified_audience: str,
        session_id: str,
        signature_fingerprint: str,
        verified_at: UtcDateTime | None = None,
    ) -> VerifiedClaimsToken:
        """Internal factory for verified authentication boundaries."""
        v_at = verified_at or UtcDateTime.now()
        prov = _compute_token_provenance(
            claims.sub,
            verified_issuer,
            verified_audience,
            session_id,
            signature_fingerprint,
            v_at.isoformat(),
        )
        return cls(
            claims=claims,
            verified_issuer=verified_issuer,
            verified_audience=verified_audience,
            session_id=session_id,
            verified_at=v_at,
            signature_fingerprint=signature_fingerprint,
            _provenance_token=prov,
        )


@dataclass(frozen=True, slots=True)
class PrivilegedContext:
    """
    Opaque immutable execution context for platform-level maintenance operations.
    Issued strictly at the verified platform boundary for registered service accounts (INV-TEN-003).
    Application/caller code has no public constructor to self-elevate.
    """
    principal_id: PrincipalId
    ticket_id: str
    justification: str
    issued_at: UtcDateTime
    expires_at: UtcDateTime
    _provenance_signature: str

    def __post_init__(self) -> None:
        if not isinstance(self.principal_id, PrincipalId):
            raise TypeError(f"principal_id must be PrincipalId, got {type(self.principal_id).__name__}")
        if not isinstance(self.ticket_id, str) or not self.ticket_id.strip():
            raise ValidationError("ticket_id cannot be empty or whitespace-only")
        if not isinstance(self.justification, str) or not self.justification.strip():
            raise ValidationError("justification cannot be empty or whitespace-only")
        if not isinstance(self.issued_at, UtcDateTime):
            raise TypeError(f"issued_at must be UtcDateTime, got {type(self.issued_at).__name__}")
        if not isinstance(self.expires_at, UtcDateTime):
            raise TypeError(f"expires_at must be UtcDateTime, got {type(self.expires_at).__name__}")

        lifetime_seconds = (self.expires_at.value - self.issued_at.value).total_seconds()
        if lifetime_seconds <= 0:
            raise ValidationError("expires_at must be strictly after issued_at")
        if lifetime_seconds > 3600:
            raise ValidationError(
                f"PrivilegedContext maximum lifetime is 60 minutes (3600s), got {lifetime_seconds}s"
            )

        expected_sig = _compute_privileged_signature(
            str(self.principal_id),
            self.ticket_id.strip(),
            self.justification.strip(),
            self.issued_at.isoformat(),
            self.expires_at.isoformat(),
        )
        if not hmac.compare_digest(self._provenance_signature, expected_sig):
            raise AuthorizationError(
                "PrivilegedContext construction denied: invalid platform provenance signature"
            )

    def is_valid(self, as_of: UtcDateTime | None = None) -> bool:
        """Check if context is within valid time bounds and maintains valid provenance."""
        check_time = as_of or UtcDateTime.now()
        if check_time.value < self.issued_at.value or check_time.value > self.expires_at.value:
            return False
        expected_sig = _compute_privileged_signature(
            str(self.principal_id),
            self.ticket_id.strip(),
            self.justification.strip(),
            self.issued_at.isoformat(),
            self.expires_at.isoformat(),
        )
        return hmac.compare_digest(self._provenance_signature, expected_sig)

    @classmethod
    def _issue_platform_context(
        cls,
        *,
        principal_id: PrincipalId,
        ticket_id: str,
        justification: str,
        issued_at: UtcDateTime,
        expires_at: UtcDateTime,
    ) -> PrivilegedContext:
        """Internal platform boundary factory for privileged context."""
        t_id = ticket_id.strip()
        just = justification.strip()
        sig = _compute_privileged_signature(
            str(principal_id),
            t_id,
            just,
            issued_at.isoformat(),
            expires_at.isoformat(),
        )
        return cls(
            principal_id=principal_id,
            ticket_id=t_id,
            justification=just,
            issued_at=issued_at,
            expires_at=expires_at,
            _provenance_signature=sig,
        )


@dataclass(frozen=True, slots=True)
class Principal:
    """
    Aggregate root representing an authenticated actor.
    """
    id: PrincipalId
    type: PrincipalType
    tenant_id: TenantId | None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    is_active: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.id, PrincipalId):
            raise TypeError(f"id must be PrincipalId instance, got {type(self.id).__name__}")
        if not isinstance(self.type, PrincipalType):
            raise TypeError(f"type must be PrincipalType instance, got {type(self.type).__name__}")
        if self.tenant_id is not None and not isinstance(self.tenant_id, TenantId):
            raise TypeError(f"tenant_id must be TenantId or None, got {type(self.tenant_id).__name__}")
        if self.type != PrincipalType.SYSTEM and self.tenant_id is None:
            raise TenancyViolationError(
                "Non-system principal requires explicit tenant association (INV-TEN-003)"
            )
        if not isinstance(self.roles, frozenset):
            object.__setattr__(self, "roles", frozenset(self.roles))
        if not isinstance(self.permissions, frozenset):
            object.__setattr__(self, "permissions", frozenset(self.permissions))

    def has_role(self, role: str) -> bool:
        """Check if principal possesses specified role (case-insensitive)."""
        return role.lower() in (r.lower() for r in self.roles)

    def has_permission(self, permission: str) -> bool:
        """Check if principal possesses specified permission (case-insensitive)."""
        return permission.lower() in (p.lower() for p in self.permissions)

    def to_context(self) -> PrincipalContext:
        """
        Produce standard immutable PrincipalContext.
        Hardcodes is_system=False; structurally prohibited from producing is_system=True.
        Enforces tenant_id is not None for non-system actors.
        """
        if self.tenant_id is None:
            raise TenancyViolationError("Cannot create PrincipalContext without tenant_id for non-system actor")
        return PrincipalContext(
            principal_id=self.id,
            tenant_id=self.tenant_id,
            roles=self.roles,
            permissions=self.permissions,
            is_system=False,  # Hardcoded: structurally cannot manufacture is_system=True
        )


def create_principal_from_verified_claims(
    verified: VerifiedClaimsToken,
    as_of: UtcDateTime | None = None,
) -> Principal:
    """
    Trusted domain factory enforcing claim invariants at creation.
    Requires strictly typed VerifiedClaimsToken issued by verified boundary.
    Rejects unverified AuthTokenClaims or caller booleans.
    """
    if not isinstance(verified, VerifiedClaimsToken):
        raise TypeError(
            f"create_principal_from_verified_claims requires VerifiedClaimsToken, got {type(verified).__name__}"
        )

    claims = verified.claims
    check_time = as_of or UtcDateTime.now()
    if not isinstance(check_time, UtcDateTime):
        raise TypeError(f"as_of must be UtcDateTime, got {type(check_time).__name__}")

    # Revalidate time window with 60-second clock skew tolerance
    if check_time.value >= claims.exp.value + timedelta(seconds=60):
        raise AuthenticationError("Token has expired")

    if claims.nbf is not None and check_time.value < claims.nbf.value - timedelta(seconds=60):
        raise AuthenticationError("Token not yet active")

    # Validate sub parses as valid PrincipalId (usr_... or svc_...)
    sub = claims.sub.strip()
    if sub.startswith("usr_"):
        pid = PrincipalId(sub)
        ptype = PrincipalType.USER
    elif sub.startswith("svc_"):
        pid = ServiceAccountId(sub)
        ptype = PrincipalType.SERVICE_ACCOUNT
    else:
        raise ValidationError(f"Invalid principal subject identifier prefix: '{claims.sub}'")

    # Enforce INV-TEN-003: Non-system principal MUST have a valid tenant_id
    if claims.tenant_id is None:
        raise TenancyViolationError("Principal lacks required tenant association")

    try:
        tid = TenantId(claims.tenant_id)
    except (TypeError, ValueError) as e:
        raise TenancyViolationError(f"Invalid tenant_id in token claims: {claims.tenant_id}") from e

    # NEVER assigns SYSTEM to token-authenticated actors
    return Principal(
        id=pid,
        type=ptype,
        tenant_id=tid,
        roles=claims.roles,
        permissions=claims.permissions,
        is_active=True,
    )


@runtime_checkable
class TokenVerificationPort(Protocol):
    """
    Port protocol defining the verified authentication boundary.
    Mandates cryptographic signature verification, issuer/audience validation,
    clock skew bounds (60s), active session, revocation list, and anti-replay (JTI).
    """

    def verify_token(
        self,
        token_string: str,
        *,
        expected_issuer: str = "revpilot-idp",
        expected_audience: str = "revpilot-api",
        as_of: UtcDateTime | None = None,
    ) -> VerifiedClaimsToken:
        """
        Cryptographically verifies token signature, issuer, audience,
        clock skew bounds (60s), active session, revocation list, and anti-replay (JTI).
        Returns trusted VerifiedClaimsToken or raises AuthenticationError / TenancyViolationError.
        """
        ...


class InMemoryTokenVerifier:
    """
    Reference in-memory implementation of TokenVerificationPort.
    Enforces fail-closed token signature, issuer, audience, clock skew (60s),
    active session, revocation, replay protection, and tenant status checks.
    """

    def __init__(
        self,
        *,
        secret_key: bytes = b"revpilot-in-memory-verifier-key-2026",
        active_sessions: set[str] | None = None,
        revoked_tokens: set[str] | None = None,
        revoked_sessions: set[str] | None = None,
        active_tenants: set[str] | None = None,
    ) -> None:
        self._secret_key = secret_key
        self._active_sessions = set(active_sessions) if active_sessions is not None else set()
        self._revoked_tokens = set(revoked_tokens) if revoked_tokens is not None else set()
        self._revoked_sessions = set(revoked_sessions) if revoked_sessions is not None else set()
        self._active_tenants = set(active_tenants) if active_tenants is not None else None
        self._seen_jtis: set[str] = set()

    def add_active_session(self, session_id: str) -> None:
        self._active_sessions.add(session_id)

    def revoke_session(self, session_id: str) -> None:
        self._revoked_sessions.add(session_id)

    def revoke_token(self, token_or_jti: str) -> None:
        self._revoked_tokens.add(token_or_jti)

    def sign_token(
        self,
        claims: AuthTokenClaims,
        session_id: str,
    ) -> str:
        """Serialize claims and session into signed token string."""
        payload = {
            "sub": claims.sub,
            "iss": claims.iss,
            "aud": claims.aud,
            "exp": claims.exp.isoformat(),
            "iat": claims.iat.isoformat(),
            "nbf": claims.nbf.isoformat() if claims.nbf else None,
            "tenant_id": claims.tenant_id,
            "roles": sorted(claims.roles),
            "permissions": sorted(claims.permissions),
            "email": claims.email,
            "jti": claims.jti,
            "session_id": session_id,
        }
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8")
        sig = hmac.new(self._secret_key, encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{encoded_payload}.{sig}"

    def verify_token(
        self,
        token_string: str,
        *,
        expected_issuer: str = "revpilot-idp",
        expected_audience: str = "revpilot-api",
        as_of: UtcDateTime | None = None,
    ) -> VerifiedClaimsToken:
        check_time = as_of or UtcDateTime.now()
        if not isinstance(token_string, str) or "." not in token_string:
            raise AuthenticationError("Malformed token structure: expected header/payload.signature")

        parts = token_string.split(".")
        if len(parts) != 2:
            raise AuthenticationError("Invalid token format")

        encoded_payload, sig = parts
        expected_sig = hmac.new(self._secret_key, encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            raise AuthenticationError("Invalid token signature")

        try:
            payload_bytes = base64.urlsafe_b64decode(encoded_payload.encode("utf-8"))
            data = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            raise AuthenticationError(f"Malformed token payload: {e}") from e

        # Issuer check
        iss = data.get("iss")
        if iss != expected_issuer:
            raise AuthenticationError(f"Issuer mismatch: expected '{expected_issuer}', got '{iss}'")

        # Audience check
        aud = data.get("aud")
        if aud != expected_audience:
            raise AuthenticationError(f"Audience mismatch: expected '{expected_audience}', got '{aud}'")

        # Expiration & timestamps
        try:
            exp = UtcDateTime.from_iso(data["exp"])
            iat = UtcDateTime.from_iso(data["iat"])
            nbf = UtcDateTime.from_iso(data["nbf"]) if data.get("nbf") else None
        except Exception as e:
            raise ValidationError(f"Invalid timestamp in token claims: {e}") from e

        # Clock skew 60s tolerance
        if check_time.value >= exp.value + timedelta(seconds=60):
            raise AuthenticationError("Token has expired")
        if nbf is not None and check_time.value < nbf.value - timedelta(seconds=60):
            raise AuthenticationError("Token not yet active")

        # Session validity
        session_id = data.get("session_id", "")
        if not session_id or session_id not in self._active_sessions:
            raise AuthenticationError("Session is not active or missing")
        if session_id in self._revoked_sessions:
            raise AuthenticationError("Session has been revoked")

        # Revocation
        jti = data.get("jti")
        if token_string in self._revoked_tokens or (jti and jti in self._revoked_tokens):
            raise AuthenticationError("Token has been revoked")

        # Anti-replay (JTI)
        if jti:
            if jti in self._seen_jtis:
                raise AuthenticationError(f"Token replay detected for JTI: {jti}")
            self._seen_jtis.add(jti)

        # Tenant binding
        tenant_id = data.get("tenant_id")
        if not tenant_id:
            raise TenancyViolationError("Principal lacks required tenant association")

        if self._active_tenants is not None and tenant_id not in self._active_tenants:
            raise TenancyViolationError(f"Tenant '{tenant_id}' is deactivated or suspended")

        claims = AuthTokenClaims(
            sub=data["sub"],
            iss=iss,
            aud=aud,
            exp=exp,
            iat=iat,
            nbf=nbf,
            tenant_id=tenant_id,
            roles=frozenset(data.get("roles", [])),
            permissions=frozenset(data.get("permissions", [])),
            email=data.get("email"),
            jti=jti,
        )

        sig_fp = hashlib.sha256(sig.encode("utf-8")).hexdigest()[:16]
        return VerifiedClaimsToken.issue(
            claims=claims,
            verified_issuer=iss,
            verified_audience=aud,
            session_id=session_id,
            signature_fingerprint=sig_fp,
            verified_at=check_time,
        )
