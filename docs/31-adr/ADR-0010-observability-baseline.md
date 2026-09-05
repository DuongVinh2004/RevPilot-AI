# ADR-0010 — Observability Baseline

Status: Accepted  
Date: 2026-09-03  
Owner: SRE + AI Platform Architecture  
Approver: Dương Vinh
Version: v1.0

## Context

An Investigation spans API, Temporal, Agent Runtime, retrieval, model, SQL/ML, policy, approval, Tool Gateway, and providers. Debugging, cost allocation, audit, and AI evaluation require shared correlation without exposing PII, secrets, or hidden chain-of-thought.

## Decision

Use OpenTelemetry APIs/semantic conventions and a vendor-neutral Collector boundary for traces, metrics, and structured logs. All stages carry Tenant-safe correlation, causation, Investigation, Run, task, artifact version, and cost metadata. Operational telemetry is separate from immutable audit and AI evaluation records. Prompts/evidence/credentials/chain-of-thought are not logged by default.

## Decision Drivers

`NFR-OBS-001`, `NFR-COST-001`, `NFR-PRV-001`, cross-plane diagnosis, vendor portability.

## Alternatives

- Direct vendor SDK throughout code: rejected due coupling/inconsistent semantics.
- Logs only: rejected because workflow/distributed latency and causality are lost.
- Store full prompts/traces: rejected due privacy/secret/chain-of-thought risk.

## Why Selected

OpenTelemetry provides one instrumentation boundary while allowing local and managed backends to evolve.

## Pros

End-to-end traceability, backend choice, consistent cost/latency attribution.

## Cons

Schema/cardinality/sampling governance required; telemetry pipeline has cost and failure modes.

## Consequences

Each component defines low-cardinality metrics and structured events. Security/audit events are not probabilistically sampled. Sensitive payload inspection uses separately authorized encrypted evidence access.

## Risks

High-cardinality cost, PII leakage, missing spans, telemetry outage. Mitigate with attribute allowlist, redaction, contract tests, bounded buffering, health alerts.

## Security Impact

Credential values and raw PII are prohibited. Tenant identifiers use approved opaque IDs. Logs cannot grant authority.

## Tenancy Impact

Telemetry access is Tenant/role-scoped; shared backend queries enforce Tenant and platform-operator separation.

## Operational Impact

Minimum signals include API/workflow/activity/model/tool latency/error, queue/approval/outbox lag, cost, policy decisions, action outcomes, and guardrail activations.

## Cost Impact

Sampling/retention/cardinality budgets are explicit; audit-required events are budgeted separately.

## Implementation Implications

Instrumentation uses shared semantic contracts, not backend-specific SDK calls in domain code. Local backend selection is deferred to observability spec.

## Revisit Triggers

Select/change telemetry backend when INITIAL COMMERCIAL deployment is chosen; monthly telemetry COGS exceeds 10% of platform COGS for two months; query/retention/SLO requirements fail for three windows; or regulated tenant isolation/residency cannot be enforced. Instrumentation standard remains OpenTelemetry unless a superseding ADR proves incompatibility.

## Affected Requirements

`NFR-OBS-001`, `NFR-COST-001`, `NFR-PRV-001`, `FR-CTL-002`, `SEC-009`.

## Affected Specs

Observability, audit, FinOps, AI evaluation, SRE, every API/event/workflow contract.
