"""
RevPilot AI — Unit and Contract Tests for Metric Semantics (Phase 01)
Verifies METRIC-REGISTRY.md, INV-TEN-001, INV-DATA-001, and AC-P01-002-01 .. AC-P01-002-04.
Imports analytics lazily to prevent cross-module test contamination during test collection.
"""

from __future__ import annotations
import sys
from decimal import Decimal
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.monetary import Currency

from revpilot.modules.canonical import (
    Customer,
    CustomerSegment,
    AccountTier,
    CustomerStatus,
    Order,
    OrderStatus,
    OrderLine,
    Shipment,
    DispatchStatus,
    SupportTicket,
    TicketTopic,
    TicketPriority,
    TicketStatus,
    Contract,
    ContractType,
    ContractStatus,
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
def base_time() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-09-04T10:00:00.000000Z")


@pytest.fixture
def as_of_time() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-09-04T12:00:00.000000Z")


@pytest.fixture
def future_time() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-09-04T14:00:00.000000Z")


# =============================================================================
# Architectural & Module Boundary Tests
# =============================================================================

def test_analytics_module_exports():
    """Verify public exports of the analytics metrics module."""
    import revpilot.modules.analytics as analytics
    expected = {
        "MetricType",
        "MetricGrain",
        "MetricEvaluationDataset",
        "MetricValue",
        "MetricDefinition",
        "CANONICAL_METRIC_DEFINITIONS",
        "MetricNotFoundError",
        "InvalidMetricFilterError",
        "TemporalLeakageError",
        "MetricEvaluationError",
        "MetricRegistry",
        "CANONICAL_METRIC_REGISTRY",
    }
    actual = set(analytics.__all__)
    assert expected.issubset(actual), f"Missing exports: {expected - actual}"


def test_analytics_module_forbidden_dependencies():
    """Verify analytics module has zero forbidden dependencies."""
    import revpilot.modules.analytics as analytics
    forbidden = ["sqlalchemy", "psycopg", "temporalio", "langgraph", "fastapi"]
    for mod in forbidden:
        assert mod not in sys.modules or not any(
            mod in getattr(val, "__module__", "")
            for val in vars(analytics).values()
        ), f"Analytics module illegally depends on {mod}"


# =============================================================================
# AC-P01-002-01: All 9 Canonical Metrics Registered & Retrievable
# =============================================================================

def test_all_9_canonical_metrics_registered():
    """AC-P01-002-01: METRIC-001 through METRIC-009 are registered and retrievable."""
    from revpilot.modules.analytics import CANONICAL_METRIC_REGISTRY
    expected_ids = [
        "METRIC-001",
        "METRIC-002",
        "METRIC-003",
        "METRIC-004",
        "METRIC-005",
        "METRIC-006",
        "METRIC-007",
        "METRIC-008",
        "METRIC-009",
    ]
    expected_names = [
        "cancellation_rate",
        "revenue_at_risk",
        "fulfillment_delay_rate",
        "sla_violation_rate",
        "payment_failure_rate",
        "customer_churn_rate",
        "order_volume",
        "shipment_volume",
        "support_ticket_volume",
    ]

    all_metrics = CANONICAL_METRIC_REGISTRY.list_metrics()
    assert len(all_metrics) == 9

    for mid in expected_ids:
        res = CANONICAL_METRIC_REGISTRY.get(mid)
        assert res.is_success, f"Failed to get {mid}"
        metric = res.unwrap()
        assert metric.metric_id == mid

    for name in expected_names:
        res = CANONICAL_METRIC_REGISTRY.get(name)
        assert res.is_success, f"Failed to get {name}"
        metric = res.unwrap()
        assert metric.name == name


def test_unknown_metric_returns_not_found():
    """Querying an unknown metric returns MetricNotFoundError."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricNotFoundError,
        MetricEvaluationDataset,
    )
    res = CANONICAL_METRIC_REGISTRY.get("METRIC-999")
    assert res.is_failure
    assert isinstance(res.unwrap_error(), MetricNotFoundError)

    eval_res = CANONICAL_METRIC_REGISTRY.evaluate(
        metric_id="METRIC-999",
        tenant_id=TenantId("tnt_alpha001"),
        data=MetricEvaluationDataset(),
        as_of=UtcDateTime.now(),
    )
    assert eval_res.is_failure
    assert isinstance(eval_res.unwrap_error(), MetricNotFoundError)


# =============================================================================
# AC-P01-002-02: Deterministic Cancellation Rate Math Verification
# =============================================================================

def test_cancellation_rate_exact_math_on_fixture(tenant_a, base_time, as_of_time, future_time):
    """AC-P01-002-02: cancellation_rate evaluates to exact expected ratio (2/5 = 0.4000)."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
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
            sla_delivery_deadline=future_time,
            event_time=base_time,
            effective_from=base_time,
            cancelled_at=base_time if i in (1, 2) else None,
        )
        for i in range(1, 6)
    ]

    dataset = MetricEvaluationDataset(orders=orders)
    eval_res = CANONICAL_METRIC_REGISTRY.evaluate(
        metric_id="METRIC-001",
        tenant_id=tenant_a,
        data=dataset,
        as_of=as_of_time,
    )

    assert eval_res.is_success
    result = eval_res.unwrap()
    assert result.value == 0.4000
    assert result.numerator == 2.0
    assert result.denominator == 5.0
    assert not result.is_zero_sample


