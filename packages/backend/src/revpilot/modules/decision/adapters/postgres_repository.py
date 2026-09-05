"""
RevPilot AI — PostgreSQL Decision and ML Repository Adapter (Phase 05)
Implements persistence for ChurnPredictionRecord, UpliftScoreRecord, and RecommendationRecord.
Enforces INV-COST-001, INV-TEN-001, and INV-TEN-002.
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


class PostgresDecisionRepository:
    """
    PostgreSQL persistence adapter for ML predictions, uplift scores, and decisions.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def save_churn_prediction(self, context: TenantContext, data: dict[str, Any]) -> str:
        """Save calibrated churn prediction."""
        pred_id = data["id"]
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.churn_predictions (
                tenant_id, id, customer_id, as_of_time, model_artifact_id,
                calibrated_probability, risk_tier, ece_at_release,
                feature_snapshot_digest, is_treatment_contaminated, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                pred_id,
                data["customer_id"],
                data.get("as_of_time", now),
                data["model_artifact_id"],
                Decimal(str(data["calibrated_probability"])),
                data["risk_tier"],
                Decimal(str(data.get("ece_at_release", "0.0250"))),
                data.get("feature_snapshot_digest", "hash_placeholder"),
                bool(data.get("is_treatment_contaminated", False)),
                now,
            )
        return pred_id

    async def save_uplift_score(self, context: TenantContext, data: dict[str, Any]) -> str:
        """Save incremental uplift score."""
        score_id = data["id"]
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.uplift_scores (
                tenant_id, id, customer_id, intervention_type, cate_estimate,
                standard_error, confidence_interval, persuadability_segment, as_of_time, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            )
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                score_id,
                data["customer_id"],
                data["intervention_type"],
                Decimal(str(data["cate_estimate"])),
                Decimal(str(data["standard_error"])),
                json.dumps(data.get("confidence_interval", {})),
                data["persuadability_segment"],
                data.get("as_of_time", now),
                now,
            )
        return score_id

    async def save_recommendation(self, context: TenantContext, data: dict[str, Any]) -> str:
        """Save optimized decision recommendation."""
        rec_id = data["id"]
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.decision_recommendations (
                tenant_id, id, investigation_id, customer_id, selected_action,
                expected_utility, constraint_results, decision_digest, status, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            )
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                rec_id,
                data["investigation_id"],
                data["customer_id"],
                data["selected_action"],
                Decimal(str(data["expected_utility"])),
                json.dumps(data.get("constraint_results", {})),
                data.get("decision_digest", "hash_placeholder"),
                data.get("status", "PROPOSED"),
                now,
            )
        return rec_id
