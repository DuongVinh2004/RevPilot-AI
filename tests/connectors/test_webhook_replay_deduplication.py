"""
RevPilot AI — TC-P07-019: Transactional Inbox Replay Deduplication Test
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §4.1
Conforms to AC-P07-006-02, INV-DATA-002, and INV-TEN-001.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_connectors_module():
    """Ensure connectors module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.connectors"):
            sys.modules.pop(mod, None)


def test_transactional_inbox_deduplication_and_isolation():
    """
    TC-P07-019 / AC-P07-006-02:
    - Duplicate external_event_ids return 200/202 DUPLICATE without reprocessing.
    - Idempotency is partitioned by tenant_id and connector_id.
    """
    from revpilot.modules.connectors.ingestion import (
        TransactionalInboxService,
        InboxStatus,
    )

    inbox = TransactionalInboxService()
    tenant_a = TenantId.generate()
    tenant_b = TenantId.generate()
    connector_id = UUIDv7.generate()

    event_id_shared = "evt_stripe_charge_succeeded_998811"
    payload = {"entity_id": "inv_001", "amount": 2500, "status": "paid"}

    # 1. First Ingestion: PROCESSED
    receipt1 = inbox.record_incoming_event(
        tenant_id=tenant_a,
        connector_id=connector_id,
        external_event_id=event_id_shared,
        raw_payload=payload,
    )
    assert receipt1.status == InboxStatus.PROCESSED
    assert receipt1.is_duplicate is False
    assert receipt1.external_event_id == event_id_shared

    # 2. Duplicate Ingestion: DUPLICATE (Idempotent Acknowledgment)
    receipt2 = inbox.record_incoming_event(
        tenant_id=tenant_a,
        connector_id=connector_id,
        external_event_id=event_id_shared,
        raw_payload=payload,
    )
    assert receipt2.status == InboxStatus.DUPLICATE
    assert receipt2.is_duplicate is True
    # Reuses same underlying canonical event_id
    assert receipt2.event_id == receipt1.event_id

    # 3. Same Event ID for Different Tenant: PROCESSED (Tenant Isolation)
    receipt_tenant_b = inbox.record_incoming_event(
        tenant_id=tenant_b,
        connector_id=connector_id,
        external_event_id=event_id_shared,
        raw_payload=payload,
    )
    assert receipt_tenant_b.status == InboxStatus.PROCESSED
    assert receipt_tenant_b.is_duplicate is False
    assert receipt_tenant_b.event_id != receipt1.event_id
