"""
RevPilot AI — Secret Zero-Downtime Rotation Service
Specification: docs/15-security/SECURITY-ARCHITECTURE.md §7.2, ADR-0009
Conforms to INV-SEC-001, INV-REL-001, and TC-P07-016.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable
from uuid import uuid4
from pydantic import BaseModel, ConfigDict

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.security.secrets.envelope import (
    EnvelopeEncryptionService,
    EnvelopeEncryptedSecret,
)
from revpilot.modules.security.secrets.broker import (
    CredentialBroker,
    SecretReference,
    SecretLifecycleStatus,
    SecretRevokedError,
    SecretNotFoundError,
    RotationValidationFailedError,
)


class RotationStatus(str, Enum):
    INITIATED = "INITIATED"
    VALIDATED = "VALIDATED"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"


class RotationSession(BaseModel):
    """Tracks a dual-version zero-downtime secret rotation workflow."""
    model_config = ConfigDict(frozen=True)

    session_id: str
    tenant_id: TenantId
    secret_ref: SecretReference
    new_envelope: EnvelopeEncryptedSecret
    status: RotationStatus
    created_at: UtcDateTime
    committed_at: UtcDateTime | None = None
    rollback_reason: str | None = None


class SecretRotationService:
    """
    Orchestrates zero-downtime dual-version secret rotation, external canary validation,
    idempotent promotion, automated rollback, and immediate revocation purging.
    """

    def __init__(
        self,
        broker: CredentialBroker,
        envelope_service: EnvelopeEncryptionService | None = None,
    ) -> None:
        self.broker = broker
        self.envelope_service = envelope_service or broker.envelope_service
        self._sessions: dict[str, tuple[RotationSession, str]] = {}

    def initiate_rotation(
        self,
        tenant_id: TenantId,
        secret_ref: SecretReference,
        new_secret_plaintext: str,
    ) -> RotationSession:
        """
        Transition secret to ROTATING and prepare encrypted pending envelope.
        In-flight callers can continue utilizing the active secret.
        """
        record = self.broker.get_secret_record(tenant_id, secret_ref)
        if record.status == SecretLifecycleStatus.REVOKED:
            raise SecretRevokedError(f"Cannot rotate revoked secret '{secret_ref.value}'")

        kek, kek_id = self.broker._get_tenant_kek(tenant_id)
        new_version = record.envelope.version + 1

        new_envelope = self.envelope_service.encrypt(
            plaintext=new_secret_plaintext,
            kek=kek,
            kek_id=kek_id,
            version=new_version,
        )

        # Register plaintext for leak scrubbing
        if new_secret_plaintext:
            self.broker._scrub_registry.add(new_secret_plaintext)

        # Mark record as ROTATING
        record.status = SecretLifecycleStatus.ROTATING
        record.updated_at = UtcDateTime.now()

        session_id = f"rot_sess_{uuid4().hex}"
        session = RotationSession(
            session_id=session_id,
            tenant_id=tenant_id,
            secret_ref=secret_ref,
            new_envelope=new_envelope,
            status=RotationStatus.INITIATED,
            created_at=UtcDateTime.now(),
        )

        self._sessions[session_id] = (session, new_secret_plaintext)
        return session

    def validate_and_commit_rotation(
        self,
        session_id: str,
        canary_validator: Callable[[str], bool] | None = None,
    ) -> None:
        """
        Validate new key via external provider canary check.
        Promote new version to ACTIVE on success, or rollback on failure.
        Idempotent by session ID.
        """
        session_entry = self._sessions.get(session_id)
        if not session_entry:
            raise SecretNotFoundError(f"Rotation session '{session_id}' not found")

        session, plaintext = session_entry

        # Idempotent check
        if session.status == RotationStatus.COMMITTED:
            return

        if session.status == RotationStatus.ROLLED_BACK:
            raise RotationValidationFailedError(
                f"Rotation session '{session_id}' was already rolled back: {session.rollback_reason}"
            )

        # 1. Canary Validation against External Provider
        if canary_validator is not None:
            try:
                is_valid = canary_validator(plaintext)
                if not is_valid:
                    self.rollback_rotation(session_id, reason="Canary validation returned False")
                    raise RotationValidationFailedError(
                        "Rotation validation failed: external canary rejected new key credentials"
                    )
            except RotationValidationFailedError:
                raise
            except Exception as err:
                self.rollback_rotation(session_id, reason=f"Canary validation exception: {err}")
                raise RotationValidationFailedError(
                    f"Rotation validation failed: canary error: {err}"
                ) from err

        # 2. Promote New Version to ACTIVE & Retain Previous Envelope (Dual-Version)
        record = self.broker.get_secret_record(session.tenant_id, session.secret_ref)
        record.previous_envelope = record.envelope
        record.envelope = session.new_envelope
        record.status = SecretLifecycleStatus.ACTIVE
        record.updated_at = UtcDateTime.now()

        # 3. Update Session to COMMITTED
        committed_session = RotationSession(
            session_id=session.session_id,
            tenant_id=session.tenant_id,
            secret_ref=session.secret_ref,
            new_envelope=session.new_envelope,
            status=RotationStatus.COMMITTED,
            created_at=session.created_at,
            committed_at=UtcDateTime.now(),
        )
        self._sessions[session_id] = (committed_session, plaintext)

        # 4. Purge Ephemeral Token Cache for Secret
        self.broker.purge_cache(tenant_id=session.tenant_id, secret_ref=session.secret_ref)

    def rollback_rotation(self, session_id: str, reason: str = "") -> None:
        """
        Abort rotation, leaving the current active version intact.
        """
        session_entry = self._sessions.get(session_id)
        if not session_entry:
            raise SecretNotFoundError(f"Rotation session '{session_id}' not found")

        session, plaintext = session_entry
        if session.status == RotationStatus.COMMITTED:
            raise ValueError("Cannot rollback already committed rotation session")

        record = self.broker.get_secret_record(session.tenant_id, session.secret_ref)
        record.status = SecretLifecycleStatus.ACTIVE
        record.updated_at = UtcDateTime.now()

        rolled_back_session = RotationSession(
            session_id=session.session_id,
            tenant_id=session.tenant_id,
            secret_ref=session.secret_ref,
            new_envelope=session.new_envelope,
            status=RotationStatus.ROLLED_BACK,
            created_at=session.created_at,
            rollback_reason=reason,
        )
        self._sessions[session_id] = (rolled_back_session, plaintext)

    def revoke_secret(self, tenant_id: TenantId, secret_ref: SecretReference) -> None:
        """
        Immediately revoke a secret and purge active broker tokens (< 500ms).
        Subsequent token resolutions will fail closed with 403 SECRET_REVOKED.
        """
        record = self.broker.get_secret_record(tenant_id, secret_ref)
        record.status = SecretLifecycleStatus.REVOKED
        record.updated_at = UtcDateTime.now()

        # Purge all cached tokens immediately
        self.broker.purge_cache(tenant_id=tenant_id, secret_ref=secret_ref)
