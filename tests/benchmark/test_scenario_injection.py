"""
RevPilot AI — Scenario Injection Unit and Contract Tests (Phase 01)
Verifies SYNTHETIC-DATASET-SPEC.md §6, AC-P01-004-01, AC-P01-004-02, and AC-P01-004-03.
"""

from __future__ import annotations
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.modules.canonical.enums import OrderStatus
from revpilot.modules.benchmark import (
    DatasetProfile,
    GeneratorConfig,
    SyntheticDataGenerator,
    TruckCapacityScenarioInjector,
    ScenarioInjectionError,
)


@pytest.fixture(scope="module")
def base_dataset():
    config = GeneratorConfig(
        profile=DatasetProfile.DEVELOPMENT,
        seed=42,
        duration_days=14,
        tenants=[TenantId("tnt_alpha"), TenantId("tnt_beta")],
    )
    gen = SyntheticDataGenerator(config)
    return gen.generate()


@pytest.fixture(scope="module")
def injected_result(base_dataset):
    injector = TruckCapacityScenarioInjector()
    return injector.inject(base_dataset, seed=42)


def test_affected_cohort_cancellation_rate_elevation(injected_result):
    """
    AC-P01-004-01: Midwest truck-capacity incident elevates affected cohort
    cancellation rate by +6.6% (+/- 0.5% tolerance).
    """
    injected_bundle, ground_truth = injected_result

    # Identify shipments in the affected cohort
    affected_shipments = [
        s for s in injected_bundle.shipments
        if s.tenant_id == TenantId("tnt_alpha")
        and s.warehouse_id == "WH-MIDWEST-01"
        and s.carrier_id == "CARRIER_REGIONAL_LOGISTICS"
        and ground_truth.causal_start_time.value <= s.event_time.value <= ground_truth.causal_end_time.value
    ]
    assert len(affected_shipments) > 0

    affected_order_ids = {s.order_id for s in affected_shipments}
    affected_orders = [o for o in injected_bundle.orders if o.id in affected_order_ids]
    assert len(affected_orders) > 0

    cancelled_affected = [o for o in affected_orders if o.order_status == OrderStatus.CANCELLED]
    actual_rate = len(cancelled_affected) / len(affected_orders)

    # Expected: 8.4% (+/- 0.5% tolerance) -> delta of +6.6% from 1.8% baseline
    expected_target = 0.0840
    tolerance = 0.0050
    assert abs(actual_rate - expected_target) <= tolerance, (
        f"Affected cancellation rate {actual_rate:.4f} outside [{expected_target - tolerance:.4f}, {expected_target + tolerance:.4f}]"
    )
    assert ground_truth.true_ate_cancellation_rate_delta == 0.0660


def test_control_cohorts_remain_at_baseline(injected_result):
    """
    AC-P01-004-02: ten_beta and unaffected ten_alpha facilities maintain baseline
    cancellation rates (~1.8% +/- 0.5%).
    """
    injected_bundle, ground_truth = injected_result

    # 1. External control tenant (ten_beta)
    beta_orders = [o for o in injected_bundle.orders if o.tenant_id == TenantId("tnt_beta")]
    beta_cancelled = [o for o in beta_orders if o.order_status == OrderStatus.CANCELLED]
    beta_rate = len(beta_cancelled) / len(beta_orders)

    expected_baseline = 0.0180
    tolerance = 0.0050
    assert abs(beta_rate - expected_baseline) <= tolerance, (
        f"Control tenant beta cancellation rate {beta_rate:.4f} drifted from baseline"
    )

    # 2. Internal control group within ten_alpha (WH-WEST-01 and air express)
    affected_order_ids = {
        s.order_id for s in injected_bundle.shipments
        if s.tenant_id == TenantId("tnt_alpha")
        and s.warehouse_id == "WH-MIDWEST-01"
        and s.carrier_id == "CARRIER_REGIONAL_LOGISTICS"
        and ground_truth.causal_start_time.value <= s.event_time.value <= ground_truth.causal_end_time.value
    }
    alpha_control_orders = [
        o for o in injected_bundle.orders
        if o.tenant_id == TenantId("tnt_alpha") and o.id not in affected_order_ids
    ]
    alpha_control_cancelled = [o for o in alpha_control_orders if o.order_status == OrderStatus.CANCELLED]
    alpha_ctrl_rate = len(alpha_control_cancelled) / len(alpha_control_orders)

    assert abs(alpha_ctrl_rate - expected_baseline) <= tolerance, (
        f"Alpha internal control cancellation rate {alpha_ctrl_rate:.4f} drifted from baseline"
    )


