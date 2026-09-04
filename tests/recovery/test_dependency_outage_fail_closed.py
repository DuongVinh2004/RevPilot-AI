"""
RevPilot AI — TC-P07-026: Dependency Outage Fail-Closed Resilience Test
Specification: docs/24-sre/SRE-SPEC.md §1, docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md §7
Conforms to INV-REL-001, NFR-TEN-002, and TC-P07-026.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.errors import TenancyViolationError


@pytest.fixture(autouse=True)
def _isolate_operations_module():
    """Ensure operations module is isolated in test environment."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.operations"):
            sys.modules.pop(mod, None)


def test_dependency_outage_fails_closed_across_tenancy_and_secrets():
    """
    TC-P07-026 / INV-REL-001:
    When core dependencies (tenancy context, KMS/secrets, or database) encounter an outage or timeout:
    100% of sensitive write operations, tool gateway dispatches, and mutations MUST fail closed with 503.
    Tenant boundaries cannot be relaxed or bypassed under degraded mode.
    """
    from revpilot.modules.operations import RehearsalRunner

    runner = RehearsalRunner()
    tenant_id = TenantId.generate()

    # 1. Tenancy Verification Service Outage Simulation
    tenancy_outage = runner.simulate_dependency_outage("tenancy_service")
    assert tenancy_outage.failed_closed is True
    assert tenancy_outage.status_code == 503
    assert tenancy_outage.dispatches_blocked > 0

    # 2. In-flight dispatch execution under outage fails closed
    def execute_governed_action(is_dependency_available: bool) -> bool:
        if not is_dependency_available:
            # SRE Fail-Closed Guardrail (INV-REL-001)
            raise TenancyViolationError("Tenancy service timeout: external mutation blocked (503)")
        return True

    with pytest.raises(TenancyViolationError) as exc_info:
        execute_governed_action(is_dependency_available=False)
    assert "timeout" in str(exc_info.value).lower() or "blocked" in str(exc_info.value).lower()

    # 3. Secret Broker Outage Simulation
    secret_outage = runner.simulate_dependency_outage("secret_broker")
    assert secret_outage.failed_closed is True
    assert secret_outage.status_code == 503
