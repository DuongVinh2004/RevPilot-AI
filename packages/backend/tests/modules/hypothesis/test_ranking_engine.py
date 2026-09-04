"""
RevPilot AI — Unit and Verification Tests for Competing-Cause Ranking Engine
Specification: docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md §3, §4
Conforms to BR-001, BR-002, FR-RCA-001, FR-RCA-002, INV-AI-001..002, INV-TEN-001, and AC-004.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_hypothesis_module():
    """Ensure hypothesis and evidence modules are purged from sys.modules."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.hypothesis") or mod.startswith("revpilot.modules.evidence"):
            sys.modules.pop(mod, None)


@pytest.fixture
def hypothesis_module():
    import revpilot.modules.hypothesis as mod
    return mod


@pytest.fixture
def evidence_module():
    import revpilot.modules.evidence as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_us_logistics")


@pytest.fixture
def sample_investigation_id() -> UUIDv7:
    return UUIDv7.generate()


def test_multi_hypothesis_competition_invariant_enforced(
    hypothesis_module, sample_tenant, sample_investigation_id
):
    """FR-RCA-001 / AC-004: Ranking must reject single-hypothesis submissions."""
    now = UtcDateTime.now()
    single_h = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_solo",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Single hypothesis statement",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(hypothesis_module.HypothesisError) as exc_info:
        hypothesis_module.rank_competing_hypotheses([single_h])
    assert exc_info.value.code == "ERR_MULTI_HYPOTHESIS_VIOLATION"


def test_cross_tenant_hypothesis_ranking_forbidden(
    hypothesis_module, sample_tenant, sample_investigation_id
):
    """INV-TEN-001: Cannot rank hypotheses belonging to different tenants."""
    now = UtcDateTime.now()
    h1 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_alpha",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Alpha statement",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )
    h2 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_beta",
        investigation_id=sample_investigation_id,
        tenant_id=TenantId("tnt_other_corp"),
        statement="Beta statement",
        hypothesis_type=hypothesis_module.HypothesisType.PAYMENT_GATEWAY_OUTAGE,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(hypothesis_module.HypothesisError) as exc_info:
        hypothesis_module.rank_competing_hypotheses([h1, h2])
    assert exc_info.value.code == "ERR_TENANT_MISMATCH"


def test_cross_tenant_evidence_bundle_forbidden(
    hypothesis_module, evidence_module, sample_tenant, sample_investigation_id
):
    """INV-TEN-001: Evidence bundle must match candidate hypotheses tenant."""
    now = UtcDateTime.now()
    h1 = hypothesis_module.HypothesisRecord(
        hypothesis_id="h1",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Statement 1",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )
    h2 = hypothesis_module.HypothesisRecord(
        hypothesis_id="h2",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Statement 2",
        hypothesis_type=hypothesis_module.HypothesisType.PAYMENT_GATEWAY_OUTAGE,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )

    foreign_bundle = evidence_module.EvidenceBundle(
        bundle_id=UUIDv7.generate(),
        investigation_id=sample_investigation_id,
        tenant_id=TenantId("tnt_foreign_firm"),
        evidence_count=0,
        evidence_items=[],
        bundle_digest="abc",
        sealed_at=now,
    )

    with pytest.raises(hypothesis_module.HypothesisError) as exc_info:
        hypothesis_module.rank_competing_hypotheses([h1, h2], bundle=foreign_bundle)
    assert exc_info.value.code == "ERR_TENANT_MISMATCH"


def test_contradiction_veto_rule(hypothesis_module, sample_tenant, sample_investigation_id):
    """Contradiction Veto: If S_con >= 0.80, status is REFUTED and demoted below non-refuted."""
    now = UtcDateTime.now()
    con_ev = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_con",
        relevance_score=0.85,
        polarity="CONTRADICTING",
        provenance_source="payment_gateway_logs",
    )
    h_refuted = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_refuted",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Payment gateway outage",
        hypothesis_type=hypothesis_module.HypothesisType.PAYMENT_GATEWAY_OUTAGE,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        contradicting_evidence=[con_ev],
        evidence_coverage_ratio=0.8,
        created_at=now,
        updated_at=now,
    )
    h_valid = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_valid",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Logistics bottleneck",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        evidence_coverage_ratio=0.5,
        created_at=now,
        updated_at=now,
    )

    ranked = hypothesis_module.rank_competing_hypotheses([h_refuted, h_valid])
    assert ranked[0].hypothesis_id == "hypo_valid"
    assert ranked[1].hypothesis_id == "hypo_refuted"
    assert ranked[1].status == hypothesis_module.HypothesisStatus.REFUTED
    assert ranked[1].ordinal_rank == 2


def test_need_more_evidence_fallback_when_low_coverage(
    hypothesis_module, sample_tenant, sample_investigation_id
):
    """FR-RCA-002: Deterministic fallback to NEED_MORE_EVIDENCE when coverage < 0.75."""
    now = UtcDateTime.now()
    sup_ev = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_sup",
        relevance_score=0.95,
        polarity="SUPPORTING",
        provenance_source="warehouse_metrics",
    )
    h1 = hypothesis_module.HypothesisRecord(
        hypothesis_id="h1_low_coverage",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Truck capacity shortage with partial telemetry",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[sup_ev],
        evidence_coverage_ratio=0.60,  # Below 0.75 threshold
        created_at=now,
        updated_at=now,
    )
    h2 = hypothesis_module.HypothesisRecord(
        hypothesis_id="h2_decoy",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Decoy candidate",
        hypothesis_type=hypothesis_module.HypothesisType.CUSTOMER_BEHAVIOR_SHIFT,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        evidence_coverage_ratio=0.30,
        created_at=now,
        updated_at=now,
    )

    ranked = hypothesis_module.rank_competing_hypotheses([h1, h2])
    assert ranked[0].hypothesis_id == "h1_low_coverage"
    # Cannot be VERIFIED because coverage < 0.75
    assert ranked[0].status == hypothesis_module.HypothesisStatus.NEED_MORE_EVIDENCE


