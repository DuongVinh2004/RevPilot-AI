"""
RevPilot AI — Seasonal Naive Baseline Model
Predicts historical expectation based on seasonal lag (Y_t = Y_{t-s}) with calibrated prediction intervals.
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.1 and TASK-P02-002.
"""

from __future__ import annotations
import math
from typing import Sequence

# Normal distribution critical value approximation for two-tailed 1 - alpha/2
_Z_CRITICAL_95 = 1.959963984540054  # alpha = 0.05 (95% confidence)


class SeasonalNaiveBaseline:
    """
    Deterministic seasonal naive benchmark model.
    Forecasts Y_t = Y_{t - season_length} using empirical residual standard error for prediction intervals.
    """

    BASELINE_ID = "BASE-SEASONAL-NAIVE-001"
    BASELINE_VERSION = "1.0.0"

    def __init__(self, season_length: int = 7, alpha: float = 0.05) -> None:
        if not isinstance(season_length, int) or season_length <= 0:
            raise ValueError(f"season_length must be positive integer, got {season_length}")
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"alpha must be between 0.0 and 1.0 exclusive, got {alpha}")
        self.season_length = season_length
        self.alpha = alpha

    def predict(self, series: Sequence[float]) -> Any:
        """
        Produce deterministic point forecast and prediction interval bounds.
        Invariant: Uses only historical values up to the end of the series.
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

        # Insufficient history for seasonal lag
        if n < self.season_length:
            raise InsufficientHistoryError(
                f"Series length ({n}) is less than required season_length ({self.season_length})",
                details={"series_length": n, "required_window": self.season_length},
            )

        # Point estimate: Y_{t - season_length}
        point_est = float(series[-self.season_length])

        # Compute empirical residual standard deviation over available historical seasonal cycles
        # Residual e_i = Y_i - Y_{i - season_length} for i in range(season_length, n)
        if n > self.season_length:
            squared_diffs = [
                (float(series[i]) - float(series[i - self.season_length])) ** 2
                for i in range(self.season_length, n)
            ]
            variance = sum(squared_diffs) / len(squared_diffs)
            std_err = math.sqrt(variance)
        else:
            std_err = 0.0

        # Margin for two-tailed (1 - alpha) interval
        # Use exact z-score approximation
        z = _compute_z_score(self.alpha)
        margin = z * std_err

        return BaselinePrediction(
            point_estimate=point_est,
            lower_bound=point_est - margin,
            upper_bound=point_est + margin,
            baseline_id=self.BASELINE_ID,
            baseline_version=self.BASELINE_VERSION,
        )


def _compute_z_score(alpha: float) -> float:
    """Compute two-tailed normal critical value z_{1 - alpha/2}."""
    if abs(alpha - 0.05) < 1e-4:
        return _Z_CRITICAL_95
    if abs(alpha - 0.01) < 1e-4:
        return 2.5758293035489004
    if abs(alpha - 0.10) < 1e-4:
        return 1.6448536269514722
    # Rational approximation of probit function (Abramowitz & Stegun 26.2.23)
    p = 1.0 - (alpha / 2.0)
    t = math.sqrt(-2.0 * math.log(1.0 - p))
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308
    return t - ((c0 + c1 * t + c2 * (t**2)) / (1.0 + d1 * t + d2 * (t**2) + d3 * (t**3)))


__all__ = ["SeasonalNaiveBaseline"]
