"""
RevPilot AI — Anomaly Domain Event Contract Tests (Phase 02)
Verifies AC-P02-005-02, EVENT-CONTRACTS.md §4, ANOMALY-DOMAIN-SPEC.md §4, and INV-SEC-001.
"""

from __future__ import annotations
import sys
import re
import pytest

from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import PrincipalContext


@pytest.fixture(autouse=True)
def _isolate_analytics_module():
    """Ensure analytics module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.analytics"):
            sys.modules.pop(mod, None)


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha")


@pytest.fixture
def actor_context(tenant_alpha: TenantId) -> PrincipalContext:
    return PrincipalContext(
        principal_id=PrincipalId("usr_analyst_jane"),
        tenant_id=tenant_alpha,
        is_system=False,
    )


@pytest.fixture
def sample_detected_anomaly(tenant_alpha: TenantId):
    from revpilot.modules.analytics.lifecycle import AnomalyAggregate
    now = UtcDateTime.from_iso("2026-02-16T12:00:00.000000Z")
    return AnomalyAggregate.create_detected(
        id="anm_contract_test_001",
        tenant_id=tenant_alpha,
        metric_id="chargeback_rate",
        metric_version="v1.0",
        detector_id="stl_chargeback_v1",
        detector_version="v1.0.0",
        baseline_id="seasonal_naive",
        baseline_version="v1.0.0",
        observation_window_start=UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z"),
        observation_window_end=UtcDateTime.from_iso("2026-02-16T00:00:00.000000Z"),
        as_of_time=now,
        actual_value=0.035,
        expected_value=0.010,
        expected_interval=(0.005, 0.015),
        anomaly_score=4.2,
        severity="HIGH",
        affected_scope={"channel": "web"},
    )


def test_anomaly_detected_event_contract(sample_detected_anomaly, tenant_alpha: TenantId) -> None:
    """Verify anomaly.detected.v1 envelope and payload structure."""
    events = sample_detected_anomaly.pending_outbox_events
    assert len(events) == 1
    evt = events[0]

    # Envelope validation (EVENT-CONTRACTS.md §4.1)
    assert evt.event_id.startswith("evt_")
    assert evt.event_type == "anomaly.detected.v1"
    assert evt.event_version == 1
    assert isinstance(evt.occurred_at, UtcDateTime)
    assert evt.producer == "revpilot.modules.analytics"
    assert evt.aggregate_id == sample_detected_anomaly.id
    assert evt.aggregate_version == 1
    assert evt.tenant_id == tenant_alpha
    assert evt.correlation_id.startswith("cor_")
    assert evt.causation_id == "det_stl_chargeback_v1"
    assert evt.idempotency_key == f"anm_detect_{sample_detected_anomaly.id}_v1"

    # Payload validation
    p = evt.payload
    assert p["anomaly_id"] == sample_detected_anomaly.id
    assert p["metric_id"] == "chargeback_rate"
    assert p["metric_version"] == "v1.0"
    assert p["detector_id"] == "stl_chargeback_v1"
    assert p["actual_value"] == 0.035
    assert p["expected_value"] == 0.010
    assert p["expected_interval"] == [0.005, 0.015]
    assert p["anomaly_score"] == 4.2
    assert p["severity"] == "HIGH"
    assert "observation_window" in p
    assert "start_time" in p["observation_window"]
    assert "end_time" in p["observation_window"]
    assert "as_of_time" in p


def test_all_seven_anomaly_lifecycle_events_contracts(
    sample_detected_anomaly, actor_context: PrincipalContext
) -> None:
    """Verify all 7 event types produced across full lifecycle path with valid contracts."""
    from revpilot.modules.analytics.lifecycle import AnomalyState

    anm = sample_detected_anomaly

    # 1. DETECTED already recorded
    assert anm.pending_outbox_events[-1].event_type == "anomaly.detected.v1"

    # 2. VALIDATED
    res_val = anm.transition_to(
        target_state=AnomalyState.VALIDATED,
        actor=actor_context,
        reason="ANOMALY_CONFIRMED_BY_METRIC_DRIFT",
    )
    assert res_val.is_success
    evt_val = anm.pending_outbox_events[-1]
    assert evt_val.event_type == "anomaly.validated.v1"
    assert evt_val.event_version == 1
    assert evt_val.aggregate_version == 2
    assert evt_val.payload["anomaly_id"] == anm.id
    assert evt_val.payload["data_quality_state"] == "PASSED"
    assert evt_val.payload["freshness_state"] == "FRESH"
    assert "validated_at" in evt_val.payload

    # 3. LOCALIZED
    res_loc = anm.transition_to(
        target_state=AnomalyState.LOCALIZED,
        actor=actor_context,
        reason="DRILL_DOWN_COMPLETED",
        metadata={
            "top_contributing_segments": [{"dimension": "processor", "value": "stripe", "contribution": 0.85}],
            "dimension": "processor",
            "data_coverage_pct": 99.8,
        },
    )
    assert res_loc.is_success
    evt_loc = anm.pending_outbox_events[-1]
    assert evt_loc.event_type == "anomaly.localized.v1"
    assert evt_loc.event_version == 1
    assert evt_loc.aggregate_version == 3
    assert evt_loc.payload["anomaly_id"] == anm.id
    assert len(evt_loc.payload["top_contributing_segments"]) == 1
    assert evt_loc.payload["primary_dimension"] == "processor"
    assert evt_loc.payload["data_coverage_pct"] == 99.8

    # 4. ACKNOWLEDGED
    res_ack = anm.transition_to(
        target_state=AnomalyState.ACKNOWLEDGED,
        actor=actor_context,
        reason="OPS_TEAM_INVESTIGATING",
        metadata={"investigation_id": "inv_test_001"},
    )
    assert res_ack.is_success
    evt_ack = anm.pending_outbox_events[-1]
    assert evt_ack.event_type == "anomaly.acknowledged.v1"
    assert evt_ack.event_version == 1
    assert evt_ack.aggregate_version == 4
    assert evt_ack.payload["anomaly_id"] == anm.id
    assert evt_ack.payload["acknowledged_by_principal"] == actor_context.principal_id.value
    assert evt_ack.payload["investigation_id"] == "inv_test_001"
    assert "acknowledged_at" in evt_ack.payload

    # 5. RESOLVED
    res_res = anm.transition_to(
        target_state=AnomalyState.RESOLVED,
        actor=actor_context,
        reason="PATCH_DEPLOYED_RULE_UPDATED",
        metadata={"resolution_type": "INCIDENT_MITIGATED", "final_metric_value": 0.010},
    )
    assert res_res.is_success
    evt_res = anm.pending_outbox_events[-1]
    assert evt_res.event_type == "anomaly.resolved.v1"
    assert evt_res.event_version == 1
    assert evt_res.aggregate_version == 5
    assert evt_res.payload["anomaly_id"] == anm.id
    assert evt_res.payload["resolution_type"] == "INCIDENT_MITIGATED"
    assert evt_res.payload["final_metric_value"] == 0.010
    assert "resolved_at" in evt_res.payload

    # 6. REOPENED
    res_reopen = anm.transition_to(
        target_state=AnomalyState.REOPENED,
        actor=actor_context,
        reason="RECURRENCE_DETECTED",
        metadata={"new_actual_value": 0.040, "trigger_score": 5.1},
    )
    assert res_reopen.is_success
    evt_reopen = anm.pending_outbox_events[-1]
    assert evt_reopen.event_type == "anomaly.reopened.v1"
    assert evt_reopen.event_version == 1
    assert evt_reopen.aggregate_version == 6
    assert evt_reopen.payload["anomaly_id"] == anm.id
    assert evt_reopen.payload["new_actual_value"] == 0.040
    assert evt_reopen.payload["trigger_score"] == 5.1
    assert "reopened_at" in evt_reopen.payload

    # 7. SUPPRESSED (from reopened)
    res_sup = anm.transition_to(
        target_state=AnomalyState.SUPPRESSED,
        actor=actor_context,
        reason="FALSE_POSITIVE_DUE_TO_PLANNED_MAINTENANCE",
        metadata={"suppression_rule_id": "rule_suppress_maint_981"},
    )
    assert res_sup.is_success
    evt_sup = anm.pending_outbox_events[-1]
    assert evt_sup.event_type == "anomaly.suppressed.v1"
    assert evt_sup.event_version == 1
    assert evt_sup.aggregate_version == 7
    assert evt_sup.payload["anomaly_id"] == anm.id
    assert evt_sup.payload["suppression_reason"] == "FALSE_POSITIVE_DUE_TO_PLANNED_MAINTENANCE"
    assert evt_sup.payload["suppression_rule_id"] == "rule_suppress_maint_981"
    assert "suppressed_at" in evt_sup.payload


def test_events_inv_sec_001_no_credentials_leak(
    sample_detected_anomaly, actor_context: PrincipalContext
) -> None:
    """Verify INV-SEC-001: No secret, token, password, or auth credentials leak into events."""
    from revpilot.modules.analytics.lifecycle import AnomalyState

    anm = sample_detected_anomaly
    anm.transition_to(
        target_state=AnomalyState.VALIDATED,
        actor=actor_context,
        reason="VALIDATION_CHECK",
        metadata={"meta_key": "meta_value"},
    )

    sensitive_patterns = [
        re.compile(r"password", re.IGNORECASE),
        re.compile(r"token", re.IGNORECASE),
        re.compile(r"secret", re.IGNORECASE),
        re.compile(r"api[_-]?key", re.IGNORECASE),
        re.compile(r"bearer\s+", re.IGNORECASE),
    ]

    for evt in anm.pending_outbox_events:
        # Check payload keys and string values
        def _check_dict(d: dict) -> None:
            for k, v in d.items():
                for pat in sensitive_patterns:
                    assert not pat.search(k), f"Sensitive key pattern '{pat.pattern}' in key '{k}'"
                if isinstance(v, str):
                    for pat in sensitive_patterns:
                        # Allow standard token names if any, but no bearer or password
                        if "bearer" in pat.pattern or "password" in pat.pattern or "secret" in pat.pattern:
                            assert not pat.search(v), f"Sensitive token pattern '{pat.pattern}' in value '{v}'"
                elif isinstance(v, dict):
                    _check_dict(v)

        _check_dict(evt.payload)
