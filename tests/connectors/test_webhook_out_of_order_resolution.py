"""
RevPilot AI — TC-P07-020: Webhook Out-of-Order Resolution Test
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §4.1
Conforms to INV-DATA-002 and INV-REL-002.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
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


def test_webhook_out_of_order_resolution_preserves_newer_canonical_state():
    """
    TC-P07-020: Out-of-order webhook delivery resolution.
    Older timestamped events arriving later MUST NOT overwrite newer canonical state.
    Monotonic timestamp ordering is preserved.
    """
    from revpilot.modules.connectors.ingestion import (
        TransactionalInboxService,
        InboxStatus,
    )

    inbox = TransactionalInboxService()
    tenant_id = TenantId.generate()
    connector_id = UUIDv7.generate()

    entity_id = "inv_enterprise_order_4455"
    base_time = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)

    t1_old = UtcDateTime(base_time)
    t2_newer = UtcDateTime(base_time + timedelta(minutes=5))
    t3_latest = UtcDateTime(base_time + timedelta(minutes=10))

    # 1. First Arriving Event: T2 (Newer state arrives first due to network race)
    receipt_t2 = inbox.record_incoming_event(
        tenant_id=tenant_id,
        connector_id=connector_id,
        external_event_id="evt_t2_charge_paid",
        raw_payload={"id": entity_id, "status": "PAID", "amount": 1000},
        event_timestamp=t2_newer,
    )
    assert receipt_t2.status == InboxStatus.PROCESSED
    canonical_state = inbox.get_canonical_state(tenant_id, entity_id)
    assert canonical_state is not None
    assert canonical_state["status"] == "PAID"

    # 2. Delayed Arriving Event: T1 (Older state arrives second)
    receipt_t1 = inbox.record_incoming_event(
        tenant_id=tenant_id,
        connector_id=connector_id,
        external_event_id="evt_t1_invoice_pending",
        raw_payload={"id": entity_id, "status": "PENDING", "amount": 1000},
        event_timestamp=t1_old,
    )
    # Must be marked IGNORED_OUT_OF_ORDER and MUST NOT overwrite
    assert receipt_t1.status == InboxStatus.IGNORED_OUT_OF_ORDER
    assert "superseded" in (receipt_t1.status_reason or "").lower()

    # Verify canonical state was NOT overwritten and remains PAID
    canonical_state_after_stale = inbox.get_canonical_state(tenant_id, entity_id)
    assert canonical_state_after_stale is not None
    assert canonical_state_after_stale["status"] == "PAID"

    # 3. New Update: T3 (Even newer state arrives)
    receipt_t3 = inbox.record_incoming_event(
        tenant_id=tenant_id,
        connector_id=connector_id,
        external_event_id="evt_t3_invoice_refunded",
        raw_payload={"id": entity_id, "status": "REFUNDED", "amount": 1000},
        event_timestamp=t3_latest,
    )
    assert receipt_t3.status == InboxStatus.PROCESSED

    # Verify canonical state is successfully updated to REFUNDED
    canonical_state_latest = inbox.get_canonical_state(tenant_id, entity_id)
    assert canonical_state_latest is not None
    assert canonical_state_latest["status"] == "REFUNDED"
