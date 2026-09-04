# Documentation Standards Matrix

Date: 2026-09-04
Auditor: Antigravity Documentation Quality Auditor
Scope: Gap analysis against applicable external standards

> **DISCLAIMER**: This matrix is a documentation gap analysis, NOT a compliance certification. Formal certification requires accredited third-party auditors.

---

## 1. ISO/IEC 25010 (Systems/Software Quality Model)

| Characteristic | Sub-characteristic | Addressed By | Gap | Status |
|---|---|---|---|---|
| Functional Suitability | Completeness | PRD, SRS, Domain specs | 66 FR gaps (F-COMP-001) | PARTIAL |
| Functional Suitability | Correctness | Evaluation benchmarks | All benchmarks DESIGN TARGET | PARTIAL |
| Functional Suitability | Appropriateness | Business Domain Model | Covered | PASS |
| Performance Efficiency | Time behaviour | NFR-LAT-001, NFR-LAT-002 | Zero measured results | DESIGN ONLY |
| Performance Efficiency | Resource utilization | WORKLOAD-ASSUMPTIONS | Zero measured results | DESIGN ONLY |
| Performance Efficiency | Capacity | NFR-THR-001, NFR-THR-002 | Zero load tests (EVD-LOD-001) | NOT EXECUTED |
| Compatibility | Interoperability | CONNECTOR-PLATFORM-SPEC | Connector adapters not built | DESIGN ONLY |
| Usability | Accessibility | — | No WCAG 2.2 AA coverage | **MISSING** |
| Usability | User interface aesthetics | FRONTEND-SPEC (10 lines) | Stub only (F-FRONTEND-001) | **INADEQUATE** |
| Reliability | Maturity | SRE-SPEC, SLOs | Zero production data | DESIGN ONLY |
| Reliability | Availability | NFR-AVL-001 (99.9% target) | Zero measurement (EVD-SLO-001) | NOT EXECUTED |
| Reliability | Fault tolerance | DR-PLAN, Incident Runbook | Zero DR drills (EVD-DR-001) | NOT EXECUTED |
| Reliability | Recoverability | BACKUP-RESTORE-RUNBOOK | Zero restore exercises (EVD-BCK-001) | NOT EXECUTED |
| Security | Confidentiality | SECURITY-ARCHITECTURE, RLS | Zero pen tests (EVD-SEC-001) | DESIGN ONLY |
| Security | Integrity | AUDIT-LOG-SPEC, hash chains | Zero audit chain verification | DESIGN ONLY |
| Security | Non-repudiation | Immutable audit log design | Not implemented | DESIGN ONLY |
| Security | Accountability | IAM-SPEC, break-glass | Not implemented | DESIGN ONLY |
| Security | Authenticity | ENTERPRISE-IDENTITY-INTEGRATION | Not implemented | DESIGN ONLY |
| Maintainability | Modularity | MODULE-BOUNDARIES, ADR-0001 | Strong design; 2 modules implemented | PARTIAL |
| Maintainability | Reusability | DEPENDENCY-RULES | Design target; execution evidence pending | PENDING EVIDENCE |
| Maintainability | Testability | TEST-STRATEGY | Historical 100-test claim; not independently rerun | PENDING REVALIDATION |
| Portability | Adaptability | DEPLOYMENT-ARCHITECTURE | Cloud provider UNKNOWN | BLOCKED |

---

## 2. ISO/IEC 25012 (Data Quality Model)

| Characteristic | Addressed By | Status |
|---|---|---|
| Accuracy | DATA-QUALITY-LINEAGE-SPEC, DQ rules | DESIGN ONLY |
| Completeness | DATA-QUALITY-LINEAGE-SPEC, DQ-REQ-001 | DESIGN ONLY |
| Consistency | CANONICAL-DATA-MODEL, EVENT-CONTRACTS | DESIGN ONLY |
| Credibility | EVIDENCE-PROVENANCE-SPEC, citations | DESIGN ONLY |
| Currentness | Time semantics (as_of_time, effective_from) | DESIGN ONLY |
| Accessibility | API-STANDARDS, METRIC-SERVICE-SPEC | DESIGN ONLY |
| Compliance | DATA-GOVERNANCE, COMPLIANCE-READINESS | DESIGN ONLY (NFR-PRV-002 UNKNOWN) |
| Confidentiality | PII masking, DLP redaction, classification tiers | DESIGN ONLY |
| Efficiency | METRIC-SERVICE-SPEC query timeouts | DESIGN ONLY |
| Precision | Money (BIGINT cents), metric SQL formulas | DESIGN ONLY |
| Traceability | Data lineage, source_entity_ids | DESIGN ONLY |
| Understandability | GLOSSARY, normative terms | PASS |
| Availability | SRE-SPEC tier targets | NOT EXECUTED |
| Portability | Export contract, manifest.sha256 | DESIGN ONLY |
| Recoverability | BACKUP-RESTORE, deletion tombstones | NOT EXECUTED |

