# Business Domain Model

Status: Accepted Canonical Specification  
Owner: Domain Architecture Lead  
Approver: Dương Vinh  
Version: v1.0  
Date: 2026-09-04  

## Revision History

| Version | Date | Author | Reviewer | Approval | Summary of Changes |
|---|---|---|---|---|---|
| v0.1 | 2026-09-04 | Domain Architecture | Principal Architect | Dương Vinh | Initial business domain bounded contexts |


## Bounded contexts

| Context | Owns | Does not own |
|---|---|---|
| Tenant & Identity | tenant, user, role, delegated authority | CRM customer identity truth |
| Revenue Ledger | normalized revenue events and metric definitions | external accounting ledger |
| Customer 360 | canonical customer references and segment attributes | source-system master mutation |
| Fulfillment | order/shipment/warehouse/carrier signals | WMS operational control |
| Service Intelligence | tickets, topics, sentiment, issue taxonomy | source CRM ticket workflow |
| Contract Intelligence | versioned contracts, SLA/policy clauses | legal interpretation authority |
| Investigation | plan, task graph, hypothesis, evidence, decision | source data ownership |
| Intervention | approval, action, compensation, outcome | unrestricted external credentials |
| Model Governance | model/prompt/index/policy versions and eval status | raw business records |
| Usage & Billing | metered consumption, invoice inputs, COGS | payment-card storage |

## Core aggregates and invariants

### Anomaly

Root: `Anomaly`. Represents a validated statistical departure of a canonical business metric from its historical baseline. Contains immutable observation and baseline windows, actual vs expected values, prediction intervals, anomaly score, severity, affected dimensional scope, and data quality state. Governed by `docs/02-domain/ANOMALY-DOMAIN-SPEC.md`.

States: `DETECTED -> VALIDATED -> LOCALIZED -> ACKNOWLEDGED -> RESOLVED`, with `SUPPRESSED` and `REOPENED` paths.

Invariant: An anomaly record provides statistical evidence of divergence; it DOES NOT assert a root cause or causal claim (`INV-AI-001`).

### Investigation

Root: `Investigation`. Contains immutable scope snapshot, metric definition version, task graph version, hypotheses, evidence references, decision, and lifecycle state. Every child belongs to one tenant. Evidence references are immutable; corrected evidence creates a new version.

States: `DETECTED -> PLANNING -> INVESTIGATING -> VERIFYING -> DECIDING -> AWAITING_APPROVAL -> EXECUTING -> MEASURING -> CLOSED`, with terminal `CANCELLED`, `FAILED_SAFE`, and `REJECTED` paths. Transitions require recorded actor, reason, timestamp, and correlation ID.

### Recommendation

A ranked, non-executable proposal containing target cohort, action type, parameters, expected utility distribution, assumptions, policy evaluation, model versions, expiry, and evidence set. Changing any executable field invalidates prior approval.

### Action

An immutable intent plus execution attempts. Uniqueness is enforced by `(tenant_id, idempotency_key)`. External outcome is reconciled rather than inferred from network response alone. Irreversible actions require explicit classification and follow-up compensation behavior.

### Approval

Binds approver authority and decision to `recommendation_version + action_digest + target_digest + max_cost + expiry`. Amendment creates a new recommendation version; it is not an in-place edit.

### Outcome

Observation of post-intervention behavior at a defined horizon. Outcomes retain treatment assignment, eligibility, propensity/model version, and censoring information so evaluation does not confuse association with treatment effect.

## Canonical entities

Every tenant-owned entity includes `tenant_id`, source lineage, source-system ID, canonical ID, schema version, effective time, ingestion time, and data classification.

```text
Tenant 1---* User/ServicePrincipal/AgentDelegation
Tenant 1---* Customer 1---* Order 1---* Shipment
Customer 1---* Ticket
Customer 1---* Contract 1---* ContractClause
Order 1---* Payment
Warehouse 1---* Shipment
Warehouse 1---* OperationalEvent
Anomaly 1---* AnomalyLocalization
Anomaly 1---0..1 Investigation
Investigation *---* EvidenceRef
Investigation 1---* Hypothesis
Investigation 1---* Recommendation 1---* Approval
Recommendation 1---* Action 1---* ActionAttempt
Action 1---* Outcome
ModelVersion/PromptVersion/PolicyVersion/RagSnapshot --- Investigation
```

## Time semantics

- `event_time`: when the business event occurred.
- `effective_from/to`: when a contract/policy/model definition applies.
- `ingested_at`: when RevPilot observed it.
- `recorded_at`: when RevPilot persisted it.

Investigations declare an `as_of` timestamp. Queries must not use future information relative to that timestamp during benchmark/backtest runs.

## Metric semantics

Metrics are versioned data contracts. For example, cancellation rate defines numerator status set, denominator eligibility, event timestamp, timezone, exclusions, late-arrival policy, and aggregation dimensions. A natural-language request never invents a metric; it resolves to a registered definition or asks for clarification.

## Causal vocabulary

- Exposure/treatment: intervention or operational condition being evaluated.
- Outcome: cancellation, retained revenue, repeat order, or another registered measure.
- Confounders: pre-treatment attributes affecting exposure and outcome.
- Mediator: post-treatment variable on the causal pathway; not blindly controlled.
- Estimand: ATE, ATT, CATE, or policy value.

Every causal claim includes estimand, cohort, time window, assumptions, overlap checks, uncertainty interval, sensitivity analysis, and limitations.
