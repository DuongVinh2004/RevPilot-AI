"""
RevPilot AI — Noise Suppression and Small-Sample Guardrails Unit Tests (Phase 02)
Verifies AC-P02-004-03, ANOMALY-LOCALIZATION-SPEC.md §2.2, §2.3 (sample size filtering, FDR correction, fail-closed behavior).
"""

from __future__ import annotations
import sys
from datetime import timedelta
import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.monetary import Currency
from revpilot.shared.context import TenantContext
from revpilot.modules.canonical import (
    Order,
    OrderStatus,
    Shipment,
    DispatchStatus,
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
def alpha_context(tenant_alpha) -> TenantContext:
    return TenantContext(tenant_id=tenant_alpha, organization_id=OrganizationId("org_alpha"))


@pytest.fixture
def base_window() -> tuple[UtcDateTime, UtcDateTime, UtcDateTime]:
    start = UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z")
    end = UtcDateTime.from_iso("2026-02-22T23:59:59.000000Z")
    as_of = UtcDateTime.from_iso("2026-02-23T00:00:00.000000Z")
    return start, end, as_of


# =============================================================================
# AC-P02-004-03: Small-Sample Slices Excluded (< 30 observations)
# =============================================================================

def test_slices_under_thirty_excluded_from_top_contributors(
    tenant_alpha, alpha_context, base_window
):
    """AC-P02-004-03: Slices with sample size < 30 are excluded from top contributors and counted in suppressed_segments_count."""
    from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
    from revpilot.modules.analytics.localization import AnomalyLocalizer, AnomalyRecord
    start, end, as_of = base_window

    orders: list[Order] = []
    shipments: list[Shipment] = []

    # Valid segment: CARRIER_LARGE (100 orders, 10 cancelled = 10%)
    for i in range(100):
        o_id = f"ord_large_{i}"
        dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i % 168))
        orders.append(
            Order(
                tenant_id=tenant_alpha,
                id=o_id,
                customer_id="cust_001",
                order_number=f"ORD-LRG-{i}",
                order_status=OrderStatus.CANCELLED if i < 10 else OrderStatus.DELIVERED,
                currency=Currency.USD,
                subtotal_cents=1000,
                tax_cents=100,
                shipping_cents=50,
                total_cents=1150,
                sla_delivery_deadline=dt,
                event_time=dt,
                effective_from=dt,
                ingested_at=dt,
                cancelled_at=dt if i < 10 else None,
            )
        )
        shipments.append(
            Shipment(
                tenant_id=tenant_alpha,
                id=f"shp_large_{i}",
                order_id=o_id,
                tracking_number=f"TRKLRG{i}",
                carrier_id="CARRIER_LARGE",
                carrier_name="Carrier Large",
                warehouse_id="WH-01",
                origin_region="US-MIDWEST",
                destination_region="US-MIDWEST",
                dispatch_status=DispatchStatus.DELIVERED,
                estimated_delivery_at=dt,
                event_time=dt,
                effective_from=dt,
                ingested_at=dt,
            )
        )

    # 3 Small segments (< 30 orders each):
    # CARRIER_TINY_1: 29 orders
    # CARRIER_TINY_2: 15 orders
    # CARRIER_TINY_3: 5 orders
    tiny_counts = [("CARRIER_TINY_1", 29), ("CARRIER_TINY_2", 15), ("CARRIER_TINY_3", 5)]
    for c_id, count in tiny_counts:
        for i in range(count):
            o_id = f"ord_{c_id}_{i}"
            dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i % 168))
            orders.append(
                Order(
                    tenant_id=tenant_alpha,
                    id=o_id,
                    customer_id="cust_001",
                    order_number=f"ORD-{c_id}-{i}",
                    order_status=OrderStatus.CANCELLED,
                    currency=Currency.USD,
                    subtotal_cents=1000,
                    tax_cents=100,
                    shipping_cents=50,
                    total_cents=1150,
                    sla_delivery_deadline=dt,
                    event_time=dt,
                    effective_from=dt,
                    ingested_at=dt,
                    cancelled_at=dt,
                )
            )
            shipments.append(
                Shipment(
                    tenant_id=tenant_alpha,
                    id=f"shp_{c_id}_{i}",
                    order_id=o_id,
                    tracking_number=f"TRK{c_id}{i}",
                    carrier_id=c_id,
                    carrier_name=c_id,
                    warehouse_id="WH-01",
                    origin_region="US-MIDWEST",
                    destination_region="US-MIDWEST",
                    dispatch_status=DispatchStatus.DELIVERED,
                    estimated_delivery_at=dt,
                    event_time=dt,
                    effective_from=dt,
                    ingested_at=dt,
                )
            )

    dataset = MetricEvaluationDataset(orders=tuple(orders), shipments=tuple(shipments))
    anomaly = AnomalyRecord(
        id="anm_sample_test",
        tenant_id=tenant_alpha,
        metric_id="METRIC-001",
        observation_window_start=start,
        observation_window_end=end,
        as_of_time=as_of,
        actual_value=0.0840,
        expected_value=0.0180,
    )

    localizer = AnomalyLocalizer(dataset=dataset)
    res = localizer.localize(anomaly, dimension="carrier_id", tenant_context=alpha_context)

    assert res.is_success
    loc = res.unwrap()

    # AC-P02-004-03: small slices are excluded
    ranked_carriers = [s.segment_value for s in loc.top_contributing_segments]
    assert "CARRIER_LARGE" in ranked_carriers
    assert "CARRIER_TINY_1" not in ranked_carriers
    assert "CARRIER_TINY_2" not in ranked_carriers
    assert "CARRIER_TINY_3" not in ranked_carriers
    assert loc.suppressed_segments_count == 3


