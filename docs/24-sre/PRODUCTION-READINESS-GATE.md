# Production Readiness Gate and Verification Matrix

Status: Accepted
Initiative: REVPILOT
Phase: Phase 08 — Production Readiness, Release Governance & Operational Evidence
Owner Role: SRE Lead & Principal Platform Architect
Approver: Dương Vinh
Last Reviewed Date: 2026-09-03
Traceability: `INV-TEN-001..003`, `INV-IAM-001..002`, `INV-SEC-001..003`, `INV-ACT-001..004`, `INV-WF-001..002`, `INV-AI-001..002`, `INV-EVD-001..002`, `INV-DATA-001..002`, `INV-AUD-001..002`, `INV-COST-001`, `INV-PRV-001`, `INV-REL-001..002`, `NFR-SEC-001..002`, `NFR-DUR-001`, `NFR-REL-001..002`, `NFR-TEN-001..002`, `NFR-AUD-001`, `NFR-COST-001..002`, `NFR-PRV-001..002`, `NFR-OBS-001..002`, `NFR-AI-001..007`, `AC-001..014`, `ADR-0001..0012`

---

## 1. Purpose
Establish the definitive, machine-verifiable gate criteria for certifying RevPilot AI as ready for commercial production deployment. Eliminate subjective or documentation-only readiness claims.

## 2. Scope
Covers all infrastructure, persistence, tenant isolation, identity, connector, workflow, approval, security, AI governance, FinOps, observability, and disaster recovery controls across all software tiers.

## 3. Non-Goals
- Authorizing production deployment without empirical test execution.
- Substituting architecture documentation for live production evidence.
- Overriding external regulatory or legal compliance determinations.

## 4. Normative Requirements
1. Every gate control must be tied to a canonical invariant or NFR.
2. Control status cannot be set to `PASS` without a cryptographic or machine-generated evidence artifact.
3. If evidence is missing, status must be explicitly recorded as `PLANNED`, `NOT EXECUTED`, `UNKNOWN`, or `BLOCKED`.
4. Any `BLOCKED` or unverified P0 control halts production promotion.

## 5. Architectural Invariants
- `INV-REL-001`: Fail closed on uncertainty. Any unverified readiness gate defaults to `BLOCKED`.
- `INV-TEN-001`: Hard persistence and derived store isolation across 100% of tenants.
- `INV-SEC-001`: Zero raw credentials in Agent Runtime or operational logs.
- `INV-ACT-001`: External write actions blocked unless explicitly approved and verified.

## 6. Interfaces and System Boundaries
- Ingress: API Gateway, OIDC/SAML Federation endpoints, Webhook listeners.
- Compute: Orchestrator, Temporal workers, Agent reasoning workers, Connector sync engines.
- State: PostgreSQL (primary store), Redis (cache), Vector DB (disposable projection), S3 (blobs).

## 7. Failure Modes
- Premature Promotion: System promoted to production while isolation or disaster recovery is unverified.
- False Verification: Test results fabricated or drawn from non-representative synthetic mocks.
- Drift Degradation: Post-deployment configuration drift invalidates pre-flight certification.

## 8. Operational Procedures
1. SRE and Security Leads run automated verification suites (`TC-P08-001..028`) and operational verification protocols covering the canonical 31-control Production Readiness Verification Matrix.
2. Evidence collector aggregates run manifests, SHA-256 digests, and benchmark logs into `evidence/production-readiness/`.
3. Gate review committee verifies each checklist item.
4. Gate sign-off requires unanimous approval from Architecture, Security, SRE, and Legal.

---

## 9. Production Readiness Verification Matrix

> [!IMPORTANT]
> Design target only — not yet measured. No production ready state is claimed prior to empirical execution.
>
> **Canonical Control Registry**: Exactly 31 production readiness controls across 14 operational domains (`PRG-TEN-01` through `PRG-INC-01`). The 31 controls are validated via the 28 automated test suites defined in `TEST-STRATEGY.md` §13.2 (`TC-P08-001..028`) and 3 operational/procedural verification protocols (`PRG-SRE-01` 72-hour synthetic soak dashboard, `DEC-P08-01` cloud platform evaluation, and `DEC-P08-02` statutory retention review).

