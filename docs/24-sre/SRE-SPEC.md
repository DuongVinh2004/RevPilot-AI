# Site Reliability Engineering Architecture and Production Operations Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 08 — Production Readiness, Release Governance & Operational Evidence
Rail Alignment: Rail 17 (Observability/FinOps/Audit), Rail 2 (Tenant Context & Lifecycle), Rail 5 (Persistence Isolation)
Owner: SRE Lead & Platform Architect
Approver: Dương Vinh
Last Reviewed Date: 2026-09-03
Traceability: `BR-004`, `INV-REL-001..002`, `INV-TEN-001..003`, `NFR-AVL-001`, `NFR-REL-001..002`, `NFR-TEN-001..002`, `NFR-REC-001`, `AC-010`, `ADR-0005`, `ADR-0008`, `ADR-0009`
Version: v1.0

## Revision History

| Version | Date | Author | Reviewer | Approval | Summary of Changes |
|---|---|---|---|---|---|
| v1.0 | 2026-09-04 | SRE Team | Platform Architect | Dương Vinh | Canonical SRE and production operations specification |

---

## 1. Reliability Principles and Boundaries

1. **Empirical Verification Required**: No availability, latency, or throughput number is claimed as an achieved metric without executed benchmark evidence. All figures are design targets.
2. **Fail-Closed Gateways (`INV-REL-001`)**:
   - If tenancy, IAM, policy, or audit backends encounter an outage or timeout: all write operations, external mutations, and tool dispatches are immediately rejected with HTTP 503.
   - Isolation is never relaxed to preserve availability (`NFR-TEN-002`). Cross-tenant boundaries take absolute precedence over uptime.
3. **Defense-in-Depth Resiliency**:
   - Connection pools use circuit breakers with fail-fast timeouts ($\le 3000$ms).
   - Ingestion webhooks and events use transactional outbox/inbox queues with dead-letter buffering.
   - AI model calls route through an automated multi-provider fallback hierarchy with strict token and cost caps.

---

## 2. Production Service Level Architecture

Operational reliability is partitioned into 4 core service tiers:

| Tier | Services Included | Target Availability (Design) | Maximum Allowed Outage (30-day) | On-Call Tier |
|---|---|---|---|---|
| **Tier 0 (Core)** | API Gateway, PostgreSQL Primary, IAM/OIDC Validation, Audit Log Sink | 99.9% | 43.8 minutes | 24/7 PagerDuty (P0) |
| **Tier 1 (Execution)**| Temporal Orchestrator, Ingestion Workers, Tool Gateway, Quota Manager | 99.5% | 3.6 hours | 24/7 PagerDuty (P1) |
| **Tier 2 (Intelligence)**| AI Agent Workers, Vector Search DB, Causal Estimators, RAG Pipelines | 99.0% | 7.2 hours | Business Hours (P2) |
| **Tier 3 (Reporting)** | Usage Metering Aggregator, Billing Reports, Customer Export Workers | 98.0% | 14.4 hours | Next-Day Queue (P3) |

---

## 3. Operational Reference Catalog

The operational SRE system is specified across specialized canonical documents:
- **Production Readiness Gate**: Comprehensive 31-point checklist and evidence contracts (`docs/24-sre/PRODUCTION-READINESS-GATE.md`).
- **Telemetry, SLOs, and Alerting**: Detailed SLI/SLO mathematical definitions, error budgets, and alerting rules (`docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md`).
- **Disaster Recovery & Scenarios**: 11 master failure scenario playbooks, RPO $\le 5$m, RTO $\le 30$m specifications (`docs/24-sre/DR-PLAN.md`).
- **Backup & PITR Runbook**: Point-in-time recovery, continuous WAL archiving, and ephemeral restore verification (`docs/24-sre/BACKUP-RESTORE-VALIDATION-RUNBOOK.md`).
- **Incident Response & Paging**: Command structure, communication SLAs, and 8 triage playbooks (`docs/24-sre/INCIDENT-RESPONSE-RUNBOOK.md`).
- **Pilot Onboarding & Rehearsals**: Pre-flight checklist and 7 live failure rehearsals (`docs/24-sre/PILOT-ONBOARDING-AND-RECOVERY-SPEC.md`).

---

## 4. Acceptance Criteria
1. `AC-SRE-01`: SRE architecture establishes fail-closed behavior across 100% of critical paths without exception.
2. `AC-SRE-02`: Every Tier 0 and Tier 1 service has an assigned on-call team, automated health probe, and documented recovery runbook.
