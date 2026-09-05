# ADR-0003 — Agent Orchestration Boundary

Status: Accepted  
Date: 2026-09-03  
Owner: AI Platform Architecture  
Approver: Dương Vinh
Version: v1.0

## Context

RevPilot needs dynamic typed reasoning DAGs, parallel read-only investigation, critique, budgets, and structured evidence. It must not allow an Agent framework to own business durability, authorization, credentials, approval, or side effects.

## Decision

Use LangGraph behind a RevPilot-owned typed `AgentRuntime` port for bounded reasoning subgraphs. Temporal Activities invoke the port. The runtime receives immutable task scope, approved capability catalog, evidence references, model budget, and deadlines; it returns versioned typed results. It cannot receive reusable credentials, perform external side effects, approve actions, or own multi-day workflow state.

## Decision Drivers

Dynamic DAG support, trace/eval integration, framework containment, replacement seam, `FR-INV-001..004`, `SEC-002..004`.

## Alternatives

- Direct LangGraph types across the application: rejected due framework coupling.
- Custom DAG engine now: rejected because it duplicates orchestration capabilities before gaps are measured.
- One agent per microservice: rejected because roles are logical capabilities, not deployment boundaries.

## Why Selected

It accelerates reasoning-graph work while keeping business/security contracts owned by RevPilot.

## Pros

Graph composition, parallel nodes, bounded framework integration, replaceable adapter.

## Cons

Framework learning/version risk; duplicate checkpoint concepts; adapter maintenance.

## Consequences

All Agent schemas, allowed/denied Tools, budgets, retries, escalation, and evaluation are declared outside prompts. Agent checkpoint data is non-authoritative and disposable/reconstructable from durable state plus evidence references.

## Risks

Framework leakage or hidden side effects. Mitigate with dependency rules, capability adapters, schema validation, and forbidden-import tests.

## Security Impact

Agent output is untrusted. Authorization and tenant context are injected by trusted adapters and re-enforced by every called capability.

## Tenancy Impact

Agent state and traces are Tenant-scoped; cross-tenant memory/training is forbidden by default.

## Operational Impact

AgentRuntime version, graph, prompts, model usage, Tool calls, latency, and cost are observable under the Investigation trace.

## Cost Impact

Framework reduces initial build cost; the port limits later replacement cost.

## Implementation Implications

No module imports provider/LangGraph types outside the AI infrastructure adapter. No Agent directly imports external connector clients.

## Revisit Triggers

Replace or narrow LangGraph if two consecutive release cycles cannot enforce required structured schemas/replay compatibility; framework overhead consumes >20% of p95 Agent Activity latency for three windows; critical tracing/budget/tool-policy gaps remain after adapter mitigation; or upgrade cadence causes repeated production gate failures. A custom runtime requires a superseding ADR.

## Affected Requirements

`FR-INV-001..004`, `FR-RCA-001..002`, `NFR-AI-001`, `SEC-002..004`.

## Affected Specs

AI architecture, multi-agent spec, Temporal workflow, evaluation, model provider abstraction, dependency rules.
