"""
RevPilot AI — Phase 02 Detection & Analytics Exit-Gate Verification Suite
Verifies execution/MASTER-ROADMAP.md §Phase-02, AC-P02-006-01 through AC-P02-006-05.
Enforces INV-DATA-001, INV-DATA-002, INV-AUD-001, INV-TEN-001, INV-AI-001, and NFR-AI-004.
"""

from __future__ import annotations
import os
import sys
import tempfile
from datetime import timedelta
from decimal import Decimal
import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.monetary import Currency
from revpilot.modules.canonical import (
    Customer,
    Order,
    OrderStatus,
    Shipment,
    DispatchStatus,
)
from revpilot.modules.benchmark.ground_truth import (
    GroundTruthIncident,
    EvaluationGroundTruthStore,
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
def alpha_tenant_context(tenant_alpha: TenantId) -> TenantContext:
    return TenantContext(tenant_id=tenant_alpha, organization_id=OrganizationId("org_alpha"))


@pytest.fixture
def alpha_principal_context(tenant_alpha: TenantId) -> PrincipalContext:
    return PrincipalContext(
        principal_id=PrincipalId("usr_analyst_jane"),
        tenant_id=tenant_alpha,
        is_system=False,
    )


@pytest.fixture
def base_date() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-01-01T00:00:00.000000Z")


@pytest.fixture
def midwest_incident(tenant_alpha, base_date) -> GroundTruthIncident:
    start_dt = base_date.value
    return GroundTruthIncident(
        tenant_id=tenant_alpha,
        incident_id="INC-SYNTH-TRUCK-001",
        scenario_name="Midwest Regional Carrier Disruption",
        causal_start_time=UtcDateTime.from_datetime(start_dt + timedelta(days=44, hours=8)),
        causal_end_time=UtcDateTime.from_datetime(start_dt + timedelta(days=51, hours=23, minutes=59, seconds=59)),
        primary_root_cause="CARRIER_CAPACITY_COLLAPSE",
        affected_facility_id="WH-MIDWEST-01",
        affected_carrier_id="CARRIER_REGIONAL_LOGISTICS",
        true_ate_cancellation_rate_delta=0.0660,
        true_delayed_shipment_count=42,
        true_revenue_at_risk_cents=4500000,
        competing_hypotheses=[],
    )


@pytest.fixture
def midwest_60day_series() -> list[float]:
    """
    Simulated 60-day cancellation rate series for tnt_alpha Midwest cohort:
    - Days 1 to 44: baseline ~ 1.8% (0.0180) with weekly seasonality.
    - Days 45 to 52: disrupted ~ 8.4% (0.0840) (+6.6% surge).
    - Days 53 to 60: recovered baseline ~ 1.8% (0.0180).
    """
    seasonal_noise = [0.000, 0.001, -0.001, 0.002, 0.001, -0.002, 0.000]
    series: list[float] = []

    for d in range(1, 61):
        noise = seasonal_noise[(d - 1) % 7]
        if 45 <= d <= 52:
            series.append(round(0.0840 + noise, 4))
        else:
            series.append(round(0.0180 + noise, 4))

    return series


@pytest.fixture
def midwest_localization_dataset(tenant_alpha):
    from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
    start = UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z")

    orders: list[Order] = []
    shipments: list[Shipment] = []

    # 1. CARRIER_REGIONAL_LOGISTICS: 500 orders, 42 cancelled (8.4%)
    for i in range(500):
        o_id = f"ord_reg_{i:04d}"
        is_cancelled = (i < 42)
        # 38 of 42 cancellations in WH-MIDWEST-01 (90.5%)
        if is_cancelled:
            wh_id = "WH-MIDWEST-01" if i < 38 else "WH-WEST-01"
        else:
            wh_id = "WH-MIDWEST-01" if i < 250 else "WH-WEST-01"

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
        wh_id = "WH-MIDWEST-01" if i < 250 else "WH-WEST-01"
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
                origin_region="US-MIDWEST",
                destination_region="US-MIDWEST",
                dispatch_status=DispatchStatus.DELIVERED,
                estimated_delivery_at=event_dt,
                event_time=event_dt,
                effective_from=event_dt,
                ingested_at=event_dt,
            )
        )

    return MetricEvaluationDataset(
        customers=[],
        orders=orders,
        order_lines=[],
        shipments=shipments,
        support_tickets=[],
        maintenance_events=[],
        contracts=[],
        contract_clauses=[],
        payment_references=[],
    )


