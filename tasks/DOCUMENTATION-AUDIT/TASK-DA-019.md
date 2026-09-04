# TASK-DA-019 — Codify Explicit Non-Goals in Core Subsystem Specifications

1. **Task ID**: TASK-DA-019
2. **Parent Finding ID**: FINDING-019
3. **Title**: Codify Explicit Non-Goals in Core Subsystem Specifications
4. **Objective**: Add explicit 'Non-Goals' sections to major subsystem specifications to eliminate scope ambiguity.
5. **Single Expected Outcome**: MULTI-AGENT-SPEC.md, DATA-ARCHITECTURE.md, CAUSAL-INFERENCE-SPEC.md, and TEMPORAL-WORKFLOW-SPEC.md contain explicit Non-Goals sections.
6. **Scope**: docs/06-agent-platform/MULTI-AGENT-SPEC.md, docs/07-data-platform/DATA-ARCHITECTURE.md, docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md, docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md.
7. **Non-Goals**: Modifying existing functional goals; changing contracts.
8. **Exact File(s)**: `4 core subsystem specification files`
9. **Exact Section(s)**: §Non-Goals
10. **Input**: PRD §Non-Goals and ADR boundary decisions.
11. **Output**: 4 updated subsystem specifications.
12. **Preconditions**: FINDING-019 open.
13. **Invariant / Requirement Affected**: `INV-REL-002`
14. **Detailed Atomic Steps**:
1. Formulate exact Non-Goals for Multi-Agent platform (e.g. no autonomous credential generation, no arbitrary web browsing).
2. Formulate Non-Goals for Data platform (e.g. no real-time streaming CDC before Phase 07 trigger, no distributed Spark cluster).
3. Formulate Non-Goals for Causal AI (e.g. no automated causal discovery over uncurated schemas).
4. Formulate Non-Goals for Workflow engine (e.g. no arbitrary long-running process state in web API memory).
5. Insert sections and verify markdown rendering.

15. **Acceptance Criteria**:
    - `AC-DA-019-01: Each of the 4 subsystem specifications contains an explicit '## Non-Goals' section with at least 3 bulleted boundary constraints.`
16. **Validation Method**:
    ```powershell
    python -c "for f in ['docs/06-agent-platform/MULTI-AGENT-SPEC.md', 'docs/07-data-platform/DATA-ARCHITECTURE.md', 'docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md', 'docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md']: assert 'Non-Goals' in open(f, encoding='utf-8').read()"
    ```
17. **Evidence Artifact**: `Git diff across 4 subsystem specifications`
18. **Owner Role**: Principal Architect
19. **Estimated Size**: 60 min
20. **Dependencies**: `None`
21. **Blocks**: `None`
22. **Risk**: Over-restricting future product phases.
23. **Recovery Note**: Explicitly qualify non-goals with 'In MVP / v1 Release' scope.
24. **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
25. **Traceability**: `FINDING-019 -> TASK-DA-019 -> docs/06,07,10,12`
