# Documentation Findings Register

Version: 1.0
Date: 2026-09-04
Auditor: Antigravity Documentation Quality Auditor (AI-assisted)
Total Findings: 44

---

## P0 — Blocker (4 Findings)

### F-INTEG-001 | SHA-256 Hash of Empty String in Evidence Index
- **Severity**: P0 — Blocker
- **Category**: Integrity / Evidence
- **File**: `execution/evidence/EVIDENCE-INDEX.md` line 22
- **Evidence**: Hash `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` = SHA-256 of 0-byte input. Presented as "ACTUAL" integrity proof for EVD-TEN-001.
- **Impact**: Any integrity claim relying on this hash is void. Evidence package cannot be trusted.
- **Owner**: Tenancy Lead
- **Remediation**: TASK-DA-016. Recompute hash from actual evidence content.
- **Validation**: `echo -n "" | sha256sum` confirms same hash. Corrected hash must differ.

### F-INTEG-002 | 9/10 Evidence Packages Not Executed
- **Severity**: P0 — Blocker
- **Category**: Verifiability
- **Files**: All evidence files in `execution/evidence/` except EVD-TEN-001 partial
- **Evidence**: EVD-SEC-001, EVD-AI-001, EVD-LOD-001, EVD-BCK-001, EVD-DR-001, EVD-REL-001, EVD-BIL-001, EVD-AUD-001 all show `NOT EXECUTED` or `PENDING EVIDENCE`. EVD-SLO-001 shows `DESIGN TARGET ONLY`.
- **Impact**: No empirical validation of any system property. Production readiness assessment impossible.
- **Owner**: SRE Lead + All Domain Leads
- **Remediation**: Execute all evidence packages per their respective runbooks after implementation reaches Stage B.
- **Validation**: Each evidence file must transition to PASS/FAIL with measured results.

### F-COMP-001 | 66 PRD Requirements Missing from SRS
- **Severity**: P0 — Blocker
- **Category**: Completeness
- **Files**: `docs/01-product/PRD.md` vs `docs/03-requirements/SRS.md`
- **Evidence**: PRD specifies epic ranges spanning 86 FR IDs. SRS defines only 20 discrete FR requirements. 66 requirements have no specification.
- **Impact**: Downstream specs, tasks, and tests cannot trace to authoritative requirements.
- **Owner**: Product Lead
- **Remediation**: TASK-DA-013. Either define missing FRs or narrow PRD ranges.
- **Validation**: Count of SRS FR IDs must match PRD epic ranges, or PRD must document exclusions.

### F-COMP-002 | SRS Introduces FR-RCA-* Not in PRD
- **Severity**: P0 — Blocker
- **Category**: Traceability
- **Files**: `docs/03-requirements/SRS.md` (FR-RCA-001, FR-RCA-002) vs `docs/01-product/PRD.md`
- **Evidence**: SRS defines FR-RCA-001 and FR-RCA-002. PRD epic table has no RCA epic or ID range.
- **Impact**: Requirements exist without product mandate; traceability chain broken.
- **Owner**: Product Lead
- **Remediation**: TASK-DA-014. Add RCA epic to PRD or reclassify under existing epic.
- **Validation**: Every SRS FR must trace to a PRD epic.

---

## P1 — Critical (8 Findings)

### F-CORR-001 | Flagship Scenario Geographic Contradiction
- **Severity**: P1 — Critical
- **Category**: Correctness
- **Files**: `docs/00-executive/EXECUTIVE-VISION.md` line 11 vs `docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` lines 136-148
- **Evidence**: EXECUTIVE-VISION says "Southern Vietnam". SYNTHETIC-DATASET-SPEC says "Midwest Regional Carrier Fleet Capacity Disruption" at Chicago WH-MIDWEST-01.
- **Impact**: Flagship scenario is anchor for all evaluation benchmarks. Geographic contradiction creates ambiguity.
- **Owner**: Product Lead
- **Remediation**: TASK-DA-001. Update EXECUTIVE-VISION to reflect canonical scenario.
- **Validation**: All documents must reference same geography.

### F-CORR-002 | Credential Broker Token TTL Conflict
- **Severity**: P1 — Critical
- **Category**: Security / Correctness
- **Files**: `docs/15-security/SECURITY-ARCHITECTURE.md` line 142 vs `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` line 155
- **Evidence**: SECURITY-ARCHITECTURE: "maximum 60-minute lifetime". TOOL-GATEWAY-SPEC: "maximum 15-minute TTL".
- **Impact**: Implementation cannot choose TTL. Security impact.
- **Owner**: Security Architect
- **Remediation**: TASK-DA-002. Reconcile to single standard.
- **Validation**: Single TTL value in both documents.

