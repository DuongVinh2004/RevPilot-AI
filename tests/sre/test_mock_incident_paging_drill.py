"""
RevPilot AI — Mock P0 Incident Response & On-Call Paging Drill Tests
Specification: docs/24-sre/INCIDENT-RESPONSE-RUNBOOK.md §1..§6
Specification: docs/24-sre/PRODUCTION-READINESS-GATE.md §10
Conforms to INV-REL-002, AC-P08-008-02, and TC-P08-025.
"""

from __future__ import annotations

import pytest

from revpilot.modules.operations.review.incident_drill import (
    DrillResult,
    IncidentDrillRunner,
    PagingDrillTimeoutError,
)


@pytest.fixture
def drill_runner() -> IncidentDrillRunner:
    return IncidentDrillRunner()


def test_mock_p0_paging_alert_within_15_minutes(drill_runner: IncidentDrillRunner):
    """
    AC-P08-008-02 & TC-P08-025: Mock P0 paging alert successfully verifies
    on-call notification within 15 minutes (< 900s).
    """
    result = drill_runner.simulate_p0_paging_drill(
        max_allowed_seconds=900.0,
        simulated_latency_sec=180.0,  # 3 minutes
    )

    assert isinstance(result, DrillResult)
    assert result.status == "PASS"
    assert result.severity == "P0"
    assert result.on_call_acknowledged is True
    assert result.paging_latency_seconds == 180.0
    assert result.paging_latency_seconds < 900.0
    assert result.acknowledged_by == "primary_oncall_sre"
    assert result.incident_id.startswith("inc_")
    assert result.timestamp is not None


def test_mock_p0_paging_timeout_breaches_sla_raises_error(drill_runner: IncidentDrillRunner):
    """
    Verify that on-call paging latency > 15 minutes triggers PAGING_DRILL_TIMEOUT (500).
    """
    with pytest.raises(PagingDrillTimeoutError) as exc_info:
        drill_runner.simulate_p0_paging_drill(
            max_allowed_seconds=900.0,
            simulated_latency_sec=1050.0,  # 17.5 minutes
        )

    err = exc_info.value
    assert err.code == "PAGING_DRILL_TIMEOUT"
    assert err.status_code == 500
    assert err.retryable is False
    assert err.details["paging_latency_seconds"] == 1050.0
    assert err.details["sla_limit_seconds"] == 900.0
