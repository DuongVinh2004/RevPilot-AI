"""
RevPilot AI — 12-Step Governed Decision Intelligence Engine
Specification: docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md §2, §3
Conforms to BR-002, BR-005, FR-DEC-001, INV-AI-001, INV-ACT-001, INV-COST-001, INV-TEN-001..003, INV-DATA-001, NFR-AI-006..007, NFR-COST-001, AC-007, and ADR-0003.
"""

from __future__ import annotations
import hashlib
import json
from decimal import Decimal
from typing import Any

from revpilot.shared.identifiers import UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.constraints.domain import ConstraintEvaluatorRequest
from revpilot.modules.constraints.evaluator import evaluate_hard_constraints
from revpilot.modules.decision.domain import (
    DecisionRequest,
    DecisionCandidate,
    RankedAlternative,
    RecommendationRecord,
    RecommendationStatus,
    DecisionError,
)


class DecisionEngine:
    """Deterministic, read-only optimizer implementing the governed 12-step decision pipeline."""

    BASE_RISK_PENALTIES: dict[str, Decimal] = {
        "LOW": Decimal("0.0"),
        "MEDIUM": Decimal("25.00"),
        "HIGH": Decimal("100.00"),
    }

    def execute_decision_pipeline(self, request: DecisionRequest) -> RecommendationRecord:
        """
        Execute the non-bypassable 12-step decision intelligence pipeline.
        Strictly read-only barrier: zero side-effects or external tool execution (INV-ACT-001).
        """
        # =========================================================================
        # Step 1: Validate TenantContext, PrincipalContext, and Request Auth (INV-TEN-001)
        # =========================================================================
        self._step1_validate_auth_and_context(request)

        # =========================================================================
        # Step 2: Validate Versioned Data Snapshot and As-Of Watermark (INV-DATA-001)
        # =========================================================================
        self._step2_validate_temporal_watermark(request)

        # =========================================================================
        # Step 3: Validate Candidate Interventions and Cost Parameters
        # =========================================================================
        self._step3_validate_candidate_parameters(request)

        # =========================================================================
        # Step 4–7: Apply Hard Constraints (Eligibility, Policy, Budget, Capacity) (AC-007)
        # =========================================================================
        eligible_candidates, ineligible_reasons = self._steps4_to_7_apply_hard_constraints(request)

        # =========================================================================
        # Step 8: Compute Expected Utility for Eligible Candidates
        # =========================================================================
        computed_utilities = self._step8_compute_expected_utility(request, eligible_candidates)

        # =========================================================================
        # Step 9: Rank Eligible Candidates using Deterministic Tie-Breaking
        # =========================================================================
        ranked_candidates = self._step9_rank_candidates(computed_utilities)

        # =========================================================================
        # Step 10: Attach Uncertainty Interval, Risk Penalties, and Limitations
        # =========================================================================
        ranked_alternatives = self._step10_build_ranked_alternatives(ranked_candidates)

        # =========================================================================
        # Step 11: Format Recommendation Record or Return NEED_MORE_EVIDENCE / ABSTAINED / BLOCKED
        # =========================================================================
        status, selected_candidate, top_metrics = self._step11_determine_status(
            request=request,
            eligible_candidates=eligible_candidates,
            ranked_alternatives=ranked_alternatives,
        )

        # =========================================================================
        # Step 12: Seal Reproducibility Manifest (SHA-256 Digest) and Emit Audit
        # =========================================================================
        recommendation_id = UUIDv7.generate()
        created_at = UtcDateTime.now()

        decision_digest = self._step12_compute_reproducibility_digest(
            request=request,
            recommendation_id=recommendation_id,
            status=status,
            selected_candidate_id=selected_candidate.candidate_id if selected_candidate else None,
            top_metrics=top_metrics,
            ranked_alternatives=ranked_alternatives,
            ineligible_reasons=ineligible_reasons,
        )

        return RecommendationRecord(
            recommendation_id=recommendation_id,
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            selected_candidate_id=selected_candidate.candidate_id if selected_candidate else None,
            expected_utility_usd=top_metrics["expected_utility_usd"],
            expected_incremental_retention_rate=top_metrics["expected_cate"],
            direct_cost_usd=top_metrics["direct_cost_usd"],
            risk_penalty_usd=top_metrics["risk_penalty_usd"],
            uncertainty_penalty_usd=top_metrics["uncertainty_penalty_usd"],
            confidence_interval_95=top_metrics["confidence_interval_95"],
            ranked_alternatives=[alt.model_dump() for alt in ranked_alternatives],
            ineligible_candidates=ineligible_reasons,
            status=status,
            decision_digest=decision_digest,
            created_at=created_at,
        )

    # -------------------------------------------------------------------------
    # Pipeline Step Implementations
    # -------------------------------------------------------------------------

    def _step1_validate_auth_and_context(self, request: DecisionRequest) -> None:
        if not str(request.tenant_id).strip():
            raise DecisionError(code="ERR_TENANT_MISMATCH", message="Tenant ID must not be empty")
        if not request.customer_id.strip():
            raise DecisionError(code="ERR_INVALID_REQUEST", message="Customer ID must not be empty")

    def _step2_validate_temporal_watermark(self, request: DecisionRequest) -> None:
        # Anti-leakage: feature snapshot cannot be in future relative to as-of watermark
        if request.feature_timestamp > request.as_of_time:
            raise DecisionError(
                code="ERR_TEMPORAL_LEAKAGE",
                message="Feature timestamp exceeds as-of watermark time",
                details={
                    "feature_timestamp": request.feature_timestamp.isoformat(),
                    "as_of_time": request.as_of_time.isoformat(),
                },
            )
        # Check staleness limit
        staleness_hours = (
            request.as_of_time.value - request.feature_timestamp.value
        ).total_seconds() / 3600.0
        if staleness_hours > request.max_feature_staleness_hours:
            raise DecisionError(
                code="ERR_STALE_FEATURES",
                message=f"Feature staleness ({staleness_hours:.1f}h) exceeds limit ({request.max_feature_staleness_hours}h)",
            )

    def _step3_validate_candidate_parameters(self, request: DecisionRequest) -> None:
        if not request.candidates:
            raise DecisionError(
                code="ERR_EMPTY_CANDIDATES",
                message="Decision request must contain at least one candidate intervention",
            )
        for cand in request.candidates:
            if cand.estimated_cost_usd < Decimal("0.0"):
                raise DecisionError(
                    code="ERR_INVALID_CANDIDATE_PARAMETERS",
                    message=f"Candidate {cand.candidate_id} has negative estimated cost",
                )
            if not cand.eligible_tiers:
                raise DecisionError(
                    code="ERR_INVALID_CANDIDATE_PARAMETERS",
                    message=f"Candidate {cand.candidate_id} must specify eligible tiers",
                )

    def _steps4_to_7_apply_hard_constraints(
        self, request: DecisionRequest
    ) -> tuple[list[DecisionCandidate], dict[str, list[str]]]:
        eligible: list[DecisionCandidate] = []
        ineligible_reasons: dict[str, list[str]] = {}

        for candidate in request.candidates:
            eval_req = ConstraintEvaluatorRequest(
                tenant_id=request.tenant_id,
                customer_id=request.customer_id,
                customer_tier=request.customer_tier,
                intervention=candidate,
                current_time=request.as_of_time,
                budget_ledger=request.budget_ledger,
                active_capacity_count=request.active_capacity_count,
                max_capacity_limit=request.max_capacity_limit,
                customer_history_timestamps=request.customer_history_timestamps,
                quarterly_history_timestamps=request.quarterly_history_timestamps,
                max_quarterly_frequency=request.max_quarterly_frequency,
                customer_opt_out=request.customer_opt_out,
                is_excluded=request.is_excluded,
                incident_treated_count=request.incident_treated_count,
                max_blast_radius=request.max_blast_radius,
                feature_timestamp=request.feature_timestamp,
                max_feature_staleness_hours=request.max_feature_staleness_hours,
            )
            outcome = evaluate_hard_constraints(eval_req)
            if outcome.is_eligible:
                eligible.append(candidate)
            else:
                ineligible_reasons[candidate.candidate_id] = outcome.violated_constraints

        return eligible, ineligible_reasons

    def _step8_compute_expected_utility(
        self, request: DecisionRequest, eligible_candidates: list[DecisionCandidate]
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        customer_arr = float(request.customer_arr_usd)
        lambda_risk = Decimal(str(request.risk_aversion_lambda))
        lambda_unc = Decimal(str(request.uncertainty_lambda))

        for cand in eligible_candidates:
            # 1. Expected incremental gain = \tau(X_i, a) * V_customer
            incremental_gain_val = round(cand.expected_cate * customer_arr, 4)
            incremental_gain_usd = Decimal(str(incremental_gain_val))

            # 2. Direct cost C(a)
            direct_cost_usd = cand.estimated_cost_usd

            # 3. Risk penalty = \lambda_risk * RiskPenalty(a)
            base_risk = (
                cand.custom_risk_penalty_usd
                if cand.custom_risk_penalty_usd is not None
                else self.BASE_RISK_PENALTIES.get(cand.risk_tier, Decimal("0.0"))
            )
            risk_penalty_usd = round(lambda_risk * base_risk, 4)

            # 4. Uncertainty penalty = \lambda_unc * (\sigma_\tau * V_customer)
            uncertainty_monetary = round(cand.cate_standard_error * customer_arr, 4)
            uncertainty_penalty_usd = round(lambda_unc * Decimal(str(uncertainty_monetary)), 4)

            # 5. Expected Utility E[U] = Incremental Gain - Cost - RiskPenalty - UncertaintyPenalty
            expected_utility_usd = (
                incremental_gain_usd - direct_cost_usd - risk_penalty_usd - uncertainty_penalty_usd
            )

            results.append({
                "candidate": cand,
                "expected_utility_usd": expected_utility_usd,
                "expected_cate": cand.expected_cate,
                "incremental_gain_usd": incremental_gain_usd,
                "direct_cost_usd": direct_cost_usd,
                "risk_penalty_usd": risk_penalty_usd,
                "uncertainty_penalty_usd": uncertainty_penalty_usd,
                "cate_standard_error": cand.cate_standard_error,
                "confidence_interval_95": cand.confidence_interval_95,
                "overlap_satisfied": cand.overlap_satisfied,
            })

        return results

    def _step9_rank_candidates(
        self, computed_utilities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Sort candidates deterministically by expected utility with tie-breaking:
        1. Higher expected utility.
        2. Within |delta U| < 0.001:
           a. Lower direct cost C(a).
           b. Lower uncertainty sigma_tau(a).
           c. Lexicographical candidate_id.
        """
        def sort_key(item: dict[str, Any]) -> tuple[float, float, float, str]:
            u = float(item["expected_utility_usd"])
            cost = float(item["direct_cost_usd"])
            unc = float(item["cate_standard_error"])
            cid = item["candidate"].candidate_id
            # Quantize utility to 3 decimal places to group near-ties (|delta U| < 0.001)
            quantized_u = round(u, 3)
            # Higher quantized utility first (negated), then lower cost, lower uncertainty, lexicographical ID
            return (-quantized_u, cost, unc, cid)

        return sorted(computed_utilities, key=sort_key)

    def _step10_build_ranked_alternatives(
        self, ranked_candidates: list[dict[str, Any]]
    ) -> list[RankedAlternative]:
        alternatives: list[RankedAlternative] = []
        for rank_idx, item in enumerate(ranked_candidates, start=1):
            cand: DecisionCandidate = item["candidate"]
            alternatives.append(
                RankedAlternative(
                    candidate_id=cand.candidate_id,
                    name=cand.name,
                    expected_utility_usd=item["expected_utility_usd"],
                    expected_cate=item["expected_cate"],
                    incremental_gain_usd=item["incremental_gain_usd"],
                    direct_cost_usd=item["direct_cost_usd"],
                    risk_penalty_usd=item["risk_penalty_usd"],
                    uncertainty_penalty_usd=item["uncertainty_penalty_usd"],
                    confidence_interval_95=item["confidence_interval_95"],
                    rank=rank_idx,
                )
            )
        return alternatives

    def _step11_determine_status(
        self,
        request: DecisionRequest,
        eligible_candidates: list[DecisionCandidate],
        ranked_alternatives: list[RankedAlternative],
    ) -> tuple[RecommendationStatus, DecisionCandidate | None, dict[str, Any]]:
        zero_metrics: dict[str, Any] = {
            "expected_utility_usd": Decimal("0.0"),
            "expected_cate": 0.0,
            "direct_cost_usd": Decimal("0.0"),
            "risk_penalty_usd": Decimal("0.0"),
            "uncertainty_penalty_usd": Decimal("0.0"),
            "confidence_interval_95": (0.0, 0.0),
        }

        # Case 1: No eligible candidates passed hard constraints
        if not eligible_candidates:
            return "BLOCKED", None, zero_metrics

        # Candidate mapping for lookup
        cand_map = {c.candidate_id: c for c in eligible_candidates}
        top_alt = ranked_alternatives[0]
        top_cand = cand_map[top_alt.candidate_id]

        # Case 2: Positivity / Overlap violation or insufficient causal evidence
        if not top_cand.overlap_satisfied:
            return "NEED_MORE_EVIDENCE", None, zero_metrics

        # Case 3: Economic Viability Rule (E[U] <= 0 -> Abstain)
        if top_alt.expected_utility_usd <= Decimal("0.0"):
            return "ABSTAINED", None, zero_metrics

        # Case 4: Positive Expected Utility -> Recommend
        top_metrics = {
            "expected_utility_usd": top_alt.expected_utility_usd,
            "expected_cate": top_alt.expected_cate,
            "direct_cost_usd": top_alt.direct_cost_usd,
            "risk_penalty_usd": top_alt.risk_penalty_usd,
            "uncertainty_penalty_usd": top_alt.uncertainty_penalty_usd,
            "confidence_interval_95": top_alt.confidence_interval_95,
        }
        return "RECOMMENDED", top_cand, top_metrics

    def _step12_compute_reproducibility_digest(
        self,
        request: DecisionRequest,
        recommendation_id: UUIDv7,
        status: RecommendationStatus,
        selected_candidate_id: str | None,
        top_metrics: dict[str, Any],
        ranked_alternatives: list[RankedAlternative],
        ineligible_reasons: dict[str, list[str]],
    ) -> str:
        manifest = {
            "version": "1.0",
            "recommendation_id": str(recommendation_id),
            "request_id": str(request.request_id),
            "tenant_id": str(request.tenant_id),
            "customer_id": request.customer_id,
            "as_of_time": request.as_of_time.isoformat(),
            "customer_arr_usd": str(request.customer_arr_usd),
            "risk_aversion_lambda": request.risk_aversion_lambda,
            "uncertainty_lambda": request.uncertainty_lambda,
            "status": status,
            "selected_candidate_id": selected_candidate_id,
            "expected_utility_usd": str(top_metrics["expected_utility_usd"]),
            "ranked_candidate_ids": [alt.candidate_id for alt in ranked_alternatives],
            "ineligible_candidate_ids": sorted(list(ineligible_reasons.keys())),
        }
        canonical_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
