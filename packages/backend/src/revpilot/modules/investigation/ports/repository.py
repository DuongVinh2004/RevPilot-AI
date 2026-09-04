"""
RevPilot AI — Investigation Persistence Port Contract
Conforms to docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md §5 and TASK-P03-001.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from revpilot.shared.identifiers import TenantId
from revpilot.modules.investigation.domain.models import Investigation, BudgetState


class InvestigationRepository(ABC):
    """
    Persistence port interface for Investigation aggregate root.
    Enforces multi-tenant isolation on all state retrieval and mutations (INV-TEN-001).
    """

    @abstractmethod
    async def get_by_id(
        self,
        tenant_id: TenantId,
        investigation_id: str,
    ) -> Optional[Investigation]:
        """Fetch investigation aggregate by ID scoped strictly to tenant_id."""
        ...

    @abstractmethod
    async def save(
        self,
        investigation: Investigation,
    ) -> None:
        """Persist or upsert investigation aggregate."""
        ...

    @abstractmethod
    async def update_budget(
        self,
        tenant_id: TenantId,
        investigation_id: str,
        budget: BudgetState,
    ) -> None:
        """Atomically persist updated budget resource counters."""
        ...


__all__ = ["InvestigationRepository"]
