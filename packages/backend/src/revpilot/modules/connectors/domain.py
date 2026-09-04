"""
RevPilot AI — Connector Platform Domain Models & State Aggregate
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §2, DATABASE-SCHEMA.md §21.3
Conforms to INV-DATA-002, INV-SEC-001, and INV-SEC-003.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.security.secrets.broker import SecretReference


class SyncMode(str, Enum):
    BATCH_PULL = "BATCH_PULL"
    WEBHOOK_PUSH = "WEBHOOK_PUSH"
    CDC_STREAM = "CDC_STREAM"


class ConnectorStatus(str, Enum):
    REGISTERED = "REGISTERED"
    CONFIGURED = "CONFIGURED"
    VALIDATING = "VALIDATING"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    PAUSED = "PAUSED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    QUARANTINED = "QUARANTINED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    DELETING = "DELETING"
    DELETED = "DELETED"
    FAILED = "FAILED"


class ConnectorError(Exception):
    """Base error for connector domain operations."""
    def __init__(self, message: str, code: str = "CONNECTOR_ERROR", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ConnectorNotFoundError(ConnectorError):
    def __init__(self, message: str = "Connector not found") -> None:
        super().__init__(message=message, code="CONNECTOR_NOT_FOUND", status_code=404)


class InvalidScopeError(ConnectorError):
    def __init__(self, message: str = "Requested scopes exceed policy") -> None:
        super().__init__(message=message, code="INVALID_SCOPE", status_code=422)


class InvalidStateTransitionError(ConnectorError):
    def __init__(self, message: str = "Invalid connector lifecycle state transition") -> None:
        super().__init__(message=message, code="INVALID_STATE_TRANSITION", status_code=400)


class AuthExpiredError(ConnectorError):
    def __init__(self, message: str = "Integration authentication expired") -> None:
        super().__init__(message=message, code="AUTH_EXPIRED", status_code=401)


class RateLimitedError(ConnectorError):
    def __init__(self, message: str = "Provider rate limit reached") -> None:
        super().__init__(message=message, code="RATE_LIMITED", status_code=429)


class ConnectorInstanceRecord(BaseModel):
    """
    Canonical Connector Aggregate conforming to DATABASE-SCHEMA.md §21.3.
    Strictly isolated by TenantId; holds opaque SecretReference (zero raw secret exposure).
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector_id: UUIDv7
    tenant_id: TenantId
    provider_name: str
    provider_version: str = "v1"
    capability_type: str
    auth_method: str = "oauth2_client_credentials"
    secret_ref: SecretReference | None = None
    granted_scopes: list[str] = Field(default_factory=list)
    data_classification: str = "CONFIDENTIAL"
    sync_mode: SyncMode = SyncMode.BATCH_PULL
    cursor_position: str | None = None
    last_successful_sync_at: UtcDateTime | None = None
    sync_lag_seconds: int = 0
    schema_version: str = "1.0.0"
    mapping_version: str = "1.0.0"
    status: ConnectorStatus = ConnectorStatus.REGISTERED
    rate_limit_per_minute: int = 60
    retry_class: str = "standard_backoff"
    timeout_seconds: int = 30
    freshness_target_minutes: int = 60
    quarantine_count: int = 0
    consecutive_errors: int = 0
    consecutive_rate_limits: int = 0
    status_reason: str | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime
