"""
RevPilot AI — Ground Truth Air-Gap Access Control Tests (Phase 01)
Verifies SYNTHETIC-DATASET-SPEC.md §7, AC-P01-004-04, and INV-DATA-001.
"""

from __future__ import annotations
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.benchmark import (
    GroundTruthIncident,
    EvaluatorAuthToken,
    EvaluationGroundTruthStore,
    AccessDeniedError,
)


@pytest.fixture
def sample_ground_truth():
    return GroundTruthIncident(
        tenant_id=TenantId("tnt_alpha"),
        incident_id="INC-SYNTH-TRUCK-001",
        scenario_name="Midwest Regional Carrier Fleet Capacity Disruption",
        causal_start_time=UtcDateTime.from_iso("2026-02-14T08:00:00.000000Z"),
        causal_end_time=UtcDateTime.from_iso("2026-02-21T23:59:59.000000Z"),
        primary_root_cause="TRUCK_CAPACITY_SHORTAGE_MIDWEST",
        affected_facility_id="WH-MIDWEST-01",
        affected_carrier_id="CARRIER_REGIONAL_LOGISTICS",
        true_ate_cancellation_rate_delta=0.0660,
        true_delayed_shipment_count=482,
        true_revenue_at_risk_cents=14256000,
        competing_hypotheses=[
            {"hypothesis_id": "HYP-001", "status": "DISPROVED_CONFOUNDER"},
        ],
    )


def test_unauthenticated_access_denied(tmp_path, sample_ground_truth):
    """
    AC-P01-004-04: Unauthenticated access to EvaluationGroundTruthStore
    fails closed with AccessDeniedError.
    """
    gt_file = str(tmp_path / "ground_truth.json")
    EvaluationGroundTruthStore.save_ground_truth(sample_ground_truth, gt_file)

    # Call with None token
    res = EvaluationGroundTruthStore.load_ground_truth_for_eval(gt_file, auth_token=None)
    assert res.is_failure
    error = res.unwrap_error()
    assert isinstance(error, AccessDeniedError)
    assert error.code == "GROUND_TRUTH_ACCESS_DENIED"


def test_runtime_principal_access_denied(tmp_path, sample_ground_truth):
    """
    AC-P01-004-04: Runtime application principal (revpilot_app) is denied
    access to hidden ground truth.
    """
    gt_file = str(tmp_path / "ground_truth.json")
    EvaluationGroundTruthStore.save_ground_truth(sample_ground_truth, gt_file)

    runtime_token = EvaluatorAuthToken(
        principal_id="app_runtime_agent_01",
        role="revpilot_app",
        is_valid=True,
    )

    res = EvaluationGroundTruthStore.load_ground_truth_for_eval(gt_file, auth_token=runtime_token)
    assert res.is_failure
    error = res.unwrap_error()
    assert isinstance(error, AccessDeniedError)
    assert error.code == "GROUND_TRUTH_ACCESS_DENIED"
    assert error.details["http_status"] == 403


def test_invalid_evaluator_token_denied(tmp_path, sample_ground_truth):
    """Expired or invalid evaluator token is denied access."""
    gt_file = str(tmp_path / "ground_truth.json")
    EvaluationGroundTruthStore.save_ground_truth(sample_ground_truth, gt_file)

    invalid_token = EvaluatorAuthToken(
        principal_id="evaluator_batch_runner",
        role="revpilot_evaluator",
        is_valid=False,
    )

    res = EvaluationGroundTruthStore.load_ground_truth_for_eval(gt_file, auth_token=invalid_token)
    assert res.is_failure
    assert res.unwrap_error().code == "GROUND_TRUTH_ACCESS_DENIED"


def test_authorized_evaluator_access_granted(tmp_path, sample_ground_truth):
    """Authorized offline evaluator receives ground truth incident successfully."""
    gt_file = str(tmp_path / "ground_truth.json")
    EvaluationGroundTruthStore.save_ground_truth(sample_ground_truth, gt_file)

    valid_token = EvaluatorAuthToken(
        principal_id="evaluator_batch_runner",
        role="revpilot_evaluator",
        is_valid=True,
    )

    res = EvaluationGroundTruthStore.load_ground_truth_for_eval(gt_file, auth_token=valid_token)
    assert res.is_success
    incident = res.unwrap()
    assert incident == sample_ground_truth
    assert incident.primary_root_cause == "TRUCK_CAPACITY_SHORTAGE_MIDWEST"
    assert incident.true_ate_cancellation_rate_delta == 0.0660


def test_ground_truth_serialization_round_trip(sample_ground_truth):
    """GroundTruthIncident serializes to dict and JSON and reconstructs losslessly."""
    json_str = sample_ground_truth.to_json()
    reconstructed = GroundTruthIncident.from_json(json_str)
    assert reconstructed == sample_ground_truth

    dict_repr = sample_ground_truth.to_dict()
    reconstructed_dict = GroundTruthIncident.from_dict(dict_repr)
    assert reconstructed_dict == sample_ground_truth