def test_no_ground_truth_leakage_in_runtime_entities(injected_result):
    """
    AC-P01-004-03 & INV-DATA-001: Runtime canonical entity schemas contain zero
    ground-truth label attributes or leakage tokens.
    """
    injected_bundle, _ = injected_result

    forbidden_tokens = ["incident", "truck_delay", "ground_truth", "root_cause"]
    forbidden_attrs = ["is_ground_truth", "true_cause", "causal_label", "ground_truth"]

    # Check Orders
    for o in injected_bundle.orders:
        for attr in forbidden_attrs:
            assert not hasattr(o, attr), f"Order schema leaks ground-truth attribute: {attr}"
        for token in forbidden_tokens:
            assert token not in o.id.lower()
            assert token not in o.order_number.lower()

    # Check Shipments
    for s in injected_bundle.shipments:
        for attr in forbidden_attrs:
            assert not hasattr(s, attr), f"Shipment schema leaks ground-truth attribute: {attr}"
        for token in forbidden_tokens:
            assert token not in s.id.lower()
            assert token not in s.tracking_number.lower()

    # Check SupportTickets
    for t in injected_bundle.support_tickets:
        for attr in forbidden_attrs:
            assert not hasattr(t, attr), f"Support ticket schema leaks ground-truth attribute: {attr}"
        for token in forbidden_tokens:
            assert token not in t.id.lower()
            assert token not in t.ticket_number.lower()


def test_affected_shipments_mechanistic_latency(injected_result):
    """Verify affected shipments experience elevated dispatch latency (84 hours)."""
    injected_bundle, ground_truth = injected_result

    affected_shipments = [
        s for s in injected_bundle.shipments
        if s.tenant_id == TenantId("tnt_alpha")
        and s.warehouse_id == "WH-MIDWEST-01"
        and s.carrier_id == "CARRIER_REGIONAL_LOGISTICS"
        and ground_truth.causal_start_time.value <= s.event_time.value <= ground_truth.causal_end_time.value
    ]
    assert len(affected_shipments) > 0
    for s in affected_shipments:
        assert s.is_delayed is True
        latency_hours = (s.dispatched_at.value - s.event_time.value).total_seconds() / 3600
        assert latency_hours >= 72.0


def test_scenario_injection_reproducibility(base_dataset):
    """Injecting with identical seed produces identical output and hashes."""
    injector = TruckCapacityScenarioInjector()
    bundle1, gt1 = injector.inject(base_dataset, seed=42)
    bundle2, gt2 = injector.inject(base_dataset, seed=42)

    assert gt1 == gt2
    assert bundle1.build_manifest().artifact_hashes == bundle2.build_manifest().artifact_hashes


def test_scenario_injection_rejects_inconsistent_timestamps():
    """Inconsistent cohort timestamps (< 10 days duration) raises ScenarioInjectionError."""
    config = GeneratorConfig(
        profile=DatasetProfile.DEVELOPMENT,
        seed=42,
        duration_days=5,
    )
    gen = SyntheticDataGenerator(config)
    bundle = gen.generate()

    injector = TruckCapacityScenarioInjector()
    with pytest.raises(ScenarioInjectionError):
        injector.inject(bundle)
