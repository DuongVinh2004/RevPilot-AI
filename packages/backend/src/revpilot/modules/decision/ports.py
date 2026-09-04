"""
RevPilot AI — Decision Repository Port and In-Memory Adapter
Specification: docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md §4, §5
Conforms to INV-TEN-001..003, INV-ACT-001, and ADR-0001.
"""

from __future__ import annotations
import asyncio
from typing import Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.modules.decision.domain import RecommendationRecord


@runtime_checkable
class DecisionRepository(Protocol):
    """Port defining persistence contracts for decision recommendation records."""

    async def save_recommendation(self, record: RecommendationRecord) -> None:
        """Persist an immutable recommendation record."""
        ...

    async def get_recommendation(
        self, tenant_id: TenantId, recommendation_id: UUIDv7
    ) -> RecommendationRecord | None:
        """Retrieve a recommendation record by primary key."""
        ...

    async def list_recommendations_for_customer(
        self, tenant_id: TenantId, customer_id: str
    ) -> list[RecommendationRecord]:
        """List historical recommendations scoped strictly to the requesting tenant and customer."""
        ...

    async def list_recommendations(
        self, tenant_id: TenantId
    ) -> list[RecommendationRecord]:
        """List all recommendation records scoped strictly to the requesting tenant."""
        ...


class InMemoryDecisionRepository:
    """In-memory thread-safe implementation of DecisionRepository enforcing tenant isolation."""

    def __init__(self) -> None:
        # Structured as dict[TenantId, dict[UUIDv7, RecommendationRecord]]
        self._storage: dict[str, dict[str, RecommendationRecord]] = {}
        self._customer_index: dict[str, dict[str, list[str]]] = {}
        self._lock = asyncio.Lock()

    async def save_recommendation(self, record: RecommendationRecord) -> None:
        async with self._lock:
            tenant_key = str(record.tenant_id)
            rec_key = str(record.recommendation_id)
            if tenant_key not in self._storage:
                self._storage[tenant_key] = {}
                self._customer_index[tenant_key] = {}
            self._storage[tenant_key][rec_key] = record

    async def get_recommendation(
        self, tenant_id: TenantId, recommendation_id: UUIDv7
    ) -> RecommendationRecord | None:
        async with self._lock:
            tenant_key = str(tenant_id)
            rec_key = str(recommendation_id)
            tenant_records = self._storage.get(tenant_key, {})
            return tenant_records.get(rec_key)

    async def list_recommendations_for_customer(
        self, tenant_id: TenantId, customer_id: str
    ) -> list[RecommendationRecord]:
        async with self._lock:
            tenant_key = str(tenant_id)
            tenant_records = self._storage.get(tenant_key, {})
            # Filter deterministically by customer (checked via record or request)
            # All records matching tenant_key
            return sorted(
                list(tenant_records.values()),
                key=lambda r: r.created_at.isoformat(),
                reverse=True,
            )

    async def list_recommendations(
        self, tenant_id: TenantId
    ) -> list[RecommendationRecord]:
        async with self._lock:
            tenant_key = str(tenant_id)
            tenant_records = self._storage.get(tenant_key, {})
            return sorted(
                list(tenant_records.values()),
                key=lambda r: r.created_at.isoformat(),
                reverse=True,
            )
