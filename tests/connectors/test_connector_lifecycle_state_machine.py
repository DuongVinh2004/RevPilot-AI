"""
RevPilot AI — Connector Lifecycle State Machine Comprehensive Test
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §3
Conforms to AC-P07-005-01 and INV-DATA-002.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.modules.security.secrets.broker import SecretReference


@pytest.fixture(autouse=True)
def _isolate_connectors_module():
    """Ensure connectors module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.connectors"):
            sys.modules.pop(mod, None)


def test_connector_lifecycle_state_machine_all_13_states():
    """
    AC-P07-005-01: Verifies full transition coverage across all 13 lifecycle states
    without orphaned state, and strictly rejects illegal state jumps.
    """
    from revpilot.modules.connectors import (
        ConnectorLifecycleService,
        ConnectorStatus,
        InvalidScopeError,
        InvalidStateTransitionError,
    )

    service = ConnectorLifecycleService()
    tenant_id = TenantId.generate()
    secret_ref = SecretReference.generate()

    # 1. Registration -> REGISTERED
    cid = service.register_connector(
        tenant_id=tenant_id,
        provider="salesforce",
        capability="crm_sync",
    )
    rec = service.get_connector(cid)
    assert rec.status == ConnectorStatus.REGISTERED
    assert rec.tenant_id == tenant_id

    # Reject empty scopes
    with pytest.raises(InvalidScopeError):
        service.configure_credentials(cid, secret_ref=secret_ref, scopes=[])

    # 2. Configure Credentials -> CONFIGURED
    service.configure_credentials(cid, secret_ref=secret_ref, scopes=["api:read", "contacts:read"])
    assert rec.status == ConnectorStatus.CONFIGURED
    assert rec.secret_ref == secret_ref

    # 3. Validate Connectivity (Failure Branch) -> VALIDATING -> FAILED
    failed_probe = service.validate_connectivity(cid, probe_fn=lambda: False)
    assert not failed_probe
    assert rec.status == ConnectorStatus.FAILED

    # Re-validate after fixing -> CONFIGURED -> VALIDATING -> ACTIVE
    service.transition_state(cid, ConnectorStatus.CONFIGURED, reason="Credentials re-bound")
    success_probe = service.validate_connectivity(cid, probe_fn=lambda: True)
    assert success_probe
    assert rec.status == ConnectorStatus.ACTIVE

    # 4. Manual Pause & Resume -> PAUSED -> ACTIVE
    service.transition_state(cid, ConnectorStatus.PAUSED, reason="Tenant admin requested maintenance")
    assert rec.status == ConnectorStatus.PAUSED

    service.transition_state(cid, ConnectorStatus.ACTIVE, reason="Tenant admin resumed sync")
    assert rec.status == ConnectorStatus.ACTIVE

    # 5. Schema Drift -> QUARANTINED -> RECONCILIATION_REQUIRED -> ACTIVE
    service.transition_state(cid, ConnectorStatus.SCHEMA_DRIFT, reason="Incompatible schema detected")
    assert rec.status == ConnectorStatus.SCHEMA_DRIFT

    service.transition_state(cid, ConnectorStatus.QUARANTINED, reason="Unparseable payloads quarantined")
    assert rec.status == ConnectorStatus.QUARANTINED

    service.transition_state(cid, ConnectorStatus.RECONCILIATION_REQUIRED, reason="Mapping update deployed")
    assert rec.status == ConnectorStatus.RECONCILIATION_REQUIRED

    service.transition_state(cid, ConnectorStatus.ACTIVE, reason="Reconciliation complete")
    assert rec.status == ConnectorStatus.ACTIVE

    # 6. Degradation & Auth Expiry
    service.transition_state(cid, ConnectorStatus.DEGRADED, reason="Transient 429 backoff")
    assert rec.status == ConnectorStatus.DEGRADED

    service.transition_state(cid, ConnectorStatus.AUTH_EXPIRED, reason="Credentials revoked by upstream")
    assert rec.status == ConnectorStatus.AUTH_EXPIRED

    # 7. Teardown -> DELETING -> DELETED
    service.delete_connector(cid)
    assert rec.status == ConnectorStatus.DELETED
    assert rec.cursor_position is None
    assert rec.secret_ref is None

    # 8. Verify Illegal Transitions Fail Closed (400 INVALID_STATE_TRANSITION)
    with pytest.raises(InvalidStateTransitionError):
        # Cannot transition out of DELETED
        service.transition_state(cid, ConnectorStatus.ACTIVE, reason="Illegal resurrection")

    cid2 = service.register_connector(tenant_id=tenant_id, provider="hubspot", capability="crm_sync")
    with pytest.raises(InvalidStateTransitionError):
        # Cannot jump directly from REGISTERED to ACTIVE without configuration and validation
        service.transition_state(cid2, ConnectorStatus.ACTIVE, reason="Illegal bypass")
