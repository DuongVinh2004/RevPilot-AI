"""
RevPilot AI — Uplift Score Repository Ports and In-Memory Adapter
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md §2
Conforms to INV-TEN-001..003 and AC-006.
"""

from __future__ import annotations
from typing import Optional, Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.modules.uplift.domain import UpliftScoreRecord


@runtime_checkable
class UpliftRepository(Protocol):
    """Storage port for tenant-isolated uplift score records."""

    def save(self, record: UpliftScoreRecord) -> None:
        """Persist or update an uplift score record."""
        ...

    def save_all(self, records: list[UpliftScoreRecord]) -> None:
        """Batch persist uplift score records."""
        ...

    def get(self, tenant_id: TenantId, score_id: UUIDv7) -> Optional[UpliftScoreRecord]:
        """Fetch uplift record enforcing tenant boundary."""
        ...

    def list_by_customer(
        self, tenant_id: TenantId, customer_id: str
    ) -> list[UpliftScoreRecord]:
        """Fetch all uplift records for a specific customer."""
        ...


class InMemoryUpliftRepository:
    """In-memory thread-safe adapter for testing and local scoring."""

    def __init__(self) -> None:
        # Key: (tenant_id_str, score_id_str)
        self._store: dict[tuple[str, str], UpliftScoreRecord] = {}

    def save(self, record: UpliftScoreRecord) -> None:
        key = (str(record.tenant_id), str(record.score_id))
        self._store[key] = record

    def save_all(self, records: list[UpliftScoreRecord]) -> None:
        for r in records:
            self.save(r)

    def get(self, tenant_id: TenantId, score_id: UUIDv7) -> Optional[UpliftScoreRecord]:
        key = (str(tenant_id), str(score_id))
        return self._store.get(key)

    def list_by_customer(
        self, tenant_id: TenantId, customer_id: str
    ) -> list[UpliftScoreRecord]:
        t_str = str(tenant_id)
        results = [
            r
            for (tid, _), r in self._store.items()
            if tid == t_str and r.customer_id == customer_id
        ]
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results

    def clear(self) -> None:
        self._store.clear()
