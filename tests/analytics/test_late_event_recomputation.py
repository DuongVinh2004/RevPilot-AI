"""
RevPilot AI — Late-Event Metric Recomputation & Reconciliation Tests (Phase 02)
Verifies AC-P02-005-03, DATA-QUALITY-LINEAGE-SPEC.md §7.2, and INV-DATA-002.
"""

from __future__ import annotations
import sys
from datetime import timedelta
import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.monetary import Currency
from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.modules.canonical import (
    Order,
    OrderStatus,
)


@pytest.fixture(autouse=True)
def _isolate_analytics_module():
    """Ensure analytics module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.analytics"):
            sys.modules.pop(mod, None)


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha")


@pytest.fixture
def base_window() -> tuple[UtcDateTime, UtcDateTime]:
    start = UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z")
    end = UtcDateTime.from_iso("2026-02-16T00:00:00.000000Z")
    return start, end


@pytest.fixture
def initial_anomaly(tenant_alpha, base_window):
    from revpilot.modules.analytics.lifecycle import AnomalyAggregate, AnomalyState
    start, end = base_window
    anm = AnomalyAggregate.create_detected(
        id="anm_late_event_test_001",
        tenant_id=tenant_alpha,
        metric_id="METRIC-001",
        metric_version="1.0.0",
        detector_id="DET-STL-RESIDUAL-001",
        detector_version="1.0.0",
        baseline_id="BASE-SEASONAL-NAIVE-001",
        baseline_version="1.0.0",
        observation_window_start=start,
        observation_window_end=end,
        as_of_time=end,
        actual_value=0.1000,  # 10% cancellation rate
        expected_value=0.0180,
        expected_interval=(0.0100, 0.0250),  # Upper bound 2.5%
        anomaly_score=0.9000,
        severity="CRITICAL",
        created_at=end,
    )
    # Advance to VALIDATED
    actor = PrincipalContext(PrincipalId("usr_system"), tenant_alpha, is_system=True)
    anm.transition_to(AnomalyState.VALIDATED, actor, "DQ_PASSED")
    return anm


# =============================================================================
# AC-P02-005-03: Late-Event Supersession Workflow
# =============================================================================

def test_late_event_supersedes_anomaly_to_suppressed(tenant_alpha, base_window, initial_anomaly):
    """
    AC-P02-005-03: Late-event metric recomputation transitions superseded anomalies to SUPPRESSED
    with reason SUPERSEDED_BY_RECOMPUTATION while preserving immutable historical audit records.
    """
    from revpilot.modules.analytics.schemas import TimeWindow
    from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
    from revpilot.modules.analytics.lifecycle import AnomalyState
    from revpilot.modules.analytics.reconciliation import ReconciliationEngine

    start, end = base_window
    reconciliation_as_of = UtcDateTime.from_iso("2026-02-18T12:00:00.000000Z")

    # Construct updated dataset where late delivered orders reduce cancellation rate below 2.5% bound:
    # 2 cancelled orders out of 100 total orders = 2.0% (< 2.5% upper bound)
    orders: list[Order] = []
    for i in range(100):
        o_id = f"ord_reconcile_{i}"
        dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i % 24))
        is_cancelled = (i < 2)
        orders.append(
            Order(
                tenant_id=tenant_alpha,
                id=o_id,
                customer_id="cust_001",
                order_number=f"ORD-REC-{i}",
                order_status=OrderStatus.CANCELLED if is_cancelled else OrderStatus.DELIVERED,
                currency=Currency.USD,
                subtotal_cents=1000,
                tax_cents=100,
                shipping_cents=50,
                total_cents=1150,
                sla_delivery_deadline=dt,
                event_time=dt,
                effective_from=dt,
                ingested_at=dt,
                cancelled_at=dt if is_cancelled else None,
            )
        )

    updated_dataset = MetricEvaluationDataset(orders=tuple(orders))
    engine = ReconciliationEngine(dataset=updated_dataset)
    engine.register_anomaly(initial_anomaly)

    # Prior transition count before reconciliation
    prior_transition_count = len(initial_anomaly.transitions)
    assert prior_transition_count == 2  # DETECTED + VALIDATED

    # Execute reconciliation pass over affected window
    affected = engine.reconcile_window(
        tenant_id=tenant_alpha,
        metric_id="METRIC-001",
        affected_window=TimeWindow(start, end),
        as_of=reconciliation_as_of,
    )

    assert len(affected) == 1
    anm = affected[0]

    # AC-P02-005-03: Transitioned to SUPPRESSED with SUPERSEDED_BY_RECOMPUTATION
    assert anm.state == AnomalyState.SUPPRESSED
    assert anm.suppression_reason == "SUPERSEDED_BY_RECOMPUTATION"
    assert anm.effective_to == reconciliation_as_of
    assert anm.data_freshness == "FRESH"

    # Verify immutable audit trail preserved without overwriting historical records (INV-DATA-002)
    assert len(anm.transitions) == prior_transition_count + 1
    latest_trans = anm.transitions[-1]
    assert latest_trans.from_state == AnomalyState.VALIDATED
    assert latest_trans.to_state == AnomalyState.SUPPRESSED
    assert latest_trans.reason == "SUPERSEDED_BY_RECOMPUTATION"
    assert latest_trans.metadata["recalculated_value"] == 0.02
    assert latest_trans.metadata["previous_value"] == 0.1000

    # Verify outbox event emitted
    latest_event = anm.pending_outbox_events[-1]
    assert latest_event.event_type == "anomaly.suppressed.v1"
    assert latest_event.payload["suppression_reason"] == "SUPERSEDED_BY_RECOMPUTATION"


def test_late_event_still_anomalous_remains_active(tenant_alpha, base_window, initial_anomaly):
    """When recalculated metric still breaches upper threshold, anomaly remains in active state."""
    from revpilot.modules.analytics.schemas import TimeWindow
    from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
    from revpilot.modules.analytics.lifecycle import AnomalyState
    from revpilot.modules.analytics.reconciliation import ReconciliationEngine

    start, end = base_window
    reconciliation_as_of = UtcDateTime.from_iso("2026-02-18T12:00:00.000000Z")

    # 8 cancelled out of 100 orders = 8.0% (> 2.5% upper bound)
    orders: list[Order] = []
    for i in range(100):
        o_id = f"ord_still_anm_{i}"
        dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i % 24))
        is_cancelled = (i < 8)
        orders.append(
            Order(
                tenant_id=tenant_alpha,
                id=o_id,
                customer_id="cust_001",
                order_number=f"ORD-STILL-{i}",
                order_status=OrderStatus.CANCELLED if is_cancelled else OrderStatus.DELIVERED,
                currency=Currency.USD,
                subtotal_cents=1000,
                tax_cents=100,
                shipping_cents=50,
                total_cents=1150,
                sla_delivery_deadline=dt,
                event_time=dt,
                effective_from=dt,
                ingested_at=dt,
                cancelled_at=dt if is_cancelled else None,
            )
        )

    updated_dataset = MetricEvaluationDataset(orders=tuple(orders))
    engine = ReconciliationEngine(dataset=updated_dataset)
    engine.register_anomaly(initial_anomaly)

    affected = engine.reconcile_window(
        tenant_id=tenant_alpha,
        metric_id="METRIC-001",
        affected_window=TimeWindow(start, end),
        as_of=reconciliation_as_of,
    )

    assert len(affected) == 1
    anm = affected[0]
    # Remains VALIDATED (not superseded)
    assert anm.state == AnomalyState.VALIDATED
    assert anm.actual_value == 0.08
    assert anm.data_freshness == "FRESH"
    assert anm.effective_to is None
