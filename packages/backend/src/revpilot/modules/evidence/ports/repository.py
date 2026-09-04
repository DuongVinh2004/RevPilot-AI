"""
RevPilot AI — Evidence Repository Port and In-Memory Adapter
Specification: docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md §3, §5
Enforces INV-TEN-001 tenant isolation on persistence boundary.
"""

from __future__ import annotations
import threading
from typing import Protocol, runtime_checkable
from collections import defaultdict

from revpilot.shared.context import TenantContext
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.errors import TenancyViolationError
from revpilot.modules.evidence.domain.models import EvidenceRecord, EvidenceBundle


@runtime_checkable
class EvidenceRepositoryPort(Protocol):
    """Authoritative persistence boundary for evidence records and sealed bundles."""

    def save_evidence(self, context: TenantContext, record: EvidenceRecord) -> None:
        """Persist evidence record within tenant boundary."""
        ...

    def get_evidence(self, context: TenantContext, evidence_id: UUIDv7) -> EvidenceRecord | None:
        """Retrieve evidence record by ID, returning None if missing or cross-tenant."""
        ...

    def save_bundle(self, context: TenantContext, bundle: EvidenceBundle) -> None:
        """Persist sealed evidence bundle within tenant boundary."""
        ...

    def get_bundle(self, context: TenantContext, bundle_id: UUIDv7) -> EvidenceBundle | None:
        """Retrieve evidence bundle by ID, returning None if missing or cross-tenant."""
        ...

    def list_bundles_by_investigation(
        self, context: TenantContext, investigation_id: UUIDv7
    ) -> list[EvidenceBundle]:
        """List all sealed bundles associated with an investigation."""
        ...


class InMemoryEvidenceRepository:
    """
    In-memory thread-safe implementation of EvidenceRepositoryPort.
    Partitions all stored items strictly by TenantId (INV-TEN-001).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[TenantId, dict[UUIDv7, EvidenceRecord]] = defaultdict(dict)
        self._bundles: dict[TenantId, dict[UUIDv7, EvidenceBundle]] = defaultdict(dict)

    def _verify_tenant(self, context: TenantContext, target_tenant: TenantId) -> None:
        if context is None:
            raise TenancyViolationError("TenantContext is required for evidence operations (INV-TEN-001)")
        if not getattr(context, "is_active", True):
            raise TenancyViolationError(f"Tenant '{context.tenant_id}' is not active")
        if context.tenant_id != target_tenant:
            raise TenancyViolationError(
                f"Cross-tenant access violation: context '{context.tenant_id}' != target '{target_tenant}' (INV-TEN-001)"
            )

    def save_evidence(self, context: TenantContext, record: EvidenceRecord) -> None:
        self._verify_tenant(context, record.tenant_id)
        with self._lock:
            self._records[record.tenant_id][record.evidence_id] = record

    def get_evidence(self, context: TenantContext, evidence_id: UUIDv7) -> EvidenceRecord | None:
        if context is None or not getattr(context, "is_active", True):
            raise TenancyViolationError("Valid TenantContext is required (INV-TEN-001)")
        with self._lock:
            return self._records[context.tenant_id].get(evidence_id)

    def save_bundle(self, context: TenantContext, bundle: EvidenceBundle) -> None:
        self._verify_tenant(context, bundle.tenant_id)
        with self._lock:
            self._bundles[bundle.tenant_id][bundle.bundle_id] = bundle

    def get_bundle(self, context: TenantContext, bundle_id: UUIDv7) -> EvidenceBundle | None:
        if context is None or not getattr(context, "is_active", True):
            raise TenancyViolationError("Valid TenantContext is required (INV-TEN-001)")
        with self._lock:
            return self._bundles[context.tenant_id].get(bundle_id)

    def list_bundles_by_investigation(
        self, context: TenantContext, investigation_id: UUIDv7
    ) -> list[EvidenceBundle]:
        if context is None or not getattr(context, "is_active", True):
            raise TenancyViolationError("Valid TenantContext is required (INV-TEN-001)")
        with self._lock:
            return [
                b for b in self._bundles[context.tenant_id].values()
                if b.investigation_id == investigation_id
            ]
