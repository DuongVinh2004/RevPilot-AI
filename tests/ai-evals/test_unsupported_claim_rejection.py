"""
RevPilot AI — Benchmark Harness for Unsupported Claim Rejection
Specification: docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md
Specification: docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md §3, §4
Verifies GATE-UNSUPPORTED-CLAIMS: Verifier catches and rejects 100% of claims lacking grounded evidence (INV-AI-001).
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
        if mod.startswith("revpilot.modules.hypothesis") or mod.startswith("revpilot.modules.evidence"):
            sys.modules.pop(mod, None)


@pytest.fixture
def hypothesis_module():
    import revpilot.modules.hypothesis as mod
    return mod


def test_gate_unsupported_claim_zero_evidence_fallback(hypothesis_module):
    """
    GATE-UNSUPPORTED-CLAIMS: A candidate claiming an anomaly root cause without
    valid supporting evidence records cannot be verified (INV-AI-001).
    Deterministic fallback to NEED_MORE_EVIDENCE.
    """
    tenant_id = TenantId("tnt_logistics_enterprise")
    investigation_id = UUIDv7.generate()
    now = UtcDateTime.now()

    # Ungrounded claim with 0 supporting evidence and 0 coverage
    h_ungrounded = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_ungrounded_hallucination",
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        statement="A cyber attack caused disruptions",
        hypothesis_type=hypothesis_module.HypothesisType.EXTERNAL_MACRO_EVENT,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[],
        contradicting_evidence=[],
        evidence_coverage_ratio=0.0,
        created_at=now,
        updated_at=now,
    )

    # Decoy to satisfy competition invariant (>= 2)
    h_competitor = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_baseline_competitor",
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        statement="Normal baseline fluctuation",
        hypothesis_type=hypothesis_module.HypothesisType.CUSTOMER_BEHAVIOR_SHIFT,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[],
        contradicting_evidence=[],
        evidence_coverage_ratio=0.20,
        created_at=now,
        updated_at=now,
    )

    ranked = hypothesis_module.rank_competing_hypotheses([h_ungrounded, h_competitor])

    # Assert 0% unsupported claims verified
    for h in ranked:
        assert (
            h.status != hypothesis_module.HypothesisStatus.VERIFIED
        ), f"GATE-UNSUPPORTED-CLAIMS violated: ungrounded hypothesis {h.hypothesis_id} declared VERIFIED"
        assert h.status == hypothesis_module.HypothesisStatus.NEED_MORE_EVIDENCE
