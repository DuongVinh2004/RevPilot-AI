"""
RevPilot AI — Unit Tests for Causal Covariate and Temporal Anti-Leakage Audit
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §1.1, §5
Conforms to BR-001, BR-002, FR-ML-003, FR-ML-004, INV-AI-001, INV-DATA-001, and AC-006.
"""

from __future__ import annotations
import sys
import pytest
from datetime import timedelta

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_causal_module():
    """Purge causal module between test runs."""
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
    return TenantId("tnt_logistics_corp")


@pytest.fixture
def sample_investigation_id() -> UUIDv7:
    return UUIDv7.generate()


def test_pre_treatment_covariate_audit_detects_collider_overlap(causal_module):
    """Detects post-treatment variable erroneously included in adjustment set."""
    covariates = ["customer_tier", "order_subtotal", "delivery_delay_hours"]
    exclusions = ["delivery_delay_hours", "support_ticket_count"]

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.audit_pre_treatment_covariates(
            pre_treatment_covariates=covariates,
            post_treatment_exclusions=exclusions,
        )
    assert exc_info.value.code == "ERR_POST_TREATMENT_COLLIDER"
    assert "delivery_delay_hours" in str(exc_info.value.details)


def test_pre_treatment_covariate_audit_detects_metadata_mediator(causal_module):
    """Detects post-treatment variable via semantic metadata role."""
    covariates = ["customer_tier", "support_ticket_spike"]
    metadata = {
        "customer_tier": {"role": "CONFOUNDER", "is_post_treatment": False},
        "support_ticket_spike": {"role": "MEDIATOR", "is_post_treatment": True},
    }

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.audit_pre_treatment_covariates(
            pre_treatment_covariates=covariates,
            post_treatment_exclusions=[],
            variable_metadata=metadata,
        )
    assert exc_info.value.code == "ERR_POST_TREATMENT_COLLIDER"


def test_pre_treatment_covariate_audit_rejects_empty_set(causal_module):
    """Observational causal inference requires at least one covariate."""
    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.audit_pre_treatment_covariates([], [])
    assert exc_info.value.code == "ERR_EMPTY_COVARIATE_SET"


def test_temporal_leakage_audit_detects_future_record(causal_module):
    """INV-DATA-001: Records with timestamp > as_of_time trigger ERR_TEMPORAL_LEAKAGE."""
    as_of = UtcDateTime.now()
    treatment_start = UtcDateTime(as_of.value - timedelta(days=5))

    leaked_record = {
        "order_id": "ord_1001",
        "timestamp": UtcDateTime(as_of.value + timedelta(hours=2)).isoformat(),
        "status": "CANCELLED",
    }

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.audit_temporal_leakage(
            as_of_time=as_of,
            treatment_window_start=treatment_start,
            records=[leaked_record],
        )
    assert exc_info.value.code == "ERR_TEMPORAL_LEAKAGE"


def test_temporal_leakage_audit_detects_post_treatment_covariate(causal_module):
    """Covariates must strictly precede treatment window start."""
    now = UtcDateTime.now()
    treatment_start = UtcDateTime(now.value - timedelta(days=3))
    as_of = now

    covariate_times = {
        "customer_tier": UtcDateTime(treatment_start.value - timedelta(days=10)),
        "order_subtotal": UtcDateTime(treatment_start.value + timedelta(hours=1)),  # Occurred AFTER treatment start
    }

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.audit_temporal_leakage(
            as_of_time=as_of,
            treatment_window_start=treatment_start,
            covariate_timestamps=covariate_times,
        )
    assert exc_info.value.code == "ERR_TEMPORAL_LEAKAGE"


def test_midwest_truck_capacity_specification_passes_audit(
    causal_module, sample_tenant, sample_investigation_id
):
    """Canonical Midwest Truck-Capacity incident specification passes full audit."""
    base_time = UtcDateTime.from_iso("2026-02-21T00:00:00Z")
    t_start = UtcDateTime.from_iso("2026-02-14T00:00:00Z")
    t_end = UtcDateTime.from_iso("2026-02-21T00:00:00Z")
    o_start = UtcDateTime.from_iso("2026-02-14T00:00:00Z")
    o_end = UtcDateTime.from_iso("2026-02-21T00:00:00Z")

    covariates = ["customer_tier", "order_subtotal", "shipping_service_level", "product_category"]
    exclusions = ["actual_dispatch_delay", "support_ticket_created"]

    study = causal_module.CausalStudy(
        study_id=UUIDv7.generate(),
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        causal_question="What was the average treatment effect of regional truck capacity shortage at WH-MIDWEST-01 on order cancellations?",
        treatment_variable="carrier_truck_shortage",
        outcome_variable="order_cancelled",
        unit_of_analysis="order_id",
        target_population="Orders originating at WH-MIDWEST-01 during Days 45-52",
        treatment_window_start=t_start,
        treatment_window_end=t_end,
        outcome_window_start=o_start,
        outcome_window_end=o_end,
        as_of_time=base_time,
        pre_treatment_covariates=covariates,
        post_treatment_exclusions=exclusions,
        estimand_type=causal_module.EstimandType.ATE,
        identification_strategy=causal_module.IdentificationStrategy.BACKDOOR_ADJUSTMENT,
        causal_dag_ref="dag_midwest_fulfillment",
        explicit_assumptions=["SUTVA", "Positivity", "Exchangeability", "No Unobserved Confounders"],
        estimator=causal_module.EstimatorType.DOUBLY_ROBUST_AIPW,
        overlap=causal_module.OverlapDiagnostics(
            min_propensity=0.15,
            max_propensity=0.85,
            positivity_satisfied=True,
            common_support_ratio=1.0,
            trimmed_sample_count=0,
        ),
        point_estimate=0.0660,
        standard_error=0.0110,
        confidence_interval_95=(0.0444, 0.0876),
        p_value=0.0001,
        sensitivity=causal_module.SensitivityAnalysis(
            method="E_VALUE",
            robustness_value=2.40,
            e_value_estimate=2.12,
            e_value_ci=1.78,
            is_sensitive_to_unobserved_confounding=False,
        ),
        reproducibility_seed=42,
        created_at=base_time,
    )

    # Valid pre-treatment records within as_of watermark
    records = [
        {"order_id": "ord_001", "timestamp": "2026-02-15T12:00:00Z", "cancelled": 1},
        {"order_id": "ord_002", "timestamp": "2026-02-18T16:00:00Z", "cancelled": 0},
    ]

    covariate_times = {
        "customer_tier": UtcDateTime.from_iso("2026-02-01T00:00:00Z"),
        "order_subtotal": UtcDateTime.from_iso("2026-02-10T00:00:00Z"),
        "shipping_service_level": UtcDateTime.from_iso("2026-02-10T00:00:00Z"),
        "product_category": UtcDateTime.from_iso("2026-02-01T00:00:00Z"),
    }

    # Should execute without raising any error
    causal_module.audit_causal_study_specification(
        study=study,
        records=records,
        covariate_timestamps=covariate_times,
    )
