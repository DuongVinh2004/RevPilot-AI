# Architectural Decision Closure Register

Date: 2026-09-04  
Status: Authoritative Post-Phase-08 Closure Register  
Owner: Principal Platform Architect, SRE Lead, Security Architect, Compliance Lead  
Approver: Dương Vinh  
Reference: PRD §Open Decisions, SYSTEM-BOUNDARIES §Known Unknowns, ADR-0001..0012, RUN-R06-001  

---

## 1. Overview and Closure Policy

This register formally tracks and resolves or designates the 12 core architectural decisions governing the RevPilot AI platform. Per platform safety invariants (INV-REL-001, INV-REL-002), all decisions are backed by empirical evidence, contract specifications, or explicit human approver authorization (APPROVAL-RECORD-RUN-R06-001.md). No decision is fabricated.

---

## 2. Decision Closure Records

### DEC-001: Initial Commercial Vertical and Use Case
- **Decision ID**: DEC-001
- **Topic**: Initial commercial vertical after synthetic benchmark qualification.
- **Context**: PRD §Open Decisions and SYSTEM-BOUNDARIES §Known Unknowns require selecting between E-commerce fulfillment logistics vs. B2B subscription SaaS revenue for the first commercial connector deployment.
- **Options**:
  1. Option A: E-commerce fulfillment & cancellation intelligence (Shopify, ERP, Logistics).
  2. Option B: B2B subscription & churn intelligence (Salesforce, Stripe, Zendesk).
- **Selected Option**: Option B (B2B subscription SaaS) approved by Repository Owner Dương Vinh.
- **Decision Owner**: Head of Product / Commercial Lead (Approved: Dương Vinh)
- **Impacted Documents**: docs/01-product/PRD.md, docs/07-data-platform/CANONICAL-DATA-MODEL.md, docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md
- **Impacted Invariants / NFRs**: INV-DATA-001, BR-001, BR-002
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-04 (Approved in RUN-R06-001)
- **Required Evidence**: First commercial pilot sponsor contract and connector target inventory.
- **Blocking Impact**: None. Phase 07 connector scope locked to Salesforce, Stripe, Zendesk.

---

### DEC-002: Base Currency, Timezone, and Billing Localization
- **Decision ID**: DEC-002
- **Topic**: Canonical currency representation, timezone normalization, and billing region.
- **Context**: Financial calculations, ledger entries, and audit timestamps require deterministic multi-currency and temporal arithmetic without floating-point errors.
- **Options**:
  1. Option A: Dynamic runtime floating-point currency and local server timezones.
  2. Option B: Pinned UTC ISO 8601 temporal baseline, integer minor-currency units (Money value object with ISO 4217 code), and explicit USD canonical reporting base.
- **Recommended Option**: Option B.
- **Decision Owner**: Principal Platform Architect & FinOps Lead
- **Impacted Documents**: docs/02-domain/BUSINESS-DOMAIN-MODEL.md, docs/21-finops/FINOPS-SPEC.md, docs/22-billing/BILLING-SPEC.md
- **Impacted Invariants / NFRs**: INV-COST-001, INV-DATA-001, NFR-COST-001, NFR-COST-002
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-03
- **Required Evidence**: Unit test suite packages/backend/tests/shared/test_primitives.py verifying Money and DateTimeUTC immutable value objects.
- **Blocking Impact**: None. Implemented in Rail 1 (TASK-R01-001..002).

---

### DEC-003: Statutory Customer Data Retention and Jurisdictional Residency
- **Decision ID**: DEC-003
- **Topic**: Statutory retention windows for audit/analytics and jurisdictional residency boundaries.
- **Context**: Compliance frameworks (GDPR, SOC 2, HIPAA) dictate exact retention limits and geographical data boundaries. NFR-PRV-002 declares retention as UNKNOWN until legal counsel review.
- **Options**:
  1. Option A: Assume 7-year universal retention and US-East residency for all tenants.
  2. Option B: Maintain configurable tenant-level retention policies with hard-coded UNKNOWN defaults, blocking commercial tenant onboarding until formal legal counsel DPA sign-off.
- **Selected Option**: Option B (Configurable tenant policies with strict fail-closed boundary on unconfigured regions).
- **Decision Owner**: Compliance Lead & External Legal Counsel (Approved: Dương Vinh)
- **Impacted Documents**: docs/03-requirements/WORKLOAD-ASSUMPTIONS.md, docs/18-data-governance/DATA-GOVERNANCE.md, docs/25-compliance/COMPLIANCE-READINESS.md
- **Impacted Invariants / NFRs**: NFR-PRV-002, INV-PRV-001, INV-AUD-001
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-04 (Approved in RUN-R06-001)
- **Required Evidence**: Executed Data Processing Agreement (DPA) and statutory jurisdiction schedule approved by legal counsel.
- **Blocking Impact**: None for architecture; commercial tenant onboarding enforces per-tenant DPA boundary.

