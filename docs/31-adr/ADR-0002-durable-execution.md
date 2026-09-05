# ADR-0002 — Durable Execution

Status: Accepted  
Date: 2026-09-03  
Owner: Execution Architecture  
Approver: Dương Vinh
Version: v1.0

## Context

Investigations may run for minutes, wait for approval for days, retry transient activities, compensate partial actions, and resume after worker/process loss. Ephemeral process memory and agent checkpointing alone cannot be the authoritative business workflow history.

## Decision

Temporal owns durable Business Workflow state, timers, retry scheduling, signals, queries, cancellation, child workflows, versioning, and compensation coordination. Model calls, database access, network calls, clock/randomness, and Tool calls execute in Activities. LangGraph/Agent Runtime runs only bounded reasoning subgraphs inside Activities and returns typed results.

## Decision Drivers

`FR-INV-003`, `NFR-REL-001`, multi-day approval, deterministic replay, duplicate-action prevention, observable recovery.

## Alternatives

- Database state machine plus custom workers: viable but rejected because it recreates durable scheduling/replay/versioning.
- Queue-only orchestration: rejected because queues do not define long-lived business state or approval signals.
- LangGraph persistence as outer workflow: rejected because it conflates reasoning checkpoints with business durability/action coordination.

## Why Selected

Temporal matches the required interruption, timer, signal, replay, and recovery semantics while isolating nondeterminism in Activities.

## Pros

Durable histories, explicit timeouts/retries, deterministic recovery, visibility into waiting workflows.

## Cons

Operational dependency, deterministic-code constraints, history/version management, developer learning cost.

## Consequences

Workflow code must be deterministic and versioned. Activities must be idempotent/reconcilable. PostgreSQL remains authoritative for product aggregates; Temporal history is authoritative for workflow progression.

## Risks

History growth, nondeterministic replay, unsafe Activity retry. Mitigate with child/continue-as-new policy, replay tests, and task-specific retry classes.

## Security Impact

Workflow inputs reference sensitive data rather than copying unrestricted payloads. Signals require authenticated tenant/authority validation at the application boundary.

## Tenancy Impact

Workflow IDs include Tenant and Investigation IDs; search attributes/logs are minimized and access-controlled.

## Operational Impact

Requires supported Temporal environment, workers, visibility, backup/DR ownership, and replay compatibility tests.

## Cost Impact

Adds service/operations cost but removes a large custom durability implementation and reduces recovery incidents.

## Implementation Implications

Canonical workflow ID: `tenant/{tenantId}/investigation/{investigationId}`. Detailed Activity, Signal, Query, timeout, retry, cancellation, and compensation contracts belong in the workflow spec.

## Revisit Triggers

Re-evaluate only if an approved deployment cannot meet Temporal operational/data-residency requirements; validated replay/history limits prevent required workflows after documented mitigations; or a replacement proves all required timers/signals/replay/versioning/recovery semantics at lower total operational risk. Preference or agent-framework features alone are insufficient.

## Affected Requirements

`FR-INV-001..003`, `FR-ACT-002..004`, `NFR-REL-001..002`, `SEC-005..007`.

## Affected Specs

Temporal workflow, multi-agent, approval, action safety, SRE, DR, observability.
