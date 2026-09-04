# TASK-DA-011 — Standardize Header Metadata in 58 Phase 00 Task Packets

1. **Task ID**: TASK-DA-011
2. **Parent Finding ID**: FINDING-011
3. **Title**: Standardize Header Metadata in 58 Phase 00 Task Packets
4. **Objective**: Convert single-paragraph uppercase headers in tasks/PHASE-00/SPEC-*.md to standard Markdown header blocks conforming to tasks/TASK-TEMPLATE.md.
5. **Single Expected Outcome**: All 58 SPEC-* task files contain standardized metadata blocks readable by automated parsers.
6. **Scope**: Header blocks in tasks/PHASE-00/SPEC-*.md (58 files).
7. **Non-Goals**: Modifying task objectives, write sets, or acceptance criteria.
8. **Exact File(s)**: `tasks/PHASE-00/SPEC-*.md (all 58 files)`
9. **Exact Section(s)**: Top of each file (lines 1–3)
10. **Input**: tasks/TASK-TEMPLATE.md header format.
11. **Output**: 58 standardized task files.
12. **Preconditions**: FINDING-011 open.
13. **Invariant / Requirement Affected**: `INV-REL-002`
14. **Detailed Atomic Steps**:
1. Write a python script to parse existing uppercase key-value pairs (TASK ID, TITLE, TYPE, STATUS, EPIC, COMPLEXITY, etc.).
2. Generate standard Markdown frontmatter / header lines matching tasks/TASK-TEMPLATE.md.
3. Apply transformation across all 58 SPEC-* files in tasks/PHASE-00/.
4. Verify that each file parses with standard regex for TYPE, STATUS, and OWNER.

15. **Acceptance Criteria**:
    - `AC-DA-011-01: 100% of the 58 task files in tasks/PHASE-00/ contain separate lines for TYPE:, STATUS:, EPIC:, and OWNER:.`
16. **Validation Method**:
    ```powershell
    python -c "import glob; files = glob.glob('tasks/PHASE-00/SPEC-*.md'); assert all('STATUS:' in open(f, encoding='utf-8').read() for f in files)"
    ```
17. **Evidence Artifact**: `Git diff across tasks/PHASE-00/`
18. **Owner Role**: Task Decomposition Lead
19. **Estimated Size**: 90 min
20. **Dependencies**: `None`
21. **Blocks**: `None`
22. **Risk**: Script parsing error corrupting task body text.
23. **Recovery Note**: Test script on 1 file first; verify diff before applying batch.
24. **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
25. **Traceability**: `FINDING-011 -> TASK-DA-011 -> tasks/PHASE-00/`
