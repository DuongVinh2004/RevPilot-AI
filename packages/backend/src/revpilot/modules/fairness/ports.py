"""
RevPilot AI — Fairness Audit Repository Port and In-Memory Adapter
Specification: docs/11-decision-intelligence/FAIRNESS-SLICE-EVALUATION.md §4
Conforms to INV-TEN-001..003, AC-014, and ADR-0001.
"""

from __future__ import annotations
import asyncio
from typing import Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.modules.fairness.domain import DisparityAuditReport


@runtime_checkable
class FairnessAuditRepository(Protocol):
    """Port defining persistence contracts for fairness and disparity audit reports."""

    async def save_report(self, report: DisparityAuditReport) -> None:
        """Persist an immutable disparity audit report."""
        ...

    async def get_report(
        self, tenant_id: TenantId, report_id: UUIDv7
    ) -> DisparityAuditReport | None:
        """Retrieve an audit report by primary key with tenant isolation."""
        ...

    async def list_reports(
        self, tenant_id: TenantId
    ) -> list[DisparityAuditReport]:
        """List all audit reports scoped strictly to the requesting tenant."""
        ...


class InMemoryFairnessAuditRepository:
    """In-memory thread-safe implementation of FairnessAuditRepository enforcing tenant isolation."""

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, DisparityAuditReport]] = {}
        self._lock = asyncio.Lock()

    async def save_report(self, report: DisparityAuditReport) -> None:
        async with self._lock:
            tenant_key = str(report.tenant_id)
            report_key = str(report.report_id)
            if tenant_key not in self._storage:
                self._storage[tenant_key] = {}
            self._storage[tenant_key][report_key] = report

    async def get_report(
        self, tenant_id: TenantId, report_id: UUIDv7
    ) -> DisparityAuditReport | None:
        async with self._lock:
            tenant_key = str(tenant_id)
            report_key = str(report_id)
            return self._storage.get(tenant_key, {}).get(report_key)

    async def list_reports(
        self, tenant_id: TenantId
    ) -> list[DisparityAuditReport]:
        async with self._lock:
            tenant_key = str(tenant_id)
            tenant_reports = self._storage.get(tenant_key, {})
            return sorted(
                list(tenant_reports.values()),
                key=lambda r: r.created_at.isoformat(),
                reverse=True,
            )
