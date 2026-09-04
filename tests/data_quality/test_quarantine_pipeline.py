"""
RevPilot AI — Quarantine Pipeline and Replay Unit & Contract Tests (Phase 01)
Verifies DATA-QUALITY-LINEAGE-SPEC.md §3, §5, AC-P01-005-01, 02, 03, 04.
"""

from __future__ import annotations
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.data_quality import (
    DataQualityValidator,
    QuarantineRecord,
    QuarantineRepository,
    LineageRecord,
    LineageRecorder,
)


@pytest.fixture
def validator():
    return DataQualityValidator()


@pytest.fixture
def repository():
    return QuarantineRepository()


def test_quarantine_routing_on_invalid_payload(validator, repository):
    """
    AC-P01-005-01: 100% of payloads violating schema, range, or null constraints
    route to QuarantineRepository.
    """
    tenant_id = TenantId("tnt_alpha")
    poisoned_payloads = [
        # Missing id
        {"tenant_id": "tnt_alpha", "event_time": "2026-01-01T00:00:00Z", "total_cents": 1000},
        # Missing tenant_id
        {"id": "ord_001", "event_time": "2026-01-01T00:00:00Z", "total_cents": 1000},
        # Negative monetary amount
        {"tenant_id": "tnt_alpha", "id": "ord_002", "event_time": "2026-01-01T00:00:00Z", "total_cents": -500},
        # Negative quantity
        {"tenant_id": "tnt_alpha", "id": "orl_003", "event_time": "2026-01-01T00:00:00Z", "quantity": -2},
        # Invalid currency
        {"tenant_id": "tnt_alpha", "id": "ord_004", "event_time": "2026-01-01T00:00:00Z", "currency": "BITCOIN"},
    ]

    for idx, payload in enumerate(poisoned_payloads):
        val_res = validator.validate_record(payload, session_tenant_id=tenant_id)
        assert not val_res.is_valid, f"Payload {idx} should have failed validation"
        assert val_res.rule_id is not None
        assert val_res.rejection_reason is not None

        # Route to quarantine
        q_record = QuarantineRecord(
            quarantine_id=f"q_{idx:03d}",
            tenant_id=tenant_id,
            rule_id=val_res.rule_id,
            raw_payload=payload,
            rejection_reason=val_res.rejection_reason,
        )
        repository.quarantine(q_record)

    quarantined = repository.list_quarantined(tenant_id)
    assert len(quarantined) == len(poisoned_payloads)
    for rec in quarantined:
        assert rec.status == "QUARANTINED"
        assert rec.resolved_at is None


def test_canonical_isolation_from_quarantined_records(validator, repository):
    """
    AC-P01-005-02: Zero invalid or quarantined records are visible to canonical entity queries.
    """
    tenant_id = TenantId("tnt_alpha")
    canonical_table: list[dict] = []

    inbound_records = [
        {"tenant_id": "tnt_alpha", "id": "ord_valid_1", "event_time": "2026-01-01T00:00:00Z", "total_cents": 1500, "currency": "USD"},
        {"tenant_id": "tnt_alpha", "id": "ord_bad_2", "event_time": "2026-01-01T00:00:00Z", "total_cents": -999, "currency": "USD"},
        {"tenant_id": "tnt_alpha", "id": "ord_valid_3", "event_time": "2026-01-01T00:00:00Z", "total_cents": 2500, "currency": "USD"},
    ]

    for r in inbound_records:
        val_res = validator.validate_record(r, session_tenant_id=tenant_id)
        if val_res.is_valid:
            canonical_table.append(r)
        else:
            repository.quarantine(
                QuarantineRecord(
                    quarantine_id=f"q_{r.get('id', 'unknown')}",
                    tenant_id=tenant_id,
                    rule_id=val_res.rule_id or "UNKNOWN",
                    raw_payload=r,
                    rejection_reason=val_res.rejection_reason or "Invalid",
                )
            )

    # Assert canonical table contains ONLY valid records
    canonical_ids = {r["id"] for r in canonical_table}
    assert canonical_ids == {"ord_valid_1", "ord_valid_3"}
    assert "ord_bad_2" not in canonical_ids

    # Assert bad record is in quarantine
    quarantined = repository.list_quarantined(tenant_id)
    assert len(quarantined) == 1
    assert quarantined[0].quarantine_id == "q_ord_bad_2"


