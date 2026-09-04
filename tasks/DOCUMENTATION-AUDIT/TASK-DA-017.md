# TASK-DA-017 — Establish Repository Root AGENTS.md Policy File

1. **Task ID**: TASK-DA-017
2. **Parent Finding ID**: FINDING-017
3. **Title**: Establish Repository Root AGENTS.md Policy File
4. **Objective**: Create canonical AGENTS.md at repository root defining autonomous agent boundaries, safety invariants, and execution protocols.
5. **Single Expected Outcome**: AGENTS.md exists at repository root and passes agent inspection.
6. **Scope**: Root AGENTS.md file.
7. **Non-Goals**: Modifying existing execution policies in execution/.
8. **Exact File(s)**: `AGENTS.md`
9. **Exact Section(s)**: Entire file
10. **Input**: Audit instructions Section 1; execution/MICRO-TASK-RAIL-SYSTEM.md; Invariant Registry.
11. **Output**: New AGENTS.md file at repository root.
12. **Preconditions**: FINDING-017 open; file does not exist.
13. **Invariant / Requirement Affected**: `INV-REL-001, INV-REL-002, INV-ACT-001..004`
14. **Detailed Atomic Steps**:
1. Draft AGENTS.md covering: Agent Role & Mission, Mandatory Safety Rules, Non-Destructive Operation Policy, Rail Sequence & Fail-Closed Queue, and Links to Control Plane Files.
2. Write file to c:\Users\Duong Vinh\RevPilot AI\AGENTS.md.
3. Verify file existence and readability.

15. **Acceptance Criteria**:
    - `AC-DA-017-01: AGENTS.md exists at repository root and defines fail-closed queue, non-destructive execution, and core invariant references.`
16. **Validation Method**:
    ```powershell
    python -c "import os; assert os.path.exists('AGENTS.md'); assert 'Fail-Closed' in open('AGENTS.md', encoding='utf-8').read()"
    ```
17. **Evidence Artifact**: `New file AGENTS.md in git status`
18. **Owner Role**: Principal Architect & Safety Officer
19. **Estimated Size**: 45 min
20. **Dependencies**: `None`
21. **Blocks**: `TASK-DA-004`
22. **Risk**: Conflicting with existing execution guidelines.
23. **Recovery Note**: Ensure AGENTS.md directly cites execution/MICRO-TASK-RAIL-SYSTEM.md as authoritative.
24. **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
25. **Traceability**: `FINDING-017 -> TASK-DA-017 -> AGENTS.md`
