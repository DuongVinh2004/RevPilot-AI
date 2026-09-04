"""
RevPilot AI — Unit and Contract Tests for Zero-Volume Metric Queries (Phase 02)
Verifies zero-volume sample handling, denominator zero safety, and exception immunity.
Conforms to METRIC-SERVICE-SPEC.md §3.1, TASK-P02-001, and AC-P02-001-02.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext
from revpilot.shared.monetary import Currency

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
def tenant_id() -> TenantId:
    return TenantId("tnt_zero_vol_001")


@pytest.fixture
def tenant_context(tenant_id) -> TenantContext:
    return TenantContext(tenant_id=tenant_id, organization_id=OrganizationId("org_001"))


@pytest.fixture
def as_of_time() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z")


@pytest.fixture
def window():
    from revpilot.modules.analytics import TimeWindow
    return TimeWindow(
        start_time=UtcDateTime.from_iso("2026-02-01T00:00:00.000000Z"),
        end_time=UtcDateTime.from_iso("2026-02-02T00:00:00.000000Z"),
    )


# =============================================================================
# AC-P02-001-02: Zero-Volume Window Evaluations
# =============================================================================

@pytest.mark.parametrize(
    "metric_id",
    [
        "METRIC-001",  # cancellation_rate (RATIO)
        "METRIC-002",  # revenue_at_risk (SUM)
        "METRIC-003",  # fulfillment_delay_rate (RATIO)
        "METRIC-004",  # sla_violation_rate (RATIO)
        "METRIC-005",  # payment_failure_rate (RATIO)
        "METRIC-006",  # customer_churn_rate (RATIO)
        "METRIC-007",  # order_volume (COUNT)
        "METRIC-008",  # shipment_volume (COUNT)
        "METRIC-009",  # support_ticket_volume (COUNT)
    ],
)
def test_zero_event_window_returns_zero_and_flag_true(metric_id, tenant_context, as_of_time, window):
    """AC-P02-001-02: Zero-event window returns actual_value = 0.0 and is_zero_volume_sample = True without exception."""
    from revpilot.modules.analytics import (
        MetricEvaluationDataset,
        MetricService,
        MetricQueryRequest,
    )

    service = MetricService(dataset=MetricEvaluationDataset(), clock=lambda: as_of_time)
    req = MetricQueryRequest(
        metric_id=metric_id,
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        as_of_time=as_of_time,
    )

    res = service.query(req, tenant_context)
    assert res.is_success, f"Failed for {metric_id}: {res.unwrap_error()}"

    resp = res.unwrap()
    assert len(resp.series) >= 1
    pt = resp.series[0]

    assert pt.actual_value == 0.0
    assert pt.sample_size == 0
    assert pt.is_zero_volume_sample is True


def test_zero_event_window_when_events_exist_outside_window(tenant_id, tenant_context, as_of_time):
    """AC-P02-001-02: Window with no events returns 0.0 and is_zero_volume_sample = True even when other windows have data."""
    from revpilot.modules.analytics import (
        TimeWindow,
        MetricEvaluationDataset,
        MetricService,
        MetricQueryRequest,
    )

    jan_time = UtcDateTime.from_iso("2026-01-10T12:00:00.000000Z")
    order_jan = Order(
        tenant_id=tenant_id,
        id="ord_jan",
        customer_id="cus_001",
        order_number="ORD-JAN",
        order_status=OrderStatus.CANCELLED,
        currency=Currency.USD,
        subtotal_cents=1000,
        tax_cents=100,
        shipping_cents=50,
        total_cents=1150,
        sla_delivery_deadline=as_of_time,
        event_time=jan_time,
        effective_from=jan_time,
        cancelled_at=jan_time,
    )

    feb_window = TimeWindow(
        start_time=UtcDateTime.from_iso("2026-02-01T00:00:00.000000Z"),
        end_time=UtcDateTime.from_iso("2026-02-02T00:00:00.000000Z"),
    )

    service = MetricService(
        dataset=MetricEvaluationDataset(orders=[order_jan]),
        clock=lambda: as_of_time,
    )

    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=feb_window,
        grain="DAILY",
        as_of_time=as_of_time,
    )

    res = service.query(req, tenant_context)
    assert res.is_success
    pt = res.unwrap().series[0]
    assert pt.actual_value == 0.0
    assert pt.sample_size == 0
    assert pt.is_zero_volume_sample is True


def test_zero_denominator_safe_no_exception(tenant_context, as_of_time, window):
    """Ratio metric evaluation on empty denominator never raises ZeroDivisionError."""
    from revpilot.modules.analytics import (
        MetricEvaluationDataset,
        MetricService,
        MetricQueryRequest,
    )

    service = MetricService(dataset=MetricEvaluationDataset(), clock=lambda: as_of_time)
    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        as_of_time=as_of_time,
    )

    try:
        res = service.query(req, tenant_context)
        assert res.is_success
        pt = res.unwrap().series[0]
        assert pt.denominator_value == 0.0
        assert pt.actual_value == 0.0
    except ZeroDivisionError:
        pytest.fail("ZeroDivisionError raised during zero denominator query")
