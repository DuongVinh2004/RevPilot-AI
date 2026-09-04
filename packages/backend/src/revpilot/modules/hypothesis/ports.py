"""
RevPilot AI — Hypothesis Repository Ports and In-Memory Adapter
Specification: docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md §5
Conforms to INV-TEN-001..003 and AC-004.
"""

from __future__ import annotations
from typing import Optional, Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.modules.hypothesis.domain import HypothesisRecord, HypothesisError


@runtime_checkable
class HypothesisRepository(Protocol):
    """Authoritative storage port for tenant-isolated hypothesis aggregates."""

    def save(self, hypothesis: HypothesisRecord) -> None:
        """Persist or update a hypothesis record."""
        ...

    def get(self, tenant_id: TenantId, hypothesis_id: str) -> Optional[HypothesisRecord]:
        """Fetch hypothesis by ID ensuring single-tenant boundary."""
        ...

    def list_by_investigation(
        self, tenant_id: TenantId, investigation_id: UUIDv7
    ) -> list[HypothesisRecord]:
        """Fetch all hypotheses for an investigation sorted by ordinal_rank."""
        ...


class InMemoryHypothesisRepository:
    """In-memory thread-safe adapter for testing and fast local evaluation."""

    def __init__(self) -> None:
        # Key: (tenant_id_str, hypothesis_id)
        self._store: dict[tuple[str, str], HypothesisRecord] = {}

    def save(self, hypothesis: HypothesisRecord) -> None:
        """Persist single hypothesis with tenant key."""
        key = (str(hypothesis.tenant_id), hypothesis.hypothesis_id)
        self._store[key] = hypothesis

    def save_all(self, hypotheses: list[HypothesisRecord]) -> None:
        """Persist multiple hypotheses."""
        for h in hypotheses:
            self.save(h)

    def get(self, tenant_id: TenantId, hypothesis_id: str) -> Optional[HypothesisRecord]:
        """Fetch hypothesis ensuring strict tenant isolation."""
        key = (str(tenant_id), hypothesis_id)
        return self._store.get(key)

    def list_by_investigation(
        self, tenant_id: TenantId, investigation_id: UUIDv7
    ) -> list[HypothesisRecord]:
        """List hypotheses for given tenant and investigation, ordered by rank."""
        t_str = str(tenant_id)
        inv_str = str(investigation_id)
        results = [
            h
            for (tid, _), h in self._store.items()
            if tid == t_str and str(h.investigation_id) == inv_str
        ]
        results.sort(key=lambda h: h.ordinal_rank)
        return results

    def clear(self) -> None:
        """Clear store for test teardown."""
        self._store.clear()
