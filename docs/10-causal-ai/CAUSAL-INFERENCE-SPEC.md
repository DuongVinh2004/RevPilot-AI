# Causal Inference Contract

Status: Proposed v0.1 — E02 specification output

## Claim boundary

The Causal module may emit a causal estimate only for a declared `CausalStudy` with treatment, outcome, unit, time window, estimand, causal graph/assumptions, confounders, identification rationale, overlap result, estimator, uncertainty interval and sensitivity/refutation result. Otherwise it emits an association or `INSUFFICIENT_EVIDENCE`. LLMs may summarize a validated study but cannot produce causal evidence.

## Study lifecycle

`DRAFT -> IDENTIFIED -> ESTIMATED -> VALIDATED -> RELEASED` is allowed; any failed identification, overlap, leakage, or sensitivity gate transitions to `REJECTED` or `INSUFFICIENT_EVIDENCE`. Inputs use versioned, tenant-authorized as-of datasets. A study and estimate reference artifact and dataset manifests, never mutable tables. Counterfactual and synthetic-ground-truth fixtures are evaluation-only and hidden from runtime reasoning.

## Evaluation and failure

Required gates: pre-treatment feature audit, treatment/outcome time ordering, positivity/overlap threshold declared before estimation, confidence interval, effect-error <= 0.05 only on the declared synthetic estimand, falsification/sensitivity result, and slice disclosure. Missing data, unsupported identification, unstable estimate or gate failure prevents Decision use. Emit study/version/status/metric references without raw personal data.

## Traceability

`INV-AI-001`, `INV-DATA-001`, `NFR-AI-007`; E02 evaluation and future Phase 04 only.
