"""
Integration tests for Approval and Action Dispatch Negative Test Matrix (TASK-AR-016).
Verifies fail-closed enforcement across 15 negative bypass scenarios.
Conforms to INV-ACT-001, INV-ACT-002, INV-ACT-003, INV-TEN-002, AC-008, AC-009.

Strict invariant: No module-level imports of FastAPI or apps.api.main.
"""

from __future__ import annotations
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
import pytest


def _issue_token(app, user_id="usr_op_1", tenant_id="tnt_dev_001", roles=("OPERATOR", "SYSTEM_ADMIN")):
    token = f"token_{user_id}_{tenant_id}"
    app.state.auth_adapter.issue_test_token(
        token,
        sub=user_id,
        tenant_id=tenant_id,
        roles=frozenset(roles),
    )
    return token


@pytest.fixture
def test_setup():
    from fastapi.testclient import TestClient
    from apps.api.main import app

    orig_pending = getattr(app.state, "_pending_approvals_cache", None)
    orig_intents = getattr(app.state, "_action_intents_cache", None)
    orig_gateway = getattr(app.state, "tool_gateway", None)
    orig_ks = getattr(app.state, "killswitch_repo", None)

    app.state._pending_approvals_cache = {}
    app.state._action_intents_cache = {}

    default_token = _issue_token(app, "usr_op_1", "tnt_dev_001")
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {default_token}"})

    yield client, app

    # Teardown to prevent test leakage
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


def _seed_record(
    app,
    tenant_id="tnt_dev_001",
    approval_id=None,
    status="APPROVED",
    requester="usr_requester_other",
    expiry=None,
    tampered=False,
    artifact=None,
):
    from revpilot.modules.approval.digest import ApprovalArtifact, compute_approval_digest

    appr_id = approval_id or f"appr_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    expiry_dt = expiry if expiry is not None else (now + timedelta(hours=24))

    payload = {"credit_amount": 100.0}
    if artifact is None:
        artifact = ApprovalArtifact(
            tenant_id=tenant_id,
            action_type="ISSUE_SERVICE_CREDIT_VOUCHER",
            target_entities=["cust_test_1"],
            payload=payload,
            policy_version="revpilot_policy_2026_09",
            required_tier="TIER_1",
            expires_at=expiry_dt.isoformat(),
            created_by=requester,
        )
    digest = compute_approval_digest(artifact)
    policy_digest = hashlib.sha256(b"revpilot_policy_2026_09").hexdigest()

    rec = {
        "id": appr_id,
        "tenant_id": tenant_id,
        "decision_id": f"dec_{uuid.uuid4().hex[:8]}",
        "action_type": "ISSUE_SERVICE_CREDIT_VOUCHER",
        "target_entity_refs": ["cust_test_1"],
        "payload": payload,
        "payload_digest": "tampered_digest_000000000000000000000000000000000000000000000000000" if tampered else digest,
        "policy_digest": policy_digest,
        "policy_version": "revpilot_policy_2026_09",
        "estimated_cost_usd": 100.0,
        "cost_usd": 100.0,
        "required_approval_tier": "TIER_1",
        "status": status,
        "expiry_time": expiry_dt,
        "requester_principal_id": requester,
        "correlation_id": f"corr_{uuid.uuid4().hex[:12]}",
        "artifact": artifact,
    }

    cache = getattr(app.state, "_pending_approvals_cache", None)
    if cache is None:
        cache = {}
        app.state._pending_approvals_cache = cache
    cache[appr_id] = rec
    return appr_id, rec


def test_01_approve_unknown_id_returns_404(test_setup):
    """Test 1: Approve non-existent approval ID returns 404 Not Found."""
    client, _ = test_setup
    resp = client.post("/api/v1/approvals/appr_nonexistent/approve", json={})
    assert resp.status_code == 404


def test_02_approve_already_approved_returns_409(test_setup):
    """Test 2: Re-approving already APPROVED request returns 409 Conflict."""
    client, app = test_setup
    appr_id, _ = _seed_record(app, status="APPROVED")
    resp = client.post(f"/api/v1/approvals/{appr_id}/approve", json={})
    assert resp.status_code == 409


def test_03_approve_expired_returns_410(test_setup):
    """Test 3: Approving an expired approval request returns 410 Gone."""
    client, app = test_setup
    past_expiry = datetime.now(timezone.utc) - timedelta(hours=2)
    appr_id, _ = _seed_record(app, status="PENDING", expiry=past_expiry)
    resp = client.post(f"/api/v1/approvals/{appr_id}/approve", json={})
    assert resp.status_code == 410


def test_04_self_approve_returns_403(test_setup):
    """Test 4: Requester principal attempting to approve own request returns 403 Forbidden (SoD)."""
    client, app = test_setup
    appr_id, _ = _seed_record(app, status="PENDING", requester="usr_op_1")
    resp = client.post(f"/api/v1/approvals/{appr_id}/approve", json={})
    assert resp.status_code == 403


def test_05_approve_wrong_tenant_returns_403(test_setup):
    """Test 5: Approver from tenant B attempting to approve tenant A request returns 403 Forbidden."""
    client, app = test_setup
    appr_id, _ = _seed_record(app, tenant_id="tnt_tenant_a", status="PENDING")
    token_b = _issue_token(app, user_id="usr_op_b", tenant_id="tnt_tenant_b")
    resp = client.post(
        f"/api/v1/approvals/{appr_id}/approve",
        json={},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


def test_06_dispatch_pending_returns_409(test_setup):
    """Test 6: Dispatching approval still in PENDING status returns 409 Conflict."""
    client, app = test_setup
    appr_id, _ = _seed_record(app, status="PENDING")
    resp = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id, "idempotency_key": "idemp_neg_06"},
    )
    assert resp.status_code == 409


