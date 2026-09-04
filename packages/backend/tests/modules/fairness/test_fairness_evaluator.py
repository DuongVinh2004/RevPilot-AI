"""
RevPilot AI — Unit Tests for Fairness & Disparity Evaluation Engine
Specification: docs/11-decision-intelligence/FAIRNESS-SLICE-EVALUATION.md §1..§4
Conforms to BR-002, FR-ML-002..003, INV-AI-001, INV-PRV-001, INV-TEN-001..003, NFR-AI-005..006, and AC-014.
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


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_corp")


def test_ece_perfect_calibration(fairness_module):
    """Perfect calibration yields near-zero ECE."""
    # 50 positives with p=1.0, 50 negatives with p=0.0
    actuals = [1] * 50 + [0] * 50
    probs = [1.0] * 50 + [0.0] * 50
    ece = fairness_module.compute_expected_calibration_error(actuals, probs)
    assert ece == 0.0


def test_ece_miscalibration_detection(fairness_module):
    """Severely overconfident model yields high ECE."""
    # 100 actual negatives but model predicts 0.90
    actuals = [0] * 100
    probs = [0.90] * 100
    ece = fairness_module.compute_expected_calibration_error(actuals, probs)
    assert ece >= 0.80


def test_pr_auc_calculation(fairness_module):
    """PR-AUC correctly ranks well-separated probabilities."""
    actuals = [1, 1, 1, 0, 0]
    probs = [0.9, 0.8, 0.7, 0.3, 0.2]
    pr_auc = fairness_module.compute_pr_auc(actuals, probs)
    assert pr_auc == 1.0


def test_evaluate_fairness_slices_pass_criteria(fairness_module, sample_tenant):
    """Well-calibrated, equitably allocated slices achieve PASS governance status."""
    observations = []
    # Tier ENTERPRISE: 60 units, calibrated p ~ 0.20, rec rate = 0.50
    for i in range(60):
        y = 1 if i < 12 else 0
        p = 0.20
        observations.append(
            fairness_module.SliceObservation(
                customer_id=f"ent_{i}",
                slice_dimension="customer_tier",
                slice_value="ENTERPRISE",
                actual_churn=y,
                predicted_prob=p,
                cate_estimate=0.08,
                is_recommended=(i % 2 == 0),
            )
        )
    # Tier MID_MARKET: 60 units, calibrated p ~ 0.20, rec rate = 0.50
    for i in range(60):
        y = 1 if i < 12 else 0
        p = 0.20
        observations.append(
            fairness_module.SliceObservation(
                customer_id=f"mm_{i}",
                slice_dimension="customer_tier",
                slice_value="MID_MARKET",
                actual_churn=y,
                predicted_prob=p,
                cate_estimate=0.08,
                is_recommended=(i % 2 == 0),
            )
        )

    report = fairness_module.evaluate_fairness_slices(
        observations=observations,
        tenant_id=sample_tenant,
        model_artifact_id="mdl_churn_v2",
        decision_policy_id="pol_retention_v1",
        as_of_time=UtcDateTime.now(),
        min_sample_size=50,
    )

    assert report.governance_status == "PASS"
    assert report.max_calibration_disparity <= 0.0300
    assert 0.80 <= report.max_allocation_disparity_ratio <= 1.25
    assert len(report.evaluated_slices) == 2
    assert len(report.audit_digest) == 64


def test_evaluate_fairness_slices_disparity_triggers_needs_review(fairness_module, sample_tenant):
    """High disparity between slices triggers NEEDS_REVIEW governance status."""
    observations = []
    # Slice A: 60 units, rec rate = 0.80
    for i in range(60):
        observations.append(
            fairness_module.SliceObservation(
                customer_id=f"a_{i}",
                slice_dimension="geographic_region",
                slice_value="US-WEST",
                actual_churn=1 if i < 10 else 0,
                predicted_prob=0.15,
                cate_estimate=0.05,
                is_recommended=(i < 48),  # 80%
            )
        )
    # Slice B: 60 units, rec rate = 0.20 -> Ratio = 0.80 / 0.20 = 4.0 (> 1.25)
    for i in range(60):
        observations.append(
            fairness_module.SliceObservation(
                customer_id=f"b_{i}",
                slice_dimension="geographic_region",
                slice_value="US-SOUTH",
                actual_churn=1 if i < 10 else 0,
                predicted_prob=0.15,
                cate_estimate=0.05,
                is_recommended=(i < 12),  # 20%
            )
        )

    report = fairness_module.evaluate_fairness_slices(
        observations=observations,
        tenant_id=sample_tenant,
        model_artifact_id="mdl_churn_v2",
        decision_policy_id="pol_retention_v1",
        as_of_time=UtcDateTime.now(),
        min_sample_size=50,
    )

    assert report.governance_status == "NEEDS_REVIEW"
    assert report.max_allocation_disparity_ratio > 1.25


@pytest.mark.asyncio
async def test_fairness_audit_repository_tenant_isolation(fairness_module, sample_tenant):
    """FairnessAuditRepository enforces strict tenant isolation (INV-TEN-001)."""
    repo = fairness_module.InMemoryFairnessAuditRepository()
    obs = [
        fairness_module.SliceObservation(
            customer_id=f"c_{i}",
            slice_dimension="customer_tier",
            slice_value="SMB",
            actual_churn=0,
            predicted_prob=0.1,
            cate_estimate=0.05,
            is_recommended=True,
        )
        for i in range(60)
    ]
    report = fairness_module.evaluate_fairness_slices(
        observations=obs,
        tenant_id=sample_tenant,
        model_artifact_id="mdl_v1",
        decision_policy_id="pol_v1",
        as_of_time=UtcDateTime.now(),
    )

    await repo.save_report(report)

    # Scoped fetch under same tenant
    fetched = await repo.get_report(sample_tenant, report.report_id)
    assert fetched is not None
    assert fetched.report_id == report.report_id

    # Cross-tenant adversary read
    adversary = TenantId("tnt_adversary")
    assert await repo.get_report(adversary, report.report_id) is None
    assert len(await repo.list_reports(adversary)) == 0
