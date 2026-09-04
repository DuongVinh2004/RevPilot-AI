"""
RevPilot AI — Competing-Cause Hypothesis Ranking Engine
Specification: docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md §3
Conforms to BR-001, BR-002, FR-RCA-001, FR-RCA-002, INV-AI-001..002, INV-TEN-001, and AC-004.
"""

from __future__ import annotations
from typing import Any, Optional

from revpilot.modules.hypothesis.domain import (
    HypothesisRecord,
    HypothesisStatus,
    HypothesisError,
    compute_hypothesis_digest,
)
from revpilot.modules.evidence.domain.models import EvidenceBundle

DEFAULT_WEIGHTS: dict[str, float] = {
    "w_sup": 0.40,
    "w_con": 0.45,
    "w_causal": 0.30,
    "w_gap": 0.25,
}

TIE_THRESHOLD: float = 0.05
CONTRADICTION_VETO_THRESHOLD: float = 0.80
COVERAGE_VERIFIED_THRESHOLD: float = 0.75


def calculate_hypothesis_score(
    hypothesis: HypothesisRecord,
    weights: Optional[dict[str, float]] = None,
) -> float:
    """
    Evaluate candidate hypothesis against gathered evidence using multi-criteria scoring:
    Score(H) = w_sup * S_sup(H) - w_con * S_con(H) + w_causal * S_causal(H) - w_gap * G(H)
    Result is clamped to [0.0, 1.0].
    """
    w = DEFAULT_WEIGHTS.copy()
    if weights:
        w.update(weights)

    # Supporting evidence score: normalized average of supporting relevance
    if hypothesis.supporting_evidence:
        s_sup = sum(e.relevance_score for e in hypothesis.supporting_evidence) / len(hypothesis.supporting_evidence)
    else:
        s_sup = 0.0

    # Contradicting evidence score: maximum authoritative contradiction relevance
    if hypothesis.contradicting_evidence:
        s_con = max(e.relevance_score for e in hypothesis.contradicting_evidence)
    else:
        s_con = 0.0

    # Causal study backing bonus
    s_causal = 1.0 if hypothesis.causal_study_id is not None else 0.0

    # Missing evidence gap penalty
    g_gap = max(0.0, 1.0 - hypothesis.evidence_coverage_ratio)

    raw_score = (
        w["w_sup"] * s_sup
        - w["w_con"] * s_con
        + w["w_causal"] * s_causal
        - w["w_gap"] * g_gap
    )

    return max(0.0, min(1.0, round(raw_score, 4)))


