"""
RevPilot AI — TC-P07-018: Webhook HMAC-SHA256 Signature Verification Test
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §4.1
Conforms to AC-P07-006-01 and INV-REL-001.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_connectors_module():
    """Ensure connectors module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.connectors"):
            sys.modules.pop(mod, None)


def test_webhook_signature_verification_and_anti_replay():
    """
    TC-P07-018 / AC-P07-006-01:
    - Valid HMAC-SHA256 signature with fresh timestamp passes verification.
    - Forged signature raises 401 INVALID_SIGNATURE.
    - Timestamp skew > 300s raises 400 TIMESTAMP_SKEW.
    - Payload size > 2MB raises 413 PAYLOAD_TOO_LARGE.
    """
    from revpilot.modules.connectors.ingestion import (
        WebhookVerifier,
        generate_webhook_signature,
        InvalidWebhookSignatureError,
        TimestampSkewError,
        PayloadTooLargeError,
    )

    verifier = WebhookVerifier(max_skew_seconds=300, max_payload_bytes=2 * 1024 * 1024)
    secret = "whsec_test_enterprise_webhook_secret_998877"
    raw_body = b'{"event": "invoice.paid", "amount": 150000, "customer": "cus_123"}'

    now = UtcDateTime.now()
    now_ts = int(now.value.timestamp())
    valid_timestamp = str(now_ts)

    # 1. Valid Signature & Fresh Timestamp: PASS
    valid_sig = generate_webhook_signature(raw_body, secret, valid_timestamp)
    is_valid = verifier.verify_signature(
        raw_body=raw_body,
        signature_header=f"v1={valid_sig}",
        secret=secret,
        timestamp_header=valid_timestamp,
        as_of_time=now,
    )
    assert is_valid is True

    # 2. Forged Signature: FAIL CLOSED (401 INVALID_SIGNATURE)
    forged_sig = "a" * 64
    with pytest.raises(InvalidWebhookSignatureError) as exc_info:
        verifier.verify_signature(
            raw_body=raw_body,
            signature_header=f"v1={forged_sig}",
            secret=secret,
            timestamp_header=valid_timestamp,
            as_of_time=now,
        )
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "INVALID_SIGNATURE"

    # 3. Timestamp Skew > 300s (Replay Attack): FAIL CLOSED (400 TIMESTAMP_SKEW)
    stale_timestamp = str(now_ts - 305)  # 305 seconds old
    stale_sig = generate_webhook_signature(raw_body, secret, stale_timestamp)

    with pytest.raises(TimestampSkewError) as exc_info:
        verifier.verify_signature(
            raw_body=raw_body,
            signature_header=f"v1={stale_sig}",
            secret=secret,
            timestamp_header=stale_timestamp,
            as_of_time=now,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "TIMESTAMP_SKEW"

    # 4. Payload Size Exceeding 2MB: FAIL CLOSED (413 PAYLOAD_TOO_LARGE)
    oversized_body = b"x" * (2 * 1024 * 1024 + 1)
    oversized_sig = generate_webhook_signature(oversized_body, secret, valid_timestamp)

    with pytest.raises(PayloadTooLargeError) as exc_info:
        verifier.verify_signature(
            raw_body=oversized_body,
            signature_header=f"v1={oversized_sig}",
            secret=secret,
            timestamp_header=valid_timestamp,
            as_of_time=now,
        )
    assert exc_info.value.status_code == 413
    assert exc_info.value.code == "PAYLOAD_TOO_LARGE"
