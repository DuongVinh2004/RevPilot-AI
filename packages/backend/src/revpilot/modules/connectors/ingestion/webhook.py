"""
RevPilot AI — Inbound Webhook Signature & Anti-Replay Verifier
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §4, API-STANDARDS.md §10.7
Conforms to INV-REL-001 and TC-P07-018.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone

from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.connectors.domain import ConnectorError


class InvalidWebhookSignatureError(ConnectorError):
    def __init__(self, message: str = "Invalid webhook signature") -> None:
        super().__init__(message=message, code="INVALID_SIGNATURE", status_code=401)


class TimestampSkewError(ConnectorError):
    def __init__(self, message: str = "Webhook timestamp out of bounds") -> None:
        super().__init__(message=message, code="TIMESTAMP_SKEW", status_code=400)


class PayloadTooLargeError(ConnectorError):
    def __init__(self, message: str = "Webhook payload too large") -> None:
        super().__init__(message=message, code="PAYLOAD_TOO_LARGE", status_code=413)


def generate_webhook_signature(raw_body: bytes, secret: str, timestamp_str: str) -> str:
    """Generate canonical HMAC-SHA256 signature over 't={timestamp}.{body}'."""
    signed_payload = f"t={timestamp_str}.".encode("utf-8") + raw_body
    return hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()


class WebhookVerifier:
    """
    Validates inbound push webhooks using constant-time HMAC-SHA256 signature verification,
    timestamp anti-replay defense (max 300s skew), and payload size bounding (max 2MB).
    """

    def __init__(
        self,
        max_skew_seconds: int = 300,
        max_payload_bytes: int = 2 * 1024 * 1024,  # 2MB
    ) -> None:
        self.max_skew_seconds = max_skew_seconds
        self.max_payload_bytes = max_payload_bytes

    def verify_signature(
        self,
        raw_body: bytes,
        signature_header: str,
        secret: str,
        timestamp_header: str,
        as_of_time: UtcDateTime | None = None,
    ) -> bool:
        """
        Verify inbound webhook signature and freshness.
        Enforces 413 on oversized payloads, 400 on skew > 300s, 401 on signature forgery.
        """
        # 1. Payload Size Bounding (2MB Max)
        if len(raw_body) > self.max_payload_bytes:
            raise PayloadTooLargeError(
                f"Webhook payload size {len(raw_body)} bytes exceeds maximum {self.max_payload_bytes} bytes (2MB)"
            )

        # 2. Timestamp Skew Evaluation (Anti-Replay Window <= 300s)
        try:
            # Supports Unix epoch seconds or float
            ts_float = float(timestamp_header.strip())
        except ValueError:
            # Fallback ISO parse
            try:
                dt = datetime.fromisoformat(timestamp_header.strip())
                ts_float = dt.timestamp()
            except Exception as err:
                raise TimestampSkewError(f"Invalid timestamp format '{timestamp_header}': {err}") from err

        now_dt = as_of_time or UtcDateTime.now()
        current_ts = now_dt.value.timestamp()
        skew_seconds = abs(current_ts - ts_float)

        if skew_seconds > self.max_skew_seconds:
            raise TimestampSkewError(
                f"Webhook timestamp skew {skew_seconds:.1f}s exceeds maximum allowed tolerance of {self.max_skew_seconds}s"
            )

        # 3. Constant-Time HMAC-SHA256 Signature Verification
        # Strip provider scheme prefix if present (e.g. 'v1=', 'sha256=')
        actual_sig = signature_header.strip()
        if "=" in actual_sig:
            actual_sig = actual_sig.split("=", 1)[1]

        expected_sig = generate_webhook_signature(raw_body, secret, timestamp_header.strip())

        if not hmac.compare_digest(actual_sig, expected_sig):
            raise InvalidWebhookSignatureError("HMAC-SHA256 signature mismatch: forged or tampered webhook payload")

        return True
