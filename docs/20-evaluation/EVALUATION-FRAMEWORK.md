# Evaluation Framework Contract

Status: Proposed v0.1 — E02 specification output

## EvalRun schema

An immutable `EvalRun` records evaluator version, artifact versions, dataset manifest/digest, split, slices, metric definitions, thresholds, execution environment digest, timestamp, owner and outcome. Results are `PASS|FAIL|INCONCLUSIVE`; targets are never reported as measured results until an EvalRun exists.

## Mandatory suites

RAG: Recall@10, MRR, citation precision, ACL/effective-date/tenant negatives. Analytics: semantic correctness and unauthorized query rate. RCA: Top-1/Top-3 and unsupported claim rate. ML: baseline comparison, time leakage, calibration/PR-AUC/Brier. Uplift: Qini and slices. Causal: effect error, overlap, sensitivity/refutation. Agent: schema, tool-policy, injection, budget and recovery. Every suite has fixed fixtures/hidden holdout where relevant and a declared rerun trigger.

## Interpretation

An evaluation is comparable only when dataset, split, metric and artifact versions match. A failure blocks the declared use case; an inconclusive result is not a pass. Reports disclose limitation, sample/slice, confidence where meaningful, and target-versus-measured status. Evaluation payloads obey tenant/data-governance policy and do not contain reusable credentials.

## Traceability

`NFR-AI-001..007`, `INV-DATA-001`, `INV-AI-001..002`.
