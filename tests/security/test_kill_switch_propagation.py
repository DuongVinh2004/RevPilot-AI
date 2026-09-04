"""
RevPilot AI — Multi-Tier Kill Switch & Distributed Propagation Tests
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §5
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7.4
Conforms to INV-REL-001 (< 500ms propagation), INV-ACT-003, and TC-P06-019.
"""

from __future__ import annotations
import time
import pytest

from revpilot.modules.safety.killswitch.domain import (
    AgentOverrideForbiddenError,
    KillSwitchError,
    KillSwitchRecord,
    KillSwitchScope,
)
from revpilot.modules.safety.killswitch.service import (
    DistributedKillSwitchBus,
    KillSwitchService,
)
from revpilot.shared.identifiers import TenantId, UUIDv7


@pytest.fixture
def clean_bus() -> DistributedKillSwitchBus:
    """Isolated distributed bus instance for test isolation."""
    return DistributedKillSwitchBus()


@pytest.fixture
def service(clean_bus: DistributedKillSwitchBus) -> KillSwitchService:
    return KillSwitchService(bus=clean_bus)


@pytest.mark.asyncio
async def test_global_kill_switch_blocks_all_traffic(service: KillSwitchService) -> None:
    """
    Tier 1 Global Platform kill switch must immediately halt all tenant write actions.
    """
    t1 = TenantId("tnt_alpha")
    t2 = TenantId("tnt_beta")

    # Initial state: not blocked
    assert not await service.is_blocked(t1, "refund_issue", "stripe", None)
    assert not await service.is_blocked(t2, "inventory_adjust", "wms", None)

    # Activate global kill switch
    rec = await service.activate(
        scope=KillSwitchScope.GLOBAL,
        target_id=None,
        reason="Critical security alert: unauthorized token leak detected",
        principal="usr_secops_admin",
    )
    assert rec.is_active
    assert rec.scope == KillSwitchScope.GLOBAL

    # All traffic across all tenants must fail closed
    assert await service.is_blocked(t1, "refund_issue", "stripe", None)
    assert await service.is_blocked(t2, "inventory_adjust", "wms", None)

    # Deactivate restores normal flow
    deactivated = await service.deactivate(rec.switch_id, "Threat contained", "usr_secops_admin")
    assert not deactivated.is_active
    assert not await service.is_blocked(t1, "refund_issue", "stripe", None)


@pytest.mark.asyncio
async def test_tenant_kill_switch_isolation(service: KillSwitchService) -> None:
    """
    Tier 2 Tenant-level kill switch isolates target tenant without affecting others.
    """
    t_target = TenantId("tnt_compromised")
    t_other = TenantId("tnt_healthy")

    rec = await service.activate(
        scope=KillSwitchScope.TENANT,
        target_id=str(t_target),
        reason="Suspicious automated billing activity detected on tenant",
        principal="usr_compliance_lead",
    )
    assert rec.is_active

    # Target tenant is blocked; other tenant remains untouched
    assert await service.is_blocked(t_target, "action_refund", "provider_1", None)
    assert not await service.is_blocked(t_other, "action_refund", "provider_1", None)


@pytest.mark.asyncio
async def test_capability_kill_switch(service: KillSwitchService) -> None:
    """
    Tier 3 Capability/tool switch blocks only matching action type across all tenants.
    """
    t1 = TenantId("tnt_tenant_one")
    t2 = TenantId("tnt_tenant_two")

    await service.activate(
        scope=KillSwitchScope.CAPABILITY,
        target_id="courier_priority_book",
        reason="Courier API rate limit exhaustion",
        principal="usr_ops_lead",
    )

    # Blocked for matching capability
    assert await service.is_blocked(t1, "courier_priority_book", "dhl", None)
    assert await service.is_blocked(t2, "courier_priority_book", "fedex", None)

    # Unblocked for other capabilities
    assert not await service.is_blocked(t1, "inventory_reserve", "dhl", None)


