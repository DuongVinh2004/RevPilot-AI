"""
RevPilot AI — Base Connector Adapter Port
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §2..§4
Conforms to INV-DATA-002, INV-SEC-001, INV-SEC-003, and INV-TEN-001..002.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from revpilot.modules.connectors.domain import (
    ConnectorInstanceRecord,
    ConnectorStatus,
    SyncMode,
)
from revpilot.shared.errors import TenancyViolationError
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


class BaseConnectorAdapter(ABC):
    """
    Abstract Base Class for all RevPilot commercial SaaS connectors.
    Enforces tenant isolation, read-only sync boundary, and error handling.
    """

    def __init__(self, instance_record: ConnectorInstanceRecord) -> None:
        if not isinstance(instance_record, ConnectorInstanceRecord):
            raise TypeError("instance_record must be an instance of ConnectorInstanceRecord")
        self._record = instance_record

    @property
    def connector_id(self) -> str:
        return str(self._record.connector_id)

    @property
    def tenant_id(self) -> TenantId:
        return self._record.tenant_id

    @property
    def provider_name(self) -> str:
        return self._record.provider_name

    @property
    def sync_mode(self) -> SyncMode:
        return self._record.sync_mode

    @property
    def status(self) -> ConnectorStatus:
        return self._record.status

    def verify_tenant_boundary(self, execution_tenant_id: TenantId) -> None:
        """Enforces INV-TEN-001 tenant isolation boundary."""
        if execution_tenant_id != self.tenant_id:
            raise TenancyViolationError(
                f"Cross-tenant sync violation: Connector belongs to tenant '{self.tenant_id}', "
                f"execution requested by '{execution_tenant_id}' (INV-TEN-001).",
                details={
                    "connector_tenant": str(self.tenant_id),
                    "execution_tenant": str(execution_tenant_id),
                },
            )

    @abstractmethod
    def validate_connection(self, scoped_token: str) -> bool:
        """Validates upstream provider connectivity using an ephemeral token."""
        pass

    @abstractmethod
    def sync_incremental(
        self,
        execution_tenant_id: TenantId,
        cursor: str | None,
        batch_size: int = 500,
    ) -> tuple[list[Any], str | None]:
        """
        Pulls incremental records from source, returning mapped canonical entities
        and the updated checkpoint cursor.
        """
        pass
