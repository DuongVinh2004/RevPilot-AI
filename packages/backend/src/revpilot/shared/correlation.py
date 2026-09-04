"""
RevPilot AI — Distributed Correlation Context
Provides immutable trace, correlation, and causation identifiers across API, Temporal workflows, and events.
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass


def _generate_hex_id(length: int = 16) -> str:
    """Generate hex identifier for tracing."""
    return uuid.uuid4().hex[:length]


@dataclass(frozen=True, slots=True)
class CorrelationContext:
    """
    Immutable distributed tracing context.
    Conforms to OpenTelemetry trace and W3C correlation standards.
    """
    trace_id: str
    span_id: str
    correlation_id: str
    causation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.trace_id or not isinstance(self.trace_id, str):
            raise ValueError("trace_id must be a non-empty string")
        if not self.span_id or not isinstance(self.span_id, str):
            raise ValueError("span_id must be a non-empty string")
        if not self.correlation_id or not isinstance(self.correlation_id, str):
            raise ValueError("correlation_id must be a non-empty string")

    @classmethod
    def create_root(cls, correlation_id: str | None = None) -> CorrelationContext:
        """Create a new root correlation context with unique trace and span IDs."""
        trace = _generate_hex_id(32)
        span = _generate_hex_id(16)
        corr = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        return cls(trace_id=trace, span_id=span, correlation_id=corr, causation_id=None)

    def create_child(self, new_span_id: str | None = None) -> CorrelationContext:
        """
        Derive child context within same trace.
        The current span becomes the causation_id for the child.
        """
        child_span = new_span_id or _generate_hex_id(16)
        return CorrelationContext(
            trace_id=self.trace_id,
            span_id=child_span,
            correlation_id=self.correlation_id,
            causation_id=self.span_id,
        )

    def to_dict(self) -> dict[str, str]:
        """Serialize to string dictionary suitable for headers or telemetry attributes."""
        res = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "correlation_id": self.correlation_id,
        }
        if self.causation_id:
            res["causation_id"] = self.causation_id
        return res

    def __repr__(self) -> str:
        return (
            f"CorrelationContext(trace={self.trace_id!r}, span={self.span_id!r}, "
            f"corr={self.correlation_id!r}, cause={self.causation_id!r})"
        )
