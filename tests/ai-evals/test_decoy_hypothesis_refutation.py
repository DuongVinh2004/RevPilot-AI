"""
RevPilot AI — Benchmark Harness for Decoy Hypothesis Refutation
Specification: docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md §3, §4
Specification: docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md §3, §4
Verifies GATE-DECOY-REFUTATION: Both payment outage and product defect decoys marked REFUTED (FR-RCA-001).
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_modules():
    """Ensure modules are purged from sys.modules to prevent collection-time contract violations."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.hypothesis"):
            sys.modules.pop(mod, None)


@pytest.fixture
def hypothesis_module():
    import revpilot.modules.hypothesis as mod
    return mod


def test_gate_decoy_refutation_rate_100_percent(hypothesis_module):
    """
    GATE-DECOY-REFUTATION: Verifies that 100% of contradictory decoy hypotheses
    are formally refuted via Contradiction Veto (S_con >= 0.80).
    """
    tenant_id = TenantId("tnt_logistics_enterprise")
    investigation_id = UUIDv7.generate()
    now = UtcDateTime.now()

    # Legitimate root cause
    h_legit = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_true_cause",
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        statement="Regional fleet truck capacity deficit",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        evidence_coverage_ratio=0.85,
        created_at=now,
        updated_at=now,
    )

    # Decoy 1: Contradicted by steady payment metric
    con_payment = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_payment",
        relevance_score=0.92,
        polarity="CONTRADICTING",
        provenance_source="payment_gateway_monitoring",
    )
    h_decoy_payment = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_decoy_payment",
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        statement="Payment gateway outage caused cancellations",
        hypothesis_type=hypothesis_module.HypothesisType.PAYMENT_GATEWAY_OUTAGE,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        contradicting_evidence=[con_payment],
        evidence_coverage_ratio=0.80,
        created_at=now,
        updated_at=now,
    )

    # Decoy 2: Contradicted by return reasons
    con_defect = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_defect",
        relevance_score=0.89,
        polarity="CONTRADICTING",
        provenance_source="returns_root_cause_analysis",
    )
    h_decoy_defect = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_decoy_defect",
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        statement="Product defect caused customer churn",
        hypothesis_type=hypothesis_module.HypothesisType.PRODUCT_QUALITY_DEFECT,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        contradicting_evidence=[con_defect],
        evidence_coverage_ratio=0.75,
        created_at=now,
        updated_at=now,
    )

    ranked = hypothesis_module.rank_competing_hypotheses([h_legit, h_decoy_payment, h_decoy_defect])

    # Find decoys in output
    ranked_map = {h.hypothesis_id: h for h in ranked}

    # GATE-DECOY-REFUTATION: 100% of decoys must be REFUTED
    assert (
        ranked_map["hypo_decoy_payment"].status == hypothesis_module.HypothesisStatus.REFUTED
    ), "GATE-DECOY-REFUTATION violated: Payment decoy was not marked REFUTED"

    assert (
        ranked_map["hypo_decoy_defect"].status == hypothesis_module.HypothesisStatus.REFUTED
    ), "GATE-DECOY-REFUTATION violated: Defect decoy was not marked REFUTED"
