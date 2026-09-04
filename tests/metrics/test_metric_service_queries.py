"""
RevPilot AI — Unit and Contract Tests for Metric Service Queries (Phase 02)
Verifies MetricService.query(), canonical calculations, tenant isolation, and error matrix.
Conforms to METRIC-SERVICE-SPEC.md §1–§4, TASK-P02-001, and AC-P02-001-01 .. AC-P02-001-04.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext
from revpilot.shared.monetary import Currency

from revpilot.modules.canonical import (
    Customer,
    AccountTier,
    CustomerStatus,
    Order,
    OrderStatus,
    Shipment,
    DispatchStatus,
    SupportTicket,
    TicketTopic,
    TicketPriority,
    TicketStatus,
    Contract,
    ContractClause,
    ClauseType,
    PaymentReference,
    GatewayProvider,
    TransactionType,
    PaymentStatus,
)


@pytest.fixture(autouse=True)
def _isolate_analytics_module():
    """Ensure analytics module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.analytics"):
            sys.modules.pop(mod, None)


@pytest.fixture
def tenant_a() -> TenantId:
    return TenantId("tnt_alpha001")


@pytest.fixture
def tenant_b() -> TenantId:
    return TenantId("tnt_bravo002")


@pytest.fixture
def tenant_context_a(tenant_a) -> TenantContext:
    return TenantContext(tenant_id=tenant_a, organization_id=OrganizationId("org_001"))


@pytest.fixture
def tenant_context_b(tenant_b) -> TenantContext:
    return TenantContext(tenant_id=tenant_b, organization_id=OrganizationId("org_002"))


@pytest.fixture
def base_time() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-02-01T10:00:00.000000Z")


@pytest.fixture
def as_of_time() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-02-01T12:00:00.000000Z")


@pytest.fixture
def window(base_time, as_of_time):
    from revpilot.modules.analytics import TimeWindow
    return TimeWindow(
        start_time=UtcDateTime.from_iso("2026-02-01T00:00:00.000000Z"),
        end_time=UtcDateTime.from_iso("2026-02-01T23:59:59.000000Z"),
    )


# =============================================================================
# AC-P02-001-01: Exact Canonical Values for cancellation_rate & revenue_at_risk
# =============================================================================

def test_cancellation_rate_exact_canonical_calculation(tenant_a, tenant_context_a, base_time, as_of_time, window):
    """AC-P02-001-01: MetricService.query computes exact canonical cancellation_rate (2/5 = 0.4000)."""
    from revpilot.modules.analytics import (
        MetricEvaluationDataset,
        MetricService,
        MetricQueryRequest,
    )

    orders = [
        Order(
            tenant_id=tenant_a,
            id=f"ord_00{i}",
            customer_id="cus_001",
            order_number=f"ORD-00{i}",
            order_status=OrderStatus.CANCELLED if i in (1, 2) else OrderStatus.DELIVERED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=as_of_time,
            event_time=base_time,
            effective_from=base_time,
            cancelled_at=base_time if i in (1, 2) else None,
        )
        for i in range(1, 6)
    ]

    dataset = MetricEvaluationDataset(orders=orders)
    service = MetricService(dataset=dataset, clock=lambda: as_of_time)

    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        as_of_time=as_of_time,
    )

    res = service.query(req, tenant_context_a)
    assert res.is_success, f"Expected success, got {res.unwrap_error()}"

    resp = res.unwrap()
    assert resp.metric_id == "METRIC-001"
    assert resp.metric_name == "cancellation_rate"
    assert resp.tenant_id == tenant_a
    assert len(resp.series) == 1

    pt = resp.series[0]
    assert pt.actual_value == 0.4000
    assert pt.numerator_value == 2.0
    assert pt.denominator_value == 5.0
    assert pt.sample_size == 5
    assert not pt.is_zero_volume_sample
    assert len(resp.lineage_snapshot_hash) == 64


