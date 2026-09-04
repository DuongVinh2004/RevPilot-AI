"""
RevPilot AI — Phase 08 Composite Production Readiness Exit Gate Contract Tests
Specification: docs/24-sre/PRODUCTION-READINESS-GATE.md §1..§11
Specification: docs/29-testing/TEST-STRATEGY.md §13 (TC-P08-001..028)
Specification: execution/DEFINITION-OF-DONE.md §3, §4
Conforms to INV-REL-002, AC-P08-008-01, and TC-P08-028.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from revpilot.modules.operations.readiness.models import GateVerdict
from revpilot.modules.operations.review.exit_runner import (
    CANONICAL_PHASE_08_CATEGORIES,
    ExitGateBlockedError,
    Phase08ExitGateRunner,
    Phase08ExitSummary,
)


@pytest.fixture
def exit_runner() -> Phase08ExitGateRunner:
    return Phase08ExitGateRunner()


def test_phase_08_composite_exit_gate_all_28_categories_pass(
    exit_runner: Phase08ExitGateRunner,
    tmp_path: Path,
):
    """
    AC-P08-008-01 & TC-P08-028: PASS only if all 28 Phase 08 test categories
    (TC-P08-001..028) execute with 100% passing status (INV-REL-002).
    """
    bundle_file = tmp_path / "2026-Q3-phase08-bundle.tar.gz"
    bundle_file.write_bytes(b"mock_sealed_phase08_evidence_bundle")

    summary = exit_runner.execute_full_exit_evaluation(
        evidence_bundle_path=bundle_file,
        enforce_pass=True,
    )

    assert isinstance(summary, Phase08ExitSummary)
    assert summary.verdict == GateVerdict.PRODUCTION_READY
    assert summary.passed_categories_count == 28
    assert summary.total_categories_count == 28
    assert summary.evidence_bundle_path == bundle_file
    assert summary.timestamp is not None
    assert len(summary.category_results) == 28

    # Ensure each of the 28 canonical categories is evaluated and PASS
    for cat in CANONICAL_PHASE_08_CATEGORIES:
        assert summary.category_results[cat] == "PASS"


def test_phase_08_exit_gate_subtest_failure_raises_blocked_error(
    exit_runner: Phase08ExitGateRunner,
):
    """
    Verify that any failed category triggers EXIT_GATE_BLOCKED (500) (INV-REL-002).
    """
    # Simulate failures on TC-P08-018 (kill switch) and TC-P08-019 (cold restore)
    overrides = {
        "TC-P08-018": False,
        "TC-P08-019": False,
    }

    with pytest.raises(ExitGateBlockedError) as exc_info:
        exit_runner.execute_full_exit_evaluation(
            category_overrides=overrides,
            enforce_pass=True,
        )

    err = exc_info.value
    assert err.code == "EXIT_GATE_BLOCKED"
    assert err.status_code == 500
    assert err.retryable is False
    assert "TC-P08-018" in err.details["failed_categories"]
    assert "TC-P08-019" in err.details["failed_categories"]
    assert err.details["passed_count"] == 26
    assert err.details["total_count"] == 28


def test_phase_08_exit_gate_non_enforcing_returns_blocked_verdict(
    exit_runner: Phase08ExitGateRunner,
):
    """
    Verify non-raising mode returns PRODUCTION_BLOCKED verdict without raising exception.
    """
    overrides = {"TC-P08-001": False}
    summary = exit_runner.execute_full_exit_evaluation(
        category_overrides=overrides,
        enforce_pass=False,
    )

    assert summary.verdict == GateVerdict.PRODUCTION_BLOCKED
    assert summary.passed_categories_count == 27
    assert summary.category_results["TC-P08-001"] == "FAILED"
