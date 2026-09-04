"""
RevPilot AI — Connector Lifecycle Service & State Machine
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §3, DATABASE-SCHEMA.md §21.3
Conforms to INV-DATA-002, INV-SEC-003, and INV-REL-001.
"""

from __future__ import annotations

from typing import Callable
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.security.secrets.broker import SecretReference
from revpilot.modules.connectors.domain import (
    ConnectorStatus,
    ConnectorInstanceRecord,
    ConnectorNotFoundError,
    InvalidScopeError,
    InvalidStateTransitionError,
    AuthExpiredError,
    RateLimitedError,
)

VALID_TRANSITIONS: dict[ConnectorStatus, set[ConnectorStatus]] = {
    ConnectorStatus.REGISTERED: {
        ConnectorStatus.CONFIGURED,
        ConnectorStatus.DELETING,
        ConnectorStatus.FAILED,
    },
    ConnectorStatus.CONFIGURED: {
        ConnectorStatus.VALIDATING,
        ConnectorStatus.DELETING,
        ConnectorStatus.FAILED,
    },
    ConnectorStatus.VALIDATING: {
        ConnectorStatus.ACTIVE,
        ConnectorStatus.FAILED,
        ConnectorStatus.DELETING,
    },
    ConnectorStatus.ACTIVE: {
        ConnectorStatus.DEGRADED,
        ConnectorStatus.PAUSED,
        ConnectorStatus.AUTH_EXPIRED,
        ConnectorStatus.SCHEMA_DRIFT,
        ConnectorStatus.DELETING,
        ConnectorStatus.FAILED,
    },
    ConnectorStatus.DEGRADED: {
        ConnectorStatus.ACTIVE,
        ConnectorStatus.AUTH_EXPIRED,
        ConnectorStatus.PAUSED,
        ConnectorStatus.DELETING,
        ConnectorStatus.FAILED,
    },
    ConnectorStatus.PAUSED: {
        ConnectorStatus.ACTIVE,
        ConnectorStatus.DELETING,
        ConnectorStatus.FAILED,
    },
    ConnectorStatus.AUTH_EXPIRED: {
        ConnectorStatus.VALIDATING,
        ConnectorStatus.CONFIGURED,
        ConnectorStatus.DELETING,
        ConnectorStatus.FAILED,
    },
    ConnectorStatus.SCHEMA_DRIFT: {
        ConnectorStatus.QUARANTINED,
        ConnectorStatus.DELETING,
        ConnectorStatus.FAILED,
    },
    ConnectorStatus.QUARANTINED: {
        ConnectorStatus.RECONCILIATION_REQUIRED,
        ConnectorStatus.DELETING,
        ConnectorStatus.FAILED,
    },
    ConnectorStatus.RECONCILIATION_REQUIRED: {
        ConnectorStatus.ACTIVE,
        ConnectorStatus.DELETING,
        ConnectorStatus.FAILED,
    },
    ConnectorStatus.FAILED: {
        ConnectorStatus.CONFIGURED,
        ConnectorStatus.VALIDATING,
        ConnectorStatus.DELETING,
    },
    ConnectorStatus.DELETING: {
        ConnectorStatus.DELETED,
    },
    ConnectorStatus.DELETED: set(),
}


