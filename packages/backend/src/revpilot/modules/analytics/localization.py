"""
RevPilot AI — Anomaly Localization and Dimensional Drill-Down Engine (Phase 02)
Isolates which dimensional slices contribute disproportionately to metric anomalies,
enforces minimum sample sizes, applies Benjamini-Hochberg FDR control, and produces
strictly associative (non-causal) diagnostic summaries.
Conforms to ANOMALY-LOCALIZATION-SPEC.md §1–§4, METRIC-REGISTRY.md, and TASK-P02-004.
"""

from __future__ import annotations
import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence
from uuid import uuid4

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure

from revpilot.modules.analytics.schemas import (
    TimeWindow,
    MetricQueryRequest,
    MetricSeriesPoint,
    MetricQueryResponse,
    MetricServiceError,
)
from revpilot.modules.analytics.metrics.definitions import (
    MetricType,
    MetricEvaluationDataset,
)
from revpilot.modules.analytics.metrics.registry import (
    MetricRegistry,
    CANONICAL_METRIC_REGISTRY,
)
from revpilot.modules.analytics.metric_service import MetricService


# =============================================================================
# Error Contract Hierarchy
# =============================================================================

class LocalizationError(DomainError):
    """Base domain exception for anomaly localization operations."""

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


class UnsupportedDimensionError(LocalizationError):
    """Raised when dimension is not permitted or registered for the metric (HTTP 400)."""

    def __init__(
        self,
        message: str = "Dimension not supported for drill-down",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="UNSUPPORTED_DIMENSION",
            message=message,
            http_status=400,
            details=details,
            retryable=False,
        )


class InsufficientDataForLocalizationError(LocalizationError):
    """Raised when all slices have insufficient sample size (< 30 observations) (HTTP 422)."""

    def __init__(
        self,
        message: str = "Insufficient sample volume to localize",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INSUFFICIENT_DATA_FOR_LOCALIZATION",
            message=message,
            http_status=422,
            details=details,
            retryable=False,
        )


# =============================================================================
# Domain Contracts & Schemas
# =============================================================================

@dataclass(frozen=True, slots=True)
class AnomalyRecord:
    """
    Validated tenant-isolated anomaly state entity.
    Conforms to ANOMALY-DOMAIN-SPEC.md §2.1 and TASK-P02-004.
    """
    id: str
    tenant_id: TenantId
    metric_id: str
    observation_window_start: UtcDateTime
    observation_window_end: UtcDateTime
    as_of_time: UtcDateTime
    actual_value: float
    expected_value: float
    anomaly_type: str = "CANCELLATION"
    metric_version: str = "1.0.0"
    detector_id: str = "DET-STL-RESIDUAL-001"
    detector_version: str = "1.0.0"
    baseline_id: str = "BASE-SEASONAL-NAIVE-001"
    baseline_version: str = "1.0.0"
    comparison_window_start: Optional[UtcDateTime] = None
    comparison_window_end: Optional[UtcDateTime] = None
    expected_interval_lower: float = 0.0
    expected_interval_upper: float = 0.0
    anomaly_score: float = 1.0
    severity: str = "CRITICAL"
    affected_scope: dict[str, str] = field(default_factory=dict)
    data_freshness: str = "FRESH"
    data_quality_state: str = "PASSED"
    confidence: float = 1.0
    status: str = "DETECTED"
    created_at: UtcDateTime = field(default_factory=UtcDateTime.now)


@dataclass(frozen=True, slots=True)
class SegmentContribution:
    """
    Dimensional slice contribution metrics and hypothesis test outcome.
    Conforms to ANOMALY-LOCALIZATION-SPEC.md §3 and TASK-P02-004.
    """
    rank: int
    segment_value: str
    actual_value: float
    baseline_expected_value: float
    relative_lift: float
    sample_size: int
    excess_volume: float
    contribution_pct: float
    p_value: float
    fdr_rejected: bool

    @property
    def statistical_significance_pvalue(self) -> float:
        """Alias for p_value conforming to ANOMALY-LOCALIZATION-SPEC.md §3 schema."""
        return self.p_value


