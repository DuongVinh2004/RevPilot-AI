"""
RevPilot AI — Integration Test: Readiness Probe and Metrics Endpoint
Conforms to:
- TASK-AR-006
- docs/22-operations/RUNBOOK.md#health-checks
- NFR-REL-001, INV-REL-001
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(ROOT / "packages" / "backend" / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def client() -> Generator[Any, None, None]:
    """Fixture providing TestClient with deferred imports."""
    from fastapi.testclient import TestClient
    from apps.api.main import app

    c = TestClient(app)
    yield c


def test_readiness_healthy(client: Any) -> None:
    """AC-AR-006-04: Mock pool+adapter present returns 200 ready."""
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_pool.acquire.return_value.__aexit__.return_value = None

    client.app.state.db_pool = mock_pool
    try:
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] == "ok"
        assert data["checks"]["auth"] == "ok"
    finally:
        client.app.state.db_pool = None


def test_readiness_no_pool(client: Any) -> None:
    """AC-AR-006-01: pool=None returns 503 not_ready."""
    client.app.state.db_pool = None
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["database"] == "degraded"


def test_readiness_pool_select_fails(client: Any) -> None:
    """AC-AR-006-04: pool.execute raises exception returns 503."""
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.execute.side_effect = RuntimeError("Connection dropped")
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_pool.acquire.return_value.__aexit__.return_value = None

    client.app.state.db_pool = mock_pool
    try:
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"] == "degraded"
    finally:
        client.app.state.db_pool = None


def test_readiness_no_auth_adapter(client: Any) -> None:
    """AC-AR-006-02: auth_adapter=None returns 503 not_ready."""
    original_adapter = client.app.state.auth_adapter
    client.app.state.auth_adapter = None
    try:
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["auth"] == "degraded"
    finally:
        client.app.state.auth_adapter = original_adapter


def test_metrics_not_hardcoded(client: Any) -> None:
    """AC-AR-006-03: /metrics does not return hardcoded static 201 0 counter."""
    resp = client.get("/metrics")
    forbidden = 'revpilot_http_requests_total{method="POST",path="/api/v1/anomalies/detect",status="201"} 0'
    assert forbidden not in resp.text
