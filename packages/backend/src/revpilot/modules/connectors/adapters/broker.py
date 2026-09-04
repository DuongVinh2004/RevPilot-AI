"""
RevPilot AI — Ephemeral Credential Broker
Specification: docs/31-adr/ADR-0009-secrets-and-keys.md
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7.2
Conforms to DEC-007, INV-SEC-001, and INV-IAM-002.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import secrets
from typing import Any

from revpilot.shared.errors import DomainError, TenancyViolationError
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime

# DEC-007 & ADR-0009: Maximum allowed TTL for ephemeral credentials is 15 minutes (900 seconds)
MAX_TOKEN_TTL_SECONDS = 900


class CredentialBrokerError(DomainError):
    """Base error for credential brokering failures."""
    pass


class TokenTtlExceededError(CredentialBrokerError):
    """Raised when requested token lifespan exceeds the 15-minute policy limit."""
    def __init__(self, requested_ttl: int) -> None:
        super().__init__(
            code="ERR_EXCESSIVE_TOKEN_TTL",
            message=f"Requested TTL ({requested_ttl}s) exceeds maximum allowed 15-minute policy limit ({MAX_TOKEN_TTL_SECONDS}s) per DEC-007.",
            details={"requested_ttl": requested_ttl, "max_allowed_ttl": MAX_TOKEN_TTL_SECONDS},
            retryable=False,
        )


@dataclass(frozen=True, slots=True)
class ScopedToken:
    """
    Downscoped ephemeral access token issued to connector worker.
    Opaque token string with strict expiration and tenant context.
    """
    token_value: str
    tenant_id: TenantId
    scopes: frozenset[str]
    expires_at: UtcDateTime
    provider: str

    def is_expired(self, as_of: UtcDateTime | None = None) -> bool:
        check_time = as_of or UtcDateTime.now()
        return check_time.value >= self.expires_at.value

    def __repr__(self) -> str:
        # Prevent secret exposure in logs or trace dumps (INV-SEC-001)
        return (
            f"ScopedToken(tenant={self.tenant_id!r}, provider={self.provider!r}, "
            f"scopes={sorted(self.scopes)}, expires_at={self.expires_at.isoformat()!r}, token=***REDACTED***)"
        )


class CredentialBroker:
    """
    Mediates dynamic downscoped credential issuance for SaaS connectors.
    Enforces DEC-007: Max TTL <= 15 minutes (900s).
    """

    def __init__(self, max_allowed_ttl: int = MAX_TOKEN_TTL_SECONDS) -> None:
        self.max_ttl = max_allowed_ttl
        self._active_tokens: dict[str, ScopedToken] = {}

    def issue_ephemeral_token(
        self,
        tenant_id: TenantId,
        provider: str,
        requested_scopes: list[str] | set[str],
        ttl_seconds: int = 900,
    ) -> ScopedToken:
        """
        Issues an ephemeral downscoped token.
        Raises TokenTtlExceededError if ttl_seconds > 900.
        """
        if not isinstance(tenant_id, TenantId):
            raise TypeError("tenant_id must be an instance of TenantId")

        if ttl_seconds > self.max_ttl:
            raise TokenTtlExceededError(ttl_seconds)

        now = UtcDateTime.now()
        expires_at = UtcDateTime(now.value + timedelta(seconds=ttl_seconds))

        raw_token = f"eph_{provider}_{secrets.token_urlsafe(32)}"

        scoped_token = ScopedToken(
            token_value=raw_token,
            tenant_id=tenant_id,
            scopes=frozenset(requested_scopes),
            expires_at=expires_at,
            provider=provider,
        )

        self._active_tokens[raw_token] = scoped_token
        return scoped_token

    def validate_token(self, token_value: str, required_tenant_id: TenantId) -> ScopedToken:
        """Validates token exists, is unexpired, and matches tenant."""
        token = self._active_tokens.get(token_value)
        if not token:
            raise CredentialBrokerError(
                code="ERR_INVALID_TOKEN",
                message="Ephemeral token does not exist or has been revoked.",
                retryable=False,
            )

        if token.is_expired():
            self._active_tokens.pop(token_value, None)
            raise CredentialBrokerError(
                code="ERR_TOKEN_EXPIRED",
                message="Ephemeral token has expired (TTL <= 15m exceeded).",
                retryable=False,
            )

        if token.tenant_id != required_tenant_id:
            raise TenancyViolationError(
                f"Token tenant mismatch: Token belongs to '{token.tenant_id}', "
                f"caller is '{required_tenant_id}' (INV-TEN-001).",
            )

        return token

    def revoke_token(self, token_value: str) -> None:
        """Revokes an ephemeral token immediately."""
        self._active_tokens.pop(token_value, None)
