"""
RevPilot AI — Ingestion Lineage Metadata Recorder (Phase 01)
Adheres to docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md §4, INV-DATA-002, and INV-AUD-001.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


@dataclass(frozen=True, slots=True)
class LineageRecord:
    """
    Immutable lineage tracking record linking canonical aggregates to raw source payloads.
    Satisfies INV-DATA-002 and INV-AUD-001.
    """
    lineage_id: str
    tenant_id: TenantId
    source_system: str
    source_batch_id: str
    raw_payload_hash: str
    transformation_name: str
    record_counts: Dict[str, int]
    executed_at: UtcDateTime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "tenant_id": self.tenant_id.value,
            "source_system": self.source_system,
            "source_batch_id": self.source_batch_id,
            "raw_payload_hash": self.raw_payload_hash,
            "transformation_name": self.transformation_name,
            "record_counts": dict(self.record_counts),
            "executed_at": self.executed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineageRecord:
        return cls(
            lineage_id=data["lineage_id"],
            tenant_id=TenantId(data["tenant_id"]),
            source_system=data["source_system"],
            source_batch_id=data["source_batch_id"],
            raw_payload_hash=data["raw_payload_hash"],
            transformation_name=data["transformation_name"],
            record_counts=dict(data["record_counts"]),
            executed_at=UtcDateTime.from_iso(data["executed_at"]),
        )


class LineageRecorder:
    """
    In-memory immutable lineage store enforcing multi-tenant isolation.
    """

    def __init__(self) -> None:
        self._records: Dict[tuple[str, str], LineageRecord] = {}

    def record(self, lineage: LineageRecord) -> None:
        """Store immutable lineage event."""
        key = (lineage.tenant_id.value, lineage.lineage_id)
        self._records[key] = lineage

    def get_lineage(self, tenant_id: TenantId, lineage_id: str) -> Optional[LineageRecord]:
        """Fetch lineage record within tenant boundary."""
        return self._records.get((tenant_id.value, lineage_id))

    def list_lineage(self, tenant_id: TenantId) -> List[LineageRecord]:
        """List lineage records strictly isolated to tenant."""
        return [
            rec for (t_val, _), rec in self._records.items()
            if t_val == tenant_id.value
        ]


__all__ = [
    "LineageRecord",
    "LineageRecorder",
]
