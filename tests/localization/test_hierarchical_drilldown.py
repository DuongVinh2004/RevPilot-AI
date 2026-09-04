"""
RevPilot AI — Hierarchical Anomaly Drill-Down Unit and Contract Tests (Phase 02)
Verifies AC-P02-004-02, ANOMALY-LOCALIZATION-SPEC.md §4 (two-level hierarchical drill-down, depth = 2 stop rule).
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


@pytest.fixture
def hierarchical_dataset(tenant_alpha, base_window):
    """
    Dataset where CARRIER_REGIONAL_LOGISTICS has 500 orders:
    - WH-MIDWEST-01: 300 orders, 38 cancelled (~12.67%, baseline ~1.8% -> ~32.6 excess).
    - WH-WEST-01: 200 orders, 4 cancelled (~2.0%, baseline ~1.8% -> ~0.4 excess).
    Excess volume is ~98.8% concentrated in WH-MIDWEST-01.
    """
    from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
    start, end, as_of = base_window

    orders: list[Order] = []
    shipments: list[Shipment] = []

    # 1. CARRIER_REGIONAL_LOGISTICS
    for i in range(500):
        o_id = f"ord_reg_{i:04d}"
        if i < 300:
            wh_id = "WH-MIDWEST-01"
            is_cancelled = (i < 38)
        else:
            wh_id = "WH-WEST-01"
            is_cancelled = (300 <= i < 304)

        event_dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i % 168))
        orders.append(
            Order(
                tenant_id=tenant_alpha,
                id=o_id,
                customer_id=f"cust_{i % 50:03d}",
                order_number=f"ORD-REG-{i:04d}",
                order_status=OrderStatus.CANCELLED if is_cancelled else OrderStatus.DELIVERED,
                currency=Currency.USD,
                subtotal_cents=1000,
                tax_cents=100,
                shipping_cents=50,
                total_cents=1150,
                sla_delivery_deadline=event_dt,
                event_time=event_dt,
                effective_from=event_dt,
                ingested_at=event_dt,
                cancelled_at=event_dt if is_cancelled else None,
            )
        )
        shipments.append(
            Shipment(
                tenant_id=tenant_alpha,
                id=f"shp_reg_{i:04d}",
                order_id=o_id,
                tracking_number=f"TRKREG{i:06d}",
                carrier_id="CARRIER_REGIONAL_LOGISTICS",
                carrier_name="Regional Express",
                warehouse_id=wh_id,
                origin_region="US-MIDWEST" if wh_id == "WH-MIDWEST-01" else "US-WEST",
                destination_region="US-MIDWEST",
                dispatch_status=DispatchStatus.DELIVERED,
                estimated_delivery_at=event_dt,
                event_time=event_dt,
                effective_from=event_dt,
                ingested_at=event_dt,
            )
        )

    # 2. CARRIER_AIR_EXPRESS (Control): 500 orders, 9 cancelled (~1.8%)
    for i in range(500):
        o_id = f"ord_air_{i:04d}"
        is_cancelled = (i < 9)
        wh_id = "WH-MIDWEST-01" if i < 300 else "WH-WEST-01"
        event_dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i % 168))
        orders.append(
            Order(
                tenant_id=tenant_alpha,
                id=o_id,
                customer_id=f"cust_{i % 50:03d}",
                order_number=f"ORD-AIR-{i:04d}",
                order_status=OrderStatus.CANCELLED if is_cancelled else OrderStatus.DELIVERED,
                currency=Currency.USD,
                subtotal_cents=1000,
                tax_cents=100,
                shipping_cents=50,
                total_cents=1150,
                sla_delivery_deadline=event_dt,
                event_time=event_dt,
                effective_from=event_dt,
                ingested_at=event_dt,
                cancelled_at=event_dt if is_cancelled else None,
            )
        )
        shipments.append(
            Shipment(
                tenant_id=tenant_alpha,
                id=f"shp_air_{i:04d}",
                order_id=o_id,
                tracking_number=f"TRKAIR{i:06d}",
                carrier_id="CARRIER_AIR_EXPRESS",
                carrier_name="Air Express",
                warehouse_id=wh_id,
                origin_region="US-WEST",
                destination_region="US-EAST",
                dispatch_status=DispatchStatus.DELIVERED,
                estimated_delivery_at=event_dt,
                event_time=event_dt,
                effective_from=event_dt,
                ingested_at=event_dt,
            )
        )

    return MetricEvaluationDataset(orders=tuple(orders), shipments=tuple(shipments))


@pytest.fixture
def midwest_anomaly(tenant_alpha, base_window):
    from revpilot.modules.analytics.localization import AnomalyRecord
    start, end, as_of = base_window
    return AnomalyRecord(
        id="anm_midwest_hierarchical_001",
        tenant_id=tenant_alpha,
        metric_id="METRIC-001",
        observation_window_start=start,
        observation_window_end=end,
        as_of_time=as_of,
        actual_value=0.0840,
        expected_value=0.0180,
    )


# =============================================================================
# AC-P02-004-02: Two-Level Hierarchical Drill-Down Pinpointing Facility
# =============================================================================

def test_hierarchical_drilldown_pinpoints_warehouse(
    hierarchical_dataset, midwest_anomaly, alpha_context
):
    """AC-P02-004-02: Two-level drill-down pinpoints WH-MIDWEST-01 within the carrier slice."""
    from revpilot.modules.analytics.localization import AnomalyLocalizer

    localizer = AnomalyLocalizer(dataset=hierarchical_dataset)
    res = localizer.localize(
        anomaly=midwest_anomaly,
        dimension="carrier_id",
        secondary_dimension="warehouse_id",
        tenant_context=alpha_context,
    )

    assert res.is_success, f"Hierarchical drill-down failed: {res.unwrap_error() if res.is_failure else ''}"
    loc = res.unwrap()

    # Level 1: Carrier
    assert len(loc.top_contributing_segments) >= 1
    carrier_top = loc.top_contributing_segments[0]
    assert carrier_top.rank == 1
    assert carrier_top.segment_value == "CARRIER_REGIONAL_LOGISTICS"
    assert carrier_top.contribution_pct >= 70.0

    # Level 2: Warehouse restricted to CARRIER_REGIONAL_LOGISTICS
    assert loc.secondary_localization is not None
    sec = loc.secondary_localization
    assert sec.dimension == "warehouse_id"
    assert len(sec.top_contributing_segments) >= 1

    wh_top = sec.top_contributing_segments[0]
    assert wh_top.rank == 1
    assert wh_top.segment_value == "WH-MIDWEST-01"
    assert wh_top.contribution_pct >= 90.0, f"Expected WH contribution >= 90%, got {wh_top.contribution_pct}%"
    assert wh_top.fdr_rejected is True

    # Summary contains both levels and associative disclaimer
    assert "CARRIER_REGIONAL_LOGISTICS" in loc.association_summary
    assert "WH-MIDWEST-01" in loc.association_summary
    assert "This reflects an observed association; causal investigation is required to establish underlying root causes." in loc.association_summary


def test_hierarchical_drilldown_depth_stop_rule(
    hierarchical_dataset, midwest_anomaly, alpha_context
):
    """ANOMALY-LOCALIZATION-SPEC.md §4: Recursion stops at depth = 2 to prevent combinatorial explosion."""
    from revpilot.modules.analytics.localization import AnomalyLocalizer

    localizer = AnomalyLocalizer(dataset=hierarchical_dataset)
    res = localizer.localize(
        anomaly=midwest_anomaly,
        dimension="carrier_id",
        secondary_dimension="warehouse_id",
        tenant_context=alpha_context,
    )

    assert res.is_success
    loc = res.unwrap()
    assert loc.secondary_localization is not None
    # Level 2 must not have a Level 3 child
    assert loc.secondary_localization.secondary_localization is None


def test_direct_drilldown_with_carrier_scope(
    hierarchical_dataset, midwest_anomaly, alpha_context
):
    """Direct single-dimension drill-down on warehouse_id when scoped to CARRIER_REGIONAL_LOGISTICS."""
    from revpilot.modules.analytics.localization import AnomalyLocalizer, AnomalyRecord

    scoped_anomaly = AnomalyRecord(
        id=midwest_anomaly.id,
        tenant_id=midwest_anomaly.tenant_id,
        metric_id=midwest_anomaly.metric_id,
        observation_window_start=midwest_anomaly.observation_window_start,
        observation_window_end=midwest_anomaly.observation_window_end,
        as_of_time=midwest_anomaly.as_of_time,
        actual_value=midwest_anomaly.actual_value,
        expected_value=midwest_anomaly.expected_value,
        affected_scope={"carrier_id": "CARRIER_REGIONAL_LOGISTICS"},
    )

    localizer = AnomalyLocalizer(dataset=hierarchical_dataset)
    res = localizer.localize(
        anomaly=scoped_anomaly,
        dimension="warehouse_id",
        tenant_context=alpha_context,
    )

    assert res.is_success
    loc = res.unwrap()
    assert loc.top_contributing_segments[0].segment_value == "WH-MIDWEST-01"
    assert loc.top_contributing_segments[0].contribution_pct >= 90.0


def test_identical_primary_and_secondary_dimension_rejected(
    hierarchical_dataset, midwest_anomaly, alpha_context
):
    """Secondary dimension cannot be identical to primary dimension (HTTP 400)."""
    from revpilot.modules.analytics.localization import AnomalyLocalizer, UnsupportedDimensionError

    localizer = AnomalyLocalizer(dataset=hierarchical_dataset)
    res = localizer.localize(
        anomaly=midwest_anomaly,
        dimension="carrier_id",
        secondary_dimension="carrier_id",
        tenant_context=alpha_context,
    )

    assert res.is_failure
    err = res.unwrap_error()
    assert isinstance(err, UnsupportedDimensionError)
    assert err.code == "UNSUPPORTED_DIMENSION"
    assert err.http_status == 400
