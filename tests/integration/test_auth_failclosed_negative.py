"""
RevPilot AI — Integration Test: Authentication Fail-Closed Negative Matrix
Conforms to:
- TASK-AR-005
- docs/14-iam/IAM-SPEC.md#authentication-boundary
- docs/14-iam/IAM-SPEC.md#negative-test-matrix
- INV-IAM-001, INV-TEN-002, INV-SEC-001
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Generator
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(ROOT / "packages" / "backend" / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def client() -> Generator[Any, None, None]:
    """Fixture providing TestClient with deferred imports to protect contract tests."""
    from fastapi.testclient import TestClient
    from apps.api.main import app

    c = TestClient(app)
    yield c


def test_empty_token_returns_401(client: Any) -> None:
    """AC-AR-005-02: Missing Authorization header must return 401."""
    resp = client.get("/api/v1/auth/mfa/status")
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTHENTICATION_ERROR"


def test_random_token_returns_401(client: Any) -> None:
    """AC-AR-005-02: Random garbage token must return 401."""
    resp = client.get(
        "/api/v1/auth/mfa/status",
        headers={"Authorization": "Bearer random_garbage_xyz"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTHENTICATION_ERROR"


def test_malformed_token_returns_401(client: Any) -> None:
    """AC-AR-005-02: Malformed token format must return 401."""
    resp = client.get(
        "/api/v1/auth/mfa/status",
        headers={"Authorization": "Bearer not-a-valid-token-format"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTHENTICATION_ERROR"


def test_expired_token_returns_401(client: Any) -> None:
    """AC-AR-005-02: Token with expired claims must return 401."""
    from revpilot.shared.errors import AuthenticationError

    adapter = client.app.state.auth_adapter
    orig_verify = adapter.verify_token

    def mock_verify(token: str, **kwargs: Any) -> Any:
        if token == "tok_expired_999":
            raise AuthenticationError("Token has expired")
        return orig_verify(token, **kwargs)

    adapter.verify_token = mock_verify
    try:
        resp = client.get(
            "/api/v1/auth/mfa/status",
            headers={"Authorization": "Bearer tok_expired_999"},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTHENTICATION_ERROR"
    finally:
        adapter.verify_token = orig_verify


def test_revoked_token_returns_401(client: Any) -> None:
    """AC-AR-005-02: Revoked session token must return 401."""
    adapter = client.app.state.auth_adapter
    tok, sess = adapter.issue_test_token(
        "tok_revoked_test_001", session_id="sess_revoked_test_001"
    )
    adapter.revoke_session("sess_revoked_test_001")

    resp = client.get(
        "/api/v1/auth/mfa/status",
        headers={"Authorization": "Bearer tok_revoked_test_001"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTHENTICATION_ERROR"


def test_no_adapter_valid_looking_token_returns_401(client: Any) -> None:
    """AC-AR-005-02: auth_adapter=None with structured token must return 401 (NOT 200)."""
    original_adapter = client.app.state.auth_adapter
    client.app.state.auth_adapter = None
    try:
        resp = client.get(
            "/api/v1/auth/mfa/status",
            headers={"Authorization": "Bearer usr_analyst_001_tnt_dev_001"},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTHENTICATION_ERROR"
        assert resp.json()["details"]["error"] == "auth_adapter_unavailable"
    finally:
        client.app.state.auth_adapter = original_adapter


def test_dev_principal_header_ignored_in_production(client: Any, monkeypatch: Any) -> None:
    """AC-AR-005-02: X-Dev-Principal header ignored in production mode."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    resp = client.get(
        "/api/v1/auth/mfa/status",
        headers={"X-Dev-Principal": "usr_dev_001"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTHENTICATION_ERROR"


def test_dev_tenant_header_ignored_in_production(client: Any, monkeypatch: Any) -> None:
    """AC-AR-005-02: X-Dev-Tenant header ignored in production mode."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    resp = client.get(
        "/api/v1/auth/mfa/status",
        headers={"X-Dev-Tenant": "tnt_dev_001"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTHENTICATION_ERROR"
