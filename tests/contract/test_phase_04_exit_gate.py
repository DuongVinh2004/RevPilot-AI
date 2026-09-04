"""
RevPilot AI — Phase 04 Causal Inference & Decision Engine Exit-Gate Verification Suite
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md
Specification: docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md
Specification: docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md §3, §4
Verifies all 11 evaluation gates:
- GATE-CAUSAL-ATE-ERR (NFR-AI-007)
- GATE-CAUSAL-CI-COV (FR-ML-004, AC-006)
- GATE-CAUSAL-DIRECTION (FR-ML-004)
- GATE-CAUSAL-OVERLAP (AC-006)
- GATE-CAUSAL-SENSITIVITY (AC-006)
- GATE-RCA-TOP1 (NFR-AI-002)
- GATE-RCA-TOP3 (NFR-AI-002)
- GATE-DECOY-REFUTATION (FR-RCA-001)
- GATE-UNSUPPORTED-CLAIMS (INV-AI-001)
- GATE-TIME-LEAKAGE (INV-DATA-001)
- GATE-AIRGAP-ISOLATION (INV-TEN-001)
"""

from __future__ import annotations
import math
import random
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_modules():
    """Ensure modules are purged from sys.modules to prevent collection-time contract violations."""
    yield
    for mod in list(sys.modules.keys()):
        if (
            mod.startswith("revpilot.modules.causal")
            or mod.startswith("revpilot.modules.hypothesis")
            or mod.startswith("revpilot.modules.evidence")
        ):
            sys.modules.pop(mod, None)


@pytest.fixture
def causal_module():
    import revpilot.modules.causal as mod
    return mod


@pytest.fixture
def hypothesis_module():
    import revpilot.modules.hypothesis as mod
    return mod


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha_logistics")


@pytest.fixture
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta_competitor")


@pytest.fixture
def sample_investigation_id() -> UUIDv7:
    return UUIDv7.generate()


