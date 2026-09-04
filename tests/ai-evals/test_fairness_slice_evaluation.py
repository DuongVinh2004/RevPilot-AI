"""
RevPilot AI — Fairness Slice Evaluation Benchmark
Specification: docs/11-decision-intelligence/FAIRNESS-SLICE-EVALUATION.md §1..§5
Benchmark Gates:
  - Calibration disparity Delta ECE <= 0.030 (3.0%) across customer tiers.
  - Uplift treatment allocation parity ratio 0.80 <= Ratio <= 1.25 across comparable segments.
  - No unmeasured compliance claims (AC-014).
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


def test_fairness_slice_benchmark_gates(fairness_module):
    """
    Evaluates fairness and calibration parity across standard operational tiers:
    ENTERPRISE, MID_MARKET, SMB.
    """
    tenant_id = TenantId("tnt_enterprise_corp")
    observations = []

    # Synthetic population across 3 tiers (70 units each >= 50)
    tiers = ["ENTERPRISE", "MID_MARKET", "SMB"]
    for tier in tiers:
        for i in range(70):
            # Calibrated baseline churn ~ 15%
            y = 1 if i < 10 else 0
            p = 0.14  # Close to 10/70 = 0.1428
            # Comparable uplift tau = 0.06
            tau = 0.06
            # Balanced treatment recommendation rate = 35/70 = 0.50
            is_rec = (i % 2 == 0)

            observations.append(
                fairness_module.SliceObservation(
                    customer_id=f"{tier}_{i}",
                    slice_dimension="customer_tier",
                    slice_value=tier,
                    actual_churn=y,
                    predicted_prob=p,
                    cate_estimate=tau,
                    is_recommended=is_rec,
                )
            )

    report = fairness_module.evaluate_fairness_slices(
        observations=observations,
        tenant_id=tenant_id,
        model_artifact_id="mdl_churn_production_v1",
        decision_policy_id="pol_decision_opt_v1",
        as_of_time=UtcDateTime.now(),
        min_sample_size=50,
    )

    # 1. Calibration disparity across tiers <= 0.030 (3.0%)
    assert report.max_calibration_disparity <= 0.0300, (
        f"Calibration disparity {report.max_calibration_disparity} exceeded 0.0300"
    )

    # 2. Treatment allocation disparity ratio between 0.80 and 1.25
    assert 0.80 <= report.max_allocation_disparity_ratio <= 1.25, (
        f"Allocation disparity ratio {report.max_allocation_disparity_ratio} out of bounds [0.80, 1.25]"
    )

    # 3. Governance Status must PASS
    assert report.governance_status == "PASS"

    # 4. Invariant AC-014: Zero unmeasured compliance claims
    report_dict = report.model_dump()
    serialized = str(report_dict).lower()
    for forbidden_claim in ["fairness certified", "bias-free", "regulatory compliant"]:
        assert forbidden_claim not in serialized, f"Forbidden compliance claim detected: {forbidden_claim}"
