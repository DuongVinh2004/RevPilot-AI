# Canonical Future Repository Topology

Status: Accepted v1.0
Owner: Principal Architecture  
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Date: 2026-09-04
Important: This document defines future paths. It does not authorize creating application source or infrastructure.

## Topology

```text
RevPilot AI/
├── apps/
│   ├── api/                         # FastAPI composition and HTTP adapters
│   ├── web/                         # Next.js Experience Plane
│   ├── workflow-worker/             # Temporal worker composition
│   ├── ingestion-worker/            # connector ingestion composition
│   └── ml-worker/                   # offline/async ML composition
├── packages/
│   ├── backend/
│   │   ├── src/revpilot/
│   │   │   ├── shared/              # minimal stable primitives/ports
│   │   │   └── modules/             # modular-monolith domain modules
│   │   └── tests/
│   ├── contracts/                   # JSON Schema/OpenAPI/event/tool schemas
│   └── web-client/                  # generated API client source definition
├── tests/
│   ├── contract/
│   ├── integration/
│   ├── e2e/
│   ├── security/
│   ├── tenancy/
│   ├── recovery/
│   ├── performance/
│   └── ai-evals/
├── config/
│   ├── schemas/                     # validated non-secret configuration schemas
│   └── examples/                    # safe placeholder-only examples
├── infra/
│   ├── local/                       # local composition declarations
│   ├── environments/                # deployment definitions after provider ADR
│   └── policies/                    # machine-enforced deployment/security policy
├── scripts/                         # bounded developer/CI commands
├── generated/                       # reproducible output; never authoritative input
├── docs/                            # canonical product/architecture specifications
├── execution/                       # roadmap, rails, queues, traceability
└── tasks/                           # one-file task packets
```

## Top-level ownership and dependency rules

| Area | Purpose | Owner | Allowed dependencies | Prohibited dependencies |
|---|---|---|---|---|
| `apps/api` | HTTP composition, middleware, routing, dependency injection | API Platform | backend application ports, contracts, telemetry bootstrap | domain logic in controllers; provider SDKs; direct tables of another module |
| `apps/web` | dashboards, investigation/evidence/approval UX | Experience | generated web client, UI libraries | database/provider credentials; hidden chain-of-thought; direct external enterprise APIs |
| `apps/workflow-worker` | register Temporal workflows/activities and adapters | Execution | backend workflow/application ports, Temporal SDK | business state only in worker memory; direct Agent/provider credentials |
| `apps/ingestion-worker` | schedule and compose source ingestion | Data Platform | connector/data ports, contracts | business actions; cross-tenant batching without enforced isolation |
| `apps/ml-worker` | train/evaluate/batch-score approved artifacts | ML Platform | ML/data/eval ports, contracts | silent production promotion; future/as-of leakage |
| `packages/backend` | canonical modular-monolith domain/application/infrastructure code | Backend Architecture | Python runtime and ADR-approved adapters | imports from any `apps/*`; frontend code |
| `packages/contracts` | versioned API/event/tool/config schemas | Platform Contracts | schema tooling only | business implementation or secrets |
| `packages/web-client` | client generated from accepted API contracts | Experience/API | contracts/generator | hand-authored business rules or server authority |
| `tests` | cross-component verification/evals | Quality owners | public interfaces and approved test fixtures | production secrets or destructive production targets |
| `config` | schemas and safe examples | Platform | contracts | credentials, tenant/customer data, environment secrets |
| `infra` | declared local/production infrastructure after task authorization | Platform/SRE | approved deployment/ADR contracts | application business logic; premature unapproved systems |
| `scripts` | exact non-destructive automation entry points | Developer Platform | public build/test tools | hidden architecture changes, secret access, destructive cleanup |
| `generated` | reproducible derived artifacts | Producing pipeline | declared source manifests | hand edits; authority over source schemas/specs |
| `docs` | canonical design intent | Architecture/Product | source references for evidence only | runtime side effects |
| `execution` | planning gates and status | Planning/Architecture | canonical docs/tasks | implementation authority outside queue |
| `tasks` | exact work packets | Planning/Architecture | accepted spec anchors | redefining architecture/contracts |

## Backend module shape

Each module lives at `packages/backend/src/revpilot/modules/<module>/` with:

```text
domain/          # entities, value objects, invariants, domain events
application/     # use cases and orchestration through ports
ports/           # published inbound/outbound interfaces and DTOs
infrastructure/  # adapters owned by this module
tests/           # module-local unit/contract tests when colocated policy permits
```

Domain may import only its own domain and `revpilot.shared` primitives. Application may import its own domain/ports and explicitly allowed published ports. Infrastructure implements ports and may use approved SDKs. Composition occurs in `apps/*`; modules never import app entry points.

## Shared-kernel limits

`packages/backend/src/revpilot/shared/` may contain only stable opaque IDs, Tenant/Principal context value references, UTC/time abstractions, Money/currency primitives, result/error primitives, correlation metadata, and cross-cutting port contracts. It cannot contain business entities, repositories, provider clients, mutable global state, or convenience utilities tied to one module.

## Configuration and secrets

Only configuration schemas and non-secret examples belong in Git. Local/production secret values are injected through ADR-0009 mechanisms. Generated secrets, credentials, customer datasets, model provider payloads, and local environment files are prohibited from repository paths.

## Generated artifacts

Every item under `generated/` identifies its source schema/tool/version and reproducible command. Generated output cannot override `packages/contracts`, accepted docs, or source. CI verifies regeneration drift before accepting a task that changes source contracts.

## Bootstrap gate

Application paths above may be created only after this topology and ADR-0001 are Accepted, Rail 0 prerequisites identify exact toolchain versions, and a one-file bootstrap micro-task enters the executor queue. Until then, they remain documentation-only paths.