---

## 3. ISO 27001/27002/27017/27018/27701

| Control Area | Addressed By | Implementation Status | Gap |
|---|---|---|---|
| A.5 Information Security Policies | SECURITY-ARCHITECTURE, INVARIANT-REGISTRY | DESIGNED | No formal ISMS policy document |
| A.6 Organization of Info Security | Owner fields in specs | PARTIAL | No dedicated CISO role defined |
| A.7 Human Resource Security | — | **MISSING** | No personnel security controls |
| A.8 Asset Management | DATA-GOVERNANCE classification tiers | DESIGNED | No asset inventory |
| A.9 Access Control | IAM-SPEC, RBAC/ABAC, break-glass | DESIGNED | Not implemented |
| A.10 Cryptography | AES-256-GCM, SHA-256, TLS 1.3 | DESIGNED | CMEK UNKNOWN (ADR-0009) |
| A.11 Physical Security | — | **MISSING** | Cloud provider dependency |
| A.12 Operations Security | SRE-SPEC, Incident Response | DESIGNED | No operational evidence |
| A.13 Communications Security | TLS 1.3, mTLS, egress proxy | DESIGNED | Not implemented |
| A.14 System Acquisition | DEPENDENCY-RULES, MODULE-BOUNDARIES | DESIGNED | No SDLC security gates |
| A.15 Supplier Relationships | — | **MISSING** | No vendor risk assessment |
| A.16 Incident Management | INCIDENT-RESPONSE-RUNBOOK | DESIGNED | No incidents processed |
| A.17 Business Continuity | DR-PLAN, BACKUP-RESTORE | DESIGNED | Zero DR exercises |
| A.18 Compliance | COMPLIANCE-READINESS, COMPLIANCE-RUNBOOK | DESIGNED | No legal review completed |
| 27017 Cloud Controls | DEPLOYMENT-ARCHITECTURE | DESIGNED | Cloud provider UNKNOWN |
| 27018 PII in Cloud | DATA-GOVERNANCE, PII masking | DESIGNED | Residency UNKNOWN |
| 27701 Privacy | DATA-GOVERNANCE, INV-PRV-001 | DESIGNED | DPA/DPIA not created |

---

## 4. NIST Frameworks

### NIST Cybersecurity Framework (CSF)

| Function | Addressed By | Status |
|---|---|---|
| Identify | THREAT-MODEL, RISK-REGISTER, SYSTEM-BOUNDARIES | DESIGNED |
| Protect | IAM-SPEC, RLS, SECURITY-ARCHITECTURE | DESIGNED |
| Detect | ANOMALY-DOMAIN-SPEC (business), OBSERVABILITY-SPEC (ops) | DESIGNED |
| Respond | INCIDENT-RESPONSE-RUNBOOK | DESIGNED |
| Recover | DR-PLAN, BACKUP-RESTORE-RUNBOOK | DESIGNED |

### NIST SSDF (Secure Software Development)

| Practice | Addressed By | Status |
|---|---|---|
| PO: Define Security Requirements | INVARIANT-REGISTRY, NFR-BASELINE | DESIGNED |
| PW: Protect Software | DEPENDENCY-RULES, forbidden edges | PARTIAL (2 modules) |
| RV: Respond to Vulnerabilities | INCIDENT-RESPONSE-RUNBOOK | DESIGNED |
| PS: Produce Well-Secured Software | TEST-STRATEGY (negative tests) | PARTIAL (100 tests) |

### NIST AI RMF

| Category | Addressed By | Status |
|---|---|---|
| Govern | AI-GOVERNANCE, MODEL-RELEASE-PROCESS | DESIGNED |
| Map | AI-ARCHITECTURE, MULTI-AGENT-SPEC | DESIGNED |
| Measure | EVALUATION-FRAMEWORK, Benchmark Protocols | DESIGNED (NOT EXECUTED) |
| Manage | UNSUPPORTED-CLAIM-POLICY, FAIRNESS-SLICE-EVAL | DESIGNED (NOT EXECUTED) |

---

## 5. OWASP

### OWASP ASVS 4.0

| Area | Addressed By | Status |
|---|---|---|
| V1: Architecture | SYSTEM-ARCHITECTURE, DEPENDENCY-RULES | DESIGNED |
| V2: Authentication | IAM-SPEC, ENTERPRISE-IDENTITY-INTEGRATION | DESIGNED |
| V3: Session Management | Session max age 28800s, JTI replay cache | DESIGNED |
| V4: Access Control | RBAC/ABAC, delegation tokens | DESIGNED |
| V5: Validation | Schema validation, DQ rules | DESIGNED |
| V7: Error Handling | Canonical error envelope | DESIGNED |
| V8: Data Protection | Classification tiers, PII masking | DESIGNED |
| V9: Communications | TLS 1.3, mTLS, egress proxy | DESIGNED |
| V10: Malicious Code | — | **MISSING** (no SAST/DAST) |
| V11: Business Logic | Domain invariants, fail-closed | DESIGNED |
| V12: Files and Resources | 10MB payload limit, 8-level nesting | DESIGNED |
| V13: API | API-STANDARDS, idempotency keys | DESIGNED |
| V14: Configuration | env.example, no committed secrets | PARTIAL |

