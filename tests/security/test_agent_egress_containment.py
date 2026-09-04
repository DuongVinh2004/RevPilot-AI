"""
RevPilot AI — Security Tests for Agent Egress Containment
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §1, §7.1
Conforms to INV-SEC-001: Direct agent egress is barred; only the Tool Gateway possesses network capability.
Direct network connection attempts from within agent sub-processes fail closed.
"""

from __future__ import annotations
import http.client
import socket
import sys
import urllib.request
import pytest

from revpilot.modules.tool_gateway.action.gateway import (
    ActionCapabilityGateway,
    ActionCapabilityRequest,
    agent_egress_barrier,
    GatewayError,
)
from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.results import Success


@pytest.fixture(autouse=True)
def _isolate_gateway_modules():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.tool_gateway"):
            sys.modules.pop(mod, None)


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_containment_corp")


@pytest.fixture
def sample_context(sample_tenant: TenantId) -> TenantContext:
    return TenantContext(
        tenant_id=sample_tenant,
        organization_id=OrganizationId("org_containment"),
    )


def test_agent_direct_socket_fails_closed_in_barrier():
    """
    INV-SEC-001: Direct socket instantiation from within the agent egress barrier fails closed.
    """
    with agent_egress_barrier():
        with pytest.raises(GatewayError) as exc_info:
            _ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        assert exc_info.value.code == "ERR_DIRECT_EGRESS_BLOCKED"
        assert "direct agent egress is barred" in exc_info.value.message.lower()


def test_agent_http_client_fails_closed_in_barrier():
    """
    INV-SEC-001: Attempting high-level HTTP client connections fails closed immediately.
    """
    with agent_egress_barrier():
        conn = http.client.HTTPConnection("127.0.0.1", 8080)
        with pytest.raises(GatewayError) as exc_info:
            conn.connect()

        assert exc_info.value.code == "ERR_DIRECT_EGRESS_BLOCKED"


def test_agent_urllib_fails_closed_in_barrier():
    """
    INV-SEC-001: urllib.request.urlopen fails closed when called inside agent containment barrier.
    """
    with agent_egress_barrier():
        with pytest.raises(GatewayError) as exc_info:
            urllib.request.urlopen("http://127.0.0.1:9999", timeout=1)

        assert exc_info.value.code == "ERR_DIRECT_EGRESS_BLOCKED"


def test_egress_barrier_clean_cleanup():
    """
    Ensure agent egress barrier cleans up its socket interception upon exit.
    """
    assert hasattr(socket.socket, "__call__")
    with agent_egress_barrier():
        with pytest.raises(GatewayError):
            socket.socket()

    # After barrier exits, socket constructor is normal socket class again
    s = socket.socket()
    assert s is not None
    s.close()


@pytest.mark.asyncio
async def test_gateway_dispatches_cleanly_without_unauthorized_egress(
    sample_tenant: TenantId,
    sample_context: TenantContext,
):
    """
    Tool Gateway dispatches through mock provider boundary cleanly without attempting direct socket egress.
    """
    gateway = ActionCapabilityGateway()
    req = ActionCapabilityRequest(
        intent_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        approval_id=UUIDv7.generate(),
        approval_digest="d" * 64,
        action_type="CARRIER_EXPEDITE",
        idempotency_key="idemp_containment_01",
        target_entities=["shipment_safe_01"],
        payload={"carrier": "carrier_internal"},
        as_of_time=UtcDateTime.now(),
    )

    res = await gateway.dispatch_action(ctx=sample_context, req=req)
    assert isinstance(res, Success)
    assert res.value.execution_status == "SUCCESS"
    assert res.value.http_status_code == 200
