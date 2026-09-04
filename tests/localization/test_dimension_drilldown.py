"""
RevPilot AI — Dimensional Drill-Down Unit and Contract Tests (Phase 02)
Verifies AC-P02-004-01, AC-P02-004-04, INV-AI-001, INV-TEN-001, and FR-INV-004.
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
    Customer,
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
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta")


@pytest.fixture
def alpha_context(tenant_alpha) -> TenantContext:
    return TenantContext(tenant_id=tenant_alpha, organization_id=OrganizationId("org_alpha"))


@pytest.fixture
def beta_context(tenant_beta) -> TenantContext:
    return TenantContext(tenant_id=tenant_beta, organization_id=OrganizationId("org_beta"))


@pytest.fixture
def base_window() -> tuple[UtcDateTime, UtcDateTime, UtcDateTime]:
    start = UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z")
    end = UtcDateTime.from_iso("2026-02-22T23:59:59.000000Z")
    as_of = UtcDateTime.from_iso("2026-02-23T00:00:00.000000Z")
    return start, end, as_of


@pytest.fixture
def midwest_dataset(tenant_alpha, base_window):
    from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
    start, end, as_of = base_window

    orders: list[Order] = []
    shipments: list[Shipment] = []

    # 1. CARRIER_REGIONAL_LOGISTICS: 500 orders, 42 cancelled (8.4%)
    for i in range(500):
        o_id = f"ord_reg_{i:04d}"
        is_cancelled = (i < 42)
        wh_id = "WH-MIDWEST-01" if i < 300 else "WH-WEST-01"
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
                origin_region="US-MIDWEST",
                destination_region="US-MIDWEST",
                dispatch_status=DispatchStatus.DELIVERED,
                estimated_delivery_at=event_dt,
                event_time=event_dt,
                effective_from=event_dt,
                ingested_at=event_dt,
            )
        )

    # 2. CARRIER_AIR_EXPRESS: 500 orders, 9 cancelled (1.8%)
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

    # 3. Suppressed carriers: 4 carriers with 5 orders each (< 30 observations)
    for c_idx in range(1, 5):
        c_name = f"CARRIER_LOCAL_{c_idx}"
        for i in range(5):
            o_id = f"ord_loc_{c_idx}_{i}"
            event_dt = UtcDateTime.from_datetime(start.value + timedelta(hours=i * 2))
            orders.append(
                Order(
                    tenant_id=tenant_alpha,
                    id=o_id,
                    customer_id="cust_001",
                    order_number=f"ORD-LOC-{c_idx}-{i}",
                    order_status=OrderStatus.DELIVERED,
                    currency=Currency.USD,
                    subtotal_cents=1000,
                    tax_cents=100,
                    shipping_cents=50,
                    total_cents=1150,
                    sla_delivery_deadline=event_dt,
                    event_time=event_dt,
                    effective_from=event_dt,
                    ingested_at=event_dt,
                )
            )
            shipments.append(
                Shipment(
                    tenant_id=tenant_alpha,
                    id=f"shp_loc_{c_idx}_{i}",
                    order_id=o_id,
                    tracking_number=f"TRKLOC{c_idx}{i}",
                    carrier_id=c_name,
                    carrier_name=c_name,
                    warehouse_id="WH-MIDWEST-01",
                    origin_region="US-MIDWEST",
                    destination_region="US-MIDWEST",
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
        id="anm_midwest_disruption_001",
        tenant_id=tenant_alpha,
        metric_id="METRIC-001",
        observation_window_start=start,
        observation_window_end=end,
        as_of_time=as_of,
        actual_value=0.0840,
        expected_value=0.0180,
    )


# =============================================================================
# AC-P02-004-01: Midwest Carrier Drill-Down
# =============================================================================

def test_carrier_drilldown_identifies_regional_logistics_top_contributor(
    midwest_dataset, midwest_anomaly, alpha_context
):
    """AC-P02-004-01: Single-dimension drill-down on Midwest cancellation anomaly identifies CARRIER_REGIONAL_LOGISTICS as rank 1 with contribution >= 70%."""
    from revpilot.modules.analytics.localization import AnomalyLocalizer

    localizer = AnomalyLocalizer(dataset=midwest_dataset)
    res = localizer.localize(
        anomaly=midwest_anomaly,
        dimension="carrier_id",
        tenant_context=alpha_context,
    )

    assert res.is_success, f"Localization failed: {res.failure() if res.is_failure else ''}"
    loc_result = res.unwrap()

    assert len(loc_result.top_contributing_segments) >= 1
    top = loc_result.top_contributing_segments[0]

    assert top.rank == 1
    assert top.segment_value == "CARRIER_REGIONAL_LOGISTICS"
    assert top.contribution_pct >= 70.0, f"Expected contribution >= 70%, got {top.contribution_pct}%"
    assert top.fdr_rejected is True
    assert top.actual_value == pytest.approx(0.084, abs=0.005)
    assert top.sample_size == 500
    assert top.excess_volume > 0.0
    assert loc_result.suppressed_segments_count == 4
    assert loc_result.diagnostic_status == "ACTIONABLE_FOR_INVESTIGATION"


# =============================================================================
# Dimension Allowlist Rejection (FR-INV-004)
# =============================================================================

def test_unsupported_dimension_rejected(midwest_dataset, midwest_anomaly, alpha_context):
    """Slicing on unapproved dimension returns UnsupportedDimensionError (HTTP 400, UNSUPPORTED_DIMENSION)."""
    from revpilot.modules.analytics.localization import AnomalyLocalizer, UnsupportedDimensionError

    localizer = AnomalyLocalizer(dataset=midwest_dataset)
    res = localizer.localize(
        anomaly=midwest_anomaly,
        dimension="fraud_risk_score",
        tenant_context=alpha_context,
    )

    assert res.is_failure
    err = res.unwrap_error()
    assert isinstance(err, UnsupportedDimensionError)
    assert err.code == "UNSUPPORTED_DIMENSION"
    assert err.http_status == 400


# =============================================================================
# AC-P02-004-04: Non-Causal Associative Disclaimer (INV-AI-001)
# =============================================================================

def test_association_summary_disclaims_causality(midwest_dataset, midwest_anomaly, alpha_context):
    """AC-P02-004-04: Localization output contains associative disclaimer without asserting root causation."""
    from revpilot.modules.analytics.localization import AnomalyLocalizer

    localizer = AnomalyLocalizer(dataset=midwest_dataset)
    res = localizer.localize(
        anomaly=midwest_anomaly,
        dimension="carrier_id",
        tenant_context=alpha_context,
    )

    assert res.is_success
    loc_result = res.unwrap()
    summary = loc_result.association_summary

    # Mandatory associative disclaimer present
    assert "This reflects an observed association; causal investigation is required to establish underlying root causes." in summary
    assert "concentrated in" in summary

    # Strict ban on causal claims (INV-AI-001)
    summary_lower = summary.lower()
    forbidden_phrases = [
        "caused by",
        "root cause is",
        "root cause:",
        "proven cause",
        "causal attribution",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in summary_lower, f"Forbidden causal phrase '{phrase}' detected in summary: {summary}"


# =============================================================================
# Cross-Tenant Boundary Rejection (INV-TEN-001)
# =============================================================================

def test_cross_tenant_localization_rejected(midwest_dataset, midwest_anomaly, beta_context):
    """INV-TEN-001: Caller tenant cannot localize another tenant's anomaly (HTTP 403)."""
    from revpilot.modules.analytics.localization import AnomalyLocalizer

    localizer = AnomalyLocalizer(dataset=midwest_dataset)
    res = localizer.localize(
        anomaly=midwest_anomaly,
        dimension="carrier_id",
        tenant_context=beta_context,
    )

    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "TENANCY_VIOLATION"
    assert err.http_status == 403
