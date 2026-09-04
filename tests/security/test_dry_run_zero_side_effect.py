"""
RevPilot AI — Security Tests for Dry-Run Zero Side Effects
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 4, §2 Stage 6
Conforms to INV-ACT-001, AC-009: Dry-run simulation physically makes 0 external network requests
and causes 0 side-effect mutations.
"""

from __future__ import annotations
from decimal import Decimal
import socket
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext


@pytest.fixture(autouse=True)
def _isolate_action_module():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.action") or mod.startswith("revpilot.modules.approval"):
            sys.modules.pop(mod, None)


@pytest.fixture
def action_module():
    import revpilot.modules.action as mod
    return mod


@pytest.fixture
def approval_module():
    import revpilot.modules.approval as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_corp")


@pytest.fixture
def sample_context(sample_tenant) -> TenantContext:
    return TenantContext(
        tenant_id=sample_tenant,
        organization_id=OrganizationId("org_sample"),
    )


@pytest.mark.asyncio
async def test_dry_run_strictly_zero_socket_egress(
    action_module, approval_module, sample_tenant, sample_context, monkeypatch
):
    """
    Ensure dry-run simulation never opens network sockets or makes outbound HTTP calls.
    Attempts to open a socket during dry run raise an error immediately.
    """
    intent_repo = action_module.InMemoryActionIntentRepository()
    ledger_repo = action_module.InMemoryActionLedgerRepository()
    service = action_module.ActionLedgerService(intent_repo, ledger_repo)

    approval_repo = approval_module.InMemoryApprovalRepository()
    approval_svc = approval_module.ApprovalService(approval_repo)

    # Monkeypatch socket.socket to detect any attempted network egress
    def forbidden_socket(*args, **kwargs):
        raise AssertionError("Security violation: Socket opened during dry-run simulation (INV-ACT-001)")

    monkeypatch.setattr(socket, "socket", forbidden_socket)

    app_rec = await approval_svc.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_DISPATCH",
        target_customer_id="cust_001",
        target_entity_refs=["ship_01"],
        action_payload={"carrier": "carrier_x"},
        estimated_cost_usd=Decimal("100.00"),
    )

    intent = await service.create_intent(
        ctx=sample_context,
        approval=app_rec,
        idempotency_key="idemp_zero_egress_test",
        classification=action_module.ActionClassification.REVERSIBLE,
        is_dry_run=True,
    )

    # Simulation must complete cleanly with 0 sockets opened
    res = await service.execute_dry_run(
        ctx=sample_context,
        intent=intent,
        payload={"carrier": "carrier_x"},
        cost_usd=Decimal("100.00"),
        targets=["ship_01"],
    )

    assert res.zero_side_effect_verified is True
    assert res.is_dry_run is True
