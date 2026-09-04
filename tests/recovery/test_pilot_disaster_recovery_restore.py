"""
RevPilot AI — TC-P07-027: Pilot Disaster Recovery Restore Rehearsal Test
Specification: docs/24-sre/DR-PLAN.md §2, §3
Conforms to AC-P07-008-02, NFR-REC-001, and INV-REL-001.
"""

from __future__ import annotations
import sys
import pytest


@pytest.fixture(autouse=True)
def _isolate_operations_module():
    """Ensure operations module is isolated in test environment."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.operations"):
            sys.modules.pop(mod, None)


def test_pilot_disaster_recovery_restore_rehearsal_and_slas():
    """
    TC-P07-027 / AC-P07-008-02:
    - Verifies disaster recovery restoration achieves RTO <= 30 minutes and RPO <= 5 minutes.
    - Enforces restoration order across KMS, DB, Audit, IAM, S3, Temporal, and Vector rebuild.
    - Verifies disposable projections (vector embeddings, cache) are deterministically rebuilt.
    """
    from revpilot.modules.operations import RehearsalRunner

    runner = RehearsalRunner()
    report = runner.run_rehearsal_suite("REH-P07-01")

    # 1. Recovery SLAs Verification (AC-P07-008-02)
    assert report.passed is True
    assert report.measured_rto_minutes <= 30.0, f"RTO {report.measured_rto_minutes}m exceeded 30m SLA"
    assert report.measured_rpo_minutes <= 5.0, f"RPO {report.measured_rpo_minutes}m exceeded 5m SLA"

    # 2. Dependency Order Verification (DR-PLAN.md §2.3)
    assert len(report.restoration_steps) == 8
    assert "KMS" in report.restoration_steps[0]
    assert "PostgreSQL" in report.restoration_steps[1]
    assert "Audit Ledger" in report.restoration_steps[2]
    assert "IAM" in report.restoration_steps[3]
    assert "Object Storage" in report.restoration_steps[4]
    assert "Temporal" in report.restoration_steps[5]
    assert "Vector" in report.restoration_steps[6]
    assert "API Gateway" in report.restoration_steps[7]

    # 3. Disposable Projection Rebuilding Verification
    assert "vector_embeddings_index" in report.rebuilt_projections
    assert "redis_session_cache" in report.rebuilt_projections
