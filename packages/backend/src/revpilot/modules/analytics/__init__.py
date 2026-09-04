"""
RevPilot AI — Analytics Module
Authoritative public exports for analytics module metrics, query gateway, and data contracts.
Conforms to MODULE-BOUNDARIES.md §analytics, METRIC-SERVICE-SPEC.md, and TASK-P02-001.
"""

from revpilot.modules.analytics.metrics import (
    MetricType,
    MetricGrain,
    MetricEvaluationDataset,
    MetricValue,
    MetricDefinition,
    CANONICAL_METRIC_DEFINITIONS,
    MetricNotFoundError,
    InvalidMetricFilterError,
    TemporalLeakageError,
    MetricEvaluationError,
    MetricRegistry,
    CANONICAL_METRIC_REGISTRY,
)
from revpilot.modules.analytics.schemas import (
    TimeWindow,
    MetricQueryRequest,
    MetricSeriesPoint,
    MetricQueryResponse,
    MetricServiceError,
    MetricNotRegisteredError,
    InvalidDimensionFilterError,
    TemporalLeakageRejectedError,
    TenancyViolationServiceError,
    QueryTimeoutError,
)
from revpilot.modules.analytics.metric_service import (
    MetricService,
)

__all__ = [
    # Phase 01 Canonical Metric Registry Primitives
    "MetricType",
    "MetricGrain",
    "MetricEvaluationDataset",
    "MetricValue",
    "MetricDefinition",
    "CANONICAL_METRIC_DEFINITIONS",
    "MetricNotFoundError",
    "InvalidMetricFilterError",
    "TemporalLeakageError",
    "MetricEvaluationError",
    "MetricRegistry",
    "CANONICAL_METRIC_REGISTRY",
    # Phase 02 Metric Query Gateway & Schemas
    "TimeWindow",
    "MetricQueryRequest",
    "MetricSeriesPoint",
    "MetricQueryResponse",
    "MetricService",
    "MetricServiceError",
    "MetricNotRegisteredError",
    "InvalidDimensionFilterError",
    "TemporalLeakageRejectedError",
    "TenancyViolationServiceError",
    "QueryTimeoutError",
]
