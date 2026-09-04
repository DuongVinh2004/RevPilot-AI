"""
RevPilot AI — Connectors & Ingestion Platform Module
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md
Conforms to INV-DATA-002, INV-SEC-001, and INV-SEC-003.
"""

from revpilot.modules.connectors.domain import (
    AuthExpiredError,
    ConnectorError,
    ConnectorInstanceRecord,
    ConnectorNotFoundError,
    ConnectorStatus,
    InvalidScopeError,
    InvalidStateTransitionError,
    RateLimitedError,
    SyncMode,
)
from revpilot.modules.connectors.lifecycle import (
    VALID_TRANSITIONS,
    ConnectorLifecycleService,
)
from revpilot.modules.connectors.health import (
    ConnectorHealthService,
    HealthProbeResult,
    HealthStatus,
)
from revpilot.modules.connectors.ingestion import (
    DriftClassification,
    DriftEvaluationResult,
    InboxReceipt,
    InboxStatus,
    InvalidWebhookSignatureError,
    PayloadTooLargeError,
    QuarantineRecord,
    QuarantineService,
    SchemaDriftClassifier,
    TimestampSkewError,
    TransactionalInboxService,
    WebhookVerifier,
    generate_webhook_signature,
)

__all__ = [
    "AuthExpiredError",
    "ConnectorError",
    "ConnectorHealthService",
    "ConnectorInstanceRecord",
    "ConnectorLifecycleService",
    "ConnectorNotFoundError",
    "ConnectorStatus",
    "DriftClassification",
    "DriftEvaluationResult",
    "HealthProbeResult",
    "HealthStatus",
    "InboxReceipt",
    "InboxStatus",
    "InvalidScopeError",
    "InvalidStateTransitionError",
    "InvalidWebhookSignatureError",
    "PayloadTooLargeError",
    "QuarantineRecord",
    "QuarantineService",
    "RateLimitedError",
    "SchemaDriftClassifier",
    "SyncMode",
    "TimestampSkewError",
    "TransactionalInboxService",
    "VALID_TRANSITIONS",
    "WebhookVerifier",
    "generate_webhook_signature",
]
