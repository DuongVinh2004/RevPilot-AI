# TASK-DA-013 | Define Missing 66 SRS Requirements

## Metadata
- **Task ID**: TASK-DA-013
- **Finding**: F-COMP-001
- **Priority**: P0 — Blocker
- **Owner**: Product Lead
- **Size**: L (120 minutes)
- **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
- **Dependencies**: TASK-DA-001 (flagship scenario must be reconciled first)

---

## Problem

PRD (`docs/01-product/PRD.md`) specifies epic ranges spanning 86 FR IDs:
- FR-DET-001..006 (6)
- FR-INV-001..012 (12)
- FR-EVD-001..010 (10)
- FR-ML-001..014 (14)
- FR-DEC-001..009 (9)
- FR-ACT-001..015 (15)
- FR-LRN-001..006 (6)
- FR-CTL-001..018 (18)

SRS (`docs/03-requirements/SRS.md`) defines only 20 discrete FR requirements. 66 IDs have no specification.

---

## Scope

### Option A: Define Missing FRs
- Add 66 FR definitions to SRS.md with statement, invariant references, and test pointers

### Option B: Narrow PRD Ranges
- Update PRD epic ranges to match actual SRS coverage
- Document excluded IDs with rationale

### Change Boundary
- **WRITE**: SRS.md and/or PRD.md
- **DO NOT MODIFY**: Domain specs, evaluation protocols, task packets

---

## Acceptance Criteria

1. `[ ]` Every FR ID in PRD epic ranges either has SRS definition OR PRD documents its exclusion
2. `[ ]` Zero orphan FR IDs (every SRS FR traces to a PRD epic)
3. `[ ]` New/modified FRs have invariant cross-references
4. `[ ]` Traceability Matrix updated to reflect changes
