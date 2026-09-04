# Documentation Consistency Report

Date: 2026-09-04
Auditor: Antigravity Documentation Quality Auditor

---

## 1. Cross-Document Contradictions

| # | Doc A | Claim A | Doc B | Claim B | Severity | Finding |
|---|---|---|---|---|---|---|
| 1 | EXECUTIVE-VISION.md:11 | "Southern Vietnam" flagship | SYNTHETIC-DATASET-SPEC.md:136 | "Midwest" Chicago WH-MIDWEST-01 | P1 | F-CORR-001 |
| 2 | SECURITY-ARCHITECTURE.md:142 | Broker TTL 60 min | TOOL-GATEWAY-SPEC.md:155 | Broker TTL 15 min | P1 | F-CORR-002 |
| 3 | IAM-SPEC.md:230 | Tier 3 "Unbounded" | IAM-SPEC.md:230 | Tier 3 "<= $10,000" | P1 | F-CORR-003 |
| 4 | APPROVAL-ACTION-LOOP.md:185 | "automated tier-1" | IAM-SPEC.md:228 | Human approval mandatory | P1 | F-CORR-004 |
| 5 | MULTI-TENANCY-SPEC.md:37 | tenant_id: TenantId (non-null) | MULTI-TENANCY-SPEC.md:48 | tenant_id=None (system ops) | P1 | F-CORR-005 |
| 6 | CURRENT-STATUS-RECONCILIATION | Rail 3 = UNLOCKED_FOR_PLANNING | RAIL-STATUS.md | Rail 3 = READY_WITH_TASK | P2 | F-CONS-001 |
| 7 | EXECUTOR-QUEUE.md:3 | "1 TASK QUEUED" | EXECUTOR-QUEUE.md:11 | "fail-closed empty state" | P2 | F-CONS-002 |
| 8 | CONTINUOUS-EVAL-TEMPLATE | Unsupported claims <= 2% | INV-AI-001 / EVAL-FRAMEWORK | Unsupported claims = 0% | P2 | F-CONS-005 |
| 9 | MODEL-RELEASE-PROCESS | claude-3-5-sonnet pinned | DECISION-CLOSURE-REGISTER | DEC-005 vendor OPEN | P2 | F-CONS-006 |
| 10 | SRE-SPEC.md §3 | "31-point checklist" | PRODUCTION-READINESS-GATE | 29 gate entries | P2 | F-CONS-007 |
| 11 | BACKUP-EXERCISE-RECORD | Exercise "quarterly" | BACKUP-RUNBOOK | Exercise "weekly" | P2 | F-CONS-008 |
| 12 | DEPLOYMENT-ARCH.md:107 | TC-P08-010 = container scan | TEST-STRATEGY.md | TC-P08-010 = audit stream | P2 | F-CONS-009 |

---

## 2. Evaluation Parameter Inconsistencies

| Parameter | Source A | Value A | Source B | Value B | Finding |
|---|---|---|---|---|---|
| Incident ID | ANOMALY-BENCHMARK | INC-SYNTH-TRUCK-001 | INVESTIGATION-BENCHMARK | INC-SYN-001 | F-EVAL-001 |
| Date Window | CAUSAL-BENCHMARK | Feb 14-21, 2026 | INVESTIGATION-BENCHMARK | May 10-17, 2026 | F-EVAL-001 |
| Cost Budget | INVESTIGATION-BENCHMARK | $2.00 USD | EVALUATION-FRAMEWORK §5.3 | $5.00 USD | F-EVAL-001 |
| RCA Top-1 | CAUSAL-BENCHMARK | >= 0.80 | CONTINUOUS-EVAL-TEMPLATE | >= 0.85 | F-EVAL-001 |
| Cost per Investigation | CONTINUOUS-EVAL-TEMPLATE:38 | "<= .00" (truncated) | — | — | F-EVAL-002 |

---

## 3. ID Reference Consistency

| ID Type | Total Defined | Total Referenced | Orphaned | Missing Reference |
|---|---|---|---|---|
| INV-* | 26 | 26 (all docs) | 0 | 0 |
| NFR-* | 28 | 28 (all docs) | 0 | 0 |
| ADR-* | 12 | 11 in RULEBOOK | 0 | ADR-0012 missing from RULEBOOK |
| AC-* | 14 | 14 (all docs) | 0 | 0 |
| FR-* (SRS) | 22 | 22 (downstream) | 2 (FR-RCA-*) | 66 PRD ranges unspecified |
| SEC-* | 10 | 10 (via shorthand) | 0 | Shorthand vs canonical prefix |
| RISK-* | 20 | 20 | 0 | 0 |
| TASK-* | 80+ | 80+ | 0 | 0 |
| METRIC-* | 9 | 9 (all analytics docs) | 0 | 0 |
| EVD-* | 10 | 10 | 0 | 0 |
| BLK-* | 5 | 5 | 0 | 0 |
| DEC-* | 5+ | 5+ | 0 | 0 |

---

## 4. Broken Links

| File | Link Target | Issue | Finding |
|---|---|---|---|
| ADR-AUTHORITY-REVIEW.md:3 | CURRENT-STATUS-RECONCILIATION.md | File is CURRENT-STATE-RECONCILIATION.md | F-LINK-001 |
| Multiple specs | SYNTHETIC-DATASET-SPEC.md | Missing directory path ../03-requirements/ | F-PATH-001 |
| Multiple specs | DATABASE-SCHEMA.md | Missing directory path ../27-database/ | F-PATH-001 |
| Multiple specs | FINOPS-SPEC.md | Missing directory path ../21-finops/ | F-PATH-001 |
| Multiple specs | DR-PLAN.md | Missing directory path ../24-sre/ | F-PATH-001 |

---

## 5. Status Consistency

| Document | Declared Status | Authoritative? | Parent Status | Governance Issue? |
|---|---|---|---|---|
| EXECUTIVE-VISION.md | Proposed v0.1 | Base | — | No |
| PRD.md | Proposed v0.1 | Base | — | No |
| INVARIANT-REGISTRY.md | Proposed v0.1 | Base | — | No |
| NFR-BASELINE.md | Proposed v0.1 | Base | — | No |
| SYSTEM-ARCHITECTURE.md | Proposed v0.2 | Base | — | No |
| ANOMALY-DOMAIN-SPEC.md | Accepted | Downstream | Proposed parents | **YES** (F-PREC-001) |
| ANOMALY-LOCALIZATION-SPEC.md | Accepted | Downstream | Proposed parents | **YES** (F-PREC-001) |
| SYNTHETIC-DATASET-SPEC.md | Accepted | Downstream | Proposed parents | **YES** (F-PREC-001) |
| All docs/06-19 specs | Accepted | Downstream | Proposed parents | **YES** (F-PREC-001) |
| All docs/20-30 specs | Accepted | Downstream | Proposed parents | **YES** (F-PREC-001) |
| THREAT-MODEL.md | Proposed v0.1 | Base | — | No |
| AI-GOVERNANCE.md | Proposed v0.1 | Base | — | No |
| FRONTEND-SPEC.md | Proposed v0.1 | Base | — | No |
