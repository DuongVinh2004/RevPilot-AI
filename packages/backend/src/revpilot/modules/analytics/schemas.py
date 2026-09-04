"""
RevPilot AI — Metric Service Query Schemas & Contracts
Defines typed query contracts, time windows, series points, responses, and error hierarchy.
Conforms to METRIC-SERVICE-SPEC.md §2, §4 and TASK-P02-001.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError


# =============================================================================
# Temporal Window Contract
# =============================================================================

@dataclass(frozen=True, slots=True)
class TimeWindow:
    """
    Bounded time interval [start_time, end_time].
    Invariant: start_time <= end_time.
    """
    start_time: UtcDateTime
    end_time: UtcDateTime

    def __post_init__(self) -> None:
        if not isinstance(self.start_time, UtcDateTime):
            raise TypeError(f"start_time must be UtcDateTime, got {type(self.start_time).__name__}")
        if not isinstance(self.end_time, UtcDateTime):
            raise TypeError(f"end_time must be UtcDateTime, got {type(self.end_time).__name__}")
        if self.start_time.value > self.end_time.value:
            raise ValueError(
                f"Invalid TimeWindow: start_time ({self.start_time}) must precede or equal end_time ({self.end_time})"
            )

    @property
    def start(self) -> UtcDateTime:
        """Alias for start_time for API symmetry."""
        return self.start_time

    @property
    def end(self) -> UtcDateTime:
        """Alias for end_time for API symmetry."""
        return self.end_time

    def contains(self, dt: UtcDateTime) -> bool:
        """Return True if dt falls within [start_time, end_time] inclusive."""
        if not isinstance(dt, UtcDateTime):
            raise TypeError(f"dt must be UtcDateTime, got {type(dt).__name__}")
        return self.start_time.value <= dt.value <= self.end_time.value

    def duration_seconds(self) -> float:
        """Return total duration in seconds."""
        return (self.end_time.value - self.start_time.value).total_seconds()


# =============================================================================
# Query Request & Response Models
# =============================================================================

@dataclass(frozen=True, slots=True)
class MetricQueryRequest:
    """
    Strongly-typed metric query specification.
    Guarantees immutable parameter semantics and clean grain specification.
    """
    metric_id: str
    metric_version: str
    time_window: TimeWindow
    grain: str
    group_by_dimensions: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    as_of_time: UtcDateTime = field(default_factory=UtcDateTime.now)

    def __post_init__(self) -> None:
        if not isinstance(self.metric_id, str) or not self.metric_id.strip():
            raise ValueError("metric_id must be a non-empty string")
        if not isinstance(self.metric_version, str) or not self.metric_version.strip():
            raise ValueError("metric_version must be a non-empty string")
        if not isinstance(self.time_window, TimeWindow):
            raise TypeError(f"time_window must be TimeWindow, got {type(self.time_window).__name__}")
        if not isinstance(self.grain, str) or not self.grain.strip():
            raise ValueError("grain must be a non-empty string")
        if not isinstance(self.as_of_time, UtcDateTime):
            raise TypeError(f"as_of_time must be UtcDateTime, got {type(self.as_of_time).__name__}")


@dataclass(frozen=True, slots=True)
class MetricSeriesPoint:
    """
    Single discrete aggregate time-series slice point.
    Conforms to METRIC-SERVICE-SPEC.md §2.2.
    """
    window_start: UtcDateTime
    window_end: UtcDateTime
    dimensions: dict[str, str]
    actual_value: float
    numerator_value: float
    denominator_value: float
    sample_size: int
    is_zero_volume_sample: bool


@dataclass(frozen=True, slots=True)
class MetricQueryResponse:
    """
    Authoritative query evaluation response payload.
    Includes provenance metadata, freshness indicators, and cryptographic lineage hash.
    """
    query_id: str
    metric_id: str
    metric_name: str
    metric_version: str
    tenant_id: TenantId
    grain: str
    as_of_time: UtcDateTime
    freshness_state: str
    data_quality_state: str
    lineage_snapshot_hash: str
    series: list[MetricSeriesPoint]


# =============================================================================
# Error Contract Hierarchy
# =============================================================================

class MetricServiceError(DomainError):
    """Base exception for all metric service errors."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=retryable)
        self.http_status = http_status


class MetricNotRegisteredError(MetricServiceError):
    """Raised when metric identifier cannot be found in MetricRegistry (HTTP 404)."""

    def __init__(self, message: str = "Unknown metric identifier", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="METRIC_NOT_REGISTERED",
            message=message,
            http_status=404,
            details=details,
            retryable=False,
        )


class InvalidDimensionFilterError(MetricServiceError):
    """Raised when query requests an unapproved dimension or filter (HTTP 400)."""

    def __init__(self, message: str = "Dimension not permitted for metric", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="INVALID_DIMENSION_FILTER",
            message=message,
            http_status=400,
            details=details,
            retryable=False,
        )


class TemporalLeakageRejectedError(MetricServiceError):
    """Raised when as_of_time is in the future relative to server clock (HTTP 422)."""

    def __init__(self, message: str = "Future as-of timestamp rejected", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="TEMPORAL_LEAKAGE_REJECTED",
            message=message,
            http_status=422,
            details=details,
            retryable=False,
        )


class TenancyViolationServiceError(MetricServiceError):
    """Raised when tenant context is invalid, missing, or mismatched (HTTP 403)."""

    def __init__(self, message: str = "Cross-tenant access denied", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="TENANCY_VIOLATION",
            message=message,
            http_status=403,
            details=details,
            retryable=False,
        )


class QueryTimeoutError(MetricServiceError):
    """Raised when query execution exceeds deadline (HTTP 504)."""

    def __init__(self, message: str = "Metric computation deadline exceeded", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="QUERY_TIMEOUT",
            message=message,
            http_status=504,
            details=details,
            retryable=True,
        )


__all__ = [
    "TimeWindow",
    "MetricQueryRequest",
    "MetricSeriesPoint",
    "MetricQueryResponse",
    "MetricServiceError",
    "MetricNotRegisteredError",
    "InvalidDimensionFilterError",
    "TemporalLeakageRejectedError",
    "TenancyViolationServiceError",
    "QueryTimeoutError",
]
