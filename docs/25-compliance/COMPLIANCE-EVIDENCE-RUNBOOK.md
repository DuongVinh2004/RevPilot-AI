# Compliance Evidence Collection and Audit Readiness Runbook

Status: Accepted
Initiative: REVPILOT
Phase: Phase 08 — Production Readiness, Release Governance & Operational Evidence
Owner Role: Compliance Lead & Security Architect
Approver: Dương Vinh
Last Reviewed Date: 2026-09-03
Traceability: `ADR-0009`, `ADR-0010`, `NFR-SEC-001..002`, `NFR-AUD-001`, `NFR-PRV-001..002`, `INV-SEC-001..003`, `INV-AUD-001..002`, `INV-PRV-001`
Version: v1.0

---

## 1. Purpose
Defines operational procedures and automated tooling for collecting, verifying, cryptographically signing, and preserving audit evidence required for regulatory compliance evaluations (SOC 2 Type II, ISO 27001, GDPR readiness).

## 2. Scope
Covers identity, data isolation, cryptographic keys, system audit trails, vulnerability management, data lifecycle (export/deletion), and incident governance across all RevPilot AI subsystems.

## 3. Non-Goals
- Claiming formal third-party certification or regulatory compliance stamp before external CPA/auditor evaluation.
- Substituting architecture documentation for live evidence artifacts.

> [!WARNING]
> Software controls and evidence runbooks demonstrate technical readiness only. They do NOT constitute formal SOC 2, ISO 27001, HIPAA, or GDPR certification. Formal certification requires an independent assessment by an accredited third-party auditor.

## 4. Evidence Classification and Control Status Model

All compliance evidence controls must be tracked under the following standardized status lifecycle:
1. `Designed`: Control architecture and specification documented.
2. `Implemented`: Software code or configuration in place.
3. `Tested`: Automated or manual test suite verifies functionality.
4. `Evidenced`: Immutable, cryptographically verifiable artifact stored in evidence vault.
5. `Reviewed`: Internal security and compliance review complete.
6. `Accepted`: Formal sign-off by designated control owner.
7. `Blocked`: Critical deficiency or upstream blocker prevents evidence generation.
8. `Not Applicable`: Control out of scope for current architecture tier.

---

## 5. Compliance Evidence Matrix

