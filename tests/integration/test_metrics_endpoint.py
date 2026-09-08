"""
RevPilot AI — Integration Tests for Dynamic Prometheus Metrics Endpoint (TASK-AR-025)
Enforces INV-REL-001 (observability integrity), AC-014 (anti-fabrication), and AC-AR-025-01..03.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def metrics_client(monkeypatch):
    monkeypatch.setenv("METRICS_ENABLED", "true")
    from fastapi.testclient import TestClient
    from apps.api.main import app

    app.state.metrics_enabled = True
    app.state.request_count_200 = 0
    client = TestClient(app)
    yield client
    app.state.metrics_enabled = None


def test_metrics_endpoint_status_and_content_type(metrics_client):
    """Verifies HTTP 200 and content-type text/plain; version=0.0.4."""
    res = metrics_client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    assert "version=0.0.4" in res.headers["content-type"]
    assert "revpilot_up 1" in res.text


def test_metrics_counter_increments_after_requests(metrics_client):
    """AC-AR-025-01: Sending 5 requests to /health/live increments status=200 counter >= 5."""
    initial_res = metrics_client.get("/metrics")
    assert initial_res.status_code == 200

    # Send 5 requests to live health probe
    for _ in range(5):
        resp = metrics_client.get("/health/live")
        assert resp.status_code == 200

    metrics_res = metrics_client.get("/metrics")
    assert metrics_res.status_code == 200

    found_counter = False
    for line in metrics_res.text.splitlines():
        if line.startswith('revpilot_http_requests_total{status="200"}'):
            count = int(line.split()[-1])
            assert count >= 5
            found_counter = True
            break
    assert found_counter, "Counter revpilot_http_requests_total{status='200'} not found in output"


def test_metrics_has_no_hardcoded_zero_counter(metrics_client):
    """AC-AR-025-02: Output contains dynamic non-zero count after traffic, no static zero."""
    for _ in range(3):
        metrics_client.get("/health/live")

    res = metrics_client.get("/metrics")
    assert res.status_code == 200
    # Must not contain hardcoded zero
    assert 'revpilot_http_requests_total{status="200"} 0' not in res.text