---

### DEC-004: Target Production Cloud Provider and Container Execution Platform
- **Decision ID**: DEC-004
- **Topic**: Selection of primary hyperscaler (AWS, GCP, Azure) and managed container orchestration runtime.
- **Context**: ADR-0008 establishes a deployment baseline on managed containers without premature Kubernetes complexity. Cloud-specific KMS, networking, and identity integration remain open.
- **Options**:
  1. Option A: AWS (ECS Fargate + RDS Aurora PostgreSQL + Secrets Manager + KMS).
  2. Option B: GCP (Cloud Run / GKE Autopilot + Cloud SQL PostgreSQL + Secret Manager + Cloud KMS).
  3. Option C: Azure (Azure Container Apps + Azure Flexible Server + Key Vault).
- **Selected Option**: Option A (AWS: ECS Fargate + RDS Aurora PostgreSQL + Secrets Manager + KMS) approved by Repository Owner Dương Vinh.
- **Decision Owner**: SRE Lead & Platform Architecture (Approved: Dương Vinh)
- **Impacted Documents**: docs/04-system-architecture/SYSTEM-BOUNDARIES.md, docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md, docs/31-adr/ADR-0008-deployment-baseline.md
- **Impacted Invariants / NFRs**: NFR-REL-001, NFR-SEC-001, ADR-0008
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-04 (Approved in RUN-R06-001)
- **Required Evidence**: Commercial infrastructure budget approval and Terraform/OpenTofu provider test execution.
- **Blocking Impact**: None. Architecture baseline locked to AWS ECS Fargate & Aurora PostgreSQL.

---

### DEC-005: Hosted LLM Provider Selection and Data Protection Agreement
- **Decision ID**: DEC-005
- **Topic**: Initial primary and fallback hosted LLM providers and enterprise zero-data-retention SLA.
- **Context**: ADR-0011 establishes a Model Gateway abstraction. Live model calls require a vendor agreement guaranteeing zero prompt retention, tenant isolation, and private API routing.
- **Options**:
  1. Option A: Anthropic Claude 3.5 Sonnet via AWS Bedrock / Direct API with Zero Data Retention.
  2. Option B: OpenAI GPT-4o via Azure OpenAI with enterprise tenant data boundary.
  3. Option C: Google Vertex AI (Gemini 1.5 Pro) with private VPC endpoint.
  4. Option D: Dual-provider strategy (Primary: Claude 3.5 Sonnet / Azure OpenAI; Fallback: Vertex AI) mediated by RevPilot Model Gateway.
- **Selected Option**: Option D (Dual-provider: Claude 3.5 Sonnet / Azure OpenAI primary; Vertex AI fallback) with Zero Data Retention.
- **Decision Owner**: AI Platform Lead & Security Architect (Approved: Dương Vinh)
- **Impacted Documents**: docs/05-ai-architecture/AI-ARCHITECTURE.md, docs/06-agent-platform/MULTI-AGENT-SPEC.md, docs/20-evaluation/MODEL-RELEASE-PROCESS.md, docs/31-adr/ADR-0011-ai-provider-abstraction.md
- **Impacted Invariants / NFRs**: INV-AI-001, INV-SEC-002, NFR-AI-001..007, RISK-020
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-04 (Approved in RUN-R06-001)
- **Required Evidence**: Signed Business Associate Agreement / Zero Data Retention terms and golden set regression benchmark report (EVAL-REP-001).
- **Blocking Impact**: None. Architecture baseline locked to Dual-provider Model Gateway.

---

### DEC-006: External Connector Idempotency and Replay Deduplication
- **Decision ID**: DEC-006
- **Topic**: Idempotency key strategy and duplicate webhook handling across disparate SaaS connectors.
- **Context**: Third-party APIs exhibit network retries, duplicate webhooks, and inconsistent idempotency header support.
- **Options**:
  1. Option A: Rely exclusively on external provider deduplication.
  2. Option B: Implement two-tier deduplication: (1) Ingress SHA-256 event signature deduplication in Redis with 24h TTL; (2) Persistent database unique constraint on (tenant_id, connector_id, external_event_id).
- **Recommended Option**: Option B.
- **Decision Owner**: Integration Lead & Principal Architect
- **Impacted Documents**: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md, docs/26-api/EVENT-CONTRACTS.md
- **Impacted Invariants / NFRs**: INV-ACT-002, NFR-REL-002, INV-DATA-002
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-03
- **Required Evidence**: Specification accepted in CONNECTOR-PLATFORM-SPEC.md §1.1; contract test test_webhook_replay_deduplication.py codified.
- **Blocking Impact**: None. Implemented in Phase 07 connector specifications.

---

