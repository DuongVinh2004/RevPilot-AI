# Functional Requirement Closure Catalog

Status: Proposed v0.2 — content complete, approval pending  
Owner: Product Architecture & Domain Leads  
Approval required: Product Owner and Principal Architecture  
Scope: Resolves the PRD-to-SRS coverage gap for IDs planned in `PRD.md` but previously absent from `SRS.md`.  
Traceability: `PRD.md` §Functional epics, `SRS.md` §Business and functional requirements, `NFR-BASELINE.md`, `TEST-STRATEGY.md`

> [!CAUTION]
> This is a requirements-closure artifact, not implementation authorization. Every verification entry below is planned evidence until its referenced implementation and test exist and execute. No row is a test-pass claim.

## Lifecycle rule

All rows below are `PROPOSED / IMPLEMENTATION PENDING`. A row may enter implementation only after its acceptance criteria, owning specification, executable task, and test path are approved through the canonical governance process.

| ID | P | Requirement | Planned acceptance / evidence | Owner | Design traceability |
|---|---:|---|---|---|---|
| `FR-DET-004` | P1 | Persist detection lineage, feature version, baseline and threshold used for every anomaly. | Reproducibility fixture; design-only until executed. | Analytics Lead | ANOMALY-DOMAIN-SPEC, METRIC-REGISTRY |
| `FR-DET-005` | P1 | Quarantine detections with stale, incomplete, or schema-drifted inputs. | Data-quality negative fixture. | Data Lead | DATA-QUALITY-LINEAGE-SPEC |
| `FR-DET-006` | P2 | Expose detector confidence and known limitations without claiming causality. | Explanation contract review. | Analytics/AI Lead | ANOMALY-LOCALIZATION-SPEC |
| `FR-INV-005` | P0 | Enforce investigation-level time, tool-call, and cost budgets. | Budget-boundary test. | Workflow/FinOps Lead | MULTI-AGENT-SPEC, BUDGET-CONSTRAINT-SPEC |
| `FR-INV-006` | P0 | Require trusted tenant and principal context for every investigation node. | Cross-tenant negative test. | IAM/Tenancy Lead | MULTI-TENANCY-SPEC, IAM-SPEC |
| `FR-INV-007` | P1 | Record deterministic node inputs, outputs, retries, and dependency state. | Replay contract test. | Workflow Lead | TEMPORAL-WORKFLOW-SPEC |
| `FR-INV-008` | P1 | Surface partial completion, blocked dependencies, and degraded reads to users. | State-transition test. | Workflow/Frontend Lead | TEMPORAL-WORKFLOW-SPEC, FRONTEND-SPEC |
| `FR-INV-009` | P1 | Require explicit cancellation semantics that preserve audit and evidence lineage. | Cancellation/recovery test. | Workflow Lead | TEMPORAL-WORKFLOW-SPEC, AUDIT-LOG-SPEC |
| `FR-INV-010` | P2 | Allow approved human amendments while invalidating affected downstream plans. | Amendment invalidation test. | Product/Workflow Lead | APPROVAL-ACTION-LOOP-SPEC |
| `FR-INV-011` | P1 | Prevent unbounded recursive planning and tool fan-out. | Depth/fan-out limit test. | Agent Platform Lead | MULTI-AGENT-SPEC |
| `FR-INV-012` | P1 | Preserve correlation, causation, and artifact-version references across nodes. | Trace contract test. | SRE/Workflow Lead | OPERATIONS-TELEMETRY-SPEC |
| `FR-EVD-004` | P0 | Enforce tenant and ACL checks before evidence retrieval or caching. | A/B negative retrieval test. | Evidence/Security Lead | EVIDENCE-PROVENANCE-SPEC |
| `FR-EVD-005` | P1 | Preserve source digest, parser version, chunk offsets, and extraction lineage. | Evidence schema test. | Evidence Lead | EVIDENCE-PROVENANCE-SPEC |
| `FR-EVD-006` | P1 | Prevent raw secrets and disallowed PII from entering evidence storage or embeddings. | DLP/redaction test. | Privacy Lead | EVIDENCE-PROVENANCE-SPEC, DATA-GOVERNANCE |
| `FR-EVD-007` | P1 | Support point-in-time retrieval using effective, expiry, and supersession state. | Effective-date boundary test. | Evidence Lead | EVIDENCE-PROVENANCE-SPEC |
| `FR-EVD-008` | P1 | Return machine-verifiable citations for every evidence-grounded claim. | Citation span verifier test. | RAG/Verifier Lead | RAG-SPEC, HYPOTHESIS-VERIFIER-SPEC |
| `FR-EVD-009` | P2 | Quarantine malformed, tampered, or unsupported evidence records. | Tamper/quarantine test. | Evidence/Security Lead | EVIDENCE-PROVENANCE-SPEC |
| `FR-EVD-010` | P2 | Enforce retention, legal-hold, export, and deletion state on evidence. | Governance workflow test. | Data Governance Lead | DATA-GOVERNANCE |
| `FR-ML-005` | P1 | Use time-aware splits and leakage controls for predictive evaluation. | Time-split evaluation. | ML Lead | ML-SYSTEM-SPEC |
| `FR-ML-006` | P1 | Track model, feature, dataset, and calibration versions with each score. | Manifest validation test. | ML Lead | ML-SYSTEM-SPEC |
| `FR-ML-007` | P1 | Detect drift and block unsafe score use when calibration degrades. | Drift/calibration gate. | ML Lead | ML-SYSTEM-SPEC |
| `FR-ML-008` | P2 | Report uncertainty and confidence intervals with causal estimates. | Causal benchmark review. | Causal/ML Lead | CAUSAL-INFERENCE-SPEC |
| `FR-ML-009` | P2 | Require overlap and sensitivity diagnostics before using treatment-effect estimates. | Causal gate test. | Causal/ML Lead | CAUSAL-INFERENCE-SPEC |
| `FR-ML-010` | P2 | Keep churn prediction distinct from uplift and causal eligibility. | Misuse negative test. | ML/Product Lead | ML-SYSTEM-SPEC, UPLIFT-BENCHMARK-PROTOCOL |
| `FR-ML-011` | P2 | Evaluate fairness and performance slices before release. | Slice-evaluation report. | ML/Product Lead | FAIRNESS-SLICE-EVALUATION |
| `FR-ML-012` | P1 | Reject unversioned or unapproved model artifacts. | Registry gate test. | AI Governance Lead | MODEL-RELEASE-PROCESS |
| `FR-ML-013` | P2 | Support rollback to a prior approved model/prompt/policy bundle. | Rollback contract test. | AI Governance Lead | MODEL-RELEASE-PROCESS |
| `FR-ML-014` | P2 | Record outcome feedback without silently promoting a model or policy. | Release-policy test. | ML/Product Lead | AI-GOVERNANCE |
| `FR-DEC-002` | P0 | Reject decisions when evidence freshness, ACL, or provenance is insufficient. | Decision denial test. | Decision/Evidence Lead | DECISION-ENGINE-SPEC |
| `FR-DEC-003` | P0 | Enforce hard spend, risk, policy, and blast-radius constraints. | Deterministic policy test. | Decision/FinOps Lead | BUDGET-CONSTRAINT-SPEC |
| `FR-DEC-004` | P1 | Explain utility inputs, constraints, uncertainty, and rejected alternatives. | Explanation contract review. | Decision/Product Lead | DECISION-ENGINE-SPEC |
| `FR-DEC-005` | P1 | Require human confirmation when policy tier demands approval. | Approval routing test. | Actions/IAM Lead | IAM-SPEC, APPROVAL-ACTION-LOOP-SPEC |
| `FR-DEC-006` | P1 | Produce dry-run plans when execution eligibility is absent. | Dry-run contract test. | Decision/Actions Lead | APPROVAL-ACTION-LOOP-SPEC |
| `FR-DEC-007` | P2 | Detect conflicting policies and fail closed rather than choosing arbitrarily. | Policy-conflict negative test. | IAM/Policy Lead | IAM-SPEC |
| `FR-DEC-008` | P1 | Bind a recommendation to evidence, model, policy and dataset versions. | Decision manifest test. | AI Governance Lead | MODEL-RELEASE-PROCESS |
| `FR-DEC-009` | P2 | Record decision outcomes for post-hoc calibration and governance review. | Outcome audit test. | Product/FinOps Lead | AUDIT-LOG-SPEC |
| `FR-ACT-005` | P0 | Validate approval, payload digest, target set, policy and freshness immediately before dispatch. | Pre-dispatch tamper test. | Actions/IAM Lead | APPROVAL-ACTION-LOOP-SPEC |
| `FR-ACT-006` | P0 | Use short-lived scoped credentials only through the Credential Broker. | Credential boundary test. | Security/Tool Gateway Lead | SECURITY-ARCHITECTURE, TOOL-GATEWAY-SPEC |
| `FR-ACT-007` | P0 | Deny direct agent egress to external systems. | Egress-wall test. | Security/Platform Lead | TOOL-GATEWAY-SPEC |
| `FR-ACT-008` | P1 | Persist append-only action intent, attempt and reconciliation records. | Ledger immutability test. | Actions/Audit Lead | APPROVAL-ACTION-LOOP-SPEC, AUDIT-LOG-SPEC |
| `FR-ACT-009` | P1 | Mark uncertain external outcomes `UNKNOWN` and reconcile before retry. | Timeout reconciliation test. | Actions/Workflow Lead | APPROVAL-ACTION-LOOP-SPEC |
| `FR-ACT-010` | P1 | Apply tenant, capability and global kill switches fail closed. | Kill-switch propagation test. | SRE/Actions Lead | APPROVAL-ACTION-LOOP-SPEC |
| `FR-ACT-011` | P1 | Require provider-specific idempotency and replay protection. | Provider adapter contract test. | Connector Lead | CONNECTOR-PLATFORM-SPEC |
| `FR-ACT-012` | P1 | Use compensation only where reversibility is declared and verified. | Saga compensation test. | Workflow/Actions Lead | APPROVAL-ACTION-LOOP-SPEC |
| `FR-ACT-013` | P2 | Escalate irreversible or high-blast-radius actions to a human operator. | Tier-routing test. | Product/Actions Lead | IAM-SPEC |
| `FR-ACT-014` | P1 | Emit complete policy, approval and action audit events. | Audit completeness test. | Audit/Security Lead | AUDIT-LOG-SPEC |
| `FR-ACT-015` | P2 | Provide operator reconciliation queues for unresolved provider outcomes. | Queue/reconciliation test. | Operations Lead | APPROVAL-ACTION-LOOP-SPEC |
| `FR-LRN-003` | P1 | Separate observational outcomes from causal treatment labels. | Data lineage test. | ML/Data Lead | CAUSAL-INFERENCE-SPEC |
| `FR-LRN-004` | P2 | Detect outcome-label delay, drift and missingness before learning. | Data-quality test. | ML/Data Lead | DATA-QUALITY-LINEAGE-SPEC |
| `FR-LRN-005` | P2 | Require policy approval before a learned recommendation policy changes. | Governance gate test. | AI Governance Lead | AI-GOVERNANCE |
| `FR-LRN-006` | P2 | Retain outcome lineage for audit, deletion and legal hold. | Governance propagation test. | Data Governance Lead | DATA-GOVERNANCE |
| `FR-CTL-004` | P0 | Authenticate all principals from verified claims; reject fabricated contexts. | Authentication negative test. | IAM Lead | IAM-SPEC |
| `FR-CTL-005` | P0 | Authorize every sensitive tenant lifecycle and context operation. | Service authorization test. | IAM/Tenancy Lead | IAM-SPEC, TENANT-OPERATIONS-SPEC |
| `FR-CTL-006` | P0 | Revalidate tenant and principal state at sensitive boundaries. | Suspension/revocation test. | IAM/Tenancy Lead | MULTI-TENANCY-SPEC |
| `FR-CTL-007` | P0 | Make privileged system context opaque, verified, scoped and auditable. | Privileged-context test. | Security/IAM Lead | SECURITY-ARCHITECTURE |
| `FR-CTL-008` | P0 | Enforce database row-level isolation and safe session binding. | PostgreSQL RLS concurrency test. | Database/Tenancy Lead | DATABASE-SCHEMA |
| `FR-CTL-009` | P1 | Prevent tenant resource ID overwrite and enforce idempotent provisioning. | Duplicate-ID conflict test. | Tenancy Lead | TENANT-OPERATIONS-SPEC |
| `FR-CTL-010` | P1 | Issue revocable, expiring execution contexts. | Session/context invalidation test. | IAM/Tenancy Lead | IAM-SPEC |
| `FR-CTL-011` | P1 | Maintain organization, tenant, entitlement and lifecycle invariants through immutable boundaries. | Aggregate integrity test. | Tenancy Lead | MULTI-TENANCY-SPEC |
| `FR-CTL-012` | P1 | Require export/delete/hold workflows to preserve legal and audit state. | Delete/legal-hold test. | Privacy/Data Lead | DATA-GOVERNANCE |
| `FR-CTL-013` | P1 | Audit privileged operations and access-review decisions without raw secrets or PII. | Audit redaction test. | Security/Privacy Lead | AUDIT-LOG-SPEC |
| `FR-CTL-014` | P1 | Apply data retention and residency policy only after legal configuration is known. | Configuration gate test. | Compliance Lead | COMPLIANCE-READINESS |
| `FR-CTL-015` | P1 | Make security control availability fail closed for writes. | Dependency-outage test. | Security/SRE Lead | NFR-REL-002 |
| `FR-CTL-016` | P2 | Preserve evidence and audit lineage during tenant suspension and deactivation. | Lifecycle lineage test. | Tenancy/Audit Lead | TENANT-OPERATIONS-SPEC |
| `FR-CTL-017` | P2 | Report tenant-scoped cost, usage and quota status without cross-tenant aggregation leakage. | Metering isolation test. | FinOps/Tenancy Lead | FINOPS-SPEC |
| `FR-CTL-018` | P1 | Block commercial onboarding when mandatory legal, security or evidence controls remain unknown. | Onboarding gate test. | Compliance/Platform Lead | COMPLIANCE-READINESS, PILOT-ONBOARDING-AND-RECOVERY-SPEC |

## Approval disposition

This catalog removes the content gap, but not approval or implementation dependencies. Until the named owners and approvers accept the affected foundation documents, all rows remain `PROPOSED / IMPLEMENTATION PENDING / NOT EXECUTED`.
