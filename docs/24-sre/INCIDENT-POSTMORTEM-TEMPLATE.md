# Operational Incident Postmortem Template

Template ID: TMPL-SRE-001  
Owner: SRE Lead & Incident Commander  
Status: OPERATIONAL TEMPLATE (Not an executed incident record)  
Reference: INCIDENT-RESPONSE-RUNBOOK.md  

---

## 1. Incident Overview
- **Incident Title**: [Short descriptive summary of outage/degradation]
- **Incident ID**: INC-[YYYYMMDD]-[###]
- **Severity**: [P0 (Catastrophic) / P1 (Major) / P2 (Degraded) / P3 (Minor) / P4 (Low)]
- **Incident Commander**: [Name / Role]
- **Communications Lead**: [Name / Role]
- **Technical Lead**: [Name / Role]
- **Date of Incident**: YYYY-MM-DD
- **Incident Start Time (UTC)**: HH:MM:SS
- **Incident Detection Time (UTC)**: HH:MM:SS
- **Containment Time (UTC)**: HH:MM:SS
- **Full Resolution Time (UTC)**: HH:MM:SS
- **Total Duration / TTR**: [Minutes/Hours]

---

## 2. Customer and Business Impact
- **Tenants Affected**: [List of tenant IDs or 'All Tenants']
- **User Experience Impact**: [Error messages seen by users, UI impact]
- **API Impact**: [Total requests failed, error rate spike, latency degradation]
- **Workflow / Task Impact**: [Number of Temporal workflows stalled/terminated]
- **Financial / Action Impact**: [Any unauthorized or duplicate side effects; financial cost]
- **Data Integrity / Privacy Impact**: [Any data corruption, PII leakage, or tenant boundary violation; confirmed 0 or detail]

---

## 3. Incident Timeline (UTC)
| Timestamp (UTC) | Elapsed | Event / Action Taken | Actor / System |
|---|---|---|---|
| HH:MM:SS | +00:00 | Outage begins / anomaly condition triggered | System |
| HH:MM:SS | +00:0X | Automated alarm fires on [Alert Name] | Alertmanager |
| HH:MM:SS | +00:0Y | Incident Commander paged and acknowledges | IC |
| HH:MM:SS | +00:0Z | War room opened; initial mitigation attempted | Response Team |
| HH:MM:SS | +00:XY | Containment achieved via [Rollback / Failover / Kill-Switch] | Tech Lead |
| HH:MM:SS | +00:XX | Full recovery verified; monitoring confirms green | IC |

---

## 4. Root Cause Analysis (5 Whys)
1. **Why did the outage occur?** [Direct cause]
2. **Why did [direct cause] occur?** [Second level]
3. **Why did [second level] occur?** [Third level]
4. **Why did [third level] occur?** [Fourth level]
5. **Why was this not prevented or detected sooner?** [Systemic/Architectural root cause]

---

## 5. Contributing Factors
- **Technical Factors**: [Bug, schema mismatch, memory leak, provider timeout]
- **Procedural Factors**: [Missing canary stage, untested migration, insufficient runbook]
- **Environmental Factors**: [Cloud provider AZ degradation, external SaaS API rate limit]

---

## 6. Detection and Response Evaluation
- **How was the incident detected?** [Automated Alert / Customer Report / Internal Staff]
- **Did alerts fire appropriately?** [Yes / No / Flapping]
- **Were runbooks accurate and actionable?** [Yes / Needs Revision]
- **Did kill-switches / containment operate within target thresholds?** [Measured duration]

---

## 7. Corrective and Preventive Actions (Action Items)

| Action Item ID | Preventive Action Description | Action Type | Owner | Target Due Date | Status |
|---|---|---|---|---|---|
| ACT-INC-001 | Add regression test in test suite | Code / Test | [Owner] | YYYY-MM-DD | Open |
| ACT-INC-002 | Refine alert threshold to reduce MTTA | Monitoring | [Owner] | YYYY-MM-DD | Open |
| ACT-INC-003 | Update deployment canary validation step | Release | [Owner] | YYYY-MM-DD | Open |

---

## 8. Evidence and Audit References
- Grafana Dashboard Snapshot: [URL / File Link]
- Log Scrape Archive: [S3/GCS Object URI]
- Hash Chain Audit Entry: SHA256:[HASH]