# =============================================================================
# AC-P01-002-03: Zero Denominator Safe Handling
# =============================================================================

def test_ratio_metrics_zero_denominator_safe(tenant_a, as_of_time):
    """AC-P01-002-03: Empty dataset returns 0.0 with is_zero_sample=True, no divide by zero."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    ratio_metric_ids = ["METRIC-001", "METRIC-003", "METRIC-004", "METRIC-005", "METRIC-006"]
    empty_data = MetricEvaluationDataset()

    for mid in ratio_metric_ids:
        res = CANONICAL_METRIC_REGISTRY.evaluate(
            metric_id=mid,
            tenant_id=tenant_a,
            data=empty_data,
            as_of=as_of_time,
        )
        assert res.is_success
        metric_val = res.unwrap()
        assert metric_val.value == 0.0
        assert metric_val.is_zero_sample
        assert metric_val.denominator == 0.0


# =============================================================================
# AC-P01-002-04: Strict As-Of Watermarking (INV-DATA-001)
# =============================================================================

def test_future_records_strictly_excluded_from_metrics(tenant_a, base_time, as_of_time, future_time):
    """AC-P01-002-04: Orders with event_time > as_of are strictly excluded."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    orders = [
        Order(
            tenant_id=tenant_a,
            id="ord_past_1",
            customer_id="cus_001",
            order_number="ORD-P1",
            order_status=OrderStatus.CANCELLED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=future_time,
            event_time=base_time,
            effective_from=base_time,
            cancelled_at=base_time,
        ),
        Order(
            tenant_id=tenant_a,
            id="ord_past_2",
            customer_id="cus_001",
            order_number="ORD-P2",
            order_status=OrderStatus.DELIVERED,
            currency=Currency.USD,
            subtotal_cents=1000,
            tax_cents=100,
            shipping_cents=50,
            total_cents=1150,
            sla_delivery_deadline=future_time,
            event_time=base_time,
            effective_from=base_time,
        ),
        Order(
            tenant_id=tenant_a,
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
            tenant_id=tenant_a,
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

    dataset = MetricEvaluationDataset(orders=orders)
    eval_res = CANONICAL_METRIC_REGISTRY.evaluate(
        metric_id="METRIC-001",
        tenant_id=tenant_a,
        data=dataset,
        as_of=as_of_time,
    )

    assert eval_res.is_success
    result = eval_res.unwrap()
    assert result.denominator == 2.0
    assert result.numerator == 1.0
    assert result.value == 0.5000


# =============================================================================
# Mandatory Tenant Scoping (INV-TEN-001)
# =============================================================================

def test_tenant_isolation_in_evaluations(tenant_a, tenant_b, base_time, as_of_time, future_time):
    """INV-TEN-001: Evaluation for tenant A strictly ignores tenant B records."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    orders = [
        Order(
            tenant_id=tenant_a,
            id="ord_a_1",
            customer_id="cus_001",
            order_number="ORD-A1",
            order_status=OrderStatus.CANCELLED,
            currency=Currency.USD,
            subtotal_cents=100,
            tax_cents=10,
            shipping_cents=5,
            total_cents=115,
            sla_delivery_deadline=future_time,
            event_time=base_time,
            effective_from=base_time,
            cancelled_at=base_time,
        ),
        *[
            Order(
                tenant_id=tenant_b,
                id=f"ord_b_{i}",
                customer_id="cus_b_001",
                order_number=f"ORD-B{i}",
                order_status=OrderStatus.DELIVERED,
                currency=Currency.USD,
                subtotal_cents=100,
                tax_cents=10,
                shipping_cents=5,
                total_cents=115,
                sla_delivery_deadline=future_time,
                event_time=base_time,
                effective_from=base_time,
            )
            for i in range(1, 100)
        ],
    ]

    dataset = MetricEvaluationDataset(orders=orders)

    res_a = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-001", tenant_a, dataset, as_of_time)
    assert res_a.is_success
    assert res_a.unwrap().value == 1.0
    assert res_a.unwrap().denominator == 1.0

    res_b = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-001", tenant_b, dataset, as_of_time)
    assert res_b.is_success
    assert res_b.unwrap().value == 0.0
    assert res_b.unwrap().denominator == 99.0


# =============================================================================
# Dimension Filtering & Rejection
# =============================================================================

def test_invalid_dimension_filter_fails_closed(tenant_a, as_of_time):
    """Querying with a non-allowed dimension returns InvalidMetricFilterError."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        InvalidMetricFilterError,
        MetricEvaluationDataset,
    )
    res = CANONICAL_METRIC_REGISTRY.evaluate(
        metric_id="METRIC-001",
        tenant_id=tenant_a,
        data=MetricEvaluationDataset(),
        as_of=as_of_time,
        filters={"unregistered_fake_dimension": "test"},
    )
    assert res.is_failure
    assert isinstance(res.unwrap_error(), InvalidMetricFilterError)


