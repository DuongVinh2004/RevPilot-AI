# Modular-Monolith Module Boundary Map

Status: Accepted v1.0
Owner: Principal Architecture
Approver: Duong Vinh (Explicit user confirmation covering Repository Owner, Principal Architecture, Security Architecture/IAM, SRE)
Date: 2026-09-04
Approval record: execution/APPROVAL-RECORD-RUN-R03-001.md
Decision basis: ADR-0001 and ADR-0003

Logical modules are not automatically runtime services. Each module owns its model and exposes ports; infrastructure adapters remain replaceable.

## Module map

| Module/path suffix | Responsibility | Owns data | Public interface | Allowed module dependencies | Forbidden dependencies | Produces / consumes | Extraction trigger |
|---|---|---|---|---|---|---|---|
| `tenancy` | Tenant/Organization lifecycle, entitlement and trusted Tenant context contract | Tenant, Organization, Entitlement | `TenantQueryPort`, `TenantContextPolicy` | shared only; identity through application port for admin actor check | provider SDKs, business modules | tenant lifecycle / usage-billing consumers | dedicated provisioning/region lifecycle needs isolation |
| `identity` | Principal, membership, role/permission/delegation semantics | PrincipalRef, Membership, Role, Delegation | `PrincipalContextPort`, `AuthorizationPort` | tenancy query port | business tables, Agent output as claims | identity/delegation / policy, approval, admin | independent IdP/security boundary or high auth load |
| `investigations` | Investigation aggregate, Run, state, plan/task references | Investigation, Run, HypothesisRef, DecisionRef | `InvestigationCommandPort`, `InvestigationQueryPort` | evidence, analytics, retrieval, ML, decisions through ports | connector SDKs, provider secrets, direct action execution | investigation lifecycle / workflow, UI, audit | dominant scale or independent product ownership |
| `evidence` | Evidence/EvidenceBundle provenance, version, access and sufficiency contract | EvidenceRef, EvidenceBundle | `EvidenceCommandPort`, `EvidenceQueryPort` | tenancy/identity policy ports | raw connector clients, decision/action mutation | evidence events / investigations, retrieval, analytics | separately scaled evidence graph/storage |
| `analytics` | Registered metric queries, drill-downs, anomaly results | MetricDefinition, AnalysisResult | `AnalyticsPort` | evidence publish port, governed data ports | unrestricted SQL, actions | analysis evidence / investigations | heavy compute/query isolation required |
| `retrieval` | Document/chunk/index projection and governed hybrid retrieval | DocumentRef, DocumentVersion, ChunkProjection, IndexManifest | `RetrievalPort`, `IndexAdminPort` | evidence, tenancy/identity policy ports | action/approval, provider auth | retrieval evidence/index events / investigations | ADR-0006 triggers or independent index operations |
| `ml` | Model/dataset/feature manifests, training/eval/serving results | ModelArtifact, DatasetManifest, FeatureDefinition, Prediction | `ModelInferencePort`, `ModelGovernancePort` | evidence/data governance ports | production promotion without release gate | prediction/eval / investigations, decisions | GPU/runtime/release isolation |
| `decisions` | Expected utility, constraints, ranked Recommendations/Decisions | Recommendation, Decision | `DecisionPort` | evidence, ML outputs, policy eligibility query | approval authority, external action | decision/recommendation / investigation, policy | high-volume optimizer or separate risk ownership |
| `policy` | Deterministic policy evaluation and risk tier | PolicyVersion, PolicyDecision | `PolicyEvaluationPort` | identity/tenancy context, recommendation DTO | LLM as authority, credentials | policy decision / approvals, actions | strong independent security/runtime boundary |
| `approvals` | Approval request, authority check, digest binding, expiry/amendment | ApprovalRequest, Approval | `ApprovalCommandPort`, `ApprovalQueryPort` | identity, tenancy, policy, action-intent digest ports | modifying recommendation/action payload | approval events / Temporal, actions, audit | compliance/scale/ownership boundary |
| `actions` | Tool Gateway, Action/Attempt ledger, dry-run, blast limit, reconciliation, compensation | Action, ActionAttempt, ActionLedger, KillSwitch | `ActionCommandPort`, `ActionQueryPort`, `ToolGatewayPort` | approval, policy, identity/tenancy, connector capability ports | Agent framework, direct unapproved provider call | action lifecycle / outcomes, audit, usage | security blast-radius or independent scale |
| `connectors` | Provider registration, auth reference, sync state, webhook/CDC and provider adapters | Connector, CredentialRef, SyncCursor, ProviderCapability | `ConnectorReadPort`, `ConnectorCapabilityPort` | tenancy, secret/egress ports | exposing credential value, decision authority | source records/sync health / data, actions | provider-specific workload/team or egress isolation |
| `audit` | Immutable minimized audit event and integrity verification | AuditEvent, IntegrityCheckpoint | `AuditAppendPort`, `AuditQueryPort` | identity/tenancy references | raw prompt/secret logging, business decision | audit integrity / security/admin | WORM/compliance isolation |
| `usage` | Metering and cost attribution | UsageRecord, CostAllocation | `UsageRecordPort`, `UsageQueryPort` | tenancy references, artifact IDs | changing business outcomes or invoice totals | usage events / billing, FinOps | high-volume event/analytics isolation |
| `billing` | Plans, billable aggregation, invoice ledger integration | Plan, Subscription, BillingRecord, CreditLedger | `BillingPort` | usage, tenancy entitlement ports | payment card storage, model decisions | billing events / admin | commercial finance ownership/provider boundary |
| `administration` | Admin use cases over published control ports | AdminOperationRef only | `AdminCommandPort` | tenancy, identity, connector, model, audit, billing public ports | direct table/secret access, bypass policy | admin audit / UI | separate control-plane team/runtime |

## Orchestration ownership

The `investigations` application layer coordinates read capabilities, but Temporal owns durable sequencing. It must not import infrastructure adapters. `actions` owns side-effect safety; `connectors` owns provider mechanics; neither Agent Runtime nor `investigations` may bypass them.

## Data ownership rules

- Exactly one module owns writes for each aggregate/table.
- Another module obtains data through a published query/command port or subscribed projection.
- Cross-module foreign-key references use stable IDs; they do not authorize cross-module writes.
- Reporting projections may join governed copies but cannot mutate source aggregates or grant authority.
- A database transaction crossing module ownership requires an explicit application contract and ADR review; default is prohibited.

## Shared dependencies

All modules may use the minimal shared kernel, configuration ports, structured telemetry ports, and standard library. No module may use a global service locator, mutable Tenant singleton, raw credential accessor, or provider client not owned by its infrastructure adapter.

## Runtime extraction policy

Extraction is evaluated per ADR-0001. Moving code to a network service does not change data, security, tenant, idempotency, or contract semantics. An extraction plan must define API/event compatibility, data migration, failure behavior, observability, ownership, cost, and rollback.

