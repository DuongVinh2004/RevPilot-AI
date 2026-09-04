"""
RevPilot AI — Pre-Treatment Covariate and Temporal Anti-Leakage Audit Engine
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §1.1, §5
Conforms to BR-001, BR-002, FR-ML-003, FR-ML-004, INV-AI-001, INV-DATA-001, and AC-006.
"""

from __future__ import annotations
from typing import Any, Optional

from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.causal.domain import CausalStudy, CausalInferenceError

PROHIBITED_VARIABLE_ROLES = {"MEDIATOR", "COLLIDER", "DOWNSTREAM_OUTCOME", "POST_TREATMENT"}


def audit_pre_treatment_covariates(
    pre_treatment_covariates: list[str],
    post_treatment_exclusions: list[str],
    variable_metadata: Optional[dict[str, dict[str, Any]]] = None,
) -> None:
    """
    Step 1: Pre-treatment covariate audit.
    Guarantees no post-treatment mediators or colliders enter the adjustment set.
    Raises ERR_POST_TREATMENT_COLLIDER on violation.
    """
    if not pre_treatment_covariates:
        raise CausalInferenceError(
            code="ERR_EMPTY_COVARIATE_SET",
            message="Pre-treatment covariates cannot be empty for observational causal identification",
        )

    # Check direct exclusion overlap
    cov_set = set(pre_treatment_covariates)
    excl_set = set(post_treatment_exclusions)
    overlap = cov_set.intersection(excl_set)
    if overlap:
        raise CausalInferenceError(
            code="ERR_POST_TREATMENT_COLLIDER",
            message=f"Post-treatment mediator/collider detected in adjustment covariates: {sorted(list(overlap))}",
            details={"violating_variables": sorted(list(overlap))},
        )

    # Check semantic metadata if available
    if variable_metadata:
        for var_name in pre_treatment_covariates:
            meta = variable_metadata.get(var_name)
            if meta:
                role = meta.get("role", "").upper()
                is_post = meta.get("is_post_treatment", False)
                if role in PROHIBITED_VARIABLE_ROLES or is_post:
                    raise CausalInferenceError(
                        code="ERR_POST_TREATMENT_COLLIDER",
                        message=f"Variable '{var_name}' identified as post-treatment mediator/collider with role '{role}'",
                        details={"variable": var_name, "role": role},
                    )


def audit_temporal_leakage(
    as_of_time: UtcDateTime,
    treatment_window_start: UtcDateTime,
    records: Optional[list[dict[str, Any]]] = None,
    covariate_timestamps: Optional[dict[str, UtcDateTime]] = None,
) -> None:
    """
    Step 2: Temporal as-of watermark and pre-treatment ordering audit.
    Guarantees zero future data leakage past as_of_time (INV-DATA-001),
    and strictly asserts covariates precede treatment window start.
    Raises ERR_TEMPORAL_LEAKAGE on violation.
    """
    # Check covariate timestamp ordering (must strictly precede treatment window start)
    if covariate_timestamps:
        for var_name, ts in covariate_timestamps.items():
            if ts >= treatment_window_start:
                raise CausalInferenceError(
                    code="ERR_TEMPORAL_LEAKAGE",
                    message=f"Covariate '{var_name}' timestamp {ts.isoformat()} is not strictly prior to treatment window start {treatment_window_start.isoformat()}",
                    details={"variable": var_name, "covariate_time": ts.isoformat(), "treatment_start": treatment_window_start.isoformat()},
                )

    # Check data records against as_of_time watermark
    if records:
        for idx, rec in enumerate(records):
            for time_field in ("timestamp", "event_time", "created_at", "updated_at"):
                val = rec.get(time_field)
                if val is not None:
                    if isinstance(val, str):
                        try:
                            rec_time = UtcDateTime.from_iso(val)
                        except Exception:
                            continue
                    elif isinstance(val, UtcDateTime):
                        rec_time = val
                    else:
                        continue

                    if rec_time > as_of_time:
                        raise CausalInferenceError(
                            code="ERR_TEMPORAL_LEAKAGE",
                            message=f"Record #{idx} contains timestamp {rec_time.isoformat()} exceeding as_of_time {as_of_time.isoformat()} (INV-DATA-001 lookahead violation)",
                            details={"record_index": idx, "record_time": rec_time.isoformat(), "as_of_time": as_of_time.isoformat()},
                        )


def audit_causal_study_specification(
    study: CausalStudy,
    records: Optional[list[dict[str, Any]]] = None,
    variable_metadata: Optional[dict[str, dict[str, Any]]] = None,
    covariate_timestamps: Optional[dict[str, UtcDateTime]] = None,
) -> None:
    """
    Comprehensive pre-estimation audit validating identification invariants:
    1. Pre-treatment covariate audit (no mediators/colliders).
    2. Temporal window sequencing.
    3. As-of time anti-leakage boundary.
    """
    # Check window consistency
    if study.treatment_window_start > study.treatment_window_end:
        raise CausalInferenceError(
            code="ERR_INVALID_WINDOW",
            message="Treatment window start must be <= treatment window end",
        )
    if study.outcome_window_start > study.outcome_window_end:
        raise CausalInferenceError(
            code="ERR_INVALID_WINDOW",
            message="Outcome window start must be <= outcome window end",
        )
    if study.treatment_window_start > study.outcome_window_start:
        raise CausalInferenceError(
            code="ERR_TEMPORAL_LEAKAGE",
            message="Treatment window cannot begin after outcome window start",
        )

    # Step 1: Covariate audit
    audit_pre_treatment_covariates(
        pre_treatment_covariates=study.pre_treatment_covariates,
        post_treatment_exclusions=study.post_treatment_exclusions,
        variable_metadata=variable_metadata,
    )

    # Step 2: Temporal leakage audit
    audit_temporal_leakage(
        as_of_time=study.as_of_time,
        treatment_window_start=study.treatment_window_start,
        records=records,
        covariate_timestamps=covariate_timestamps,
    )
