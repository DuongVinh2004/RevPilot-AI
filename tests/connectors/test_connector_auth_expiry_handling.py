"""
RevPilot AI — TC-P07-017: Connector Auth Expiry Handling Test
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §3.1
Conforms to AC-P07-005-02 and INV-SEC-001.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.modules.security.secrets.broker import SecretReference


@pytest.fixture(autouse=True)
def _isolate_connectors_module():
    """Ensure connectors module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.connectors"):
            sys.modules.pop(mod, None)


def test_connector_auth_expiry_transitions_and_halts_sync():
    """
    TC-P07-017 / AC-P07-005-02:
    When an upstream provider returns 401 Unauthorized or 403 Forbidden,
    the connector MUST immediately transition to AUTH_EXPIRED and halt sync workers.
    Subsequent sync attempts are blocked until credentials are reconfigured and validated.
    """
    from revpilot.modules.connectors import (
        ConnectorLifecycleService,
        ConnectorStatus,
    )

    service = ConnectorLifecycleService()
    tenant_id = TenantId.generate()
    secret_ref_v1 = SecretReference.generate()
    secret_ref_v2 = SecretReference.generate()

    # 1. Setup Active Connector
    cid = service.register_connector(
        tenant_id=tenant_id,
        provider="stripe",
        capability="billing_sync",
    )
    service.configure_credentials(cid, secret_ref=secret_ref_v1, scopes=["charges:read"])
    service.validate_connectivity(cid, probe_fn=lambda: True)

    rec = service.get_connector(cid)
    assert rec.status == ConnectorStatus.ACTIVE

    # Simulate Normal Sync Iterations
    service.record_sync_success(cid, cursor="cursor_chk_001", lag_seconds=12)
    assert rec.cursor_position == "cursor_chk_001"
    assert rec.sync_lag_seconds == 12

    # 2. Simulate Provider 401 Unauthorized during Sync
    provider_response_status = 401

    if provider_response_status in (401, 403):
        service.record_auth_failure(cid)

    # 3. Verify Immediate State Transition to AUTH_EXPIRED (AC-P07-005-02)
    assert rec.status == ConnectorStatus.AUTH_EXPIRED
    assert "401/403" in (rec.status_reason or "")
    assert rec.consecutive_errors >= 1

    # 4. Ingestion Worker Execution Guardrail: Sync MUST Halt
    def run_sync_worker_iteration(connector_id) -> bool:
        c = service.get_connector(connector_id)
        if c.status != ConnectorStatus.ACTIVE:
            # Sync is immediately halted for non-ACTIVE states
            return False
        # Sync logic executes
        return True

    worker_result = run_sync_worker_iteration(cid)
    assert worker_result is False, "Worker should halt when connector is in AUTH_EXPIRED state"

    # 5. Recovery via Credential Rotation & Validation
    service.configure_credentials(cid, secret_ref=secret_ref_v2, scopes=["charges:read"])
    assert rec.status == ConnectorStatus.CONFIGURED

    # Re-validate connectivity with new credentials
    revalidated = service.validate_connectivity(cid, probe_fn=lambda: True)
    assert revalidated is True
    assert rec.status == ConnectorStatus.ACTIVE

    # Sync operations resume cleanly
    worker_resumed_result = run_sync_worker_iteration(cid)
    assert worker_resumed_result is True
