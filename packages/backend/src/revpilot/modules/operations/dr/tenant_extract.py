"""
RevPilot AI — Single-Tenant Slice Data Extractor
Specification: docs/24-sre/BACKUP-RESTORE-VALIDATION-RUNBOOK.md §8
Conforms to INV-TEN-001, AC-P08-005-02.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


class TenantSliceManifest(BaseModel):
    """Manifest describing isolated single-tenant dataset extracted from global backup."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tenant_id: str
    extracted_at: UtcDateTime
    table_records: dict[str, int]
    total_records: int
    slice_hash: str
    output_file: str


class TenantDataExtractor:
    """
    Extracts a strictly isolated single-tenant partition slice from a restored global database (§8).
    Guarantees zero cross-tenant contamination or leakage into the output artifact (INV-TEN-001).
    """

    def extract_single_tenant_slice(
        self,
        source_data: dict[str, list[dict[str, Any]]],
        tenant_id: TenantId | str,
        output_path: Path | str,
    ) -> TenantSliceManifest:
        """
        Filter source datastore tables by tenant_id and generate cryptographically sealed export slice.
        """
        target_tenant = str(tenant_id)
        filtered_data: dict[str, list[dict[str, Any]]] = {}
        table_counts: dict[str, int] = {}
        total_records = 0

        for table_name, rows in source_data.items():
            tenant_rows: list[dict[str, Any]] = []
            for row in rows:
                # Direct tenant_id field matching or primary tenant record ID
                row_tenant = row.get("tenant_id")
                if table_name == "tenants" and row.get("id") == target_tenant:
                    tenant_rows.append(row)
                elif row_tenant is not None and str(row_tenant) == target_tenant:
                    tenant_rows.append(row)

            filtered_data[table_name] = tenant_rows
            table_counts[table_name] = len(tenant_rows)
            total_records += len(tenant_rows)

        # Serialize and compute digest
        serialized = json.dumps(filtered_data, sort_keys=True, indent=2)
        slice_hash = f"slice_sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"

        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(serialized, encoding="utf-8")

        manifest = TenantSliceManifest(
            tenant_id=target_tenant,
            extracted_at=UtcDateTime.now(),
            table_records=table_counts,
            total_records=total_records,
            slice_hash=slice_hash,
            output_file=str(dest.resolve()),
        )

        logger.info(
            "TENANT_SLICE_EXTRACTED: tenant=%s total_records=%d slice_hash=%s",
            target_tenant,
            total_records,
            slice_hash,
        )
        return manifest
