"""
RevPilot AI — PostgreSQL Hypothesis Repository Adapter (Phase 04)
Implements persistence for Hypothesis aggregates and ranked results against PostgreSQL.
Enforces INV-AI-001, INV-TEN-001, and INV-TEN-002.
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


class PostgresHypothesisRepository:
    """
    PostgreSQL persistence adapter for Hypotheses.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def save_hypothesis(self, context: TenantContext, data: dict[str, Any]) -> str:
        """Persist candidate hypothesis."""
        h_id = data["id"]
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.hypotheses (
                tenant_id, id, investigation_id, statement, epistemic_category,
                hypothesis_type, supporting_evidence, contradicting_evidence,
                evidence_coverage_ratio, ordinal_rank, ranking_score, status,
                causal_study_id, manifest_digest, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $15
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                ordinal_rank = EXCLUDED.ordinal_rank,
                ranking_score = EXCLUDED.ranking_score,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                h_id,
                data["investigation_id"],
                data["statement"],
                data.get("epistemic_category", "CAUSAL_HYPOTHESIS"),
                data["hypothesis_type"],
                json.dumps(data.get("supporting_evidence", [])),
                json.dumps(data.get("contradicting_evidence", [])),
                Decimal(str(data.get("evidence_coverage_ratio", "0.0000"))),
                int(data.get("ordinal_rank", 1)),
                Decimal(str(data.get("ranking_score", "0.0000"))),
                data.get("status", "PROPOSED"),
                data.get("causal_study_id"),
                data.get("manifest_digest", "hash_placeholder"),
                now,
            )
        return h_id

    async def list_by_investigation(
        self, context: TenantContext, investigation_id: str
    ) -> list[dict[str, Any]]:
        """List ranked hypotheses for an investigation."""
        query = """
            SELECT
                id, tenant_id, investigation_id, statement, epistemic_category,
                hypothesis_type, supporting_evidence, contradicting_evidence,
                evidence_coverage_ratio, ordinal_rank, ranking_score, status,
                causal_study_id, manifest_digest, created_at, updated_at
            FROM revpilot.hypotheses
            WHERE investigation_id = $1
            ORDER BY ordinal_rank ASC;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            rows = await conn.fetch(query, investigation_id)
            results = []
            for r in rows:
                item = dict(r)
                item["evidence_coverage_ratio"] = float(item["evidence_coverage_ratio"])
                item["ranking_score"] = float(item["ranking_score"])
                item["supporting_evidence"] = json.loads(item["supporting_evidence"]) if isinstance(item["supporting_evidence"], str) else item["supporting_evidence"]
                item["contradicting_evidence"] = json.loads(item["contradicting_evidence"]) if isinstance(item["contradicting_evidence"], str) else item["contradicting_evidence"]
                results.append(item)
            return results
