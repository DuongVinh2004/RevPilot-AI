"""
RevPilot AI — Unit and Domain Invariant Tests for Causal Study Contract
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §1, §2
Conforms to BR-001, BR-002, FR-ML-003, FR-ML-004, INV-AI-001, INV-TEN-001, and AC-006.
"""

from __future__ import annotations
import sys
import pytest
from pydantic import ValidationError

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_causal_module():
    """Ensure causal module is cleaned from sys.modules after every test."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.causal"):
            sys.modules.pop(mod, None)


@pytest.fixture
def causal_module():
    import revpilot.modules.causal as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_alpha_logistics")


@pytest.fixture
def sample_investigation_id() -> UUIDv7:
    return UUIDv7.generate()


def test_causal_study_creation_and_frozen_invariant(
    causal_module, sample_tenant, sample_investigation_id
):
    """Verify CausalStudy model is frozen and enforces strict typing."""
    now = UtcDateTime.now()
    study = causal_module.CausalStudy(
        study_id=UUIDv7.generate(),
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        causal_question="What was the effect of carrier truck shortage on cancellations?",
        treatment_variable="carrier_truck_shortage",
        outcome_variable="order_cancelled",
        unit_of_analysis="order_id",
        target_population="Orders originating at WH-MIDWEST-01 during Days 45-52",
        treatment_window_start=now,
        treatment_window_end=now,
        outcome_window_start=now,
        outcome_window_end=now,
        as_of_time=now,
        pre_treatment_covariates=["customer_tier", "order_subtotal"],
        post_treatment_exclusions=["actual_dispatch_delay", "support_ticket_created"],
        estimand_type=causal_module.EstimandType.ATE,
        identification_strategy=causal_module.IdentificationStrategy.BACKDOOR_ADJUSTMENT,
        causal_dag_ref="dag_midwest_fulfillment_v1",
        explicit_assumptions=["SUTVA", "Positivity", "Exchangeability"],
        estimator=causal_module.EstimatorType.DOUBLY_ROBUST_AIPW,
        overlap=causal_module.OverlapDiagnostics(
            min_propensity=0.12,
            max_propensity=0.88,
            positivity_satisfied=True,
            common_support_ratio=0.98,
            trimmed_sample_count=4,
        ),
        point_estimate=0.0660,
        standard_error=0.0120,
        confidence_interval_95=(0.0425, 0.0895),
        p_value=0.0001,
        sensitivity=causal_module.SensitivityAnalysis(
            method="E_VALUE",
            robustness_value=2.45,
            e_value_estimate=2.10,
            e_value_ci=1.75,
            is_sensitive_to_unobserved_confounding=False,
        ),
        reproducibility_seed=42,
        created_at=now,
    )

    assert study.point_estimate == 0.0660
    assert study.estimand_type == causal_module.EstimandType.ATE

    # Enforce immutability
    with pytest.raises(ValidationError):
        study.point_estimate = 0.10


def test_deterministic_study_digest(causal_module, sample_tenant, sample_investigation_id):
    """Verify compute_study_digest produces deterministic SHA-256 string."""
    study_id = UUIDv7.generate()
    d1 = causal_module.compute_study_digest(
        study_id=study_id,
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        causal_question="Test Question",
        treatment_variable="T",
        outcome_variable="Y",
        estimand_type=causal_module.EstimandType.ATE,
        identification_strategy=causal_module.IdentificationStrategy.BACKDOOR_ADJUSTMENT,
        estimator=causal_module.EstimatorType.DOUBLY_ROBUST_AIPW,
        reproducibility_seed=42,
    )
    d2 = causal_module.compute_study_digest(
        study_id=study_id,
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        causal_question="Test Question",
        treatment_variable="T",
        outcome_variable="Y",
        estimand_type=causal_module.EstimandType.ATE,
        identification_strategy=causal_module.IdentificationStrategy.BACKDOOR_ADJUSTMENT,
        estimator=causal_module.EstimatorType.DOUBLY_ROBUST_AIPW,
        reproducibility_seed=42,
    )
    assert d1 == d2
    assert len(d1) == 64


def test_in_memory_causal_repository_isolation(
    causal_module, sample_tenant, sample_investigation_id
):
    """Verify repository strictly isolates studies between tenants."""
    repo = causal_module.InMemoryCausalStudyRepository()
    now = UtcDateTime.now()
    s_id = UUIDv7.generate()

    study = causal_module.CausalStudy(
        study_id=s_id,
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        causal_question="Test Question",
        treatment_variable="T",
        outcome_variable="Y",
        unit_of_analysis="unit",
        target_population="pop",
        treatment_window_start=now,
        treatment_window_end=now,
        outcome_window_start=now,
        outcome_window_end=now,
        as_of_time=now,
        pre_treatment_covariates=["X1"],
        post_treatment_exclusions=["M1"],
        estimand_type=causal_module.EstimandType.ATE,
        identification_strategy=causal_module.IdentificationStrategy.BACKDOOR_ADJUSTMENT,
        causal_dag_ref="dag1",
        explicit_assumptions=[],
        estimator=causal_module.EstimatorType.DOUBLY_ROBUST_AIPW,
        overlap=causal_module.OverlapDiagnostics(
            min_propensity=0.1, max_propensity=0.9, positivity_satisfied=True, common_support_ratio=1.0, trimmed_sample_count=0
        ),
        point_estimate=0.05,
        standard_error=0.01,
        confidence_interval_95=(0.03, 0.07),
        p_value=0.01,
        sensitivity=causal_module.SensitivityAnalysis(
            method="E_VALUE", robustness_value=2.0, e_value_estimate=1.8, e_value_ci=1.5, is_sensitive_to_unobserved_confounding=False
        ),
        reproducibility_seed=123,
        created_at=now,
    )

    repo.save(study)

    # Retrieval by matching tenant succeeds
    assert repo.get(sample_tenant, s_id) is not None

    # Retrieval by foreign tenant returns None
    foreign_tenant = TenantId("tnt_competitor_corp")
    assert repo.get(foreign_tenant, s_id) is None

    # List by investigation respects tenant boundary
    assert len(repo.list_by_investigation(sample_tenant, sample_investigation_id)) == 1
    assert len(repo.list_by_investigation(foreign_tenant, sample_investigation_id)) == 0
