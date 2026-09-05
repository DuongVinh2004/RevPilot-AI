# Master Open Blockers Register

Date: 2026-09-04  
Status: Authoritative Active Blocker Tracking  
Owner: Principal Platform Architect & SRE Lead  

---

## 1. Active Go-Live and Execution Blockers

### BLK-001: Statutory Data Retention Windows and Jurisdictional Residency
- **Blocker ID**: BLK-001
- **Description**: Customer data retention periods and geographical residency rules confirmed by Repository Owner Dương Vinh (DEC-003 Option B).
- **Affected Phase / Rail**: Phase 07 (Commercial Pilots) & Phase 08 (Compliance Readiness).
- **Affected Requirements**: NFR-PRV-002, INV-PRV-001, INV-AUD-001.
- **Why Blocking**: Resolved. Configurable tenant-level retention policies enforced with fail-closed hard stop on unconfigured jurisdictions.
- **Owner**: Compliance Lead & External Legal Counsel (Approved: Dương Vinh).
- **Required Decision**: DEC-003 in docs/31-adr/DECISION-CLOSURE-REGISTER.md (ACCEPTED in RUN-R06-001).
- **Required Evidence**: Executed Data Processing Agreement template and statutory jurisdiction schedule.
- **Mitigation**: Default to strict configurable tenant policies with fail-closed hard stop on unconfigured jurisdictions.
- **Target Resolution**: Resolved 2026-09-04.
- **Status**: RESOLVED (Decision accepted in RUN-R06-001).

---

### BLK-002: Production Cloud Provider and Container Execution Platform
- **Blocker ID**: BLK-002
- **Description**: Production cloud hyperscaler confirmed as AWS (ECS Fargate + RDS Aurora PostgreSQL + Secrets Manager + KMS) per DEC-004 Option A.
- **Affected Phase / Rail**: Phase 08 (Staging/Production Deployment).
- **Affected Requirements**: NFR-REL-001, ADR-0008, ADR-0009.
- **Why Blocking**: Resolved. Infrastructure target selected and locked to AWS managed containers.
- **Owner**: SRE Lead & Platform Architecture (Approved: Dương Vinh).
- **Required Decision**: DEC-004 in docs/31-adr/DECISION-CLOSURE-REGISTER.md (ACCEPTED in RUN-R06-001).
- **Required Evidence**: Approved infrastructure budget and Terraform/OpenTofu provider deployment smoke test.
- **Mitigation**: Develop on local container composition (Docker Compose) with portable OCI container contracts.
- **Target Resolution**: Resolved 2026-09-04.
- **Status**: RESOLVED (Decision accepted in RUN-R06-001).

---

### BLK-003: Hosted AI Model Provider Terms and Zero-Retention SLA
- **Blocker ID**: BLK-003
- **Description**: Hosted LLM provider strategy confirmed as Dual-Provider (Claude 3.5 Sonnet / Azure OpenAI primary, Vertex AI fallback) with Zero Data Retention per DEC-005 Option D.
- **Affected Phase / Rail**: Phase 03 (Governed Investigation) & Phase 04 (Causal AI).
- **Affected Requirements**: INV-AI-001, INV-SEC-002, NFR-AI-001..007, ADR-0011.
- **Why Blocking**: Resolved. Dual-provider architecture locked with mandatory Zero Data Retention SLA.
- **Owner**: AI Platform Lead & Security Architect (Approved: Dương Vinh).
- **Required Decision**: DEC-005 in docs/31-adr/DECISION-CLOSURE-REGISTER.md (ACCEPTED in RUN-R06-001).
- **Required Evidence**: Signed Business Associate Agreement / Zero Data Retention terms and golden set evaluation report (EVAL-REP-001).
- **Mitigation**: Use local deterministic fake model gateway for all development and unit testing.
- **Target Resolution**: Resolved 2026-09-04.
- **Status**: RESOLVED (Decision accepted in RUN-R06-001).

---

