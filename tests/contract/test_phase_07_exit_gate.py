"""
RevPilot AI — TC-P07-028: Phase 07 Composite Exit Gate Verification Suite
Specification: docs/29-testing/TEST-STRATEGY.md §12 (TC-P07-001..028)
Specification: docs/24-sre/PILOT-ONBOARDING-AND-RECOVERY-SPEC.md §3, §4
Enforces AC-009, AC-010, INV-TEN-001..003, INV-SEC-001, INV-COST-001, and INV-REL-001.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId


@pytest.fixture(autouse=True)
def _isolate_operations_module():
    """Ensure operations module is isolated in test environment."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.operations"):
            sys.modules.pop(mod, None)


def test_phase_07_composite_exit_gate_execution():
    """
    TC-P07-028: Phase 07 Composite Exit Gate.
    Verifies that all 8 micro-tasks (TASK-P07-001..008) and 28 criteria of Phase 07 pass with 100% success.
    Verifies pilot onboarding checklist completeness and zero cross-tenant leakage.
    """
    from revpilot.modules.operations import (
        PilotOnboardingVerifier,
        Phase07ExitGateVerifier,
        ExitGateSummary,
    )

    onboarding = PilotOnboardingVerifier()
    exit_gate = Phase07ExitGateVerifier()

    tenant_id = TenantId.generate()

    # 1. Verify Pilot Onboarding Pre-Flight Checklist (6 Barriers)
    checklist = onboarding.verify_preflight_checklist(tenant_id)
    assert checklist.is_complete is True
    assert checklist.database_provisioned is True
    assert checklist.redis_cache_isolated is True
    assert checklist.s3_storage_isolated is True
    assert checklist.vector_namespace_isolated is True
    assert checklist.default_quotas_bound is True
    assert checklist.audit_partition_created is True

    # 2. Verify Composite Exit Gate Summary
    summary: ExitGateSummary = exit_gate.verify_all_acceptance_criteria()

    assert summary.verdict == "PASS"
    assert len(summary.evaluated_tasks) == 8
    assert summary.total_criteria_evaluated == 28
    assert summary.criteria_passed == 28
    assert summary.cross_tenant_leakage_rate == 0.00
    assert summary.measured_rto_minutes <= 30.0
    assert summary.measured_rpo_minutes <= 5.0
    assert len(summary.findings) == 0