def test_valid_dimension_filter_filtering(tenant_a, base_time, as_of_time, future_time):
    """Valid dimension filters filter data correctly."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    orders = [
        Order(
            tenant_id=tenant_a,
            id="ord_1",
            customer_id="cus_1",
            order_number="ORD-1",
            order_status=OrderStatus.CANCELLED,
            currency=Currency.USD,
            subtotal_cents=100,
            tax_cents=10,
            shipping_cents=5,
            total_cents=115,
            sla_delivery_deadline=future_time,
            event_time=base_time,
            effective_from=base_time,
            cancelled_at=base_time,
        ),
        Order(
            tenant_id=tenant_a,
            id="ord_2",
            customer_id="cus_2",
            order_number="ORD-2",
            order_status=OrderStatus.DELIVERED,
            currency=Currency.USD,
            subtotal_cents=100,
            tax_cents=10,
            shipping_cents=5,
            total_cents=115,
            sla_delivery_deadline=future_time,
            event_time=base_time,
            effective_from=base_time,
        ),
    ]

    shipments = [
        Shipment(
            tenant_id=tenant_a,
            id="shp_1",
            order_id="ord_1",
            tracking_number="TRK1",
            carrier_id="CARRIER_A",
            carrier_name="Carrier A",
            warehouse_id="WH-EAST",
            origin_region="US-EAST",
            destination_region="US-EAST",
            dispatch_status=DispatchStatus.IN_TRANSIT,
            estimated_delivery_at=future_time,
            event_time=base_time,
            effective_from=base_time,
        ),
        Shipment(
            tenant_id=tenant_a,
            id="shp_2",
            order_id="ord_2",
            tracking_number="TRK2",
            carrier_id="CARRIER_B",
            carrier_name="Carrier B",
            warehouse_id="WH-WEST",
            origin_region="US-WEST",
            destination_region="US-WEST",
            dispatch_status=DispatchStatus.DELIVERED,
            estimated_delivery_at=future_time,
            event_time=base_time,
            effective_from=base_time,
        ),
    ]

    dataset = MetricEvaluationDataset(orders=orders, shipments=shipments)

    res_a = CANONICAL_METRIC_REGISTRY.evaluate(
        metric_id="METRIC-001",
        tenant_id=tenant_a,
        data=dataset,
        as_of=as_of_time,
        filters={"carrier_id": "CARRIER_A"},
    )
    assert res_a.is_success
    assert res_a.unwrap().denominator == 1.0
    assert res_a.unwrap().value == 1.0

    res_b = CANONICAL_METRIC_REGISTRY.evaluate(
        metric_id="METRIC-001",
        tenant_id=tenant_a,
        data=dataset,
        as_of=as_of_time,
        filters={"carrier_id": "CARRIER_B"},
    )
    assert res_b.is_success
    assert res_b.unwrap().denominator == 1.0
    assert res_b.unwrap().value == 0.0


# =============================================================================
# Coverage for Remaining Canonical Metrics (METRIC-002 .. METRIC-009)
# =============================================================================

def test_revenue_at_risk_metric(tenant_a, base_time, as_of_time, future_time):
    """METRIC-002: revenue_at_risk sums total_cents of delayed or cancellation-inquiry orders."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    order_delayed = Order(
        tenant_id=tenant_a,
        id="ord_risk_1",
        customer_id="cus_1",
        order_number="O1",
        order_status=OrderStatus.SHIPPED,
        currency=Currency.USD,
        subtotal_cents=10000,
        tax_cents=500,
        shipping_cents=200,
        total_cents=10700,
        sla_delivery_deadline=future_time,
        event_time=base_time,
        effective_from=base_time,
    )
    order_safe = Order(
        tenant_id=tenant_a,
        id="ord_safe",
        customer_id="cus_1",
        order_number="O2",
        order_status=OrderStatus.SHIPPED,
        currency=Currency.USD,
        subtotal_cents=5000,
        tax_cents=200,
        shipping_cents=100,
        total_cents=5300,
        sla_delivery_deadline=future_time,
        event_time=base_time,
        effective_from=base_time,
    )

    shipment_delayed = Shipment(
        tenant_id=tenant_a,
        id="shp_risk_1",
        order_id="ord_risk_1",
        tracking_number="TRK1",
        carrier_id="C1",
        carrier_name="Carrier",
        warehouse_id="WH1",
        origin_region="US-MIDWEST",
        destination_region="US-EAST",
        dispatch_status=DispatchStatus.DELAYED,
        is_delayed=True,
        estimated_delivery_at=future_time,
        event_time=base_time,
        effective_from=base_time,
    )
    shipment_safe = Shipment(
        tenant_id=tenant_a,
        id="shp_safe",
        order_id="ord_safe",
        tracking_number="TRK2",
        carrier_id="C1",
        carrier_name="Carrier",
        warehouse_id="WH1",
        origin_region="US-MIDWEST",
        destination_region="US-EAST",
        dispatch_status=DispatchStatus.IN_TRANSIT,
        is_delayed=False,
        estimated_delivery_at=future_time,
        event_time=base_time,
        effective_from=base_time,
    )

    data = MetricEvaluationDataset(
        orders=[order_delayed, order_safe],
        shipments=[shipment_delayed, shipment_safe],
    )

    res = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-002", tenant_a, data, as_of_time)
    assert res.is_success
    assert res.unwrap().value == 10700


