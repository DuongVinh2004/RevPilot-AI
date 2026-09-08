"""
RevPilot AI — Integration Tests for Inbound Webhook Signature Verification (TASK-AR-023)
Enforces INV-SEC-001 (HMAC verification) and INV-REL-001 (anti-replay defense).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import pytest


def _make_sig(raw_body: bytes, secret: str, ts_str: str) -> str:
    signed_payload = f"t={ts_str}.".encode("utf-8") + raw_body
    return hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()


@pytest.fixture
def webhook_client(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SIGNING_SECRET", "test_webhook_secret_key_32_bytes_len")
    from fastapi.testclient import TestClient
    from apps.api.main import app

    token = "token_usr_analyst_001_tnt_dev_001"
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    if hasattr(app.state, "_seen_webhook_events"):
        delattr(app.state, "_seen_webhook_events")
    yield client, "test_webhook_secret_key_32_bytes_len"


def test_valid_signature_returns_202(webhook_client):
    client, secret = webhook_client
    body = json.dumps({"event": "order.created", "amount": 100}).encode("utf-8")
    now_ts = str(int(time.time()))
    sig = _make_sig(body, secret, now_ts)

    headers = {
        "X-Signature-SHA256": sig,
        "X-Timestamp": now_ts,
        "X-Event-ID": "evt_valid_001",
        "Content-Type": "application/json",
    }
    res = client.post("/api/v1/connectors/conn_stripe/webhooks", content=body, headers=headers)
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "ACCEPTED"
    assert data["is_duplicate"] is False


def test_tampered_body_returns_401(webhook_client):
    client, secret = webhook_client
    original_body = json.dumps({"event": "order.created", "amount": 100}).encode("utf-8")
    now_ts = str(int(time.time()))
    sig = _make_sig(original_body, secret, now_ts)

    tampered_body = json.dumps({"event": "order.created", "amount": 999999}).encode("utf-8")
    headers = {
        "X-Signature-SHA256": sig,
        "X-Timestamp": now_ts,
        "X-Event-ID": "evt_tampered_001",
        "Content-Type": "application/json",
    }
    res = client.post("/api/v1/connectors/conn_stripe/webhooks", content=tampered_body, headers=headers)
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_SIGNATURE"


def test_wrong_secret_returns_401(webhook_client):
    client, _ = webhook_client
    body = json.dumps({"event": "order.created"}).encode("utf-8")
    now_ts = str(int(time.time()))
    wrong_sig = _make_sig(body, "wrong_secret_key", now_ts)

    headers = {
        "X-Signature-SHA256": wrong_sig,
        "X-Timestamp": now_ts,
        "X-Event-ID": "evt_wrong_secret_001",
        "Content-Type": "application/json",
    }
    res = client.post("/api/v1/connectors/conn_stripe/webhooks", content=body, headers=headers)
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_SIGNATURE"


def test_missing_signature_returns_401(webhook_client):
    client, _ = webhook_client
    body = json.dumps({"event": "order.created"}).encode("utf-8")
    now_ts = str(int(time.time()))

    headers = {
        "X-Timestamp": now_ts,
        "X-Event-ID": "evt_no_sig_001",
        "Content-Type": "application/json",
    }
    res = client.post("/api/v1/connectors/conn_stripe/webhooks", content=body, headers=headers)
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "MISSING_WEBHOOK_SIGNATURE"


def test_replay_duplicate_event_returns_409(webhook_client):
    client, secret = webhook_client
    body = json.dumps({"event": "order.created", "order_id": "ord_999"}).encode("utf-8")
    now_ts = str(int(time.time()))
    sig = _make_sig(body, secret, now_ts)
    event_id = "evt_dedup_unique_001"

    headers = {
        "X-Signature-SHA256": sig,
        "X-Timestamp": now_ts,
        "X-Event-ID": event_id,
        "Content-Type": "application/json",
    }
    # First delivery -> 202
    res1 = client.post("/api/v1/connectors/conn_stripe/webhooks", content=body, headers=headers)
    assert res1.status_code == 202

    # Second delivery with identical event_id -> 409 DUPLICATE_WEBHOOK_EVENT
    res2 = client.post("/api/v1/connectors/conn_stripe/webhooks", content=body, headers=headers)
    assert res2.status_code == 409
    assert res2.json()["detail"]["code"] == "DUPLICATE_WEBHOOK_EVENT"


def test_timestamp_skew_exceeding_window_returns_401(webhook_client):
    client, secret = webhook_client
    body = json.dumps({"event": "order.created"}).encode("utf-8")
    # Skewed timestamp 600s in past (> 300s window)
    stale_ts = str(int(time.time()) - 600)
    sig = _make_sig(body, secret, stale_ts)

    headers = {
        "X-Signature-SHA256": sig,
        "X-Timestamp": stale_ts,
        "X-Event-ID": "evt_skew_001",
        "Content-Type": "application/json",
    }
    res = client.post("/api/v1/connectors/conn_stripe/webhooks", content=body, headers=headers)
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "TIMESTAMP_SKEW"
