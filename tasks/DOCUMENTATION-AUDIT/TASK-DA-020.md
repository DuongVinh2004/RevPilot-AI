# TASK-DA-020 — Codify Synthetic Probe and Latency Evaluation Harness in SRE Specification

1. **Task ID**: TASK-DA-020
2. **Parent Finding ID**: FINDING-020
3. **Title**: Codify Synthetic Probe and Latency Evaluation Harness in SRE Specification
4. **Objective**: Add Section 6 'Synthetic Probe and Latency Evaluation Harness' to docs/23-observability/OBSERVABILITY-SPEC.md specifying Prometheus probe jobs and recording rules for NFR-LAT-001 and NFR-AVL-001.
5. **Single Expected Outcome**: docs/23-observability/OBSERVABILITY-SPEC.md contains concrete probe configuration contracts.
6. **Scope**: docs/23-observability/OBSERVABILITY-SPEC.md.
7. **Non-Goals**: Deploying live Prometheus server; writing Python test code.
8. **Exact File(s)**: `docs/23-observability/OBSERVABILITY-SPEC.md`
9. **Exact Section(s)**: §6 Synthetic Probe and Latency Evaluation Harness
10. **Input**: NFR-LAT-001 (<500ms p95), NFR-AVL-001 (>=99.9%), Prometheus Blackbox Exporter syntax.
11. **Output**: Expanded docs/23-observability/OBSERVABILITY-SPEC.md.
12. **Preconditions**: FINDING-020 open.
13. **Invariant / Requirement Affected**: `INV-REL-001, NFR-LAT-001, NFR-AVL-001`
14. **Detailed Atomic Steps**:
1. Draft Section 6 for docs/23-observability/OBSERVABILITY-SPEC.md.
2. Define synthetic blackbox probe endpoint contract (/healthz, /api/v1/healthz/deep).
3. Codify Prometheus recording rules for rolling 15-minute and 30-day p95 latency calculation.
4. Codify error budget burn rate alerting rules (2% burn in 1h, 5% burn in 6h).
5. Verify markdown formatting.

15. **Acceptance Criteria**:
    - `AC-DA-020-01: OBSERVABILITY-SPEC.md specifies synthetic probe endpoints, recording rules for NFR-LAT-001 p95 latency, and error budget burn rate alert formulas.`
16. **Validation Method**:
    ```powershell
    python -c "t = open('docs/23-observability/OBSERVABILITY-SPEC.md', encoding='utf-8').read(); assert 'Synthetic Probe' in t; assert 'recording rules' in t or 'Recording Rules' in t"
    ```
17. **Evidence Artifact**: `docs/23-observability/OBSERVABILITY-SPEC.md diff`
18. **Owner Role**: SRE Reviewer
19. **Estimated Size**: 60 min
20. **Dependencies**: `None`
21. **Blocks**: `None`
22. **Risk**: Vendor lock-in to specific monitoring provider.
23. **Recovery Note**: Use open-standard OpenTelemetry / Prometheus syntax.
24. **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
25. **Traceability**: `FINDING-020 -> TASK-DA-020 -> docs/23-observability/OBSERVABILITY-SPEC.md`
