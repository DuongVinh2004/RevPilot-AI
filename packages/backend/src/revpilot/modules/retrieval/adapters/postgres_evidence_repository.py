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

    async def save_document_chunk(
        self, context: TenantContext, chunk_data: dict[str, Any]
    ) -> str:
        """Persist a DocumentChunk with vector embedding."""
        chunk_id = chunk_data["id"]
        now = UtcDateTime.now().as_datetime()
        meta = chunk_data.get("metadata", {})
        emb = chunk_data.get("embedding")
        emb_str = f"[{','.join(str(x) for x in emb)}]" if emb is not None else None

        query = """
            INSERT INTO revpilot.document_chunks (
                tenant_id, id, document_id, chunk_index, content, metadata,
                classification, effective_from, effective_to, created_at, embedding
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                effective_to = EXCLUDED.effective_to,
                embedding = EXCLUDED.embedding
            RETURNING id;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                chunk_id,
                chunk_data["document_id"],
                int(chunk_data.get("chunk_index", 0)),
                chunk_data["content"],
                json.dumps(meta),
                chunk_data.get("classification", "INTERNAL"),
                chunk_data.get("effective_from", now),
                chunk_data.get("effective_to"),
                now,
                emb_str,
            )
        return chunk_id

    async def search_similar_chunks(
        self,
        context: TenantContext,
        query_embedding: list[float],
        top_k: int = 5,
        as_of: UtcDateTime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute vector similarity search using pgvector cosine distance (<=>).
        Filtered strictly by tenant context via RLS and effective temporal window.
        """
        emb_str = f"[{','.join(str(x) for x in query_embedding)}]"
        as_of_dt = as_of.as_datetime() if as_of else UtcDateTime.now().as_datetime()

        query = """
            SELECT
                id, tenant_id, document_id, chunk_index, content, metadata,
                classification, effective_from, effective_to,
                (embedding <=> $1::vector) AS distance
            FROM revpilot.document_chunks
            WHERE (effective_from <= $2)
              AND (effective_to IS NULL OR effective_to > $2)
            ORDER BY embedding <=> $1::vector ASC
            LIMIT $3;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            rows = await conn.fetch(query, emb_str, as_of_dt, top_k)
            results = []
            for r in rows:
                item = dict(r)
                item["metadata"] = json.loads(item["metadata"]) if isinstance(item["metadata"], str) else item["metadata"]
                item["similarity_score"] = 1.0 - float(item["distance"]) if item.get("distance") is not None else 1.0
                results.append(item)
            return results