### OWASP API Security Top 10

| Risk | Addressed By | Status |
|---|---|---|
| API1: Broken Object Level Auth | RLS + TenantContext | DESIGNED |
| API2: Broken Authentication | OIDC/PKCE, JTI replay | DESIGNED |
| API3: Broken Object Property Level Auth | Schema validation, field allowlists | DESIGNED |
| API4: Unrestricted Resource Consumption | Rate limits, budget ceilings | DESIGNED |
| API5: Broken Function Level Auth | RBAC/ABAC, capability catalog | DESIGNED |
| API6: Unrestricted Access to Sensitive Flows | Tool Gateway, approval loop | DESIGNED |
| API7: SSRF | Egress proxy DNS allowlist | DESIGNED |
| API8: Security Misconfiguration | ADR-0008 container hardening | DESIGNED |
| API9: Improper Inventory Management | API-STANDARDS canonical endpoints | DESIGNED |
| API10: Unsafe Consumption of APIs | Untrusted content tags, HMAC verification | DESIGNED |

### OWASP LLM Top 10

| Risk | Addressed By | Status |
|---|---|---|
| LLM01: Prompt Injection | Untrusted tags, injection quarantine | DESIGNED |
| LLM02: Insecure Output Handling | Schema validation, unsupported claim policy | DESIGNED |
| LLM03: Training Data Poisoning | No model training on customer data | DESIGNED |
| LLM04: Model Denial of Service | Token/cost budgets, hard stops | DESIGNED |
| LLM05: Supply Chain Vulnerabilities | Model pinning, artifact governance | DESIGNED |
| LLM06: Sensitive Information Disclosure | CoT suppression, PII masking | DESIGNED |
| LLM07: Insecure Plugin Design | Capability catalog, Tool Gateway | DESIGNED |
| LLM08: Excessive Agency | INV-ACT-001, zero ambient authority | DESIGNED |
| LLM09: Overreliance | INV-AI-001, evidence-backed claims only | DESIGNED |
| LLM10: Model Theft | No model training, provider contracts | DESIGNED |

---

## 6. GDPR / PDPA

| Article | Addressed By | Status | Gap |
|---|---|---|---|
| Art 5 (Data minimization) | DATA-GOVERNANCE classification | DESIGNED | No DPO appointed |
| Art 6 (Lawful basis) | — | **MISSING** | No lawful basis documented |
| Art 13/14 (Privacy notice) | — | **MISSING** | No privacy notice |
| Art 15 (Right of access) | Export contract | DESIGNED | Not implemented |
| Art 17 (Right to erasure) | Cascade deletion saga | DESIGNED | Not implemented |
| Art 18 (Right to restriction) | Legal hold mechanism | DESIGNED | Not implemented |
| Art 20 (Data portability) | Export manifest.sha256 | DESIGNED | Not implemented |
| Art 25 (Privacy by design) | DATA-GOVERNANCE, PII masking | DESIGNED | |
| Art 28 (Processor contracts) | — | **MISSING** | No DPA template |
| Art 32 (Security measures) | Security controls matrix | DESIGNED | |
| Art 33 (Breach notification) | INCIDENT-RESPONSE-RUNBOOK | DESIGNED | No 72h process |
| Art 35 (DPIA) | — | **MISSING** | No DPIA conducted |
| NFR-PRV-002 | Retention/residency | **UNKNOWN** | Blocks GDPR compliance |

---

## 7. SOC 2

| Trust Service Criterion | Addressed By | Implementation | Evidence |
|---|---|---|---|
| CC6.1 Logical Access | IAM-SPEC, RBAC/ABAC | DESIGNED | NONE |
| CC6.2 Credential Management | Credential Broker, Argon2id | DESIGNED | NONE |
| CC6.3 Encryption | AES-256-GCM, TLS 1.3 | DESIGNED | NONE |
| CC7.1 Configuration Management | DEPLOYMENT-ARCHITECTURE | DESIGNED | NONE |
| CC7.2 Change Management | RELEASE-CANARY-ROLLBACK | DESIGNED | NONE |
| CC7.3 Vulnerability Management | — | **MISSING** | NONE |
| CC7.4 Incident Detection | OBSERVABILITY-SPEC | DESIGNED | NONE |
| CC8.1 Testing | TEST-STRATEGY | PLANNED / historical claim only | Retained execution evidence required |
| A1.1 Availability Monitoring | SLO targets | DESIGNED | NONE |
| A1.2 Disaster Recovery | DR-PLAN | DESIGNED | NONE |
| C1.1 Data Classification | 4-tier classification | DESIGNED | NONE |
| PI1.1 Data Integrity | Immutable audit log | DESIGNED | NONE |