def test_deterministic_replay_transition_to_reprocessed(validator, repository):
    """
    AC-P01-005-03: Replaying a quarantined record with corrected payload
    transitions its status to 'REPROCESSED'.
    """
    tenant_id = TenantId("tnt_alpha")
    bad_payload = {
        "tenant_id": "tnt_alpha",
        "id": "ord_replay_001",
        "event_time": "2026-01-01T00:00:00Z",
        "total_cents": -5000,
        "currency": "USD",
    }
    q_rec = QuarantineRecord(
        quarantine_id="q_rep_001",
        tenant_id=tenant_id,
        rule_id="DQ-TYP-001",
        raw_payload=bad_payload,
        rejection_reason="total_cents must be a non-negative integer",
    )
    repository.quarantine(q_rec)

    # 1. Attempt replay with still-broken payload -> remains QUARANTINED
    res1 = repository.replay(
        quarantine_id="q_rep_001",
        validator=validator,
        corrected_payload=bad_payload,
    )
    assert res1.is_failure
    stored = repository.get(tenant_id, "q_rep_001")
    assert stored.status == "QUARANTINED"

    # 2. Attempt replay with corrected payload -> transitions to REPROCESSED
    corrected_payload = dict(bad_payload)
    corrected_payload["total_cents"] = 5000

    res2 = repository.replay(
        quarantine_id="q_rep_001",
        validator=validator,
        corrected_payload=corrected_payload,
    )
    assert res2.is_success
    assert res2.unwrap() == corrected_payload

    stored_after = repository.get(tenant_id, "q_rep_001")
    assert stored_after.status == "REPROCESSED"
    assert stored_after.resolved_at is not None
    assert stored_after.resolved_by == "operator_replay"


def test_cross_tenant_injection_fails_with_tenant_mismatch(validator, repository):
    """
    AC-P01-005-04: Cross-tenant payload injection fails with TENANT_MISMATCH_DETECTED
    and generates an audit log.
    """
    session_tenant = TenantId("tnt_alpha")
    injected_payload = {
        "tenant_id": "tnt_beta",  # mismatch!
        "id": "ord_cross_tenant_01",
        "event_time": "2026-01-01T00:00:00Z",
        "total_cents": 1000,
        "currency": "USD",
    }

    initial_audit_count = len(validator.audit_log)
    val_res = validator.validate_record(injected_payload, session_tenant_id=session_tenant)

    assert not val_res.is_valid
    assert val_res.rule_id == "DQ-TEN-001"
    assert val_res.error_code == "TENANT_MISMATCH_DETECTED"

    # Assert security audit log was emitted
    assert len(validator.audit_log) == initial_audit_count + 1
    latest_audit = validator.audit_log[-1]
    assert latest_audit["event_type"] == "SECURITY_TENANT_MISMATCH"
    assert latest_audit["session_tenant_id"] == "tnt_alpha"
    assert latest_audit["payload_tenant_id"] == "tnt_beta"


def test_quarantine_repository_strict_tenant_isolation(repository):
    """INV-TEN-001: list_quarantined never leaks records across tenant boundaries."""
    t_alpha = TenantId("tnt_alpha")
    t_beta = TenantId("tnt_beta")

    rec_a = QuarantineRecord(
        quarantine_id="q_a_1",
        tenant_id=t_alpha,
        rule_id="DQ-REQ-001",
        raw_payload={"tenant_id": "tnt_alpha"},
        rejection_reason="missing id",
    )
    rec_b = QuarantineRecord(
        quarantine_id="q_b_1",
        tenant_id=t_beta,
        rule_id="DQ-REQ-001",
        raw_payload={"tenant_id": "tnt_beta"},
        rejection_reason="missing id",
    )
    repository.quarantine(rec_a)
    repository.quarantine(rec_b)

    alpha_items = repository.list_quarantined(t_alpha)
    beta_items = repository.list_quarantined(t_beta)

    assert len(alpha_items) == 1
    assert alpha_items[0].quarantine_id == "q_a_1"

    assert len(beta_items) == 1
    assert beta_items[0].quarantine_id == "q_b_1"


def test_lineage_recorder_registration():
    """Verify lineage recording and multi-tenant retrieval."""
    recorder = LineageRecorder()
    tenant = TenantId("tnt_alpha")
    record = LineageRecord(
        lineage_id="lin_001",
        tenant_id=tenant,
        source_system="shopify_connector_v1",
        source_batch_id="batch_01",
        raw_payload_hash="sha256:abc123def456",
        transformation_name="TransformShopifyOrdersToCanonical",
        record_counts={"input": 1000, "canonical": 998, "quarantined": 2},
        executed_at=UtcDateTime.now(),
    )
    recorder.record(record)

    fetched = recorder.get_lineage(tenant, "lin_001")
    assert fetched == record

    # Check isolation from another tenant
    assert recorder.get_lineage(TenantId("tnt_beta"), "lin_001") is None
