# Documentation map and governance

Status: Documentation map. Current documentation target: `DOCUMENTATION COMPLETE / IMPLEMENTATION PENDING / EMPIRICAL VALIDATION PENDING / GO-LIVE BLOCKED`.

> [!IMPORTANT]
> This map is a documentation navigation aid, not evidence that Rails, tests, production controls, or release gates have passed. Read [`DOCUMENTATION-CLOSURE-DECISIONS.md`](00-executive/DOCUMENTATION-CLOSURE-DECISIONS.md) before relying on a status claim.

## Reading order

1. `00-executive/EXECUTIVE-VISION.md`
2. `01-product/PRD.md`
3. `02-domain/BUSINESS-DOMAIN-MODEL.md`
4. `03-requirements/SRS.md`
5. `04-system-architecture/SYSTEM-ARCHITECTURE.md`
6. `15-security/THREAT-MODEL.md`
7. `execution/MASTER-ROADMAP.md`
8. `execution/DEPENDENCY-GRAPH.md`
9. `execution/TRACEABILITY-MATRIX.md`
10. `execution/MICRO-TASK-RAIL-SYSTEM.md`
11. `execution/EXECUTOR-QUEUE.md`
12. `00-executive/GLOSSARY.md`
13. `00-executive/SPECIFICATION-PRECEDENCE.md`
14. `03-requirements/WORKLOAD-ASSUMPTIONS.md`
15. `03-requirements/INVARIANT-REGISTRY.md`
16. `03-requirements/NFR-BASELINE.md`
17. `04-system-architecture/SYSTEM-BOUNDARIES.md`
18. `04-system-architecture/REPOSITORY-TOPOLOGY.md`
19. `04-system-architecture/MODULE-BOUNDARIES.md`
20. `04-system-architecture/DEPENDENCY-RULES.md`
21. `31-adr/ADR-0001-application-architecture.md` through `ADR-0012-action-approval-autonomy-boundary.md`, plus `31-adr/DECISION-CLOSURE-REGISTER.md`
22. `00-executive/DOCUMENTATION-CLOSURE-DECISIONS.md`
23. `03-requirements/FR-CLOSURE-CATALOG.md`

## Planned specification tree

The canonical tree is `docs/00-executive` through `docs/31-adr`, plus `execution/` and `tasks/PHASE-00` onward. A document is not considered complete merely because its path exists. Document status is one of `Proposed`, `Accepted`, `Superseded`, or `Deferred`; accepted documents include owner, approver, version, and last-reviewed date. All 12 ADRs were individually accepted by Dương Vinh on 2026-09-03 and 2026-09-04. A passing specification task outcome (PASS) produces the proposed document; formal document acceptance remains distinct.

