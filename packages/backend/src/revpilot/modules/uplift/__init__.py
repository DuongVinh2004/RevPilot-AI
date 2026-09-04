"""
RevPilot AI — Uplift, Heterogeneous Treatment Effect & Decision Simulation Module
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md
Conforms to BR-002, BR-005, FR-ML-003, FR-ML-004, INV-AI-001, and AC-006.
"""

from revpilot.modules.uplift.domain import (
    UpliftEstimatorType,
    PersuadabilitySegment,
    UpliftScoreRecord,
    UpliftError,
    compute_uplift_digest,
)
from revpilot.modules.uplift.estimators import (
    classify_persuadability,
    estimate_t_learner_cate,
    estimate_s_learner_cate,
)
from revpilot.modules.uplift.ports import (
    UpliftRepository,
    InMemoryUpliftRepository,
)

__all__ = [
    # Domain Enums & Models
    "UpliftEstimatorType",
    "PersuadabilitySegment",
    "UpliftScoreRecord",
    "UpliftError",
    "compute_uplift_digest",
    # Estimators & Classification
    "classify_persuadability",
    "estimate_t_learner_cate",
    "estimate_s_learner_cate",
    # Ports & Adapters
    "UpliftRepository",
    "InMemoryUpliftRepository",
]
