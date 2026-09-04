"""
RevPilot AI — Connectors Ingestion Submodule
"""

from revpilot.modules.connectors.ingestion.webhook import (
    InvalidWebhookSignatureError,
    PayloadTooLargeError,
    TimestampSkewError,
    WebhookVerifier,
    generate_webhook_signature,
)
from revpilot.modules.connectors.ingestion.inbox import (
    InboxReceipt,
    InboxStatus,
    TransactionalInboxService,
)
from revpilot.modules.connectors.ingestion.drift import (
    DriftClassification,
    DriftEvaluationResult,
    SchemaDriftClassifier,
)
from revpilot.modules.connectors.ingestion.quarantine import (
    QuarantineRecord,
    QuarantineService,
)

__all__ = [
    "DriftClassification",
    "DriftEvaluationResult",
    "InboxReceipt",
    "InboxStatus",
    "InvalidWebhookSignatureError",
    "PayloadTooLargeError",
    "QuarantineRecord",
    "QuarantineService",
    "SchemaDriftClassifier",
    "TimestampSkewError",
    "TransactionalInboxService",
    "WebhookVerifier",
    "generate_webhook_signature",
]