def test_fulfillment_delay_rate_metric(tenant_a, base_time, as_of_time, future_time):
    """METRIC-003: fulfillment_delay_rate calculates ratio of delayed shipments."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    s1 = Shipment(
        tenant_id=tenant_a,
        id="shp_1",
        order_id="ord_1",
        tracking_number="T1",
        carrier_id="C1",
        carrier_name="C",
        warehouse_id="W1",
        origin_region="US",
        destination_region="US",
        dispatch_status=DispatchStatus.DELAYED,
        is_delayed=True,
        estimated_delivery_at=future_time,
        event_time=base_time,
        effective_from=base_time,
    )
    s2 = Shipment(
        tenant_id=tenant_a,
        id="shp_2",
        order_id="ord_2",
        tracking_number="T2",
        carrier_id="C1",
        carrier_name="C",
        warehouse_id="W1",
        origin_region="US",
        destination_region="US",
        dispatch_status=DispatchStatus.DELIVERED,
        is_delayed=False,
        estimated_delivery_at=future_time,
        event_time=base_time,
        effective_from=base_time,
    )

    data = MetricEvaluationDataset(shipments=[s1, s2])
    res = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-003", tenant_a, data, as_of_time)
    assert res.is_success
    assert res.unwrap().value == 0.5000


def test_sla_violation_rate_metric(tenant_a, base_time, as_of_time, future_time):
    """METRIC-004: sla_violation_rate calculates ratio of orders breaching SLA hours."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    delivery_time = UtcDateTime.from_iso("2026-09-04T13:00:00.000000Z")
    as_of = UtcDateTime.from_iso("2026-09-04T15:00:00.000000Z")

    cust = Customer(
        tenant_id=tenant_a,
        id="cus_1",
        name="Acme",
        email="a@a.com",
        segment=CustomerSegment.ENTERPRISE,
        account_tier=AccountTier.TIER_1_PLATINUM,
        billing_country="US",
        contract_mrr_cents=1000,
        currency=Currency.USD,
        status=CustomerStatus.ACTIVE,
        event_time=base_time,
        effective_from=base_time,
    )
    contract = Contract(
        tenant_id=tenant_a,
        id="ctr_1",
        customer_id="cus_1",
        title="Enterprise SLA",
        contract_type=ContractType.ENTERPRISE_SLA,
        document_uri="s3://doc.pdf",
        document_digest="a" * 64,
        event_time=base_time,
        effective_from=base_time,
    )
    clause = ContractClause(
        tenant_id=tenant_a,
        id="cls_1",
        contract_id="ctr_1",
        clause_number="1.0",
        clause_type=ClauseType.DELIVERY_SLA,
        clause_text="Deliver in 2h",
        sla_threshold_hours=2,
        event_time=base_time,
        effective_from=base_time,
    )
    order = Order(
        tenant_id=tenant_a,
        id="ord_1",
        customer_id="cus_1",
        order_number="O1",
        order_status=OrderStatus.DELIVERED,
        currency=Currency.USD,
        subtotal_cents=100,
        tax_cents=10,
        shipping_cents=5,
        total_cents=115,
        sla_delivery_deadline=future_time,
        event_time=base_time,
        effective_from=base_time,
    )
    shipment = Shipment(
        tenant_id=tenant_a,
        id="shp_1",
        order_id="ord_1",
        tracking_number="T1",
        carrier_id="C1",
        carrier_name="C",
        warehouse_id="W1",
        origin_region="US",
        destination_region="US",
        dispatch_status=DispatchStatus.DELIVERED,
        estimated_delivery_at=future_time,
        actual_delivered_at=delivery_time,
        event_time=base_time,
        effective_from=base_time,
    )

    data = MetricEvaluationDataset(
        customers=[cust],
        contracts=[contract],
        contract_clauses=[clause],
        orders=[order],
        shipments=[shipment],
    )

    res = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-004", tenant_a, data, as_of)
    assert res.is_success
    assert res.unwrap().value == 1.0000


