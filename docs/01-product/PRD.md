# Product Requirements Document

Status: Proposed v0.1

## Problem

Revenue incidents are investigated manually across sales, support, fulfillment, payment, and contract systems. Analysts spend hours collecting data, conclusions are difficult to reproduce, interventions are often based on churn probability rather than incremental treatment effect, and action/audit controls live outside the analytical workflow.

## Product promise

Given a revenue signal or analyst question, RevPilot creates a bounded investigation, gathers only authorized evidence, evaluates competing hypotheses, recommends a policy-compliant action with expected economics, requests approval when required, and records measurable outcomes.

## Product boundaries

### In scope

- Revenue anomaly, cancellation, churn, failed payment, delayed fulfillment, SLA violation, and revenue-at-risk investigations.
- Structured analytics, ticket intelligence, governed document retrieval, forecasting, causal/uplift analysis, decision optimization, approval, controlled execution, and outcome measurement.
- Synthetic benchmark data followed by explicitly configured enterprise connectors.
- Tiered tenant isolation, delegated agent identity, action budgets, evidence/audit lineage, and reproducible versions.

### Out of scope for MVP

- Autonomous financial transfers or contract modification.
- Sending external communications to real customers.
- General-purpose enterprise assistant behavior.
- Training foundation models or exposing hidden chain-of-thought.
- Claims of legal/compliance certification.
- Multi-region active-active architecture without measured need.

## Primary journeys

### J-01 Proactive anomaly investigation

1. A scheduled detector compares cancellation rate with a historical baseline.
2. A validated anomaly opens an investigation with tenant, metric, period, segments, and evidence snapshot.
3. The planner creates a typed DAG within time/tool/cost budgets.
4. authorized analytics and retrieval nodes execute in parallel.
5. The verifier ranks hypotheses and identifies missing evidence.
6. The decision engine computes eligible interventions and expected utility.
7. The policy engine determines approval tier.
8. MVP ends with a dry-run; later releases execute through the Tool Gateway.

### J-02 Analyst-initiated investigation

An analyst asks why cancellations increased. The system resolves the business metric and scope, presents its interpretation for confirmation if materially ambiguous, then follows J-01 from step 3.

### J-03 Approval and action

The approver sees affected customers, cost ceiling, expected benefit interval, evidence, policy checks, expiry, and compensations. Approve/reject/amend signals resume the durable workflow. Execution revalidates policy and data freshness before any side effect.

## Functional epics

| Epic | Requirements | MVP | Production v1 |
|---|---|---:|---:|
| Detect | `FR-DET-001..006` | Yes | Yes |
| Investigate | `FR-INV-001..012` | Yes | Yes |
| Evidence/RAG | `FR-EVD-001..010` | Yes | Yes |
| ML/Causal | `FR-ML-001..014` | Baseline | Full gates |
| Decide | `FR-DEC-001..009` | Dry-run | Governed actions |
| Approve/Act | `FR-ACT-001..015` | Mock adapter | Real adapters |
| Learn | `FR-LRN-001..006` | Outcome capture | Retraining gates |
| Tenant/Control | `FR-CTL-001..018` | Single-tenant-compatible | Multi-tenant |

## MVP acceptance narrative

Using a deterministic seed, generate orders, shipments, tickets, maintenance events, and contract/SLA documents. Inject a truck-capacity incident whose causal window and affected scope are known. The system must detect the cancellation anomaly, rank the injected incident as the leading root-cause hypothesis with cited evidence, reject at least two plausible alternatives as insufficiently supported, propose an eligible intervention, show a dry-run and approval request, and reproduce the result from versioned inputs. Exact metric thresholds are defined before model implementation and actual results are reported separately.

## Product constraints

- All business data access carries tenant and authorization context.
- LLM output is untrusted until schema-validated and policy-checked.
- No direct agent credentials and no direct agent-to-external-system calls.
- Approval is bound to exact action payload, version, cost, target set, and expiration.
- Recommendations disclose uncertainty and evidence limitations.
- Outcome learning never silently promotes a model or policy to production.

## Open product decisions

- Initial commercial vertical after synthetic benchmark: e-commerce fulfillment or B2B subscription revenue.
- Currency/timezone localization and region hierarchy.
- Which interventions may ever qualify as low-risk auto-actions.
- Retention periods and regulated-tier residency markets.

