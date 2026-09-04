"""
RevPilot AI — Phase 01 Contract Verification and Reproducibility Gate
Verifies execution/MASTER-ROADMAP.md §Phase-01, AC-P01-006-01 through AC-P01-006-05.
"""

from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.canonical.enums import OrderStatus
from revpilot.modules.benchmark import (
    DatasetProfile,
    GeneratorConfig,
    SyntheticDataGenerator,
    TruckCapacityScenarioInjector,
    GroundTruthIncident,
    EvaluatorAuthToken,
    EvaluationGroundTruthStore,
    AccessDeniedError,
)
from revpilot.modules.data_quality import (
    DataQualityValidator,
    QuarantineRecord,
    QuarantineRepository,
    DQ_TYP_001,
    DQ_TEN_001,
    DQ_REQ_001,
)


@pytest.fixture(scope="module")
def run_benchmark_generation():
    """Generates two independent runs using seed 42 (DEVELOPMENT profile)."""
    cfg1 = GeneratorConfig(profile=DatasetProfile.DEVELOPMENT, seed=42, duration_days=14)
    gen1 = SyntheticDataGenerator(cfg1)
    bundle1 = gen1.generate()
    manifest1 = bundle1.build_manifest()

    cfg2 = GeneratorConfig(profile=DatasetProfile.DEVELOPMENT, seed=42, duration_days=14)
    gen2 = SyntheticDataGenerator(cfg2)
    bundle2 = gen2.generate()
    manifest2 = bundle2.build_manifest()

    return bundle1, manifest1, bundle2, manifest2


def test_gate_deterministic_reproducibility(run_benchmark_generation):
    """
    AC-P01-006-01: PASS only if deterministic generator produces identical
    SHA-256 artifact hashes on two independent runs.
    """
    bundle1, manifest1, bundle2, manifest2 = run_benchmark_generation

    # 1. Manifest IDs and entity counts match exactly
    assert manifest1.manifest_id == manifest2.manifest_id
    assert manifest1.entity_counts == manifest2.entity_counts
    assert manifest1.entity_counts["orders"] == 1000
    assert manifest1.entity_counts["customers"] == 200
    assert manifest1.entity_counts["order_lines"] == 2400
    assert manifest1.entity_counts["shipments"] == 1020

    # 2. Cryptographic SHA-256 artifact hashes match byte-for-byte
    assert manifest1.artifact_hashes == manifest2.artifact_hashes
    assert len(manifest1.artifact_hashes) >= 9

    for artifact_name, hash_val in manifest1.artifact_hashes.items():
        assert hash_val.startswith("sha256:")
        assert hash_val == manifest2.artifact_hashes[artifact_name]


def test_gate_ground_truth_airgap_protection(tmp_path, run_benchmark_generation):
    """
    AC-P01-006-02: PASS only if ground truth labels are completely inaccessible
    from runtime application context (revpilot_app).
    """
    bundle1, _, _, _ = run_benchmark_generation
    injector = TruckCapacityScenarioInjector()
    injected_bundle, ground_truth = injector.inject(bundle1, seed=42)

    gt_file = str(tmp_path / "ground_truth_incident.json")
    EvaluationGroundTruthStore.save_ground_truth(ground_truth, gt_file)

    # 1. Unauthenticated runtime query fails closed
    unauth_res = EvaluationGroundTruthStore.load_ground_truth_for_eval(gt_file, auth_token=None)
    assert unauth_res.is_failure
    assert isinstance(unauth_res.unwrap_error(), AccessDeniedError)
    assert unauth_res.unwrap_error().code == "GROUND_TRUTH_ACCESS_DENIED"

    # 2. Runtime agent principal (revpilot_app) fails closed with HTTP 403
    runtime_token = EvaluatorAuthToken(
        principal_id="agent_investigation_worker_01",
        role="revpilot_app",
        is_valid=True,
    )
    runtime_res = EvaluationGroundTruthStore.load_ground_truth_for_eval(gt_file, auth_token=runtime_token)
    assert runtime_res.is_failure
    err = runtime_res.unwrap_error()
    assert err.code == "GROUND_TRUTH_ACCESS_DENIED"
    assert err.details["http_status"] == 403

    # 3. Only offline evaluator principal receives truth
    eval_token = EvaluatorAuthToken(
        principal_id="offline_benchmark_runner",
        role="revpilot_evaluator",
        is_valid=True,
    )
    eval_res = EvaluationGroundTruthStore.load_ground_truth_for_eval(gt_file, auth_token=eval_token)
    assert eval_res.is_success
    assert eval_res.unwrap().incident_id == "INC-SYNTH-TRUCK-001"

    # 4. Anti-leakage: canonical entity schemas contain zero ground truth attributes or tokens
    forbidden_tokens = ["incident", "truck_delay", "ground_truth", "root_cause"]
    for o in injected_bundle.orders:
        assert not hasattr(o, "is_ground_truth")
        assert not hasattr(o, "true_cause")
        for token in forbidden_tokens:
            assert token not in o.id.lower()
            assert token not in o.order_number.lower()


