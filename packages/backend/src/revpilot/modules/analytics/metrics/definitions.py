"""
RevPilot AI — Canonical Metric Definitions & Mathematical Evaluators (Phase 01)
Implements METRIC-001 through METRIC-009 calculation logic according to METRIC-REGISTRY.md.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Sequence

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.canonical import (
    Customer,
    CustomerStatus,
    Order,
    OrderStatus,
    OrderLine,
    Shipment,
    SupportTicket,
    TicketTopic,
    TicketStatus,
    MaintenanceEvent,
    Contract,
    ContractClause,
    PaymentReference,
    PaymentStatus,
)


class MetricType(str, Enum):
    """Aggregation semantics for business metrics."""
    RATIO = "RATIO"
    SUM = "SUM"
    COUNT = "COUNT"
    AVG = "AVG"


class MetricGrain(str, Enum):
    """Temporal evaluation resolution."""
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    AS_OF_SNAPSHOT = "AS_OF_SNAPSHOT"


@dataclass(frozen=True, slots=True)
class MetricEvaluationDataset:
    """In-memory dataset container for metric evaluations."""
    customers: Sequence[Customer] = ()
    orders: Sequence[Order] = ()
    order_lines: Sequence[OrderLine] = ()
    shipments: Sequence[Shipment] = ()
    support_tickets: Sequence[SupportTicket] = ()
    maintenance_events: Sequence[MaintenanceEvent] = ()
    contracts: Sequence[Contract] = ()
    contract_clauses: Sequence[ContractClause] = ()
    payment_references: Sequence[PaymentReference] = ()


@dataclass(frozen=True, slots=True)
class MetricValue:
    """Calculated metric result conforming to CANONICAL-DATA-MODEL & METRIC-REGISTRY."""
    metric_id: str
    tenant_id: TenantId
    value: float | int
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    grain: MetricGrain = MetricGrain.DAILY
    as_of: UtcDateTime = field(default_factory=UtcDateTime.now)
    is_zero_sample: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """Immutable specification contract for a registered business metric."""
    metric_id: str
    name: str
    version: str
    metric_type: MetricType
    unit: str
    allowed_dimensions: list[str]
    calculate_fn: Callable[[TenantId, MetricEvaluationDataset, UtcDateTime, Optional[dict[str, Any]]], MetricValue]
    description: str = ""


# =============================================================================
# Helper utilities for evaluations
# =============================================================================

def _build_indexes(data: MetricEvaluationDataset, tenant_id: TenantId, as_of: UtcDateTime):
    """Build fast lookup indexes for joined dimensions."""
    customer_by_id: dict[str, Customer] = {}
    for c in data.customers:
        if c.tenant_id == tenant_id and c.event_time.value <= as_of.value:
            customer_by_id[c.id] = c

    shipments_by_order: dict[str, list[Shipment]] = {}
    for s in data.shipments:
        if s.tenant_id == tenant_id and s.event_time.value <= as_of.value:
            shipments_by_order.setdefault(s.order_id, []).append(s)

    lines_by_order: dict[str, list[OrderLine]] = {}
    for ol in data.order_lines:
        if ol.tenant_id == tenant_id and ol.event_time.value <= as_of.value:
            lines_by_order.setdefault(ol.order_id, []).append(ol)

    tickets_by_order: dict[str, list[SupportTicket]] = {}
    for t in data.support_tickets:
        if t.tenant_id == tenant_id and t.event_time.value <= as_of.value:
            if t.order_id:
                tickets_by_order.setdefault(t.order_id, []).append(t)

    clauses_by_contract: dict[str, list[ContractClause]] = {}
    for cl in data.contract_clauses:
        if cl.tenant_id == tenant_id and cl.event_time.value <= as_of.value:
            clauses_by_contract.setdefault(cl.contract_id, []).append(cl)

    contracts_by_customer: dict[str, list[Contract]] = {}
    for ctr in data.contracts:
        if ctr.tenant_id == tenant_id and ctr.event_time.value <= as_of.value:
            contracts_by_customer.setdefault(ctr.customer_id, []).append(ctr)

    return (
        customer_by_id,
        shipments_by_order,
        lines_by_order,
        tickets_by_order,
        clauses_by_contract,
        contracts_by_customer,
    )


# =============================================================================
# Mathematical Evaluators (METRIC-001 through METRIC-009)
# =============================================================================

def calculate_cancellation_rate(
    tenant_id: TenantId,
    data: MetricEvaluationDataset,
    as_of: UtcDateTime,
    filters: Optional[dict[str, Any]] = None,
) -> MetricValue:
    """METRIC-001: Proportion of orders transitioning to CANCELLED."""
    filters = filters or {}
    (
        customer_by_id,
        shipments_by_order,
        lines_by_order,
        _,
        _,
        _,
    ) = _build_indexes(data, tenant_id, as_of)

    eligible_orders: list[Order] = []
    for order in data.orders:
        if order.tenant_id != tenant_id or order.event_time.value > as_of.value:
            continue

        # Dimension filtering
        if "customer_tier" in filters:
            cust = customer_by_id.get(order.customer_id)
            if not cust or (cust.account_tier.value != filters["customer_tier"] and cust.account_tier != filters["customer_tier"]):
                continue

        order_shipments = shipments_by_order.get(order.id, [])
        if "carrier_id" in filters:
            if not any(s.carrier_id == filters["carrier_id"] for s in order_shipments):
                continue
        if "warehouse_id" in filters:
            if not any(s.warehouse_id == filters["warehouse_id"] for s in order_shipments):
                continue
        if "origin_region" in filters:
            if not any(s.origin_region == filters["origin_region"] for s in order_shipments):
                continue
        if "destination_region" in filters:
            if not any(s.destination_region == filters["destination_region"] for s in order_shipments):
                continue

        if "product_category" in filters:
            order_lines = lines_by_order.get(order.id, [])
            if not any(l.product_category == filters["product_category"] for l in order_lines):
                continue

        eligible_orders.append(order)

    denominator = len(eligible_orders)
    if denominator == 0:
        return MetricValue(
            metric_id="METRIC-001",
            tenant_id=tenant_id,
            value=0.0,
            numerator=0.0,
            denominator=0.0,
            grain=MetricGrain.DAILY,
            as_of=as_of,
            is_zero_sample=True,
        )

    numerator = sum(
        1
        for o in eligible_orders
        if o.order_status == OrderStatus.CANCELLED
        and (o.cancelled_at is None or o.cancelled_at.value <= as_of.value)
    )

    ratio = round(float(numerator) / float(denominator), 4)
    return MetricValue(
        metric_id="METRIC-001",
        tenant_id=tenant_id,
        value=ratio,
        numerator=float(numerator),
        denominator=float(denominator),
        grain=MetricGrain.DAILY,
        as_of=as_of,
        is_zero_sample=False,
    )


def calculate_revenue_at_risk(
    tenant_id: TenantId,
    data: MetricEvaluationDataset,
    as_of: UtcDateTime,
    filters: Optional[dict[str, Any]] = None,
) -> MetricValue:
    """METRIC-002: Total cents of active orders exposed to delay or cancellation signals."""
    filters = filters or {}
    (
        customer_by_id,
        shipments_by_order,
        _,
        tickets_by_order,
        _,
        _,
    ) = _build_indexes(data, tenant_id, as_of)

    total_risk_cents = 0
    at_risk_orders_count = 0

    for order in data.orders:
        if order.tenant_id != tenant_id or order.event_time.value > as_of.value:
            continue

        if "customer_tier" in filters:
            cust = customer_by_id.get(order.customer_id)
            if not cust or (cust.account_tier.value != filters["customer_tier"] and cust.account_tier != filters["customer_tier"]):
                continue

        order_shipments = shipments_by_order.get(order.id, [])
        if "carrier_id" in filters:
            if not any(s.carrier_id == filters["carrier_id"] for s in order_shipments):
                continue
        if "warehouse_id" in filters:
            if not any(s.warehouse_id == filters["warehouse_id"] for s in order_shipments):
                continue
        if "origin_region" in filters:
            if not any(s.origin_region == filters["origin_region"] for s in order_shipments):
                continue

        # Condition: shipment is delayed OR open ticket with cancellation inquiry
        has_delayed_shipment = any(s.is_delayed for s in order_shipments)
        order_tickets = tickets_by_order.get(order.id, [])
        has_cancellation_inquiry = any(
            t.topic == TicketTopic.CANCELLATION_INQUIRY and t.status == TicketStatus.OPEN
            for t in order_tickets
        )

        if has_delayed_shipment or has_cancellation_inquiry:
            total_risk_cents += order.total_cents
            at_risk_orders_count += 1

    return MetricValue(
        metric_id="METRIC-002",
        tenant_id=tenant_id,
        value=total_risk_cents,
        numerator=float(total_risk_cents),
        denominator=float(at_risk_orders_count),
        grain=MetricGrain.AS_OF_SNAPSHOT,
        as_of=as_of,
        is_zero_sample=(at_risk_orders_count == 0),
    )


def calculate_fulfillment_delay_rate(
    tenant_id: TenantId,
    data: MetricEvaluationDataset,
    as_of: UtcDateTime,
    filters: Optional[dict[str, Any]] = None,
) -> MetricValue:
    """METRIC-003: Percentage of shipments where is_delayed is True."""
    filters = filters or {}
    eligible_shipments: list[Shipment] = []

    for s in data.shipments:
        if s.tenant_id != tenant_id or s.event_time.value > as_of.value:
            continue
        if "carrier_id" in filters and s.carrier_id != filters["carrier_id"]:
            continue
        if "warehouse_id" in filters and s.warehouse_id != filters["warehouse_id"]:
            continue
        if "origin_region" in filters and s.origin_region != filters["origin_region"]:
            continue
        if "destination_region" in filters and s.destination_region != filters["destination_region"]:
            continue
        eligible_shipments.append(s)

    denominator = len(eligible_shipments)
    if denominator == 0:
        return MetricValue(
            metric_id="METRIC-003",
            tenant_id=tenant_id,
            value=0.0,
            numerator=0.0,
            denominator=0.0,
            grain=MetricGrain.DAILY,
            as_of=as_of,
            is_zero_sample=True,
        )

    numerator = sum(1 for s in eligible_shipments if s.is_delayed)
    ratio = round(float(numerator) / float(denominator), 4)
    return MetricValue(
        metric_id="METRIC-003",
        tenant_id=tenant_id,
        value=ratio,
        numerator=float(numerator),
        denominator=float(denominator),
        grain=MetricGrain.DAILY,
        as_of=as_of,
        is_zero_sample=False,
    )


def calculate_sla_violation_rate(
    tenant_id: TenantId,
    data: MetricEvaluationDataset,
    as_of: UtcDateTime,
    filters: Optional[dict[str, Any]] = None,
) -> MetricValue:
    """METRIC-004: Proportion of delivered orders exceeding contract SLA thresholds."""
    filters = filters or {}
    (
        customer_by_id,
        shipments_by_order,
        _,
        _,
        clauses_by_contract,
        contracts_by_customer,
    ) = _build_indexes(data, tenant_id, as_of)

    evaluated_delivered_orders = 0
    sla_breaches = 0

    for order in data.orders:
        if order.tenant_id != tenant_id or order.event_time.value > as_of.value:
            continue

        cust = customer_by_id.get(order.customer_id)
        if not cust:
            continue

        if "customer_tier" in filters:
            if cust.account_tier.value != filters["customer_tier"] and cust.account_tier != filters["customer_tier"]:
                continue

        customer_contracts = contracts_by_customer.get(cust.id, [])
        if "contract_type" in filters:
            customer_contracts = [
                c for c in customer_contracts
                if c.contract_type.value == filters["contract_type"] or c.contract_type == filters["contract_type"]
            ]

        if not customer_contracts:
            continue

        order_shipments = shipments_by_order.get(order.id, [])
        if "carrier_id" in filters:
            order_shipments = [s for s in order_shipments if s.carrier_id == filters["carrier_id"]]

        # Find delivered shipment
        delivered_shipments = [
            s for s in order_shipments
            if s.actual_delivered_at is not None and s.actual_delivered_at.value <= as_of.value
        ]
        if not delivered_shipments:
            continue

        # Look up SLA threshold from clauses
        sla_threshold_hours: Optional[int] = None
        for ctr in customer_contracts:
            for cl in clauses_by_contract.get(ctr.id, []):
                if cl.sla_threshold_hours is not None:
                    if sla_threshold_hours is None or cl.sla_threshold_hours < sla_threshold_hours:
                        sla_threshold_hours = cl.sla_threshold_hours

        if sla_threshold_hours is None:
            continue

        evaluated_delivered_orders += 1
        # Check delivery duration against order.event_time
        earliest_delivery = min(s.actual_delivered_at.value for s in delivered_shipments)  # type: ignore
        duration_hours = (earliest_delivery - order.event_time.value).total_seconds() / 3600.0

        if duration_hours > sla_threshold_hours:
            sla_breaches += 1

    if evaluated_delivered_orders == 0:
        return MetricValue(
            metric_id="METRIC-004",
            tenant_id=tenant_id,
            value=0.0,
            numerator=0.0,
            denominator=0.0,
            grain=MetricGrain.DAILY,
            as_of=as_of,
            is_zero_sample=True,
        )

    ratio = round(float(sla_breaches) / float(evaluated_delivered_orders), 4)
    return MetricValue(
        metric_id="METRIC-004",
        tenant_id=tenant_id,
        value=ratio,
        numerator=float(sla_breaches),
        denominator=float(evaluated_delivered_orders),
        grain=MetricGrain.DAILY,
        as_of=as_of,
        is_zero_sample=False,
    )


def calculate_payment_failure_rate(
    tenant_id: TenantId,
    data: MetricEvaluationDataset,
    as_of: UtcDateTime,
    filters: Optional[dict[str, Any]] = None,
) -> MetricValue:
    """METRIC-005: Ratio of failed payment attempts to total attempts."""
    filters = filters or {}
    eligible_payments: list[PaymentReference] = []

    for p in data.payment_references:
        if p.tenant_id != tenant_id or p.processed_at.value > as_of.value:
            continue
        if "gateway_provider" in filters:
            val = filters["gateway_provider"]
            if p.gateway_provider.value != val and p.gateway_provider != val:
                continue
        if "transaction_type" in filters:
            val = filters["transaction_type"]
            if p.transaction_type.value != val and p.transaction_type != val:
                continue
        if "currency" in filters:
            val = filters["currency"]
            if p.currency.value != val and p.currency != val:
                continue
        eligible_payments.append(p)

    denominator = len(eligible_payments)
    if denominator == 0:
        return MetricValue(
            metric_id="METRIC-005",
            tenant_id=tenant_id,
            value=0.0,
            numerator=0.0,
            denominator=0.0,
            grain=MetricGrain.DAILY,
            as_of=as_of,
            is_zero_sample=True,
        )

    numerator = sum(1 for p in eligible_payments if p.payment_status == PaymentStatus.FAILED)
    ratio = round(float(numerator) / float(denominator), 4)
    return MetricValue(
        metric_id="METRIC-005",
        tenant_id=tenant_id,
        value=ratio,
        numerator=float(numerator),
        denominator=float(denominator),
        grain=MetricGrain.DAILY,
        as_of=as_of,
        is_zero_sample=False,
    )


def calculate_customer_churn_rate(
    tenant_id: TenantId,
    data: MetricEvaluationDataset,
    as_of: UtcDateTime,
    filters: Optional[dict[str, Any]] = None,
) -> MetricValue:
    """METRIC-006: Percentage of active customer cohort that transitioned to CHURNED."""
    filters = filters or {}
    eligible_customers: list[Customer] = []

    for c in data.customers:
        if c.tenant_id != tenant_id or c.event_time.value > as_of.value:
            continue
        if "segment" in filters:
            val = filters["segment"]
            if c.segment.value != val and c.segment != val:
                continue
        if "account_tier" in filters:
            val = filters["account_tier"]
            if c.account_tier.value != val and c.account_tier != val:
                continue
        if "billing_country" in filters and c.billing_country != filters["billing_country"]:
            continue

        if c.status in (CustomerStatus.ACTIVE, CustomerStatus.CHURN_RISK, CustomerStatus.CHURNED):
            eligible_customers.append(c)

    denominator = len(eligible_customers)
    if denominator == 0:
        return MetricValue(
            metric_id="METRIC-006",
            tenant_id=tenant_id,
            value=0.0,
            numerator=0.0,
            denominator=0.0,
            grain=MetricGrain.MONTHLY,
            as_of=as_of,
            is_zero_sample=True,
        )

    numerator = sum(1 for c in eligible_customers if c.status == CustomerStatus.CHURNED)
    ratio = round(float(numerator) / float(denominator), 4)
    return MetricValue(
        metric_id="METRIC-006",
        tenant_id=tenant_id,
        value=ratio,
        numerator=float(numerator),
        denominator=float(denominator),
        grain=MetricGrain.MONTHLY,
        as_of=as_of,
        is_zero_sample=False,
    )


def calculate_order_volume(
    tenant_id: TenantId,
    data: MetricEvaluationDataset,
    as_of: UtcDateTime,
    filters: Optional[dict[str, Any]] = None,
) -> MetricValue:
    """METRIC-007: Total count of distinct orders placed."""
    filters = filters or {}
    (
        customer_by_id,
        shipments_by_order,
        lines_by_order,
        _,
        _,
        _,
    ) = _build_indexes(data, tenant_id, as_of)

    matching_count = 0
    for order in data.orders:
        if order.tenant_id != tenant_id or order.event_time.value > as_of.value:
            continue

        if "customer_tier" in filters:
            cust = customer_by_id.get(order.customer_id)
            if not cust or (cust.account_tier.value != filters["customer_tier"] and cust.account_tier != filters["customer_tier"]):
                continue

        if "origin_region" in filters:
            order_shipments = shipments_by_order.get(order.id, [])
            if not any(s.origin_region == filters["origin_region"] for s in order_shipments):
                continue

        if "product_category" in filters:
            order_lines = lines_by_order.get(order.id, [])
            if not any(l.product_category == filters["product_category"] for l in order_lines):
                continue

        matching_count += 1

    return MetricValue(
        metric_id="METRIC-007",
        tenant_id=tenant_id,
        value=matching_count,
        numerator=float(matching_count),
        grain=MetricGrain.DAILY,
        as_of=as_of,
        is_zero_sample=(matching_count == 0),
    )


def calculate_shipment_volume(
    tenant_id: TenantId,
    data: MetricEvaluationDataset,
    as_of: UtcDateTime,
    filters: Optional[dict[str, Any]] = None,
) -> MetricValue:
    """METRIC-008: Total count of distinct shipment dispatches."""
    filters = filters or {}
    matching_count = 0

    for s in data.shipments:
        if s.tenant_id != tenant_id or s.event_time.value > as_of.value:
            continue
        if "carrier_id" in filters and s.carrier_id != filters["carrier_id"]:
            continue
        if "warehouse_id" in filters and s.warehouse_id != filters["warehouse_id"]:
            continue
        if "origin_region" in filters and s.origin_region != filters["origin_region"]:
            continue
        matching_count += 1

    return MetricValue(
        metric_id="METRIC-008",
        tenant_id=tenant_id,
        value=matching_count,
        numerator=float(matching_count),
        grain=MetricGrain.DAILY,
        as_of=as_of,
        is_zero_sample=(matching_count == 0),
    )


def calculate_support_ticket_volume(
    tenant_id: TenantId,
    data: MetricEvaluationDataset,
    as_of: UtcDateTime,
    filters: Optional[dict[str, Any]] = None,
) -> MetricValue:
    """METRIC-009: Total count of new support tickets submitted."""
    filters = filters or {}
    customer_by_id, _, _, _, _, _ = _build_indexes(data, tenant_id, as_of)

    matching_count = 0
    for t in data.support_tickets:
        if t.tenant_id != tenant_id or t.event_time.value > as_of.value:
            continue

        if "topic" in filters:
            val = filters["topic"]
            if t.topic.value != val and t.topic != val:
                continue
        if "priority" in filters:
            val = filters["priority"]
            if t.priority.value != val and t.priority != val:
                continue
        if "customer_tier" in filters:
            cust = customer_by_id.get(t.customer_id)
            if not cust or (cust.account_tier.value != filters["customer_tier"] and cust.account_tier != filters["customer_tier"]):
                continue

        matching_count += 1

    return MetricValue(
        metric_id="METRIC-009",
        tenant_id=tenant_id,
        value=matching_count,
        numerator=float(matching_count),
        grain=MetricGrain.DAILY,
        as_of=as_of,
        is_zero_sample=(matching_count == 0),
    )


# =============================================================================
# Canonical 9 Metric Definitions List
# =============================================================================

CANONICAL_METRIC_DEFINITIONS: list[MetricDefinition] = [
    MetricDefinition(
        metric_id="METRIC-001",
        name="cancellation_rate",
        version="1.0.0",
        metric_type=MetricType.RATIO,
        unit="PERCENT",
        allowed_dimensions=[
            "carrier_id",
            "warehouse_id",
            "origin_region",
            "destination_region",
            "customer_tier",
            "product_category",
        ],
        calculate_fn=calculate_cancellation_rate,
        description="The proportion of customer orders placed within window that transitioned to CANCELLED.",
    ),
    MetricDefinition(
        metric_id="METRIC-002",
        name="revenue_at_risk",
        version="1.0.0",
        metric_type=MetricType.SUM,
        unit="CURRENCY_MINOR_UNITS",
        allowed_dimensions=["customer_tier", "carrier_id", "warehouse_id", "origin_region"],
        calculate_fn=calculate_revenue_at_risk,
        description="Total monetary value (cents) of active orders exposed to severe delays or cancellation signals.",
    ),
    MetricDefinition(
        metric_id="METRIC-003",
        name="fulfillment_delay_rate",
        version="1.0.0",
        metric_type=MetricType.RATIO,
        unit="PERCENT",
        allowed_dimensions=["carrier_id", "warehouse_id", "origin_region", "destination_region"],
        calculate_fn=calculate_fulfillment_delay_rate,
        description="The percentage of shipments where dispatch or delivery exceeded promises (is_delayed = true).",
    ),
    MetricDefinition(
        metric_id="METRIC-004",
        name="sla_violation_rate",
        version="1.0.0",
        metric_type=MetricType.RATIO,
        unit="PERCENT",
        allowed_dimensions=["customer_tier", "contract_type", "carrier_id"],
        calculate_fn=calculate_sla_violation_rate,
        description="The proportion of contract-governed delivered orders that breached contractual SLA thresholds.",
    ),
    MetricDefinition(
        metric_id="METRIC-005",
        name="payment_failure_rate",
        version="1.0.0",
        metric_type=MetricType.RATIO,
        unit="PERCENT",
        allowed_dimensions=["gateway_provider", "transaction_type", "currency"],
        calculate_fn=calculate_payment_failure_rate,
        description="The ratio of failed payment attempts to total payment authorization and capture attempts.",
    ),
    MetricDefinition(
        metric_id="METRIC-006",
        name="customer_churn_rate",
        version="1.0.0",
        metric_type=MetricType.RATIO,
        unit="PERCENT",
        allowed_dimensions=["segment", "account_tier", "billing_country"],
        calculate_fn=calculate_customer_churn_rate,
        description="Percentage of active customers at start of cohort who transitioned to CHURNED status.",
    ),
    MetricDefinition(
        metric_id="METRIC-007",
        name="order_volume",
        version="1.0.0",
        metric_type=MetricType.COUNT,
        unit="COUNT",
        allowed_dimensions=["customer_tier", "origin_region", "product_category"],
        calculate_fn=calculate_order_volume,
        description="Total count of distinct orders placed within the time grain.",
    ),
    MetricDefinition(
        metric_id="METRIC-008",
        name="shipment_volume",
        version="1.0.0",
        metric_type=MetricType.COUNT,
        unit="COUNT",
        allowed_dimensions=["carrier_id", "warehouse_id", "origin_region"],
        calculate_fn=calculate_shipment_volume,
        description="Total count of distinct shipment dispatches initiated within the time grain.",
    ),
    MetricDefinition(
        metric_id="METRIC-009",
        name="support_ticket_volume",
        version="1.0.0",
        metric_type=MetricType.COUNT,
        unit="COUNT",
        allowed_dimensions=["topic", "priority", "customer_tier"],
        calculate_fn=calculate_support_ticket_volume,
        description="Total count of new support tickets submitted within the time grain.",
    ),
]

__all__ = [
    "MetricType",
    "MetricGrain",
    "MetricEvaluationDataset",
    "MetricValue",
    "MetricDefinition",
    "CANONICAL_METRIC_DEFINITIONS",
    "calculate_cancellation_rate",
    "calculate_revenue_at_risk",
    "calculate_fulfillment_delay_rate",
    "calculate_sla_violation_rate",
    "calculate_payment_failure_rate",
    "calculate_customer_churn_rate",
    "calculate_order_volume",
    "calculate_shipment_volume",
    "calculate_support_ticket_volume",
]
