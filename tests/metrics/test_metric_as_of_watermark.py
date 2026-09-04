"""
RevPilot AI — Unit and Contract Tests for As-Of Watermark & Anti-Leakage (Phase 02)
Verifies strict temporal boundaries, future watermark rejection, and point-in-time reproducibility.
Conforms to METRIC-SERVICE-SPEC.md §1.4, §4.1, TASK-P02-001, and AC-P02-001-03.
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
    return TenantId("tnt_watermark_001")


@pytest.fixture
def tenant_context(tenant_id) -> TenantContext:
    return TenantContext(tenant_id=tenant_id, organization_id=OrganizationId("org_001"))


@pytest.fixture
def past_time() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-02-01T10:00:00.000000Z")


@pytest.fixture
def as_of_watermark() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-02-01T12:00:00.000000Z")


@pytest.fixture
def future_time() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-02-01T14:00:00.000000Z")


@pytest.fixture
def server_now() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-02-01T12:00:00.000000Z")


@pytest.fixture
def window():
    from revpilot.modules.analytics import TimeWindow
    return TimeWindow(
        start_time=UtcDateTime.from_iso("2026-02-01T00:00:00.000000Z"),
        end_time=UtcDateTime.from_iso("2026-02-01T23:59:59.000000Z"),
    )


# =============================================================================
# AC-P02-001-03: Records with event_time > as_of_time Strictly Excluded
# =============================================================================

def test_future_event_time_records_strictly_excluded(
    tenant_id,
    tenant_context,
    past_time,
    as_of_watermark,
    future_time,
    window,
):
    """AC-P02-001-03: Records with event_time > as_of_time are 100% excluded from query results."""
    from revpilot.modules.analytics import (
        MetricEvaluationDataset,
        MetricService,
        MetricQueryRequest,
    )

    # 2 orders in past (1 cancelled, 1 delivered), 2 orders in future (both cancelled)
    orders = [
        Order(
            tenant_id=tenant_id,
            id="ord_past_1",
            customer_id="cus_001",
            order_number="ORD-P1",
            order_status=OrderStatus.CANCELLED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=as_of_watermark,
            event_time=past_time,
            effective_from=past_time,
            cancelled_at=past_time,
        ),
        Order(
            tenant_id=tenant_id,
            id="ord_past_2",
            customer_id="cus_001",
            order_number="ORD-P2",
            order_status=OrderStatus.DELIVERED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=as_of_watermark,
            event_time=past_time,
            effective_from=past_time,
        ),
        Order(
            tenant_id=tenant_id,
            id="ord_future_1",
            customer_id="cus_001",
            order_number="ORD-F1",
            order_status=OrderStatus.CANCELLED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=future_time,
            event_time=future_time,
            effective_from=future_time,
            cancelled_at=future_time,
        ),
        Order(
            tenant_id=tenant_id,
            id="ord_future_2",
            customer_id="cus_001",
            order_number="ORD-F2",
            order_status=OrderStatus.CANCELLED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=future_time,
            event_time=future_time,
            effective_from=future_time,
            cancelled_at=future_time,
        ),
    ]

    # Server clock matches as_of_watermark
    service = MetricService(
        dataset=MetricEvaluationDataset(orders=orders),
        clock=lambda: as_of_watermark,
    )

    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        as_of_time=as_of_watermark,
    )

    res = service.query(req, tenant_context)
    assert res.is_success
    pt = res.unwrap().series[0]

    # Future orders MUST NOT be included: total evaluated should be 2 (from past), not 4
    assert pt.sample_size == 2
    assert pt.denominator_value == 2.0
    assert pt.numerator_value == 1.0
    assert pt.actual_value == 0.5000


def test_future_as_of_watermark_rejected(tenant_context, server_now, window):
    """Query with as_of_time in the future relative to server clock returns TEMPORAL_LEAKAGE_REJECTED (HTTP 422)."""
    from revpilot.modules.analytics import (
        MetricService,
        MetricQueryRequest,
    )

    future_as_of = UtcDateTime.from_iso("2026-02-01T15:00:00.000000Z")
    service = MetricService(clock=lambda: server_now)

    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        as_of_time=future_as_of,
    )

    res = service.query(req, tenant_context)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "TEMPORAL_LEAKAGE_REJECTED"
    assert err.http_status == 422


def test_point_in_time_backtest_reproducibility(tenant_id, tenant_context, window):
    """Queries evaluated as-of different timestamps deterministically reflect point-in-time state."""
    from revpilot.modules.analytics import (
        MetricEvaluationDataset,
        MetricService,
        MetricQueryRequest,
    )

    t1 = UtcDateTime.from_iso("2026-02-01T10:00:00.000000Z")
    t2 = UtcDateTime.from_iso("2026-02-01T14:00:00.000000Z")
    t3 = UtcDateTime.from_iso("2026-02-01T18:00:00.000000Z")

    order_1 = Order(
        tenant_id=tenant_id,
        id="ord_1",
        customer_id="cus_001",
        order_number="O1",
        order_status=OrderStatus.CANCELLED,
        currency=Currency.USD,
        subtotal_cents=1000,
        tax_cents=100,
        shipping_cents=50,
        total_cents=1150,
        sla_delivery_deadline=t3,
        event_time=t1,
        effective_from=t1,
        cancelled_at=t1,
    )
    order_2 = Order(
        tenant_id=tenant_id,
        id="ord_2",
        customer_id="cus_001",
        order_number="O2",
        order_status=OrderStatus.DELIVERED,
        currency=Currency.USD,
        subtotal_cents=1000,
        tax_cents=100,
        shipping_cents=50,
        total_cents=1150,
        sla_delivery_deadline=t3,
        event_time=t2,
        effective_from=t2,
    )

    dataset = MetricEvaluationDataset(orders=[order_1, order_2])
    service = MetricService(dataset=dataset, clock=lambda: t3)

    # As of T1: only order_1 exists -> 1/1 = 1.0000
    req_t1 = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        as_of_time=t1,
    )
    res_t1 = service.query(req_t1, tenant_context)
    assert res_t1.is_success
    assert res_t1.unwrap().series[0].sample_size == 1
    assert res_t1.unwrap().series[0].actual_value == 1.0000

    # As of T3: both order_1 and order_2 exist -> 1/2 = 0.5000
    req_t3 = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        as_of_time=t3,
    )
    res_t3 = service.query(req_t3, tenant_context)
    assert res_t3.is_success
    assert res_t3.unwrap().series[0].sample_size == 2
    assert res_t3.unwrap().series[0].actual_value == 0.5000