### DEC-007: Scoped-Token Support and Credential Brokering
- **Decision ID**: DEC-007
- **Topic**: Ephemeral downscoped credential issuance for external API actions.
- **Context**: Reusable long-lived API keys exposed to agent execution environments present severe confused-deputy risk (SEC-002..004, ADR-0009).
- **Options**:
  1. Option A: Long-lived environment variables injected into worker containers.
  2. Option B: Tool Gateway Credential Broker with dynamic token exchange, narrow OAuth scopes, and max TTL <= 15 minutes (superseding older 1 hour proposal per `DOCUMENTATION-CLOSURE-DECISIONS.md` and `TOOL-GATEWAY-SPEC.md` §7.2).
- **Recommended Option**: Option B (max 15-minute ephemeral token TTL).
- **Decision Owner**: Security Architect
- **Impacted Documents**: docs/15-security/SECURITY-ARCHITECTURE.md, docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md, docs/31-adr/ADR-0009-secrets-and-keys.md
- **Impacted Invariants / NFRs**: INV-IAM-002, INV-SEC-001, NFR-SEC-002
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-03
- **Required Evidence**: Codified in ADR-0009 and TOOL-GATEWAY-SPEC.md §3; planned verification in test_connector_secret_scrubbing.py.
- **Blocking Impact**: None for planning; live connector execution blocked until broker adapter is implemented.

---

### DEC-008: Autonomous Action Policy and Unbounded Autonomy Prohibition
- **Decision ID**: DEC-008
- **Topic**: Boundaries of automated execution and absolute prohibition of unbounded AI autonomy.
- **Context**: Autonomous financial transfers, contract alterations, or unsanctioned direct customer communications carry catastrophic legal and business risk.
- **Options**:
  1. Option A: Allow autonomous action under dynamic confidence score thresholds.
  2. Option B: Strict prohibition of autonomous money movement or external customer communication in MVP/v1; all side effects require pre-declared risk tiering and approval gates.
- **Recommended Option**: Option B (Codified in new ADR-0012).
- **Decision Owner**: Principal Architect & Head of Product
- **Impacted Documents**: docs/01-product/PRD.md, docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md, docs/31-adr/ADR-0012-action-approval-autonomy-boundary.md
- **Impacted Invariants / NFRs**: INV-ACT-001, INV-ACT-003, NFR-SEC-001
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-04
- **Required Evidence**: ADR-0012-action-approval-autonomy-boundary.md authored; PRD §Product Boundaries codified.
- **Blocking Impact**: None. Hard constraint enforced across all downstream phases.

---

### DEC-009: Human Approval Boundary and Cryptographic Digest Binding
- **Decision ID**: DEC-009
- **Topic**: Approval center integrity, payload tampering prevention, and separation of duties.
- **Context**: Actions routed through human review must guarantee that the payload approved is identical to the payload dispatched.
- **Options**:
  1. Option A: Approval record references mutable investigation database rows.
  2. Option B: Cryptographic SHA-256 digest binding covering (tenant_id, action_type, target_payload, cost_ceiling, expires_at). Execution re-verifies digest and aborts if hash diverges. Self-approval by AI agent is strictly blocked.
- **Recommended Option**: Option B (Codified in new ADR-0012).
- **Decision Owner**: Security Architect & Principal Architect
- **Impacted Documents**: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md, docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md, docs/31-adr/ADR-0012-action-approval-autonomy-boundary.md
- **Impacted Invariants / NFRs**: INV-ACT-002, INV-ACT-003, NFR-REL-002
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-04
- **Required Evidence**: Codified in APPROVAL-ACTION-LOOP-SPEC.md §2.1 and ADR-0012.
- **Blocking Impact**: None. Governs Phase 06 implementation.

---

### DEC-010: Production Tenancy Isolation Architecture
- **Decision ID**: DEC-010
- **Topic**: Data isolation architecture across customer pricing and compliance tiers.
- **Context**: ADR-0005 establishes a three-tier model (Shared SMB, Dedicated DB Enterprise, Dedicated Cluster Regulated).
- **Options**:
  1. Option A: Shared database for all customers without database-level RLS.
  2. Option B: Mandatory Row-Level Security (RLS) with session-bound tenant_id for SMB tier; isolated schema/database for Enterprise; isolated physical VPC/cluster for Regulated.
- **Recommended Option**: Option B.
- **Decision Owner**: Principal Security Architect & Database Lead
- **Impacted Documents**: docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md, docs/27-database/DATABASE-SCHEMA.md, docs/31-adr/ADR-0005-tenant-isolation.md
- **Impacted Invariants / NFRs**: INV-TEN-001..003, NFR-TEN-001..002
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-03
- **Required Evidence**: Planned unit tests in packages/backend/tests/modules/tenancy/ and negative isolation matrix tests/tenancy/test_tenant_isolation_negative.py; execution evidence is still required.
- **Blocking Impact**: None for in-memory domain; live PostgreSQL RLS pending Rail 5 implementation (TASK-R05-001..004).

