"""
RevPilot AI — Fairness and Demographic Disparity Evaluation Module
Specification: docs/11-decision-intelligence/FAIRNESS-SLICE-EVALUATION.md
"""

from revpilot.modules.fairness.domain import (
    EvaluationStatus,
    GovernanceStatus,
    SliceObservation,
    SliceMetric,
    DisparityAuditReport,
    FairnessError,
)
from revpilot.modules.fairness.evaluator import (
    compute_expected_calibration_error,
    compute_pr_auc,
    evaluate_fairness_slices,
)
from revpilot.modules.fairness.ports import (
    FairnessAuditRepository,
    InMemoryFairnessAuditRepository,
)

__all__ = [
    "EvaluationStatus",
    "GovernanceStatus",
    "SliceObservation",
    "SliceMetric",
    "DisparityAuditReport",
    "FairnessError",
    "compute_expected_calibration_error",
    "compute_pr_auc",
    "evaluate_fairness_slices",
    "FairnessAuditRepository",
    "InMemoryFairnessAuditRepository",
]
