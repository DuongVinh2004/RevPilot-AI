"""
RevPilot AI — PostgreSQL Causal Study Repository Adapter (Phase 04)
Implements persistence for CausalStudy records against PostgreSQL.
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


class PostgresCausalStudyRepository:
    """
    PostgreSQL persistence adapter for CausalStudy records.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def save_study(self, context: TenantContext, data: dict[str, Any]) -> str:
        """Persist completed causal study."""
        study_id = data["id"]
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.causal_studies (
                tenant_id, id, investigation_id, causal_question, treatment_variable,
                outcome_variable, estimand_type, estimator, point_estimate, standard_error,
                confidence_interval_95, p_value, overlap, sensitivity, reproducibility_seed,
                study_digest, status, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                point_estimate = EXCLUDED.point_estimate,
                standard_error = EXCLUDED.standard_error,
                confidence_interval_95 = EXCLUDED.confidence_interval_95,
                p_value = EXCLUDED.p_value,
                overlap = EXCLUDED.overlap,
                sensitivity = EXCLUDED.sensitivity,
                status = EXCLUDED.status
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                study_id,
                data["investigation_id"],
                data["causal_question"],
                data["treatment_variable"],
                data["outcome_variable"],
                data.get("estimand_type", "ATE"),
                data.get("estimator", "DOUBLY_ROBUST_AIPW"),
                Decimal(str(data["point_estimate"])) if data.get("point_estimate") is not None else None,
                Decimal(str(data["standard_error"])) if data.get("standard_error") is not None else None,
                json.dumps(data.get("confidence_interval_95", {})),
                Decimal(str(data["p_value"])) if data.get("p_value") is not None else None,
                json.dumps(data.get("overlap", {})),
                json.dumps(data.get("sensitivity", {})),
                int(data.get("reproducibility_seed", 42)),
                data.get("study_digest", "hash_placeholder"),
                data.get("status", "COMPLETED"),
                now,
            )
        return study_id

    async def get_by_id(self, context: TenantContext, study_id: str) -> dict[str, Any] | None:
        """Retrieve causal study by ID."""
        query = """
            SELECT
                id, tenant_id, investigation_id, causal_question, treatment_variable,
                outcome_variable, estimand_type, estimator, point_estimate, standard_error,
                confidence_interval_95, p_value, overlap, sensitivity, reproducibility_seed,
                study_digest, status, created_at
            FROM revpilot.causal_studies
            WHERE id = $1;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            row = await conn.fetchrow(query, study_id)
            if not row:
                return None
            res = dict(row)
            if res["point_estimate"] is not None:
                res["point_estimate"] = float(res["point_estimate"])
            if res["standard_error"] is not None:
                res["standard_error"] = float(res["standard_error"])
            if res["p_value"] is not None:
                res["p_value"] = float(res["p_value"])
            res["confidence_interval_95"] = json.loads(res["confidence_interval_95"]) if isinstance(res["confidence_interval_95"], str) else res["confidence_interval_95"]
            res["overlap"] = json.loads(res["overlap"]) if isinstance(res["overlap"], str) else res["overlap"]
            res["sensitivity"] = json.loads(res["sensitivity"]) if isinstance(res["sensitivity"], str) else res["sensitivity"]
            return res
