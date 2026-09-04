"""
RevPilot AI — Analytics Metrics Subpackage
Authoritative public exports for metric definitions, registry, and calculation evaluators.
"""

from revpilot.modules.analytics.metrics.definitions import (
    MetricType,
    MetricGrain,
    MetricEvaluationDataset,
    MetricValue,
    MetricDefinition,
    CANONICAL_METRIC_DEFINITIONS,
    calculate_cancellation_rate,
    calculate_revenue_at_risk,
    calculate_fulfillment_delay_rate,
    calculate_sla_violation_rate,
    calculate_payment_failure_rate,
    calculate_customer_churn_rate,
    calculate_order_volume,
    calculate_shipment_volume,
    calculate_support_ticket_volume,
)
from revpilot.modules.analytics.metrics.registry import (
    MetricNotFoundError,
    InvalidMetricFilterError,
    TemporalLeakageError,
    MetricEvaluationError,
    MetricRegistry,
    CANONICAL_METRIC_REGISTRY,
)

__all__ = [
    # Enums & Value objects
    "MetricType",
    "MetricGrain",
    "MetricEvaluationDataset",
    "MetricValue",
    "MetricDefinition",
    "CANONICAL_METRIC_DEFINITIONS",
    # Evaluator functions
    "calculate_cancellation_rate",
    "calculate_revenue_at_risk",
    "calculate_fulfillment_delay_rate",
    "calculate_sla_violation_rate",
    "calculate_payment_failure_rate",
    "calculate_customer_churn_rate",
    "calculate_order_volume",
    "calculate_shipment_volume",
    "calculate_support_ticket_volume",
    # Errors & Registry
    "MetricNotFoundError",
    "InvalidMetricFilterError",
    "TemporalLeakageError",
    "MetricEvaluationError",
    "MetricRegistry",
    "CANONICAL_METRIC_REGISTRY",
]
