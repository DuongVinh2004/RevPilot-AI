"""
RevPilot AI — Rolling Stats Baseline Model
Computes robust rolling median and Interquartile Range (IQR) bounds resistant to transient outliers.
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.1 and TASK-P02-002.
"""

from __future__ import annotations
import math
import statistics
from typing import Sequence, Any


class RollingStatsBaseline:
    """
    Deterministic rolling statistics benchmark model.
    Point estimate: Median of trailing window.
    Bounds: [Q1 - iqr_multiplier * IQR, Q3 + iqr_multiplier * IQR].
    """

    BASELINE_ID = "BASE-ROLLING-STATS-001"
    BASELINE_VERSION = "1.0.0"

    def __init__(self, window_size: int = 14, iqr_multiplier: float = 1.5) -> None:
        if not isinstance(window_size, int) or window_size <= 0:
            raise ValueError(f"window_size must be positive integer, got {window_size}")
        if iqr_multiplier < 0.0:
            raise ValueError(f"iqr_multiplier must be non-negative, got {iqr_multiplier}")
        self.window_size = window_size
        self.iqr_multiplier = float(iqr_multiplier)

    def predict(self, series: Sequence[float]) -> Any:
        """
        Produce robust rolling point estimate and IQR bounds.
        Invariant: Uses only trailing window_size elements.
        """
        from revpilot.modules.analytics.baselines import (
            BaselinePrediction,
            InsufficientHistoryError,
        )

        n = len(series)
        # Empty series corner case
        if n == 0:
            return BaselinePrediction(
                point_estimate=0.0,
                lower_bound=0.0,
                upper_bound=0.0,
                baseline_id=self.BASELINE_ID,
                baseline_version=self.BASELINE_VERSION,
            )

        # Insufficient history check
        if n < self.window_size:
            raise InsufficientHistoryError(
                f"Series length ({n}) is less than required window_size ({self.window_size})",
                details={"series_length": n, "required_window": self.window_size},
            )

        # Trailing slice
        window = [float(x) for x in series[-self.window_size:]]
        sorted_window = sorted(window)

        # Median
        med = float(statistics.median(sorted_window))

        # Quantiles Q1 (25th percentile) and Q3 (75th percentile)
        q1 = _percentile(sorted_window, 0.25)
        q3 = _percentile(sorted_window, 0.75)
        iqr = q3 - q1

        lower_bound = q1 - (self.iqr_multiplier * iqr)
        upper_bound = q3 + (self.iqr_multiplier * iqr)

        return BaselinePrediction(
            point_estimate=med,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            baseline_id=self.BASELINE_ID,
            baseline_version=self.BASELINE_VERSION,
        )


def _percentile(data: list[float], p: float) -> float:
    """Compute exact percentile using linear interpolation between closest ranks."""
    if not data:
        return 0.0
    if len(data) == 1:
        return data[0]
    k = (len(data) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    d0 = data[int(f)] * (c - k)
    d1 = data[int(c)] * (k - f)
    return d0 + d1


__all__ = ["RollingStatsBaseline"]