| ID | Domain | Target Requirement | Control Description | Required Evidence Artifact | Evidence Owner | Validation Method | Current Status | Blocking Impact | Exit Condition |
|---|---|---|---|---|---|---|---|---|---|
| `PRG-TEN-01` | Tenancy | `INV-TEN-001`, `NFR-TEN-001` | Hard PostgreSQL RLS & Schema Isolation | Cross-tenant negative suite log (`TEST-TEN-001..011`) | Tenancy Lead | Adversarial automated SQL injection probe | PLANNED | CRITICAL (Halts Release) | 0 rows leaked across 100,000 synthetic queries |
| `PRG-TEN-02` | Tenancy | `INV-TEN-002` | Server-derived tenant context binding | Middleware token claim verification test report | IAM Lead | Header spoofing negative test suite | PLANNED | CRITICAL | 100% rejection of `X-Tenant-ID` overrides |
| `PRG-IAM-01` | Identity | `INV-IAM-001`, `NFR-SEC-001` | OIDC PKCE & JWKS Key Rotation | Cryptographic test log with key rollover | Security Lead | Automated IdP key rollover emulation | PLANNED | HIGH | Zero downtime on rotation; 100% signature verify |
| `PRG-IAM-02` | Identity | `INV-IAM-002` | Scoped Agent Delegation Token TTL $\le 24$h | Token expiry and privilege escalation test run | Security Lead | Adversarial agent privilege escalation test | PLANNED | CRITICAL | Agents strictly barred from exceeding delegator role |
| `PRG-SEC-01` | Secrets | `INV-SEC-001`, `NFR-SEC-002` | Credential Broker ephemeral scoping | Memory dump & log scanner report | Security Lead | Automated entropy/credential regex scanner | PLANNED | CRITICAL | 0 secrets found in logs, prompts, or workflows |
| `PRG-SEC-02` | Secrets | `ADR-0009` | Secret service outage fail-closed behavior | Chaos fault injection test report | SRE Lead | Secret store socket blackhole emulation | PLANNED | HIGH | 100% external mutations blocked upon outage |
| `PRG-CON-01` | Connectors | `INV-SEC-003`, `FR-ACT-001` | Connector egress read-only barrier | Egress proxy firewall policy audit | Integrations Lead | Direct socket connection attempt test | PLANNED | CRITICAL | 100% outbound mutations outside Tool Gateway blocked |
| `PRG-CON-02` | Connectors | `INV-DATA-002` | Webhook HMAC verification & anti-replay | Webhook replay test suite manifest | Integrations Lead | Replay of 1,000 recorded webhook payloads | PLANNED | HIGH | 100% duplicate/tampered events rejected |
| `PRG-CON-03` | Connectors | `INV-DATA-002` | Schema drift quarantine & alerting | Schema drift injection test output | Data Lead | Injection of altered payload columns | PLANNED | HIGH | Breaking schemas diverted to quarantine; 0 corruption |
| `PRG-WF-01` | Workflows | `INV-WF-001`, `NFR-DUR-001` | Temporal Saga crash recovery & replay | Worker kill/restart test execution log | SRE Lead | SIGKILL worker injection during active Saga | PLANNED | CRITICAL | 100% workflows resume from history; 0 duplicate tasks |
| `PRG-WF-02` | Workflows | `INV-WF-002` | Deterministic workflow compensation | Saga compensation execution ledger | Architecture Lead | Simulated step failure in multi-step action | PLANNED | HIGH | Prior actions compensated in reverse order |
| `PRG-ACT-01` | Approval | `INV-ACT-002`, `AC-008` | Cryptographic approval digest binding | SHA-256 payload tampering test report | Security Lead | Modified payload dispatch verification | PLANNED | CRITICAL | Digest mismatch rejects action dispatch |
| `PRG-ACT-02` | Approval | `INV-ACT-003` | Agent self-approval strict block | Negative test run with agent identity | IAM Lead | Agent principal signing attempt | PLANNED | CRITICAL | 100% agent approval attempts blocked with 403 |
| `PRG-ACT-03` | Approval | `INV-ACT-004` | Immutable Action Ledger progression | Ledger audit trail checksum dump | Audit Lead | Read-only verification of ledger rows | PLANNED | HIGH | Append-only ledger; zero mutating updates |
| `PRG-AUD-01` | Audit | `INV-AUD-001`, `NFR-AUD-001` | 100% Unsampled security audit logging | Audit event stream parity verification | Audit Lead | Automated event count reconciliation | PLANNED | HIGH | Zero dropped audit records; hash chain intact |
| `PRG-AUD-02` | Audit | `INV-AUD-002`, `INV-PRV-001` | PII and secret stripping from audit | DLP scan report over 50,000 audit rows | Privacy Lead | Automated pattern and PII validator | PLANNED | HIGH | 0 PII or secret instances in audit payloads |
| `PRG-EVD-01` | Lineage | `INV-EVD-001`, `AC-005` | End-to-end evidence citation provenance | Investigation citation audit report | AI Lead | Automated citation accuracy benchmark | PLANNED | HIGH | 100% claims linked to valid evidence spans |
| `PRG-DAT-01` | Data Gov | `INV-DATA-001` | Temporal anti-leakage (`:as_of_time`) | Temporal boundary unit & query test | Data Lead | Future-dated record query test | PLANNED | CRITICAL | Zero future-dated records consumed |
| `PRG-DAT-02` | Data Gov | `FR-CTL-003` | Irreversible tenant deletion cascade | Cascade deletion verification probe | Data Lead | Post-deletion multi-store query probe | PLANNED | HIGH | Zero residual records across all 10 datastores |
| `PRG-DAT-03` | Data Gov | `FR-CTL-003` | Legal hold deletion blockage | Legal hold negative test execution | Legal Lead | Deletion request on hold-locked tenant | PLANNED | CRITICAL | 100% deletion requests rejected with 409 Conflict |
| `PRG-OBS-01` | Observability | `NFR-OBS-001` | End-to-end correlation ID propagation | Distributed trace span continuity log | SRE Lead | Trace ID propagation verification suite | PLANNED | MEDIUM | 100% trace spans carry tenant and correlation IDs |
| `PRG-OBS-02` | Observability | `NFR-OBS-002` | Zero-sampling for security/audit telemetry | OTel Collector pipeline configuration audit | SRE Lead | Pipeline load test with dropped-event counter | PLANNED | HIGH | Zero dropped spans for high-priority routes |
| `PRG-SRE-01` | SRE | `NFR-AVL-001`, `NFR-LAT-001` | API availability $\ge 99.9\%$ under soak; synchronous API p95 $<500$ms | 72-hour synthetic soak test dashboard plus 30-day SLI | SRE Lead | Continuous synthetic traffic runner | NOT EXECUTED | HIGH | Measured uptime $\ge 99.9\%$, p95 latency $<500$ms |
| `PRG-SRE-02` | SRE | `INV-REL-001` | Fail-closed kill switches ($< 500$ms) | Kill-switch propagation latency benchmark | SRE Lead | Cluster-wide kill-switch trigger test | PLANNED | CRITICAL | All tool executions halt within 500ms |
| `PRG-DR-01` | Recovery | `NFR-REC-001` | Target RPO $\le 5$m, RTO $\le 30$m | Staging DR exercise report (`REH-P07-04`) | SRE Lead | Cold restore into isolated staging target | NOT EXECUTED | HIGH | Measured RPO $\le 5$m, RTO $\le 30$m |
| `PRG-FIN-01` | FinOps | `INV-COST-001`, `NFR-COST-001` | Atomic spend reservation (zero overspend) | 500-thread concurrent spend race test | FinOps Lead | Thread contention load test script | PLANNED | HIGH | Zero over-allocation beyond hard budget |
| `PRG-FIN-02` | FinOps | `NFR-COST-002` | Usage attribution precision $\ge 99.5\%$ | Daily billing reconciliation report | FinOps Lead | Provider bill vs internal usage ledger diff | PLANNED | MEDIUM | Attribution reconciliation variance $< 0.5\%$ |
| `PRG-AI-01` | AI Quality | `NFR-AI-001`, `AC-011` | Immutable artifact versioning | Model/Prompt registry integrity manifest | AI Lead | Hash validation against golden artifact store | PLANNED | HIGH | 100% models/prompts pinned to digest |
| `PRG-AI-02` | AI Quality | `NFR-AI-002..007` | Golden test set regression & safety gates | Golden set evaluation benchmark run | AI Lead | Automated benchmark suite execution | NOT EXECUTED | HIGH | Uplift, calibration, and safety pass baseline |
| `PRG-REL-01` | Release | `ADR-0008` | Automated canary & multi-tier rollback | Staging canary deploy & rollback run | Release Lead | Canary rollback trigger test script | PLANNED | HIGH | Zero-downtime rollback; 0 schema conflict |
| `PRG-INC-01` | Ops | `INV-REL-002` | On-call rotation & paging runbook tested | Mock P0 incident paging drill report | SRE Lead | Simulated production P0 paging drill | NOT EXECUTED | HIGH | Pager escalation acknowledged within 15 minutes |

---

## 10. Open Decisions
- `DEC-P08-01`: Target production cloud provider and managed Kubernetes/container hosting platform (`UNKNOWN`, pending commercial review).
- `DEC-P08-02`: Statutory retention windows for regional markets (`UNKNOWN`, pending formal legal counsel review, `NFR-PRV-002`).

## 11. Acceptance Criteria
1. `AC-PRG-01`: Production readiness gate is complete when 100% of checklist controls have defined validation scripts, owners, and non-null evidence requirements.
2. `AC-PRG-02`: No software release may be designated as `PRODUCTION_READY` while any item in the matrix has status `PLANNED`, `NOT EXECUTED`, `UNKNOWN`, or `BLOCKED`.