# =============================================================================
# Exit Gate 1: Metric Service MVP Aggregation and Anti-Leakage
# =============================================================================

def test_gate_all_nine_metrics_evaluate_via_metric_service(
    alpha_tenant_context, midwest_localization_dataset
):
    """
    Verify MetricService queries all 9 canonical metrics without error or temporal leakage.
    Enforces FR-DET-001 and INV-DATA-001.
    """
    from revpilot.modules.analytics.metric_service import MetricService
    from revpilot.modules.analytics.schemas import MetricQueryRequest, TimeWindow

    metric_service = MetricService()
    start = UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z")
    end = UtcDateTime.from_iso("2026-02-22T23:59:59.000000Z")

    all_metrics = [
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

    for m_id in all_metrics:
        req = MetricQueryRequest(
            metric_id=m_id,
            metric_version="1.0.0",
            time_window=TimeWindow(start_time=start, end_time=end),
            grain="AS_OF_SNAPSHOT",
            as_of_time=end,
        )
        res = metric_service.query(req, alpha_tenant_context, dataset=midwest_localization_dataset)
        assert res.is_success, f"MetricService evaluation failed for {m_id}: {res.unwrap_error()}"
        resp = res.unwrap()
        assert resp.metric_name == m_id
        assert resp.tenant_id == alpha_tenant_context.tenant_id
        assert len(resp.series) >= 1
        assert resp.lineage_snapshot_hash.startswith("sha256:") or len(resp.lineage_snapshot_hash) == 64

    # Anti-leakage check: past cutoff returns 0 for future records
    early_cutoff = UtcDateTime.from_iso("2026-02-14T00:00:00.000000Z")
    early_req = MetricQueryRequest(
        metric_id="order_volume",
        metric_version="1.0.0",
        time_window=TimeWindow(start_time=start, end_time=end),
        grain="AS_OF_SNAPSHOT",
        as_of_time=early_cutoff,
    )
    early_res = metric_service.query(early_req, alpha_tenant_context, dataset=midwest_localization_dataset)
    assert early_res.is_success
    assert early_res.unwrap().series[0].actual_value == 0.0


# =============================================================================
# Exit Gate 2: AC-P02-006-01 StlResidualDetector Benchmark Accuracy
# =============================================================================

def test_gate_stl_detector_benchmark_accuracy(
    tenant_alpha,
    midwest_incident,
    midwest_60day_series,
    base_date,
):
    """
    AC-P02-006-01: PASS only if StlResidualDetector achieves:
    - Precision >= 0.80
    - Recall >= 0.85
    - F1 >= 0.82
    - FPR <= 0.05
    - Lead time <= 48 hours
    on the Midwest incident benchmark.
    """
    from revpilot.modules.analytics.detectors import StlResidualDetector
    from revpilot.modules.benchmark.detector_evaluator import RollingTimeSplitEvaluator

    with tempfile.TemporaryDirectory() as tmp_dir:
        gt_file = os.path.join(tmp_dir, "ground_truth_incident.json")
        EvaluationGroundTruthStore.save_ground_truth(midwest_incident, gt_file)

        detector = StlResidualDetector(seasonal_period=7, sigma_threshold=3.0)
        evaluator = RollingTimeSplitEvaluator()

        metrics = evaluator.run_backtest(
            tenant_id=tenant_alpha,
            metric_id="METRIC-001",
            detector=detector,
            start_day=1,
            end_day=60,
            ground_truth_path=gt_file,
            series_data=midwest_60day_series,
            base_date=base_date,
        )

        assert metrics.precision >= 0.80, f"Precision {metrics.precision:.4f} < 0.80 threshold"
        assert metrics.recall >= 0.85, f"Recall {metrics.recall:.4f} < 0.85 threshold"
        assert metrics.f1_score >= 0.82, f"F1 {metrics.f1_score:.4f} < 0.82 threshold"
        assert metrics.false_positive_rate <= 0.05, f"FPR {metrics.false_positive_rate:.4f} > 0.05 threshold"
        assert metrics.lead_time_hours <= 48.0, f"Lead time {metrics.lead_time_hours:.1f}h > 48h threshold"


# =============================================================================
# Exit Gate 3: AC-P02-006-02 Rolling Time-Split Zero-Lookahead Leakage
# =============================================================================

def test_gate_rolling_timesplit_zero_lookahead_leakage(
    tenant_alpha,
    midwest_incident,
    midwest_60day_series,
    base_date,
):
    """
    AC-P02-006-02: PASS only if rolling time-split backtest across 60 steps
    verifies 0 lookahead events (evaluated strictly with historical window <= as_of).
    """
    from revpilot.modules.analytics.detectors import StlResidualDetector
    from revpilot.modules.benchmark.detector_evaluator import RollingTimeSplitEvaluator

    with tempfile.TemporaryDirectory() as tmp_dir:
        gt_file = os.path.join(tmp_dir, "ground_truth_incident.json")
        EvaluationGroundTruthStore.save_ground_truth(midwest_incident, gt_file)

        detector = StlResidualDetector(seasonal_period=7, sigma_threshold=3.0)
        evaluator = RollingTimeSplitEvaluator()

        # Intercept detect calls to assert strictly incremental series[:day] length
        observed_slice_lengths: list[int] = []
        orig_detect = detector.detect

        def _detect_spy(data):
            observed_slice_lengths.append(len(data))
            return orig_detect(data)

        detector.detect = _detect_spy

        metrics = evaluator.run_backtest(
            tenant_id=tenant_alpha,
            metric_id="METRIC-001",
            detector=detector,
            start_day=1,
            end_day=60,
            ground_truth_path=gt_file,
            series_data=midwest_60day_series,
            base_date=base_date,
        )

        assert len(observed_slice_lengths) == 60, "Expected exactly 60 rolling evaluation steps"
        for day_idx, slice_len in enumerate(observed_slice_lengths, start=1):
            assert slice_len == day_idx, (
                f"Lookahead leakage detected at step {day_idx}: received {slice_len} points, expected {day_idx}"
            )


# =============================================================================
# Exit Gate 4: AC-P02-006-03 Dimensional Localization & Non-Causal Contract
# =============================================================================

def test_gate_dimensional_localization_accuracy_and_non_causal_contract(
    tenant_alpha,
    alpha_tenant_context,
    midwest_localization_dataset,
):
    """
    AC-P02-006-03: PASS only if dimensional localization correctly identifies
    CARRIER_REGIONAL_LOGISTICS as top-1 contributor (>= 70%) and WH-MIDWEST-01 in two-level
    drill-down (>= 90%), and contains non-causal association wording (INV-AI-001).
    """
    from revpilot.modules.analytics.metric_service import MetricService
    from revpilot.modules.analytics.localization import AnomalyLocalizer, AnomalyRecord

    as_of = UtcDateTime.from_iso("2026-02-23T00:00:00.000000Z")
    localizer = AnomalyLocalizer(metric_service=MetricService())
    anomaly = AnomalyRecord(
        id="anm_midwest_test_001",
        tenant_id=tenant_alpha,
        metric_id="cancellation_rate",
        observation_window_start=UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z"),
        observation_window_end=UtcDateTime.from_iso("2026-02-22T23:59:59.000000Z"),
        as_of_time=as_of,
        actual_value=0.051,
        expected_value=0.018,
        affected_scope={"origin_region": "US-MIDWEST"},
    )

    # 1. Single-dimension drill-down on carrier_id
    drill_res = localizer.localize(
        anomaly=anomaly,
        dimension="carrier_id",
        tenant_context=alpha_tenant_context,
        dataset=midwest_localization_dataset,
    )
    assert drill_res.is_success
    result = drill_res.unwrap()
    assert len(result.top_contributing_segments) > 0
    top_c = result.top_contributing_segments[0]
    assert top_c.segment_value == "CARRIER_REGIONAL_LOGISTICS"
    assert top_c.rank == 1
    assert top_c.contribution_pct >= 70.0

    # 2. Strict non-causal association wording check (INV-AI-001)
    summary_lower = result.association_summary.lower()
    assert "association" in summary_lower
    forbidden_phrases = [
        "caused by",
        "root cause is",
        "root cause:",
        "proven cause",
        "causal attribution",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in summary_lower, f"Causal assertion phrase '{phrase}' detected in localization summary"

    # 3. Hierarchical two-level drilldown to warehouse_id
    hier_res = localizer.localize(
        anomaly=anomaly,
        dimension="carrier_id",
        secondary_dimension="warehouse_id",
        tenant_context=alpha_tenant_context,
        dataset=midwest_localization_dataset,
    )
    assert hier_res.is_success
    hier_result = hier_res.unwrap()
    assert hier_result.secondary_localization is not None
    sec_loc = hier_result.secondary_localization
    assert len(sec_loc.top_contributing_segments) > 0
    top_hier = sec_loc.top_contributing_segments[0]
    assert top_hier.segment_value == "WH-MIDWEST-01"
    assert top_hier.contribution_pct >= 90.0


# =============================================================================
# Exit Gate 5: AC-P02-006-04 Anomaly Lifecycle & Reconciliation Replay
# =============================================================================

def test_gate_anomaly_lifecycle_and_reconciliation_immutable_audit(
    tenant_alpha,
    alpha_principal_context,
    midwest_localization_dataset,
):
    """
    AC-P02-006-04: PASS only if anomaly lifecycle transitions and reconciliation
    preserve immutable audit history without data loss (INV-AUD-001, INV-DATA-002).
    """
    from revpilot.modules.analytics.lifecycle import AnomalyAggregate, AnomalyState
    from revpilot.modules.analytics.reconciliation import ReconciliationEngine
    from revpilot.modules.analytics.metric_service import MetricService
    from revpilot.modules.analytics.schemas import TimeWindow

    now = UtcDateTime.from_iso("2026-02-16T12:00:00.000000Z")
    anomaly = AnomalyAggregate.create_detected(
        id="anm_exit_gate_001",
        tenant_id=tenant_alpha,
        metric_id="cancellation_rate",
        metric_version="1.0.0",
        detector_id="stl_cancellation_v1",
        detector_version="1.0.0",
        baseline_id="seasonal_naive",
        baseline_version="1.0.0",
        observation_window_start=UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z"),
        observation_window_end=UtcDateTime.from_iso("2026-02-16T00:00:00.000000Z"),
        as_of_time=now,
        actual_value=0.084,
        expected_value=0.018,
        expected_interval=(0.010, 0.025),
        anomaly_score=4.8,
        severity="HIGH",
    )

    # Valid progression DETECTED -> VALIDATED -> LOCALIZED -> ACKNOWLEDGED
    res1 = anomaly.transition_to(
        target_state=AnomalyState.VALIDATED,
        actor=alpha_principal_context,
        reason="ANOMALY_VALIDATED",
    )
    assert res1.is_success
    res2 = anomaly.transition_to(
        target_state=AnomalyState.LOCALIZED,
        actor=alpha_principal_context,
        reason="LOCALIZED_TO_CARRIER",
        metadata={"top_contributing_segments": [], "primary_dimension": "carrier_id", "data_coverage_pct": 100.0},
    )
    assert res2.is_success
    res3 = anomaly.transition_to(
        target_state=AnomalyState.ACKNOWLEDGED,
        actor=alpha_principal_context,
        reason="ACKNOWLEDGED_BY_OPERATOR",
        metadata={"investigation_id": "inv_exit_gate_001"},
    )
    assert res3.is_success

    # Verify audit trail contains 4 records (initial DETECTED + 3 transitions)
    assert len(anomaly.transitions) == 4

    # Reconciliation replay: late events arrive, metric recomputed
    start_obs = UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z")
    rec_orders: list[Order] = []
    for i in range(100):
        o_id = f"ord_reconcile_{i}"
        dt = UtcDateTime.from_datetime(start_obs.value + timedelta(hours=i % 24))
        is_cancelled = (i < 2)
        rec_orders.append(
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
    from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
    reconciled_dataset = MetricEvaluationDataset(orders=tuple(rec_orders))

    reconciliation_engine = ReconciliationEngine(
        metric_service=MetricService(),
    )
    reconciliation_engine.register_anomaly(anomaly)

    reconciled = reconciliation_engine.reconcile_window(
        tenant_id=tenant_alpha,
        metric_id="cancellation_rate",
        affected_window=TimeWindow(
            start_time=UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z"),
            end_time=UtcDateTime.from_iso("2026-02-16T00:00:00.000000Z"),
        ),
        as_of=UtcDateTime.from_iso("2026-02-18T12:00:00.000000Z"),
        dataset=reconciled_dataset,
    )

    assert len(reconciled) == 1
    rec_anm = reconciled[0]

    # Superseded anomaly transitioned to SUPPRESSED without overwriting history (INV-DATA-002)
    assert rec_anm.state == AnomalyState.SUPPRESSED
    assert rec_anm.suppression_reason == "SUPERSEDED_BY_RECOMPUTATION"
    assert rec_anm.effective_to is not None
    # All 5 transitions intact in immutable append-only log (INV-AUD-001)
    assert len(rec_anm.transitions) == 5
    assert rec_anm.transitions[-1].reason == "SUPERSEDED_BY_RECOMPUTATION"
    assert rec_anm.transitions[-1].to_state == AnomalyState.SUPPRESSED


# =============================================================================
# Exit Gate 6: NFR-AI-004 Zero LLM Dependencies in Detection Loop
# =============================================================================

def test_gate_zero_llm_dependencies_in_detection_loop():
    """
    NFR-AI-004: PASS only if detection and localization engines execute
    with 100% deterministic algorithms and zero LLM dependencies in the runtime loop.
    """
    import inspect
    import revpilot.modules.analytics as analytics_mod
    import revpilot.modules.analytics.metric_service as metric_service_mod
    import revpilot.modules.analytics.baselines as baselines_mod
    import revpilot.modules.analytics.detectors as detectors_mod
    import revpilot.modules.analytics.localization as localization_mod
    import revpilot.modules.analytics.lifecycle as lifecycle_mod
    import revpilot.modules.analytics.reconciliation as reconciliation_mod

    modules_to_inspect = [
        analytics_mod,
        metric_service_mod,
        baselines_mod,
        detectors_mod,
        localization_mod,
        lifecycle_mod,
        reconciliation_mod,
    ]

    forbidden_llm_terms = [
        "openai",
        "anthropic",
        "langchain",
        "langgraph",
        "google.generativeai",
        "chatgpt",
        "claude",
        "bedrock",
        "completion",
    ]

    for mod in modules_to_inspect:
        source = inspect.getsource(mod)
        for term in forbidden_llm_terms:
            assert f"import {term}" not in source.lower(), f"Forbidden LLM import '{term}' in {mod.__name__}"
            assert f"from {term}" not in source.lower(), f"Forbidden LLM from-import '{term}' in {mod.__name__}"
