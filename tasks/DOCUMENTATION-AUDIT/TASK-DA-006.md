# TASK-DA-006 — Apply Historical Notice Banner to Superseded 2026-09-03 Reconciliation Report

1. **Task ID**: TASK-DA-006
2. **Parent Finding ID**: FINDING-006
3. **Title**: Apply Historical Notice Banner to Superseded 2026-09-03 Reconciliation Report
4. **Objective**: Mark execution/CURRENT-STATUS-RECONCILIATION.md as superseded by CURRENT-STATE-RECONCILIATION.md and update historical banners across reports.
5. **Single Expected Outcome**: execution/CURRENT-STATUS-RECONCILIATION.md has historical notice banner; 4 historical reports link to CURRENT-STATE-RECONCILIATION.md.
6. **Scope**: execution/CURRENT-STATUS-RECONCILIATION.md, STAGE-B-PREFLIGHT-REPORT.md, E05-CLOSURE-REPORT.md, ADR-AUTHORITY-REVIEW.md, RAIL-0-E01-CONSISTENCY-REPORT.md.
7. **Non-Goals**: Deleting historical reports; modifying current state report.
8. **Exact File(s)**: `execution/CURRENT-STATUS-RECONCILIATION.md, execution/STAGE-B-PREFLIGHT-REPORT.md, execution/E05-CLOSURE-REPORT.md, execution/ADR-AUTHORITY-REVIEW.md, execution/RAIL-0-E01-CONSISTENCY-REPORT.md`
9. **Exact Section(s)**: Historical notice banners at top of each file
10. **Input**: Canonical path execution/CURRENT-STATE-RECONCILIATION.md.
11. **Output**: 5 updated historical reports with accurate forward pointers.
12. **Preconditions**: TASK-DA-004 completed.
13. **Invariant / Requirement Affected**: `INV-REL-002`
14. **Detailed Atomic Steps**:
1. Insert historical notice banner at line 3 of execution/CURRENT-STATUS-RECONCILIATION.md stating it is a point-in-time snapshot from 2026-09-03 superseded by CURRENT-STATE-RECONCILIATION.md.
2. Update banner links in STAGE-B-PREFLIGHT-REPORT.md to reference CURRENT-STATE-RECONCILIATION.md.
3. Update banner links in E05-CLOSURE-REPORT.md to reference CURRENT-STATE-RECONCILIATION.md.
4. Update banner links in ADR-AUTHORITY-REVIEW.md to reference CURRENT-STATE-RECONCILIATION.md.
5. Update banner links in RAIL-0-E01-CONSISTENCY-REPORT.md to reference CURRENT-STATE-RECONCILIATION.md.

15. **Acceptance Criteria**:
    - `AC-DA-006-01: CURRENT-STATUS-RECONCILIATION.md contains a HISTORICAL NOTICE banner; all 4 historical reports link to CURRENT-STATE-RECONCILIATION.md.`
16. **Validation Method**:
    ```powershell
    python -c "t = open('execution/CURRENT-STATUS-RECONCILIATION.md', encoding='utf-8').read(); assert 'HISTORICAL NOTICE' in t; assert 'CURRENT-STATE-RECONCILIATION.md' in t"
    ```
17. **Evidence Artifact**: `Git diff across 5 execution reports`
18. **Owner Role**: Documentation Quality Auditor
19. **Estimated Size**: 30 min
20. **Dependencies**: `TASK-DA-004`
21. **Blocks**: `TASK-DA-012`
22. **Risk**: Breaking relative markdown links.
23. **Recovery Note**: Validate with link checker script after edit.
24. **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
25. **Traceability**: `FINDING-006 -> TASK-DA-006 -> execution/*RECONCILIATION*.md`
