"""
RevPilot AI — Fairness and Subgroup Slice Disparity Evaluator
Specification: docs/11-decision-intelligence/FAIRNESS-SLICE-EVALUATION.md §1..§4
Conforms to BR-002, FR-ML-002..003, INV-AI-001, INV-PRV-001, INV-TEN-001..003, NFR-AI-005..006, and AC-014.
"""

from __future__ import annotations
import hashlib
import json
from collections import defaultdict
from typing import Any

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.fairness.domain import (
    SliceObservation,
    SliceMetric,
    DisparityAuditReport,
    GovernanceStatus,
    FairnessError,
)


def compute_expected_calibration_error(
    actuals: list[int], predicted_probs: list[float], num_bins: int = 10
) -> float:
    """
    Compute Expected Calibration Error (ECE) via equal-width probability binning.
    ECE = sum_{b=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|
    """
    n = len(actuals)
    if n == 0:
        return 0.0

    bins: list[list[tuple[int, float]]] = [[] for _ in range(num_bins)]
    for y, p in zip(actuals, predicted_probs):
        # Clip to [0.0, 1.0]
        p_clipped = max(0.0, min(1.0, float(p)))
        bin_idx = min(int(p_clipped * num_bins), num_bins - 1)
        bins[bin_idx].append((y, p_clipped))

    ece = 0.0
    for b in bins:
        if not b:
            continue
        bin_size = len(b)
        avg_acc = sum(y for y, _ in b) / bin_size
        avg_conf = sum(p for _, p in b) / bin_size
        ece += (bin_size / n) * abs(avg_acc - avg_conf)

    return round(ece, 4)


def compute_pr_auc(actuals: list[int], predicted_probs: list[float]) -> float:
    """
    Compute Precision-Recall AUC (Average Precision) via trapezoidal / Riemann sum.
    """
    n = len(actuals)
    total_positives = sum(actuals)
    if n == 0 or total_positives == 0:
        return 0.0

    # Sort descending by predicted probability
    paired = sorted(zip(predicted_probs, actuals), key=lambda x: x[0], reverse=True)

    tp = 0
    fp = 0
    prev_recall = 0.0
    ap = 0.0

    for _, y in paired:
        if y == 1:
            tp += 1
        else:
            fp += 1
        recall = tp / total_positives
        precision = tp / (tp + fp)
        delta_recall = recall - prev_recall
        if delta_recall > 0.0:
            ap += precision * delta_recall
            prev_recall = recall

    return round(ap, 4)


