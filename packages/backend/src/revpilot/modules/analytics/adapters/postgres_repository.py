"""
RevPilot AI — PostgreSQL Analytics and Anomaly Repository Adapter (Phase 02)
Implements persistence for AnomalyRecord and AnomalyLocalization against PostgreSQL.
Enforces INV-TEN-001, INV-TEN-002, and INV-AI-001.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
import asyncpg

from revpilot.infrastructure.database import TenantDatabaseSession
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import NotFoundError, ValidationError, TenancyViolationError
from revpilot.shared.temporal import UtcDateTime


class PostgresAnomalyRepository:
    """
    PostgreSQL persistence adapter for Anomaly domain entities.
    Executes within TenantDatabaseSession to guarantee RLS boundary enforcement.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def save_anomaly(self, context: TenantContext, anomaly_data: dict[str, Any]) -> str:
        """Persist a newly detected anomaly record within caller tenant boundary."""
        anomaly_id = anomaly_data["id"]
        affected_scope = anomaly_data.get("affected_scope", {})
        evidence_refs = anomaly_data.get("supporting_evidence_refs", [])

        query = """
            INSERT INTO revpilot.anomaly_records (
                tenant_id, id, anomaly_type, metric_id, metric_version, detector_id, detector_version,
                observation_window_start, observation_window_end, event_time, effective_from, as_of_time,
                actual_value, expected_value, anomaly_score, severity, affected_scope,
                supporting_evidence_refs, status, reproducibility_hash, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $21
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            RETURNING id;
        """

        now = UtcDateTime.now().as_datetime()
        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                anomaly_id,
                anomaly_data.get("anomaly_type", "REVENUE_AT_RISK"),
                anomaly_data["metric_id"],
                anomaly_data.get("metric_version", "1.0.0"),
                anomaly_data.get("detector_id", "DET-STL-RESIDUAL-001"),
                anomaly_data.get("detector_version", "1.0.0"),
                anomaly_data["observation_window_start"],
                anomaly_data["observation_window_end"],
                anomaly_data.get("event_time", now),
                anomaly_data.get("effective_from", now),
                anomaly_data.get("as_of_time", now),
                Decimal(str(anomaly_data["actual_value"])),
                Decimal(str(anomaly_data["expected_value"])),
                Decimal(str(anomaly_data.get("anomaly_score", "0.5000"))),
                anomaly_data.get("severity", "HIGH"),
                json.dumps(affected_scope),
                json.dumps(evidence_refs),
                anomaly_data.get("status", "DETECTED"),
                anomaly_data.get("reproducibility_hash", "hash_default"),
                now,
            )
        return anomaly_id

    async def get_by_id(self, context: TenantContext, anomaly_id: str) -> dict[str, Any] | None:
        """Retrieve anomaly by id strictly within tenant boundary via RLS."""
        query = """
            SELECT
                id, tenant_id, anomaly_type, metric_id, metric_version, detector_id,
                observation_window_start, observation_window_end, actual_value, expected_value,
                anomaly_score, severity, affected_scope, supporting_evidence_refs, status,
                reproducibility_hash, created_at, updated_at
            FROM revpilot.anomaly_records
            WHERE id = $1;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            row = await conn.fetchrow(query, anomaly_id)
            if not row:
                return None
            res = dict(row)
            res["actual_value"] = float(res["actual_value"])
            res["expected_value"] = float(res["expected_value"])
            res["anomaly_score"] = float(res["anomaly_score"])
            res["affected_scope"] = json.loads(res["affected_scope"]) if isinstance(res["affected_scope"], str) else res["affected_scope"]
            res["supporting_evidence_refs"] = json.loads(res["supporting_evidence_refs"]) if isinstance(res["supporting_evidence_refs"], str) else res["supporting_evidence_refs"]
            return res

    async def list_anomalies(
        self,
        context: TenantContext,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List anomalies for tenant with optional status and severity filtering."""
        clauses = ["1=1"]
        params: list[Any] = []

        if status:
            params.append(status.upper())
            clauses.append(f"status = ${len(params)}")
        if severity:
            params.append(severity.upper())
            clauses.append(f"severity = ${len(params)}")

        params.append(limit)
        limit_idx = len(params)
        params.append(offset)
        offset_idx = len(params)

        where_sql = " AND ".join(clauses)
        query = f"""
            SELECT
                id, tenant_id, anomaly_type, metric_id, observation_window_start, observation_window_end,
                actual_value, expected_value, anomaly_score, severity, status, created_at
            FROM revpilot.anomaly_records
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ${limit_idx} OFFSET ${offset_idx};
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            rows = await conn.fetch(query, *params)
            results = []
            for r in rows:
                item = dict(r)
                item["actual_value"] = float(item["actual_value"])
                item["expected_value"] = float(item["expected_value"])
                item["anomaly_score"] = float(item["anomaly_score"])
                results.append(item)
            return results

    async def transition_status(
        self, context: TenantContext, anomaly_id: str, target_state: str, reason: str | None = None
    ) -> dict[str, Any]:
        """Transition anomaly lifecycle state."""
        valid_states = {"DETECTED", "VALIDATED", "LOCALIZED", "ACKNOWLEDGED", "SUPPRESSED", "RESOLVED", "REOPENED"}
        if target_state.upper() not in valid_states:
            raise ValidationError(f"Invalid target state '{target_state}'. Must be one of {valid_states}")

        now = UtcDateTime.now().as_datetime()
        query = """
            UPDATE revpilot.anomaly_records
            SET status = $1, updated_at = $2
            WHERE id = $3
            RETURNING id, status, updated_at;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            row = await conn.fetchrow(query, target_state.upper(), now, anomaly_id)
            if not row:
                raise NotFoundError(f"Anomaly '{anomaly_id}' not found or inaccessible in tenant boundary.")
            return dict(row)