def test_gate_all_nine_canonical_metrics_evaluate_without_leakage(run_benchmark_generation):
    """
    AC-P01-006-03: PASS only if all 9 canonical metrics compute accurately against
    generated scenario data without time leakage.
    """
    from revpilot.modules.analytics.metrics import (
        CANONICAL_METRIC_REGISTRY,
        MetricEvaluationDataset,
        MetricValue,
    )

    try:
        bundle1, _, _, _ = run_benchmark_generation
        injector = TruckCapacityScenarioInjector()
        injected_bundle, _ = injector.inject(bundle1, seed=42)

        eval_dataset = MetricEvaluationDataset(
            customers=injected_bundle.customers,
            orders=injected_bundle.orders,
            order_lines=injected_bundle.order_lines,
            shipments=injected_bundle.shipments,
            support_tickets=injected_bundle.support_tickets,
            maintenance_events=injected_bundle.maintenance_events,
            contracts=injected_bundle.contracts,
            contract_clauses=injected_bundle.contract_clauses,
            payment_references=injected_bundle.payment_references,
        )

        all_metric_ids = [
            "METRIC-001",  # cancellation_rate
            "METRIC-002",  # revenue_at_risk
            "METRIC-003",  # fulfillment_delay_rate
            "METRIC-004",  # sla_violation_rate
            "METRIC-005",  # payment_failure_rate
            "METRIC-006",  # customer_churn_rate
            "METRIC-007",  # order_volume
            "METRIC-008",  # shipment_volume
            "METRIC-009",  # support_ticket_volume
        ]

        tenant_id = TenantId("tnt_alpha")
        end_of_time = UtcDateTime.from_datetime(
            injected_bundle.config.start_date.value + timedelta(days=20)
        )

        for m_id in all_metric_ids:
            eval_res = CANONICAL_METRIC_REGISTRY.evaluate(
                metric_id=m_id,
                tenant_id=tenant_id,
                data=eval_dataset,
                as_of=end_of_time,
            )
            assert eval_res.is_success, f"Evaluation of {m_id} failed: {eval_res.unwrap_error()}"
            m_val = eval_res.unwrap()
            assert isinstance(m_val, MetricValue)
            assert m_val.metric_id == m_id
            assert m_val.tenant_id == tenant_id
            assert m_val.value >= Decimal("0.0")

        # Anti-leakage: as_of cutoff excludes future events strictly
        early_cutoff = UtcDateTime.from_datetime(
            injected_bundle.config.start_date.value + timedelta(days=2)
        )
        early_vol_res = CANONICAL_METRIC_REGISTRY.evaluate(
            metric_id="METRIC-007",  # order_volume
            tenant_id=tenant_id,
            data=eval_dataset,
            as_of=early_cutoff,
        )
        assert early_vol_res.is_success
        early_vol = early_vol_res.unwrap().value

        full_vol_res = CANONICAL_METRIC_REGISTRY.evaluate(
            metric_id="METRIC-007",
            tenant_id=tenant_id,
            data=eval_dataset,
            as_of=end_of_time,
        )
        assert full_vol_res.is_success
        full_vol = full_vol_res.unwrap().value

        assert early_vol < full_vol, "Early volume must strictly be lower than full volume without temporal leakage"
    finally:
        for mod in list(sys.modules.keys()):
            if mod.startswith("revpilot.modules.analytics"):
                sys.modules.pop(mod, None)