### F-CORR-003 | Tier 3 Approval Ceiling Self-Contradiction
- **Severity**: P1 — Critical
- **Category**: Correctness
- **File**: `docs/14-iam/IAM-SPEC.md` line 230
- **Evidence**: Tier 3 listed as "Unbounded / <= $10,000.00" — simultaneously unbounded and capped.
- **Impact**: Financial governance gap.
- **Owner**: Security Architect
- **Remediation**: TASK-DA-003. Define hard cap or document unbounded with escalation.
- **Validation**: Unambiguous financial boundary.

### F-CORR-004 | Tier-1 "Automated" Terminology Conflict
- **Severity**: P1 — Critical
- **Category**: Correctness / Security
- **Files**: `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` line 185 vs `docs/14-iam/IAM-SPEC.md` line 228
- **Evidence**: APPROVAL-ACTION-LOOP says "automated tier-1 actions". IAM-SPEC mandates human approval.
- **Impact**: Suggests tier-1 actions can bypass human approval. Contradicts INV-ACT-003.
- **Owner**: Security Architect
- **Remediation**: TASK-DA-004. Change "automated" to "human-approved".

### F-CORR-005 | TenantContext Type Nullability Mismatch
- **Severity**: P1 — Critical
- **Category**: Correctness / Type Safety
- **File**: `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` lines 37, 48, 122
- **Evidence**: Line 37: `tenant_id: TenantId` (non-nullable). Lines 48/122: `tenant_id=None`.
- **Impact**: Type signature contradicts usage.
- **Owner**: Tenancy Architect
- **Remediation**: TASK-DA-005. Update type to `tenant_id: TenantId | None`.

### F-PREC-001 | Proposed to Accepted Governance Inversion
- **Severity**: P1 — Critical
- **Category**: Governance
- **Files**: `docs/00-executive/SPECIFICATION-PRECEDENCE.md` line 25 vs downstream specs
- **Evidence**: Proposed parents have Accepted children. PRD, Architecture, Invariants all Proposed v0.1.
- **Impact**: Authority chain inverted.
- **Owner**: Principal Architect
- **Remediation**: TASK-DA-015. Promote parents or add governance exception.

### F-EVAL-001 | Incident ID and Date Window Inconsistencies
- **Severity**: P1 — Critical
- **Category**: Consistency
- **Files**: Evaluation docs (20-evaluation/)
- **Evidence**: INC-SYNTH-TRUCK-001 vs INC-SYN-001; Feb vs May 2026; $2 vs $5; Top-1 0.80 vs 0.85.
- **Impact**: Evaluation benchmarks not executable consistently.
- **Owner**: AI Evaluation Lead
- **Remediation**: Reconcile all benchmark parameters.

### F-EVAL-002 | Missing Cost Figure in Evaluation Template
- **Severity**: P1 — Critical
- **Category**: Completeness
- **File**: `docs/20-evaluation/CONTINUOUS-EVALUATION-REPORT-TEMPLATE.md` line 38
- **Evidence**: "Cost per Investigation | <= .00 |" — dollar figure missing.
- **Owner**: AI Evaluation Lead
- **Remediation**: Fill canonical cost value.

---

## P2 — High (14 Findings)

### F-META-001 | AGENTS.md Does Not Exist
- **Severity**: P2 — High
- **Category**: Completeness
- **Owner**: Platform Architect
- **Remediation**: TASK-DA-011.

### F-META-002 | Missing Version/Date Metadata in 30+ Specs
- **Severity**: P2 — High
- **Category**: Metadata
- **Owner**: Documentation Engineer
- **Remediation**: TASK-DA-012.

### F-CONS-001 | Rail 3 Status Inconsistency
- **Severity**: P2 — High
- **Category**: Consistency
- **Files**: CURRENT-STATUS-RECONCILIATION vs RAIL-STATUS
- **Owner**: Platform Architect
- **Remediation**: TASK-DA-006.

### F-CONS-002 | EXECUTOR-QUEUE Boilerplate Contradiction
- **Severity**: P2 — High
- **Files**: EXECUTOR-QUEUE.md lines 3 vs 11
- **Owner**: Platform Architect
- **Remediation**: TASK-DA-007.

### F-CONS-003 | TRACEABILITY-MATRIX Stale Header
- **Severity**: P2 — High
- **Files**: TRACEABILITY-MATRIX.md header
- **Owner**: Platform Architect
- **Remediation**: TASK-DA-008.

### F-CONS-004 | Duplicate Reconciliation Files
- **Severity**: P2 — High
- **Files**: CURRENT-STATE-RECONCILIATION vs CURRENT-STATUS-RECONCILIATION
- **Owner**: Platform Architect

### F-CONS-005 | Unsupported Claim Rate Threshold Conflict
- **Severity**: P2 — High
- **Files**: Evaluation template vs INV-AI-001
- **Evidence**: Template allows 2%. Invariant requires 0%.
- **Owner**: AI Evaluation Lead