# =============================================================================
# Fail-Closed when All Slices Under Threshold (< 30)
# =============================================================================

def test_all_slices_under_threshold_fails_closed(
    tenant_alpha, alpha_context, base_window
):
    """When all slices have < 30 observations, localization fails closed with INSUFFICIENT_DATA_FOR_LOCALIZATION (HTTP 422)."""
    from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
    from revpilot.modules.analytics.localization import (
        AnomalyLocalizer,
        AnomalyRecord,
        InsufficientDataForLocalizationError,
    )
    start, end, as_of = base_window

    orders: list[Order] = []
    shipments: list[Shipment] = []

    # 2 carriers, each with 20 orders (< 30)
    for c_idx in (1, 2):
        c_id = f"CARRIER_SMALL_{c_idx}"
        for i in range(20):
            o_id = f"ord_small_{c_idx}_{i}"
            dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i))
            orders.append(
                Order(
                    tenant_id=tenant_alpha,
                    id=o_id,
                    customer_id="cust_001",
                    order_number=f"ORD-SML-{c_idx}-{i}",
                    order_status=OrderStatus.CANCELLED if i % 2 == 0 else OrderStatus.DELIVERED,
                    currency=Currency.USD,
                    subtotal_cents=1000,
                    tax_cents=100,
                    shipping_cents=50,
                    total_cents=1150,
                    sla_delivery_deadline=dt,
                    event_time=dt,
                    effective_from=dt,
                    ingested_at=dt,
                )
            )
            shipments.append(
                Shipment(
                    tenant_id=tenant_alpha,
                    id=f"shp_small_{c_idx}_{i}",
                    order_id=o_id,
                    tracking_number=f"TRKSML{c_idx}{i}",
                    carrier_id=c_id,
                    carrier_name=c_id,
                    warehouse_id="WH-01",
                    origin_region="US-MIDWEST",
                    destination_region="US-MIDWEST",
                    dispatch_status=DispatchStatus.DELIVERED,
                    estimated_delivery_at=dt,
                    event_time=dt,
                    effective_from=dt,
                    ingested_at=dt,
                )
            )

    dataset = MetricEvaluationDataset(orders=tuple(orders), shipments=tuple(shipments))
    anomaly = AnomalyRecord(
        id="anm_insufficient_samples",
        tenant_id=tenant_alpha,
        metric_id="METRIC-001",
        observation_window_start=start,
        observation_window_end=end,
        as_of_time=as_of,
        actual_value=0.5000,
        expected_value=0.0180,
    )

    localizer = AnomalyLocalizer(dataset=dataset)
    res = localizer.localize(anomaly, dimension="carrier_id", tenant_context=alpha_context)

    assert res.is_failure
    err = res.unwrap_error()
    assert isinstance(err, InsufficientDataForLocalizationError)
    assert err.code == "INSUFFICIENT_DATA_FOR_LOCALIZATION"
    assert err.http_status == 422
    assert err.details.get("suppressed_segments_count") == 2


# =============================================================================
# Benjamini-Hochberg FDR Multiple Testing Control
# =============================================================================

