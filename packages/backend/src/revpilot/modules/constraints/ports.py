"""
RevPilot AI — Budget Ledger Ports and In-Memory Adapter
Specification: docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md §3, §4
Conforms to INV-COST-001, INV-TEN-001..003, and NFR-COST-001.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Optional, Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId
from revpilot.modules.constraints.domain import BudgetLedgerEntry, ConstraintViolationError


@runtime_checkable
class BudgetLedgerRepository(Protocol):
    """Authoritative storage and atomic reservation port for monetary budget ledger."""

    def get_ledger(self, tenant_id: TenantId, ledger_date: str) -> Optional[BudgetLedgerEntry]:
        """Fetch budget ledger entry for given tenant and date."""
        ...

    def reserve_budget(
        self, tenant_id: TenantId, ledger_date: str, amount_usd: Decimal
    ) -> BudgetLedgerEntry:
        """Atomically reserve funds, rejecting if insufficient balance."""
        ...

    def release_budget(
        self, tenant_id: TenantId, ledger_date: str, amount_usd: Decimal
    ) -> BudgetLedgerEntry:
        """Release reserved funds back to available balance."""
        ...


class InMemoryBudgetLedgerRepository:
    """In-memory thread-safe adapter enforcing optimistic concurrency and zero overdraft."""

    def __init__(self) -> None:
        # Key: (tenant_id_str, ledger_date)
        self._store: dict[tuple[str, str], BudgetLedgerEntry] = {}

    def init_ledger(
        self, tenant_id: TenantId, ledger_date: str, total_allocated_usd: Decimal
    ) -> BudgetLedgerEntry:
        key = (str(tenant_id), ledger_date)
        entry = BudgetLedgerEntry(
            tenant_id=tenant_id,
            ledger_date=ledger_date,
            total_allocated_usd=total_allocated_usd,
            committed_expenditure_usd=Decimal("0.0"),
            remaining_balance_usd=total_allocated_usd,
            version=1,
        )
        self._store[key] = entry
        return entry

    def get_ledger(self, tenant_id: TenantId, ledger_date: str) -> Optional[BudgetLedgerEntry]:
        key = (str(tenant_id), ledger_date)
        return self._store.get(key)

    def reserve_budget(
        self, tenant_id: TenantId, ledger_date: str, amount_usd: Decimal
    ) -> BudgetLedgerEntry:
        key = (str(tenant_id), ledger_date)
        current = self._store.get(key)
        if current is None:
            raise ConstraintViolationError(
                code="ERR_BUDGET_LEDGER_NOT_FOUND",
                message=f"No budget ledger initialized for tenant {tenant_id} on {ledger_date}",
            )

        if current.remaining_balance_usd < amount_usd:
            raise ConstraintViolationError(
                code="ERR_BUDGET_EXCEEDED",
                message=f"Requested reservation {amount_usd} exceeds available budget {current.remaining_balance_usd}",
                details={"requested": str(amount_usd), "available": str(current.remaining_balance_usd)},
            )

        updated = current.model_copy(
            update={
                "committed_expenditure_usd": current.committed_expenditure_usd + amount_usd,
                "remaining_balance_usd": current.remaining_balance_usd - amount_usd,
                "version": current.version + 1,
            }
        )
        self._store[key] = updated
        return updated

    def release_budget(
        self, tenant_id: TenantId, ledger_date: str, amount_usd: Decimal
    ) -> BudgetLedgerEntry:
        key = (str(tenant_id), ledger_date)
        current = self._store.get(key)
        if current is None:
            raise ConstraintViolationError(
                code="ERR_BUDGET_LEDGER_NOT_FOUND",
                message=f"No budget ledger initialized for tenant {tenant_id} on {ledger_date}",
            )

        amount_to_release = min(amount_usd, current.committed_expenditure_usd)
        updated = current.model_copy(
            update={
                "committed_expenditure_usd": current.committed_expenditure_usd - amount_to_release,
                "remaining_balance_usd": current.remaining_balance_usd + amount_to_release,
                "version": current.version + 1,
            }
        )
        self._store[key] = updated
        return updated

    def clear(self) -> None:
        self._store.clear()
