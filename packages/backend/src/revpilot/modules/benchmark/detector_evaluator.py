"""
RevPilot AI — Detector Benchmark and Rolling Time-Split Evaluator
Simulates daily inference steps over time horizons enforcing strict as-of watermarking,
and scores detection accuracy against air-gapped ground-truth incident annotations.
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §3, §4 and TASK-P02-003.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
import os
from typing import Sequence, Any

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError
from revpilot.modules.analytics.detectors.stl import StlResidualDetector
from revpilot.modules.benchmark.ground_truth import (
    EvaluationGroundTruthStore,
    EvaluatorAuthToken,
    GroundTruthIncident,
)


@dataclass(frozen=True, slots=True)
class DetectorBenchmarkMetrics:
    """
    Standard quantitative benchmark evaluation metrics.
    Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §3 and TASK-P02-003.
    """
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    lead_time_hours: float
    evaluated_at: UtcDateTime


class EvalGroundTruthMissingError(DomainError):
    """Raised when the specified ground truth fixture file cannot be located (HTTP 404)."""

    def __init__(
        self,
        message: str = "Benchmark ground-truth file missing",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="EVAL_GROUND_TRUTH_MISSING",
            message=message,
            details=details,
            retryable=False,
        )
        self.http_status = 404


class RollingTimeSplitEvaluator:
    """
    Offline benchmark harness executing strict rolling time-split backtesting.
    Enforces INV-DATA-001 (zero future lookahead) and INV-AI-001 (air-gapped ground truth access).
    """

    def run_backtest(
        self,
        tenant_id: TenantId,
        metric_id: str,
        detector: StlResidualDetector,
        start_day: int,
        end_day: int,
        ground_truth_path: str,
        series_data: Sequence[float] | None = None,
        base_date: UtcDateTime | None = None,
    ) -> DetectorBenchmarkMetrics:
        """
        Execute rolling day-by-day evaluation across the [start_day, end_day] horizon.
        At each day d, detector receives only series[:d].
        Ground truth is accessed strictly offline via EvaluatorAuthToken.
        """
        # 1. Load ground truth using air-gapped credentials
        if not os.path.exists(ground_truth_path):
            raise EvalGroundTruthMissingError(
                f"Benchmark ground-truth file missing at: {ground_truth_path}",
                details={"path": ground_truth_path},
            )

        token = EvaluatorAuthToken(principal_id="evaluator_harness", role="revpilot_evaluator")
        gt_res = EvaluationGroundTruthStore.load_ground_truth_for_eval(ground_truth_path, token)
        if gt_res.is_failure:
            raise EvalGroundTruthMissingError(
                f"Failed to load ground truth: {gt_res.unwrap_error()}",
                details={"error": str(gt_res.unwrap_error())},
            )
        incident: GroundTruthIncident = gt_res.unwrap()

        # 2. Setup simulation parameters
        start_dt = base_date or UtcDateTime.from_iso("2026-01-01T00:00:00.000000Z")
        series = list(series_data) if series_data is not None else []

        tp = 0
        fp = 0
        fn = 0
        tn = 0
        first_alarm_time: UtcDateTime | None = None

        # 3. Step-by-step rolling evaluation
        for day in range(start_day, end_day + 1):
            day_dt = UtcDateTime.from_datetime(start_dt.value + timedelta(days=day - 1))
            day_end_dt = UtcDateTime.from_datetime(start_dt.value + timedelta(days=day))

            # Anti-leakage: slice series strictly up to current day index
            visible_series = series[:day]
            det_res = detector.detect(visible_series)

            # Determine if current day falls within incident window for the evaluated tenant
            is_incident_active = False
            if incident.tenant_id == tenant_id:
                # Active if day overlaps with causal disruption window
                if day_dt.value <= incident.causal_end_time.value and day_end_dt.value >= incident.causal_start_time.value:
                    is_incident_active = True

            # Score classification
            if is_incident_active:
                if det_res.is_anomaly:
                    tp += 1
                    if first_alarm_time is None:
                        first_alarm_time = day_dt
                else:
                    fn += 1
            else:
                if det_res.is_anomaly:
                    fp += 1
                else:
                    tn += 1

        # 4. Compute benchmark evaluation metrics
        precision = float(tp) / float(tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
        recall = float(tp) / float(tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2.0 * precision * recall) / (precision + recall) if (precision + recall) > 0.0 else 0.0
        fpr = float(fp) / float(fp + tn) if (fp + tn) > 0 else 0.0

        if first_alarm_time is not None:
            diff_sec = (first_alarm_time.value - incident.causal_start_time.value).total_seconds()
            lead_time_hours = max(0.0, round(diff_sec / 3600.0, 2))
        else:
            lead_time_hours = 0.0 if (tp + fn) == 0 else 999.0

        return DetectorBenchmarkMetrics(
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            false_positive_rate=round(fpr, 4),
            lead_time_hours=lead_time_hours,
            evaluated_at=UtcDateTime.now(),
        )


__all__ = [
    "DetectorBenchmarkMetrics",
    "EvalGroundTruthMissingError",
    "RollingTimeSplitEvaluator",
]
