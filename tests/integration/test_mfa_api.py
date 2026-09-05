"""
RevPilot AI — Integration Tests for MFA API Endpoints
Specification: docs/14-iam/IAM-SPEC.md §8, ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md
"""

from __future__ import annotations
import time
from typing import Any
import pytest

from revpilot.modules.identity.mfa import TotpManager


@pytest.fixture
def client() -> Any:
    """Fixture providing initialized FastAPI test client without preloading at collection time."""
    from fastapi.testclient import TestClient
    from apps.api.main import app
    return TestClient(app)


def test_mfa_api_endpoints(client: Any):
    headers = {"Authorization": "Bearer token_usr_analyst_001_tnt_dev_001"}

    # 1. Initial MFA status
    resp = client.get("/api/v1/auth/mfa/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mfa_enabled"] is False

    # 2. Setup
    setup_resp = client.post("/api/v1/auth/mfa/totp/setup", headers=headers)
    assert setup_resp.status_code == 200
    setup_data = setup_resp.json()
    secret = setup_data["secret"]
    assert "otpauth://totp" in setup_data["provisioning_uri"]

    # 3. Activate with valid code
    code = TotpManager.generate_code(secret)
    act_resp = client.post("/api/v1/auth/mfa/totp/activate", json={"code": code}, headers=headers)
    assert act_resp.status_code == 200
    act_data = act_resp.json()
    assert act_data["status"] == "ACTIVATED"
    recovery_codes = act_data["recovery_codes"]
    assert len(recovery_codes) == 8

    # 4. Verify step-up with code in new step
    time_future = time.time() + 35.0
    code_future = TotpManager.generate_code(secret, for_time=time_future)
    verify_resp = client.post("/api/v1/auth/mfa/totp/verify", json={"code": code_future}, headers=headers)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified"] is True

    # 5. Consume recovery code
    rec_resp = client.post("/api/v1/auth/mfa/recovery/consume", json={"code": recovery_codes[0]}, headers=headers)
    assert rec_resp.status_code == 200
    assert rec_resp.json()["verified"] is True