### F-CONS-006 | MODEL-RELEASE-PROCESS Hard-Codes Provider Models
- **Severity**: P2 — High
- **Evidence**: Commercial model names while DEC-005 OPEN.
- **Owner**: AI Platform Lead

### F-CONS-007 | Production Readiness Gate Count Mismatch
- **Severity**: P2 — High
- **Evidence**: SRE-SPEC says 31; Gate doc has 29.
- **Owner**: SRE Lead

### F-CONS-008 | Backup Exercise Cadence Conflict
- **Severity**: P2 — High
- **Evidence**: Quarterly vs weekly vs monthly.
- **Owner**: SRE Lead

### F-CONS-009 | TC-P08-010 Description Conflict
- **Severity**: P2 — High
- **Evidence**: Container scan vs audit stream.
- **Owner**: Quality Engineering Lead

### F-LINK-001 | Broken Link in ADR-AUTHORITY-REVIEW
- **Severity**: P2 — High
- **File**: ADR-AUTHORITY-REVIEW.md line 3
- **Owner**: Documentation Engineer
- **Remediation**: TASK-DA-009.

### F-LINK-002 | FLASH-EXECUTOR-RULEBOOK Missing ADR-0012
- **Severity**: P2 — High
- **Owner**: Documentation Engineer
- **Remediation**: TASK-DA-010.

### F-SCHEMA-001 | EvidenceRecord Missing superseded_at
- **Severity**: P2 — High
- **File**: EVIDENCE-PROVENANCE-SPEC.md
- **Owner**: Evidence Architect
- **Remediation**: TASK-DA-019.

---

## P3 — Medium (12 Findings)

### F-STRUCT-001 | AI-GOVERNANCE Section Numbering Jump
- **Severity**: P3 — Medium
- **Owner**: AI Governance Lead — TASK-DA-017

### F-STRUCT-002 | SQL Capability Catalog Incomplete Templates
- **Severity**: P3 — Medium
- **Owner**: Data Platform Lead — TASK-DA-018

### F-STRUCT-003 | CAP-SQL-DRILLDOWN-DIMENSION vs -DIM
- **Severity**: P3 — Medium
- **Owner**: AI Platform Lead

### F-PHASE-001 | ML-SYSTEM-SPEC Phase Scope Bleed
- **Severity**: P3 — Medium
- **Owner**: AI/ML Architect — TASK-DA-020

### F-PHASE-002 | TEMPORAL-WORKFLOW-SPEC Phase Scope Bleed
- **Severity**: P3 — Medium
- **Owner**: Workflow Architect — TASK-DA-021

### F-PHASE-003 | TOOL-GATEWAY-SPEC Scope Inconsistency
- **Severity**: P3 — Medium
- **Owner**: Security Architect — TASK-DA-022

### F-PATH-001 | Relative Path References in Multiple Specs
- **Severity**: P3 — Medium
- **Owner**: Documentation Engineer — TASK-DA-023

### F-ID-001 | SEC-* Shorthand Usage
- **Severity**: P3 — Medium
- **Owner**: Documentation Engineer — TASK-DA-024

### F-METRIC-001 | METRIC-002 Potential Double-Counting
- **Severity**: P3 — Medium
- **Owner**: Analytics Architecture Lead

### F-FRONTEND-001 | FRONTEND-SPEC Extremely Terse
- **Severity**: P3 — Medium
- **Owner**: Frontend Architect

### F-ACCESS-001 | Typo in Access Review Template
- **Severity**: P3 — Medium
- **Owner**: Compliance Lead

### F-COST-001 | Tab Characters in File Paths
- **Severity**: P3 — Medium
- **Owner**: Documentation Engineer

---

## P4 — Low (6 Findings)

### F-FORMAT-001 | Typo in Operations Telemetry Spec
- **Severity**: P4 — Low — "withPromQL" missing space

### F-FORMAT-002 | Double Space in Post-Release Template
- **Severity**: P4 — Low — "(e.g.,  1.1.0)"

### F-FORMAT-003 | COMPLIANCE-EVIDENCE-RUNBOOK Empty Hash
- **Severity**: P4 — Low — Example uses empty-string SHA-256

### F-META-003 | Missing Non-Goals Section in 19 Specs
- **Severity**: P4 — Low

### F-META-004 | Missing Owner in 6 Key Documents
- **Severity**: P4 — Low — PRD, SYSTEM-ARCHITECTURE, AI-ARCHITECTURE, BDM, SRS, FRONTEND-SPEC

### F-ENTITY-001 | Investigation Cardinality Gap
- **Severity**: P4 — Low — ER diagram vs PRD J-02 analyst-initiated flow