| Control Domain | Control ID | Specific Requirement | Evidence Artifact Required | Collection Cadence | Collection Method | Current Status | Control Owner |
|---|---|---|---|---|---|---|---|
| **Authentication** | `CTL-AUTH-01` | Multi-tenant OIDC/SAML with PKCE & MFA enforcement | IdP configuration export & authentication trace log | Monthly | Automated OTel log parser | Designed / Pending | IAM Lead |
| **Authorization** | `CTL-AUTH-02` | Least-privilege RBAC / ReBAC role assignment | Database permission dump & policy AST audit | Weekly | Script `export_rbac_permissions.py` | Designed / Pending | Security Lead |
| **Tenant Isolation** | `CTL-ISO-01` | 100% Negative cross-tenant query rejection | Automated adversarial test report (`TEST-TEN-001..011`) | Per Release | CI test runner artifact | Implemented in-memory / DB RLS and execution evidence pending | Tenancy Lead |
| **Encryption at Rest** | `CTL-CRYP-01` | AES-256 / CMEK encryption across all persistent volumes | Cloud KMS key metadata & disk encryption manifest | Monthly | Cloud provider CLI audit script | Designed (CMEK UNKNOWN) | Platform SRE |
| **Encryption in Transit**| `CTL-CRYP-02` | TLS 1.3 mandatory on all ingress & inter-service mTLS | SSL Labs benchmark report & Envoy mTLS config | Monthly | Automated TLS probe scan | Designed / Pending | Platform SRE |
| **Secret Lifecycle** | `CTL-SEC-01` | Zero raw secrets; 90-day automatic key rotation | Secret rotation audit events (`security.secret.rotated`) | Continuous | Audit log filter pipeline | Designed / Pending | Security Lead |
| **Audit Immutability** | `CTL-AUD-01` | Append-only ledger with cryptographic hash chaining | Audit ledger root block hash verification log | Daily | Daily cryptographic audit cron | Designed / Pending | Audit Lead |
| **Audit Redaction** | `CTL-AUD-02` | Zero credentials or PII in audit records | DLP scan output over rolling 30-day audit log sample | Weekly | Automated regex DLP inspector | Designed / Pending | Privacy Lead |
| **Tenant Export** | `CTL-PRV-01` | Automated customer data export package with SHA-256 seal| Generated tenant export archive manifest & signature | On-demand | Export worker test suite | Designed / Pending | Data Lead |
| **Cascade Deletion** | `CTL-PRV-02` | Complete cascade erasure across all 10 persistent stores | Deletion certificate signed digest (`FR-CTL-003`) | On-demand | Deletion saga verifier report | Designed / Pending | Data Lead |
| **Legal Hold** | `CTL-PRV-03` | Immutable block on data deletion under active litigation | Negative deletion rejection audit log (409 Conflict) | Monthly | CI integration test run | Designed / Pending legal policy | Legal Lead |
| **Vulnerability Mgmt** | `CTL-SEC-02` | Zero Critical/High CVEs in container base images | Trivy / Grype vulnerability scan report | Per Commit | CI container security scanner | Designed / Pending | DevSecOps Lead |
| **Dependency Review** | `CTL-SEC-03` | License compliance & supply chain signature verification | SBOM (SPDX/CycloneDX) & Dependency-Check report | Per Release | Automated SBOM generator | Designed / Pending | DevSecOps Lead |
| **Backup Verification** | `CTL-DR-01` | Daily encrypted snapshot with verified restore rehearsal | DR restore rehearsal execution log (`REH-P07-04`) | Monthly | Staging restore exercise script | Designed / Pending execution | SRE Lead |
| **Incident Governance** | `CTL-INC-01` | Documented post-mortem and RCA for all P0/P1 incidents | Incident post-mortem document signed by SRE Lead | Per Incident | Incident management repository | Designed | SRE Lead |
| **Access Reviews** | `CTL-GOV-01` | Quarterly review of platform operator access grants | Privileged access review sign-off sheet | Quarterly | Human-in-the-loop review | Designed | Security Lead |

---

## 6. Automated Evidence Packaging and Vault Ingestion

### 6.1 Collection Script Interface
Evidence artifacts are packaged using the standard compliance CLI:
```bash
python scripts/compliance/collect_evidence.py \
  --period 2026-Q3 \
  --output /var/evidence/2026-Q3-bundle.tar.gz \
  --sign-key-ref "ref://kms/evidence-signer-key"
```

### 6.2 Evidence Manifest Format
Every evidence package includes an immutable `evidence-manifest.json`:
```json
{
  "period": "2026-Q3",
  "collected_at": "2026-09-03T23:50:00Z",
  "collector_agent": "revpilot-compliance-worker v0.8",
  "artifacts": [
    {
      "control_id": "CTL-ISO-01",
      "filename": "test-tenancy-isolation-report.xml",
      "sha256": "[SHA256_OF_NONEMPTY_EXECUTED_ARTIFACT_REQUIRED]",
      "evaluator": "pytest v8.0",
      "result": "[NOT_EXECUTED_OR_RETAINED_RESULT]"
    }
  ],
  "bundle_signature": "MEQCIF6...[ECDSA-P256-SHA256]..."
}
```

## 7. Acceptance Criteria
1. `AC-COMP-01`: Evidence collection script packages 100% of defined control outputs into a cryptographically sealed archive.
2. `AC-COMP-02`: Zero controls in the Compliance Matrix are assigned status `Evidenced` without an associated non-empty SHA-256 digest artifact.
