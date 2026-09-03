# Phase 00 — Legacy Specification Planning Objects

Status: SUPERSEDED by `execution/SPECIFICATION-QUEUE.md` and future one-file documentation micro-tasks. The IDs below are retained and must never be reused. These objects are EPIC-sized, are not implementation-ready, and must never enter `execution/EXECUTOR-QUEUE.md` or be sent directly to Antigravity.

## DAG

```text
RP-P00-T001
├──> RP-P00-T002
├──> RP-P00-T003
└──> RP-P00-T004

RP-P00-T002 + T003 + T004
└──> RP-P00-T005
```

## RP-P00-T001

**TITLE:** Freeze architecture decisions and workload assumptions  
**OBJECTIVE:** Convert every proposed technology/boundary in the Foundation Pack into an accepted or deferred ADR with measurable revisit triggers.  
**BUSINESS RATIONALE:** Prevent implementation from silently selecting expensive infrastructure or changing safety semantics.  
**ARCHITECTURAL CONTEXT:** Five-plane architecture; modular monolith plus justified workers; Temporal outer workflow.  
**DEPENDENCIES:** Foundation Pack v0.1.  
**PRECONDITIONS:** Product owner identifies initial vertical, MVP time/team/budget envelope, and target deployment environment.  
**FILES / MODULES EXPECTED:** Historical expectation normalized to the canonical E01 ADR set: `docs/31-adr/ADR-0001-application-architecture.md`, `docs/31-adr/ADR-0002-durable-execution.md`, `docs/31-adr/ADR-0003-agent-orchestration-boundary.md`, `docs/31-adr/ADR-0004-primary-relational-persistence.md`, `docs/31-adr/ADR-0005-tenant-isolation.md`, `docs/31-adr/ADR-0006-retrieval-baseline.md`, `docs/31-adr/ADR-0007-messaging-event-baseline.md`, `docs/31-adr/ADR-0008-deployment-baseline.md`, `docs/31-adr/ADR-0009-secrets-and-keys.md`, `docs/31-adr/ADR-0010-observability-baseline.md`, `docs/31-adr/ADR-0011-ai-provider-abstraction.md`, and `docs/04-system-architecture/SYSTEM-ARCHITECTURE.md`.  
**DATA MODEL:** No schema change; define workload/capacity assumptions used by later schemas.  
**API CONTRACT:** None; record API style/versioning decision.  
**EVENT CONTRACT:** None; record outbox/Kafka introduction criteria.  
**IMPLEMENTATION REQUIREMENTS:** Each ADR includes context, decision, alternatives, pros/cons, consequences, owner, decision status, and numeric/observable revisit trigger.  
**SECURITY REQUIREMENTS:** Decisions cannot weaken `SEC-001..010`; identify enforcing component and fail-closed behavior.  
**MULTI-TENANCY REQUIREMENTS:** Explicit shared/enterprise/regulated tier boundaries.  
**OBSERVABILITY REQUIREMENTS:** Identify signals needed to evaluate each revisit trigger.  
**FAILURE BEHAVIOR:** Unresolved P0 decision blocks dependent task; it is not guessed by the implementer.  
**IDEMPOTENCY REQUIREMENTS:** Record which components own mutation idempotency.  
**TESTS REQUIRED:** ADR schema, link, duplicate-ID, and contradiction checks.  
**AI EVALS REQUIRED:** None; select required eval infrastructure boundaries.  
**PERFORMANCE REQUIREMENTS:** State tenant/event/investigation/data-volume and latency assumptions.  
**MIGRATION REQUIREMENTS:** Every deferred/replaceable choice states migration seam and data portability.  
**ROLLBACK / COMPENSATION:** ADR reversal requires a superseding ADR; never rewrite accepted history.  
**VERIFICATION COMMANDS:** `rg -n "^# ADR-|^Status:|Revisit Trigger|Alternatives|Consequences" docs/31-adr`; `rg -n "TBD|TO BE DECIDED" docs/31-adr`.  
**EXPECTED OUTPUT:** Nine reviewable ADRs with no unexplained P0 `TBD`.  
**ACCEPTANCE CRITERIA:** `AC-003`, `AC-005`, `AC-008..012` have supporting decisions and owners.  
**DEFINITION OF DONE:** ADRs are accepted/deferred and all affected canonical docs agree.  
**DO NOT:** Add a service because it is fashionable; initialize infrastructure; change business semantics; claim benchmark results.

