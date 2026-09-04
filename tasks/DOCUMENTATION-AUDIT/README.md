# Documentation Audit — Micro-Task Index

Date: 2026-09-04
Total Tasks: 24
Source: DOCUMENTATION-FINDINGS-REGISTER.md

---

## Task Summary

| Task ID | Finding | Title | Owner | Size | Priority | Dependency | Status |
|---|---|---|---|---|---|---|---|
| TASK-DA-001 | F-CORR-001 | Reconcile flagship scenario geography | Product Lead | S | P1 | — | SUPERSEDED / RESOLVED (FINAL-TASK-008) |
| TASK-DA-002 | F-CORR-002 | Reconcile Credential Broker TTL | Security Architect | S | P1 | — | SUPERSEDED / RESOLVED (FINAL-TASK-005) |
| TASK-DA-003 | F-CORR-003 | Clarify Tier 3 approval ceiling | Security Architect | S | P1 | — | SUPERSEDED / RESOLVED (FINAL-TASK-005) |
| TASK-DA-004 | F-CORR-004 | Fix "automated tier-1" terminology | Security Architect | S | P1 | — | SUPERSEDED / RESOLVED (FINAL-TASK-005) |
| TASK-DA-005 | F-CORR-005 | Fix TenantContext type nullability | Tenancy Architect | S | P1 | — | SUPERSEDED / RESOLVED (FINAL-TASK-006) |
| TASK-DA-006 | F-CONS-001 | Reconcile Rail 3 status | Platform Architect | S | P2 | — | SUPERSEDED / RESOLVED (FINAL-TASK-007) |
| TASK-DA-007 | F-CONS-002 | Fix EXECUTOR-QUEUE boilerplate | Platform Architect | S | P2 | — | SUPERSEDED / RESOLVED (FINAL-TASK-007) |
| TASK-DA-008 | F-CONS-003 | Update TRACEABILITY-MATRIX header | Platform Architect | S | P2 | — | SUPERSEDED / RESOLVED (FINAL-TASK-004, 012) |
| TASK-DA-009 | F-LINK-001 | Fix ADR-AUTHORITY-REVIEW link | Documentation Engineer | S | P2 | — | SUPERSEDED / RESOLVED (FINAL-TASK-007) |
| TASK-DA-010 | F-LINK-002 | Add ADR-0012 to FLASH-EXECUTOR-RULEBOOK | Documentation Engineer | S | P2 | — | SUPERSEDED / RESOLVED (FINAL-TASK-010) |
| TASK-DA-011 | F-META-001 | Create AGENTS.md | Platform Architect | M | P2 | — | SUPERSEDED / RESOLVED (FINAL-TASK-011) |
| TASK-DA-012 | F-META-002 | Add version/date metadata to 30+ specs | Documentation Engineer | L | P2 | — | SUPERSEDED / RESOLVED (FINAL-TASK-011) |
| TASK-DA-013 | F-COMP-001 | Define missing 66 SRS requirements | Product Lead | L | P0 | TASK-DA-001 | SUPERSEDED / RESOLVED (FINAL-TASK-003) |
| TASK-DA-014 | F-COMP-002 | Reconcile SRS FR-RCA-* with PRD | Product Lead | S | P0 | TASK-DA-013 | SUPERSEDED / RESOLVED (FINAL-TASK-003) |
| TASK-DA-015 | F-PREC-001 | Resolve Proposed→Accepted governance gap | Principal Architect | M | P1 | — | SUPERSEDED / RESOLVED (FINAL-TASK-011) |
| TASK-DA-016 | F-INTEG-001 | Fix EVD-TEN-001 SHA-256 hash | Tenancy Lead | S | P0 | — | SUPERSEDED / RESOLVED (FINAL-TASK-001) |
| TASK-DA-017 | F-STRUCT-001 | Fix AI-GOVERNANCE section numbering | AI Governance Lead | S | P3 | — | SUPERSEDED / RESOLVED (FINAL-TASK-013) |
| TASK-DA-018 | F-STRUCT-002 | Add missing SQL templates | Data Platform Lead | M | P3 | — | SUPERSEDED / RESOLVED (FINAL-TASK-013) |
| TASK-DA-019 | F-SCHEMA-001 | Add superseded_at to EvidenceRecord | Evidence Architect | S | P2 | — | SUPERSEDED / RESOLVED (FINAL-TASK-006) |
| TASK-DA-020 | F-PHASE-001 | Fix ML-SYSTEM-SPEC phase scope | AI/ML Architect | S | P3 | — | SUPERSEDED / RESOLVED (FINAL-TASK-013) |
| TASK-DA-021 | F-PHASE-002 | Fix TEMPORAL-WORKFLOW-SPEC phase scope | Workflow Architect | S | P3 | — | SUPERSEDED / RESOLVED (FINAL-TASK-013) |
| TASK-DA-022 | F-PHASE-003 | Fix TOOL-GATEWAY-SPEC scope | Security Architect | S | P3 | — | SUPERSEDED / RESOLVED (FINAL-TASK-013) |
| TASK-DA-023 | F-PATH-001 | Fix relative path references | Documentation Engineer | M | P3 | — | SUPERSEDED / RESOLVED (FINAL-TASK-012) |
| TASK-DA-024 | F-ID-001 | Standardize SEC-* shorthand | Documentation Engineer | M | P3 | — | SUPERSEDED / RESOLVED (FINAL-TASK-013) |

---

## Execution Order (Dependency-Aware)

### Wave 1 — No dependencies (parallel)
TASK-DA-016, TASK-DA-001, TASK-DA-002, TASK-DA-003, TASK-DA-004, TASK-DA-005, TASK-DA-015,
TASK-DA-006, TASK-DA-007, TASK-DA-008, TASK-DA-009, TASK-DA-010, TASK-DA-011, TASK-DA-012,
TASK-DA-017, TASK-DA-018, TASK-DA-019, TASK-DA-020, TASK-DA-021, TASK-DA-022, TASK-DA-023, TASK-DA-024

### Wave 2 — Depends on Wave 1
TASK-DA-013 (depends on TASK-DA-001)

### Wave 3 — Depends on Wave 2
TASK-DA-014 (depends on TASK-DA-013)

---

## Size Legend
- **S** (Small): <= 30 minutes, single file, straightforward edit
- **M** (Medium): 30-90 minutes, 2-5 files, requires cross-reference checking
- **L** (Large): 90-180 minutes, 5+ files or significant content creation
