# Decision Intelligence Contract

Status: Proposed v0.1 — E02 specification output

## Deterministic decision boundary

Decision Intelligence owns versioned `Recommendation` and `Decision` records. It ranks only candidates that have authorized tenant scope, cited evidence, eligible policy result and required validated predictive/uplift/causal inputs. Generative text explains an already computed result and cannot change rank, eligibility, constraints or authority.

## Optimization contract

`DecisionRequest` supplies candidate actions, expected retained-revenue inputs, intervention cost, risk penalty, policy penalty, budget, hard constraints, artifact/evidence references and as-of time. The engine first removes ineligible candidates, then optimizes declared utility under budget, blast-radius and policy constraints. Output includes ordered candidates, objective decomposition, constraint results, uncertainty/limitations, fallback reason, and immutable decision digest.

## Failure and lifecycle

When confidence, calibration, uplift/causal eligibility, evidence, or policy is insufficient, output `NO_DECISION` or `REQUIRES_REVIEW`; never substitute correlation or churn for incremental value. `DRAFT -> EVALUATED -> DECIDED -> SUPERSEDED` preserves history. An approved action binds the exact decision digest; actions are separately governed by Policy/Approval/Tool Gateway.

## Traceability

`INV-AI-001`, `INV-ACT-003..004`, `NFR-AI-005..007`, `NFR-COST-001`.
