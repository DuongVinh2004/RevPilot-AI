"""
RevPilot AI — Integration Tests for Connectors Webhook API Gateway
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §4, docs/26-api/API-STANDARDS.md §10
Conforms to INV-SEC-001, INV-DATA-002, DEC-001, DEC-006.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import time
from typing import Any
import pytest


@pytest.fixture
def api_client() -> Any:
    """FastAPI TestClient fixture with authenticated tenant context."""
    from fastapi.testclient import TestClient
    from apps.api.main import app

    token = "token_usr_admin_001_tnt_dev_001"
    app.state.auth_adapter.issue_test_token(
        token,
        sub="usr_admin_001",
        tenant_id="tnt_dev_001",
        roles=frozenset(["SYSTEM_ADMIN", "ADMIN"]),
    )
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


from revpilot.modules.connectors.ingestion.webhook import generate_webhook_signature


def _generate_signature(raw_bytes: bytes, secret: str, timestamp: str) -> str:
    sig = generate_webhook_signature(raw_bytes, secret, timestamp)
    return f"sha256={sig}"


def test_connector_webhook_valid_signature_accepted(api_client: Any):
    """Verify inbound webhook with valid cryptographic HMAC-SHA256 signature returns 202."""
    now_ts = str(int(time.time()))
    secret = "whsec_default_secret_2026"
    body_data = {"event": "invoice.paid", "amount_cents": 150000, "customer": "cust_001"}
    raw_bytes = json.dumps(body_data).encode("utf-8")

    sig_header = _generate_signature(raw_bytes, secret, now_ts)

    headers = {
        "X-Signature-SHA256": sig_header,
        "X-Timestamp": now_ts,
        "X-Event-ID": "evt_test_001",
        "Content-Type": "application/json",
    }

    res = api_client.post(
        "/api/v1/connectors/conn_stripe_001/webhooks",
        content=raw_bytes,
        headers=headers,
    )
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "ACCEPTED"
    assert data["is_duplicate"] is False


def test_connector_webhook_invalid_signature_rejected(api_client: Any):
    """Verify inbound webhook with tampered body or forged signature fails with 401."""
    now_ts = str(int(time.time()))
    secret = "whsec_wrong_secret"
    body_data = {"event": "invoice.paid", "amount_cents": 150000}
    raw_bytes = json.dumps(body_data).encode("utf-8")

    sig_header = _generate_signature(raw_bytes, secret, now_ts)

    headers = {
        "X-Signature-SHA256": sig_header,
        "X-Timestamp": now_ts,
        "X-Event-ID": "evt_test_002",
        "Content-Type": "application/json",
    }

    res = api_client.post(
        "/api/v1/connectors/conn_stripe_001/webhooks",
        content=raw_bytes,
        headers=headers,
    )
    assert res.status_code == 401
    assert "INVALID_SIGNATURE" in res.json()["detail"]["code"]


def test_connector_webhook_missing_signature_rejected(api_client: Any):
    """Verify inbound webhook lacking X-Signature-SHA256 header fails with 401."""
    body_data = {"event": "invoice.paid"}
    raw_bytes = json.dumps(body_data).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
    }

    res = api_client.post(
        "/api/v1/connectors/conn_stripe_001/webhooks",
        content=raw_bytes,
        headers=headers,
    )
    assert res.status_code == 401
    assert "MISSING_WEBHOOK_SIGNATURE" in res.json()["detail"]["code"]


def test_connector_webhook_empty_body_rejected(api_client: Any):
    """Verify empty webhook body fails with 400."""
    headers = {
        "X-Signature-SHA256": "dummy_sig",
        "Content-Type": "application/json",
    }

    res = api_client.post(
        "/api/v1/connectors/conn_stripe_001/webhooks",
        content=b"",
        headers=headers,
    )
    assert res.status_code == 400
    assert "EMPTY_PAYLOAD" in res.json()["detail"]["code"]