def evaluate_fairness_slices(
    observations: list[SliceObservation],
    tenant_id: TenantId,
    model_artifact_id: str,
    decision_policy_id: str,
    as_of_time: UtcDateTime,
    min_sample_size: int = 50,
) -> DisparityAuditReport:
    """
    Audit model and policy equity across operational slices.
    Strictly enforces small-sample noise suppression (AC-014):
    Slices with N < min_sample_size are marked INSUFFICIENT_SAMPLE and metrics are suppressed.
    """
    if not observations:
        raise FairnessError(
            code="ERR_EMPTY_OBSERVATIONS",
            message="Cannot evaluate fairness slices on empty observation dataset",
        )

    # 1. Group observations by (slice_dimension, slice_value)
    grouped: dict[tuple[str, str], list[SliceObservation]] = defaultdict(list)
    for obs in observations:
        grouped[(obs.slice_dimension, obs.slice_value)].append(obs)

    evaluated_slices: list[SliceMetric] = []
    # Index reliable slices by dimension for disparity comparison
    dimension_slices: dict[str, list[SliceMetric]] = defaultdict(list)

    for (dimension, value), items in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1])):
        sample_size = len(items)
        if sample_size < min_sample_size:
            # Small-sample suppression
            metric = SliceMetric(
                slice_dimension=dimension,
                slice_value=value,
                sample_size=sample_size,
                is_statistically_reliable=False,
                pr_auc=None,
                ece=None,
                mean_uplift_cate=None,
                treatment_recommendation_rate=None,
                evaluation_status="INSUFFICIENT_SAMPLE",
            )
        else:
            # Reliable sample size
            actuals = [it.actual_churn for it in items]
            probs = [it.predicted_prob for it in items]
            ece = compute_expected_calibration_error(actuals, probs)
            pr_auc = compute_pr_auc(actuals, probs)
            mean_cate = round(sum(it.cate_estimate for it in items) / sample_size, 4)
            rec_rate = round(sum(1 for it in items if it.is_recommended) / sample_size, 4)

            metric = SliceMetric(
                slice_dimension=dimension,
                slice_value=value,
                sample_size=sample_size,
                is_statistically_reliable=True,
                pr_auc=pr_auc,
                ece=ece,
                mean_uplift_cate=mean_cate,
                treatment_recommendation_rate=rec_rate,
                evaluation_status="EVALUATED",
            )
            dimension_slices[dimension].append(metric)

        evaluated_slices.append(metric)

    # 2. Compute disparity metrics
    max_calib_disparity = 0.0
    max_alloc_ratio = 1.0
    min_alloc_ratio = 1.0

    for dim, rel_slices in dimension_slices.items():
        if len(rel_slices) >= 2:
            # Pairwise calibration disparity Delta ECE = |ECE(s1) - ECE(s2)|
            for i in range(len(rel_slices)):
                for j in range(i + 1, len(rel_slices)):
                    s1 = rel_slices[i]
                    s2 = rel_slices[j]
                    if s1.ece is not None and s2.ece is not None:
                        cal_disp = abs(s1.ece - s2.ece)
                        if cal_disp > max_calib_disparity:
                            max_calib_disparity = cal_disp

                    # Pairwise treatment recommendation rate ratio
                    r1 = s1.treatment_recommendation_rate
                    r2 = s2.treatment_recommendation_rate
                    if r1 is not None and r2 is not None:
                        if r2 > 0.0:
                            ratio1 = r1 / r2
                            max_alloc_ratio = max(max_alloc_ratio, ratio1)
                            min_alloc_ratio = min(min_alloc_ratio, ratio1)
                        if r1 > 0.0:
                            ratio2 = r2 / r1
                            max_alloc_ratio = max(max_alloc_ratio, ratio2)
                            min_alloc_ratio = min(min_alloc_ratio, ratio2)

    max_calib_disparity = round(max_calib_disparity, 4)
    max_alloc_ratio = round(max_alloc_ratio, 4)

    # 3. Governance Status Gate
    reliable_count = sum(1 for m in evaluated_slices if m.is_statistically_reliable)
    if reliable_count == 0:
        gov_status: GovernanceStatus = "INSUFFICIENT_DATA"
    elif max_calib_disparity > 0.0300 or max_alloc_ratio > 1.25 or min_alloc_ratio < 0.80:
        gov_status = "NEEDS_REVIEW"
    else:
        gov_status = "PASS"

    # 4. Seal Reproducibility Manifest (SHA-256)
    report_id = UUIDv7.generate()
    created_at = UtcDateTime.now()

    manifest = {
        "version": "1.0",
        "report_id": str(report_id),
        "tenant_id": str(tenant_id),
        "model_artifact_id": model_artifact_id,
        "decision_policy_id": decision_policy_id,
        "as_of_time": as_of_time.isoformat(),
        "max_calibration_disparity": max_calib_disparity,
        "max_allocation_disparity_ratio": max_alloc_ratio,
        "governance_status": gov_status,
        "evaluated_slices": [s.model_dump() for s in evaluated_slices],
    }
    canonical_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    audit_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    return DisparityAuditReport(
        report_id=report_id,
        tenant_id=tenant_id,
        model_artifact_id=model_artifact_id,
        decision_policy_id=decision_policy_id,
        as_of_time=as_of_time,
        evaluated_slices=evaluated_slices,
        max_calibration_disparity=max_calib_disparity,
        max_allocation_disparity_ratio=max_alloc_ratio,
        governance_status=gov_status,
        audit_digest=audit_digest,
        created_at=created_at,
    )
