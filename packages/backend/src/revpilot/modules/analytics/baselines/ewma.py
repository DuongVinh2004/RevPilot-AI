"""
RevPilot AI — Exponentially Weighted Moving Average (EWMA) Baseline Model
Tracks dynamic baseline trends with low memory footprint and calibrated residual variance bounds.
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.1 and TASK-P02-002.
"""

from __future__ import annotations
import math
from typing import Sequence, Any


class EwmaBaseline:
    """
    Deterministic Exponentially Weighted Moving Average benchmark model.
    Point estimate: S_t = alpha * Y_t + (1 - alpha) * S_{t-1}.
    Bounds: S_t +/- sigma_multiplier * sigma_residuals.
    """

    BASELINE_ID = "BASE-EWMA-001"
    BASELINE_VERSION = "1.0.0"

    def __init__(self, alpha: float = 0.2, sigma_multiplier: float = 3.0) -> None:
        if not (0.0 < alpha <= 1.0):
            raise ValueError(f"alpha must be in (0.0, 1.0], got {alpha}")
        if sigma_multiplier < 0.0:
            raise ValueError(f"sigma_multiplier must be non-negative, got {sigma_multiplier}")
        self.alpha = float(alpha)
        self.sigma_multiplier = float(sigma_multiplier)

    def predict(self, series: Sequence[float]) -> Any:
        """
        Produce EWMA smoothed expectation and calibrated variance bounds.
        Invariant: Pure forward recursive update without future leakage.
        """
        from revpilot.modules.analytics.baselines import (
            BaselinePrediction,
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

        # Single observation
        if n == 1:
            val = float(series[0])
            return BaselinePrediction(
                point_estimate=val,
                lower_bound=val,
                upper_bound=val,
                baseline_id=self.BASELINE_ID,
                baseline_version=self.BASELINE_VERSION,
            )

        # Forward recursive EWMA
        # S_0 = Y_0
        # S_t = alpha * Y_t + (1 - alpha) * S_{t-1}
        s = float(series[0])
        var = 0.0
        for i in range(1, n):
            y_i = float(series[i])
            s = (self.alpha * y_i) + ((1.0 - self.alpha) * s)
            err = y_i - s
            var = (self.alpha * (err**2)) + ((1.0 - self.alpha) * var)

        sigma = math.sqrt(var)
        margin = self.sigma_multiplier * sigma

        return BaselinePrediction(
            point_estimate=s,
            lower_bound=s - margin,
            upper_bound=s + margin,
            baseline_id=self.BASELINE_ID,
            baseline_version=self.BASELINE_VERSION,
        )


__all__ = ["EwmaBaseline"]