def test_payment_failure_rate_metric(tenant_a, base_time, as_of_time):
    """METRIC-005: payment_failure_rate evaluates failed payments ratio."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    p1 = PaymentReference(
        tenant_id=tenant_a,
        id="pay_1",
        order_id="ord_1",
        gateway_provider=GatewayProvider.STRIPE,
        transaction_type=TransactionType.AUTHORIZATION,
        payment_status=PaymentStatus.FAILED,
        amount_cents=1000,
        currency=Currency.USD,
        processed_at=base_time,
        event_time=base_time,
        effective_from=base_time,
    )
    p2 = PaymentReference(
        tenant_id=tenant_a,
        id="pay_2",
        order_id="ord_2",
        gateway_provider=GatewayProvider.STRIPE,
        transaction_type=TransactionType.AUTHORIZATION,
        payment_status=PaymentStatus.SUCCEEDED,
        amount_cents=1000,
        currency=Currency.USD,
        processed_at=base_time,
        event_time=base_time,
        effective_from=base_time,
    )

    data = MetricEvaluationDataset(payment_references=[p1, p2])
    res = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-005", tenant_a, data, as_of_time)
    assert res.is_success
    assert res.unwrap().value == 0.5000


def test_customer_churn_rate_metric(tenant_a, base_time, as_of_time):
    """METRIC-006: customer_churn_rate calculates ratio of churned customers."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    c1 = Customer(
        tenant_id=tenant_a,
        id="cus_1",
        name="C1",
        email="c1@c.com",
        segment=CustomerSegment.SMB,
        account_tier=AccountTier.TIER_3_STANDARD,
        billing_country="US",
        contract_mrr_cents=500,
        currency=Currency.USD,
        status=CustomerStatus.CHURNED,
        event_time=base_time,
        effective_from=base_time,
    )
    c2 = Customer(
        tenant_id=tenant_a,
        id="cus_2",
        name="C2",
        email="c2@c.com",
        segment=CustomerSegment.SMB,
        account_tier=AccountTier.TIER_3_STANDARD,
        billing_country="US",
        contract_mrr_cents=500,
        currency=Currency.USD,
        status=CustomerStatus.ACTIVE,
        event_time=base_time,
        effective_from=base_time,
    )

    data = MetricEvaluationDataset(customers=[c1, c2])
    res = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-006", tenant_a, data, as_of_time)
    assert res.is_success
    assert res.unwrap().value == 0.5000


