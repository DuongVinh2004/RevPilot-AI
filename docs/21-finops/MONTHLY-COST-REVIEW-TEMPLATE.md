# Monthly FinOps and Cost Review Template

Template ID: TMPL-FIN-001  
Owner: FinOps Lead & Engineering Leadership  
Status: OPERATIONAL TEMPLATE (Not an executed cost review)  
Reference: FINOPS-SPEC.md, BILLING-SPEC.md  

---

## 1. Review Period and Executive Summary
- **Review Period**: [YYYY-MM] (e.g., 2026-09)
- **Review Date**: YYYY-MM-DD
- **FinOps Lead**: [Name / Role]
- **Total Incurred Cloud Spend**: [$ Amount]
- **Total Attributed Customer Revenue**: [$ Amount]
- **Gross Margin on Platform Compute**: [% Percentage]
- **Budget Variance vs. Forecast**: [+/- % Delta]

---

## 2. Infrastructure Cost Breakdown by Category

| Cost Category | Budgeted Amount | Actual Spend | Variance ($) | Variance (%) | Primary Cost Driver |
|---|---|---|---|---|---|
| **AI Model & Token Ingestion** | $[Budget] | $[Actual] | $[Delta] | [%] | [Model family / Investigation volume] |
| **Compute & Containers (ECS/Fargate)**| $[Budget] | $[Actual] | $[Delta] | [%] | [Worker pool scaling / Concurrency] |
| **Relational Database (PostgreSQL)** | $[Budget] | $[Actual] | $[Delta] | [%] | [Instance tier / IOPS / Storage size] |
| **Temporal Workflow Service** | $[Budget] | $[Actual] | $[Delta] | [%] | [Activity execution count] |
| **Object Storage & Backups (S3/GCS)** | $[Budget] | $[Actual] | $[Delta] | [%] | [WAL archive retention / Snapshots] |
| **External Connectors & Egress** | $[Budget] | $[Actual] | $[Delta] | [%] | [API calls / Webhook payloads] |
| **Observability (OTel/Datadog/Grafana)**| $[Budget] | $[Actual] | $[Delta] | [%] | [Log volume / Metric cardinality] |

---

## 3. Tenant Unit Economics and Quota Utilization

| Tenant ID | Tier | Monthly Investigation Volume | Token Spend | Compute Spend | Quota Consumed (%) | Unit Margin (%) |
|---|---|---|---|---|---|---|
| tenant_demo_01 | SMB | [Count] | $[Amount] | $[Amount] | [%] | [%] |
| tenant_corp_02 | Enterprise | [Count] | $[Amount] | $[Amount] | [%] | [%] |

---

## 4. Cost Anomalies and Circuit Breaker Activations
- **Anomalies Detected**: [Summary of any spike > 3x baseline]
- **Circuit Breaker Activations**: [Count of automatic quota lock events ERR_QUOTA_EXCEEDED]
- **Unattributed Spend (<0.5% target)**: [Measured unallocated spend percentage]

---

## 5. Next Month Forecast and Optimization Actions

| Optimization Action | Impacted Service | Expected Monthly Savings | Owner | Due Date | Status |
|---|---|---|---|---|---|
| ACT-FIN-001 | Implement prompt compression / caching | $[Amount] | AI Platform Lead | YYYY-MM-DD | Open |
| ACT-FIN-002 | Transition cold WAL archives to Glacier tier | $[Amount] | Storage Lead | YYYY-MM-DD | Open |
