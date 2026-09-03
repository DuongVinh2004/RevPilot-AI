# ML System Contract

Status: Proposed v0.1 — E02 specification output

## Model families and separation

Anomaly detection, forecasting, churn prediction, uplift estimation, and causal estimation are distinct artifact families. A churn score is not uplift; association is not a causal effect; an LLM explanation is not a statistical estimate. Each `ModelArtifact` references immutable `DatasetManifest`, feature schema, target/estimand, time split, baseline, calibration, metrics, threshold policy, code/container digest, owner, and release state.

## Dataset and evaluation rules

Features are available at the recorded `as_of` time. Split by time before any fitting or transform that can learn population information; tenant data is segregated by default and pooling requires an approved governance policy. The declared baseline is evaluated against the same holdout and slices. Churn requires PR-AUC and ECE/Brier; uplift requires Qini versus random/no-target; causal requires effect error with identification/overlap/sensitivity evidence. Failed gates make the artifact ineligible for decision use.

## Serving and failure

`ModelInferenceRequest` contains tenant, authorized data references, artifact ID, as-of time, correlation ID and deadline. It returns prediction/interval or a typed `UNAVAILABLE|OUT_OF_SCOPE|INSUFFICIENT_DATA|GATE_FAILED` result. Serving never selects a model implicitly; Decision Intelligence receives the artifact ID, confidence/calibration state and limitations. Drift, leakage, missing feature, schema mismatch, or expired release blocks or falls back to a policy-approved deterministic baseline labelled as such.

## Traceability

`INV-DATA-001`, `INV-AI-001..002`, `NFR-AI-005..007`, `NFR-COST-001`; ADR-0011.