def test_volume_metrics(tenant_a, base_time, as_of_time, future_time):
    """METRIC-007, METRIC-008, METRIC-009 calculate correct integer volumes."""
    from revpilot.modules.analytics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
    )
    order = Order(
        tenant_id=tenant_a,
        id="ord_1",
        customer_id="cus_1",
        order_number="O1",
        order_status=OrderStatus.PLACED,
        currency=Currency.USD,
        subtotal_cents=100,
        tax_cents=10,
        shipping_cents=5,
        total_cents=115,
        sla_delivery_deadline=future_time,
        event_time=base_time,
        effective_from=base_time,
    )
    shipment = Shipment(
        tenant_id=tenant_a,
        id="shp_1",
        order_id="ord_1",
        tracking_number="T1",
        carrier_id="C1",
        carrier_name="C",
        warehouse_id="W1",
        origin_region="US",
        destination_region="US",
        dispatch_status=DispatchStatus.IN_TRANSIT,
        estimated_delivery_at=future_time,
        event_time=base_time,
        effective_from=base_time,
    )
    ticket = SupportTicket(
        tenant_id=tenant_a,
        id="tkt_1",
        customer_id="cus_1",
        ticket_number="TK1",
        topic=TicketTopic.GENERAL_SUPPORT,
        priority=TicketPriority.P3_NORMAL,
        status=TicketStatus.OPEN,
        subject="Help",
        transcript_text="Help me",
        event_time=base_time,
        effective_from=base_time,
    )

    data = MetricEvaluationDataset(
        orders=[order],
        shipments=[shipment],
        support_tickets=[ticket],
    )

    res_ord = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-007", tenant_a, data, as_of_time)
    assert res_ord.is_success
    assert res_ord.unwrap().value == 1

    res_shp = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-008", tenant_a, data, as_of_time)
    assert res_shp.is_success
    assert res_shp.unwrap().value == 1

    res_tkt = CANONICAL_METRIC_REGISTRY.evaluate("METRIC-009", tenant_a, data, as_of_time)
    assert res_tkt.is_success
    assert res_tkt.unwrap().value == 1
