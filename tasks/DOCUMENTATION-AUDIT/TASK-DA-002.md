# TASK-DA-002 — Reconcile NFR Semantic Collisions in Traceability Closure Matrix

1. **Task ID**: TASK-DA-002
2. **Parent Finding ID**: FINDING-002
3. **Title**: Reconcile NFR Semantic Collisions in Traceability Closure Matrix
4. **Objective**: Restore canonical descriptions, thresholds, and test references for NFR-REL-001, NFR-REL-002, NFR-AI-002, and NFR-AI-004 in Traceability Closure Matrix.
5. **Single Expected Outcome**: Canonical requirement summaries and targets match docs/03-requirements/NFR-BASELINE.md exactly.
6. **Scope**: Rows for NFR-REL-001, NFR-REL-002, NFR-AI-002, NFR-AI-004 in execution/TRACEABILITY-CLOSURE-MATRIX.md.
7. **Non-Goals**: Modifying NFR-BASELINE.md; touching invariant rows.
8. **Exact File(s)**: `execution/TRACEABILITY-CLOSURE-MATRIX.md`
9. **Exact Section(s)**: §3 Non-Functional Requirement Traceability Matrix (NFR-*)
10. **Input**: docs/03-requirements/NFR-BASELINE.md lines 21-37.
11. **Output**: Reconciled NFR rows in execution/TRACEABILITY-CLOSURE-MATRIX.md.
12. **Preconditions**: TASK-DA-001 completed; 28 NFR rows present.
13. **Invariant / Requirement Affected**: `INV-REL-001, INV-REL-002, NFR-REL-001, NFR-REL-002, NFR-AI-002, NFR-AI-004`
14. **Detailed Atomic Steps**:
1. Read exact requirement summary and target metric from NFR-BASELINE.md for NFR-REL-001 (workflow crash recovery <= 5 min).
2. Read exact summary and target metric for NFR-REL-002 (policy fail-closed on writes).
3. Read exact summary and target metric for NFR-AI-002 (RCA Top-1 >= 0.80 / Top-3 >= 0.95).
4. Read exact summary and target metric for NFR-AI-004 (SQL correctness >= 0.95 and zero unauthorized queries).
5. Edit table rows in execution/TRACEABILITY-CLOSURE-MATRIX.md to overwrite deviant text with canonical definitions.

15. **Acceptance Criteria**:
    - `AC-DA-002-01: In TRACEABILITY-CLOSURE-MATRIX.md, NFR-REL-001 describes workflow crash recovery, NFR-REL-002 describes policy write block on outage, NFR-AI-002 describes RCA top-k benchmark, and NFR-AI-004 describes SQL correctness.`
16. **Validation Method**:
    ```powershell
    python -c "t = open('execution/TRACEABILITY-CLOSURE-MATRIX.md', encoding='utf-8').read(); assert 'Workflow Resumes After Worker Failure' in t or 'Workflow Crash Recovery' in t; assert 'Policy/IAM/Audit' in t"
    ```
17. **Evidence Artifact**: `execution/TRACEABILITY-CLOSURE-MATRIX.md diff output`
18. **Owner Role**: Principal Architect
19. **Estimated Size**: 30 min
20. **Dependencies**: `TASK-DA-001`
21. **Blocks**: `TASK-DA-008`
22. **Risk**: Incorrect regex replacement affecting other rows.
23. **Recovery Note**: Discard uncommitted changes via git restore if syntax errors occur.
24. **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
25. **Traceability**: `FINDING-002 -> TASK-DA-002 -> TRACEABILITY-CLOSURE-MATRIX.md`
