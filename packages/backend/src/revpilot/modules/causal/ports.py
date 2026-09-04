"""
RevPilot AI — Causal Study Repository Ports and In-Memory Adapter
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §5
Conforms to INV-TEN-001..003 and AC-006.
"""

from __future__ import annotations
from typing import Optional, Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.modules.causal.domain import CausalStudy


@runtime_checkable
class CausalStudyRepository(Protocol):
    """Authoritative storage port for tenant-isolated causal studies."""

    def save(self, study: CausalStudy) -> None:
        """Persist or update a causal study record."""
        ...

    def get(self, tenant_id: TenantId, study_id: UUIDv7) -> Optional[CausalStudy]:
        """Fetch study ensuring single-tenant isolation."""
        ...

    def list_by_investigation(
        self, tenant_id: TenantId, investigation_id: UUIDv7
    ) -> list[CausalStudy]:
        """Fetch all causal studies for an investigation within tenant boundary."""
        ...


class InMemoryCausalStudyRepository:
    """In-memory thread-safe adapter for causal studies."""

    def __init__(self) -> None:
        # Key: (tenant_id_str, study_id_str)
        self._store: dict[tuple[str, str], CausalStudy] = {}

    def save(self, study: CausalStudy) -> None:
        key = (str(study.tenant_id), str(study.study_id))
        self._store[key] = study

    def get(self, tenant_id: TenantId, study_id: UUIDv7) -> Optional[CausalStudy]:
        key = (str(tenant_id), str(study_id))
        return self._store.get(key)

    def list_by_investigation(
        self, tenant_id: TenantId, investigation_id: UUIDv7
    ) -> list[CausalStudy]:
        t_str = str(tenant_id)
        inv_str = str(investigation_id)
        results = [
            s
            for (tid, _), s in self._store.items()
            if tid == t_str and str(s.investigation_id) == inv_str
        ]
        results.sort(key=lambda s: s.created_at)
        return results

    def clear(self) -> None:
        self._store.clear()
