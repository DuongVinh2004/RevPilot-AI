"""
RevPilot AI — Benchmark Harness for Competing Hypothesis Ranking (Top-1 / Top-3)
Specification: docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md §3, §4
Specification: docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md §3, §4
Verifies:
- GATE-RCA-TOP1: Injected truck capacity shortage ranked as primary root cause (NFR-AI-002)
- GATE-RCA-TOP3: True root cause included in top 3 ranked hypotheses (NFR-AI-002)
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
        if mod.startswith("revpilot.modules.hypothesis") or mod.startswith("revpilot.modules.causal"):
            sys.modules.pop(mod, None)


@pytest.fixture
def hypothesis_module():
    import revpilot.modules.hypothesis as mod
    return mod


def test_gate_rca_top1_and_top3_midwest_incident(hypothesis_module):
    """
    Evaluates competing-cause ranking on incident INC-SYNTH-TRUCK-001.
    Confirms H1 (truck capacity) achieves Rank 1 (Top-1) and Status VERIFIED,
    with decoys H2 and H3 ranked below and REFUTED.
    """
    tenant_id = TenantId("tnt_logistics_enterprise")
    investigation_id = UUIDv7.generate()
    now = UtcDateTime.now()

    # Leading Hypothesis H1: Carrier truck capacity shortage
    sup_dispatch = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_disp_84h",
        relevance_score=0.94,
        polarity="SUPPORTING",
        provenance_source="carrier_dispatch_latency",
    )
    sup_tickets = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_tkt_spike",
        relevance_score=0.90,
        polarity="SUPPORTING",
        provenance_source="support_ticket_volume",
    )
    h1_truck = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_midwest_truck_capacity",
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        statement="Fleet shortage at regional carrier caused dispatch backlog at WH-MIDWEST-01",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={"facility": "WH-MIDWEST-01", "region": "US-MIDWEST"},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[sup_dispatch, sup_tickets],
        contradicting_evidence=[],
        evidence_coverage_ratio=0.88,
        causal_study_id=UUIDv7.generate(),
        created_at=now,
        updated_at=now,
    )

    # Decoy H2: Payment Gateway Outage
    con_payment = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_pay_steady",
        relevance_score=0.96,
        polarity="CONTRADICTING",
        provenance_source="metric_payment_failure_rate",
    )
    h2_payment = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_payment_outage_decoy",
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        statement="Payment gateway outage caused checkout drop-offs and cancellations",
        hypothesis_type=hypothesis_module.HypothesisType.PAYMENT_GATEWAY_OUTAGE,
        affected_scope={"region": "US-MIDWEST"},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[],
        contradicting_evidence=[con_payment],
        evidence_coverage_ratio=0.80,
        created_at=now,
        updated_at=now,
    )

    # Decoy H3: Product Quality Defect
    con_defect = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_defect_delay_reason",
        relevance_score=0.88,
        polarity="CONTRADICTING",
        provenance_source="return_reasons_table",
    )
    h3_defect = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_product_defect_decoy",
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        statement="Defective batch prompted returns and cancellations",
        hypothesis_type=hypothesis_module.HypothesisType.PRODUCT_QUALITY_DEFECT,
        affected_scope={"region": "US-MIDWEST"},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[],
        contradicting_evidence=[con_defect],
        evidence_coverage_ratio=0.75,
        created_at=now,
        updated_at=now,
    )

    ranked = hypothesis_module.rank_competing_hypotheses([h1_truck, h2_payment, h3_defect])

    # 1. GATE-RCA-TOP1: True cause is Rank 1
    assert ranked[0].hypothesis_id == "hypo_midwest_truck_capacity"
    assert ranked[0].ordinal_rank == 1
    assert ranked[0].status == hypothesis_module.HypothesisStatus.VERIFIED

    # 2. GATE-RCA-TOP3: True cause in top 3
    top3_ids = [h.hypothesis_id for h in ranked[:3]]
    assert "hypo_midwest_truck_capacity" in top3_ids

    # 3. Decoys refuted
    assert ranked[1].status == hypothesis_module.HypothesisStatus.REFUTED
    assert ranked[2].status == hypothesis_module.HypothesisStatus.REFUTED
