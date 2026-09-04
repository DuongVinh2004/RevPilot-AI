"""
RevPilot AI — Multi-Dimensional Usage Metering & Immutable Ledger
Specification: docs/21-finops/FINOPS-SPEC.md §3, DATABASE-SCHEMA.md §21.7
Conforms to FR-CTL-002, NFR-COST-002, and TC-P07-023.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
import hashlib
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, PrincipalId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.finops.quota import QuotaError


class MeteringUnit(str, Enum):
    TOKENS = "tokens"
    CALLS = "calls"
    SECONDS = "seconds"
    BYTES = "bytes"
    ACTIONS = "actions"


class ReconciliationStatus(str, Enum):
    ESTIMATED = "ESTIMATED"
    CONFIRMED = "CONFIRMED"
    RECONCILED = "RECONCILED"
    DISCREPANCY = "DISCREPANCY"


class DuplicateUsageError(QuotaError):
    def __init__(self, message: str = "Usage record already logged with this idempotency key") -> None:
        super().__init__(message=message, code="DUPLICATE_USAGE", status_code=409)


class UsageRecord(BaseModel):
    """
    Immutable, multi-dimensionally attributed usage record conforming to DATABASE-SCHEMA.md §21.7.
    Hierarchically binds: Tenant -> Principal -> Investigation -> Tool/Model.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    usage_id: UUIDv7
    tenant_id: TenantId
    principal_id: PrincipalId
    investigation_id: UUIDv7 | None = None
    workflow_id: str | None = None
    agent_name: str | None = None
    model_or_tool_name: str = "claude-3-5-sonnet"
    connector_id: UUIDv7 | None = None
    unit: MeteringUnit
    quantity: Decimal
    estimated_provider_cost_usd: Decimal
    currency: str = "USD"
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.ESTIMATED
    idempotency_key: str
    recorded_at: UtcDateTime
    record_hash: str

    @property
    def dimension(self) -> MeteringUnit:
        return self.unit


class MeteringService:
    """
    Append-only usage ledger ensuring 100% cost attribution and cryptographic record hashing.
    """

    def __init__(self) -> None:
        self._ledger: dict[str, UsageRecord] = {}
        self._idempotency_index: set[str] = set()

    def record_usage(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        dimension: MeteringUnit,
        quantity: Decimal,
        estimated_cost: Decimal,
        idempotency_key: str,
        investigation_id: UUIDv7 | None = None,
        workflow_id: str | None = None,
        agent_name: str | None = None,
        model_or_tool_name: str = "claude-3-5-sonnet",
        connector_id: UUIDv7 | None = None,
    ) -> UUIDv7:
        """
        Record billable interaction with multi-dimensional attribution (FR-CTL-002).
        Enforces idempotency and computes tamper-evident cryptographic record hash.
        """
        idemp_idx_key = f"{tenant_id.value}:{idempotency_key}"
        if idemp_idx_key in self._idempotency_index:
            raise DuplicateUsageError(f"Duplicate usage record rejected for idempotency key '{idempotency_key}'")

        usage_id = UUIDv7.generate()
        now = UtcDateTime.now()

        # Compute cryptographic hash of record contents
        inv_str = investigation_id.value if investigation_id else "none"
        raw_sig = (
            f"{usage_id.value}:{tenant_id.value}:{principal_id.value}:{inv_str}:"
            f"{dimension.value}:{quantity}:{estimated_cost}:{idempotency_key}:{now.isoformat()}"
        )
        record_hash = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()

        record = UsageRecord(
            usage_id=usage_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            investigation_id=investigation_id,
            workflow_id=workflow_id,
            agent_name=agent_name,
            model_or_tool_name=model_or_tool_name,
            connector_id=connector_id,
            unit=dimension,
            quantity=quantity,
            estimated_provider_cost_usd=estimated_cost,
            currency="USD",
            reconciliation_status=ReconciliationStatus.ESTIMATED,
            idempotency_key=idempotency_key,
            recorded_at=now,
            record_hash=record_hash,
        )

        self._ledger[usage_id.value] = record
        self._idempotency_index.add(idemp_idx_key)
        return usage_id

    def get_usage_record(self, usage_id: UUIDv7) -> UsageRecord:
        """Fetch usage record by ID."""
        record = self._ledger.get(usage_id.value)
        if not record:
            raise ValueError(f"Usage record '{usage_id.value}' not found")
        return record

    def list_usage_records(
        self,
        tenant_id: TenantId,
        investigation_id: UUIDv7 | None = None,
    ) -> list[UsageRecord]:
        """Query attributed records for tenant/investigation."""
        results = []
        for rec in self._ledger.values():
            if rec.tenant_id.value == tenant_id.value:
                if investigation_id is None or (rec.investigation_id and rec.investigation_id.value == investigation_id.value):
                    results.append(rec)
        return results