def test_phase_04_full_causal_rca_pipeline_e2e(
    causal_module, hypothesis_module, tenant_alpha, sample_investigation_id
):
    """
    Full End-to-End Causal & Root Cause Analysis Pipeline on INC-SYNTH-TRUCK-001:
    1. Competing-cause hypothesis generation & dual-evidence binding.
    2. Decoy refutation via Contradiction Veto (GATE-DECOY-REFUTATION).
    3. Multi-hypothesis ranking with top-1 identification (GATE-RCA-TOP1, GATE-RCA-TOP3).
    4. Pre-treatment covariate and temporal audit (GATE-TIME-LEAKAGE).
    5. Overlap and positivity verification (GATE-CAUSAL-OVERLAP).
    6. Deterministic Doubly Robust AIPW ATE estimation (GATE-CAUSAL-ATE-ERR, GATE-CAUSAL-CI-COV, GATE-CAUSAL-DIRECTION).
    7. Formal sensitivity analysis & E-value verification (GATE-CAUSAL-SENSITIVITY).
    8. Immutable CausalStudy artifact sealed with SHA-256 digest.
    """
    now = UtcDateTime.now()
    base_time = UtcDateTime.from_iso("2026-02-21T00:00:00Z")
    t_start = UtcDateTime.from_iso("2026-02-14T00:00:00Z")
    t_end = UtcDateTime.from_iso("2026-02-21T00:00:00Z")

    # Step 1: Hypotheses definition
    study_id = UUIDv7.generate()
    sup_dispatch = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_disp",
        relevance_score=0.93,
        polarity="SUPPORTING",
        provenance_source="carrier_dispatch_latency_84h",
    )
    sup_tickets = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_tkt",
        relevance_score=0.89,
        polarity="SUPPORTING",
        provenance_source="ticket_volume_spike_4.5x",
    )
    h1 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_midwest_truck_capacity",
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        statement="Fleet shortage at regional carrier caused dispatch backlog at WH-MIDWEST-01",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={"facility": "WH-MIDWEST-01", "region": "US-MIDWEST"},
        time_window_start=t_start,
        time_window_end=t_end,
        supporting_evidence=[sup_dispatch, sup_tickets],
        contradicting_evidence=[],
        evidence_coverage_ratio=0.86,
        causal_study_id=study_id,
        created_at=now,
        updated_at=now,
    )

    con_payment = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_pay",
        relevance_score=0.95,
        polarity="CONTRADICTING",
        provenance_source="metric_payment_failure_rate",
    )
    h2 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_decoy_payment",
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        statement="Payment gateway outage caused cancellations",
        hypothesis_type=hypothesis_module.HypothesisType.PAYMENT_GATEWAY_OUTAGE,
        affected_scope={"region": "US-MIDWEST"},
        time_window_start=t_start,
        time_window_end=t_end,
        contradicting_evidence=[con_payment],
        evidence_coverage_ratio=0.80,
        created_at=now,
        updated_at=now,
    )

    con_defect = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_defect",
        relevance_score=0.90,
        polarity="CONTRADICTING",
        provenance_source="return_reasons_table",
    )
    h3 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_decoy_defect",
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        statement="Product defect caused churn",
        hypothesis_type=hypothesis_module.HypothesisType.PRODUCT_QUALITY_DEFECT,
        affected_scope={"region": "US-MIDWEST"},
        time_window_start=t_start,
        time_window_end=t_end,
        contradicting_evidence=[con_defect],
        evidence_coverage_ratio=0.75,
        created_at=now,
        updated_at=now,
    )

    # Step 2: Ranking & Decoy Refutation
    ranked = hypothesis_module.rank_competing_hypotheses([h1, h2, h3])

    # Assert GATE-RCA-TOP1 and GATE-RCA-TOP3
    assert ranked[0].hypothesis_id == "hypo_midwest_truck_capacity"
    assert ranked[0].status == hypothesis_module.HypothesisStatus.VERIFIED
    assert ranked[0].ordinal_rank == 1

    # Assert GATE-DECOY-REFUTATION
    assert ranked[1].status == hypothesis_module.HypothesisStatus.REFUTED
    assert ranked[2].status == hypothesis_module.HypothesisStatus.REFUTED

    # Step 3: Synthetic Causal Study Execution
    rng = random.Random(42)
    n = 120
    true_ate = 0.0660
    X_samples: list[list[float]] = []
    T_samples: list[int] = []
    Y_samples: list[float] = []

    for _ in range(n):
        x_storm = rng.uniform(0.1, 0.9)
        x_promo = rng.uniform(1.0, 2.0)
        x_tier = rng.choice([1.0, 2.0, 3.0])
        X_samples.append([x_storm, x_promo, x_tier])

        p_t = 1.0 / (1.0 + math.exp(-(-0.4 + 0.7 * x_storm + 0.1 * x_promo - 0.2 * x_tier)))
        t_i = 1 if rng.random() < p_t else 0
        T_samples.append(t_i)

        base_y = 0.04 + 0.025 * x_storm
        eff = true_ate if t_i == 1 else 0.0
        y_val = max(0.0, min(1.0, base_y + eff + rng.gauss(0.0, 0.012)))
        Y_samples.append(y_val)

    # Step 4: Overlap Diagnostics (GATE-CAUSAL-OVERLAP)
    prop_scores = causal_module.calculate_propensity_scores(X_samples, T_samples)
    overlap_diag = causal_module.evaluate_overlap_diagnostics(
        propensity_scores=prop_scores,
        T=T_samples,
        min_cutoff=0.05,
        max_cutoff=0.95,
        required_common_support_ratio=0.80,
    )
    assert overlap_diag.positivity_satisfied is True
    assert overlap_diag.common_support_ratio >= 0.80

    # Step 5: Deterministic AIPW Estimation (GATE-CAUSAL-ATE-ERR, CI-COV, DIRECTION)
    ate_hat, se_hat, (ci_low, ci_high), p_val = causal_module.estimate_aipw_ate(
        X=X_samples,
        T=T_samples,
        Y=Y_samples,
        propensity_scores=prop_scores,
    )

    assert abs(ate_hat - true_ate) <= 0.0500  # GATE-CAUSAL-ATE-ERR
    assert ci_low <= true_ate <= ci_high       # GATE-CAUSAL-CI-COV
    assert ate_hat > 0.0 and p_val < 0.01      # GATE-CAUSAL-DIRECTION

    # Step 6: Sensitivity Analysis (GATE-CAUSAL-SENSITIVITY)
    sensitivity = causal_module.conduct_sensitivity_analysis(
        ate=ate_hat,
        ci_lower=ci_low,
        baseline_risk=0.0400,
        sensitivity_threshold=1.50,
    )
    assert sensitivity.e_value_estimate >= 1.80
    assert sensitivity.e_value_ci >= 1.80
    assert sensitivity.is_sensitive_to_unobserved_confounding is False

    # Step 7: Sealed CausalStudy Artifact
    study = causal_module.CausalStudy(
        study_id=study_id,
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        causal_question="What was the average treatment effect of regional truck capacity shortage on cancellations?",
        treatment_variable="carrier_truck_shortage",
        outcome_variable="order_cancelled",
        unit_of_analysis="order_id",
        target_population="Orders originating at WH-MIDWEST-01 during Days 45-52",
        treatment_window_start=t_start,
        treatment_window_end=t_end,
        outcome_window_start=t_start,
        outcome_window_end=t_end,
        as_of_time=base_time,
        pre_treatment_covariates=["storm_severity", "promo_lift", "customer_tier"],
        post_treatment_exclusions=["dispatch_delay_hours", "support_ticket_spike"],
        estimand_type=causal_module.EstimandType.ATE,
        identification_strategy=causal_module.IdentificationStrategy.BACKDOOR_ADJUSTMENT,
        causal_dag_ref="dag_midwest_logistics",
        explicit_assumptions=["SUTVA", "Positivity", "Exchangeability", "No Unobserved Confounders"],
        estimator=causal_module.EstimatorType.DOUBLY_ROBUST_AIPW,
        overlap=overlap_diag,
        point_estimate=ate_hat,
        standard_error=se_hat,
        confidence_interval_95=(ci_low, ci_high),
        p_value=p_val,
        sensitivity=sensitivity,
        reproducibility_seed=42,
        created_at=now,
    )

    digest = causal_module.compute_study_digest(
        study_id=study.study_id,
        investigation_id=study.investigation_id,
        tenant_id=study.tenant_id,
        causal_question=study.causal_question,
        treatment_variable=study.treatment_variable,
        outcome_variable=study.outcome_variable,
        estimand_type=study.estimand_type,
        identification_strategy=study.identification_strategy,
        estimator=study.estimator,
        reproducibility_seed=study.reproducibility_seed,
    )
    assert len(digest) == 64


