"""
RevPilot AI — PostgreSQL Evidence Repository Adapter (Phase 03)
Implements persistence for EvidenceRecord and EvidenceBundle against PostgreSQL.
Enforces INV-EVD-001 and INV-TEN-001.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
import asyncpg

from revpilot.infrastructure.database import TenantDatabaseSession
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import NotFoundError
from revpilot.shared.temporal import UtcDateTime


class PostgresEvidenceRepository:
    """
    PostgreSQL persistence adapter for EvidenceRecord and EvidenceBundle.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def save_evidence_record(
        self, context: TenantContext, evidence_data: dict[str, Any]
    ) -> str:
        """Persist an individual EvidenceRecord."""
        evidence_id = evidence_data["id"]
        citation = evidence_data.get("citation_span", {})
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.evidence_records (
                tenant_id, id, investigation_id, source_system, source_object_ref,
                content_digest, classification, extraction_method, retrieval_method,
                citation_span, confidence_score, supersession_status,
                effective_time, as_of_time, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
            )
            ON CONFLICT (tenant_id, id) DO NOTHING
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                evidence_id,
                evidence_data["investigation_id"],
                evidence_data["source_system"],
                evidence_data["source_object_ref"],
                evidence_data["content_digest"],
                evidence_data.get("classification", "INTERNAL"),
                evidence_data["extraction_method"],
                evidence_data["retrieval_method"],
                json.dumps(citation),
                Decimal(str(evidence_data.get("confidence_score", "1.0000"))),
                evidence_data.get("supersession_status", "ACTIVE"),
                evidence_data.get("effective_time", now),
                evidence_data.get("as_of_time", now),
                now,
            )
        return evidence_id

    async def list_by_investigation(
        self, context: TenantContext, investigation_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve all verified evidence records for an investigation."""
        query = """
            SELECT
                id, tenant_id, investigation_id, source_system, source_object_ref,
                content_digest, classification, extraction_method, retrieval_method,
                citation_span, confidence_score, supersession_status, effective_time, as_of_time
            FROM revpilot.evidence_records
            WHERE investigation_id = $1
            ORDER BY created_at ASC
            LIMIT $2;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            rows = await conn.fetch(query, investigation_id, limit)
            results = []
            for r in rows:
                item = dict(r)
                item["confidence_score"] = float(item["confidence_score"])
                item["citation_span"] = json.loads(item["citation_span"]) if isinstance(item["citation_span"], str) else item["citation_span"]
                results.append(item)
            return results
