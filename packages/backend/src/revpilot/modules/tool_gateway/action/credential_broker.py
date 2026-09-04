"""
RevPilot AI — Credential Broker & Ephemeral Token Exchange
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7.2, docs/15-security/SECURITY-ARCHITECTURE.md §7.1
Conforms to INV-SEC-001, ADR-0009: Ephemeral token TTL capped at 15 minutes, bound to tenant/provider/action.
"""

from __future__ import annotations
from datetime import timedelta
import secrets
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.results import Result, Success, Failure
from revpilot.shared.errors import DomainError


class GatewayError(DomainError):
    """Base domain error for Tool Gateway and Credential Broker operations."""

    def __init__(
        self,
        code: str = "ERR_GATEWAY_ERROR",
        message: str = "Tool gateway operation failed",
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=retryable)


class EphemeralCredential(BaseModel):
    """
    Short-lived ephemeral credential scoped strictly to tenant, provider, and action.
    Bound to a maximum 15-minute validity window per ADR-0009.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    token_id: str = Field(min_length=1)
    target_provider: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    expires_at: UtcDateTime
    token_secret: str = ""


class CredentialBroker:
    """
    Internal broker issuing short-lived, least-privilege tokens for tool dispatch.
    Agents never possess long-lived secrets or external API keys (INV-SEC-001).
    """

    MAX_TTL_SECONDS: int = 900  # 15 minutes (ADR-0009)

    def __init__(self) -> None:
        self._active_tokens: dict[str, EphemeralCredential] = {}

    async def issue_ephemeral_token(
        self,
        tenant_id: TenantId,
        provider: str,
        action_type: str,
        ttl_seconds: int = 900,
    ) -> EphemeralCredential:
        """
        Issue an ephemeral token bound strictly to tenant, provider, and action type.
        Fails if requested TTL exceeds the 15-minute maximum limit.
        """
        if ttl_seconds > self.MAX_TTL_SECONDS:
            raise GatewayError(
                code="ERR_INVALID_TOKEN_TTL",
                message=f"Requested token TTL of {ttl_seconds}s exceeds maximum allowed {self.MAX_TTL_SECONDS}s (15 minutes)",
                details={"requested_ttl": ttl_seconds, "max_ttl": self.MAX_TTL_SECONDS},
            )

        token_id = f"tok_eph_{secrets.token_hex(16)}"
        scope = f"tenant:{tenant_id}:provider:{provider}:action:{action_type}"
        now = UtcDateTime.now()
        expires_at = UtcDateTime(now.value + timedelta(seconds=ttl_seconds))

        credential = EphemeralCredential(
            token_id=token_id,
            target_provider=provider,
            scope=scope,
            expires_at=expires_at,
            token_secret=secrets.token_urlsafe(32),
        )
        self._active_tokens[token_id] = credential
        return credential

    def validate_token(
        self,
        credential: EphemeralCredential,
        tenant_id: TenantId,
        provider: str,
        action_type: str,
        as_of_time: UtcDateTime | None = None,
    ) -> Result[None, GatewayError]:
        """
        Validate that the credential matches the execution scope and has not expired.
        """
        as_of = as_of_time or UtcDateTime.now()

        # 1. Expiration check
        if credential.expires_at <= as_of:
            return Failure(
                GatewayError(
                    code="ERR_CREDENTIAL_EXPIRED",
                    message=f"Ephemeral credential '{credential.token_id}' expired at {credential.expires_at}",
                    details={"token_id": credential.token_id, "expires_at": str(credential.expires_at), "as_of": str(as_of)},
                )
            )

        # 2. Scope validation: Tenant
        expected_tenant_prefix = f"tenant:{tenant_id}:"
        if not credential.scope.startswith(expected_tenant_prefix):
            return Failure(
                GatewayError(
                    code="ERR_CREDENTIAL_SCOPE_MISMATCH",
                    message=f"Credential tenant scope mismatch: expected tenant '{tenant_id}'",
                    details={"token_id": credential.token_id, "token_scope": credential.scope, "expected_tenant": str(tenant_id)},
                )
            )

        # 3. Scope validation: Provider
        if credential.target_provider != provider or f":provider:{provider}:" not in credential.scope:
            return Failure(
                GatewayError(
                    code="ERR_CREDENTIAL_SCOPE_MISMATCH",
                    message=f"Credential provider mismatch: expected provider '{provider}', token bound to '{credential.target_provider}'",
                    details={"token_id": credential.token_id, "expected_provider": provider, "token_provider": credential.target_provider},
                )
            )

        # 4. Scope validation: Action
        expected_action_suffix = f":action:{action_type}"
        if not credential.scope.endswith(expected_action_suffix):
            return Failure(
                GatewayError(
                    code="ERR_CREDENTIAL_SCOPE_MISMATCH",
                    message=f"Credential action mismatch: expected action '{action_type}'",
                    details={"token_id": credential.token_id, "token_scope": credential.scope, "expected_action": action_type},
                )
            )

        return Success(None)