def test_revenue_at_risk_exact_canonical_calculation(tenant_a, tenant_context_a, base_time, as_of_time, window):
    """AC-P02-001-01: MetricService.query computes exact revenue_at_risk sum in integer cents."""
    from revpilot.modules.analytics import (
        MetricEvaluationDataset,
        MetricService,
        MetricQueryRequest,
    )

    order_at_risk = Order(
        tenant_id=tenant_a,
        id="ord_risk_1",
        customer_id="cus_001",
        order_number="ORD-R1",
        order_status=OrderStatus.SHIPPED,
        currency=Currency.USD,
        subtotal_cents=10000,
        tax_cents=500,
        shipping_cents=200,
        total_cents=10700,
        sla_delivery_deadline=as_of_time,
        event_time=base_time,
        effective_from=base_time,
    )
    order_safe = Order(
        tenant_id=tenant_a,
        id="ord_safe_1",
        customer_id="cus_001",
        order_number="ORD-S1",
        order_status=OrderStatus.SHIPPED,
        currency=Currency.USD,
        subtotal_cents=5000,
        tax_cents=200,
        shipping_cents=100,
        total_cents=5300,
        sla_delivery_deadline=as_of_time,
        event_time=base_time,
        effective_from=base_time,
    )
    shipment_delayed = Shipment(
        tenant_id=tenant_a,
        id="shp_risk_1",
        order_id="ord_risk_1",
        tracking_number="TRK1",
        carrier_id="CARRIER_A",
        carrier_name="Carrier A",
        warehouse_id="WH1",
        origin_region="US-MIDWEST",
        destination_region="US-EAST",
        dispatch_status=DispatchStatus.DELAYED,
        is_delayed=True,
        estimated_delivery_at=as_of_time,
        event_time=base_time,
        effective_from=base_time,
    )
    shipment_safe = Shipment(
        tenant_id=tenant_a,
        id="shp_safe_1",
        order_id="ord_safe_1",
        tracking_number="TRK2",
        carrier_id="CARRIER_A",
        carrier_name="Carrier A",
        warehouse_id="WH1",
        origin_region="US-MIDWEST",
        destination_region="US-EAST",
        dispatch_status=DispatchStatus.IN_TRANSIT,
        is_delayed=False,
        estimated_delivery_at=as_of_time,
        event_time=base_time,
        effective_from=base_time,
    )

    dataset = MetricEvaluationDataset(
        orders=[order_at_risk, order_safe],
        shipments=[shipment_delayed, shipment_safe],
    )
    service = MetricService(dataset=dataset, clock=lambda: as_of_time)

    req = MetricQueryRequest(
        metric_id="METRIC-002",
        metric_version="1.0.0",
        time_window=window,
        grain="AS_OF_SNAPSHOT",
        as_of_time=as_of_time,
    )

    res = service.query(req, tenant_context_a)
    assert res.is_success
    resp = res.unwrap()
    assert resp.metric_id == "METRIC-002"
    assert len(resp.series) == 1

    pt = resp.series[0]
    assert pt.actual_value == 10700.0
    assert pt.numerator_value == 10700.0
    assert pt.sample_size == 1
    assert not pt.is_zero_volume_sample


# =============================================================================
# AC-P02-001-04: Non-allowed Dimension Fails Closed (INVALID_DIMENSION_FILTER)
# =============================================================================

def test_unapproved_dimension_in_group_by_rejected(tenant_context_a, as_of_time, window):
    """AC-P02-001-04: Requested group-by dimension not in allowed_dimensions returns INVALID_DIMENSION_FILTER."""
    from revpilot.modules.analytics import (
        MetricService,
        MetricQueryRequest,
    )

    service = MetricService(clock=lambda: as_of_time)
    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        group_by_dimensions=["unregistered_secret_dimension"],
        as_of_time=as_of_time,
    )

    res = service.query(req, tenant_context_a)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "INVALID_DIMENSION_FILTER"
    assert err.http_status == 400


def test_unapproved_dimension_in_filters_rejected(tenant_context_a, as_of_time, window):
    """AC-P02-001-04: Requested filter dimension not in allowed_dimensions returns INVALID_DIMENSION_FILTER."""
    from revpilot.modules.analytics import (
        MetricService,
        MetricQueryRequest,
    )

    service = MetricService(clock=lambda: as_of_time)
    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        filters={"malicious_sql_injection_dimension": "1 OR 1=1"},
        as_of_time=as_of_time,
    )

    res = service.query(req, tenant_context_a)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "INVALID_DIMENSION_FILTER"
    assert err.http_status == 400


# =============================================================================
# Error Matrix & Tenancy Violation Checks
# =============================================================================

def test_unknown_metric_id_rejected(tenant_context_a, as_of_time, window):
    """Querying an unknown metric returns METRIC_NOT_REGISTERED (HTTP 404)."""
    from revpilot.modules.analytics import (
        MetricService,
        MetricQueryRequest,
    )

    service = MetricService(clock=lambda: as_of_time)
    req = MetricQueryRequest(
        metric_id="METRIC-999",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        as_of_time=as_of_time,
    )

    res = service.query(req, tenant_context_a)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "METRIC_NOT_REGISTERED"
    assert err.http_status == 404


def test_tenant_context_mismatch_rejected(tenant_context_a, tenant_b, as_of_time, window):
    """Client attempt to override tenant_id via filters returns TENANCY_VIOLATION (HTTP 403)."""
    from revpilot.modules.analytics import (
        MetricService,
        MetricQueryRequest,
    )

    service = MetricService(clock=lambda: as_of_time)
    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        filters={"tenant_id": str(tenant_b)},
        as_of_time=as_of_time,
    )

    res = service.query(req, tenant_context_a)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "TENANCY_VIOLATION"
    assert err.http_status == 403