---

### DEC-011: Disaster Recovery and Backup/Restore Boundary
- **Decision ID**: DEC-011
- **Topic**: Recovery point objective (RPO), recovery time objective (RTO), and continuous restore rehearsal.
- **Context**: Data durability and business continuity require verified backup boundaries. Design target is RPO <= 5 minutes, RTO <= 30 minutes.
- **Options**:
  1. Option A: Nightly database dump to object storage without automated restore drills.
  2. Option B: Continuous WAL archiving to geographically replicated object storage, automated daily snapshot verification, and weekly automated ephemeral staging restore rehearsal.
- **Recommended Option**: Option B.
- **Decision Owner**: Storage Lead & SRE Lead
- **Impacted Documents**: docs/24-sre/DR-PLAN.md, docs/24-sre/BACKUP-RESTORE-VALIDATION-RUNBOOK.md, docs/03-requirements/WORKLOAD-ASSUMPTIONS.md
- **Impacted Invariants / NFRs**: INV-REL-001, NFR-DUR-001, NFR-REC-001
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-04
- **Required Evidence**: Runbooks codified in DR-PLAN.md and BACKUP-RESTORE-VALIDATION-RUNBOOK.md; empirical evidence pending staging drill execution (EVD-DR-001).
- **Blocking Impact**: Production sign-off blocked until empirical restore drill passes (TASK-P08-005).

---

### DEC-012: Compliance Evidence Ownership and Retention
- **Decision ID**: DEC-012
- **Topic**: Clear operational ownership and cryptographic immutability of compliance audit trails.
- **Context**: Compliance readiness frameworks mandate defined evidence owners and tamper-proof retention.
- **Options**:
  1. Option A: Ad-hoc log scraping by engineering when audits occur.
  2. Option B: Dual ownership model: SRE Lead owns automated machine telemetry and audit sink durability; Compliance Lead owns audit policy, periodic access reviews, and evidence bundle generation. Audit trail uses SHA-256 hash-chained immutable append-only ledger.
- **Recommended Option**: Option B.
- **Decision Owner**: Compliance Lead & SRE Lead
- **Impacted Documents**: docs/22-billing/AUDIT-LOG-SPEC.md, docs/25-compliance/COMPLIANCE-READINESS.md, docs/25-compliance/COMPLIANCE-EVIDENCE-RUNBOOK.md
- **Impacted Invariants / NFRs**: INV-AUD-001, INV-AUD-002, NFR-AUD-001
- **Status**: ACCEPTED
- **Decision Date**: 2026-09-04
- **Required Evidence**: Codified in COMPLIANCE-EVIDENCE-RUNBOOK.md and AUDIT-LOG-SPEC.md.
- **Blocking Impact**: None. Implemented in governance specifications.

---

## 3. Decision Summary Table

| ID | Topic | Status | Owner | Blocking Impact | Next Review |
|---|---|---|---|---|---|
| DEC-001 | Initial commercial vertical | ACCEPTED | Head of Product (Approved: Dương Vinh) | None (Locked: B2B SaaS) | Post-launch |
| DEC-002 | Currency, timezone & billing base | ACCEPTED | Platform Architect | None (Rail 1 verified) | Post-launch |
| DEC-003 | Data retention and residency | ACCEPTED | Legal / Compliance (Approved: Dương Vinh) | None (Configurable DPA) | Post-launch |
| DEC-004 | Cloud provider and region | ACCEPTED | SRE Lead (Approved: Dương Vinh) | None (Locked: AWS ECS/Aurora) | Post-launch |
| DEC-005 | Hosted LLM provider terms | ACCEPTED | AI Platform Lead (Approved: Dương Vinh) | None (Locked: Dual-Provider ZDR) | Post-launch |
| DEC-006 | Connector idempotency | ACCEPTED | Integration Lead | None (Spec codified) | Phase 07 |
| DEC-007 | Scoped-token support | ACCEPTED | Security Architect | None (ADR-0009 codified) | Phase 06 |
| DEC-008 | Autonomous action policy | ACCEPTED | Principal Architect | None (ADR-0012 codified) | Post-launch |
| DEC-009 | Human approval boundary | ACCEPTED | Security Architect | None (ADR-0012 codified) | Phase 06 |
| DEC-010 | Production tenancy model | ACCEPTED | Security / Database | None (ADR-0005 codified) | Rail 5 |
| DEC-011 | Backup/restore boundary | ACCEPTED | Storage / SRE Lead | None (Runbook codified) | Phase 08 Drill |
| DEC-012 | Compliance evidence ownership | ACCEPTED | Compliance / SRE | None (Runbook codified) | Phase 08 Audit |
