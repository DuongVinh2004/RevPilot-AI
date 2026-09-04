"""
RevPilot AI — Unit Tests for Uplift Domain Models & Invariants
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md §2
Conforms to BR-002, BR-005, FR-ML-003, INV-AI-001, and INV-TEN-001.
"""

from __future__ import annotations
import sys
import pytest
from pydantic import ValidationError

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_uplift_module():
    """Ensure uplift module is cleaned between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.uplift"):
            sys.modules.pop(mod, None)


@pytest.fixture
def uplift_module():
    import revpilot.modules.uplift as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_enterprise")


def test_uplift_score_record_frozen_invariant(uplift_module, sample_tenant):
    """Verify UpliftScoreRecord is immutable and typed strictly."""
    now = UtcDateTime.now()
    score = uplift_module.UpliftScoreRecord(
        score_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        customer_id="cust_1001",
        intervention_type="SERVICE_CREDIT_VOUCHER",
        as_of_time=now,
        model_artifact_id="t_learner_v1_run42",
        cate_estimate=0.1250,
        standard_error=0.0150,
        confidence_interval_95=(0.0956, 0.1544),
        persuadability_segment=uplift_module.PersuadabilitySegment.PERSUADABLE,
        overlap_satisfied=True,
        feature_snapshot_digest="dig_feat_abc",
        created_at=now,
    )

    assert score.cate_estimate == 0.1250
    assert score.persuadability_segment == uplift_module.PersuadabilitySegment.PERSUADABLE

    with pytest.raises(ValidationError):
        score.cate_estimate = 0.2000


def test_compute_uplift_digest_deterministic(uplift_module, sample_tenant):
    """Verify compute_uplift_digest is deterministic and produces SHA-256."""
    s_id = UUIDv7.generate()
    d1 = uplift_module.compute_uplift_digest(
        score_id=s_id,
        tenant_id=sample_tenant,
        customer_id="cust_2002",
        intervention_type="EXPEDITED_SHIPPING",
        cate_estimate=0.0820,
        persuadability_segment=uplift_module.PersuadabilitySegment.PERSUADABLE,
        feature_snapshot_digest="feat_xyz",
    )
    d2 = uplift_module.compute_uplift_digest(
        score_id=s_id,
        tenant_id=sample_tenant,
        customer_id="cust_2002",
        intervention_type="EXPEDITED_SHIPPING",
        cate_estimate=0.0820,
        persuadability_segment=uplift_module.PersuadabilitySegment.PERSUADABLE,
        feature_snapshot_digest="feat_xyz",
    )

    assert d1 == d2
    assert len(d1) == 64


def test_in_memory_uplift_repository_isolation(uplift_module, sample_tenant):
    """Verify single-tenant isolation in Uplift repository."""
    repo = uplift_module.InMemoryUpliftRepository()
    now = UtcDateTime.now()
    s_id = UUIDv7.generate()

    record = uplift_module.UpliftScoreRecord(
        score_id=s_id,
        tenant_id=sample_tenant,
        customer_id="cust_alpha",
        intervention_type="VOUCHER",
        as_of_time=now,
        model_artifact_id="model_1",
        cate_estimate=0.05,
        standard_error=0.01,
        confidence_interval_95=(0.03, 0.07),
        persuadability_segment=uplift_module.PersuadabilitySegment.PERSUADABLE,
        overlap_satisfied=True,
        feature_snapshot_digest="dig_1",
        created_at=now,
    )

    repo.save(record)

    # Valid tenant retrieval
    assert repo.get(sample_tenant, s_id) is not None

    # Competitor tenant retrieval fails
    foreign_tenant = TenantId("tnt_competitor")
    assert repo.get(foreign_tenant, s_id) is None

    # List by customer
    assert len(repo.list_by_customer(sample_tenant, "cust_alpha")) == 1
    assert len(repo.list_by_customer(foreign_tenant, "cust_alpha")) == 0
