"""
Integration tests for Action Dispatch and Tool Gateway binding (TASK-AR-014).
Conforms to INV-ACT-001, AC-008, AC-009, INV-SEC-001.
Enforces no module-level FastAPI/apps.api.main imports.
"""

from __future__ import annotations
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
import pytest


@pytest.fixture
def client_and_app():
    from fastapi.testclient import TestClient
    from apps.api.main import app

    orig_pending = getattr(app.state, "_pending_approvals_cache", None)
    orig_intents = getattr(app.state, "_action_intents_cache", None)
    orig_gateway = getattr(app.state, "tool_gateway", None)
    orig_ks = getattr(app.state, "killswitch_repo", None)

    app.state._pending_approvals_cache = {}
    app.state._action_intents_cache = {}

    token = "token_usr_op_tnt_dev_001"
    app.state.auth_adapter.issue_test_token(
        token,
        sub="usr_op_1",
        tenant_id="tnt_dev_001",
        roles=frozenset(["OPERATOR", "SYSTEM_ADMIN"]),
    )
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield client, app

    if orig_pending is not None:
        app.state._pending_approvals_cache = orig_pending
    elif hasattr(app.state, "_pending_approvals_cache"):
        delattr(app.state, "_pending_approvals_cache")

    if orig_intents is not None:
        app.state._action_intents_cache = orig_intents
    elif hasattr(app.state, "_action_intents_cache"):
        delattr(app.state, "_action_intents_cache")

    if orig_gateway is not None:
        app.state.tool_gateway = orig_gateway
    elif hasattr(app.state, "tool_gateway"):
        delattr(app.state, "tool_gateway")

    if orig_ks is not None:
        app.state.killswitch_repo = orig_ks
    elif hasattr(app.state, "killswitch_repo"):
        delattr(app.state, "killswitch_repo")


def _seed_record(app, tenant_id="tnt_dev_001", approval_id=None, status="APPROVED"):
    from revpilot.modules.approval.digest import ApprovalArtifact, compute_approval_digest

    appr_id = approval_id or f"appr_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=24)
    payload = {"credit_amount": 100.0}
    artifact = ApprovalArtifact(
        tenant_id=tenant_id,
        action_type="ISSUE_SERVICE_CREDIT_VOUCHER",
        target_entities=["cust_test_1"],
        payload=payload,
        policy_version="revpilot_policy_2026_09",
        required_tier="TIER_1",
        expires_at=expiry.isoformat(),
        created_by="usr_requester_other",
    )
    digest = compute_approval_digest(artifact)
    policy_digest = hashlib.sha256(b"revpilot_policy_2026_09").hexdigest()

    cache = getattr(app.state, "_pending_approvals_cache", None)
    if cache is None:
        cache = {}
        app.state._pending_approvals_cache = cache

    rec = {
        "id": appr_id,
        "tenant_id": tenant_id,
        "decision_id": f"dec_{uuid.uuid4().hex[:8]}",
        "action_type": "ISSUE_SERVICE_CREDIT_VOUCHER",
        "target_entity_refs": ["cust_test_1"],
        "payload": payload,
        "payload_digest": digest,
        "policy_digest": policy_digest,
        "policy_version": "revpilot_policy_2026_09",
        "estimated_cost_usd": 100.0,
        "required_approval_tier": "TIER_1",
        "status": status,
        "expiry_time": expiry,
        "requester_principal_id": "usr_requester_other",
        "approver_principal_id": "usr_op_1",
        "signed_at": now.isoformat(),
        "artifact": artifact,
    }
    cache[appr_id] = rec
    return rec


