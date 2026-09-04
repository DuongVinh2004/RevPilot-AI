"""
RevPilot AI — Deterministic Detection Baselines Subpackage
Provides statistical time-series baselines (Seasonal Naive, Rolling Stats, EWMA).
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.1, ML-SYSTEM-SPEC.md §1, and TASK-P02-002.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from revpilot.shared.errors import DomainError


@dataclass(frozen=True, slots=True)
class BaselinePrediction:
    """
    Authoritative prediction output from statistical time-series baselines.
    Contains point expectation and calibrated confidence/prediction interval bounds.
    """
    point_estimate: float
    lower_bound: float
    upper_bound: float
    baseline_id: str
    baseline_version: str


class InsufficientHistoryError(DomainError):
    """Raised when the input series has fewer observations than required for the baseline window (HTTP 422)."""

    def __init__(
        self,
        message: str = "Insufficient history to fit baseline",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INSUFFICIENT_HISTORY",
            message=message,
            details=details,
            retryable=False,
        )
        self.http_status = 422


from revpilot.modules.analytics.baselines.seasonal_naive import SeasonalNaiveBaseline
from revpilot.modules.analytics.baselines.rolling_stats import RollingStatsBaseline
from revpilot.modules.analytics.baselines.ewma import EwmaBaseline

__all__ = [
    "BaselinePrediction",
    "InsufficientHistoryError",
    "SeasonalNaiveBaseline",
    "RollingStatsBaseline",
    "EwmaBaseline",
]