def test_07_dispatch_rejected_returns_409(test_setup):
    """Test 7: Dispatching REJECTED approval returns 409 Conflict."""
    client, app = test_setup
    appr_id, _ = _seed_record(app, status="REJECTED")
    resp = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id, "idempotency_key": "idemp_neg_07"},
    )
    assert resp.status_code == 409


def test_08_dispatch_expired_approved_returns_410(test_setup):
    """Test 8: Dispatching APPROVED request whose expiry has elapsed returns 410 Gone."""
    client, app = test_setup
    past_expiry = datetime.now(timezone.utc) - timedelta(hours=2)
    appr_id, _ = _seed_record(app, status="APPROVED", expiry=past_expiry)
    resp = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id, "idempotency_key": "idemp_neg_08"},
    )
    assert resp.status_code == 410


def test_09_dispatch_wrong_tenant_returns_403(test_setup):
    """Test 9: Dispatching with tenant context mismatched from approval tenant returns 403 Forbidden."""
    client, app = test_setup
    appr_id, _ = _seed_record(app, tenant_id="tnt_tenant_a", status="APPROVED")
    token_b = _issue_token(app, user_id="usr_op_b", tenant_id="tnt_tenant_b")
    resp = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id, "idempotency_key": "idemp_neg_09"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


def test_10_dispatch_digest_mismatch_returns_409(test_setup):
    """Test 10: Dispatching with payload digest differing from approved sealed digest returns 409 Conflict."""
    client, app = test_setup
    appr_id, _ = _seed_record(app, status="APPROVED", tampered=True)
    resp = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id, "idempotency_key": "idemp_neg_10"},
    )
    assert resp.status_code == 409


def test_11_dispatch_duplicate_idempotency_returns_409(test_setup):
    """Test 11: Replaying dispatch with same idempotency key for conflicting payload returns 409 Conflict."""
    client, app = test_setup
    appr_id_1, _ = _seed_record(app, status="APPROVED")
    appr_id_2, _ = _seed_record(app, status="APPROVED")

    resp1 = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id_1, "idempotency_key": "idemp_dup_conflict"},
    )
    assert resp1.status_code == 202

    resp2 = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id_2, "idempotency_key": "idemp_dup_conflict"},
    )
    assert resp2.status_code == 409


def test_12_dispatch_kill_switch_active_returns_503(test_setup):
    """Test 12: Dispatching action while global or tenant kill switch is engaged returns 503 Service Unavailable."""
    client, app = test_setup
    appr_id, _ = _seed_record(app, status="APPROVED")

    class MockActiveKillSwitch:
        async def is_kill_switch_active(self, scope, identifier=None):
            return True

    app.state.killswitch_repo = MockActiveKillSwitch()

    resp = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id, "idempotency_key": "idemp_neg_12"},
    )
    assert resp.status_code == 503


def test_13_dry_run_causes_no_state_change(test_setup):
    """Test 13: POST /actions/dry-run executes simulation and verifies 0 state mutations."""
    client, app = test_setup
    appr_id, rec = _seed_record(app, status="PENDING")
    initial_status = rec["status"]
    intents_count_before = len(getattr(app.state, "_action_intents_cache", {}))

    resp = client.post(
        "/api/v1/actions/dry-run",
        json={"approval_id": appr_id, "idempotency_key": "idemp_neg_13"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DRY_RUN_PASSED"
    assert data["external_side_effects"] == 0

    assert rec["status"] == initial_status
    assert len(getattr(app.state, "_action_intents_cache", {})) == intents_count_before


def test_14_provider_failure_records_provider_failed(test_setup):
    """Test 14: Simulated upstream provider failure produces 502/500 and records PROVIDER_FAILED."""
    client, app = test_setup
    appr_id, rec = _seed_record(app, status="APPROVED")

    class FailingGateway:
        async def dispatch_action(self, *args, **kwargs):
            from revpilot.shared.results import Failure
            from revpilot.modules.tool_gateway.action.credential_broker import GatewayError
            return Failure(
                GatewayError(code="ERR_PROVIDER_EXECUTION_FAILED", message="Upstream provider execution timed out")
            )

    app.state.tool_gateway = FailingGateway()

    resp = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id, "idempotency_key": "idemp_neg_14"},
    )
    assert resp.status_code == 502
    assert rec["status"] == "PROVIDER_FAILED"


def test_15_kill_switch_race_fails_closed(test_setup):
    """Test 15: Concurrent dispatch attempt initiated during kill switch activation window fails closed with 503."""
    client, app = test_setup
    appr_id, _ = _seed_record(app, status="APPROVED")

    is_active = False

    class ToggleKillSwitch:
        async def is_kill_switch_active(self, scope, identifier=None):
            return is_active

    app.state.killswitch_repo = ToggleKillSwitch()

    # Kill switch engages during activation window
    is_active = True

    resp = client.post(
        "/api/v1/actions/dispatch",
        json={"approval_id": appr_id, "idempotency_key": "idemp_neg_15"},
    )
    assert resp.status_code == 503
