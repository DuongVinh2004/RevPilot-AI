"""
RevPilot AI — Unit and Invariant Tests for Hypothesis Domain Models
Specification: docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md §1, §2, §5
Conforms to BR-001, BR-002, FR-RCA-001, FR-RCA-002, INV-AI-001, INV-TEN-001, and AC-013.
"""

from __future__ import annotations
import sys
import pytest
from pydantic import ValidationError

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_hypothesis_module():
    """Ensure hypothesis module is isolated and sys.modules is purged after each test."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.hypothesis"):
            sys.modules.pop(mod, None)


@pytest.fixture
def hypothesis_module():
    """Lazily load hypothesis module inside test scope."""
    import revpilot.modules.hypothesis as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_alpha_corp")


@pytest.fixture
def sample_investigation_id() -> UUIDv7:
    return UUIDv7.generate()


def test_epistemic_categories_completeness(hypothesis_module):
    """Verify all 8 strict ontological categories from §1.1 exist."""
    cat = hypothesis_module.EpistemicCategory
    expected = [
        "OBSERVATION",
        "DERIVED_STATISTIC",
        "ASSOCIATION",
        "MECHANISM_HYPOTHESIS",
        "STATISTICAL_SIGNAL",
        "CAUSAL_HYPOTHESIS",
        "CAUSAL_ESTIMATE",
        "RECOMMENDATION",
    ]
    for exp in expected:
        assert hasattr(cat, exp)
        assert getattr(cat, exp).value == exp


def test_hypothesis_record_creation_and_frozen_invariant(
    hypothesis_module, sample_tenant, sample_investigation_id
):
    """Verify HypothesisRecord is immutable and enforces frozen attributes."""
    now = UtcDateTime.now()
    record = hypothesis_module.HypothesisRecord(
        hypothesis_id="hypo_test_01",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Test hypothesis statement",
        epistemic_category=hypothesis_module.EpistemicCategory.MECHANISM_HYPOTHESIS,
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={"region": "US-MIDWEST"},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )
    assert record.hypothesis_id == "hypo_test_01"
    assert record.status == hypothesis_module.HypothesisStatus.PROPOSED
    assert record.ranking_score == 0.0

    # Invariant: Record is frozen
    with pytest.raises(ValidationError):
        record.ranking_score = 0.5


def test_no_chain_of_thought_leakage_ac013(hypothesis_module, sample_tenant, sample_investigation_id):
    """
    AC-013 / INV-AI-002: HypothesisRecord schema must not contain scratchpad,
    prompt, raw LLM thinking, or chain-of-thought fields.
    """
    field_names = set(hypothesis_module.HypothesisRecord.model_fields.keys())
    prohibited = {"chain_of_thought", "thought", "scratchpad", "internal_reasoning", "raw_prompt", "cot"}
    found = field_names.intersection(prohibited)
    assert len(found) == 0, f"Prohibited CoT fields leaked in HypothesisRecord: {found}"


def test_deterministic_hypothesis_digest(hypothesis_module, sample_tenant, sample_investigation_id):
    """Verify compute_hypothesis_digest produces deterministic SHA-256 hex digest."""
    now = UtcDateTime.now()
    ev = hypothesis_module.EvidenceWeight(
        evidence_id=UUIDv7.generate(),
        content_digest="abc1234",
        relevance_score=0.9,
        polarity="SUPPORTING",
        provenance_source="test_metric",
    )
    digest_1 = hypothesis_module.compute_hypothesis_digest(
        hypothesis_id="hypo_1",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Same statement",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        supporting_evidence=[ev],
        contradicting_evidence=[],
    )
    digest_2 = hypothesis_module.compute_hypothesis_digest(
        hypothesis_id="hypo_1",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Same statement",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        supporting_evidence=[ev],
        contradicting_evidence=[],
    )
    assert digest_1 == digest_2
    assert len(digest_1) == 64


def test_in_memory_repository_tenant_isolation(
    hypothesis_module, sample_tenant, sample_investigation_id
):
    """Verify repository strictly isolates hypotheses across tenant boundaries."""
    repo = hypothesis_module.InMemoryHypothesisRepository()
    now = UtcDateTime.now()

    h1 = hypothesis_module.HypothesisRecord(
        hypothesis_id="h_alpha",
        investigation_id=sample_investigation_id,
        tenant_id=sample_tenant,
        statement="Alpha hypothesis",
        hypothesis_type=hypothesis_module.HypothesisType.LOGISTICS_BOTTLENECK,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )
    foreign_tenant = TenantId("tnt_beta_corp")
    h2 = hypothesis_module.HypothesisRecord(
        hypothesis_id="h_beta",
        investigation_id=sample_investigation_id,
        tenant_id=foreign_tenant,
        statement="Beta hypothesis",
        hypothesis_type=hypothesis_module.HypothesisType.PAYMENT_GATEWAY_OUTAGE,
        affected_scope={},
        time_window_start=now,
        time_window_end=now,
        created_at=now,
        updated_at=now,
    )

    repo.save(h1)
    repo.save(h2)

    # Fetching by foreign tenant must return None
    assert repo.get(foreign_tenant, "h_alpha") is None
    assert repo.get(sample_tenant, "h_beta") is None

    # Fetching by valid tenant
    assert repo.get(sample_tenant, "h_alpha") == h1
    assert repo.get(foreign_tenant, "h_beta") == h2

    # Listing by investigation respects tenant boundary
    alpha_list = repo.list_by_investigation(sample_tenant, sample_investigation_id)
    assert len(alpha_list) == 1
    assert alpha_list[0].hypothesis_id == "h_alpha"
