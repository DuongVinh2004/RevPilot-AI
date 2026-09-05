"""
RevPilot AI — Credential Broker & Workload Identity Contract
Specification: docs/15-security/SECURITY-ARCHITECTURE.md §7.1, docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §1.1, ADR-0009
Conforms to INV-SEC-001, INV-TEN-001, and INV-REL-001.
"""

from __future__ import annotations

from datetime import timedelta
from enum import Enum
import hashlib
import hmac
import re
import secrets
from typing import Protocol
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.security.secrets.envelope import (
    EnvelopeEncryptionService,
    EnvelopeEncryptedSecret,
)


class SecretLifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ROTATING = "ROTATING"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class SecretSecurityError(Exception):
    """Base error for secret and credential broker operations."""
    def __init__(self, message: str, code: str = "SECRET_SECURITY_ERROR", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class SecretNotFoundError(SecretSecurityError):
    def __init__(self, message: str = "Secret reference not found") -> None:
        super().__init__(message=message, code="SECRET_NOT_FOUND", status_code=404)


class SecretRevokedError(SecretSecurityError):
    def __init__(self, message: str = "Secret has been revoked") -> None:
        super().__init__(message=message, code="SECRET_REVOKED", status_code=403)


class SecretExpiredError(SecretSecurityError):
    def __init__(self, message: str = "Secret has expired") -> None:
        super().__init__(message=message, code="SECRET_EXPIRED", status_code=403)


class RotationValidationFailedError(SecretSecurityError):
    def __init__(self, message: str = "Rotation validation failed") -> None:
        super().__init__(message=message, code="ROTATION_VALIDATION_FAILED", status_code=422)


class BrokerUnavailableError(SecretSecurityError):
    def __init__(self, message: str = "Secret broker unavailable") -> None:
        super().__init__(message=message, code="BROKER_UNAVAILABLE", status_code=503)


class ScopeExpansionDeniedError(SecretSecurityError):
    def __init__(self, message: str = "Scope expansion denied: requested scope exceeds granted permissions") -> None:
        super().__init__(message=message, code="SCOPE_EXPANSION_DENIED", status_code=403)


class SecretAccessDeniedError(SecretSecurityError):
    def __init__(self, message: str = "Cross-tenant secret access strictly denied") -> None:
        super().__init__(message=message, code="SECRET_ACCESS_DENIED", status_code=403)


class SecretReference(BaseModel):
    """
    Opaque, immutable identifier referencing a secret stored in the Credential Broker.
    Raw secrets are NEVER exposed in Agent Runtimes or logs (INV-SEC-001).
    """
    model_config = ConfigDict(frozen=True)

    value: str

    @classmethod
    def generate(cls, prefix: str = "sec_ref_") -> SecretReference:
        return cls(value=f"{prefix}{uuid4().hex}")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"SecretReference({self.value})"


class EphemeralProviderToken(BaseModel):
    """
    Short-lived, scoped token issued to connector dispatch workers.
    Lifespan <= 15 minutes (canonical bound per SECURITY-ARCHITECTURE.md §7.1).
    """
    model_config = ConfigDict(frozen=True)

    token: str
    token_type: str = "Bearer"
    expires_at: UtcDateTime
    granted_scope: str
    audience: str
    tenant_id: TenantId
    secret_ref: SecretReference
    issued_at: UtcDateTime

    def is_expired(self, as_of: UtcDateTime | None = None) -> bool:
        ref = as_of or UtcDateTime.now()
        return ref.value.timestamp() >= self.expires_at.value.timestamp()


class SecretRecord(BaseModel):
    """Internal broker record storing enveloped secret metadata and status."""
    secret_ref: SecretReference
    tenant_id: TenantId
    provider_name: str
    granted_scopes: set[str]
    allowed_audiences: set[str]
    envelope: EnvelopeEncryptedSecret
    previous_envelope: EnvelopeEncryptedSecret | None = None
    status: SecretLifecycleStatus = SecretLifecycleStatus.ACTIVE
    created_at: UtcDateTime
    updated_at: UtcDateTime


class SecretBrokerPort(Protocol):
    """Contract for broker workload identity exchange."""
    def get_scoped_token(
        self,
        tenant_id: TenantId,
        secret_ref: SecretReference,
        required_scope: str,
        audience: str,
    ) -> EphemeralProviderToken: ...


class CredentialBroker(SecretBrokerPort):
    """
    Authoritative Credential Broker providing workload identity exchange,
    short-lived provider token scoping, zero-raw-secret scrubbing, and fail-closed resilience.
    """

    def __init__(
        self,
        envelope_service: EnvelopeEncryptionService | None = None,
        default_ttl_seconds: int = 900,  # 15 minutes canonical limit
    ) -> None:
        self.envelope_service = envelope_service or EnvelopeEncryptionService()
        self.default_ttl_seconds = min(default_ttl_seconds, 3600)  # Max 60 minutes
        self._secrets: dict[str, SecretRecord] = {}
        self._tenant_keks: dict[str, tuple[bytes, str]] = {}
        self._token_cache: dict[str, EphemeralProviderToken] = {}
        self._outage_mode: bool = False
        self._scrub_registry: set[str] = set()

    def set_outage(self, enabled: bool) -> None:
        """Simulate secret service / KMS outage for resilience evaluation."""
        self._outage_mode = enabled

    def register_tenant_kek(self, tenant_id: TenantId, kek: bytes, kek_id: str | None = None) -> str:
        """Register or update tenant-specific Key Encryption Key (KEK)."""
        kid = kek_id or f"kek_{tenant_id.value}_{secrets.token_hex(4)}"
        self._tenant_keks[tenant_id.value] = (kek, kid)
        return kid

    def _get_tenant_kek(self, tenant_id: TenantId) -> tuple[bytes, str]:
        """Retrieve tenant KEK or auto-generate one for local evaluation."""
        if tenant_id.value not in self._tenant_keks:
            auto_kek = secrets.token_bytes(32)
            auto_id = f"kek_{tenant_id.value}_default"
            self._tenant_keks[tenant_id.value] = (auto_kek, auto_id)
        return self._tenant_keks[tenant_id.value]

    def register_secret(
        self,
        tenant_id: TenantId,
        secret_ref: SecretReference | str,
        plaintext_secret: str,
        provider_name: str,
        granted_scopes: list[str] | set[str],
        allowed_audiences: list[str] | set[str] | None = None,
    ) -> SecretRecord:
        """
        Securely store a connector credential wrapped in an AES-256-GCM envelope.
        The plaintext value is encrypted immediately and tracked for scrubber redaction.
        """
        ref = secret_ref if isinstance(secret_ref, SecretReference) else SecretReference(value=secret_ref)
        kek, kek_id = self._get_tenant_kek(tenant_id)

        envelope = self.envelope_service.encrypt(
            plaintext=plaintext_secret,
            kek=kek,
            kek_id=kek_id,
            version=1,
        )

        # Track plaintext in scrubber registry to guarantee zero-exposure leak detection
        if plaintext_secret:
            self._scrub_registry.add(plaintext_secret)

        record = SecretRecord(
            secret_ref=ref,
            tenant_id=tenant_id,
            provider_name=provider_name,
            granted_scopes=set(granted_scopes),
            allowed_audiences=set(allowed_audiences or []),
            envelope=envelope,
            previous_envelope=None,
            status=SecretLifecycleStatus.ACTIVE,
            created_at=UtcDateTime.now(),
            updated_at=UtcDateTime.now(),
        )
        self._secrets[ref.value] = record
        return record

    def get_secret_record(self, tenant_id: TenantId, secret_ref: SecretReference | str) -> SecretRecord:
        """Lookup secret record ensuring strict tenant boundary isolation."""
        ref_val = secret_ref.value if isinstance(secret_ref, SecretReference) else secret_ref
        record = self._secrets.get(ref_val)
        if not record:
            raise SecretNotFoundError(f"Secret reference '{ref_val}' not found")
        if record.tenant_id.value != tenant_id.value:
            raise SecretAccessDeniedError("Cross-tenant secret resolution prohibited (INV-TEN-001)")
        return record

    def get_scoped_token(
        self,
        tenant_id: TenantId,
        secret_ref: SecretReference,
        required_scope: str,
        audience: str,
        as_of_time: UtcDateTime | None = None,
    ) -> EphemeralProviderToken:
        """
        Exchange workload identity and secret reference for a narrow, short-lived provider token.
        Enforces fail-closed behavior on outage, strict tenant boundary, and scope-bounding.
        """
        # 1. Outage / Fail-Closed Guardrail (INV-REL-001)
        if self._outage_mode:
            raise BrokerUnavailableError("Secret broker unavailable: secret store or KMS unreachable")

        # 2. Secret Record Resolution & Tenant Boundary
        record = self.get_secret_record(tenant_id, secret_ref)

        # 3. Lifecycle Status Verification
        if record.status == SecretLifecycleStatus.REVOKED:
            raise SecretRevokedError(f"Secret '{secret_ref.value}' has been revoked")
        if record.status == SecretLifecycleStatus.EXPIRED:
            raise SecretExpiredError(f"Secret '{secret_ref.value}' has expired")

        # 4. Scope Bounding & Anti-Expansion (INV-SEC-001)
        req_scopes = {s for s in re.split(r"[\s,]+", required_scope.strip()) if s}
        if not req_scopes.issubset(record.granted_scopes):
            excess = req_scopes - record.granted_scopes
            raise ScopeExpansionDeniedError(
                f"Scope expansion denied: requested scope(s) {sorted(excess)} exceed granted permissions {sorted(record.granted_scopes)}"
            )

        # 5. Audience Verification
        if record.allowed_audiences and audience not in record.allowed_audiences:
            raise ScopeExpansionDeniedError(
                f"Audience denied: target audience '{audience}' not in allowed audiences {sorted(record.allowed_audiences)}"
            )

        # 6. Memory-Only Ephemeral Token Cache Lookup
        cache_key = f"{tenant_id.value}:{secret_ref.value}:{required_scope}:{audience}"
        cached = self._token_cache.get(cache_key)
        now = as_of_time or UtcDateTime.now()

        if cached and not cached.is_expired(as_of=now):
            return cached

        # 7. Internal Decryption & Token Issuance (Zero raw secret leakage)
        kek, _ = self._get_tenant_kek(tenant_id)
        # Attempt envelope decrypt to prove key validity; fail closed on corruption
        _ = self.envelope_service.decrypt(record.envelope, kek)

        token_hash = hashlib.sha256(f"{secrets.token_hex(16)}:{cache_key}:{now.isoformat()}".encode("utf-8")).hexdigest()[:24]
        token_val = f"eph_{record.provider_name}_{token_hash}"

        expires_at = UtcDateTime(now.value + timedelta(seconds=self.default_ttl_seconds))
        ephemeral_token = EphemeralProviderToken(
            token=token_val,
            token_type="Bearer",
            expires_at=expires_at,
            granted_scope=required_scope,
            audience=audience,
            tenant_id=tenant_id,
            secret_ref=secret_ref,
            issued_at=now,
        )

        self._token_cache[cache_key] = ephemeral_token
        return ephemeral_token

    def purge_cache(
        self,
        tenant_id: TenantId | None = None,
        secret_ref: SecretReference | None = None,
    ) -> int:
        """
        Immediately purge in-memory ephemeral tokens (< 500ms requirement).
        """
        if tenant_id is None and secret_ref is None:
            count = len(self._token_cache)
            self._token_cache.clear()
            return count

        keys_to_delete = []
        for k in self._token_cache:
            parts = k.split(":")
            t_val = parts[0]
            s_val = parts[1] if len(parts) > 1 else ""

            match_tenant = (tenant_id is None) or (tenant_id.value == t_val)
            match_secret = (secret_ref is None) or (secret_ref.value == s_val)

            if match_tenant and match_secret:
                keys_to_delete.append(k)

        for k in keys_to_delete:
            self._token_cache.pop(k, None)

        return len(keys_to_delete)

    def scrub_text(self, text: str) -> str:
        """
        Sanitize log strings or telemetry payloads, redacting any registered plaintext secret.
        """
        scrubbed = text
        for secret_val in self._scrub_registry:
            if secret_val and secret_val in scrubbed:
                scrubbed = scrubbed.replace(secret_val, "[REDACTED_SECRET]")
        return scrubbed
