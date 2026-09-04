"""
RevPilot AI — Transactional Webhook Inbox & Out-of-Order Deduplication
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §4.1, DATABASE-SCHEMA.md §21.4
Conforms to INV-DATA-002, INV-REL-002, TC-P07-019, and TC-P07-020.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, ConfigDict

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


class InboxStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    DUPLICATE = "DUPLICATE"
    QUARANTINED = "QUARANTINED"
    IGNORED_OUT_OF_ORDER = "IGNORED_OUT_OF_ORDER"


class InboxReceipt(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: UUIDv7
    external_event_id: str
    tenant_id: TenantId
    connector_id: UUIDv7
    status: InboxStatus
    is_duplicate: bool
    received_at: UtcDateTime
    processed_at: UtcDateTime | None = None
    status_reason: str | None = None


class TransactionalInboxService:
    """
    Guarantees exactly-once ingestion idempotency per (tenant_id, connector_id, external_event_id),
    prevents duplicate mutation storms, and preserves canonical monotonic ordering against out-of-order deliveries.
    """

    def __init__(self) -> None:
        self._inbox_registry: dict[str, InboxReceipt] = {}
        self._canonical_entity_state: dict[str, tuple[UtcDateTime, dict]] = {}

    def record_incoming_event(
        self,
        tenant_id: TenantId,
        connector_id: UUIDv7,
        external_event_id: str,
        raw_payload: dict,
        event_timestamp: UtcDateTime | None = None,
        entity_id: str | None = None,
    ) -> InboxReceipt:
        """
        Record inbound event atomically:
        - Duplicate external_event_id returns 200/202 DUPLICATE without reprocessing (TC-P07-019).
        - Older timestamped events do not overwrite newer canonical state (TC-P07-020).
        """
        dedup_key = f"{tenant_id.value}:{connector_id.value}:{external_event_id}"
        now = UtcDateTime.now()

        # 1. Transactional Deduplication Check (TC-P07-019)
        if dedup_key in self._inbox_registry:
            existing = self._inbox_registry[dedup_key]
            return InboxReceipt(
                event_id=existing.event_id,
                external_event_id=external_event_id,
                tenant_id=tenant_id,
                connector_id=connector_id,
                status=InboxStatus.DUPLICATE,
                is_duplicate=True,
                received_at=existing.received_at,
                processed_at=now,
                status_reason="Duplicate external_event_id ignored; acknowledged without reprocessing",
            )

        event_id = UUIDv7.generate()
        ev_time = event_timestamp or now

        # 2. Out-of-Order Sequence Check (TC-P07-020)
        target_entity = entity_id or raw_payload.get("id") or raw_payload.get("entity_id")
        if target_entity:
            entity_key = f"{tenant_id.value}:{target_entity}"
            if entity_key in self._canonical_entity_state:
                last_ts, _ = self._canonical_entity_state[entity_key]
                if ev_time.value.timestamp() < last_ts.value.timestamp():
                    # Stale / Out-of-order event: do not overwrite newer state
                    receipt = InboxReceipt(
                        event_id=event_id,
                        external_event_id=external_event_id,
                        tenant_id=tenant_id,
                        connector_id=connector_id,
                        status=InboxStatus.IGNORED_OUT_OF_ORDER,
                        is_duplicate=False,
                        received_at=now,
                        processed_at=now,
                        status_reason=f"Event timestamp {ev_time.isoformat()} superseded by newer canonical state ({last_ts.isoformat()})",
                    )
                    self._inbox_registry[dedup_key] = receipt
                    return receipt

            # Update canonical state monotonically
            self._canonical_entity_state[entity_key] = (ev_time, raw_payload)

        # 3. Fresh Event Ingested Successfully
        receipt = InboxReceipt(
            event_id=event_id,
            external_event_id=external_event_id,
            tenant_id=tenant_id,
            connector_id=connector_id,
            status=InboxStatus.PROCESSED,
            is_duplicate=False,
            received_at=now,
            processed_at=now,
            status_reason="Event processed into canonical store",
        )
        self._inbox_registry[dedup_key] = receipt
        return receipt

    def get_canonical_state(self, tenant_id: TenantId, entity_id: str) -> dict | None:
        """Retrieve authoritative canonical state for an entity."""
        entity_key = f"{tenant_id.value}:{entity_id}"
        entry = self._canonical_entity_state.get(entity_key)
        return entry[1] if entry else None
