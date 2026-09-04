# TASK-DA-014 — Strip Corrupted Literal Tab Characters from Evidence Index and Traceability Tables

1. **Task ID**: TASK-DA-014
2. **Parent Finding ID**: FINDING-014
3. **Title**: Strip Corrupted Literal Tab Characters from Evidence Index and Traceability Tables
4. **Objective**: Replace literal tab characters (\t) with clean strings across table cells in EVIDENCE-INDEX.md and TRACEABILITY-CLOSURE-MATRIX.md.
5. **Single Expected Outcome**: All test paths render cleanly without leading whitespace/tab corruption.
6. **Scope**: execution/evidence/EVIDENCE-INDEX.md and execution/TRACEABILITY-CLOSURE-MATRIX.md.
7. **Non-Goals**: Modifying file paths; changing table columns.
8. **Exact File(s)**: `execution/evidence/EVIDENCE-INDEX.md, execution/TRACEABILITY-CLOSURE-MATRIX.md`
9. **Exact Section(s)**: Table columns containing test paths
10. **Input**: Raw text files with \t occurrences.
11. **Output**: Clean markdown files without literal tabs in table cells.
12. **Preconditions**: FINDING-014 open.
13. **Invariant / Requirement Affected**: `INV-REL-002`
14. **Detailed Atomic Steps**:
1. Write a python script to search for '\ttest_' and '\ttests/' in both files.
2. Replace with 'test_' and 'tests/'.
3. Check for any remaining '\t' characters in both files.
4. Verify markdown tables render cleanly in terminal and preview.

15. **Acceptance Criteria**:
    - `AC-DA-014-01: Neither EVIDENCE-INDEX.md nor TRACEABILITY-CLOSURE-MATRIX.md contains literal '\t' characters preceding test filenames.`
16. **Validation Method**:
    ```powershell
    python -c "for f in ['execution/evidence/EVIDENCE-INDEX.md', 'execution/TRACEABILITY-CLOSURE-MATRIX.md']: assert '\ttest' not in open(f, encoding='utf-8').read()"
    ```
17. **Evidence Artifact**: `Git diff across both files`
18. **Owner Role**: Documentation Engineer
19. **Estimated Size**: 20 min
20. **Dependencies**: `None`
21. **Blocks**: `TASK-DA-005`
22. **Risk**: None; pure whitespace sanitization.
23. **Recovery Note**: Git restore if regex matches unintentionally.
24. **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
25. **Traceability**: `FINDING-014 -> TASK-DA-014 -> execution/evidence/EVIDENCE-INDEX.md`