@dataclass(frozen=True, slots=True)
class AnomalyLocalizationResult:
    """
    Structured outcome of multi-dimensional anomaly localization.
    Conforms to ANOMALY-LOCALIZATION-SPEC.md §3 and TASK-P02-004.
    """
    localization_id: str
    anomaly_id: str
    tenant_id: TenantId
    dimension: str
    top_contributing_segments: list[SegmentContribution]
    suppressed_segments_count: int
    association_summary: str
    diagnostic_status: str
    metric_id: str = ""
    evaluated_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    as_of_time: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_coverage_pct: float = 100.0
    secondary_dimension: Optional[str] = None
    secondary_localization: Optional[AnomalyLocalizationResult] = None
    lineage_trace_id: str = ""


# =============================================================================
# Anomaly Localizer Engine
# =============================================================================

class AnomalyLocalizer:
    """
    Multi-dimensional anomaly localization and drill-down engine.
    Ranks top contributing slices, enforces sample-size thresholds (d_k >= 30),
    applies Benjamini-Hochberg FDR control, and outputs associative diagnostic summaries.
    Conforms to INV-AI-001 (Association, Not Causation) and INV-TEN-001.
    """

    ASSOCIATIVE_DISCLAIMER = (
        "This reflects an observed association; causal investigation is required to establish underlying root causes."
    )

    def __init__(
        self,
        metric_service: MetricService | None = None,
        registry: MetricRegistry | None = None,
        dataset: MetricEvaluationDataset | None = None,
    ) -> None:
        self._registry = registry or CANONICAL_METRIC_REGISTRY
        self._metric_service = metric_service or MetricService(dataset=dataset, registry=self._registry)
        if dataset is not None and metric_service is not None:
            self._metric_service.set_dataset(dataset)

    def set_dataset(self, dataset: MetricEvaluationDataset) -> None:
        """Update the underlying dataset in the query service."""
        self._metric_service.set_dataset(dataset)

    def localize(
        self,
        anomaly: AnomalyRecord,
        dimension: str,
        secondary_dimension: Optional[str] = None,
        tenant_context: TenantContext | None = None,
        dataset: MetricEvaluationDataset | None = None,
        _depth: int = 1,
    ) -> Result[AnomalyLocalizationResult, LocalizationError]:
        """
        Execute dimensional drill-down on an anomaly record within tenant boundaries.
        Supports conditional two-level drill-down stopped at depth = 2.
        """
        # 1. Tenancy validation (INV-TEN-001)
        if not isinstance(tenant_context, TenantContext):
            return Failure(
                LocalizationError(
                    code="TENANCY_VIOLATION",
                    message="Valid TenantContext required for anomaly localization",
                    http_status=403,
                )
            )

        if tenant_context.tenant_id != anomaly.tenant_id:
            return Failure(
                LocalizationError(
                    code="TENANCY_VIOLATION",
                    message=(
                        f"Cross-tenant localization denied: TenantContext tenant '{tenant_context.tenant_id}' "
                        f"does not match anomaly tenant '{anomaly.tenant_id}'"
                    ),
                    http_status=403,
                    details={
                        "context_tenant_id": str(tenant_context.tenant_id),
                        "anomaly_tenant_id": str(anomaly.tenant_id),
                    },
                )
            )

        # 2. Metric definition and dimension allowlist check (FR-INV-004)
        metric_res = self._registry.get(anomaly.metric_id)
        if metric_res.is_failure:
            return Failure(
                LocalizationError(
                    code="METRIC_NOT_REGISTERED",
                    message=f"Metric '{anomaly.metric_id}' is not registered in canonical registry",
                    http_status=404,
                    details={"metric_id": anomaly.metric_id},
                )
            )
        metric_def = metric_res.unwrap()

        if dimension not in metric_def.allowed_dimensions:
            return Failure(
                UnsupportedDimensionError(
                    f"Dimension '{dimension}' not supported for drill-down on metric '{anomaly.metric_id}'",
                    details={
                        "dimension": dimension,
                        "metric_id": anomaly.metric_id,
                        "allowed_dimensions": metric_def.allowed_dimensions,
                    },
                )
            )

        if secondary_dimension is not None:
            if secondary_dimension not in metric_def.allowed_dimensions:
                return Failure(
                    UnsupportedDimensionError(
                        f"Secondary dimension '{secondary_dimension}' not supported for drill-down on metric '{anomaly.metric_id}'",
                        details={
                            "secondary_dimension": secondary_dimension,
                            "metric_id": anomaly.metric_id,
                            "allowed_dimensions": metric_def.allowed_dimensions,
                        },
                    )
                )
            if secondary_dimension == dimension:
                return Failure(
                    UnsupportedDimensionError(
                        f"Secondary dimension '{secondary_dimension}' cannot be identical to primary dimension '{dimension}'",
                        details={
                            "dimension": dimension,
                            "secondary_dimension": secondary_dimension,
                        },
                    )
                )

        # 3. Query observation window metric slices
        obs_window = TimeWindow(anomaly.observation_window_start, anomaly.observation_window_end)
        query_req = MetricQueryRequest(
            metric_id=anomaly.metric_id,
            metric_version=anomaly.metric_version,
            time_window=obs_window,
            grain="AS_OF_SNAPSHOT",
            group_by_dimensions=[dimension],
            filters=dict(anomaly.affected_scope),
            as_of_time=anomaly.as_of_time,
        )
        obs_res = self._metric_service.query(query_req, tenant_context, dataset=dataset)
        if obs_res.is_failure:
            err = obs_res.unwrap_error()
            return Failure(
                LocalizationError(
                    code=err.code,
                    message=err.message,
                    http_status=getattr(err, "http_status", 400),
                    details=err.details,
                )
            )
        obs_resp = obs_res.unwrap()

        # 4. Query baseline rates if comparison window is specified
        baseline_rates: dict[str, float] = {}
        if anomaly.comparison_window_start and anomaly.comparison_window_end:
            comp_window = TimeWindow(anomaly.comparison_window_start, anomaly.comparison_window_end)
            comp_req = MetricQueryRequest(
                metric_id=anomaly.metric_id,
                metric_version=anomaly.metric_version,
                time_window=comp_window,
                grain="AS_OF_SNAPSHOT",
                group_by_dimensions=[dimension],
                filters=dict(anomaly.affected_scope),
                as_of_time=anomaly.comparison_window_end,
            )
            comp_res = self._metric_service.query(comp_req, tenant_context, dataset=dataset)
            if comp_res.is_success:
                comp_resp = comp_res.unwrap()
                for pt in comp_resp.series:
                    seg_k = pt.dimensions.get(dimension)
                    if seg_k and not pt.is_zero_volume_sample:
                        baseline_rates[seg_k] = pt.actual_value

        # 5. Evaluate slices against sample size thresholds
        # Ratio metrics: minimum denominator d_k >= 30
        # Volume metrics: minimum total order count d_k >= 10
        min_sample_size = 30 if metric_def.metric_type == MetricType.RATIO else 10

        suppressed_count = 0
        raw_candidates: list[dict[str, Any]] = []

        for pt in obs_resp.series:
            seg_val = pt.dimensions.get(dimension, "UNKNOWN")
            if pt.is_zero_volume_sample or seg_val == "UNKNOWN_OR_UNSPECIFIED":
                continue

            sample_size = pt.sample_size
            if sample_size < min_sample_size:
                suppressed_count += 1
                continue

            actual_val = pt.actual_value
            base_exp_val = baseline_rates.get(seg_val, anomaly.expected_value)
            rel_lift = round(actual_val / base_exp_val, 2) if base_exp_val > 0.0 else 1.0

            # Excess volume: Delta_k = max(0.0, n_k - (d_k * baseline_rate))
            if metric_def.metric_type == MetricType.RATIO:
                n_k = pt.numerator_value
                d_k = float(sample_size)
                excess = max(0.0, n_k - (d_k * base_exp_val))
            else:
                excess = max(0.0, actual_val - base_exp_val)

            p_val = self._compute_p_value(
                actual_val=actual_val,
                expected_val=base_exp_val,
                sample_size=sample_size,
                metric_type=metric_def.metric_type,
            )

            raw_candidates.append({
                "segment_value": seg_val,
                "actual_value": round(actual_val, 4),
                "baseline_expected_value": round(base_exp_val, 4),
                "relative_lift": rel_lift,
                "sample_size": sample_size,
                "excess_volume": round(excess, 4),
                "p_value": p_val,
            })

        # Fail closed if all slices have insufficient observations
        if not raw_candidates:
            return Failure(
                InsufficientDataForLocalizationError(
                    "Insufficient sample volume to localize",
                    details={
                        "dimension": dimension,
                        "metric_id": anomaly.metric_id,
                        "suppressed_segments_count": suppressed_count,
                        "min_sample_size": min_sample_size,
                    },
                )
            )

        # 6. Apply Benjamini-Hochberg FDR control at alpha = 0.05
        candidates_by_p = sorted(enumerate(raw_candidates), key=lambda x: x[1]["p_value"])
        m_count = len(candidates_by_p)
        alpha = 0.05
        max_fdr_rank = -1
        for rank_1_based, (_, cand) in enumerate(candidates_by_p, start=1):
            fdr_thresh = (rank_1_based / m_count) * alpha
            if cand["p_value"] <= fdr_thresh:
                max_fdr_rank = rank_1_based

        for rank_1_based, (_, cand) in enumerate(candidates_by_p, start=1):
            cand["fdr_rejected"] = (rank_1_based <= max_fdr_rank)

        # 7. Compute percentage contribution: Delta_k / sum(Delta_j) * 100%
        total_excess = sum(c["excess_volume"] for c in raw_candidates)
        for c in raw_candidates:
            if total_excess > 0.0:
                c["contribution_pct"] = round((c["excess_volume"] / total_excess) * 100.0, 1)
            else:
                c["contribution_pct"] = 0.0

        # 8. Sort and rank top contributing segments
        sorted_candidates = sorted(
            raw_candidates,
            key=lambda x: (x["excess_volume"], x["relative_lift"]),
            reverse=True,
        )

        top_contributing: list[SegmentContribution] = []
        for rank, seg in enumerate(sorted_candidates, start=1):
            top_contributing.append(
                SegmentContribution(
                    rank=rank,
                    segment_value=seg["segment_value"],
                    actual_value=seg["actual_value"],
                    baseline_expected_value=seg["baseline_expected_value"],
                    relative_lift=seg["relative_lift"],
                    sample_size=seg["sample_size"],
                    excess_volume=round(seg["excess_volume"], 1),
                    contribution_pct=seg["contribution_pct"],
                    p_value=seg["p_value"],
                    fdr_rejected=seg["fdr_rejected"],
                )
            )

        # 9. Two-level hierarchical drill-down restricted to top segment (stop rule: depth = 2)
        secondary_result: Optional[AnomalyLocalizationResult] = None
        if secondary_dimension is not None and _depth < 2 and top_contributing:
            leading_seg = top_contributing[0]
            child_scope = {**anomaly.affected_scope, dimension: leading_seg.segment_value}
            child_anomaly = AnomalyRecord(
                id=anomaly.id,
                tenant_id=anomaly.tenant_id,
                metric_id=anomaly.metric_id,
                observation_window_start=anomaly.observation_window_start,
                observation_window_end=anomaly.observation_window_end,
                as_of_time=anomaly.as_of_time,
                actual_value=leading_seg.actual_value,
                expected_value=leading_seg.baseline_expected_value,
                anomaly_type=anomaly.anomaly_type,
                metric_version=anomaly.metric_version,
                detector_id=anomaly.detector_id,
                detector_version=anomaly.detector_version,
                baseline_id=anomaly.baseline_id,
                baseline_version=anomaly.baseline_version,
                comparison_window_start=anomaly.comparison_window_start,
                comparison_window_end=anomaly.comparison_window_end,
                expected_interval_lower=anomaly.expected_interval_lower,
                expected_interval_upper=anomaly.expected_interval_upper,
                anomaly_score=anomaly.anomaly_score,
                severity=anomaly.severity,
                affected_scope=child_scope,
                data_freshness=anomaly.data_freshness,
                data_quality_state=anomaly.data_quality_state,
                confidence=anomaly.confidence,
                status=anomaly.status,
            )
            child_res = self.localize(
                anomaly=child_anomaly,
                dimension=secondary_dimension,
                secondary_dimension=None,
                tenant_context=tenant_context,
                dataset=dataset,
                _depth=_depth + 1,
            )
            if child_res.is_success:
                secondary_result = child_res.unwrap()

        # 10. Associative diagnosis summary (INV-AI-001, AC-P02-004-04)
        metric_label = metric_def.name.replace("_", " ").title()
        if top_contributing and top_contributing[0].contribution_pct > 0.0:
            top_seg = top_contributing[0]
            if secondary_result and secondary_result.top_contributing_segments:
                child_top = secondary_result.top_contributing_segments[0]
                summary = (
                    f"{metric_label} spike is concentrated in {top_seg.segment_value}, "
                    f"accounting for {top_seg.contribution_pct:.1f}% of excess volume, "
                    f"with secondary concentration in {child_top.segment_value} "
                    f"({child_top.contribution_pct:.1f}% of carrier excess volume). {self.ASSOCIATIVE_DISCLAIMER}"
                )
            else:
                summary = (
                    f"{metric_label} spike is concentrated in {top_seg.segment_value}, "
                    f"accounting for {top_seg.contribution_pct:.1f}% of excess cancelled orders. "
                    f"{self.ASSOCIATIVE_DISCLAIMER}"
                )
        else:
            summary = (
                f"No significant concentration detected across dimension '{dimension}'. "
                f"{self.ASSOCIATIVE_DISCLAIMER}"
            )

        # 11. Diagnostic status classification
        if top_contributing and top_contributing[0].fdr_rejected and top_contributing[0].contribution_pct >= 50.0:
            diagnostic_status = "ACTIONABLE_FOR_INVESTIGATION"
        elif top_contributing:
            diagnostic_status = "OBSERVED_VARIATION"
        else:
            diagnostic_status = "NO_CONCENTRATION"

        # 12. Construct response
        loc_id = f"loc_{uuid4().hex[:16]}"
        lineage_hash = hashlib.sha256(
            f"{anomaly.id}:{dimension}:{secondary_dimension}:{loc_id}".encode("utf-8")
        ).hexdigest()

        result = AnomalyLocalizationResult(
            localization_id=loc_id,
            anomaly_id=anomaly.id,
            tenant_id=anomaly.tenant_id,
            dimension=dimension,
            top_contributing_segments=top_contributing,
            suppressed_segments_count=suppressed_count,
            association_summary=summary,
            diagnostic_status=diagnostic_status,
            metric_id=anomaly.metric_id,
            as_of_time=anomaly.as_of_time,
            secondary_dimension=secondary_dimension,
            secondary_localization=secondary_result,
            lineage_trace_id=f"lin_{lineage_hash[:16]}",
        )

        return Success(result)

    @staticmethod
    def _compute_p_value(
        actual_val: float,
        expected_val: float,
        sample_size: int,
        metric_type: MetricType,
    ) -> float:
        """Calculate statistical significance p-value via two-sided normal approximation."""
        if sample_size <= 0:
            return 1.0

        if metric_type == MetricType.RATIO:
            p0 = max(1e-4, min(1.0 - 1e-4, expected_val))
            se = math.sqrt(p0 * (1.0 - p0) / sample_size)
            if se <= 0.0:
                return 1.0 if abs(actual_val - expected_val) < 1e-6 else 0.00001
            z = (actual_val - p0) / se
        else:
            denom = math.sqrt(max(expected_val, 1.0))
            z = (actual_val - expected_val) / denom

        p = math.erfc(abs(z) / math.sqrt(2))
        return round(max(0.00001, min(1.0, p)), 5)


__all__ = [
    "AnomalyRecord",
    "SegmentContribution",
    "AnomalyLocalizationResult",
    "AnomalyLocalizer",
    "LocalizationError",
    "UnsupportedDimensionError",
    "InsufficientDataForLocalizationError",
]
