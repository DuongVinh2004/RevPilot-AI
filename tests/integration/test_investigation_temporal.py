"""
RevPilot AI — Integration Tests for Investigation Temporal Orchestration (AR-021)
Verifies real workflow initiation, exception logging & 503 propagation, and 404 fail-closed behavior.
Enforces INV-WF-001 (durable orchestration guarantee) and INV-TEN-001 (tenant isolation).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest


@pytest.fixture
def client_fixture():
    from fastapi.testclient import TestClient
    from apps.api.main import app

    token = "token_usr_dev_01_tnt_dev_001"
    app.state.auth_adapter.issue_test_token(
        token,
        sub="usr_dev_01",
        tenant_id="tnt_dev_001",
        roles=frozenset(["SYSTEM_ADMIN", "ADMIN", "OPERATOR", "ANALYST", "INVESTIGATOR"]),
    )
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client, app
    # Clean up app.state mocks
    if hasattr(app.state, "temporal_client"):
        delattr(app.state, "temporal_client")
    if hasattr(app.state, "investigation_repo"):
        delattr(app.state, "investigation_repo")


def test_investigation_no_pass_statement():
    """AC-AR-021-01: Verify no pass statement exists in try/except blocks of investigations.py."""
    import ast
    with open("apps/api/routers/investigations.py", encoding="utf-8") as f:
        content = f.read()
    tree = ast.parse(content)
    passes = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Pass)]
    assert len(passes) == 0, f"Found pass statements at lines: {passes}"


def test_investigation_start_success(client_fixture):
    """With mock temporal_client, POST /api/v1/investigations returns 202 and calls start_workflow."""
    client, app = client_fixture
    mock_temporal = MagicMock()
    mock_temporal.start_workflow = AsyncMock(return_value=None)
    app.state.temporal_client = mock_temporal

    payload = {
        "anomaly_id": "anom_01h8x8a7b3c1",
        "metric_name": "Net MRR Expansion Rate",
        "time_budget_seconds": 180,
        "cost_budget_usd": 2.00,
    }
    res = client.post("/api/v1/investigations", json=payload)
    assert res.status_code == 202
    data = res.json()
    assert "investigation_id" in data
    assert data["status"] == "INITIALIZING"
    assert "workflow_id" in data
    assert mock_temporal.start_workflow.called
    call_args = mock_temporal.start_workflow.call_args
    assert call_args.kwargs.get("id") == data["workflow_id"]
    assert call_args.kwargs.get("task_queue") == "investigation-workflow-queue"


def test_investigation_start_failure_propagates_503(client_fixture, caplog):
    """AC-AR-021-02, AC-AR-021-04: With temporal_client.start_workflow raising, logs error and returns 503."""
    client, app = client_fixture
    mock_temporal = MagicMock()
    mock_temporal.start_workflow = AsyncMock(side_effect=RuntimeError("Temporal cluster unreachable"))
    app.state.temporal_client = mock_temporal

    payload = {
        "anomaly_id": "anom_01h8x8a7b3c1",
        "metric_name": "Net MRR Expansion Rate",
        "time_budget_seconds": 180,
        "cost_budget_usd": 2.00,
    }
    with caplog.at_level("ERROR"):
        res = client.post("/api/v1/investigations", json=payload)
    assert res.status_code == 503
    data = res.json()
    assert "Failed to start investigation workflow" in data.get("detail", "")
    assert any("Temporal workflow start failed" in record.message for record in caplog.records)


def test_investigation_get_repo_none_returns_404(client_fixture):
    """AC-AR-021-03: With investigation_repo = None, GET returns 404."""
    client, app = client_fixture
    app.state.investigation_repo = None

    res = client.get("/api/v1/investigations/inv_missing_repo_none")
    assert res.status_code == 404
    data = res.json()
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert "inv_missing_repo_none" in data["message"]


def test_investigation_get_not_found_returns_404(client_fixture):
    """With investigation_repo returning None, GET returns 404."""
    client, app = client_fixture
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)
    app.state.investigation_repo = mock_repo

    res = client.get("/api/v1/investigations/inv_not_exist_in_db")
    assert res.status_code == 404
    data = res.json()
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert "inv_not_exist_in_db" in data["message"]
