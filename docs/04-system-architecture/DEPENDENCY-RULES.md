# Architectural Dependency Rules

Status: Accepted v1.0
Owner: Principal Architecture
Approver: Duong Vinh (Explicit user confirmation covering Repository Owner, Principal Architecture, Security Architecture/IAM, SRE)
Date: 2026-09-04
Version: v1.0
Approval record: execution/APPROVAL-RECORD-RUN-R03-001.md

Undefined dependency edges are forbidden until specified.

## Layer direction

```text
apps/composition -> infrastructure adapters -> application -> domain
                                      ports <- application/domain
shared primitives may be imported by domain, application, ports, infrastructure
```

| From | May depend on | Must not depend on |
|---|---|---|
| Domain | own domain, approved shared primitives | application, infrastructure, apps, framework/provider SDKs |
| Application | own domain/ports, explicitly published foreign module ports, shared | foreign infrastructure/tables, apps, provider SDKs |
| Ports/contracts | domain-safe DTO/value types and shared | infrastructure/provider/framework implementation types |
| Infrastructure | ports it implements, own application/domain, approved SDK | another module's infrastructure/private tables |
| App composition | public module ports and infrastructure factories | implement domain business rules or bypass ports |
| Web | generated API client and UI contracts | backend/domain/database/provider credentials |

## Cross-module rules

1. Write ownership is exclusive; no direct cross-module table mutation.
2. Queries use a published port or purpose-built authorized projection; raw unrestricted SQL is forbidden.
3. Synchronous calls must follow the allowed module map and cannot form a cycle.
4. Asynchronous integration uses versioned domain/integration events and idempotent consumers.
5. Domain modules do not depend on Temporal, LangGraph, HTTP, ORM, vector/search, LLM, connector, or telemetry backend SDKs.
6. Temporal workflow definitions coordinate application contracts; nondeterministic work remains in Activities.
7. Agent Runtime sees capability ports and typed results, never connector clients, credentials, Policy mutation, Approval authority, or Action executors.
8. External provider calls originate only in the owning infrastructure adapter; side effects additionally require the Actions/Tool Gateway path.

## Mandatory forbidden edges

- `agents/reasoning -> connector provider SDK`: FORBIDDEN.
- `agents/reasoning -> secrets/credential provider`: FORBIDDEN.
- `controller/route -> domain persistence`: FORBIDDEN; use application use case.
- `module A -> module B infrastructure/private table`: FORBIDDEN.
- `request payload -> TenantContext/authorization`: FORBIDDEN; use verified identity mapping.
- `feature flag -> disable authorization/audit/tenant/idempotency`: FORBIDDEN.
- `generated artifact -> canonical source/spec override`: FORBIDDEN.
- `operational telemetry -> raw credentials/chain-of-thought`: FORBIDDEN.

## Tenant and identity propagation

Tenant/Principal context is an immutable typed input created at the trusted API/workflow boundary. Repositories and capability ports require it explicitly where tenant-owned data is accessed. Global/platform operations use separate typed context and authorization, never a null Tenant.

## Transaction and event boundary

A module transaction mutates only aggregates it owns and writes its outbox record atomically. Cross-module outcomes use orchestrated calls or events with compensation; distributed transactions are not inferred. Consumers reauthorize, deduplicate, and do not trust event payload Tenant fields without transport/store enforcement.

## Future enforcement

| Rule class | Machine-verifiable evidence after bootstrap |
|---|---|
| Layer/import direction | Python import architecture test and TypeScript dependency rule |
| Module cycles | dependency graph cycle check |
| Provider SDK containment | forbidden-import allowlist test |
| Cross-module persistence | repository ownership/static import test plus integration review |
| Tenant requirement | type/signature tests and negative integration suite |
| No secrets/unsafe logs | secret/DLP scanning and structured-log schema tests |
| Task write boundary | Git changed-path comparison against task WRITE_SET |

Exact enforcement tools are selected in repository/toolchain specifications; absence of tooling does not weaken the rule.

