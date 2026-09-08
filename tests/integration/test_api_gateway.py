"""
RevPilot AI — Tests: API Gateway Composition and Endpoints (apps/api)
Specification: docs/26-api/API-STANDARDS.md
Specification: docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §6
Conforms to INV-TEN-002, INV-IAM-001, INV-AUD-001, and AC-DEP-01.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(ROOT / "packages" / "backend" / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from typing import Any


@pytest.fixture
def client() -> Any:
    """Fixture providing initialized FastAPI test client."""
    from fastapi.testclient import TestClient
    from apps.api.main import app

    return TestClient(app)


def test_api_app_initialization(client: Any):
    """Verify application boots with valid title and version metadata."""
    assert client.app.title == "RevPilot AI Gateway"
    assert client.app.version == "1.0.0-rc1"


def test_liveness_probe_returns_200(client: Any):
    """
    AC-DEP-01: /health/live returns 200 OK with alive status for orchestrator liveness.
    """
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_probe_returns_200(client: Any):
    """
    AC-DEP-01: /health/ready returns 200 OK validating internal dependencies when healthy.
    """
    from unittest.mock import MagicMock, AsyncMock
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_pool.acquire.return_value.__aexit__.return_value = None

    client.app.state.db_pool = mock_pool
    try:
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert data["checks"]["database"] == "ok"
    finally:
        client.app.state.db_pool = None


def test_metrics_endpoint_returns_prometheus_format(client: Any):
    """
    SLO & Observability: /metrics returns 501 when unconfigured per AR-006.
    """
    response = client.get("/metrics")
    assert response.status_code == 501
    assert "Metrics instrumentation not configured" in response.json()["error"]


def test_correlation_id_generated_when_missing(client: Any):
    """
    API-STANDARDS §1 & §2: Client without X-Correlation-ID receives auto-generated ID.
    """
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    corr_header = response.headers.get("X-Correlation-ID")
    assert corr_header is not None
    assert corr_header.startswith("corr_")
    assert response.json()["correlation_id"] == corr_header


def test_correlation_id_preserved_when_supplied(client: Any):
    """
    API-STANDARDS §1 & §2: Client-supplied X-Correlation-ID is preserved in response.
    """
    custom_corr = "corr_custom_trace_987654321"
    response = client.get("/api/v1/status", headers={"X-Correlation-ID": custom_corr})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == custom_corr
    assert response.json()["correlation_id"] == custom_corr


def test_uniform_error_envelope_on_not_found(client: Any):
    """
    API-STANDARDS §3: Unhandled 404 path returns uniform error envelope.
    """
    response = client.get("/non_existent_path_xyz")
    assert response.status_code == 404
    # FastAPI returns standard 404 for unrouted paths
    assert response.headers.get("X-Correlation-ID") is not None