## RP-P00-T002

**TITLE:** Specify the AI, agent, ML, RAG, causal, and decision planes  
**OBJECTIVE:** Define deterministic contracts and evaluation criteria for investigation intelligence.  
**BUSINESS RATIONALE:** Make root-cause and intervention claims measurable and reproducible.  
**ARCHITECTURAL CONTEXT:** LLMs plan/summarize under typed constraints; statistical/ML services calculate metrics/effects; verifier separates evidence from claims.  
**DEPENDENCIES:** `RP-P00-T001`.  
**PRECONDITIONS:** Accepted metric/time semantics and benchmark objectives.  
**FILES / MODULES EXPECTED:** `docs/05-ai-architecture/AI-ARCHITECTURE.md`, `docs/06-agent-platform/MULTI-AGENT-SPEC.md`, `docs/08-ml-platform/ML-SYSTEM-SPEC.md`, `docs/09-rag/RAG-SPEC.md`, `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md`, `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md`, `docs/19-ai-governance/AI-GOVERNANCE.md`, `docs/20-evaluation/EVALUATION-FRAMEWORK.md`, `docs/20-evaluation/MODEL-RELEASE-PROCESS.md`.  
**DATA MODEL:** Define versioned Plan, AgentTask, Evidence, Hypothesis, ModelArtifact, EvalRun, Recommendation, and Decision schemas.  
**API CONTRACT:** Typed input/output/error schemas for every capability; no free-form output consumed as authority.  
**EVENT CONTRACT:** Investigation task/evidence/hypothesis/eval/decision lifecycle events with tenant, version, correlation, and causation fields.  
**IMPLEMENTATION REQUIREMENTS:** Cover planner DAG validation, capability registry, retrieval stages, benchmark splits, estimands, calibration, uncertainty, constraint optimization, and release gates.  
**SECURITY REQUIREMENTS:** Untrusted-context labeling, output validation, prompt-injection defenses, tool-capability bounds, PII policy, model supply-chain controls.  
**MULTI-TENANCY REQUIREMENTS:** Tenant/ACL filters at retrieval and feature/data access; no cross-tenant training by default.  
**OBSERVABILITY REQUIREMENTS:** Token/model/tool spans, evidence IDs, model/prompt/index versions, eval and cost attributes without chain-of-thought.  
**FAILURE BEHAVIOR:** Emit insufficient-evidence/degraded/unavailable typed states; never fabricate evidence or silently substitute estimands.  
**IDEMPOTENCY REQUIREMENTS:** Plan/task/eval creation keyed by investigation plus artifact/version digest.  
**TESTS REQUIRED:** Unit, contract, integration, contamination/time-leakage, deterministic fixtures, adversarial prompt/retrieval tests.  
**AI EVALS REQUIRED:** RAG Recall@K/MRR/citation; SQL semantic correctness; RCA top-k; agent/tool/policy; PR-AUC/calibration/Brier; Qini; causal effect error.  
**PERFORMANCE REQUIREMENTS:** Define per-stage budgets and asynchronous completion objectives from workload assumptions.  
**MIGRATION REQUIREMENTS:** Version compatibility for prompts, graphs, features, models, indexes, and evaluation datasets.  
**ROLLBACK / COMPENSATION:** Release artifacts support instant previous-version selection; decisions already acted on remain immutable.  
**VERIFICATION COMMANDS:** `rg -n "FR-|SEC-|AC-|API-|EVT-|TEST-" docs/05-ai-architecture docs/06-agent-platform docs/08-ml-platform docs/09-rag docs/10-causal-ai docs/11-decision-intelligence docs/19-ai-governance docs/20-evaluation`.  
**EXPECTED OUTPUT:** Complete intelligence-plane specifications with schemas, state/error models, tests, evals, and trade-offs.  
**ACCEPTANCE CRITERIA:** `AC-002..007`, `AC-011`, `AC-014`.  
**DEFINITION OF DONE:** Every P0/P2 intelligence requirement has an owner, contract, task seam, test/eval, target, and failure behavior.  
**DO NOT:** Use LLM confidence as calibrated probability; equate correlation/churn risk with causal effect/uplift; expose chain-of-thought.