def test_01_gateway_dispatch_invoked_on_dispatch(client_and_app):
    """AC-AR-014-01 & AC-AR-014-05: Gateway dispatch invoked before returning EXECUTING."""
    client, app = client_and_app
    from revpilot.modules.tool_gateway.action.gateway import ActionCapabilityGateway

    real_gateway = ActionCapabilityGateway()
    mock_dispatch = AsyncMock(side_effect=real_gateway.dispatch_action)

    app.state.tool_gateway = real_gateway
    real_gateway.dispatch_action = mock_dispatch

    record = _seed_record(app, status="APPROVED")
    appr_id = record["id"]

    res = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id, "idempotency_key": f"key_{uuid.uuid4().hex[:8]}"},
    )

    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "EXECUTING"
    assert data["approval_id"] == appr_id
    assert "intent_id" in data
    assert mock_dispatch.await_count == 1
    assert record["status"] == "SUCCEEDED"


def test_02_kill_switch_engaged_returns_503(client_and_app):
    """AC-AR-014-02: Active kill switch returns HTTP 503."""
    client, app = client_and_app

    mock_ks = AsyncMock()
    mock_ks.is_kill_switch_active = AsyncMock(return_value=True)
    orig_ks = getattr(app.state, "killswitch_repo", None)
    app.state.killswitch_repo = mock_ks

    try:
        record = _seed_record(app, status="APPROVED")
        res = client.post(
            "/api/v1/actions/dispatch",
            json={"approval_id": record["id"], "idempotency_key": "key_ks_test"},
        )
        assert res.status_code == 503
        assert "kill switch" in res.json()["detail"].lower()
    finally:
        app.state.killswitch_repo = orig_ks


def test_03_duplicate_idempotency_key_handling(client_and_app):
    """AC-AR-014-03: Duplicate idempotency key returns existing result or 409 on conflict."""
    client, app = client_and_app

    rec1 = _seed_record(app, status="APPROVED")
    rec2 = _seed_record(app, status="APPROVED")

    shared_key = f"idem_key_{uuid.uuid4().hex[:8]}"

    # First dispatch
    res1 = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": rec1["id"], "idempotency_key": shared_key},
    )
    assert res1.status_code == 202
    data1 = res1.json()

    # Replay with same idempotency key and same approval_id -> returns existing result
    res2 = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": rec1["id"], "idempotency_key": shared_key},
    )
    assert res2.status_code == 202
    assert res2.json()["intent_id"] == data1["intent_id"]

    # Replay with same idempotency key but different approval_id -> 409 Conflict
    res3 = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": rec2["id"], "idempotency_key": shared_key},
    )
    assert res3.status_code == 409
    assert "idempotency conflict" in res3.json()["detail"].lower()


def test_04_gateway_failure_returns_502_and_sets_provider_failed(client_and_app):
    """AC-AR-014-04: Gateway failure sets approval state to PROVIDER_FAILED and returns HTTP 502."""
    client, app = client_and_app
    from revpilot.shared.results import Failure
    from revpilot.modules.tool_gateway.action.credential_broker import GatewayError
    from revpilot.modules.tool_gateway.action.gateway import ActionCapabilityGateway

    gw = ActionCapabilityGateway()
    gw.dispatch_action = AsyncMock(
        return_value=Failure(GatewayError(code="ERR_UPSTREAM_TIMEOUT", message="Connection timed out"))
    )
    app.state.tool_gateway = gw

    rec = _seed_record(app, status="APPROVED")
    res = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": rec["id"], "idempotency_key": f"key_fail_{uuid.uuid4().hex[:8]}"},
    )

    assert res.status_code == 502
    assert rec["status"] == "PROVIDER_FAILED"


def test_05_unapproved_or_missing_record_rejected(client_and_app):
    """Non-existent approval returns 404, non-APPROVED approval returns 409."""
    client, app = client_and_app

    # Missing record -> 404
    res_404 = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": "appr_does_not_exist", "idempotency_key": "k1"},
    )
    assert res_404.status_code == 404

    # Status PENDING -> 409
    rec_pending = _seed_record(app, status="PENDING")
    res_409 = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": rec_pending["id"], "idempotency_key": "k2"},
    )
    assert res_409.status_code == 409
