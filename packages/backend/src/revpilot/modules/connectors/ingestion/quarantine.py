"""
RevPilot AI — Schema Drift Quarantine & Reconciliation Service
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §5, DATABASE-SCHEMA.md §21.5
Conforms to INV-DATA-002, INV-REL-001, and TC-P07-021.
"""

from __future__ import annotations

import hashlib
import json
from pydantic import BaseModel, ConfigDict

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.connectors.domain import ConnectorStatus
from revpilot.modules.connectors.lifecycle import ConnectorLifecycleService
from revpilot.modules.connectors.ingestion.drift import DriftClassification, DriftEvaluationResult


class QuarantineRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    quarantine_id: UUIDv7
    tenant_id: TenantId
    connector_id: UUIDv7
    payload_hash: str
    raw_payload: dict
    classification: DriftClassification
    reasons: list[str]
    quarantined_at: UtcDateTime
    reprocessed_at: UtcDateTime | None = None
    mapping_version: str = "1.0.0"


class QuarantineService:
    """
    Isolates corrupt or schema-drifted payloads into the quarantine store with SHA-256 integrity hash.
    Transitions connector lifecycle safely to SCHEMA_DRIFT -> QUARANTINED, and orchestrates
    reconciliation replaying once mapping schemas are updated.
    """

    def __init__(self, lifecycle_service: ConnectorLifecycleService | None = None) -> None:
        self.lifecycle_service = lifecycle_service
        self._quarantine_records: dict[str, QuarantineRecord] = {}

    def divert_to_quarantine(
        self,
        tenant_id: TenantId,
        connector_id: UUIDv7,
        raw_payload: dict,
        evaluation: DriftEvaluationResult,
    ) -> UUIDv7:
        """
        Divert breaking schema drift payload to quarantine partition.
        Computes SHA-256 digest and transitions connector to QUARANTINED.
        """
        payload_bytes = json.dumps(raw_payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        qid = UUIDv7.generate()
        record = QuarantineRecord(
            quarantine_id=qid,
            tenant_id=tenant_id,
            connector_id=connector_id,
            payload_hash=payload_hash,
            raw_payload=raw_payload,
            classification=evaluation.classification,
            reasons=evaluation.reasons,
            quarantined_at=UtcDateTime.now(),
        )
        self._quarantine_records[qid.value] = record

        # Transition Connector Lifecycle
        if self.lifecycle_service:
            c = self.lifecycle_service.get_connector(connector_id)
            c.quarantine_count += 1
            # Step 1: SCHEMA_DRIFT
            self.lifecycle_service.transition_state(
                connector_id,
                ConnectorStatus.SCHEMA_DRIFT,
                reason=f"Breaking schema drift: {'; '.join(evaluation.reasons)}",
            )
            # Step 2: QUARANTINED
            self.lifecycle_service.transition_state(
                connector_id,
                ConnectorStatus.QUARANTINED,
                reason=f"Payload {payload_hash[:12]} stored in quarantine",
            )

        return qid

    def get_quarantine_records(self, connector_id: UUIDv7) -> list[QuarantineRecord]:
        """Fetch all quarantine records for a connector."""
        return [r for r in self._quarantine_records.values() if r.connector_id.value == connector_id.value]

    def reprocess_quarantine(
        self,
        quarantine_id: UUIDv7,
        new_mapping_version: str,
    ) -> None:
        """
        Mark quarantined payload as reprocessed with updated mapping schema.
        When all quarantined payloads are cleared, transitions connector to RECONCILIATION_REQUIRED -> ACTIVE.
        """
        record = self._quarantine_records.get(quarantine_id.value)
        if not record:
            raise ValueError(f"Quarantine record '{quarantine_id.value}' not found")

        record.reprocessed_at = UtcDateTime.now()
        record.mapping_version = new_mapping_version

        if self.lifecycle_service:
            # Check if all records for this connector are reprocessed
            conn_records = self.get_quarantine_records(record.connector_id)
            all_cleared = all(r.reprocessed_at is not None for r in conn_records)

            if all_cleared:
                self.lifecycle_service.transition_state(
                    record.connector_id,
                    ConnectorStatus.RECONCILIATION_REQUIRED,
                    reason=f"All quarantined events reprocessed with mapping {new_mapping_version}",
                )
                self.lifecycle_service.transition_state(
                    record.connector_id,
                    ConnectorStatus.ACTIVE,
                    reason="Reconciliation completed; sync restored to normal polling",
                )
