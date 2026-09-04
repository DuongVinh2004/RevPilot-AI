# TASK-DA-001 | Reconcile Flagship Scenario Geography

## Metadata
- **Task ID**: TASK-DA-001
- **Finding**: F-CORR-001
- **Priority**: P1 — Critical
- **Owner**: Product Lead
- **Size**: S (30 minutes)
- **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
- **Dependencies**: None

---

## Problem

`docs/00-executive/EXECUTIVE-VISION.md` line 11 states flagship scenario is "Southern Vietnam".
`docs/03-requirements/SYNTHETIC-DATASET-SPEC.md` lines 136-148 defines flagship as "Midwest Regional Carrier Fleet Capacity Disruption" at Chicago warehouse WH-MIDWEST-01.

All downstream benchmarks, ground truth, evaluation protocols reference the Midwest scenario. EXECUTIVE-VISION is the outlier.

---

## Scope

### Files to Modify
- `docs/00-executive/EXECUTIVE-VISION.md` line 11 — Update geography

### Change Boundary
- **WRITE**: Flagship scenario description in EXECUTIVE-VISION.md
- **DO NOT MODIFY**: SYNTHETIC-DATASET-SPEC, evaluation protocols, ground truth data

---

## Acceptance Criteria

1. `[ ]` EXECUTIVE-VISION.md flagship scenario geography matches SYNTHETIC-DATASET-SPEC.md
2. `[ ]` No other content in EXECUTIVE-VISION.md is changed
3. `[ ]` grep across all docs/ for "Southern Vietnam" returns 0 results
