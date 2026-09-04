# Pilot Onboarding and Recovery Specification (Phase 07 Canonical Contract)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 07 — Multi-Tenant Pilot, Connectors, and Tenant Operations
Rail Alignment: Rail 17 (Observability/FinOps/Audit), Rail 2 (Tenant Context & Lifecycle), Rail 5 (Persistence Isolation)
Owners: SRE Architecture, Security Operations, Tenancy Operations
Traceability: `BR-004`, `FR-CTL-001`, `FR-CTL-003`, `INV-TEN-001`, `INV-TEN-002`, `INV-REL-001`, `INV-REL-002`, `NFR-TEN-001`, `NFR-TEN-002`, `NFR-REC-001`, `NFR-AUD-001`, `AC-010`, `ADR-0005`, `ADR-0009`

---

## 1. Executive Summary and Operational Gate

This specification defines the mandatory pre-flight onboarding criteria, named operational ownership, failure rehearsal protocols, and escalation runbooks required to onboard commercial pilot tenants. Passing pilot rehearsals satisfies the Phase 07 commercial pilot milestone, but does NOT grant production readiness (which is governed by Phase 08).

---

## 2. Named Ownership and Governance Matrix

Every commercial pilot tenant MUST have designated, verified owners before provisioning:

| Ownership Role | Responsibility | Designation Requirement | Incident Contact SLA |
|---|---|---|---|
| **Tenant Executive Sponsor** | Commercial agreement & business scope | Customer VP / C-Level | 24 business hours |
| **Tenant Security Owner** | SSO/OIDC integration, secret rotation sign-off | Customer SecOps Lead | 1 hour (Critical) |
| **Tenant Data Owner** | Schema mapping approval, data classification | Customer RevOps Lead | 4 hours |
| **RevPilot Lead Engineer** | Provisioning orchestration, canary verification | Platform Core Team | 15 minutes (P0/P1) |
| **RevPilot Security Lead** | Threat review, secret broker verification | SecOps Team | 15 minutes (P0) |
| **RevPilot SRE Incident Lead**| Uptime monitoring, quota management, DR | 24/7 On-Call | Immediate pager |

---

## 3. Pilot Onboarding Pre-Flight Checklist

The Provisioning Orchestrator blocks tenant activation until all 10 pre-flight checks are signed off:

1. [ ] **Commercial & Tier Agreement**: Tier assigned (`SHARED`, `ENTERPRISE`, `REGULATED`) and SLA confirmed.
2. [ ] **Identity Federation**: OIDC metadata registered, PKCE enforced, test login verified, claim mappings approved.
3. [ ] **Quotas Allocated**: Spend limit set (\$2.00 target / \$5.00 hard stop per investigation; daily token budget set).
4. [ ] **Secret References Provisioned**: Webhook signing secret and connector credentials vaulted in broker; zero raw secrets in code.
5. [ ] **Persistence Boundary Established**: PostgreSQL RLS or dedicated schema verified; Redis namespace verified.
6. [ ] **Vector Collection Filter Tested**: Semantic pre-filter (`tenant_id == :target_tenant_id`) verified by unit test.
7. [ ] **Isolation Negative Matrix**: Automated suite `TEST-TEN-001..011` executed with 100% pass rate.
8. [ ] **Mock Connector Canary**: Mock CRM and billing sync execute without error; dry-run mode active.
9. [ ] **Audit Pipeline Verified**: Initial events (`tenancy.provisioning.*`) verified in hash chain.
10. [ ] **Escalation Path Tested**: Alert routing to customer incident contacts verified via test notification.

---

## 4. Mandatory Failure Rehearsal Matrix

Before pilot traffic is accepted, the operations team executes 7 live rehearsals in staging:

| Rehearsal ID | Target Capability | Rehearsal Procedure | Expected Observable Result | Exit Gate Criteria |
|---|---|---|---|---|
| `REH-P07-01` | **Isolation Under Stress** | Concurrently dispatch 500 requests across Tenant A and Tenant B | 0 cross-tenant records exposed; PostgreSQL RLS holds 100% | `NFR-TEN-001` PASS |
| `REH-P07-02` | **Export Completeness** | Trigger full export of synthetic tenant data; verify SHA-256 manifest | All tenant records exported; zero other tenant records; digest valid | `FR-CTL-003` PASS |
| `REH-P07-03` | **Cascade Deletion** | Execute tenant deletion; scan all SQL, vector, Redis, S3 stores | 100% rows purged; post-deletion probe returns 0 rows | `FR-CTL-003` PASS |
| `REH-P07-04` | **Disaster Restore** | Restore database from snapshot into isolated target; replay outbox | RPO $\le 5$ min, RTO $\le 30$ min; data hashes reconcile | `NFR-REC-001` PASS |
| `REH-P07-05` | **Auth Expiry Recovery**| Invalidate connector token in mock provider; trigger sync | Connector transitions to `AUTH_EXPIRED`; sync halts; alerts SRE | Fail-Closed PASS |
| `REH-P07-06` | **Schema Drift Isolation**| Inject breaking column schema into webhook payload | Payload diverted to `connector_quarantine`; canonical store unaffected | `INV-DATA-002` PASS |
| `REH-P07-07` | **Webhook Replay Attack**| Replay identical webhook payload with matching signature and event ID | Gateway returns 200 OK; processing deduplicated; 0 duplicate entries | Anti-Replay PASS |

---

## 5. Escalation Runbooks and Incident Contacts

### 5.1 Runbook: RB-P07-001 — Tenant Isolation Breach Alert
- Trigger: `database.rls_violations_total > 0` or cross-tenant query detected.
- Severity: Severity 0 (Emergency).
- Immediate Action:
  1. RevPilot API Gateway automatically revokes active connection pool.
  2. Disables external ingress for affected tenant (`Tenant.suspend()`).
  3. Escalates to RevPilot Security Lead and SRE on-call via high-priority pager.
  4. Preserves memory dump and connection logs for forensic audit.

### 5.2 Runbook: RB-P07-002 — Quota Exhaustion and Throttling
- Trigger: Tenant spend reaches 95% of daily budget or rate limit triggers HTTP 429.
- Severity: Severity 3 (Operational).
- Action: Notify customer RevOps lead; provide self-service quota expansion options.

### 5.3 Runbook: RB-P07-003 — Connector Schema Drift Quarantine Clearing
- Trigger: Records accumulating in `connector_quarantine`.
- Action:
  1. Inspect payload in `connector_quarantine`.
  2. If upstream provider schema changed: author new `mapping_version`.
  3. Deploy updated adapter and execute dry-run replay against quarantined payloads.
  4. Mark records `REPROCESSED` and advance sync cursor.
