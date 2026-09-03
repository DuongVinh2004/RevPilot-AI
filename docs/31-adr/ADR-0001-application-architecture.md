# ADR-0001 — Application Architecture

Status: Accepted  
Date: 2026-09-03  
Owner: Principal Architecture  
Approver: Dương Vinh

## Context

RevPilot requires strong module, tenant, action, and workflow boundaries but begins with one product/team and INITIAL COMMERCIAL assumptions of 25 tenants and 20 concurrent investigations. A microservices-first design would add deployment, schema, event, tracing, and failure coordination before independent ownership or scaling is proven.

## Decision

Use a typed modular monolith for product API, application services, domain modules, and control logic. Deploy Temporal workers, ingestion jobs, and ML/inference workloads separately only where runtime, scaling, security, or failure characteristics require it. Modules interact through published ports/events and cannot read another module's tables directly.

## Decision Drivers

Small initial team; transactional consistency; zero-guessing task paths; lower operational cost; explicit future extraction seams; `RISK-008`.

## Alternatives

- Microservices-first: rejected because current ownership/load does not justify distributed coordination.
- Single unmodularized application: rejected because it cannot preserve domain/data/security boundaries.
- Serverless function-per-capability: rejected because long workflows, local composition, and shared contracts become fragmented.

## Why Selected

It minimizes accidental distributed complexity while preserving service extraction through stable application ports, events, and data ownership.

## Pros

Atomic local transactions, simpler development/testing, reviewable boundaries, lower baseline cost.

## Cons

Requires automated dependency enforcement; some workloads still need separate processes; careless modules can become tightly coupled.

## Consequences

Repository topology must make module ownership visible. Independent deployables use contracts rather than shared table access. Network separation is not assumed to provide logical isolation.

## Risks

Boundary erosion and whole-application scaling. Mitigate with dependency tests, module ownership, per-module telemetry, and extraction-ready ports.

## Security Impact

Central authorization is simpler, but module-local authorization and tenant enforcement remain mandatory. The Action/Tool Gateway boundary may be a separate deployable for stronger isolation.

## Tenancy Impact

Shared application processes are allowed; every data/capability boundary still enforces Tenant context independently.

## Operational Impact

Fewer deployables initially; workers scale separately. One monolith release requires strong regression/canary gates.

## Cost Impact

Lower platform/operational cost than microservices-first; later extraction has migration cost.

## Implementation Implications

Use application/domain/infrastructure layering, explicit module APIs, transactional outbox, and architecture tests. Do not create one service per Agent.

## Revisit Triggers

Re-evaluate extraction for a module only when at least one is sustained/approved: its resource profile forces scaling the whole API by >2x for three 7-day windows; it causes >20% of Sev-1/2 failure blast radius in a quarter; security requires an independently enforced network/runtime boundary; a separate owning team with independent release cadence exists; or deployment frequency/SLO conflict is evidenced for three release cycles. Extraction still requires its own ADR.

## Affected Requirements

`FR-INV-001..003`, `FR-ACT-001`, `FR-CTL-001`, `NFR-REL-001`, `SEC-001..003`.

## Affected Specs

System architecture, repository topology, module boundaries, dependency rules, deployment architecture.