def test_benjamini_hochberg_fdr_control(tenant_alpha, alpha_context, base_window):
    """Verifies Benjamini-Hochberg FDR control at alpha = 0.05 separates real signal from benign variations."""
    from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
    from revpilot.modules.analytics.localization import AnomalyLocalizer, AnomalyRecord
    start, end, as_of = base_window

    orders: list[Order] = []
    shipments: list[Shipment] = []

    # Segment A: Surge anomaly (500 orders, 42 cancelled = 8.4% vs expected 1.8%) -> strong signal
    for i in range(500):
        o_id = f"ord_a_{i}"
        dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i % 168))
        orders.append(
            Order(
                tenant_id=tenant_alpha,
                id=o_id,
                customer_id="cust_001",
                order_number=f"ORD-A-{i}",
                order_status=OrderStatus.CANCELLED if i < 42 else OrderStatus.DELIVERED,
                currency=Currency.USD,
                subtotal_cents=1000,
                tax_cents=100,
                shipping_cents=50,
                total_cents=1150,
                sla_delivery_deadline=dt,
                event_time=dt,
                effective_from=dt,
                ingested_at=dt,
            )
        )
        shipments.append(
            Shipment(
                tenant_id=tenant_alpha,
                id=f"shp_a_{i}",
                order_id=o_id,
                tracking_number=f"TRKA{i}",
                carrier_id="CARRIER_ANOMALOUS",
                carrier_name="Carrier Anomalous",
                warehouse_id="WH-01",
                origin_region="US-MIDWEST",
                destination_region="US-MIDWEST",
                dispatch_status=DispatchStatus.DELIVERED,
                estimated_delivery_at=dt,
                event_time=dt,
                effective_from=dt,
                ingested_at=dt,
            )
        )

    # Segment B: Baseline control (500 orders, 9 cancelled = 1.8% vs expected 1.8%) -> null signal
    for i in range(500):
        o_id = f"ord_b_{i}"
        dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i % 168))
        orders.append(
            Order(
                tenant_id=tenant_alpha,
                id=o_id,
                customer_id="cust_001",
                order_number=f"ORD-B-{i}",
                order_status=OrderStatus.CANCELLED if i < 9 else OrderStatus.DELIVERED,
                currency=Currency.USD,
                subtotal_cents=1000,
                tax_cents=100,
                shipping_cents=50,
                total_cents=1150,
                sla_delivery_deadline=dt,
                event_time=dt,
                effective_from=dt,
                ingested_at=dt,
            )
        )
        shipments.append(
            Shipment(
                tenant_id=tenant_alpha,
                id=f"shp_b_{i}",
                order_id=o_id,
                tracking_number=f"TRKB{i}",
                carrier_id="CARRIER_CONTROL",
                carrier_name="Carrier Control",
                warehouse_id="WH-01",
                origin_region="US-MIDWEST",
                destination_region="US-MIDWEST",
                dispatch_status=DispatchStatus.DELIVERED,
                estimated_delivery_at=dt,
                event_time=dt,
                effective_from=dt,
                ingested_at=dt,
            )
        )

    dataset = MetricEvaluationDataset(orders=tuple(orders), shipments=tuple(shipments))
    anomaly = AnomalyRecord(
        id="anm_fdr_test",
        tenant_id=tenant_alpha,
        metric_id="METRIC-001",
        observation_window_start=start,
        observation_window_end=end,
        as_of_time=as_of,
        actual_value=0.0840,
        expected_value=0.0180,
    )

    localizer = AnomalyLocalizer(dataset=dataset)
    res = localizer.localize(anomaly, dimension="carrier_id", tenant_context=alpha_context)

    assert res.is_success
    loc = res.unwrap()
    seg_by_val = {s.segment_value: s for s in loc.top_contributing_segments}

    # CARRIER_ANOMALOUS should be FDR rejected (true anomaly)
    assert "CARRIER_ANOMALOUS" in seg_by_val
    assert seg_by_val["CARRIER_ANOMALOUS"].fdr_rejected is True
    assert seg_by_val["CARRIER_ANOMALOUS"].p_value < 0.01

    # CARRIER_CONTROL should NOT be FDR rejected
    assert "CARRIER_CONTROL" in seg_by_val
    assert seg_by_val["CARRIER_CONTROL"].fdr_rejected is False
    assert seg_by_val["CARRIER_CONTROL"].p_value >= 0.05
