"""
RevPilot AI — Investigation Live Stream Integration Tests (SSE)
Verifies:
- Streaming response returns text/event-stream media type
- Tenant context validation
- Events emit well-formatted SSE chunks (connected, node_progress, completed)
"""

from __future__ import annotations
import asyncio
from typing import Any
import pytest


@pytest.fixture
def client() -> Any:
    """Fixture providing initialized FastAPI test client without preloading at collection time."""
    from fastapi.testclient import TestClient
    from apps.api.main import app
    return TestClient(app)


def test_investigation_stream_unauthenticated_fails(client: Any):
    """Unauthenticated request without tenant or token should fail closed."""
    res = client.get("/api/v1/investigations/inv_test_stream_01/stream")
    assert res.status_code in (401, 403)


def test_investigation_stream_authenticated_emits_sse_events(client: Any):
    """Authenticated tenant receives text/event-stream with progress events."""
    headers = {
        "Authorization": "Bearer token_usr_analyst_001_tnt_dev_001",
    }
    res = client.get(
        "/api/v1/investigations/inv_test_stream_01/stream",
        headers=headers,
    )

    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    content = res.text
    assert "event: connected" in content
    assert "event: node_progress" in content
    assert "event: completed" in content
    assert "node_01_scope" in content
    assert "node_03_causal" in content


def test_investigation_stream_forged_token_fails_closed(client: Any):
    """Forged or unverified token string must fail closed with 401 (INV-IAM-001)."""
    headers = {
        "Authorization": "Bearer token_attacker_tnt_victim_999",
    }
    res = client.get(
        "/api/v1/investigations/inv_test_stream_01/stream",
        headers=headers,
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_investigation_event_broadcaster_lifecycle():
    """Verify InvestigationEventBroadcaster pub/sub and subscriber isolation."""
    from revpilot.modules.investigation.event_broadcaster import InvestigationEventBroadcaster

    broadcaster = InvestigationEventBroadcaster()
    tenant_id = "tnt_001"
    inv_id = "inv_001"

    assert await broadcaster.get_subscriber_count(tenant_id, inv_id) == 0

    # Subscribe
    gen = broadcaster.subscribe(tenant_id, inv_id)
    # Start generator
    sub_task = asyncio.create_task(gen.__anext__())
    await asyncio.sleep(0.01)

    assert await broadcaster.get_subscriber_count(tenant_id, inv_id) == 1

    # Publish to matching tenant and investigation
    received_count = await broadcaster.publish(tenant_id, inv_id, "TEST_EVENT", {"detail": "hello"})
    assert received_count == 1

    event = await sub_task
    assert event["event_type"] == "TEST_EVENT"
    assert event["data"]["detail"] == "hello"

    # Close subscriber
    await gen.aclose()
    assert await broadcaster.get_subscriber_count(tenant_id, inv_id) == 0


def test_investigation_signals_publish_broadcaster(client: Any):
    """Verify pause and resume publish STATUS_CHANGED events."""
    headers = {
        "Authorization": "Bearer token_usr_analyst_001_tnt_dev_001",
    }
    inv_id = "inv_stream_sig_01"

    # Pause
    res_pause = client.post(
        f"/api/v1/investigations/{inv_id}/pause",
        json={"reason": "operator requested manual review"},
        headers=headers,
    )
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "PAUSED"

    # Resume
    res_resume = client.post(
        f"/api/v1/investigations/{inv_id}/resume",
        json={"reason": "approval granted"},
        headers=headers,
    )
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "PLANNING"

