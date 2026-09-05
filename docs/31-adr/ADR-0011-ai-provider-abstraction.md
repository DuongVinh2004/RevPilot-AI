# ADR-0011 — AI Provider Abstraction

Status: Accepted  
Date: 2026-09-03  
Owner: AI Platform Architecture  
Approver: Dương Vinh  
Version: v1.0

## Context

RevPilot may use hosted and later local models. Provider APIs differ in structured output, context, tool semantics, retention, regional processing, errors, usage, and cost. A universal lowest-common-denominator layer would hide capabilities; direct SDK coupling would spread provider choices across agents.

## Decision

Create a small RevPilot-owned Model Gateway port with provider adapters. The port declares normalized request identity, model/capability requirement, structured output schema, deadline, data classification/region policy, token/cost budget, and trace context; response declares validated content, provider/model/version, usage/cost, finish/error classification, and safety metadata. Provider-specific optional capabilities use explicit adapter capability declarations, not opaque leakage. Tests use a deterministic fake. Production provider is `UNKNOWN` until deployment/security/evaluation review.

## Decision Drivers

Replaceability, deterministic tests, cost/privacy governance, provider capability differences, `NFR-AI-001`, `NFR-COST-001`, `SEC-004`.

## Alternatives

- Direct provider SDKs in agents: rejected due coupling and inconsistent policy/telemetry.
- External universal model proxy as sole abstraction: deferred; it adds operations and may not own RevPilot policy.
- Lowest-common-denominator mega-interface: rejected because it hides meaningful capability/quality differences.

## Why Selected

The narrow port centralizes cross-cutting governance while preserving explicit capabilities and a low-cost provider migration seam.

## Pros

Deterministic fake, uniform budgets/errors/telemetry, localized provider change, policy enforcement.

## Cons

Adapter maintenance; provider-specific behavior still requires tests; production provider remains a blocker for its adapter.

## Consequences

Agent specifications request capabilities, not model brand. Routing does not grant Tool authority. A provider adapter task cannot start until retention/residency/security/eval/cost terms are accepted.

## Risks

Leaky abstraction, unsafe retries, silent output downgrade. Mitigate with capability negotiation, schema validation, error taxonomy, conformance/eval suites.

## Security Impact

Gateway minimizes/transforms sensitive input under policy and prohibits secrets. Provider output is untrusted.

## Tenancy Impact

Budgets, residency, provider eligibility, usage, and logs are Tenant-scoped; provider batching cannot mix tenant content unless explicitly proven safe and approved.

## Operational Impact

Track provider/model/version, latency, error class, rate limit, tokens, estimated/actual cost, fallback and quality gate.

## Cost Impact

Central attribution/routing enables cost controls; extra gateway hop is accepted and measured.

## Implementation Implications

Provider SDK types remain in adapters. No dynamic provider fallback occurs unless the task's data policy, capability, evaluation, and budget permit it.

## Revisit Triggers

Evaluate an external gateway when at least three production providers/local runtimes are active, adapter policy/telemetry duplication exceeds two release cycles, or centralized batching/caching yields >=20% validated cost/latency improvement without quality/privacy regression. Evaluate local serving when hosted provider cannot satisfy signed residency/privacy/availability needs or validated volume shows >=25% total-cost improvement including GPU/SRE cost and quality gates.

## Affected Requirements

`FR-INV-001`, `FR-RCA-001..002`, `NFR-AI-001`, `NFR-COST-001`, `NFR-PRV-001`, `SEC-004`.

## Affected Specs

AI architecture, multi-agent, model release, FinOps, observability, security, deployment.