def test_gate_data_quality_poisoned_payload_quarantine():
    """
    AC-P01-006-04: PASS only if data quality rules catch poisoned inputs and
    isolate them in quarantine.
    """
    validator = DataQualityValidator()
    repository = QuarantineRepository()

    tenant_id = TenantId("tnt_alpha")

    poisoned_cases = [
        ({"tenant_id": "tnt_alpha", "id": "p_01", "event_time": "2026-01-01T00:00:00Z", "total_cents": -500}, DQ_TYP_001),
        ({"tenant_id": "tnt_beta", "id": "p_02", "event_time": "2026-01-01T00:00:00Z", "total_cents": 1000}, DQ_TEN_001),
        ({"tenant_id": "tnt_alpha", "event_time": "2026-01-01T00:00:00Z", "total_cents": 1000}, DQ_REQ_001),
    ]

    for idx, (bad_payload, expected_rule) in enumerate(poisoned_cases):
        val_res = validator.validate_record(bad_payload, session_tenant_id=tenant_id)
        assert not val_res.is_valid
        assert val_res.rule_id == expected_rule

        q_rec = QuarantineRecord(
            quarantine_id=f"gate_q_{idx:02d}",
            tenant_id=tenant_id,
            rule_id=val_res.rule_id,
            raw_payload=bad_payload,
            rejection_reason=val_res.rejection_reason or "Poisoned",
        )
        repository.quarantine(q_rec)

    # All quarantined records are isolated to tnt_alpha
    quarantined = repository.list_quarantined(tenant_id)
    assert len(quarantined) == len(poisoned_cases)
    for q in quarantined:
        assert q.status == "QUARANTINED"

    # Replay with corrected payload recovers cleanly
    fixed_payload = dict(poisoned_cases[0][0])
    fixed_payload["total_cents"] = 500
    replay_res = repository.replay(
        quarantine_id="gate_q_00",
        validator=validator,
        corrected_payload=fixed_payload,
    )
    assert replay_res.is_success
    assert repository.get(tenant_id, "gate_q_00").status == "REPROCESSED"


def test_gate_scenario_injection_and_control_coexistence(run_benchmark_generation):
    """
    Verify Midwest truck disruption elevates affected cohort while preserving control groups.
    """
    bundle1, _, _, _ = run_benchmark_generation
    injector = TruckCapacityScenarioInjector()
    injected_bundle, ground_truth = injector.inject(bundle1, seed=42)

    # 1. Affected cohort
    affected_shipments = [
        s for s in injected_bundle.shipments
        if s.tenant_id == TenantId("tnt_alpha")
        and s.warehouse_id == "WH-MIDWEST-01"
        and s.carrier_id == "CARRIER_REGIONAL_LOGISTICS"
        and ground_truth.causal_start_time.value <= s.event_time.value <= ground_truth.causal_end_time.value
    ]
    affected_order_ids = {s.order_id for s in affected_shipments}
    affected_orders = [o for o in injected_bundle.orders if o.id in affected_order_ids]
    affected_cancelled = [o for o in affected_orders if o.order_status == OrderStatus.CANCELLED]
    affected_rate = len(affected_cancelled) / len(affected_orders)

    # 2. Control tenant
    beta_orders = [o for o in injected_bundle.orders if o.tenant_id == TenantId("tnt_beta")]
    beta_cancelled = [o for o in beta_orders if o.order_status == OrderStatus.CANCELLED]
    beta_rate = len(beta_cancelled) / len(beta_orders)

    # Assert elevated cancellation rate on affected (+6.6% delta) vs control baseline (~1.8%)
    assert abs(affected_rate - 0.0840) <= 0.0050
    assert abs(beta_rate - 0.0180) <= 0.0050
    assert ground_truth.true_ate_cancellation_rate_delta == 0.0660