## RP-P00-T003

**TITLE:** Specify execution safety and enterprise control planes  
**OBJECTIVE:** Define durable workflow, tenant/IAM, policy, approval, gateway, action safety, governance, FinOps, billing, audit, and SRE controls.  
**BUSINESS RATIONALE:** Prevent an analytically useful system from becoming an unsafe autonomous actor or unmanageable SaaS.  
**ARCHITECTURAL CONTEXT:** Temporal owns durable business state; Execution Plane is the sole side-effect path; Control Plane supplies authority and limits.  
**DEPENDENCIES:** `RP-P00-T001`.  
**PRECONDITIONS:** Security invariants and tenant tiers accepted.  
**FILES / MODULES EXPECTED:** `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md`, `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md`, `docs/14-iam/IAM-SPEC.md`, `docs/15-security/SECURITY-ARCHITECTURE.md`, `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md`, `docs/18-data-governance/DATA-GOVERNANCE.md`, `docs/21-finops/FINOPS-SPEC.md`, `docs/22-billing/BILLING-SPEC.md`, `docs/22-billing/AUDIT-LOG-SPEC.md`, `docs/23-observability/OBSERVABILITY-SPEC.md`, `docs/24-sre/SRE-SPEC.md`, `docs/24-sre/DR-PLAN.md`, `docs/25-compliance/COMPLIANCE-READINESS.md`.  
**DATA MODEL:** Tenant, Principal, Delegation, PolicyDecision, Approval, ActionIntent/Attempt, Compensation, Usage, Billing, AuditEvent, KillSwitch.  
**API CONTRACT:** Admin/approval/tool endpoints bind trusted context and immutable digests; stable error model.  
**EVENT CONTRACT:** Approval/action/audit/usage/kill-switch lifecycle with ordering, retention, replay, and signature rules.  
**IMPLEMENTATION REQUIREMENTS:** Temporal definitions/activities/signals/queries/versioning; ABAC; short-lived credential broker; dry-run; Saga; hierarchical budgets; SLI/SLO/RPO/RTO.  
**SECURITY REQUIREMENTS:** Address every threat-model story and separate operational trace from immutable minimized audit.  
**MULTI-TENANCY REQUIREMENTS:** Isolation enforcement and test matrices for every store/capability; lifecycle export/deletion propagation.  
**OBSERVABILITY REQUIREMENTS:** Audit/cost/action traces with redaction, sampling prohibitions for security events, alert owners.  
**FAILURE BEHAVIOR:** IAM/policy/audit uncertainty fails closed for writes; provider unknown result enters reconciliation.  
**IDEMPOTENCY REQUIREMENTS:** Define keys, uniqueness scope, retention, replay response, and provider reconciliation per action type.  
**TESTS REQUIRED:** Auth matrix, cross-tenant negative suite, digest tamper/replay, crash-at-step, kill switch, deletion, DR restore, metering.  
**AI EVALS REQUIRED:** Unauthorized action rate, policy compliance, prompt/tool injection, unnecessary tool use, recovery success.  
**PERFORMANCE REQUIREMENTS:** Approval/event propagation, gateway overhead, control-plane availability and capacity budgets.  
**MIGRATION REQUIREMENTS:** Version policy/tool schemas and preserve immutable histories; key/tenant migration procedures.  
**ROLLBACK / COMPENSATION:** Explicit reversible, compensatable, and irreversible classification per action.  
**VERIFICATION COMMANDS:** `rg -n "SEC-|Failure|Idempot|Tenant|Audit|Kill|RPO|RTO" docs/12-workflow-engine docs/13-multi-tenancy docs/14-iam docs/15-security docs/16-tool-gateway docs/18-data-governance docs/21-finops docs/22-billing docs/23-observability docs/24-sre docs/25-compliance`.  
**EXPECTED OUTPUT:** Reviewable execution/control specifications and matrices sufficient to block unsafe implementations.  
**ACCEPTANCE CRITERIA:** `AC-008..013` and Production Definition of Done.  
**DEFINITION OF DONE:** All security objectives have an enforcing owner, negative test, failure behavior, and operational signal.  
**DO NOT:** Put credentials in agent context; assume rollback of email/external effects; equate software controls with certification.

