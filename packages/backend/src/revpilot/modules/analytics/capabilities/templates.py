"""
RevPilot AI — Parameterized SQL Templates and Query Digest Builder
Specification: docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md §3, §4
Governs parameterized SQL query construction, canonical digests, and safety checks.
"""

from __future__ import annotations
import hashlib
import json
import re
from typing import Any
from revpilot.modules.analytics.capabilities.catalog import (
    SqlCapabilityDefinition,
    get_capability,
)


PROHIBITED_KEYWORDS = frozenset({
    "drop",
    "alter",
    "create",
    "insert",
    "update",
    "delete",
    "truncate",
    "grant",
    "revoke",
    "execute",
    "exec",
})

PROHIBITED_PATTERNS = [
    re.compile(r";"),               # Statement chaining
    re.compile(r"--"),              # Line comment injection
    re.compile(r"/\*.*?\*/"),       # Block comment injection
]


def detect_prohibited_sql(text: str) -> bool:
    """Check whether text contains prohibited DDL/DML keywords or injection tokens."""
    for pattern in PROHIBITED_PATTERNS:
        if pattern.search(text):
            return True

    # Check for standalone keywords
    tokens = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    for token in tokens:
        if token in PROHIBITED_KEYWORDS:
            return True

    return False


def canonicalize_query_digest(sql: str, params: dict[str, Any]) -> str:
    """
    Produce deterministic SHA-256 query digest conforming to §4.1:
    query_digest = SHA256(canonicalize_sql(template) + ":" + sort_keys_json(params))
    """
    clean_sql = " ".join(sql.strip().split())
    # Serialize parameters with sorted keys and string representation for non-primitives
    clean_params = json.dumps(
        params,
        sort_keys=True,
        default=lambda o: str(o.value) if hasattr(o, "value") else str(o),
    )
    payload = f"{clean_sql}:{clean_params}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_sql_for_capability(
    capability: SqlCapabilityDefinition,
    params: dict[str, Any],
    dialect: str = "sqlite",
) -> tuple[str, dict[str, Any]]:
    """
    Compile parameterized SQL statement and verified parameters for capability.
    Enforces server-side tenant isolation, as_of_time bounding, and limit capping.
    """
    cap_id = capability.capability_id
    bound_params = dict(params)
    max_rows = min(int(params.get("limit", capability.max_rows)), capability.max_rows)
    bound_params["max_rows"] = max_rows

    if cap_id == "CAP-SQL-DRILLDOWN-DIM":
        dimension = params.get("dimension", "order_status")
        if dimension not in capability.allowed_dimensions:
            raise ValueError(f"Dimension '{dimension}' not in allowed dimensions for {cap_id}")

        # Determine column expression and required joins
        if dimension == "order_status":
            dim_expr = "o.order_status"
            join_clause = ""
        elif dimension in ("region", "tier"):
            dim_expr = f"COALESCE(c.{dimension}, 'UNKNOWN')"
            join_clause = "LEFT JOIN canonical_customers c ON o.tenant_id = c.tenant_id AND o.customer_id = c.id"
        elif dimension in ("carrier_code", "warehouse_id"):
            col_name = "carrier_code" if dimension == "carrier_code" else "origin_warehouse"
            dim_expr = f"COALESCE(s.{col_name}, 'UNKNOWN')"
            join_clause = "LEFT JOIN canonical_shipments s ON o.tenant_id = s.tenant_id AND o.id = s.order_id"
        elif dimension == "payment_method":
            dim_expr = "COALESCE(p.gateway_provider, 'UNKNOWN')"
            join_clause = "LEFT JOIN canonical_payment_references p ON o.tenant_id = p.tenant_id AND o.id = p.order_id"
        else:
            dim_expr = f"o.{dimension}"
            join_clause = ""

        sql = f"""SELECT 
    {dim_expr} AS dimension_value,
    COUNT(o.id) AS total_orders,
    SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders,
    ROUND(SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(o.id), 0), 4) AS cancellation_rate,
    SUM(o.total_cents) / 100.0 AS total_revenue
FROM canonical_orders o
{join_clause}
WHERE o.tenant_id = :tenant_id
  AND o.event_time >= :start_time
  AND o.event_time < :end_time
  AND o.event_time <= :as_of_time
GROUP BY {dim_expr}
ORDER BY total_orders DESC
LIMIT :max_rows"""

    elif cap_id == "CAP-SQL-METRIC-TIMESERIES":
        interval = params.get("interval", "day")
        if interval not in capability.allowed_dimensions:
            interval = "day"

        if dialect == "sqlite":
            time_expr = "substr(o.event_time, 1, 13)" if interval == "hour" else "substr(o.event_time, 1, 10)"
        else:
            time_expr = "to_char(o.event_time, 'YYYY-MM-DD HH24:00:00')" if interval == "hour" else "to_char(o.event_time, 'YYYY-MM-DD')"

        sql = f"""SELECT 
    {time_expr} AS time_bucket,
    COUNT(o.id) AS total_orders,
    SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders,
    ROUND(SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(o.id), 0), 4) AS cancellation_rate,
    SUM(o.total_cents) / 100.0 AS total_revenue
FROM canonical_orders o
WHERE o.tenant_id = :tenant_id
  AND o.event_time >= :start_time
  AND o.event_time < :end_time
  AND o.event_time <= :as_of_time
GROUP BY time_bucket
ORDER BY time_bucket ASC
LIMIT :max_rows"""

    elif cap_id == "CAP-SQL-SEGMENT-COMPARE":
        segment_a = params.get("segment_a", "ENTERPRISE")
        segment_b = params.get("segment_b", "SMB")
        bound_params["segment_a"] = segment_a
        bound_params["segment_b"] = segment_b

        sql = """SELECT 
    c.segment,
    COUNT(o.id) AS total_orders,
    SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders,
    ROUND(SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(o.id), 0), 4) AS cancellation_rate,
    SUM(o.total_cents) / 100.0 AS total_revenue
FROM canonical_orders o
JOIN canonical_customers c ON o.tenant_id = c.tenant_id AND o.customer_id = c.id
WHERE o.tenant_id = :tenant_id
  AND o.event_time >= :start_time
  AND o.event_time < :end_time
  AND o.event_time <= :as_of_time
  AND c.segment IN (:segment_a, :segment_b)
GROUP BY c.segment
ORDER BY total_orders DESC
LIMIT :max_rows"""

    elif cap_id == "CAP-SQL-SHIPMENT-DELAY":
        if dialect == "sqlite":
            delay_calc = "(strftime('%s', s.actual_delivered_at) - strftime('%s', s.estimated_delivery_at)) / 3600.0"
        else:
            delay_calc = "EXTRACT(EPOCH FROM (s.actual_delivered_at - s.estimated_delivery_at)) / 3600.0"

        sql = f"""SELECT 
    s.carrier_code,
    s.origin_warehouse,
    COUNT(s.id) AS total_shipments,
    SUM(CASE WHEN s.actual_delivered_at > s.estimated_delivery_at THEN 1 ELSE 0 END) AS delayed_count,
    ROUND(AVG({delay_calc}), 2) AS avg_delay_hours
FROM canonical_shipments s
WHERE s.tenant_id = :tenant_id
  AND s.event_time >= :start_time
  AND s.event_time < :end_time
  AND s.event_time <= :as_of_time
GROUP BY s.carrier_code, s.origin_warehouse
ORDER BY delayed_count DESC
LIMIT :max_rows"""

    elif cap_id == "CAP-SQL-TICKET-VOLUME":
        if dialect == "sqlite":
            response_calc = "(strftime('%s', t.first_response_at) - strftime('%s', t.event_time)) / 3600.0"
        else:
            response_calc = "EXTRACT(EPOCH FROM (t.first_response_at - t.event_time)) / 3600.0"

        sql = f"""SELECT 
    t.category,
    t.priority,
    COUNT(t.id) AS ticket_count,
    ROUND(AVG({response_calc}), 2) AS avg_response_hours
FROM canonical_tickets t
WHERE t.tenant_id = :tenant_id
  AND t.event_time >= :start_time
  AND t.event_time < :end_time
  AND t.event_time <= :as_of_time
GROUP BY t.category, t.priority
ORDER BY ticket_count DESC
LIMIT :max_rows"""

    elif cap_id == "CAP-SQL-MAINTENANCE-WINDOW":
        sql = """SELECT 
    m.system_component,
    m.event_type,
    m.scheduled_start,
    m.scheduled_end,
    m.status
FROM canonical_maintenance_events m
WHERE m.tenant_id = :tenant_id
  AND m.scheduled_start < :end_time
  AND m.scheduled_end > :start_time
  AND m.scheduled_start <= :as_of_time
ORDER BY m.scheduled_start ASC
LIMIT :max_rows"""

    elif cap_id == "CAP-SQL-CONTRACT-SLA":
        sql = """SELECT 
    c.id AS contract_id,
    c.customer_id,
    c.title,
    c.contract_type,
    cl.clause_number,
    cl.clause_type,
    cl.sla_threshold_hours,
    cl.penalty_per_hour_cents
FROM canonical_contracts c
JOIN canonical_contract_clauses cl ON c.tenant_id = cl.tenant_id AND c.id = cl.contract_id
WHERE c.tenant_id = :tenant_id
  AND c.customer_id = :customer_id
  AND c.effective_from <= :as_of_time
  AND (c.effective_to IS NULL OR c.effective_to >= :as_of_time)
ORDER BY cl.clause_number ASC
LIMIT :max_rows"""

    else:
        raise ValueError(f"Unregistered capability template: {cap_id}")

    return sql, bound_params
