"""
RevPilot AI — Integration Tests for Domain API Routes (Track 3)
Verifies all newly wired domain routers (Analytics, Investigations, Approvals, Causal, Decisions).
"""

from __future__ import annotations

import pytest


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient
    from apps.api.main import app

    app.state.allow_dev_auth = True
    return TestClient(app)


def test_status_endpoint(api_client):
    res = api_client.get("/api/v1/status")
    assert res.status_code == 200
    assert res.json()["status"] == "OPERATIONAL"


def test_list_anomalies_endpoint(api_client):
    headers = {"X-Dev-Principal": "usr_dev_01", "X-Dev-Tenant": "tnt_dev_001"}
    res = api_client.get("/api/v1/analytics/anomalies", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["count"] >= 1


def test_detect_anomalies_endpoint(api_client):
    headers = {"X-Dev-Principal": "usr_dev_01", "X-Dev-Tenant": "tnt_dev_001"}
    payload = {
        "metric_id": "METRIC_NET_MRR_EXPANSION",
        "observation_window_start": "2026-09-01T00:00:00Z",
        "observation_window_end": "2026-09-05T00:00:00Z",
    }
    res = api_client.post("/api/v1/analytics/anomalies/detect", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["is_anomaly"] is True


def test_list_and_approve_approval_endpoint(api_client):
    headers = {"X-Dev-Principal": "usr_dev_01", "X-Dev-Tenant": "tnt_dev_001"}
    # 1. List
    res = api_client.get("/api/v1/approvals", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1

    # 2. Approve
    appr_id = items[0]["id"]
    res_appr = api_client.post(
        f"/api/v1/approvals/{appr_id}/approve",
        json={"expected_payload_digest": "dummy_digest"},
        headers=headers,
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "APPROVED"


def test_kill_switch_endpoint(api_client):
    headers = {"X-Dev-Principal": "usr_dev_01", "X-Dev-Tenant": "tnt_dev_001"}
    payload = {"scope": "GLOBAL", "reason": "Integration drill test"}
    res = api_client.post("/api/v1/actions/kill-switch", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "KILL_SWITCH_ENGAGED"
    assert data["propagation_latency_ms"] < 500


def test_create_investigation_endpoint(api_client):
    headers = {"X-Dev-Principal": "usr_dev_01", "X-Dev-Tenant": "tnt_dev_001"}
    payload = {
        "anomaly_id": "anom_01h8x8a7b3c1",
        "metric_name": "Net MRR Expansion Rate",
        "time_budget_seconds": 180,
    }
    res = api_client.post("/api/v1/investigations", json=payload, headers=headers)
    assert res.status_code == 202
    data = res.json()
    assert "investigation_id" in data
    assert data["status"] == "INITIALIZING"


def test_claim_verification_endpoint(api_client):
    headers = {"X-Dev-Principal": "usr_dev_01", "X-Dev-Tenant": "tnt_dev_001"}
    payload = {
        "statement": "Carrier SLA penalty increased churn by 14%",
        "evidence_references": ["evd_001", "evd_002"],
    }
    res = api_client.post("/api/v1/claims/verify", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["verifier_status"] == "VERIFIED"
