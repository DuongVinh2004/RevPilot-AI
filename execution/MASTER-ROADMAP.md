# RevPilot AI Master Roadmap

Status: Accepted v1.0 — Phase 00–08 specifications complete; Rails 0–5 GREEN; Rails 6–18 LOCKED (947/947 tests pass); Phase 08 documentation closure complete (`DOCUMENTATION COMPLETE / VALIDATION PENDING / GO-LIVE BLOCKED`).

Execution is governed by `execution/MICRO-TASK-RAIL-SYSTEM.md`. The phases below are planning containers, not tasks. Each phase is decomposed as `EPIC -> FEATURE -> MICRO-TASK`; only admitted micro-tasks may be sent to Antigravity.

## Delivery policy

Each phase is an end-to-end, testable increment. A later phase may be specified in parallel but cannot implement against an unaccepted upstream contract. No real side effects are enabled before Phase 06 safety gates. Each phase must update requirements, ADRs, threat model, traceability, risk register, and measured benchmark results.

## Phase 00 — Architecture and engineering foundation (P0)

Objective: freeze product boundaries, canonical vocabulary, requirements, architecture, security invariants, and executable delivery conventions.

Scope/deliverables: Foundation Pack, all mandatory detailed specifications, ADR set, API/event/database contracts, synthetic dataset specification, repository scaffold plan, task DAG, threat/failure analysis.

Dependencies: none. Data migrations: none. Tests/evals: document lint, link/ID/traceability consistency, Mermaid validation, architecture red-team review. Exit: no orphan P0 requirement; all proposed technologies have accepted/deferred ADR; unresolved blockers have owners and dates. Risk: architecture astronomy; mitigation is a mandatory “why now/revisit trigger” for every component.

## Phase 01 — Canonical data and synthetic benchmark (P0)

Objective: produce reproducible business data and ground truth.

Scope: tenant-aware canonical schema, metric registry, deterministic generator profiles, raw/normalized zones, injected causal incidents, data quality/lineage, benchmark manifest. Dependencies: Phase 00 contracts. Migration: initial schema. Tests: deterministic seed, referential/time consistency, tenant-negative tests, leakage/time-travel checks. Exit: baseline and scale datasets reproduce with hashes; ground truth is hidden from investigation runtime.

## Phase 02 — Detect and analytics (P0)

Objective: detect and localize revenue anomalies without an LLM dependency.

Scope: baselines, STL/change-point/Isolation Forest benchmark, metric service, drill-down analytics, anomaly lifecycle. Dependencies: Phase 01. Tests/evals: rolling time-split backtest, false-positive/lead-time measures, SQL semantics, late-event replay. Exit: selected detector beats or justifiably matches baseline and produces calibrated, reproducible anomaly records.

## Phase 03 — Governed evidence and investigation (P0)

Objective: create durable, bounded investigation DAGs over structured and unstructured evidence.

Scope: Temporal workflows, agent runtime, SQL capability catalog, hybrid RAG, ticket intelligence, evidence/provenance model, read-only policy. Dependencies: Phases 01–02. Tests/evals: crash/replay, prompt injection, SQL correctness, Recall@K/MRR/citation, effective-date and ACL tests. Exit: known incident evidence is retrieved without tenant/policy leak; recovery creates no duplicate task effect.

## Phase 04 — Hypothesis, causal analysis, and verification (P2)

Objective: rank competing causes and distinguish evidence, association, and causal estimates.

Scope: hypothesis schema, verifier, causal estimands, DoWhy/EconML benchmark, sensitivity/overlap checks, `NEED_MORE_EVIDENCE`. Dependencies: Phase 03 and benchmark ground truth. Tests/evals: RCA top-k, causal effect error, counterfactual fixtures, unsupported-claim rate. Exit: injected cause is ranked against alternatives and uncertainty/limitations are explicit.

## Phase 05 — Churn, uplift, and decision optimization (P2)

Objective: recommend actions based on incremental value and constraints.

Scope: calibrated churn, SHAP, uplift learners, expected-utility optimizer, policy eligibility, budget simulation. Dependencies: Phase 01 outcomes plus Phase 04. Tests/evals: PR-AUC/calibration/Brier, Qini/uplift, optimizer property tests, fairness/slice review. Exit: decision is reproducible, constraint-valid, and discloses uncertainty; churn risk is not substituted for uplift.

## Phase 06 — Approval and safe action loop (P1)

Objective: add governed approval, mock first and then explicitly enabled real adapters.

Scope: approval center, digest binding, dry-run, idempotency, blast radius, kill switches, action ledger, Saga, outcome measurement. Dependencies: Phases 03 and 05; IAM/policy/tool contracts accepted. Tests: replay/tamper, crash-at-every-step, unknown provider result, compensation, authority matrix, kill switches. Exit: no unauthorized/duplicate test actions; production adapter remains disabled until operational approval.

## Phase 07 — Multi-tenant pilot and connectors (P1)

Objective: support controlled commercial pilots.

Scope: OIDC then SAML/SCIM, tenant lifecycle, secrets/keys, connector lifecycle, CDC/event platform if ADR trigger met, quotas/metering, audit, data governance. Dependencies: Phase 06. Tests: full isolation matrix, OAuth expiry/revocation, schema drift, webhook replay, deletion/export, metering reconciliation. Exit: pilot tenant provisioning and recovery rehearsed; no P0 security finding.

## Phase 08 — Production readiness (P1/P3)

Objective: meet defined SLO, security, DR, release, billing, and operational gates.

Scope: observability, AI release gates, canary/rollback, backup/restore, DR, load/chaos, billing ledger, compliance evidence, runbooks. Kubernetes/dedicated serving only if ADR triggers are met. Exit: `execution/DEFINITION-OF-DONE.md` production checklist passes with measured evidence.

## Future v2

Broader RevOps scenarios, contextual model routing, dedicated regulated isolation/regions, larger streaming scale, and continuous policy learning. No future phase grants unbounded autonomy.