## RP-P00-T004

**TITLE:** Specify data, connectors, contracts, persistence, frontend, testing, and deployment  
**OBJECTIVE:** Complete implementable platform interfaces and operator/user experiences.  
**BUSINESS RATIONALE:** Prevent AI specifications from depending on undefined data semantics or enterprise plumbing.  
**ARCHITECTURAL CONTEXT:** Canonical enterprise data, governed ingestion, API/event contracts, evidence-oriented UI, progressive deployment.  
**DEPENDENCIES:** `RP-P00-T001`.  
**PRECONDITIONS:** Domain entities, tenancy tiers, and workload assumptions accepted.  
**FILES / MODULES EXPECTED:** `docs/07-data-platform/DATA-ARCHITECTURE.md`, `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md`, `docs/26-api/API-STANDARDS.md`, `docs/26-api/EVENT-CONTRACTS.md`, `docs/27-database/DATABASE-SCHEMA.md`, `docs/28-frontend/FRONTEND-SPEC.md`, `docs/29-testing/TEST-STRATEGY.md`, `docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md`, `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md`.  
**DATA MODEL:** Complete logical/physical ownership, keys, time semantics, classification, lineage, retention, indexes, partitions, migrations.  
**API CONTRACT:** REST conventions for versioning, pagination, concurrency, idempotency, errors, tenant context, correlation, and deprecation.  
**EVENT CONTRACT:** Envelope, schema evolution, partition/order, dedup, late/out-of-order, replay, DLQ, reconciliation.  
**IMPLEMENTATION REQUIREMENTS:** Initial/incremental sync, webhook/CDC, raw/normalized/canonical zones, connector lifecycle, UI state/error/approval behavior, environment topology.  
**SECURITY REQUIREMENTS:** Parser isolation, webhook verification, SSRF/egress control, browser/session security, data classification and masking.  
**MULTI-TENANCY REQUIREMENTS:** Physical/logical isolation and lifecycle for DB/vector/cache/event/object/search/features/logs/exports.  
**OBSERVABILITY REQUIREMENTS:** Data quality/lineage, connector lag/health, UI/API traces, migration/deployment signals.  
**FAILURE BEHAVIOR:** Quarantine drift/malformed data; surface partial freshness; reconcile duplicates/late events; fail safe.  
**IDEMPOTENCY REQUIREMENTS:** Ingestion and mutation keys plus retention/replay semantics.  
**TESTS REQUIRED:** Schema/property/contract/E2E/security/performance/chaos/data quality/accessibility and recovery suites.  
**AI EVALS REQUIRED:** Synthetic ground-truth design prevents leakage and supports all metric families.  
**PERFORMANCE REQUIREMENTS:** Capacity model and p50/p95/p99 targets for agreed workload assumptions.  
**MIGRATION REQUIREMENTS:** Expand/contract, backfill, compatibility window, verification and recovery for every schema/event change.  
**ROLLBACK / COMPENSATION:** Deployment rollback must preserve forward-written data; destructive migration prohibited without approved recovery.  
**VERIFICATION COMMANDS:** `rg -n "API-|EVT-|Migration|Tenant|Failure|Acceptance" docs/07-data-platform docs/17-connectors docs/26-api docs/27-database docs/28-frontend docs/29-testing docs/30-deployment`.  
**EXPECTED OUTPUT:** Concrete schemas/contracts/screens/test/deployment specifications with examples and failure modes.  
**ACCEPTANCE CRITERIA:** `AC-001`, `AC-005`, `AC-009..013`.  
**DEFINITION OF DONE:** Implementation agents can derive no architecture or business semantics themselves.  
**DO NOT:** Add Kafka/Kubernetes/Qdrant/OpenSearch before ADR trigger; accept client-supplied tenant authority; hide partial/stale data.