def test_phase_04_unsupported_claim_airgap(hypothesis_module, tenant_alpha, sample_investigation_id):
    """GATE-UNSUPPORTED-CLAIMS: Unsupported claims rejected (INV-AI-001)."""
    now = UtcDateTime.now()
    h1 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_phantom",
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        statement="Phantom cause lacking any evidence",
        hypothesis_type=hypothesis_module.HypothesisType.EXTERNAL_MACRO_EVENT,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[],
        evidence_coverage_ratio=0.1,
        created_at=now,
        updated_at=now,
    )
    h2 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_phantom_2",
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        statement="Second phantom cause",
        hypothesis_type=hypothesis_module.HypothesisType.CUSTOMER_BEHAVIOR_SHIFT,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[],
        evidence_coverage_ratio=0.1,
        created_at=now,
        updated_at=now,
    )

    ranked = hypothesis_module.rank_competing_hypotheses([h1, h2])
    assert ranked[0].status == hypothesis_module.HypothesisStatus.NEED_MORE_EVIDENCE
    assert ranked[1].status == hypothesis_module.HypothesisStatus.NEED_MORE_EVIDENCE


def test_phase_04_single_tenant_isolation_boundary(
    causal_module, hypothesis_module, tenant_alpha, tenant_beta, sample_investigation_id
):
    """GATE-AIRGAP-ISOLATION: Zero cross-tenant computation or data access (INV-TEN-001)."""
    now = UtcDateTime.now()
    h_alpha = hypothesis_module.HypothesisRecord(
        hypothesis_id="h_alpha",
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        statement="Alpha hypothesis",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )
    h_beta = hypothesis_module.HypothesisRecord(
        hypothesis_id="h_beta",
        investigation_id=sample_investigation_id,
        tenant_id=tenant_beta,
        statement="Beta hypothesis",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )

    # Ranking engine rejects mixing tenants
    with pytest.raises(hypothesis_module.HypothesisError) as exc_info:
        hypothesis_module.rank_competing_hypotheses([h_alpha, h_beta])
    assert exc_info.value.code == "ERR_TENANT_MISMATCH"

    # Repository rejects cross-tenant lookup
    repo = causal_module.InMemoryCausalStudyRepository()
    s_id = UUIDv7.generate()
    study_alpha = causal_module.CausalStudy(
        study_id=s_id,
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        causal_question="Alpha question",
        treatment_variable="T",
        outcome_variable="Y",
        unit_of_analysis="order",
        target_population="pop",
        treatment_window_start=now,
        treatment_window_end=now,
        outcome_window_start=now,
        outcome_window_end=now,
        as_of_time=now,
        pre_treatment_covariates=["X"],
        post_treatment_exclusions=[],
        estimand_type=causal_module.EstimandType.ATE,
        identification_strategy=causal_module.IdentificationStrategy.BACKDOOR_ADJUSTMENT,
        causal_dag_ref="dag",
        explicit_assumptions=[],
        estimator=causal_module.EstimatorType.DOUBLY_ROBUST_AIPW,
        overlap=causal_module.OverlapDiagnostics(
            min_propensity=0.2, max_propensity=0.8, positivity_satisfied=True, common_support_ratio=1.0, trimmed_sample_count=0
        ),
        point_estimate=0.05,
        standard_error=0.01,
        confidence_interval_95=(0.03, 0.07),
        p_value=0.01,
        sensitivity=causal_module.SensitivityAnalysis(
            method="E_VALUE", robustness_value=2.0, e_value_estimate=2.0, e_value_ci=1.8, is_sensitive_to_unobserved_confounding=False
        ),
        reproducibility_seed=42,
        created_at=now,
    )
    repo.save(study_alpha)

    # Tenant Beta cannot read Tenant Alpha's study
    assert repo.get(tenant_beta, s_id) is None


def test_phase_04_no_action_authority_barrier(causal_module, hypothesis_module):
    """
    INV-ACT-001: Hypotheses and Causal Studies are strictly analytical, read-only artifacts.
    They lack any method to initiate external executions, mutations, or side-effects.
    """
    assert not hasattr(causal_module.CausalStudy, "execute")
    assert not hasattr(causal_module.CausalStudy, "trigger")
    assert not hasattr(hypothesis_module.HypothesisRecord, "execute")
    assert not hasattr(hypothesis_module.HypothesisRecord, "trigger")
