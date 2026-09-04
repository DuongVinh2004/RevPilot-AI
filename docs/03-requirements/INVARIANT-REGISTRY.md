# Foundational Invariant Registry

Status: Accepted v1.0
Owner: Principal Architecture
Approver: Duong Vinh (Explicit user confirmation covering Repository Owner, Principal Architecture, Security Architecture/IAM, SRE)
Date: 2026-09-04
Approval record: execution/APPROVAL-RECORD-RUN-R03-001.md
Evidence rule: Entries are design obligations. “Future test/evidence” does not claim implementation exists.

| ID | Owner | Invariant and rationale | Violation impact | Enforcement point | Future test/evidence |
|---|---|---|---|---|---|
| `INV-TEN-001` | Tenancy + Data | Every tenant-owned persistent/derived record has enforceable Tenant ownership; a query filter alone is insufficient. | Critical cross-tenant breach | RLS/composite keys plus store/index/event/object policies | Cross-store Tenant A/B negative matrix |
| `INV-TEN-002` | Identity + API | Tenant context is server-derived from authenticated membership and cannot be supplied/overridden by model or payload. | Confused deputy/cross-tenant access | Trusted resolver and typed context | Missing/malformed/mismatch tests fail closed |
| `INV-TEN-003` | Control Plane | A global/platform operation uses an explicit privileged context, never `tenant = null`. | Hidden authorization bypass | Separate role/policy path and immutable audit | Null-tenant rejection and break-glass tests |
| `INV-IAM-001` | Identity | Authorization is deny-by-default and server-side at every sensitive capability boundary. | Unauthorized read/write/action | RBAC/ABAC policy enforcement | Permission matrix positive/negative tests |
| `INV-IAM-002` | Identity + AI | Delegated Agent Identity is tenant/task/time scoped and cannot exceed its delegating Principal. | Privilege escalation | Delegation issuer + capability authorization | Scope/expiry/escalation negative tests |
| `INV-SEC-001` | Security | Agent Runtime never receives reusable connector/model/enterprise credentials. | Secret exfiltration/persistent provider compromise | Credential Broker and adapter boundary | Context/log scan and forbidden-dependency tests |
| `INV-SEC-002` | Security + AI | Documents, tickets, websites, model/tool output are untrusted content and cannot grant authority or override Policy. | Prompt/tool injection | Taint/schema validation and deterministic authorization | Indirect-injection adversarial suite |
| `INV-SEC-003` | Platform | External destinations and Tool schemas are registered/versioned; model-controlled arbitrary egress is forbidden. | SSRF/data exfiltration | Tool registry, egress allowlist, DNS/IP validation | SSRF/registry tamper contract tests |
| `INV-ACT-001` | Actions | No external side effect occurs outside Policy -> required Approval -> Tool Gateway -> Action Ledger. | Unauthorized/untracked business harm | Network/dependency boundary and gateway | Forbidden-import/egress plus end-to-end tests |
| `INV-ACT-002` | Actions | Every side effect is idempotent or explicitly reconciled; `UNKNOWN` is never retried blindly. | Duplicate financial/customer action | Unique ledger key and provider reconciliation | Timeout-after-accept crash/retry suite |
| `INV-ACT-003` | Product Risk | Approval binds exact action/target/cost/policy/version/expiry digest; mutation/replay invalidates it. | Approval bypass/blast expansion | Approval and Gateway revalidation | Tamper/expiry/replay tests |
| `INV-ACT-004` | Actions + Risk | Dry-run, hard blast limits, budgets, and independent kill switches precede real adapters. | Mass unintended action | Gateway/action policy | Cap/kill/dry-run negative tests |
| `INV-WF-001` | Execution | Long-lived Business Workflow state is durable outside ephemeral app/Agent memory. | Lost/duplicated investigations/actions | Temporal history plus product aggregate state | Worker/process loss replay tests |
| `INV-WF-002` | Execution | Workflow code is deterministic; model/network/database/clock/random work occurs in Activities. | Replay failure/state corruption | Workflow review and replay test | Historical replay compatibility suite |
| `INV-AI-001` | AI/ML | LLM statements are not verified statistical/causal facts; conclusions require typed evidence/evaluation. | Incorrect business action | Verifier, statistical/causal services, release gates | Unsupported-claim/RCA/causal evals |
| `INV-AI-002` | AI Platform | Every model/prompt/agent graph/tool schema/dataset/index/policy used by an Investigation is immutably version-referenced. | Non-reproducible decisions | Artifact registry and Investigation manifest | Replay/manifest completeness test |
| `INV-EVD-001` | Evidence | Evidence includes provenance, Tenant/ACL, effective/event/as-of time, classification, version, and digest. | Stale/unauthorized/unverifiable decision | Evidence service | Missing-field/ACL/effective-date tests |
| `INV-EVD-002` | Evidence + RAG | Superseded or unauthorized source content cannot support a Recommendation. | Policy/SLA hallucination | Retrieval filters and citation verifier | Supersession/citation negative suite |
| `INV-DATA-001` | Data | Metric semantics and `as_of` are versioned; training/backtests cannot use future information. | Data leakage/false benchmark | Metric/dataset manifests | Time-leakage and split tests |
| `INV-DATA-002` | Data | Source systems remain authoritative; derived stores are rebuildable projections. | Divergent business truth | Lineage/reconciliation | Projection rebuild/hash reconciliation |
| `INV-AUD-001` | Audit | Every security/policy/approval/action/privileged change has a minimized immutable audit event. | Unprovable action/nonrepudiation gap | Audit append/integrity boundary | Required-event and chain verification tests |
| `INV-AUD-002` | Audit + Privacy | Immutable audit is not a raw prompt/PII/secret archive. | Permanent sensitive-data exposure | Allowlisted event schema and encrypted evidence reference | DLP/redaction schema tests |
| `INV-COST-001` | FinOps | Tenant/investigation/model/tool budgets and loop limits are enforced before further spend. | Runaway cost/denial of service | Model/Tool Gateway and workflow budget state | Budget boundary and concurrent race tests |
| `INV-PRV-001` | Privacy | Data collection, context, logs, and exports are purpose-limited and minimized. | Privacy/contract breach | Classification/masking/retention policy | Field inventory, DLP, deletion/export tests |
| `INV-REL-001` | SRE | IAM/Policy/Audit uncertainty fails closed for writes; degraded reads are explicit and cannot authorize action. | Unsafe action during dependency failure | API/Workflow/Gateway failure policy | Dependency outage matrix |
| `INV-REL-002` | SRE | No rail/dependent task proceeds while required verification is RED/FAIL/BLOCKED. | Compounded defects and invalid evidence | Rail/queue control plane | Task graph/status consistency validation |

## Mapping to existing security objectives

| Objective | Invariants |
|---|---|
| `SEC-001` | `INV-TEN-001..003` |
| `SEC-002` | `INV-IAM-002`, `INV-SEC-001` |
| `SEC-003` | `INV-IAM-001..002`, `INV-ACT-001` |
| `SEC-004` | `INV-SEC-002..003`, `INV-EVD-002` |
| `SEC-005` | `INV-ACT-003` |
| `SEC-006` | `INV-ACT-002` |
| `SEC-007` | `INV-REL-001` |
| `SEC-008` | `INV-AI-002` |
| `SEC-009` | `INV-AUD-001..002`, `INV-PRV-001` |
| `SEC-010` | `INV-ACT-004` |

Invariants cannot be disabled through feature flags or lower-precedence task text. Change requires security/architecture review and an accepted superseding artifact.