def test_cross_tenant_isolation_in_query(tenant_a, tenant_b, tenant_context_a, base_time, as_of_time, window):
    """Data belonging to tenant B is invisible to queries executing in tenant A context."""
    from revpilot.modules.analytics import (
        MetricEvaluationDataset,
        MetricService,
        MetricQueryRequest,
    )

    orders = [
        Order(
            tenant_id=tenant_a,
            id="ord_a",
            customer_id="cus_001",
            order_number="ORD-A",
            order_status=OrderStatus.CANCELLED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=as_of_time,
            event_time=base_time,
            effective_from=base_time,
            cancelled_at=base_time,
        ),
        Order(
            tenant_id=tenant_b,
            id="ord_b",
            customer_id="cus_002",
            order_number="ORD-B",
            order_status=OrderStatus.DELIVERED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=as_of_time,
            event_time=base_time,
            effective_from=base_time,
        ),
    ]

    service = MetricService(dataset=MetricEvaluationDataset(orders=orders), clock=lambda: as_of_time)
    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        as_of_time=as_of_time,
    )

    res_a = service.query(req, tenant_context_a)
    assert res_a.is_success
    pt_a = res_a.unwrap().series[0]
    # Tenant A sees only its 1 cancelled order -> ratio 1/1 = 1.0000
    assert pt_a.sample_size == 1
    assert pt_a.actual_value == 1.0000


# =============================================================================
# Dimensional Grouping & Grain Slicing Verification
# =============================================================================

def test_query_grouped_by_dimension(tenant_a, tenant_context_a, base_time, as_of_time, window):
    """Querying cancellation_rate grouped by carrier_id segments results correctly."""
    from revpilot.modules.analytics import (
        MetricEvaluationDataset,
        MetricService,
        MetricQueryRequest,
    )

    orders = [
        Order(
            tenant_id=tenant_a,
            id="ord_c1",
            customer_id="cus_001",
            order_number="O1",
            order_status=OrderStatus.CANCELLED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=as_of_time,
            event_time=base_time,
            effective_from=base_time,
            cancelled_at=base_time,
        ),
        Order(
            tenant_id=tenant_a,
            id="ord_c2",
            customer_id="cus_001",
            order_number="O2",
            order_status=OrderStatus.DELIVERED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=as_of_time,
            event_time=base_time,
            effective_from=base_time,
        ),
    ]
    shipments = [
        Shipment(
            tenant_id=tenant_a,
            id="s1",
            order_id="ord_c1",
            tracking_number="T1",
            carrier_id="CARRIER_ALPHA",
            carrier_name="Alpha",
            warehouse_id="WH1",
            origin_region="US-EAST",
            destination_region="US-EAST",
            dispatch_status=DispatchStatus.IN_TRANSIT,
            estimated_delivery_at=as_of_time,
            event_time=base_time,
            effective_from=base_time,
        ),
        Shipment(
            tenant_id=tenant_a,
            id="s2",
            order_id="ord_c2",
            tracking_number="T2",
            carrier_id="CARRIER_BETA",
            carrier_name="Beta",
            warehouse_id="WH1",
            origin_region="US-EAST",
            destination_region="US-EAST",
            dispatch_status=DispatchStatus.IN_TRANSIT,
            estimated_delivery_at=as_of_time,
            event_time=base_time,
            effective_from=base_time,
        ),
    ]

    service = MetricService(
        dataset=MetricEvaluationDataset(orders=orders, shipments=shipments),
        clock=lambda: as_of_time,
    )
    req = MetricQueryRequest(
        metric_id="METRIC-001",
        metric_version="1.0.0",
        time_window=window,
        grain="DAILY",
        group_by_dimensions=["carrier_id"],
        as_of_time=as_of_time,
    )

    res = service.query(req, tenant_context_a)
    assert res.is_success
    series = res.unwrap().series
    assert len(series) == 2

    by_carrier = {s.dimensions["carrier_id"]: s for s in series}
    assert "CARRIER_ALPHA" in by_carrier
    assert "CARRIER_BETA" in by_carrier
    assert by_carrier["CARRIER_ALPHA"].actual_value == 1.0000
    assert by_carrier["CARRIER_BETA"].actual_value == 0.0000


def test_all_9_metrics_executable_via_metric_service(tenant_context_a, as_of_time, window):
    """All canonical metrics (METRIC-001 through METRIC-009) execute cleanly via MetricService."""
    from revpilot.modules.analytics import (
        MetricService,
        MetricQueryRequest,
    )

    service = MetricService(clock=lambda: as_of_time)
    for i in range(1, 10):
        mid = f"METRIC-00{i}"
        req = MetricQueryRequest(
            metric_id=mid,
            metric_version="1.0.0",
            time_window=window,
            grain="DAILY",
            as_of_time=as_of_time,
        )
        res = service.query(req, tenant_context_a)
        assert res.is_success, f"Failed executing {mid}: {res.unwrap_error()}"
        resp = res.unwrap()
        assert resp.metric_id == mid
        assert len(resp.series) >= 1
