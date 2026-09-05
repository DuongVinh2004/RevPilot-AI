# Compliance Readiness, Privacy Framework, and Audit Governance

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 08 — Production Readiness, Release Governance & Operational Evidence
Rail Alignment: Rail 17 (Observability/FinOps/Audit), Rail 2 (Tenant Context & Lifecycle)
Owners: Legal & Compliance Lead & Security Architect
Approver: Dương Vinh
Last Reviewed Date: 2026-09-03
Traceability: `BR-004`, `INV-TEN-001..003`, `INV-PRV-001`, `INV-AUD-001..002`, `NFR-PRV-001`, `NFR-PRV-002`, `ADR-0005`, `ADR-0010`
Version: v1.0

---

## 1. Compliance Readiness Philosophy and Boundary

> [!WARNING]
> Software controls and evidence runbooks demonstrate technical readiness only. They do NOT constitute formal SOC 2, ISO 27001, HIPAA, or GDPR certification. Formal certification requires an independent assessment by an accredited third-party auditor.

1. **Zero Unverified Certification Claims**: RevPilot AI does not claim active third-party certifications prior to formal independent auditor attestation.
2. **Standardized Control Lifecycle**:
   - Every control is classified strictly as: `Designed`, `Implemented`, `Tested`, `Evidenced`, `Reviewed`, `Accepted`, `Blocked`, or `Not Applicable`.
   - The status `Evidenced` strictly requires an immutable cryptographic artifact or test report with SHA-256 seal (`COMPLIANCE-EVIDENCE-RUNBOOK.md`).
3. **Explicit UNKNOWN Boundary (`NFR-PRV-002`)**:
   - Jurisdictional data residency mandates (EU vs US vs APAC) remain flagged as `UNKNOWN` pending pilot customer contracts and legal counsel determination.
   - Statutory data retention durations (e.g. 3 years vs 7 years) remain `UNKNOWN`.
   - The platform provides parameterized configuration for retention schedules and geographic isolation, strictly avoiding hardcoding speculative legal rules into source code or database migrations.

---

## 2. Regulatory Alignment Mapping

### 2.1 GDPR Technical Alignment
- **Article 15 (Right of Access)**: Satisfied via automated tenant export packaging (`TASK-P07-001`, `docs/18-data-governance/DATA-GOVERNANCE.md`).
- **Article 17 (Right to Erasure / "Be Forgotten")**: Satisfied via 10-store cascade deletion saga with dual human approval token and deletion certificate (`TASK-P07-001`).
- **Article 18 (Restriction of Processing)**: Satisfied via `LEGAL_HOLD` state in Tenant Operations (`TENANT-OPERATIONS-SPEC.md`).
- **Article 32 (Security of Processing)**: Hard tenant RLS, TLS 1.3 in transit, AES-256-GCM at rest, ephemeral credential broker, zero raw secrets in agent runtime.

### 2.2 SOC 2 Type II Trust Services Criteria Mapping
- **Common Criteria (Security)**: `CTL-AUTH-01` (SSO/MFA), `CTL-ISO-01` (Tenant RLS), `CTL-SEC-01` (Secret Broker), `CTL-SEC-02` (Vulnerability scanning).
- **Availability**: `PRG-SRE-01` (99.0% availability target), `CTL-DR-01` (Disaster recovery restore rehearsals).
- **Confidentiality**: `CTL-AUD-02` (PII redaction), `CTL-PRV-01` (Sealed export).
- **Processing Integrity**: `INV-ACT-002` (Cryptographic action approval digests), `INV-WF-001` (Temporal deterministic replay).

### 2.3 Thailand Personal Data Protection Act (PDPA B.E. 2562) Technical Alignment
- **Section 30 (Right of Access)**: Data subjects retain the right to request access and obtain copies of personal data; satisfied via automated tenant data export packages (`TASK-P07-001`, `docs/18-data-governance/DATA-GOVERNANCE.md`).
- **Section 33 (Right to Erasure / Destruction)**: Data subjects retain the right to demand erasure, destruction, or temporary anonymization; satisfied via tenant cascade erasure sagas across persistent stores (`TASK-P07-001`).
- **Section 34 (Right to Restriction of Processing)**: Satisfied via programmatic `LEGAL_HOLD` and `SUSPENDED` lifecycle states (`docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md`).
- **Section 28 & 29 (Cross-Border Data Transfers)**: Transferring data outside Thailand requires destination adequacy standards; aligned with parameterized regional routing (`NFR-PRV-002`) and fail-closed isolation gates.

---

## 3. Subprocessor Governance and AI Boundary
1. **Subprocessor Registry**: Any third-party API or hosting service processing customer data must be registered in the subprocessor catalog.
2. **Model Vendor Data Agreements**:
   - Enterprise zero-data-retention agreements are mandatory for all external foundation model providers.
   - Foundation models are strictly barred from training on customer prompt or completion data.
3. **Tenant Opt-In / Consent**: Tenants must be able to select or restrict which approved foundation model providers may process their data.

---

## 4. Acceptance Criteria
1. `AC-CMP-01`: Compliance matrix maintains zero unsubstantiated certification claims and accurately records `UNKNOWN` for retention and residency.
2. `AC-CMP-02`: Operational evidence collection runbook is codified and automated via script interfaces (`COMPLIANCE-EVIDENCE-RUNBOOK.md`).
