"""
RevPilot AI — Hypothesis Domain, Verification, and Competing-Cause Module
Specification: docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md
Conforms to BR-001, BR-002, FR-RCA-001, FR-RCA-002, INV-AI-001..002, INV-TEN-001, and AC-004.
"""

from revpilot.modules.hypothesis.domain import (
    HypothesisType,
    HypothesisStatus,
    EpistemicCategory,
    EvidenceWeight,
    HypothesisRecord,
    HypothesisError,
    compute_hypothesis_digest,
)
from revpilot.modules.hypothesis.ranking import (
    DEFAULT_WEIGHTS,
    calculate_hypothesis_score,
    rank_competing_hypotheses,
)
from revpilot.modules.hypothesis.ports import (
    HypothesisRepository,
    InMemoryHypothesisRepository,
)

__all__ = [
    # Domain Enums & Models
    "HypothesisType",
    "HypothesisStatus",
    "EpistemicCategory",
    "EvidenceWeight",
    "HypothesisRecord",
    "HypothesisError",
    "compute_hypothesis_digest",
    # Ranking Engine
    "DEFAULT_WEIGHTS",
    "calculate_hypothesis_score",
    "rank_competing_hypotheses",
    # Ports & Adapters
    "HypothesisRepository",
    "InMemoryHypothesisRepository",
]
