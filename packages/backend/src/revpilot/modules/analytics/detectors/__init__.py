"""
RevPilot AI — Statistical Anomaly Detectors Subpackage
Provides deterministic statistical anomaly detectors (STL Residual, Change-Point).
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.2, ML-SYSTEM-SPEC.md §2, and TASK-P02-003.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from revpilot.shared.errors import DomainError


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """
    Authoritative detection result emitted by statistical anomaly detectors.
    Conforms to ML-SYSTEM-SPEC.md §3.2 and TASK-P02-003.
    """
    is_anomaly: bool
    anomaly_score: float
    expected_value: float
    expected_interval: tuple[float, float]
    deviation_sigma: float
    detector_id: str
    detector_version: str


class DetectorExecutionError(DomainError):
    """Raised when statistical detector encounters singular decomposition or convergence failure (HTTP 500)."""

    def __init__(
        self,
        message: str = "Statistical detector failed to converge",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="DETECTOR_EXECUTION_FAILED",
            message=message,
            details=details,
            retryable=False,
        )
        self.http_status = 500


from revpilot.modules.analytics.detectors.stl import StlResidualDetector

__all__ = [
    "DetectionResult",
    "DetectorExecutionError",
    "StlResidualDetector",
]
