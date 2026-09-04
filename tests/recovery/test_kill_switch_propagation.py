"""
RevPilot AI — Distributed Kill Switch Propagation Tests
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §5
Specification: docs/24-sre/PRODUCTION-READINESS-GATE.md §9 (PRG-SRE-02)
Conforms to INV-REL-001, AC-P08-006-01, and TC-P08-018.
"""

from __future__ import annotations

import asyncio
import pytest

from revpilot.modules.safety.killswitch.domain import KillSwitchScope
from revpilot.modules.safety.killswitch.service import DistributedKillSwitchBus, KillSwitchService
from revpilot.modules.testing.resilience.harness import (
    KillSwitchLagExceededError,
    ResilienceTestHarness,
)


@pytest.fixture
def harness() -> ResilienceTestHarness:
    return ResilienceTestHarness()


def test_kill_switch_propagation_within_500ms(harness: ResilienceTestHarness):
    """
    AC-P08-006-01: Kill-switch halts 100% of tool dispatches across all workers in < 500ms (INV-REL-001).
    """
    latency_ms = harness.measure_kill_switch_propagation_ms(
        workers_count=12,
        max_allowed_lag_ms=500.0,
    )

    assert latency_ms < 500.0
    assert latency_ms >= 0.0


def test_kill_switch_propagation_lag_exceeded_raises_error(harness: ResilienceTestHarness):
    """
    Verify that propagation lag > 500ms triggers KILL_SWITCH_LAG_EXCEEDED (500).
    """
    with pytest.raises(KillSwitchLagExceededError) as exc_info:
        harness.measure_kill_switch_propagation_ms(
            workers_count=10,
            max_allowed_lag_ms=500.0,
            simulated_lag_ms=620.0,
        )

    err = exc_info.value
    assert err.code == "KILL_SWITCH_LAG_EXCEEDED"
    assert err.status_code == 500
    assert err.retryable is False
    assert err.details["lag_ms"] == 620.0


@pytest.mark.asyncio
async def test_kill_switch_blocks_100_percent_worker_dispatches():
    """
    Verify active kill switch immediately reflects across all distributed worker instances.
    """
    bus = DistributedKillSwitchBus()
    worker_1 = KillSwitchService(bus=bus)
    worker_2 = KillSwitchService(bus=bus)
    worker_3 = KillSwitchService(bus=bus)

    # Initial state: 0 active kill switches
    assert len(await worker_1.get_active_switches()) == 0
    assert len(await worker_2.get_active_switches()) == 0
    assert len(await worker_3.get_active_switches()) == 0

    # Trigger kill switch on worker_1
    record = await worker_1.activate(
        scope=KillSwitchScope.GLOBAL,
        target_id=None,
        reason="Emergency halt under resilience stress test",
        principal="sre_admin",
    )

    # All workers must synchronously reflect active block
    active_w2 = await worker_2.get_active_switches()
    active_w3 = await worker_3.get_active_switches()

    assert any(s.switch_id == record.switch_id for s in active_w2)
    assert any(s.switch_id == record.switch_id for s in active_w3)
