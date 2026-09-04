# Post-Release Review Template

Template ID: TMPL-REL-001  
Owner: Release Lead & SRE Lead  
Status: OPERATIONAL TEMPLATE (Not an executed release review)  
Reference: RELEASE-CANARY-ROLLBACK-SPEC.md  

---

## 1. Release Metadata
- **Release Identifier**: REL-[YYYYMMDD]-[SEMVER] (e.g., v1.1.0)
- **Release Candidate Tag**: git-tag:v1.1.0-rc1 (Commit: [GIT_HASH])
- **Release Date**: YYYY-MM-DD
- **Release Engineer**: [Name / Role]
- **SRE On-Call**: [Name / Role]
- **Approval Sign-off**: [Approver Name / Timestamp]

---

## 2. Canary Rollout Progression
- **Canary Cohort**: [List of canary tenant IDs]
- **Canary Duration**: [Minutes/Hours observed]
- **Traffic Split History**:
  - Stage 1 (5%): Start [HH:MM], Duration [X min], Metrics [Green / Breached]
  - Stage 2 (25%): Start [HH:MM], Duration [X min], Metrics [Green / Breached]
  - Stage 3 (100%): Start [HH:MM], Full Promotion Complete
- **Canary Health Verdict**: [PASS / ABORTED / ROLLED BACK]

---

## 3. Reliability and SLO Impact
- **Product API Latency (P95)**: [Pre-release baseline] vs. [Post-release measured]
- **HTTP 5xx Error Rate**: [Pre-release baseline] vs. [Post-release measured]
- **Monthly Error Budget Consumption**: [Percentage consumed during release window, e.g., 0.02%]
- **Incidents Triggered**: [None / INC-YYYYMMDD-###]

---

## 4. Tenant and AI Quality Impact
- **Tenant Complaints / Support Tickets**: [Count / IDs]
- **AI Recommendation Groundedness**: [Benchmark score comparison]
- **Unsupported Claim Rate**: [Pre vs. Post release rate]
- **Action Execution Success Rate**: [Percentage of successful Tool Gateway dispatches]

---

## 5. Cost and FinOps Impact
- **Model / Token Spend Variance**: [Delta % vs. forecast]
- **Infrastructure Compute Cost Variance**: [Delta % vs. baseline]

---

## 6. Rollback Decision Record
- **Was Rollback Triggered?**: [NO / YES]
- **Trigger Reason (if applicable)**: [N/A or Alert Name]
- **Rollback Execution Time**: [Duration in seconds to revert traffic]
- **Data / Schema Rollback Status**: [Clean revert / Expand-Contract maintained]

---

## 7. Follow-Up Action Items

| Action Item | Description | Owner | Target Date | Status |
|---|---|---|---|---|
| ACT-REL-001 | [Post-release bug fix or telemetry tuning] | [Owner] | YYYY-MM-DD | Open |
