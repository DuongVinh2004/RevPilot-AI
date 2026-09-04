"""
RevPilot AI — STL Residual Anomaly Detector
Decomposes metric time-series into Trend, Seasonal, and Remainder components.
Flags anomalies when remainder component exceeds calibrated sigma threshold (|R_t| > k * sigma_R).
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.2, ML-SYSTEM-SPEC.md §2, and TASK-P02-003.
"""

from __future__ import annotations
import math
import statistics
from typing import Sequence, Any


class StlResidualDetector:
    """
    Deterministic Seasonal-Trend Decomposition using Residuals (STL) anomaly detector.
    Extracts cyclic patterns and flags statistically anomalous residual spikes.
    """

    DETECTOR_ID = "DET-STL-RESIDUAL-001"
    DETECTOR_VERSION = "1.0.0"

    def __init__(self, seasonal_period: int = 7, sigma_threshold: float = 3.0) -> None:
        if not isinstance(seasonal_period, int) or seasonal_period <= 0:
            raise ValueError(f"seasonal_period must be positive integer, got {seasonal_period}")
        if sigma_threshold <= 0.0:
            raise ValueError(f"sigma_threshold must be positive, got {sigma_threshold}")
        self.seasonal_period = seasonal_period
        self.sigma_threshold = float(sigma_threshold)

    def detect(self, series: Sequence[float]) -> Any:
        """
        Execute deterministic STL residual analysis on trailing time-series.
        Evaluates whether the most recent point (series[-1]) is anomalous relative to expectation.
        Guarantees zero future lookahead.
        """
        from revpilot.modules.analytics.detectors import (
            DetectionResult,
            DetectorExecutionError,
        )

        n = len(series)
        # Empty series corner case
        if n == 0:
            return DetectionResult(
                is_anomaly=False,
                anomaly_score=0.0,
                expected_value=0.0,
                expected_interval=(0.0, 0.0),
                deviation_sigma=0.0,
                detector_id=self.DETECTOR_ID,
                detector_version=self.DETECTOR_VERSION,
            )

        # Single observation corner case
        if n == 1:
            val = float(series[0])
            return DetectionResult(
                is_anomaly=False,
                anomaly_score=0.0,
                expected_value=val,
                expected_interval=(val, val),
                deviation_sigma=0.0,
                detector_id=self.DETECTOR_ID,
                detector_version=self.DETECTOR_VERSION,
            )

        target_value = float(series[-1])
        s = self.seasonal_period

        try:
            # Case A: Short series (< 2 seasonal periods)
            if n < 2 * s:
                history = [float(x) for x in series[:-1]]
                mean_val = float(statistics.mean(history))
                std_val = float(statistics.stdev(history)) if len(history) > 1 else 0.0
                effective_sigma = max(std_val, 1e-4)

                residual = target_value - mean_val
                deviation = abs(residual) / effective_sigma
                is_anomaly = deviation > self.sigma_threshold
                margin = self.sigma_threshold * effective_sigma
                score = min(1.0, round(deviation / (self.sigma_threshold * 1.5), 4))

                return DetectionResult(
                    is_anomaly=is_anomaly,
                    anomaly_score=score,
                    expected_value=round(mean_val, 4),
                    expected_interval=(round(mean_val - margin, 4), round(mean_val + margin, 4)),
                    deviation_sigma=round(deviation, 2),
                    detector_id=self.DETECTOR_ID,
                    detector_version=self.DETECTOR_VERSION,
                )

            # Case B: Robust STL Decomposition on history (series[0 : n-1])
            history = [float(x) for x in series[:-1]]
            h_len = len(history)
            trend_window_len = max(s * 3, 21)

            # 1. Robust Trend component T_i on history using rolling median of window length
            trends: list[float] = []
            for i in range(h_len):
                w_start = max(0, i - trend_window_len + 1)
                trends.append(float(statistics.median(history[w_start : i + 1])))

            # 2. Detrended series D_i = Y_i - T_i
            detrended = [history[i] - trends[i] for i in range(h_len)]

            # 3. Seasonal component S_phase[k] for k in 0..s-1
            phase_buckets: list[list[float]] = [[] for _ in range(s)]
            for i in range(h_len):
                phase_buckets[i % s].append(detrended[i])

            phase_medians = [float(statistics.median(b)) if b else 0.0 for b in phase_buckets]
            overall_seasonal_median = float(statistics.median(phase_medians))
            seasonals = [m - overall_seasonal_median for m in phase_medians]

            # 4. Historical residuals R_i = Y_i - (trends[i] + seasonals[i % s])
            residuals = [
                history[i] - (trends[i] + seasonals[i % s])
                for i in range(h_len)
            ]

            # Robust scale estimation: clean IQR outlier filtering on residuals
            sorted_res = sorted(residuals)
            half = len(sorted_res) // 2
            q1 = float(statistics.median(sorted_res[:half])) if half > 0 else sorted_res[0]
            q3 = float(statistics.median(sorted_res[-half:])) if half > 0 else sorted_res[-1]
            iqr = max(q3 - q1, 0.002)

            clean_res = [r for r in residuals if q1 - 1.5 * iqr <= r <= q3 + 1.5 * iqr]
            std_r = float(statistics.stdev(clean_res)) if len(clean_res) > 1 else 0.005
            effective_sigma = max(std_r, 0.002)

            # 5. Forecast expectation for target point (index n - 1)
            w_extrap = history[-trend_window_len:] if h_len >= trend_window_len else history
            extrapolated_trend = float(statistics.median(w_extrap))
            target_phase = (n - 1) % s
            target_seasonal = seasonals[target_phase]
            expected_val = extrapolated_trend + target_seasonal

            # 6. Target residual and deviation
            target_residual = target_value - expected_val
            deviation = abs(target_residual) / effective_sigma
            is_anomaly = deviation > self.sigma_threshold

            margin = self.sigma_threshold * effective_sigma
            score = min(1.0, round(deviation / (self.sigma_threshold * 1.5), 4))

            return DetectionResult(
                is_anomaly=is_anomaly,
                anomaly_score=score,
                expected_value=round(expected_val, 4),
                expected_interval=(round(expected_val - margin, 4), round(expected_val + margin, 4)),
                deviation_sigma=round(deviation, 2),
                detector_id=self.DETECTOR_ID,
                detector_version=self.DETECTOR_VERSION,
            )

        except Exception as exc:
            raise DetectorExecutionError(
                f"Statistical detector failed to converge: {exc}",
                details={"error": str(exc), "series_length": n},
            ) from exc


__all__ = ["StlResidualDetector"]
