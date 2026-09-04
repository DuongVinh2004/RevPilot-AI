"""
RevPilot AI — Quarantine Repository and Replay Contracts (Phase 01)
Adheres to docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md §5 and INV-TEN-001.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import ValidationError
from revpilot.shared.results import Result, Success, Failure
from revpilot.modules.data_quality.validator import DataQualityValidator


@dataclass
class QuarantineRecord:
    """
    Persisted record representing a quarantined raw or normalized payload.
    Preserves verbatim input with failure diagnostics for operator inspection and replay.
    """
    quarantine_id: str
    tenant_id: TenantId
    rule_id: str
    raw_payload: Dict[str, Any]
    rejection_reason: str
    status: str = "QUARANTINED"  # QUARANTINED, REPROCESSED, DISCARDED
    quarantined_at: UtcDateTime = None  # type: ignore[assignment]
    resolved_at: Optional[UtcDateTime] = None
    resolved_by: Optional[str] = None

    def __post_init__(self) -> None:
        if self.quarantined_at is None:
            object.__setattr__(self, "quarantined_at", UtcDateTime.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quarantine_id": self.quarantine_id,
            "tenant_id": self.tenant_id.value,
            "rule_id": self.rule_id,
            "raw_payload": self.raw_payload,
            "rejection_reason": self.rejection_reason,
            "status": self.status,
            "quarantined_at": self.quarantined_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuarantineRecord:
        return cls(
            quarantine_id=data["quarantine_id"],
            tenant_id=TenantId(data["tenant_id"]),
            rule_id=data["rule_id"],
            raw_payload=dict(data["raw_payload"]),
            rejection_reason=data["rejection_reason"],
            status=data.get("status", "QUARANTINED"),
            quarantined_at=UtcDateTime.from_iso(data["quarantined_at"]),
            resolved_at=UtcDateTime.from_iso(data["resolved_at"]) if data.get("resolved_at") else None,
            resolved_by=data.get("resolved_by"),
        )


class QuarantineRepository:
    """
    In-memory isolated quarantine repository enforcing INV-TEN-001.
    Prevents cross-tenant quarantine record visibility and supports deterministic replay.
    """

    def __init__(self) -> None:
        # Keyed by (tenant_id_value, quarantine_id)
        self._store: Dict[tuple[str, str], QuarantineRecord] = {}

    def quarantine(self, record: QuarantineRecord) -> None:
        """Store a quarantined record under its composite tenant key."""
        key = (record.tenant_id.value, record.quarantine_id)
        self._store[key] = record

    def get(self, tenant_id: TenantId, quarantine_id: str) -> Optional[QuarantineRecord]:
        """Fetch a specific quarantined record within tenant boundary."""
        return self._store.get((tenant_id.value, quarantine_id))

    def list_quarantined(self, tenant_id: TenantId) -> List[QuarantineRecord]:
        """List all quarantined records strictly isolated to caller's tenant."""
        return [
            rec for (t_val, _), rec in self._store.items()
            if t_val == tenant_id.value
        ]

    def replay(
        self,
        quarantine_id: str,
        validator: DataQualityValidator,
        corrected_payload: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[TenantId] = None,
    ) -> Result[Dict[str, Any], ValidationError]:
        """
        Replay a quarantined record through the validator.
        On success, transitions record status to 'REPROCESSED'.
        On failure, updates rejection_reason and keeps 'QUARANTINED'.
        """
        # Find record
        target_record: Optional[QuarantineRecord] = None
        for (t_val, q_id), rec in self._store.items():
            if q_id == quarantine_id:
                if tenant_id is not None and t_val != tenant_id.value:
                    continue
                target_record = rec
                break

        if target_record is None:
            return Failure(
                ValidationError(f"Quarantine record with id '{quarantine_id}' not found")
            )

        payload_to_test = corrected_payload if corrected_payload is not None else target_record.raw_payload

        # Re-validate with validator against target record's tenant
        val_result = validator.validate_record(
            record=payload_to_test,
            session_tenant_id=target_record.tenant_id,
        )

        if val_result.is_valid:
            target_record.status = "REPROCESSED"
            target_record.raw_payload = payload_to_test
            target_record.resolved_at = UtcDateTime.now()
            target_record.resolved_by = "operator_replay"
            return Success(payload_to_test)
        else:
            target_record.status = "QUARANTINED"
            target_record.rejection_reason = val_result.rejection_reason or "Replay validation failed"
            return Failure(
                ValidationError(
                    message=val_result.rejection_reason or "Replay validation failed",
                    details={"rule_id": val_result.rule_id, "error_code": val_result.error_code},
                )
            )


__all__ = [
    "QuarantineRecord",
    "QuarantineRepository",
]
