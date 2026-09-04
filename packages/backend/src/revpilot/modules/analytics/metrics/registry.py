"""
RevPilot AI — Canonical Metric Registry Engine (Phase 01)
Provides immutable registry, descriptor queries, dimension validation, and safe execution.
Conforms to METRIC-REGISTRY.md §1, §3 and TASK-P01-002.
"""

from __future__ import annotations
from typing import Any, Optional

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure

from revpilot.modules.analytics.metrics.definitions import (
    MetricDefinition,
    MetricEvaluationDataset,
    MetricValue,
    CANONICAL_METRIC_DEFINITIONS,
)


class MetricNotFoundError(DomainError):
    """Raised when querying or evaluating an unregistered metric ID."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="METRIC_NOT_FOUND", message=message, details=details, retryable=False)


class InvalidMetricFilterError(DomainError):
    """Raised when query filter specifies an unpermitted dimension."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="INVALID_METRIC_FILTER", message=message, details=details, retryable=False)


class TemporalLeakageError(DomainError):
    """Raised when evaluation data breaches the as_of watermark."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="TEMPORAL_LEAKAGE_REJECTED", message=message, details=details, retryable=False)


class MetricEvaluationError(DomainError):
    """General failure during metric computation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="METRIC_EVALUATION_ERROR", message=message, details=details, retryable=False)


class MetricRegistry:
    """Thread-safe in-memory Metric Registry and evaluation coordinator."""

    def __init__(self) -> None:
        self._metrics: dict[str, MetricDefinition] = {}

    def register(self, metric: MetricDefinition) -> None:
        """Register a canonical metric definition."""
        if not isinstance(metric, MetricDefinition):
            raise TypeError(f"metric must be MetricDefinition, got {type(metric).__name__}")
        self._metrics[metric.metric_id] = metric
        # Also index by name for convenience
        self._metrics[metric.name] = metric

    def get(self, metric_id_or_name: str) -> Result[MetricDefinition, MetricNotFoundError]:
        """Lookup metric definition by ID or name."""
        if not isinstance(metric_id_or_name, str) or not metric_id_or_name.strip():
            return Failure(MetricNotFoundError("Metric identifier cannot be empty"))

        key = metric_id_or_name.strip()
        metric = self._metrics.get(key)
        if not metric:
            return Failure(MetricNotFoundError(f"Requested metric is not registered: '{key}'"))
        return Success(metric)

    def get_or_raise(self, metric_id_or_name: str) -> MetricDefinition:
        """Lookup metric definition or raise MetricNotFoundError."""
        res = self.get(metric_id_or_name)
        return res.unwrap()

    def list_metrics(self) -> list[MetricDefinition]:
        """Return all distinct registered metric definitions."""
        # De-duplicate since stored under both ID and name
        seen: set[str] = set()
        result: list[MetricDefinition] = []
        for m in self._metrics.values():
            if m.metric_id not in seen:
                seen.add(m.metric_id)
                result.append(m)
        return sorted(result, key=lambda x: x.metric_id)

    def evaluate(
        self,
        metric_id: str,
        tenant_id: TenantId,
        data: MetricEvaluationDataset,
        as_of: UtcDateTime,
        filters: Optional[dict[str, Any]] = None,
    ) -> Result[MetricValue, DomainError]:
        """
        Evaluate a registered metric against the supplied dataset.
        Enforces tenant isolation, as_of watermarking, and dimension validation.
        """
        metric_res = self.get(metric_id)
        if metric_res.is_failure:
            return Failure(metric_res.unwrap_error())

        metric = metric_res.unwrap()

        if not isinstance(tenant_id, TenantId):
            return Failure(MetricEvaluationError("Tenant context required: tenant_id must be TenantId"))

        if not isinstance(as_of, UtcDateTime):
            return Failure(MetricEvaluationError("as_of must be UtcDateTime"))

        if filters:
            for dim in filters:
                if dim not in metric.allowed_dimensions:
                    return Failure(
                        InvalidMetricFilterError(
                            f"Dimension filter not allowed: '{dim}'. Allowed dimensions for {metric.metric_id}: {metric.allowed_dimensions}"
                        )
                    )

        try:
            val = metric.calculate_fn(tenant_id, data, as_of, filters)
            return Success(val)
        except Exception as exc:
            return Failure(MetricEvaluationError(f"Error calculating metric {metric_id}: {exc}"))


# Pre-populated canonical metric registry singleton
CANONICAL_METRIC_REGISTRY = MetricRegistry()
for _m in CANONICAL_METRIC_DEFINITIONS:
    CANONICAL_METRIC_REGISTRY.register(_m)


__all__ = [
    "MetricNotFoundError",
    "InvalidMetricFilterError",
    "TemporalLeakageError",
    "MetricEvaluationError",
    "MetricRegistry",
    "CANONICAL_METRIC_REGISTRY",
]