## RP-P00-T005

**TITLE:** Red-team, reconcile, and publish the implementation-ready specification baseline  
**OBJECTIVE:** Remove contradictions, close traceability, and approve a versioned Phase 00 baseline.  
**BUSINESS RATIONALE:** A large documentation set is harmful if its contracts disagree or leave security-critical choices implicit.  
**ARCHITECTURAL CONTEXT:** All Foundation Pack and detailed specification outputs.  
**DEPENDENCIES:** `RP-P00-T002`, `RP-P00-T003`, `RP-P00-T004`.  
**PRECONDITIONS:** No missing mandatory document and all P0 ADRs decided/deferred with blockers.  
**FILES / MODULES EXPECTED:** All `docs/**`, `execution/**`, and `tasks/PHASE-00/TASKS.md`; no source code.  
**DATA MODEL:** Verify one canonical definition and owner for every entity/field/value object.  
**API CONTRACT:** Verify API schemas match domain/database/auth/error semantics.  
**EVENT CONTRACT:** Verify event schemas match transactions, ordering, replay, and consumers.  
**IMPLEMENTATION REQUIREMENTS:** Review as Principal Architect, Security, SRE, ML, Data, Compliance, and FinOps; fix contradictions rather than only listing them.  
**SECURITY REQUIREMENTS:** Reconcile every threat story with a control/test/open prerequisite; do not claim implementation evidence.  
**MULTI-TENANCY REQUIREMENTS:** Trace isolation and deletion/export across every plane.  
**OBSERVABILITY REQUIREMENTS:** Every SLO, budget, security control, AI gate, and workflow transition has measurable signals and owner.  
**FAILURE BEHAVIOR:** Any unresolved authority/data-loss/causality contradiction blocks baseline acceptance.  
**IDEMPOTENCY REQUIREMENTS:** Verify end-to-end key derivation, retention, provider behavior, unknown-result reconciliation.  
**TESTS REQUIRED:** Markdown/link/Mermaid/ID/schema/traceability lint plus manual cross-role review.  
**AI EVALS REQUIRED:** Verify datasets, target definitions, slice analysis, leakage prevention, release thresholds, and actual-vs-target reporting.  
**PERFORMANCE REQUIREMENTS:** Capacity math must follow accepted workload assumptions and name uncertainty.  
**MIGRATION REQUIREMENTS:** Every stateful component has compatible migration/recovery ownership.  
**ROLLBACK / COMPENSATION:** Baseline changes after acceptance require ADR/change review; previous version remains recoverable.  
**VERIFICATION COMMANDS:** `rg --files docs execution tasks`; `rg -n "TBD|TODO|FIXME|PLACEHOLDER" docs execution tasks`; `rg -o "(BR|FR|NFR|SEC|ADR|API|EVT|AC|TEST|RP)-[A-Z0-9-]+" docs execution tasks`.  
**EXPECTED OUTPUT:** Versioned implementation-ready spec baseline, closed traceability matrix, updated risk register, and explicit open-decision register.  
**ACCEPTANCE CRITERIA:** All `AC-001..014` are design-verifiable and every P0 requirement has exact downstream links.  
**DEFINITION OF DONE:** Architecture board accepts Phase 00; coding tasks may then be generated phase-by-phase.  
**DO NOT:** Mark controls implemented; fabricate benchmarks; waive contradictions; begin product implementation.
