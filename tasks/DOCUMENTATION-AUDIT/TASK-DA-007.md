# TASK-DA-007 — Correct Policy Path Mismatch for INV-TEN-003 in Traceability Closure Matrix

1. **Task ID**: TASK-DA-007
2. **Parent Finding ID**: FINDING-007
3. **Title**: Correct Policy Path Mismatch for INV-TEN-003 in Traceability Closure Matrix
4. **Objective**: Update Implementation Artifact path for INV-TEN-003 to packages/backend/src/revpilot/modules/tenancy/ports/policy.py.
5. **Single Expected Outcome**: Traceability matrix references the exact physical path on disk.
6. **Scope**: Row INV-TEN-003 in execution/TRACEABILITY-CLOSURE-MATRIX.md.
7. **Non-Goals**: Moving source code files; renaming python modules.
8. **Exact File(s)**: `execution/TRACEABILITY-CLOSURE-MATRIX.md`
9. **Exact Section(s)**: §2 Invariant Traceability Matrix (INV-*), row INV-TEN-003
10. **Input**: Physical location packages/backend/src/revpilot/modules/tenancy/ports/policy.py.
11. **Output**: Corrected line 33 in execution/TRACEABILITY-CLOSURE-MATRIX.md.
12. **Preconditions**: FINDING-007 confirmed; physical file verified on disk.
13. **Invariant / Requirement Affected**: `INV-TEN-003`
14. **Detailed Atomic Steps**:
1. Locate row INV-TEN-003 in execution/TRACEABILITY-CLOSURE-MATRIX.md (line 33).
2. Replace 'packages/backend/src/revpilot/modules/tenancy/policy.py' with 'packages/backend/src/revpilot/modules/tenancy/ports/policy.py'.
3. Verify that the updated path matches an existing physical file on disk.

15. **Acceptance Criteria**:
    - `AC-DA-007-01: Line 33 of TRACEABILITY-CLOSURE-MATRIX.md references packages/backend/src/revpilot/modules/tenancy/ports/policy.py and exists on disk.`
16. **Validation Method**:
    ```powershell
    python -c "import os, re; t = open('execution/TRACEABILITY-CLOSURE-MATRIX.md', encoding='utf-8').read(); m = re.search(r'packages/backend/src/revpilot/modules/tenancy/ports/policy\.py', t); assert m is not None; assert os.path.exists(m.group(0))"
    ```
17. **Evidence Artifact**: `execution/TRACEABILITY-CLOSURE-MATRIX.md diff`
18. **Owner Role**: Platform Architect
19. **Estimated Size**: 15 min
20. **Dependencies**: `None`
21. **Blocks**: `TASK-DA-008`
22. **Risk**: None; localized string edit.
23. **Recovery Note**: Revert change if typo occurs.
24. **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
25. **Traceability**: `FINDING-007 -> TASK-DA-007 -> execution/TRACEABILITY-CLOSURE-MATRIX.md`
