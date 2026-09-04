"""
RevPilot AI — Approval Repository Port and In-Memory Adapter
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.1
Conforms to INV-TEN-001..003, INV-ACT-002, and ADR-0001.
"""

from __future__ import annotations
import asyncio
from typing import Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.modules.approval.domain import ApprovalRequestRecord, ApprovalStatus


@runtime_checkable
class ApprovalRepository(Protocol):
    """Port defining persistence contracts for governed approval request records."""

    async def save(self, record: ApprovalRequestRecord) -> None:
        """Persist a new approval request record."""
        ...

    async def get(
        self, tenant_id: TenantId, approval_id: UUIDv7
    ) -> ApprovalRequestRecord | None:
        """Retrieve an approval request by primary key with tenant isolation."""
        ...

    async def update(self, record: ApprovalRequestRecord) -> None:
        """Update an existing approval request record."""
        ...

    async def list_pending(
        self, tenant_id: TenantId
    ) -> list[ApprovalRequestRecord]:
        """List all pending approval requests scoped strictly to the requesting tenant."""
        ...

    async def list_all(
        self, tenant_id: TenantId
    ) -> list[ApprovalRequestRecord]:
        """List all approval requests scoped strictly to the requesting tenant."""
        ...


class InMemoryApprovalRepository:
    """In-memory thread-safe implementation of ApprovalRepository enforcing tenant airgap."""

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, ApprovalRequestRecord]] = {}
        self._lock = asyncio.Lock()

    async def save(self, record: ApprovalRequestRecord) -> None:
        async with self._lock:
            t_key = str(record.tenant_id)
            a_key = str(record.approval_id)
            if t_key not in self._storage:
                self._storage[t_key] = {}
            self._storage[t_key][a_key] = record

    async def get(
        self, tenant_id: TenantId, approval_id: UUIDv7
    ) -> ApprovalRequestRecord | None:
        async with self._lock:
            t_key = str(tenant_id)
            a_key = str(approval_id)
            return self._storage.get(t_key, {}).get(a_key)

    async def update(self, record: ApprovalRequestRecord) -> None:
        async with self._lock:
            t_key = str(record.tenant_id)
            a_key = str(record.approval_id)
            if t_key not in self._storage:
                self._storage[t_key] = {}
            self._storage[t_key][a_key] = record

    async def list_pending(
        self, tenant_id: TenantId
    ) -> list[ApprovalRequestRecord]:
        async with self._lock:
            t_key = str(tenant_id)
            tenant_records = self._storage.get(t_key, {})
            pending = [
                r for r in tenant_records.values()
                if r.status == ApprovalStatus.PENDING
            ]
            return sorted(pending, key=lambda r: r.created_at.isoformat())

    async def list_all(
        self, tenant_id: TenantId
    ) -> list[ApprovalRequestRecord]:
        async with self._lock:
            t_key = str(tenant_id)
            tenant_records = self._storage.get(t_key, {})
            return sorted(list(tenant_records.values()), key=lambda r: r.created_at.isoformat())
