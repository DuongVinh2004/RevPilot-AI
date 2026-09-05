# Canonical Glossary

Status: Accepted v1.0
Owner: Principal Architecture
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Date: 2026-09-04
Normative rule: Capitalized terms below have these meanings across RevPilot specifications. A local document may specialize but not contradict them.

## Identity and tenancy

### Tenant

The RevPilot security, ownership, billing, policy, and data-isolation boundary contracted to one customer. A Tenant is not merely a query filter; enforcement spans every store, event, cache, index, model artifact, log, export, tool, and workflow.

### Organization

A business hierarchy inside one Tenant, such as a legal entity, division, region, or department. Organization never substitutes for Tenant and cannot cross the Tenant boundary.

### Actor

Anything that initiates or participates in an operation: human, service, agent, connector, scheduler, or platform operator. Actor describes behavior; Principal describes authenticated identity.

### Principal

An identity authenticated by a trusted identity mechanism and used for authorization. Principal types are User, Service Principal, Platform Operator, and temporary Delegated Agent Identity.

### User

A human Principal belonging to one or more authorized Organizations within exactly one active Tenant context per request.

### Service Principal

A non-human workload identity with explicit, non-interactive permissions. It is not an Agent and must not inherit human approval authority implicitly.

### Agent

A versioned AI runtime role that transforms typed inputs into typed plans, evidence assessments, hypotheses, or recommendations under budgets and allowed tools. An Agent is untrusted for authorization and has no inherent business authority.

### Delegated Agent Identity

A short-lived, tenant-bound Principal representing a subset of an initiating Principal's permissions for one workflow/task scope. It cannot exceed the delegator, persist beyond its expiry, or hold reusable connector credentials.

## Investigation and evidence

### Investigation

The tenant-owned business aggregate that records an immutable question/scope, metric and as-of semantics, evidence, hypotheses, decision, approvals, actions, outcomes, and artifact versions.

### Investigation Run

One execution attempt/version of an Investigation plan. Retries and revised plans create traceable run/attempt records; they do not silently rewrite prior history.

### Hypothesis

A falsifiable candidate explanation with supporting evidence, contradicting evidence, assumptions, confidence basis, and verification status. It is not a verified causal fact.

### Evidence

An immutable reference to an authorized, versioned source observation with provenance, tenant, access policy, effective/event/as-of time, classification, and integrity digest.

### Evidence Bundle

A versioned set of Evidence references assembled for a specific hypothesis or decision. It contains references and evaluation metadata, not unrestricted copies of source data.

## Decision and action

### Decision

The versioned result of applying evidence, models, constraints, policy, and economics to select or reject candidate Recommendations. A Decision is not permission to execute.

### Recommendation

A non-executable proposed intervention containing target cohort, action parameters, expected-utility distribution, assumptions, policy result, evidence bundle, versions, expiry, and cost ceiling.

### Approval

An immutable authorization decision by an eligible Principal, bound to the exact Recommendation version, action digest, target digest, maximum cost, policy version, and expiry. Amendment requires a new Recommendation and Approval.

### Action

An immutable, tenant-owned intent to cause a side effect through the authorized Execution Plane. An Action has a stable idempotency key and one or more Action Attempts.

### Action Attempt

One provider invocation/reconciliation attempt for an Action. Its outcome is `CONFIRMED`, `FAILED`, or `UNKNOWN`; `UNKNOWN` must not be retried blindly.

### Intervention

The business treatment represented by one or more approved Actions and assigned to an eligible cohort. It carries treatment assignment and evaluation metadata.

### Outcome

A post-intervention business observation at a defined horizon, such as retained revenue or repeat order, with attribution inputs, censoring, and artifact versions.

## Integration and control

### Connector

A tenant-configured integration that ingests from or exposes approved capabilities of an external system. It owns provider lifecycle concerns but does not grant an Agent direct credential access.

### Tool

A versioned, typed capability registered with the Tool Gateway. Tool availability is not authorization; every invocation is separately authenticated, authorized, policy-checked, bounded, and audited.

### Policy

A versioned deterministic rule set producing `ALLOW`, `DENY`, or `REQUIRE_APPROVAL` plus reasons and constraints. LLM content cannot create or override Policy.

### Business Workflow

A durable, replayable sequence owned by Temporal, including timers, retries, signals, approvals, compensation, cancellation, and version history. It is not an Agent Graph.

### Agent Graph

A bounded, versioned reasoning DAG executed by the Agent Runtime within Business Workflow activities. It plans/selects allowed read capabilities and produces typed results; it does not own multi-day durability or side effects.

## Versioned artifacts

### Model Version

An immutable identifier and manifest for a trained or hosted model configuration, including provider/model ID, parameters, artifact/dataset references, evaluation, and release state.

### Prompt Version

An immutable content-addressed prompt/template/schema bundle. Prompt Version never contains secrets or grants authority.

### Agent Version

An immutable composition of Agent responsibility, graph, Prompt Versions, Model capability requirements, allowed/denied Tools, budgets, and evaluation release state.

### Dataset Version

An immutable manifest of data snapshots/splits, lineage, schema, time boundary, exclusions, hashes, and intended use. It prevents training/evaluation time leakage.

### RAG Index Version

An immutable logical snapshot manifest covering source Document Versions, parser/chunker/embedding versions, metadata/ACL policy, and index build identity. The physical index may be rebuilt from the manifest.

### Policy Version

An immutable released Policy bundle and test manifest. A Recommendation and Approval reference the exact Policy Version evaluated.

### Tool Schema Version

An immutable Tool input/output/error and side-effect contract. A schema change follows compatibility and approval rules; the Agent cannot invent fields.

## Naming rules

- Use `Tenant` only for the top isolation/billing boundary; use `Organization` for internal hierarchy.
- Use `Principal` for authenticated authorization subjects and `Actor` for behavioral participants.
- Use `Business Workflow` for Temporal durability and `Agent Graph` for bounded reasoning.
- Use `Recommendation` for proposals, `Decision` for ranked selection, `Approval` for authority, and `Action` for executable intent.
- “Confidence” without its method is prohibited. Use calibrated probability, statistical interval, retrieval score, verifier assessment, or explicitly qualitative confidence.
- “Rollback” is prohibited for irreversible external effects; use compensation and reconciliation.

