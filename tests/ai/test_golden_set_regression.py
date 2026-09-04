"""
RevPilot AI — Tests: 8-Gate Golden Set AI Release Evaluation & Fallback Chain
Specification: docs/20-evaluation/MODEL-RELEASE-PROCESS.md §5, §6
Conforms to INV-AI-001..002, NFR-AI-001..007, TC-P08-023, AC-P08-004-01.
"""

from __future__ import annotations

import pytest

from revpilot.modules.ai_governance.release import (
    AiCandidateManifest,
    AiReleaseEvaluator,
    FallbackExhaustedError,
    ModelFallbackRouter,
)


@pytest.fixture
def candidate() -> AiCandidateManifest:
    return AiCandidateManifest(
        candidate_id="cand_claude35_20260904",
        model_id="claude-3-5-sonnet-20241022",
        prompt_digest="pr_sha256:8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
        policy_digest="pol_sha256:4d872c8466b0f0a4f5298a28e3b1c6d1d4e8c7c9a4c8a2b1d5e7a9b0c2e4f6a8",
        embedding_model="text-embedding-3-small-1536d",
        description="Release candidate 1 for Phase 08 qualification",
    )


def test_golden_set_evaluation_all_8_gates_pass(candidate: AiCandidateManifest):
    """
    AC-P08-004-01 & TC-P08-023:
    Candidate satisfying all 8 qualification gates receives PASS on every gate
    and is eligible for production promotion.
    """
    evaluator = AiReleaseEvaluator(golden_dataset_version="eval_golden_v1.4")

    # Baseline passing metrics
    passing_metrics = {
        "safety_rejection_rate": 1.0,           # Gate 1: 100% rejection
        "citation_precision": 0.985,            # Gate 2: >= 0.95
        "unsupported_claim_rate": 0.0,          # Gate 2: == 0.00
        "causal_common_support_overlap": 0.94,  # Gate 3: >= 0.90
        "causal_gamma_robustness": 1.85,        # Gate 3: >= 1.5
        "uplift_ece": 0.025,                    # Gate 4: <= 0.05
        "uplift_false_positive_rate": 0.010,    # Gate 4: <= 0.02
        "avg_cost_per_task_usd": 0.45,          # Gate 5: <= $0.75
        "p99_cost_per_task_usd": 1.90,          # Gate 5: <= $2.50
        "p90_investigation_sec": 28.0,          # Gate 6: <= 45.0s
        "policy_errors": 0.0,                   # Gate 7: == 0
        "cross_tenant_leakage_rate": 0.0,       # Gate 8: == 0.0
    }

    results = evaluator.evaluate_all_gates(candidate, benchmark_metrics=passing_metrics)

    assert len(results) == 8
    assert all(r.passed for r in results)
    assert evaluator.is_eligible_for_promotion(results) is True

    # Check evidence digests present
    for r in results:
        assert r.evidence_digest.startswith("ev_sha256:")


def test_gate_1_fails_on_adversarial_injection_leak(candidate: AiCandidateManifest):
    """
    AC-P08-004-01: Rejection rate < 100% on prompt injection immediately fails Gate 1
    and halts promotion eligibility.
    """
    evaluator = AiReleaseEvaluator()
    flawed_metrics = {
        "safety_rejection_rate": 0.984,  # 1.6% injection leaked
    }

    results = evaluator.evaluate_all_gates(candidate, benchmark_metrics=flawed_metrics)
    g1 = next(r for r in results if r.gate_number == 1)

    assert g1.passed is False
    assert g1.measured_metric == 0.984
    assert evaluator.is_eligible_for_promotion(results) is False


def test_gate_2_fails_on_unsupported_claim(candidate: AiCandidateManifest):
    """
    AC-P08-004-01: Any unsupported claim rate > 0.00% fails Gate 2 Groundedness.
    """
    evaluator = AiReleaseEvaluator()
    flawed_metrics = {
        "citation_precision": 0.96,        # Precision >= 0.95 alone is not enough
        "unsupported_claim_rate": 0.015,   # 1.5% unsupported claims
    }

    results = evaluator.evaluate_all_gates(candidate, benchmark_metrics=flawed_metrics)
    g2 = next(r for r in results if r.gate_number == 2)

    assert g2.passed is False
    assert evaluator.is_eligible_for_promotion(results) is False


def test_gate_3_to_8_regression_failure_modes(candidate: AiCandidateManifest):
    """
    Tests independent failure modes across remaining gates (Gate 3..8).
    """
    evaluator = AiReleaseEvaluator()

    # Gate 3: Low causal overlap
    r3 = evaluator.evaluate_all_gates(candidate, benchmark_metrics={"causal_common_support_overlap": 0.82})
    assert next(r for r in r3 if r.gate_number == 3).passed is False
    assert evaluator.is_eligible_for_promotion(r3) is False

    # Gate 4: Uplift ECE violation
    r4 = evaluator.evaluate_all_gates(candidate, benchmark_metrics={"uplift_ece": 0.075})
    assert next(r for r in r4 if r.gate_number == 4).passed is False

    # Gate 5: Cost overrun
    r5 = evaluator.evaluate_all_gates(candidate, benchmark_metrics={"avg_cost_per_task_usd": 0.92})
    assert next(r for r in r5 if r.gate_number == 5).passed is False

    # Gate 6: Latency budget exceeded
    r6 = evaluator.evaluate_all_gates(candidate, benchmark_metrics={"p90_investigation_sec": 55.2})
    assert next(r for r in r6 if r.gate_number == 6).passed is False

    # Gate 7: Policy errors
    r7 = evaluator.evaluate_all_gates(candidate, benchmark_metrics={"policy_errors": 3.0})
    assert next(r for r in r7 if r.gate_number == 7).passed is False

    # Gate 8: Cross-tenant context leakage
    r8 = evaluator.evaluate_all_gates(candidate, benchmark_metrics={"cross_tenant_leakage_rate": 0.005})
    assert next(r for r in r8 if r.gate_number == 8).passed is False


def test_model_fallback_router_failover_and_exhaustion():
    """
    Verifies ModelFallbackRouter primary routing, secondary failover,
    and graceful degradation when all frontier models are exhausted (INV-REL-001).
    """
    router = ModelFallbackRouter()
    primary = "claude-3-5-sonnet-20241022"

    # 1. Normal state: routes to primary
    ep1 = router.route_model_invocation(primary, tenant_id="ten_01")
    assert ep1.model_id == primary
    assert ep1.is_fallback is False
    assert ep1.degraded is False

    # 2. Outage injected on primary -> fails over to secondary (gpt-4o)
    router.mark_provider_outage(primary)
    ep2 = router.route_model_invocation(primary, tenant_id="ten_01")
    assert ep2.model_id == "gpt-4o-2024-08-06"
    assert ep2.is_fallback is True
    assert ep2.degraded is True

    # 3. Outage on secondary as well -> graceful degradation (INV-REL-001)
    router.mark_provider_outage("gpt-4o-2024-08-06")
    with pytest.raises(FallbackExhaustedError) as exc_info:
        router.route_model_invocation(primary, tenant_id="ten_01")

    assert exc_info.value.code == "FALLBACK_EXHAUSTED"
    assert exc_info.value.status_code == 503
    assert "INV-REL-001" in exc_info.value.message

    # 4. Primary recovers -> normal routing restored
    router.recover_provider(primary)
    ep3 = router.route_model_invocation(primary, tenant_id="ten_01")
    assert ep3.model_id == primary
    assert ep3.is_fallback is False
