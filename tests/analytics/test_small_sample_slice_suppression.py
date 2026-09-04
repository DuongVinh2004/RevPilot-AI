"""
RevPilot AI — Small-Sample Slice Noise Suppression Test
Specification: docs/11-decision-intelligence/FAIRNESS-SLICE-EVALUATION.md §1.1 Invariant 2, §4, §5
Conforms to AC-014: Any subgroup slice with sample size N < 50 is marked INSUFFICIENT_SAMPLE,
and performance metrics are suppressed to prevent misleading assertions.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_fairness_module():
    """Ensure fairness module is cleaned between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.fairness"):
            sys.modules.pop(mod, None)


@pytest.fixture
def fairness_module():
    import revpilot.modules.fairness as mod
    return mod


def test_small_sample_suppression_and_insufficient_data(fairness_module):
    """
    Subgroups with sample sizes below threshold N_min = 50 must have metrics suppressed.
    When all subgroups are below threshold, report status is INSUFFICIENT_DATA.
    """
    tenant_id = TenantId("tnt_small_sample_corp")

    # Only 20 observations for REGIONAL carrier (N=20 < 50)
    small_obs = [
        fairness_module.SliceObservation(
            customer_id=f"carrier_reg_{i}",
            slice_dimension="logistics_fulfillment",
            slice_value="REGIONAL",
            actual_churn=1 if i % 2 == 0 else 0,
            predicted_prob=0.50,
            cate_estimate=0.10,
            is_recommended=True,
        )
        for i in range(20)
    ]

    report = fairness_module.evaluate_fairness_slices(
        observations=small_obs,
        tenant_id=tenant_id,
        model_artifact_id="mdl_v1",
        decision_policy_id="pol_v1",
        as_of_time=UtcDateTime.now(),
        min_sample_size=50,
    )

    # Must be INSUFFICIENT_DATA because 0 slices meet N >= 50
    assert report.governance_status == "INSUFFICIENT_DATA"
    assert len(report.evaluated_slices) == 1

    slice_res = report.evaluated_slices[0]
    assert slice_res.slice_value == "REGIONAL"
    assert slice_res.sample_size == 20
    assert slice_res.is_statistically_reliable is False
    assert slice_res.evaluation_status == "INSUFFICIENT_SAMPLE"

    # All statistical metrics must be strictly suppressed (None)
    assert slice_res.ece is None
    assert slice_res.pr_auc is None
    assert slice_res.mean_uplift_cate is None
    assert slice_res.treatment_recommendation_rate is None


def test_mixed_sample_suppression(fairness_module):
    """
    In mixed datasets, only subgroups with N >= 50 are evaluated,
    while smaller subgroups are suppressed.
    """
    tenant_id = TenantId("tnt_mixed_corp")

    # Large slice (N=60)
    obs = [
        fairness_module.SliceObservation(
            customer_id=f"nat_{i}",
            slice_dimension="logistics_fulfillment",
            slice_value="NATIONAL_GROUND",
            actual_churn=0,
            predicted_prob=0.1,
            cate_estimate=0.05,
            is_recommended=True,
        )
        for i in range(60)
    ]
    # Small slice (N=15)
    obs.extend([
        fairness_module.SliceObservation(
            customer_id=f"exp_{i}",
            slice_dimension="logistics_fulfillment",
            slice_value="EXPEDITED",
            actual_churn=0,
            predicted_prob=0.1,
            cate_estimate=0.05,
            is_recommended=True,
        )
        for i in range(15)
    ])

    report = fairness_module.evaluate_fairness_slices(
        observations=obs,
        tenant_id=tenant_id,
        model_artifact_id="mdl_v1",
        decision_policy_id="pol_v1",
        as_of_time=UtcDateTime.now(),
        min_sample_size=50,
    )

    by_val = {s.slice_value: s for s in report.evaluated_slices}
    assert by_val["NATIONAL_GROUND"].evaluation_status == "EVALUATED"
    assert by_val["NATIONAL_GROUND"].is_statistically_reliable is True
    assert by_val["NATIONAL_GROUND"].ece is not None

    assert by_val["EXPEDITED"].evaluation_status == "INSUFFICIENT_SAMPLE"
    assert by_val["EXPEDITED"].is_statistically_reliable is False
    assert by_val["EXPEDITED"].ece is None
