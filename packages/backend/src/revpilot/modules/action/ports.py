"""
RevPilot AI — Action Intent & Ledger Repository Ports and In-Memory Adapters
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.2, §3.3
Conforms to INV-TEN-001..003, INV-ACT-001, and ADR-0001.
"""

from __future__ import annotations
import asyncio
from typing import Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.modules.action.domain import ActionIntentRecord, ActionLedgerRecord


@runtime_checkable
class ActionIntentRepository(Protocol):
    """Port defining persistence contracts for action intent records."""

    async def save(self, intent: ActionIntentRecord) -> None:
        """Persist a new action intent."""
        ...

    async def get(
        self, tenant_id: TenantId, intent_id: UUIDv7
    ) -> ActionIntentRecord | None:
        """Retrieve an action intent by primary key."""
        ...

    async def get_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> ActionIntentRecord | None:
        """Retrieve an action intent by tenant-scoped idempotency key (INV-ACT-001)."""
        ...

    async def update(self, intent: ActionIntentRecord) -> None:
        """Update an existing action intent."""
        ...


@runtime_checkable
class ActionLedgerRepository(Protocol):
    """Port defining persistence contracts for action dispatch journal entries."""

    async def save(self, record: ActionLedgerRecord) -> None:
        """Persist a new action ledger journal entry."""
        ...

    async def get(
        self, tenant_id: TenantId, ledger_id: UUIDv7
    ) -> ActionLedgerRecord | None:
        """Retrieve an action ledger record by primary key."""
        ...

    async def list_by_intent(
        self, tenant_id: TenantId, intent_id: UUIDv7
    ) -> list[ActionLedgerRecord]:
        """List all dispatch attempts for an intent, sorted by attempt number."""
        ...

    async def update(self, record: ActionLedgerRecord) -> None:
        """Update an existing action ledger record."""
        ...


class InMemoryActionIntentRepository:
    """In-memory thread-safe implementation of ActionIntentRepository enforcing tenant airgap."""

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, ActionIntentRecord]] = {}
        self._idempotency_index: dict[str, dict[str, str]] = {}  # tenant_id -> idempotency_key -> intent_id
        self._lock = asyncio.Lock()

    async def save(self, intent: ActionIntentRecord) -> None:
        async with self._lock:
            t_key = str(intent.tenant_id)
            i_key = str(intent.intent_id)
            if t_key not in self._storage:
                self._storage[t_key] = {}
                self._idempotency_index[t_key] = {}
            self._storage[t_key][i_key] = intent
            self._idempotency_index[t_key][intent.idempotency_key] = i_key

    async def get(
        self, tenant_id: TenantId, intent_id: UUIDv7
    ) -> ActionIntentRecord | None:
        async with self._lock:
            t_key = str(tenant_id)
            i_key = str(intent_id)
            return self._storage.get(t_key, {}).get(i_key)

    async def get_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> ActionIntentRecord | None:
        async with self._lock:
            t_key = str(tenant_id)
            intent_id_str = self._idempotency_index.get(t_key, {}).get(idempotency_key)
            if not intent_id_str:
                return None
            return self._storage.get(t_key, {}).get(intent_id_str)

    async def update(self, intent: ActionIntentRecord) -> None:
        async with self._lock:
            t_key = str(intent.tenant_id)
            i_key = str(intent.intent_id)
            if t_key not in self._storage:
                self._storage[t_key] = {}
                self._idempotency_index[t_key] = {}
            self._storage[t_key][i_key] = intent
            self._idempotency_index[t_key][intent.idempotency_key] = i_key


class InMemoryActionLedgerRepository:
    """In-memory thread-safe implementation of ActionLedgerRepository enforcing tenant airgap."""

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, ActionLedgerRecord]] = {}
        self._lock = asyncio.Lock()

    async def save(self, record: ActionLedgerRecord) -> None:
        async with self._lock:
            t_key = str(record.tenant_id)
            l_key = str(record.ledger_id)
            if t_key not in self._storage:
                self._storage[t_key] = {}
            self._storage[t_key][l_key] = record

    async def get(
        self, tenant_id: TenantId, ledger_id: UUIDv7
    ) -> ActionLedgerRecord | None:
        async with self._lock:
            t_key = str(tenant_id)
            l_key = str(ledger_id)
            return self._storage.get(t_key, {}).get(l_key)

    async def list_by_intent(
        self, tenant_id: TenantId, intent_id: UUIDv7
    ) -> list[ActionLedgerRecord]:
        async with self._lock:
            t_key = str(tenant_id)
            records = self._storage.get(t_key, {}).values()
            matched = [r for r in records if r.intent_id == intent_id]
            return sorted(matched, key=lambda r: r.attempt_number)

    async def update(self, record: ActionLedgerRecord) -> None:
        async with self._lock:
            t_key = str(record.tenant_id)
            l_key = str(record.ledger_id)
            if t_key not in self._storage:
                self._storage[t_key] = {}
            self._storage[t_key][l_key] = record
