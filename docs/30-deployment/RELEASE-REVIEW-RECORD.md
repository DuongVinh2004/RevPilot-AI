# Deployment and Release Review Operational Record

Record ID: REC-REL-001  
Owner: Release Lead & SRE Lead  
Status: OPERATIONAL TEMPLATE & DEPLOYMENT RECORD (Not an executed release review)  
Reference: RELEASE-CANARY-ROLLBACK-SPEC.md, DEPLOYMENT-ARCHITECTURE.md  

---

## 1. Release Identification and Provenance
- **Release Identifier**: REL-[YYYYMMDD]-[SEMVER]
- **Deployment Timestamp (UTC)**: YYYY-MM-DD HH:MM:SS
- **Target Environment**: Staging / Production
- **Release Coordinator**: [Name / Role]
- **SRE Gatekeeper**: [Name / Role]

---

## 2. Artifacts and Build Manifests
- **Application Container Image**: `revpilot/app:[SEMVER]` (Digest: `sha256:[HASH]`)
- **Temporal Worker Image**: `revpilot/worker:[SEMVER]` (Digest: `sha256:[HASH]`)
- **Database Migration Version**: `alembic_v[X.Y.Z]`
- **Model Registry Bundle**: `models_bundle_v[X.Y]`
- **Prompt Registry Snapshot**: `prompts_v[X.Y]` (`SHA256:[HASH]`)
- **SBOM Verification**: Confirmed clean; 0 Critical/High CVEs.

---

## 3. Scope of Change
- **Features Included**: [List of JIRA tickets / Features promoted]
- **Bug Fixes**: [List of resolved bug tickets]
- **Breaking API Changes**: [None / List of deprecated endpoints per API-STANDARDS.md]

---

## 4. Database Schema Migration Review
- **Migration Pattern Applied**: Expand / Contract (ADR-0004)
- **Backward Compatibility Verified**: Older application pods operate without failure on expanded schema.
- **Migration Duration**: [Measured execution time in seconds]
- **Lock Acquisition Impact**: Zero exclusive table locks exceeding 100ms.

---

## 5. Canary Progression and Rollback Evaluation
- **Canary Cohort Selection**: [Internal dogfood + Opt-in pilot tenants]
- **Canary Stage 1 (5% / 1h)**: Passed; Error rate < 0.1%, P95 latency stable.
- **Canary Stage 2 (25% / 4h)**: Passed; Error rate < 0.1%, P95 latency stable.
- **Canary Stage 3 (100%)**: Full promotion complete.
- **Rollback Evaluation**: Rollback triggers not breached; rollback not invoked.

---

## 6. Associated Incidents and Remediation
- **Incidents Opened During Window**: None (or detail INC-[ID])
- **Alert Flapping / Warning Events**: None.

---

## 7. Approvals and Final Outcome
- **Release Lead Sign-Off**: [Signed / Date]
- **SRE Lead Sign-Off**: [Signed / Date]
- **Final Release Outcome**: [SUCCESSFULLY PROMOTED / ROLLED BACK / CANCELLED]