### BLK-004: Downstream Control Plane Rails 3–5 Not Yet Implemented
- **Blocker ID**: BLK-004
- **Description**: Rail 3 (Authentication), Rail 4 (Authorization), and Rail 5 (Persistence Isolation RLS) are not yet GREEN.
- **Affected Phase / Rail**: Rails 3–5, Phases 03–08.
- **Affected Requirements**: INV-IAM-001..002, INV-TEN-001..003, NFR-TEN-001..002.
- **Why Blocking**: Micro-Task Rail System strictly prohibits Phase 03–08 execution until the foundations are implemented and independently validated. Current source review also found missing service-boundary authorization, caller-constructible privileged state, non-revocable contexts, mutable tenant aggregates, and duplicate-ID overwrite semantics; documentation does not remediate these code-level conditions.
- **Owner**: Core Platform Engineering.
- **Required Decision**: Closure of BLK-006 and approval of foundation documentation pack. (Resolved in RUN-R03-001).
- **Required Evidence**: Implemented authentication/authorization/RLS boundaries; retained negative authorization, forged-privileged-context, context-revocation, duplicate-ID, aggregate-integrity and PostgreSQL RLS concurrency artifacts. Task completion status must be supported by actual execution artifacts.
- **Mitigation**: TASK-R03-001 is now admitted into execution queue following BLK-006 closure; implementation must execute under strict fail-closed rails.
- **Target Resolution**: Resolved. Rails 3–5 implemented and verified GREEN (TASK-R03-001..004, TASK-R04-001..004, TASK-R05-001..004 PASS; 343/343 backend tests pass).
- **Status**: CLOSED (Rails 3–5 fully implemented and verified GREEN).

---

### BLK-005: Absence of Empirical Non-Functional and Disaster Recovery Evidence
- **Blocker ID**: BLK-005
- **Description**: 72-hour soak test, 1,000 req/s load test, and cold restore DR rehearsal have not been executed.
- **Affected Phase / Rail**: Phase 08 (Production Readiness).
- **Affected Requirements**: NFR-REL-001, NFR-REC-001, INV-REL-001..002.
- **Why Blocking**: Platform DoD mandates empirical proof before production declaration.
- **Owner**: SRE Lead & Storage Architect.
- **Required Decision**: DEC-011.
- **Required Evidence**: Staging execution artifacts (LOAD-STRESS-SOAK-VALIDATION.md, BACKUP-RESTORE-VALIDATION.md).
- **Mitigation**: All test harnesses and runbooks are pre-authored and ready for automated pipeline triggering.
- **Target Resolution**: Phase 08 staging execution window.
- **Status**: PENDING UPSTREAM EXECUTION.

---

### BLK-006: Documentation Authority Acceptance Pending
- **Blocker ID**: BLK-006
- **Description**: The content closure pack reconciles functional requirements, NFRs, evidence semantics and policy contradictions. Foundational documentation pack accepted on 2026-09-04 via explicit confirmation by Repository Owner / Platform Approver Duong Vinh covering all four required approval scopes.
- **Affected Phase / Rail**: Any implementation work depending on unresolved product, security, SLO or AI policy authority.
- **Affected Requirements**: FR closure catalog, NFR baseline, credential/approval policy, SLO and AI governance gates.
- **Why Blocking**: Documentation content is not implementation authorization. Work must not choose product/security thresholds where the accountable approver has not accepted them.
- **Owner**: Principal Architecture, Product Owner, Security Architect, SRE Lead and AI Governance Lead.
- **Required Decision**: Approval or explicit revision of `DOCUMENTATION-CLOSURE-DECISIONS.md` and `FR-CLOSURE-CATALOG.md`. (Approved 2026-09-04).
- **Required Evidence**: Explicit user approval record `execution/APPROVAL-RECORD-RUN-R03-001.md`.
- **Mitigation**: Fully resolved. Foundation pack accepted; implementation admission unblocked for TASK-R03-001.
- **Target Resolution**: Resolved 2026-09-04.
- **Status**: CLOSED (Accepted in RUN-R03-001 / APPROVAL-RECORD-RUN-R03-001.md).

---

## 2. Summary of Open Blockers

| Blocker ID | Description | Owner | Status | Blocking Scope |
|---|---|---|---|---|
| BLK-001 | Statutory data retention & residency | Legal / Compliance | RESOLVED (DEC-003 accepted in RUN-R06-001) | Configurable tenant-level retention; fail-closed on unconfigured jurisdictions |
| BLK-002 | Production cloud provider & runtime | SRE Lead | RESOLVED (DEC-004 accepted in RUN-R06-001) | AWS ECS Fargate + RDS Aurora selected; staging deployment pending |
| BLK-003 | Hosted AI model terms & zero retention | AI Platform Lead | RESOLVED (DEC-005 accepted in RUN-R06-001) | Dual-provider (Claude 3.5 Sonnet / Azure OpenAI); Zero Data Retention SLA required |
| BLK-004 | Rails 3–5 implementation pending | Platform Engineering | CLOSED (Rails 3–5 GREEN) | None (Foundations implemented and verified) |
| BLK-005 | Missing empirical test & DR evidence | SRE Lead | PENDING | Certified Production Readiness declaration |
| BLK-006 | Documentation authority acceptance | Architecture / Domain Approvers | CLOSED (Accepted in RUN-R03-001) | None (Resolved for implementation admission) |
