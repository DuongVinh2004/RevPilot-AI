"""
RevPilot AI — Tenant Data Export Service
Generates cryptographic, tenant-isolated data snapshots sealed with SHA-256.
Conforms to DATA-GOVERNANCE.md §3, TENANT-OPERATIONS-SPEC.md §3.8, and NFR-TEN-001.
"""

from __future__ import annotations
import hashlib
import json
import re
from typing import Any

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import AuthorizationError, ValidationError
from revpilot.modules.tenancy.domain.models import TenantExportBundle


class TenantExportService:
    """
    Authoritative service producing point-in-time tenant export packages.
    Enforces strict tenant scoping (INV-TEN-001), PII redaction (INV-PRV-001),
    and SHA-256 manifest integrity sealing.
    """

    def __init__(self, datastore: dict[str, list[dict[str, Any]]] | None = None) -> None:
        # Key: collection_name -> list of records with "tenant_id"
        self._datastore = datastore if datastore is not None else {}

    def populate_collection(self, collection_name: str, records: list[dict[str, Any]]) -> None:
        """Register records for export simulation."""
        self._datastore[collection_name] = records

    def export_tenant_data(
        self,
        tenant_id: TenantId,
        as_of_time: UtcDateTime | None = None,
        caller_permissions: set[str] | None = None,
        is_agent: bool = False,
    ) -> TenantExportBundle:
        """
        Produce a point-in-time export bundle strictly containing records for tenant_id.
        Fails closed on unauthorized callers or agent callers (INV-ACT-003).
        """
        # 1. Caller Authorization Check
        if is_agent:
            raise AuthorizationError(
                "Automated agents are strictly prohibited from initiating tenant data exports (INV-ACT-003)",
                details={"is_agent": True},
            )
        perms = caller_permissions or set()
        if "tenant:export" not in perms and "admin" not in perms:
            raise AuthorizationError(
                "Caller lacks mandatory 'tenant:export' permission for data export",
                details={"required_permission": "tenant:export"},
            )

        now = as_of_time or UtcDateTime.now()
        target_tid_str = str(tenant_id)

        # 2. Strict Tenant Scoping: Zero cross-tenant record leakage (NFR-TEN-001)
        exported_records: dict[str, list[dict[str, Any]]] = {}
        total_records = 0

        for collection_name, records in self._datastore.items():
            tenant_scoped: list[dict[str, Any]] = []
            for rec in records:
                rec_tid = str(rec.get("tenant_id", ""))
                if rec_tid == target_tid_str:
                    scrubbed = self._scrub_record(rec)
                    tenant_scoped.append(scrubbed)
            exported_records[collection_name] = tenant_scoped
            total_records += len(tenant_scoped)

        # 3. Create canonical manifest
        manifest_data = {
            "export_id": str(UUIDv7.generate()),
            "tenant_id": target_tid_str,
            "as_of_time": now.isoformat(),
            "schema_version": "1.0",
            "collections": {col: len(recs) for col, recs in exported_records.items()},
            "total_records": total_records,
        }
        manifest_json = json.dumps(manifest_data, sort_keys=True)
        manifest_sha256 = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()

        return TenantExportBundle(
            export_id=UUIDv7.generate(),
            tenant_id=tenant_id,
            as_of_time=now,
            manifest_json=manifest_json,
            manifest_sha256=manifest_sha256,
            record_count=total_records,
            data_payload=exported_records,
            status="SEALED",
        )

    def _scrub_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Redact secrets and mask PII (INV-PRV-001, INV-SEC-001)."""
        scrubbed: dict[str, Any] = {}
        for k, v in record.items():
            if isinstance(v, str):
                # Mask email
                if "@" in v and re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
                    parts = v.split("@")
                    user, domain = parts[0], parts[1]
                    masked_user = user[0] + "***" + (user[-1] if len(user) > 1 else "")
                    scrubbed[k] = f"{masked_user}@{domain}"
                # Redact API key / secrets
                elif any(s in k.lower() for s in ("secret", "api_key", "password", "token", "credential")):
                    scrubbed[k] = "[REDACTED_SECRET]"
                else:
                    scrubbed[k] = v
            elif isinstance(v, dict):
                scrubbed[k] = self._scrub_record(v)
            else:
                scrubbed[k] = v
        return scrubbed
