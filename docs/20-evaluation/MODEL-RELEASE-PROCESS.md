# Model and AI Artifact Release Process

Status: Proposed v0.1 — E02 specification output

## Release record and states

`ReleaseCandidate` binds one artifact manifest, required EvalRuns, tenant eligibility, provider terms, rollback artifact and approver. States are `DRAFT -> EVALUATED -> REVIEW_REQUIRED -> APPROVED -> ACTIVE -> RETIRED`; only an authorized governance approver transitions to APPROVED. Activation is blocked without complete versions, passing gates, rollback, and audit record.

## Gate policy

Required gates are applicable quality thresholds in `NFR-AI-*`, schema validity, security/injection tests, tenant/data governance, cost budget, observability fields and compatibility. Causal/uplift artifacts additionally require estimand/overlap/sensitivity evidence. Failure, unknown evaluation, incompatible schema or revoked provider eligibility blocks release. A release is scoped to declared capability and tenant tier; it grants no external action authority.

## Rollback and monitoring

Rollback selects a previously approved compatible immutable artifact; it never rewrites decision history. Drift, safety, cost, latency or quality trigger creates a review/retire event and may suspend activation. Monitor artifact version, inputs schema, quality, slice degradation, cost and provider errors. Audit release, activation, rollback, and exception decisions.

## Traceability

`INV-AI-002`, `NFR-AI-001..007`, `NFR-COST-001`, ADR-0011.