def test_midwest_truck_capacity_canonical_benchmark(
    hypothesis_module, sample_tenant, sample_investigation_id
):
    """
    Verification of Synthetic Benchmark §4 & §6:
    - H1 (Logistics) -> VERIFIED (Rank 1)
    - H2 (Payment Decoy) -> REFUTED
    - H3 (Product Decoy) -> REFUTED
    """
    now = UtcDateTime.now()

    # H1: Midwest capacity shortage
    sup_dispatch = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_disp",
        relevance_score=0.92,
        polarity="SUPPORTING",
        provenance_source="carrier_dispatch_latency_84h",
    )
    sup_tickets = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_tkt",
        relevance_score=0.88,
        polarity="SUPPORTING",
        provenance_source="ticket_volume_spike_4.5x",
    )
    h1 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_midwest_capacity_01",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Fleet shortage at regional carrier caused dispatch backlog at WH-MIDWEST-01",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={"region": "US-MIDWEST", "facility": "WH-MIDWEST-01"},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[sup_dispatch, sup_tickets],
        contradicting_evidence=[],
        evidence_coverage_ratio=0.85,
        created_at=now,
        updated_at=now,
    )

    # H2: Payment gateway outage (decoy refuted by metric steady at 1.2%)
    con_payment = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_pay",
        relevance_score=0.95,
        polarity="CONTRADICTING",
        provenance_source="metric_payment_failure_rate_steady_1.2pct",
    )
    h2 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_payment_decoy_02",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Checkout payment failure caused cancellations",
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

    # H3: Product quality defect (decoy refuted by return reasons showing delay)
    sup_returns = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_ret",
        relevance_score=0.30,
        polarity="SUPPORTING",
        provenance_source="return_volume_table",
    )
    con_return_reasons = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_reasons",
        relevance_score=0.90,
        polarity="CONTRADICTING",
        provenance_source="return_reasons_89pct_delivery_delay",
    )
    h3 = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_product_defect_decoy_03",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="SKU-8899 batch defects prompted customer cancellations",
        hypothesis_type=hypothesis_module.HypothesisType.PRODUCT_QUALITY_DEFECT,
        affected_scope={"region": "US-MIDWEST"},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[sup_returns],
        contradicting_evidence=[con_return_reasons],
        evidence_coverage_ratio=0.75,
        created_at=now,
        updated_at=now,
    )

    ranked = hypothesis_module.rank_competing_hypotheses([h1, h2, h3])

    # Assertions
    assert len(ranked) == 3
    assert ranked[0].hypothesis_id == "hypo_midwest_capacity_01"
    assert ranked[0].ordinal_rank == 1
    assert ranked[0].status == hypothesis_module.HypothesisStatus.VERIFIED
    assert set(ranked[0].alternative_hypothesis_ids) == {
        "hypo_payment_decoy_02",
        "hypo_product_defect_decoy_03",
    }

    assert ranked[1].status == hypothesis_module.HypothesisStatus.REFUTED
    assert ranked[2].status == hypothesis_module.HypothesisStatus.REFUTED
    assert ranked[0].manifest_digest != ""


def test_ambiguous_competing_causes_tie_detection(
    hypothesis_module, sample_tenant, sample_investigation_id
):
    """Verify co-equal ranking flag when score difference <= 0.05."""
    now = UtcDateTime.now()
    sup_ev = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_tie",
        relevance_score=0.80,
        polarity="SUPPORTING",
        provenance_source="shared_telemetry",
    )
    h1 = hypothesis_module.HypothesisRecord(
        hypothesis_id="h1_mech_a",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Mechanism A",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[sup_ev],
        evidence_coverage_ratio=0.80,
        created_at=now,
        updated_at=now,
    )
    h2 = hypothesis_module.HypothesisRecord(
        hypothesis_id="h2_mech_b",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Mechanism B",
        hypothesis_type=hypothesis_module.HypothesisType.CUSTOMER_BEHAVIOR_SHIFT,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[sup_ev],
        evidence_coverage_ratio=0.80,
        created_at=now,
        updated_at=now,
    )

    ranked = hypothesis_module.rank_competing_hypotheses([h1, h2])
    # Both have identical score, difference is 0.0 <= 0.05
    assert any("AMBIGUOUS_COMPETING_CAUSES" in lim for lim in ranked[0].limitations)
    assert any("AMBIGUOUS_COMPETING_CAUSES" in lim for lim in ranked[1].limitations)


def test_causal_study_bonus_applied(hypothesis_module, sample_tenant, sample_investigation_id):
    """Verify causal_study_id grants causal bonus to ranking score."""
    now = UtcDateTime.now()
    sup_ev = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="dig_causal_test",
        relevance_score=1.0,
        polarity="SUPPORTING",
        provenance_source="test_source",
    )
    h_without = hypothesis_module.HypothesisRecord(
        hypothesis_id="h_no_causal",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Observation without causal study",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        supporting_evidence=[sup_ev],
        evidence_coverage_ratio=1.0,
        created_at=now,
        updated_at=now,
    )
    h_with = h_without.model_copy(
        update={"hypothesis_id": "h_with_causal", "causal_study_id": UUIDv7.generate()}
    )

    score_without = hypothesis_module.calculate_hypothesis_score(h_without)
    score_with = hypothesis_module.calculate_hypothesis_score(h_with)

    assert score_with > score_without
    assert pytest.approx(score_with - score_without, 0.01) == 0.30