@pytest.mark.asyncio
async def test_provider_kill_switch(service: KillSwitchService) -> None:
    """
    Tier 4 Provider-level switch halts actions directed at a faulty downstream API.
    """
    t = TenantId("tnt_enterprise")

    await service.activate(
        scope=KillSwitchScope.PROVIDER,
        target_id="mock_logistics_v1",
        reason="Provider experiencing HTTP 500 error storm",
        principal="usr_sre_lead",
    )

    # Blocked for failing provider
    assert await service.is_blocked(t, "ship_item", "mock_logistics_v1", None)

    # Unblocked for healthy provider
    assert not await service.is_blocked(t, "ship_item", "ups_api", None)


@pytest.mark.asyncio
async def test_investigation_kill_switch(service: KillSwitchService) -> None:
    """
    Tier 5 Investigation switch halts actions originating from a suspect reasoning trace.
    """
    t = TenantId("tnt_enterprise")
    inv_target = UUIDv7.generate()
    inv_other = UUIDv7.generate()

    await service.activate(
        scope=KillSwitchScope.INVESTIGATION,
        target_id=str(inv_target),
        reason="Suspected LLM hallucination in root-cause graph",
        principal="usr_evaluator_lead",
    )

    # Blocked for matching investigation
    assert await service.is_blocked(t, "apply_discount", "billing_api", inv_target)

    # Unblocked for other investigations or direct actions
    assert not await service.is_blocked(t, "apply_discount", "billing_api", inv_other)
    assert not await service.is_blocked(t, "apply_discount", "billing_api", None)


@pytest.mark.asyncio
async def test_kill_switch_distributed_propagation_under_500ms(
    clean_bus: DistributedKillSwitchBus,
) -> None:
    """
    INV-REL-001: Kill switch activation state must propagate to other gateway instances in < 500ms.
    """
    # Instantiate two separate gateway nodes sharing distributed cache bus
    node_primary = KillSwitchService(bus=clean_bus)
    node_secondary = KillSwitchService(bus=clean_bus)

    tenant = TenantId("tnt_propagation_test")

    start_time = time.perf_counter()

    # Node Primary activates kill switch
    await node_primary.activate(
        scope=KillSwitchScope.TENANT,
        target_id=str(tenant),
        reason="Emergency propagation test",
        principal="usr_sre_operator",
    )

    # Node Secondary immediately evaluates
    blocked_on_secondary = await node_secondary.is_blocked(tenant, "ship", "mock", None)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    assert blocked_on_secondary is True
    # Invariant: propagation latency < 500ms
    assert elapsed_ms < 500.0, f"Propagation took {elapsed_ms:.2f}ms, exceeding 500ms threshold (INV-REL-001)"


@pytest.mark.asyncio
async def test_ai_agent_cannot_activate_or_deactivate_kill_switch(
    service: KillSwitchService,
) -> None:
    """
    AI agents are strictly forbidden from activating or deactivating kill switches (INV-ACT-003).
    """
    # Attempt activation with agent identities
    agent_principals = [
        "usr_agent_planner",
        "bot_remediation_worker",
        "agent_delegate",
        "usr_bot_42",
    ]

    for principal in agent_principals:
        with pytest.raises(AgentOverrideForbiddenError):
            await service.activate(
                scope=KillSwitchScope.GLOBAL,
                target_id=None,
                reason="Agent attempting autonomous shutdown",
                principal=principal,
            )

    # Human activates switch
    rec = await service.activate(
        scope=KillSwitchScope.GLOBAL,
        target_id=None,
        reason="Legitimate human operator intervention",
        principal="usr_human_sre",
    )

    # Agent attempts to deactivate switch
    for principal in agent_principals:
        with pytest.raises(AgentOverrideForbiddenError):
            await service.deactivate(
                switch_id=rec.switch_id,
                reason="Agent attempting self-clearing",
                principal=principal,
            )


@pytest.mark.asyncio
async def test_fail_closed_on_total_infrastructure_outage(
    clean_bus: DistributedKillSwitchBus,
) -> None:
    """
    Rollback and Recovery Contract:
    If Redis cache is unreachable, fallback to DB. If DB is also unreachable, fail closed (block all).
    """
    service = KillSwitchService(bus=clean_bus)

    # Simulate total cache & DB outage
    clean_bus.is_healthy = False
    service.is_db_healthy = False

    # Must fail closed — returning True (blocked) for any action
    is_blocked = await service.is_blocked(
        tenant_id=TenantId("tnt_any"),
        capability="action_any",
        provider="provider_any",
        investigation_id=None,
    )
    assert is_blocked is True