def rank_competing_hypotheses(
    hypotheses: list[HypothesisRecord],
    bundle: Optional[EvidenceBundle] = None,
    weights: Optional[dict[str, float]] = None,
) -> list[HypothesisRecord]:
    """
    Rank competing candidate hypotheses for an observed anomaly.
    Enforces:
    1. Multi-hypothesis competition (>= 2 candidates, FR-RCA-001).
    2. Single-tenant isolation (INV-TEN-001).
    3. Contradiction Veto (S_con >= 0.80 -> REFUTED).
    4. Deterministic fallback to NEED_MORE_EVIDENCE when coverage < 0.75 (FR-RCA-002).
    5. Top-1 VERIFIED requires >= 0.75 coverage, 0 contradictions, and >= 2 evaluated competitors.
    6. Co-equal tie flagging (AMBIGUOUS_COMPETING_CAUSES) when score diff <= 0.05.
    """
    if len(hypotheses) < 2:
        raise HypothesisError(
            code="ERR_MULTI_HYPOTHESIS_VIOLATION",
            message="Multi-hypothesis competition invariant violated: at least 2 competing hypotheses required",
            details={"candidate_count": len(hypotheses)},
        )

    # Single-tenant check across hypotheses
    base_tenant_id = hypotheses[0].tenant_id
    for h in hypotheses[1:]:
        if h.tenant_id != base_tenant_id:
            raise HypothesisError(
                code="ERR_TENANT_MISMATCH",
                message="Cross-tenant hypothesis evaluation forbidden",
                details={"expected_tenant": str(base_tenant_id), "actual_tenant": str(h.tenant_id)},
            )

    # Single-tenant check with EvidenceBundle if provided
    if bundle is not None:
        if bundle.tenant_id != base_tenant_id:
            raise HypothesisError(
                code="ERR_TENANT_MISMATCH",
                message="Evidence bundle tenant does not match hypothesis tenant",
                details={"expected_tenant": str(base_tenant_id), "bundle_tenant": str(bundle.tenant_id)},
            )

    # Step 1: Score each hypothesis and determine base status
    evaluated: list[HypothesisRecord] = []
    for h in hypotheses:
        score = calculate_hypothesis_score(h, weights=weights)
        s_con = max([e.relevance_score for e in h.contradicting_evidence], default=0.0)

        # Invariant 1: Contradiction Veto
        if s_con >= CONTRADICTION_VETO_THRESHOLD:
            status = HypothesisStatus.REFUTED
        elif h.evidence_coverage_ratio < COVERAGE_VERIFIED_THRESHOLD:
            status = HypothesisStatus.NEED_MORE_EVIDENCE
        else:
            status = HypothesisStatus.EVALUATING

        updated_h = h.model_copy(update={"ranking_score": score, "status": status})
        evaluated.append(updated_h)

    # Step 2: Sort candidates:
    # Priority 1: Not REFUTED candidates precede REFUTED candidates
    # Priority 2: Descending ranking_score
    # Priority 3: Deterministic tie-breaker on hypothesis_id
    candidates = sorted(
        evaluated,
        key=lambda item: (
            0 if item.status == HypothesisStatus.REFUTED else 1,
            item.ranking_score,
            tuple(-ord(c) for c in item.hypothesis_id),
        ),
        reverse=True,
    )

    # Step 3: Top-1 Invariant Check (No Fabricated Top-1)
    top1 = candidates[0]
    num_competitors = len(candidates) - 1

    if top1.status != HypothesisStatus.REFUTED:
        has_sufficient_coverage = top1.evidence_coverage_ratio >= COVERAGE_VERIFIED_THRESHOLD
        has_no_contradictions = len(top1.contradicting_evidence) == 0
        has_min_two_competitors = num_competitors >= 2

        if has_sufficient_coverage and has_no_contradictions and has_min_two_competitors:
            top1_status = HypothesisStatus.VERIFIED
        else:
            top1_status = HypothesisStatus.NEED_MORE_EVIDENCE

        candidates[0] = top1.model_copy(update={"status": top1_status})

    # Step 4: Co-Equal Ranking check for non-refuted candidates
    co_equal_flags: set[int] = set()
    for i in range(len(candidates) - 1):
        c1 = candidates[i]
        c2 = candidates[i + 1]
        if (
            c1.status != HypothesisStatus.REFUTED
            and c2.status != HypothesisStatus.REFUTED
            and abs(c1.ranking_score - c2.ranking_score) <= TIE_THRESHOLD
            and c1.hypothesis_type != c2.hypothesis_type
        ):
            co_equal_flags.add(i)
            co_equal_flags.add(i + 1)

    # Step 5: Assign ordinal_rank, alternative_hypothesis_ids, limitations, and manifest_digest
    all_ids = [c.hypothesis_id for c in candidates]
    final_ranked: list[HypothesisRecord] = []

    for idx, c in enumerate(candidates):
        rank = idx + 1
        alts = [hid for hid in all_ids if hid != c.hypothesis_id]
        new_limitations = list(c.limitations)

        if idx in co_equal_flags:
            tie_msg = f"AMBIGUOUS_COMPETING_CAUSES: Score difference <= {TIE_THRESHOLD} with competing candidate"
            if tie_msg not in new_limitations:
                new_limitations.append(tie_msg)

        # Compute tamper-evident digest
        digest = compute_hypothesis_digest(
            hypothesis_id=c.hypothesis_id,
            investigation_id=c.investigation_id,
            tenant_id=c.tenant_id,
            statement=c.statement,
            hypothesis_type=c.hypothesis_type,
            supporting_evidence=c.supporting_evidence,
            contradicting_evidence=c.contradicting_evidence,
        )

        ranked_record = c.model_copy(
            update={
                "ordinal_rank": rank,
                "alternative_hypothesis_ids": alts,
                "limitations": new_limitations,
                "manifest_digest": digest,
            }
        )
        final_ranked.append(ranked_record)

    return final_ranked
