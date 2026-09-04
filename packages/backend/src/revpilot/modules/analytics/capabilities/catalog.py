"""
RevPilot AI — Authoritative SQL Capability Catalog
Specification: docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md
Governs pre-registered, read-only SQL analytical templates enforcing FR-INV-004,
INV-TEN-001..003, INV-DATA-001, and INV-ACT-001.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SqlCapabilityDefinition:
    """Authoritative definition for a pre-registered SQL analytical capability."""

    capability_id: str
    name: str
    description: str
    canonical_tables: tuple[str, ...]
    max_rows: int
    timeout_ms: int = 5000
    required_permission: str = "analytics:query"
    allowed_dimensions: tuple[str, ...] = field(default_factory=tuple)
    cost_estimate_usd: Decimal = Decimal("0.01")


REGISTERED_SQL_CAPABILITIES: dict[str, SqlCapabilityDefinition] = {
    "CAP-SQL-DRILLDOWN-DIM": SqlCapabilityDefinition(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        name="Metric Drilldown Across Dimension",
        description="Drill down metric across allowed canonical dimension with zero-division safety.",
        canonical_tables=("canonical_orders", "canonical_order_lines"),
        max_rows=100,
        timeout_ms=5000,
        required_permission="analytics:query",
        allowed_dimensions=(
            "order_status",
            "region",
            "tier",
            "payment_method",
            "fulfillment_channel",
            "carrier_code",
            "warehouse_id",
        ),
        cost_estimate_usd=Decimal("0.01"),
    ),
    "CAP-SQL-METRIC-TIMESERIES": SqlCapabilityDefinition(
        capability_id="CAP-SQL-METRIC-TIMESERIES",
        name="Metric Time Series with Aggregations",
        description="Time-bucketed metric series with order count, cancellation rate, and revenue.",
        canonical_tables=("canonical_orders", "canonical_order_lines"),
        max_rows=500,
        timeout_ms=5000,
        required_permission="analytics:query",
        allowed_dimensions=("hour", "day", "week", "month"),
        cost_estimate_usd=Decimal("0.02"),
    ),
    "CAP-SQL-SEGMENT-COMPARE": SqlCapabilityDefinition(
        capability_id="CAP-SQL-SEGMENT-COMPARE",
        name="Customer Segment Comparison",
        description="Compare operational and financial metrics between customer segments or tiers.",
        canonical_tables=("canonical_orders", "canonical_customers"),
        max_rows=50,
        timeout_ms=3000,
        required_permission="analytics:query",
        allowed_dimensions=("segment", "tier"),
        cost_estimate_usd=Decimal("0.01"),
    ),
    "CAP-SQL-SHIPMENT-DELAY": SqlCapabilityDefinition(
        capability_id="CAP-SQL-SHIPMENT-DELAY",
        name="Fulfillment Shipment Delays",
        description="Aggregate shipment delays and average delay durations by carrier and warehouse.",
        canonical_tables=("canonical_shipments",),
        max_rows=100,
        timeout_ms=5000,
        required_permission="analytics:query",
        allowed_dimensions=(
            "carrier_code",
            "origin_warehouse",
            "destination_region",
            "delayed_status",
        ),
        cost_estimate_usd=Decimal("0.01"),
    ),
    "CAP-SQL-TICKET-VOLUME": SqlCapabilityDefinition(
        capability_id="CAP-SQL-TICKET-VOLUME",
        name="Support Ticket Volume and Response Times",
        description="Aggregate ticket counts and average response duration by category and priority.",
        canonical_tables=("canonical_tickets",),
        max_rows=100,
        timeout_ms=5000,
        required_permission="analytics:query",
        allowed_dimensions=("category", "priority"),
        cost_estimate_usd=Decimal("0.01"),
    ),
    "CAP-SQL-MAINTENANCE-WINDOW": SqlCapabilityDefinition(
        capability_id="CAP-SQL-MAINTENANCE-WINDOW",
        name="System Maintenance Windows",
        description="Check overlapping facility and infrastructure maintenance events.",
        canonical_tables=("canonical_maintenance_events",),
        max_rows=50,
        timeout_ms=3000,
        required_permission="analytics:query",
        allowed_dimensions=("system_component", "event_type"),
        cost_estimate_usd=Decimal("0.005"),
    ),
    "CAP-SQL-CONTRACT-SLA": SqlCapabilityDefinition(
        capability_id="CAP-SQL-CONTRACT-SLA",
        name="Contract SLA Penalty Clauses",
        description="Retrieve active SLA penalty clauses and thresholds for an account or customer.",
        canonical_tables=("canonical_contracts", "canonical_contract_clauses"),
        max_rows=50,
        timeout_ms=3000,
        required_permission="analytics:query",
        allowed_dimensions=("contract_type", "clause_type"),
        cost_estimate_usd=Decimal("0.005"),
    ),
}


def get_capability(capability_id: str) -> SqlCapabilityDefinition | None:
    """Retrieve capability definition by identifier, or None if unregistered."""
    return REGISTERED_SQL_CAPABILITIES.get(capability_id)