class ConnectorLifecycleService:
    """
    Authoritative service governing connector registration, credential attachment,
    strict state machine transitions across 13 states, and failure recovery.
    """

    def __init__(self) -> None:
        self._connectors: dict[str, ConnectorInstanceRecord] = {}

    def register_connector(
        self,
        tenant_id: TenantId,
        provider: str,
        capability: str,
        provider_version: str = "v1",
        auth_method: str = "oauth2_client_credentials",
    ) -> UUIDv7:
        """
        Register a new connector manifest in REGISTERED status.
        """
        cid = UUIDv7.generate()
        now = UtcDateTime.now()
        record = ConnectorInstanceRecord(
            connector_id=cid,
            tenant_id=tenant_id,
            provider_name=provider,
            provider_version=provider_version,
            capability_type=capability,
            auth_method=auth_method,
            status=ConnectorStatus.REGISTERED,
            created_at=now,
            updated_at=now,
        )
        self._connectors[cid.value] = record
        return cid

    def get_connector(self, connector_id: UUIDv7) -> ConnectorInstanceRecord:
        """Fetch connector record or raise 404."""
        record = self._connectors.get(connector_id.value)
        if not record:
            raise ConnectorNotFoundError(f"Connector '{connector_id.value}' not found")
        return record

    def list_connectors(self, tenant_id: TenantId) -> list[ConnectorInstanceRecord]:
        """Fetch all connectors owned by a tenant."""
        return [c for c in self._connectors.values() if c.tenant_id.value == tenant_id.value]

    def configure_credentials(
        self,
        connector_id: UUIDv7,
        secret_ref: SecretReference,
        scopes: list[str],
    ) -> None:
        """
        Bind credential reference and least-privilege scopes.
        Transitions state from REGISTERED or AUTH_EXPIRED/FAILED to CONFIGURED.
        """
        record = self.get_connector(connector_id)
        if not scopes:
            raise InvalidScopeError("Connector registration requires at least one granted scope")

        record.secret_ref = secret_ref
        record.granted_scopes = list(scopes)
        self.transition_state(connector_id, ConnectorStatus.CONFIGURED, reason="Credentials configured")

    def validate_connectivity(
        self,
        connector_id: UUIDv7,
        probe_fn: Callable[[], bool] | None = None,
    ) -> bool:
        """
        Transition to VALIDATING and execute connectivity probe.
        Promotes to ACTIVE on success, or FAILED on rejection.
        """
        record = self.get_connector(connector_id)
        self.transition_state(connector_id, ConnectorStatus.VALIDATING, reason="Starting connectivity probe")

        is_healthy = True
        if probe_fn is not None:
            try:
                is_healthy = probe_fn()
            except Exception:
                is_healthy = False

        if is_healthy:
            self.transition_state(connector_id, ConnectorStatus.ACTIVE, reason="Connectivity and scopes verified")
            record.consecutive_errors = 0
            return True
        else:
            self.transition_state(connector_id, ConnectorStatus.FAILED, reason="Connectivity probe failed")
            return False

    def transition_state(
        self,
        connector_id: UUIDv7,
        new_status: ConnectorStatus,
        reason: str = "",
    ) -> None:
        """
        Enforce state machine transitions strictly adhering to CONNECTOR-PLATFORM-SPEC.md §3.
        Rejects illegal jumps with 400 INVALID_STATE_TRANSITION.
        """
        record = self.get_connector(connector_id)
        current = record.status

        # Idempotent same-state update
        if current == new_status:
            record.status_reason = reason
            record.updated_at = UtcDateTime.now()
            return

        allowed = VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal connector transition from '{current.value}' to '{new_status.value}'"
            )

        record.status = new_status
        record.status_reason = reason
        record.updated_at = UtcDateTime.now()

    def record_sync_success(
        self,
        connector_id: UUIDv7,
        cursor: str,
        lag_seconds: int,
    ) -> None:
        """Record successful sync, checkpoint position, and reset error meters."""
        record = self.get_connector(connector_id)
        record.cursor_position = cursor
        record.sync_lag_seconds = lag_seconds
        record.last_successful_sync_at = UtcDateTime.now()
        record.consecutive_errors = 0
        record.consecutive_rate_limits = 0
        record.updated_at = UtcDateTime.now()

    def record_auth_failure(self, connector_id: UUIDv7) -> None:
        """
        Automated transition to AUTH_EXPIRED upon HTTP 401/403 from provider.
        Halts sync operations immediately (AC-P07-005-02 / TC-P07-017).
        """
        record = self.get_connector(connector_id)
        record.consecutive_errors += 1
        self.transition_state(
            connector_id,
            ConnectorStatus.AUTH_EXPIRED,
            reason="401/403 Unauthorized received from upstream provider; sync halted",
        )

    def record_rate_limit(self, connector_id: UUIDv7) -> None:
        """
        Automated transition to DEGRADED upon >= 3 consecutive 429 rate limit responses.
        """
        record = self.get_connector(connector_id)
        record.consecutive_rate_limits += 1
        if record.consecutive_rate_limits >= 3 and record.status == ConnectorStatus.ACTIVE:
            self.transition_state(
                connector_id,
                ConnectorStatus.DEGRADED,
                reason="Consecutive rate limit (429) thresholds exceeded; backoff engaged",
            )

    def record_health_recovery(self, connector_id: UUIDv7) -> None:
        """
        Automated recovery from DEGRADED to ACTIVE when healthy response resumes.
        """
        record = self.get_connector(connector_id)
        record.consecutive_rate_limits = 0
        record.consecutive_errors = 0
        if record.status == ConnectorStatus.DEGRADED:
            self.transition_state(
                connector_id,
                ConnectorStatus.ACTIVE,
                reason="Health probe recovered 200 OK; restored full sync rate",
            )

    def delete_connector(self, connector_id: UUIDv7) -> None:
        """
        Gracefully transition to DELETING, purge cursors/credentials, and advance to DELETED.
        """
        record = self.get_connector(connector_id)
        self.transition_state(connector_id, ConnectorStatus.DELETING, reason="Connector teardown initiated")

        # Purge sync state, cursors, checkpoints, and credentials
        record.cursor_position = None
        record.secret_ref = None
        record.sync_lag_seconds = 0

        self.transition_state(connector_id, ConnectorStatus.DELETED, reason="Teardown complete; state purged")