| Area | Canonical deliverable | Foundation status |
|---|---|---|
| Executive | `00-executive/EXECUTIVE-VISION.md` | Proposed v0.1 |
| Product | `01-product/PRD.md` | Proposed v0.1 |
| Domain | `02-domain/BUSINESS-DOMAIN-MODEL.md`, `ANOMALY-DOMAIN-SPEC.md`, `ANOMALY-LOCALIZATION-SPEC.md` | Accepted v1.0 (Phase 02 canonical pack) |
| Requirements | `03-requirements/SRS.md`, `SYNTHETIC-DATASET-SPEC.md` | Accepted v1.0 (Phase 01 expanded) |
| System architecture | `04-system-architecture/SYSTEM-ARCHITECTURE.md` | Proposed v0.1 |
| Agent platform | `06-agent-platform/MULTI-AGENT-SPEC.md`, `SQL-CAPABILITY-CATALOG.md`, `EVIDENCE-PROVENANCE-SPEC.md`, `TICKET-INTELLIGENCE-SPEC.md`, `UNSUPPORTED-CLAIM-POLICY.md` | Accepted v1.0 (Phase 03–04 agent, evidence & verifier pack) |
| Data platform | `07-data-platform/CANONICAL-DATA-MODEL.md`, `METRIC-REGISTRY.md`, `METRIC-SERVICE-SPEC.md`, `DATA-QUALITY-LINEAGE-SPEC.md`, `DATA-ARCHITECTURE.md` | Accepted v1.0 (Phase 01–02 canonical pack) |
| AI & ML platform | `08-ml-platform/ML-SYSTEM-SPEC.md`, `UPLIFT-BENCHMARK-PROTOCOL.md`, `10-causal-ai/CAUSAL-INFERENCE-SPEC.md`, `11-decision-intelligence/DECISION-ENGINE-SPEC.md`, `BUDGET-CONSTRAINT-SPEC.md`, `FAIRNESS-SLICE-EVALUATION.md`, `HYPOTHESIS-VERIFIER-SPEC.md` | Accepted v1.0 (Phase 02 detector, Phase 04 causal/hypothesis, Phase 05 churn/uplift/decision pack) |
| Retrieval & RAG | `09-rag/RAG-SPEC.md` | Accepted v1.0 (Phase 03 governed hybrid RAG) |
| Workflow engine | `12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` | Accepted v1.0 (Phase 03 investigation & Phase 06 Saga workflows) |
| Multi-Tenancy & Ops | `13-multi-tenancy/MULTI-TENANCY-SPEC.md`, `TENANT-OPERATIONS-SPEC.md` | Accepted v1.0 (Phase 07 tenant lifecycle, isolation & ops pack) |
| IAM & Identity Fed | `14-iam/IAM-SPEC.md`, `ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` | Accepted v1.0 (Phase 07 OIDC, SAML, SCIM federation pack) |
| Security & Governance | `15-security/SECURITY-ARCHITECTURE.md`, `16-tool-gateway/TOOL-GATEWAY-SPEC.md`, `APPROVAL-ACTION-LOOP-SPEC.md`, `18-data-governance/DATA-GOVERNANCE.md`, `19-ai-governance/AI-GOVERNANCE.md` | Accepted v1.0 (Phase 03–07 approval/action, data governance & secret boundaries) |
| Connector Platform | `17-connectors/CONNECTOR-PLATFORM-SPEC.md` | Accepted v1.0 (Phase 07 connector lifecycle, webhook & drift pack) |
| FinOps & Billing | `21-finops/FINOPS-SPEC.md`, `22-billing/BILLING-SPEC.md`, `AUDIT-LOG-SPEC.md` | Accepted v1.0 (Phase 07 quotas, metering, ledger & audit pack) |
| Reliability & SRE | `23-observability/OBSERVABILITY-SPEC.md`, `OPERATIONS-TELEMETRY-SPEC.md`, `24-sre/SRE-SPEC.md`, `DR-PLAN.md`, `PRODUCTION-READINESS-GATE.md`, `INCIDENT-RESPONSE-RUNBOOK.md`, `BACKUP-RESTORE-VALIDATION-RUNBOOK.md`, `PILOT-ONBOARDING-AND-RECOVERY-SPEC.md`, `25-compliance/COMPLIANCE-READINESS.md`, `COMPLIANCE-EVIDENCE-RUNBOOK.md` | Accepted v1.0 (Phase 07–08 SRE, DR rehearsal, telemetry & readiness gate pack) |
| Deployment & Release | `30-deployment/DEPLOYMENT-ARCHITECTURE.md`, `RELEASE-CANARY-ROLLBACK-SPEC.md` | Accepted v1.0 (Phase 08 multi-tier canary & rollback pack) |
| AI Governance | `20-evaluation/MODEL-RELEASE-PROCESS.md`, `EVALUATION-FRAMEWORK.md` | Accepted v1.0 (Phase 08 AI model/prompt/policy release governance) |
| API & Events | `26-api/API-STANDARDS.md`, `EVENT-CONTRACTS.md` | Accepted v1.0 (Phase 03–07 tenant, SCIM, connector & action contracts) |
| Database & Persistence| `27-database/DATABASE-SCHEMA.md` | Accepted v1.0 (Phase 01–07 RLS/DDL schema expanded) |
| Testing & Evaluation | `20-evaluation/EVALUATION-FRAMEWORK.md`, `ANOMALY-BENCHMARK-PROTOCOL.md`, `INVESTIGATION-BENCHMARK-PROTOCOL.md`, `CAUSAL-BENCHMARK-PROTOCOL.md`, `29-testing/TEST-STRATEGY.md` | Accepted v1.0 (Phase 01–08 benchmark, load/chaos & test suites) |

| Foundation decisions | `31-adr/ADR-0001` … `ADR-0012`, `DECISION-CLOSURE-REGISTER.md` | Accepted individually on 2026-09-03 and 2026-09-04 |
| Execution | `execution/*` | Foundation files present |
| Agent tasks | `tasks/PHASE-*`, `tasks/RAIL-*` | Created phase-by-phase after specifications are accepted (Phase 00–08 authored) |

## Canonical ID namespaces

- Business outcomes: `BR-###`.
- Functional requirements: `FR-<DOMAIN>-###`.
- Non-functional requirements: `NFR-<QUALITY>-###`.
- Security invariants: `SEC-###`.
- Architecture decisions: `ADR-####`.
- APIs and events: `API-###`, `EVT-###`.
- Acceptance criteria and tests: `AC-###`, `TEST-###`.
- Planning objects retain their declared IDs. New executable implementation micro-tasks use stable domain IDs such as `TEN-001`, `IAM-001`, `RAG-001`, `WF-001`, `AGT-001`, `ML-001`, `CAUSAL-001`, `ACT-001`, `CONN-001`, `FIN-001`, `BILL-001`, `OBS-001`, and `SRE-001`. Specification micro-tasks use `SPEC-<DOMAIN>-###`. IDs are globally unique in their object type and never reused.

IDs are immutable. Removed items are marked superseded; IDs are never reused.

## Change rules

- Architectural behavior changes require an ADR and updates to the traceability matrix.
- Security, tenancy, money movement, action semantics, or audit changes require explicit owner review.
- No document may claim SOC 2, ISO 27001, GDPR, or other certification; it may only describe readiness controls.
- Benchmark documents separate target values from measured values. Unknown values remain `TBD`; fabricated results are prohibited.
- AI reasoning traces expose evidence, decisions, tool outcomes, confidence, and policy results—not hidden chain-of-thought.
- Only micro-tasks with `NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0` and readiness score at least 18/20 may enter the executor queue; critical tenant/security/financial/action work requires 20/20.
